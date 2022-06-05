# -*- coding: utf-8 -*-

# 제작자 : 박지용
# 프로젝트 이름 : 다중 서버 관리 웹사이트
# 프로젝트 기능 : 음성 인식을 사용하여 다중의 Centos7 서버를 관리해주는 Flask 웹 서버
# 최초 제작 날짜 : 2019-09-02
# 최종 수정 날짜 : 2020-11-05


from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pymysql
import os
import time
import sys
import subprocess
import logging
from socket import *
from datetime import datetime as dt

import threading
import socketserver

from flask_socketio import SocketIO, emit

import src.m_m.text_convert as ttc

from engineio.payload import Payload

# too many packets error 방지
Payload.max_decode_packets = 50

app_flask = Flask(__name__)
app_flask.secret_key = 'super secret key'
app_flask.config['SESSION_TYPE'] = 'filesystem'

socketio = SocketIO(app_flask, logger = False, async_mode='threading')

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

HOST = "0.0.0.0"
LISTEN_PORT = 22034

#실시간 접속된 서버 목록 (딕셔너리)
linux_connection = {}


# 서버 종료 함수
def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

# 서버강제종료 라우트
@app_flask.route('/서버강제종료', methods=['GET'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...'



#데이터베이스 접속 함수
def connect_db(): 
    database = pymysql.connect(
                        host = '0.0.0.0',
                        port = 3306,
                        user = 'root',
                        passwd = '-',
                        db = 'm_m',
                        charset = 'utf8'
                    )
    return database


# M&M서버 계정에 아이디가 존재하는지 확인하는 함수
# 아이디 존재할시 1반환
# 아이디 존재X -> 0 반환
def id_exist(user_id):
    if len(user_id) < 4 :
        return 0
    
    else:
        db = connect_db()
        try:
            with db.cursor() as cursor:
                id_result = 0
                cursor.execute(f"SELECT EXISTS(\
                    select id from users where id="{user_id}") as success")
                id_result = cursor.fetchone()[0]
        finally:
            pass
            
        return id_result

# DB에 새 데이터를 추가하는 함수
# 첫째인자 : 테이블명
# 둘째인자 : ,로 구분된 문자열 형태의 칼럼들
# 셋째인자 : ,로 구분된 데이터들
# 반환값 : 삽입한 데이터의 id
def insert_data_in_db(table, keys, values):
    db = connect_db()
    
    with db.cursor() as cursor:
        sql_qur = f"insert into {table} ({keys}) values({values})"
        cursor.execute(sql_qur)
        
        this_id = db.insert_id()
        
        db.commit()
        
        return this_id
    
# DB에 기존 데이터를 수정하는 함수
# 첫째인자 : 테이블명
# 둘째인자 : 긴 문자열 형식의 수정할 칼럼
# 셋째인자 : 리스트 형식의 수정할 데이터
# 넷째인자 : 뒷부분에 가져올 조건 (where 등)
# 반환값 : 없음
def update_data_in_db(table, col, value, where):
    db = connect_db()
    data = ""
    col = col.split(",")
    
    if len(col) == 1:
        data = f'{col[0]} = "{value[0]}"'
        
    else:
        for i in range(len(col)):
            if i > 0:
                data += ","
            data += f"""{col[i]} = '{value[i].replace("'", "''")}' """
     
    with db.cursor() as cursor:
        #sql_qur = "update %s set %s = '%s' %s"%(table, col, data, where)
        sql_qur = f"update {table} set {data} {where}"
        
        cursor.execute(sql_qur)
        
        db.commit()
    
# DB에 데이터를 삭제하는 함수
# 첫째인자 : 테이블명
# 둘째인자 : 뒷부분에 가져올 조건 (where 등)
# 반환값 : 없음
def delete_data_in_db(table, where):
    db = connect_db()
    
    with db.cursor() as cursor:
        sql_qur = f"delete from {table} {where}"
        
        cursor.execute(sql_qur)
        
        db.commit()
    
# DB에서 원하는 데이터를 가져오는 함수
# 첫째인자 : 가져올 칼럼
# 둘째인자 : 테이블명
# 셋째인자 : 뒷부분에 가져올 조건 (where 등)
# 반환값 : 해당 조건으로 검색된 데이터
def get_data_from_db(selection, table, target):
    db = connect_db()
    
    with db.cursor() as cursor:
        result = 0

        # 아이디 찾기 명령일 경우 (개수도 같이 줘야함)
        if selection == "findID":
            sql_qur = f'select id from {table} {target}'
            
            result_count = cursor.execute(sql_qur)
            result = cursor.fetchall()
            
            return (result, result_count)
            
        else:
            sql_qur = f'select {selection} from {table} {target}'
            cursor.execute(sql_qur)
            result = cursor.fetchall()
            
            if result == ((None,),):
                result = [["-1"]]
            
            return result

# DB에서 해당 유저의 서버들을 가져오는 함수
# 인자 : 유저 id
# 반환값 : ,로 구분된 문자열 형태의 서버 목록
def get_servers(user_id):
    temp = get_data_from_db("servers", "users", f"where id = '{user_id}'")
    
    if temp == ():
        return []
        
    else:
        server_list = list(get_data_from_db(
            "name, id",
            "servers",
            f"where id in ({temp[0][0]}) order by name"
        ))

        for i in range( len(server_list) ):
            server_list[i] = ":".join(server_list[i][:1])
        
        return ",".join(server_list)


def get_data_from_socket(ip, port, id, pw, work, socket_port_idx):
    command = ['curl', '-s', '-m', '1', ip+':'+port]
    sp_stream = subprocess.Popen(command, stdout=subprocess.PIPE).stdout
    result = sp_stream.read().strip().decode('utf-8')
    sp_stream.close()
    
    try:
        if result[:3] == "SSH":
            socket_port = 50100 + int(socket_port_idx)
            
            serverSock = socket(AF_INET, SOCK_STREAM)
            serverSock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            serverSock.bind(('', socket_port))
            serverSock.settimeout(2)
            serverSock.listen(1)
        
            if work.split(".")[1] == "py":
                command = f"plink {ip} -l {id} -pw {pw} -P {port} -batch %s"\
                        + f"python ./M_M/{work} {socket_port}"
                
            elif work.split("@policy@")[0] == "mysql_policy_output.sh":
                mysql_pw = work.split("@policy@")[1].replace("'", "+@+@+")
                command = f"plink {ip} -l {id} -pw {pw} -P {port} -batch %s"\
                + f"./M_M/{work.split('@policy@')[0]} {socket_port} '{mysql_pw}'"
                
            else:
                command = f"plink {ip} -l {id} -pw {pw} -P {port} -batch %s"\
                + f"./M_M/{work} {socket_port}"
            
            result = os.system(command)
        
            connectionSock, addr = serverSock.accept()
            
            if result == 0 or result == 124:
                recvData = connectionSock.recv(1024)
                data = recvData.decode('utf-8').strip()
                
            else:
                data = "unknown"
                
        else:
            print("ssh 오류")
            data = "unknown"
    
    except Exception as e:
        print("오류:", e)
        data = "unknown"
    
    return data


# 원격서버(리눅스) 접속상태 확인 함수
def check_linux_connection():
    user_id = session['user_id']
    
    if user_id:
        server_list = [i.split(":")[1] for i in get_servers(user_id).split(",")]
        
        # print("\n\n서버리스트:", server_list)
        # print("커넥션리스트:", linux_connection.keys())
        
        connection_list = ",".join( list( set(server_list) & set(linux_connection.keys()) ) )
        
        socketio.emit('linux_connect', connection_list, namespace='/socket')
    

# 클라이언트 서버에 소켓파일 실행시키는 함수
def connect_socket_to_client(server_list = None):
    user_id = session['user_id']
    
    if user_id:
        if server_list is None:
            server_list = get_servers(user_id).split(",")
        
        if server_list != ['']:
            for i in range(len(server_list)):
                server_info = get_data_from_db(
                    "name, ip, ssh_id, ssh_pw, port, id",
                    "servers",
                    f"where id = {server_list[i].split(':')[1]}"
                )[0]
                
                server_name = str(server_info[0])
                server_ip = str(server_info[1])
                ssh_id = str(server_info[2])
                ssh_pw = str(server_info[3])
                server_port = str(server_info[4])
                server_id = str(server_info[5])
                
                
                contain = f"""'[Unit]
After=network.target

[Service]
Type=simple
User=root
Group=root
Environment=port={LISTEN_PORT} user={user_id} server={server_id}
ExecStart=/bin/python /root/M_M/socket_client.py $port $user $server
Restart=on-failure

[Install]
WantedBy=multi-user.target'"""


                command = " ".join([
                    f"plink {server_ip}",
                    f"-l {ssh_id}",
                    f"-pw {ssh_pw}",
                    f"-P {server_port}",
                    f"-batch",
                    '"echo -e',
                    f'{contain} > /usr/lib/systemd/system/m_m_socket.service"'])
                
                subprocess.Popen(command)
                
                command = " ".join([
                    f"plink {server_ip}",
                    f"-l {ssh_id}",
                    f"-pw {ssh_pw}",
                    f"-P {server_port}",
                    f"-batch",
                    '"systemctl daemon-reload"'])
                
                subprocess.Popen(command)
                
                command = " ".join([
                    f"plink {server_ip}",
                    f"-l {ssh_id}",
                    f"-pw {ssh_pw}",
                    f"-P {server_port}",
                    f"-batch",
                    '"systemctl restart m_m_socket"'])
                
                subprocess.Popen(command)
                
                command = " ".join([
                    f"plink {server_ip}",
                    f"-l {ssh_id}",
                    f"-pw {ssh_pw}",
                    f"-P {server_port}",
                    f"-batch",
                    '"systemctl enable m_m_socket"'])
                
                subprocess.Popen(command)
    

# 인덱스페이지 라우트
@app_flask.route("/", methods = ["GET", "POST"])
def go_index_page ():
    if request.method == "POST":
        print(session)
    
    return render_template("index.html")
    
    
# 로그인버튼 눌렀을 시 아이디, 비번 가져오는 라우트 (GET요청 불가능)
@app_flask.route("/login", methods = ["POST"])
def checking_login ():
    try:
        user_id = request.form['user_id']
        user_pw = request.form['user_pw']
        
        if len(user_id) >= 4: #ID 길이가 4자 이상인 경우
            if id_exist(user_id): #ID가 DB에 존재하는 경우
            
                db_pw = get_data_from_db(
                    "pw",
                    "users",
                    f"where id = '{user_id}'"
                )[0][0]

                if user_pw == db_pw: # DB에 있는 비밀번호와 같은 경우
                    session['user_id'] = user_id
                    
                    connect_socket_to_client()
                    
                    return redirect("/main")
                    
                else:
                    return """<script>
                                alert('비밀번호가 잘못되었습니다.');
                                window.location.replace('/')
                            </script>""" + render_template("index.html")
            else:
                return """<script>
                            alert('존재하지 않는 아이디입니다.');
                            window.location.replace('/')
                        </script>""" + render_template("index.html")
        else:
            return """<script>
                        alert('아이디는 4자 이상 입력해주세요.');
                        window.location.replace('/')
                    </script>""" + render_template("index.html")
            
    except Exception as e:
        _, _ , tb = sys.exc_info() # tb -> traceback object
        error_str = f"file name = {__file__}"
        error_str += f"\nerror line No = {tb.tb_lineno}"
        error_str += f"\n{e}"

        return render_template("error.html", error = str(error_str))
    
    return "<script>alert('잘못된 입력입니다.');window.location.replace('/')</script>" + render_template("index.html")


# 로그아웃버튼 눌렀을 시 session에서 해당 아이디 없애서 로그아웃하는 라우트
@app_flask.route("/logout", methods = ["POST"])
def checking_logout ():
    try:
        session["user_id"] = None
        return jsonify(True)
    
    except Exception as e:
        return render_template("error.html", error = str(e))
        
    return None

   
# 회원가입
@app_flask.route("/regist", methods = ["POST"])
def checking_regist ():
    try:
        user_id = request.form['id']
        user_pw = request.form['pw']
        user_name = request.form['name']
        
        if len(user_id) >= 4: #ID 길이가 4자 이상인 경우
            if not id_exist(user_id): #ID가 DB에 존재하는 경우
                insert_data_in_db(
                    "users",
                    "id,pw,name,q_a,join_date",
                    f'"{user_id}","{user_pw}","{user_name}","DBLAB","now()"'
                )
                # ",".join(['"'+user_id+'"', '"'+user_pw+'"', '"'+user_name+'"', '"DBLAB"', "now()"]))
            
                session['user_id'] = user_id
                
                return "0"
            else:
                return "1"
        else:
            return "2"
            
    except Exception as e:
        print("오류 내용 : ", e)
        return "3"
    
    return "3"

# 아이디 찾기
@app_flask.route("/find_id",methods=['GET','POST'])
def find_id():
    if request.method == 'POST':
        user_name = request.form['name']
        result_id = []

        result_all, result_count = get_data_from_db(
                                        'findID',
                                        'users',
                                        f'where name = "{user_name}"'
                                    )

        for i in range( result_count ):
            result_id.append(result_all[i][0])

        for i in range( len(result_id) ):
            temp = result_id[i]

            result_id[i] = temp[:1] + '***' + temp[4:]

        web_args = {
            'name_chk' : 'yes',
            'user_name' : user_name,
            'result_id' : result_id,
            'result_count' : result_count
        }
        
        return render_template('find_id.html', **web_args)

    return render_template('find_id.html', name_chk='no')

# 비밀번호 찾기
@app_flask.route("/find_pw",methods=['GET','POST'])
def find_pw():
    if request.method == 'POST':
        if 'name' in request.form:
            user_name = request.form['name']

            if id_exist(user_name):
                return render_template(
                    'find_pw.html',
                    name_chk='yes',
                    user_name = user_name,
                    id_result=''
                )
            else:
                return render_template(
                    'find_pw.html',
                    name_chk='no',
                    id_result='no'
                )

        if 'pw' in request.form:
            user_pw = request.form['pw']
            user_id = request.form['user_name']

            update_data_in_db("users", "pw", user_pw, f'where id="{user_id}"')

            return redirect("/")
            
    web_args = {
        'name_chk' : 'no',
        'id_result' : ''
    }

    return render_template('find_pw.html', **web_args)


#필요한 정보를 가져오는 라우트
@app_flask.route("/get_info", methods = ["POST"])
def get_info():
    if "give_me_server_list" in request.form:
        user_id = request.form["give_me_server_list"]
        if user_id == session["user_id"]:
        
            temp = get_data_from_db(
                "servers",
                "users",
                f"where id = '{user_id}'"
            )[0]
            
            user_server_list = list( get_data_from_db(
                    "name, ip, port, id", "servers",
                    f"where id in ({temp}) order by name")
            )
            temp = None
            
            for i in range( len(user_server_list) ):
                user_server_list[i] = list(user_server_list[i])
            
            return jsonify(data = user_server_list)


#서버 추가 라우트
@app_flask.route("/insert_server", methods = ["POST"])
def insert_server():
    if "insert_name" in request.form:
        user_servers = get_servers(session["user_id"])
        ip = request.form["insert_ip"]
        port = request.form["insert_port"]
        ssh_pw = request.form["insert_pw"]
        ssh_id = "root"
        
        # target_keys = "name, ip, ssh_id, ssh_pw, port, OS, kernel, arch, processor, ram, storage, users, date"
        target_keys = "name, ip, ssh_id, ssh_pw, port, users, date"
        
        target_values = []
        target_values.append(f"""'{request.form["insert_name"]}'""")
        target_values.append(f"'{ip}'")
        target_values.append(f"'{ssh_id}'")
        target_values.append(f"'ssh_pw'")
        target_values.append(f"'port'")
        # target_values.append("'"+os+"'")
        # target_values.append("'"+kernel+"'")
        # target_values.append("'"+arch+"'")
        # target_values.append("'"+pro+"'")
        # target_values.append("'"+ram+"'")
        # target_values.append("'"+sto+"'")
        target_values.append(f"""'{session["user_id"]}'""")
        target_values.append("now()")
        target_values = ",".join(target_values)
    
        this_id = insert_data_in_db("servers", target_keys, target_values)
        
        user_servers_id = get_data_from_db(
            "servers",
            "users",
            f"""where id = '{session["user_id"]}'"""
        )
        
        if user_servers_id == ():
            user_servers_id = []
        
        else:
            user_servers_id = user_servers_id[0][0].split(",")
        
        user_servers_id.append(str(this_id))
        
        if user_servers_id[0] == '-1':
            user_servers_id.remove('-1')
            
        user_servers_id = [",".join(user_servers_id)]
        
        where = f"""where id='{session['user_id']}'"""
        update_data_in_db("users", "servers", user_servers_id, where)
    
        return redirect(url_for('go_main_page'))
        
        
        web_args = {
            'user_id' : session['user_id'],
            'user_servers' : user_servers
        }

        return "<script>window.location.replace('/monitoring')</script>" +\
        render_template("monitoring.html", **web_args)


#서버 삭제 라우트
@app_flask.route("/delete_server", methods = ["POST"])
def delete_server():
    if "delete_server_id" in request.form:
        server_id = request.form["delete_server_id"]
        where = "where id = %s"%(server_id)
        server_list = get_data_from_db(
            "servers",
            "users",
            """where id = '{session["user_id"]}'"""
        )[0][0]
        
        server_list = server_list.split(",")
        server_list.remove(server_id)
        server_list = [",".join(server_list)]
    
        where2 = "where id='[session['user_id']]'"
        
        update_data_in_db("users", "servers", server_list, where2)
        delete_data_in_db("servers", where)
    
        return jsonify(date = "success")


#서버 수정 라우트   
@app_flask.route("/modify_server", methods = ["POST"])
def modify_server():
    global linux_connection
    if "modify_server_id" in request.form:
        server_idx = request.form["modify_server_id"]
        name = request.form["server_name"]
        ip = request.form["server_ip"]
        port = request.form["server_port"]

        server_info = get_data_from_db(f"ssh_id,ssh_pw,name,ip,port,OS,kernel\
            ,arch,processor,ram,storage,mysql_ver,mysql_port,mysql_reset_pw\
            ,mysql_pw_policy_chk_name,mysql_pw_policy_dic_file\
            ,mysql_pw_policy_length,mysql_pw_policy_mix_count\
            ,mysql_pw_policy_num_count,mysql_pw_policy_type\
            ,mysql_pw_policy_special_count","servers"\
            ,"where id = {server_idx}")[0]
        
        ssh_id = server_info[0]
        ssh_pw = server_info[1]
        
        # 서버가 꺼져 있을 때 (기본 정보만 수정)
        if linux_connection.get(server_idx) is None:
        
            where = f"where id='{server_idx}'"
        
            columns = "name,ip,port"
            
            values = [name,ip,port]
            
            for i in range(len(values)):
                if values[i] == "":
                    values[i] = str(server_info[i+2])
            
            update_data_in_db("servers", columns, values, where)
            
            return redirect(url_for('go_main_page'))
        
        
        linux_connection[server_idx][0].send("get_detail".encode())

        while True:
            if linux_connection[server_idx][1] != "":
                data = linux_connection[server_idx][1]
                linux_connection[server_idx][1] = ""
                break

        os,kernel,arch,pro,ram,sto,mysql = data.split(",")
        
        mysql_pw = get_data_from_db(
            "mysql_pw",
            "servers",
            f"where id = {server_idx}"
        )[0][0]
    
        if mysql == 'unknown':  mysql = "unknown:unknown:-1\nunknown"
        
        ms_ver, ms_port, ms_status = mysql.replace("'", '').split(":")

        linux_connection[server_idx][0].send(
            (f"mysql_policy_output:{mysql_pw}").encode()
        )
        
        while True:
            if linux_connection[server_idx][1] != "":
                mysql2 = linux_connection[server_idx][1]
                linux_connection[server_idx][1] = ""
                break

        if len(mysql2.split(";")) == 7:
            (
                ms_chk_name,
                ms_DF, ms_leng,
                ms_mix_count,
                ms_num_count,
                ms_policy_type,
                ms_special_count
            ) = mysql2.split(";")
            
        else:
            (
                ms_chk_name,
                ms_DF,
                ms_leng,
                ms_mix_count,
                ms_num_count,
                ms_policy_type,
                ms_special_count
            ) = (
                'Not installed',
                'Not installed',
                'Not installed',
                'Not installed',
                'Not installed',
                'Not installed',
                'Not installed'
            )
        
        
        where = f"where id='{server_idx}'"
        
        columns = "name,ip,port,OS,kernel,arch,processor,ram,storage,mysql_ver\
            ,mysql_port,mysql_pw_policy_chk_name,mysql_pw_policy_dic_file\
            ,mysql_pw_policy_length,mysql_pw_policy_mix_count\
            ,mysql_pw_policy_num_count,mysql_pw_policy_type\
            ,mysql_pw_policy_special_count"
        
        values = [
            name, ip, port, os, kernel, arch, pro, ram, sto, ms_ver,
            ms_port, ms_chk_name, ms_DF, ms_leng, ms_mix_count, ms_num_count,
            ms_policy_type, ms_special_count
        ]
        
        for i in range(len(values)):
            if values[i] == "":
                values[i] = str(server_info[i+2])

        update_data_in_db("servers", columns, values, where)
        
        return redirect(url_for('go_main_page'))



# 메인 페이지 라우트(껍데기, annyang프롬프트)
@app_flask.route("/main", methods = ["GET", "POST"])
def go_main_page ():
    global linux_connection
    if request.method == "GET":
        if "user_id" in session and session["user_id"] != None :
            
            user_servers = get_servers(session["user_id"])
            
            web_args = {
                'user_id' : session['user_id'],
                'user_servers' : user_servers,
                'linux_connection' : ','.join(linux_connection.keys())
            }
            
            return render_template("main.html", **web_args)
            
        return "<script>alert('로그인 후 이용해주세요.');\
        window.location.replace('/')</script>" + render_template("index.html")
    


#모니터링 페이지 라우트
@app_flask.route("/monitoring", methods = ["GET", "POST"])
def go_monitoring_page ():
    global linux_connection
    if request.method == "GET":
        if "user_id" in session and session["user_id"] != None :
        
            user_servers = get_servers(session["user_id"])
            
            web_args = {
                'user_id' : session['user_id'],
                'user_servers' : user_servers,
                'linux_connection' : ','.join(linux_connection.keys())
            }
            
            return render_template("monitoring.html", **web_args )
            
        return "<script>alert('로그인 후 이용해주세요.');\
        window.location.replace('/')</script>" + render_template("index.html")
       
       
    #세부 정보(서버 눌렀을 때)
    elif request.method == "POST":
        if "user_id" in session and session["user_id"] != None :
            
            user_servers = get_servers(session["user_id"])
            target_server = request.form["select_server"]
            
            try:
                server_info = get_data_from_db("id,name,ip,port,OS,kernel,arch,processor\
                ,ram,storage,mysql_ver,mysql_port,mysql_reset_pw,mysql_pw_policy_chk_name\
                ,mysql_pw_policy_length,mysql_pw_policy_mix_count\
                ,mysql_pw_policy_num_count,mysql_pw_policy_type,mysql_pw_policy_special_count",\
                "servers", "where id = %s"%(target_server))[0]
                server_name = str(server_info[1])
                server_ip = str(server_info[2])
                server_port = str(server_info[3])
            
                data = []
                
                for i in server_info:
                    data.append(str(i))
                    
                data = ",".join(data)
            
                web_args = {
                    'user_id' : session['user_id'],
                    'user_servers' : user_servers,
                    'data' : data,
                    'linux_connection' : ','.join(linux_connection.keys())
                }
                
                return render_template("detail.html", **web_args)
                

            except Exception as e:
                print("\n\n\n\n에러남;;;", e)
                
                web_args = {
                    'user_id' : session['user_id'],
                    'user_servers' : user_servers,
                    'data' : None
                }
            
                return render_template("detail.html", **web_args)
        
        
        return "<script>alert('로그인 후 이용해주세요.');\
        window.location.replace('/')</script>" + render_template("index.html")


#작업 페이지 라우트
@app_flask.route("/work", methods = ["GET", "POST"])
def go_work_page ():
    global linux_connection
    if request.method == "GET":
        if "user_id" in session and session["user_id"] != None :
        
            user_servers = get_servers(session["user_id"])
            
            web_args = {
                'user_id' : session['user_id'],
                'user_servers' : user_servers,
                'linux_connection' : ','.join(linux_connection.keys())
            }
                
            return render_template("work.html", **web_args)
            
        return "<script>alert('로그인 후 이용해주세요.');\
        window.location.replace('/')</script>" + render_template("index.html")


#세부정보 페이지 라우트
@app_flask.route("/detail", methods = ["GET"])
def go_detail_page ():
    global linux_connection
    if request.method == "GET":
        if "user_id" in session and session["user_id"] != None :
            
            user_servers = get_servers(session["user_id"])
            target_server = request.args.get("select_server")
            
            try:
                server_info = get_data_from_db("id,name,ip,port,OS,kernel,arch,processor\
                ,ram,storage,mysql_ver,mysql_port,mysql_reset_pw,mysql_pw_policy_chk_name\
                ,mysql_pw_policy_length,mysql_pw_policy_mix_count\
                ,mysql_pw_policy_num_count,mysql_pw_policy_type,mysql_pw_policy_special_count",\
                "servers", "where id = %s"%(target_server))[0]
                server_name = str(server_info[1])
                server_ip = str(server_info[2])
                server_port = str(server_info[3])
            
                data = []
                
                for i in server_info:
                    data.append(str(i))
                    
                data = ",".join(data)
                
                web_args = {
                    'user_id' : session['user_id'],
                    'user_servers' : user_servers,
                    'data' : data,
                    'linux_connection' : ','.join(linux_connection.keys())
                }
                
                return render_template("detail.html", **web_args)
                

            except Exception as e:
                print("\n\n\n\nerror!", e)
                
                web_args = {
                    'user_id' : session['user_id'],
                    'user_servers' : user_servers,
                    'data' : None
                }
            
                return render_template("detail.html", **web_args)
        
        return "<script>alert('로그인 후 이용해주세요.');\
        window.location.replace('/')</script>" + render_template("index.html")


#팝업창 라우트
@app_flask.route("/popup", methods = ["GET"])
def go_popup_page ():
        return render_template("popup.html")
        

#데이터 출력창 라우트
@app_flask.route("/show", methods = ["GET"])
def go_show_page ():
        return render_template("show.html")
        

# 웹소켓에서 서버 새로고침 요청 응답
@socketio.on("refresh_server_list", namespace='/socket')
def request_monitoring():
    connect_socket_to_client()


# 웹소켓에서 명령어 요청응답
@socketio.on("send_command", namespace='/socket')
def send_command(data):
    global linux_connection

    client_id = request.sid
    
    user_id = data['user_id'].encode('latin1').decode('utf8')
    server_list = data['server_list'].encode('latin1').decode('utf8')
    work_name = data['command'].encode('latin1').decode('utf8')
    
    for i in server_list.split(","):
        server_info = get_data_from_db("name, ip, ssh_id, ssh_pw, port", "servers", "where id = %s"\
        %(i))[0]
        # server_name = str(server_info[0])
        server_ip = str(server_info[1])
        server_id = str(server_info[2])
        server_pw = str(server_info[3])
        server_port = str(server_info[4])
        
        # 설치파일 업데이트
        if work_name == "update_file":
            target = "./src/m_m/command_files/*"
            path = "/root/"
            
            command = "pscp -pw %s -p -P %s %s %s@%s:%s"%\
            (server_pw, server_port, target, server_id, server_ip, path)
            
            os.system(command)
            
            command = "plink %s -l %s -pw %s -P %s -batch tar xvfm /root/M_M.tar"%\
            (server_ip, server_id, server_pw, server_port)
            
            os.system(command)
            
            # 소켓 프로그램 실행시키기
            connect_socket_to_client()
        
        # 보안 점검
        elif work_name == "security_check":
            path = "/root/M_M/" + i + "_security_result.log"
            target = "./src/m_m/log_files/" + i + "_sr.log"
            
            command = "security_check"
            linux_connection[i][0].send(command.encode())
            
            while True:
                time.sleep(1)
                
                if linux_connection[i][2] == "check_finish":
                    linux_connection[i][2] = ""
                    break
            
            command = "pscp -pw %s -p -P %s %s@%s:%s %s"%\
            (server_pw, server_port, server_id, server_ip, path, target)
            
            os.system(command)
            
            time.sleep(2)
            
            with open( "./src/m_m/log_files/%s"%(i + "_sr.log"), "r", encoding="utf8" ) as f:
                check_result = f.readlines()
            
            good, warning, danger = check_result[0].strip().split(",")
            
            now_datetime = dt.today()
            
            log_file_name = i+"_"+ now_datetime.strftime("%Y%m%d%H%M%S")+".log"
            
            command = "REN .\\src\\m_m\\log_files\\%s %s"%(i + "_sr.log", log_file_name)
            
            target_keys = "date,id,good,warning,danger,log"
            
            target_values = ["'"+now_datetime.strftime("%Y-%m-%d %H:%M:%S")+"'"]
            target_values.extend([i, good, warning, danger])
            target_values.append("'" + log_file_name + "'")
            target_values = ",".join(target_values)
            insert_data_in_db("server_check", target_keys, target_values)
            
            # 삭제
            os.system(command)
            
            # 웹 반환
            emit("check_result", {'data':check_result})
        
        elif "ch_mysql_pw" in work_name:
            new_pw = work_name.split("/:,:/")[1]
            now_pw = get_data_from_db("mysql_pw", "servers", "where id = %s"%i)[0][0]
            
            where = 'where id = %s'%i
            update_data_in_db("servers", 'mysql_pw', [new_pw], where)
            
            now_pw = now_pw.replace('"', "-@-@-").replace("'", "+@+@+")
            
            new_pw = new_pw.replace('"', "-@-@-").replace("'", "+@+@+")
            
            work_name = "mysql_pw_ch.sh '"+now_pw+"' '"+new_pw+"'"
            
            command = "/root/M_M/%s >> /root/M_M/error.log"%work_name
            print (command)
            linux_connection[i][0].send(command.encode())
            
        elif "ch_mysql_policy" in work_name:
            key_list = ["mysql_pw_policy_chk_name","mysql_pw_policy_length","mysql_pw_policy_mix_count"\
            ,"mysql_pw_policy_num_count","mysql_pw_policy_type","mysql_pw_policy_special_count"]
            
            value_list = work_name.split("/:,:/")[1].split(";")
            
            now_pw = get_data_from_db("mysql_pw", "servers", "where id = %s"%i)[0][0]
            ver = get_data_from_db("mysql_ver", "servers", "where id = %s"%i)[0][0]
            
            where = 'where id = %s'%i
            
            for j in range(len(key_list)):
                if value_list[j] is None or value_list[j] == "":
                    continue
                    
                update_data_in_db("servers", key_list[j], [value_list[j]], where)
            
                now_pw = now_pw.replace('"', "-@-@-").replace("'", "+@+@+")
                
                work_name = "mysql_policy_ch.sh '" +now_pw+"' "+ ver[0]+" "+str(j)+" "+ value_list[j]
            
                command = "/root/M_M/%s"%(work_name)
                
                linux_connection[i][0].send(command.encode())
        
        elif work_name == "mysql_backup.sh":
            now_pw = get_data_from_db("mysql_pw", "servers", "where id = %s"%i)[0][0]
            
            now_pw = now_pw.replace('"', "-@-@-").replace("'", "+@+@+")
            
            work_name = "mysql_backup.sh '" + now_pw +"'"
            
            command = "/root/M_M/%s"%(work_name)
            
            linux_connection[i][0].send(command.encode())
            
        elif "mysql_rollback" in work_name:
            now_pw = get_data_from_db("mysql_pw", "servers", "where id = %s"%i)[0][0]
            
            now_pw = now_pw.replace('"', "-@-@-").replace("'", "+@+@+")
            
            file_name = work_name.split(":")[1]
            
            work_name = "mysql_rollback.sh '" + now_pw+"' " + file_name
            
            command = "/root/M_M/%s"%(work_name)
            
            linux_connection[i][0].send(command.encode())
            
        elif "linux_info:" in work_name:
            linux_connection[i][0].send(work_name.encode())
            
            while True:
                time.sleep(1)
                
                if "linux_info;" in linux_connection[i][2]:
                    result = linux_connection[i][2].split(";")[1]
                    break
            
            result = work_name.split(":")[1]+ ";" + result
            
            # 웹 반환
            emit("linux_info", {'data':result})
            
        else:
            # command = "plink %s -l %s -pw %s -P %s -batch %s"%\
            # (server_ip, server_id, server_pw, server_port, "./M_M/%s"%(work_name))
            # os.system(command)
            # linux_connection[user_id][1][i].send(work_name.encode())
            linux_connection[i][0].send(work_name.encode())
            
            if work_name.split(":")[0] == "mysql_install":
                success = "0%"
                
                while True:
                    success = linux_connection[i][0].recv(1024)
                    
                    if success == "100%":
                        emit("mysql_install", {'data':success.decode()})
                        break
                        
                    elif success == "":
                        emit("mysql_install", {'data':"설치 실패!"})
                        break
                    
                    else:
                        emit("mysql_install", {'data':success.decode()})


# 웹소켓에서 모니터링 데이터 요청 응답
@socketio.on("get_monitoring_data", namespace='/socket')
def request_monitoring(data):
    global linux_connection
    
    client_id = request.sid
    
    user_id = data['user_id'].encode('latin1').decode('utf8')
    
    monitoring_data = []
    
    for i, id in enumerate(list(linux_connection.keys())):
        monitoring_data.append([id])
        data = "get_monitoring_data"
        linux_connection[id][0].send(data.encode())
        
        while True:
            if linux_connection[id][1] != "":
                data = linux_connection[id][1]
                linux_connection[id][1] = ""
                break
        
        monitoring_data[i].append( data.split(",") )
    
    emit("monitoring_list", {'data':monitoring_data})

# 웹소켓에서 디테일 실시간 데이터 요청 응답
@socketio.on("get_usage", namespace='/socket')
def request_usage(data):
    global linux_connection
    
    client_id = request.sid
    
    user_id = data['user_id'].encode('latin1').decode('utf8')
    server_idx = data['server_idx'].encode('latin1').decode('utf8')
    
    if server_idx in linux_connection.keys():
        linux_connection[server_idx][0].send("get_usage".encode())
        
        while True:
            if linux_connection[server_idx][1] != "":
                usage_data = linux_connection[server_idx][1]
                linux_connection[server_idx][1] = ""
                break
            time.sleep(1)
        
        emit("return_usage", {'data':usage_data})



server_url_dic = {
    '모니터링페이지':'/monitoring',
    '작업페이지':'/work',
    '세부정보페이지':'/detail',
    '상세정보페이지':'/detail'
}
data_list = {
    '창': '/popup'
}
command_list = [
    ["유저목록", "유저리스트", "유저들", "사용자목록", "사용자리스트", "사용자들"],
    ["IP차단목록", "IP차단리스트", "아이피차단목록", "아이피차단리스트"],
    ["로그인성공기록", "로그인성공리스트"],
    ["로그인실패기록", "로그인실패리스트"],
    ["데이터베이스백업목록", "데이터베이스백업리스트", "DB백업목록", "DB백업리스트"]
]


#음성 명령 요청 응답
@socketio.on('voice_command', namespace='/socket')
def voice_command(data):
    user_id = data.get('id')
    command_text = data.get('text')
    
    print("\n\n\n\n음성인식결과:",command_text)
    
    server_list = get_servers(user_id).split(",")
    server_id_list = [ i.split(":")[1] for i in server_list ]

    command = ttc.convert_command(command_text, server_list)
    print("명령어 변환 결과:",command)
    
    # 해당 명령어가 없는 경우
    if command.get('type') is None or command.get('type') == 'None':
        command['type'] = 'error'
        command['action'] = '잘 이해하지 못했어요, 다시 말씀해주세요.'

    # 페이지 이동 명령어
    elif command.get('type') == 'g':
        command['action'] = command['action'].replace(" ", "")
        command['action'] = server_url_dic.get( command['action'] )

        if command.get('action') is None or command.get('action') == 'None':
            command['type'] = 'error'
            command['action'] = '요청하신 페이지를 찾지 못했어요.'

        if command['target'] is not None:
            target_server = command['target']
            command['action'] += f"?select_server={target_server}"
    
    # 새 창 생성 명령어
    elif command.get('type') == 'n':
        command['action'] = command['action'].replace(" ", "")
        if command.get('action') is None  or command.get('action') == 'None':
            command['type'] = 'error'
            command['action'] = '요청하신 데이터를 찾지 못했어요.'

        elif command.get('action') in server_url_dic:
            command['action'] = server_url_dic.get(command.get('action'))

            if command['target'] is not None:
                target_server = command['target']
                command['action'] += f"?select_server={target_server}"

        elif command.get('action') not in server_url_dic:
            command['action'] = "/popup"

        elif command.get('action') == "서버목록":
            temp = get_data_from_db("servers", "users", "where id = '%s'"%(user_id))[0]
            
            user_server_list = list( get_data_from_db("name, ip, port, id", "servers", "where id in (%s)"%(temp)) )
            
            for i in range( len(user_server_list) ):
                user_server_list[i] = list(user_server_list[i])
            
            command['action'] = [['서버 이름', 'IP', 'SSH 포트', '서버 ID']] + user_server_list

        else:
            command['type'] = 'error'
            command['action'] = '요청하신 데이터를 찾지 못했어요.'

    # 단순 명령어
    if command.get('type') == 'c':
        request_command = command.get('action').replace(' ', '')
        if request_command == "로그아웃":
            session["user_id"] = None
            command['type'] = 'go_page'
            command['action'] = '/'
        
        elif "모니터링" in request_command:
            command['action'] = ['/monitoring', 'click_monitoring()']
        
        elif request_command == "연결":
            server_id = command.get('target')

            if server_id in server_id_list:
                connect_socket_to_client(["temp:"+server_id])
                command['type'] = 'error'
                command['action'] = '성공적으로 해당 서버에 연결을 시도했습니다.'

            else:
                command['type'] = 'error'
                command['action'] = '해당 서버는 존재하지 않습니다.'
        
        elif request_command == "파일업데이트":
            server_id = command.get('target')

            if server_id in server_id_list:
                target = "./src/m_m/command_files/*"
                path = "/root/"
                
                server_info = get_data_from_db("ip, ssh_pw, port", "servers", "where id = %s"\
                %(server_id))[0]
                server_ip = str(server_info[0])
                server_pw = str(server_info[1])
                server_port = str(server_info[2])

                ssh_command = "pscp -pw %s -p -P %s %s root@%s:%s"%\
                (server_pw, server_port, target, server_ip, path)
                
                os.system(ssh_command)
                
                ssh_command = "plink %s -l root -pw %s -P %s -batch tar xvfm /root/M_M.tar"%\
                (server_ip, server_pw, server_port)
                
                os.system(ssh_command)
                
                # 소켓 프로그램 실행시키기
                connect_socket_to_client(["temp:"+server_id])

                command['type'] = 'error'
                command['action'] = '성공적으로 해당 서버의 파일을 업데이트했습니다.'

        elif request_command == "보안점검":
            server_id = command.get('target')

            if server_id in server_id_list:
                connect_socket_to_client(["temp:"+server_id])
                time.sleep(2)

                target = "./src/m_m/command_files/*"
                path = "/root/"
                
                server_info = get_data_from_db("ip, ssh_pw, port", "servers", "where id = %s"\
                %(server_id))[0]
                server_ip = str(server_info[0])
                server_pw = str(server_info[1])
                server_port = str(server_info[2])


                path = "/root/M_M/" + server_id + "_security_result.log"
                target = "./src/m_m/log_files/" + server_id + "_sr.log"
                
                ssh_command = "security_check"
                linux_connection[server_id][0].send(ssh_command.encode())
                
                # 점검 끝날 때까지 무한루프
                while True:
                    time.sleep(1)
                    
                    if linux_connection[server_id][2] == "check_finish":
                        linux_connection[server_id][2] = ""
                        break
                
                ssh_command = "pscp -pw %s -p -P %s root@%s:%s %s"%\
                (server_pw, server_port, server_ip, path, target)
                
                os.system(ssh_command)
                
                time.sleep(2)
                
                with open( "./src/m_m/log_files/%s"%(server_id + "_sr.log"), "r", encoding="utf8" ) as f:
                    check_result = f.readlines()
                
                good, warning, danger = check_result[0].strip().split(",")
                
                now_datetime = dt.today()
                
                log_file_name = server_id+"_"+ now_datetime.strftime("%Y%m%d%H%M%S")+".log"
                
                ssh_command = "REN .\\src\\m_m\\log_files\\%s %s"%(server_id + "_sr.log", log_file_name)
                
                target_keys = "date,id,good,warning,danger,log"
                
                target_values = ["'"+now_datetime.strftime("%Y-%m-%d %H:%M:%S")+"'"]
                target_values.extend([server_id, good, warning, danger])
                target_values.append("'" + log_file_name + "'")
                target_values = ",".join(target_values)
                insert_data_in_db("server_check", target_keys, target_values)
                
                # 삭제
                os.system(ssh_command)
            
                command['type'] = 's'
                command['action'] = ['보안 점검 결과', len(check_result)-1, ["항목 코드", "분류", "판단 결과", "점검 항목 결과"], check_result[1:]]

            else:
                command['type'] = 'error'
                command['action'] = '해당 서버는 존재하지 않습니다.'

        elif request_command == "데이터베이스백업":
            server_id = command.get('target')

            if server_id in server_id_list:
                # 소켓 프로그램 실행시키기
                connect_socket_to_client(["temp:"+server_id])
                time.sleep(1)

                now_pw = get_data_from_db("mysql_pw", "servers", "where id = %s"%server_id)[0][0]
                
                now_pw = now_pw.replace('"', "-@-@-").replace("'", "+@+@+")
                
                work_name = "mysql_backup.sh '" + now_pw +"'"
                
                ssh_command = "/root/M_M/%s"%(work_name)
                
                linux_connection[server_id][0].send(ssh_command.encode())

                command['type'] = 'error'
                command['action'] = '성공적으로 데이터베이스를 백업했습니다.'

                # command['type'] = 's'
                # request_command = '데이터베이스백업리스트'

        elif request_command is None or request_command == 'None':
            command['type'] = 'error'
            command['action'] = '요청하신 명령어를 찾지 못했어요.'
    
    # 데이터 출력 명령어
    if command.get('type') == 's':
        server_id = command.get('target')

        if server_id in server_id_list:
            connect_socket_to_client(["temp:"+server_id])

            request_command = command.get('action')

            if type( request_command ) == str:
                request_command = request_command.replace(' ', '')
                command['action'] = [0, 0, 0, 0]

                file_name = ''
                data_exist = True

                # 유저 목록
                if request_command in command_list[0]:
                    file_name = 'linux_info:user_list.sh'
                
                    command['action'][0] = '유저 목록'
                    command['action'][2] = ["유저 명"]

                # IP 차단 목록
                elif request_command in command_list[1]:
                    file_name = 'linux_info:ip_ban_list.sh'
                
                    command['action'][0] = 'IP 차단 목록'
                    command['action'][2] = ["IP"]

                # 로그인 성공 기록
                elif request_command in command_list[2]:
                    file_name = 'linux_info:last.sh'
                
                    command['action'][0] = '로그인 성공 기록'
                    command['action'][2] = ["User", "Terminal", "IP", "Date"]

                # 로그인 실패 기록
                elif request_command in command_list[3]:
                    file_name = 'linux_info:lastb.sh'
                
                    command['action'][0] = '로그인 실패 기록'
                    command['action'][2] = ["User", "Terminal", "IP", "Date"]

                # DB 백업 목록
                elif request_command in command_list[4]:
                    file_name = 'linux_info:mysql_backup_list.sh'
                
                    command['action'][0] = 'MySQL 백업 리스트'
                    command['action'][2] = ["백업 파일"]

                else:
                    data_exist = False
                    command['type'] = 'error'
                    command['action'] = '요청하신 데이터를 찾지 못했어요.'

                if data_exist:

                    result = None

                    while True:
                        try:
                            linux_connection[server_id][0].send(file_name.encode())
                            
                            count = 0
                            while True:
                                if count > 30:
                                    command['type'] = 'error'
                                    command['action'] = '데이터를 받아오지 못했습니다.'
                                    break
                                
                                if "linux_info;" in linux_connection[server_id][2]:
                                    result = linux_connection[server_id][2].split(";")[1]
                                    linux_connection[server_id][2] = ""
                                    break

                                time.sleep(0.1)
                                count += 1

                        except KeyError:
                            connect_socket_to_client(["temp:"+server_id])
                            time.sleep(1)

                        else:
                            break

                    if result is not None:
                        if "로그인" in request_command:
                            result = [i for i in result.split('!')[:-1]]
                        else:
                            result = [i for i in result.split(",")[:-1]]

                        command['action'][1] = len(result)
                        command['action'][3] = result

        else:
            command['type'] = 'error'
            command['action'] = '요청하신 데이터를 찾지 못했어요.'

    print("명령어 최종 결과:",command)
    emit('voice_command', command)
    

# class TcpHandler(socketserver.BaseRequestHandler):
class TcpHandler(socketserver.StreamRequestHandler):

    # socketserver.BaseRequestHandler를 상속했다면 반드시 오버라이딩 해줘야함
    # 요청을 서비스하는데 필요한 모든 작업을 수행하는 함수 (클라이언트로부터 request가 왔을때 실행)
    # 요청은 self.request로 제공됨. (스트림 서비스인 경우 소켓 객체임)
    # 클라이언트 주소는 self.client_address로 제공됨.
    # 서버 인스턴스는 self.server로 제공됨.
    def handle(self): # 클라이언트가 접속시 클라이언트 주소 출력
        print('리눅스 클라이언트 [%s] 연결됨' %self.client_address[0])
        
        server_user_id = None
        server_idx = None
        linux_connection = self.server.linux_connect_dict
        
        client_addr = self.client_address
        
        msg = None
        
        msg = self.request.recv(1024)
        
        
        while msg:
            if msg.decode() and len(msg.decode().split(":")) == 3 and msg.decode().split(":")[0] == "connect":
                
                server_user_id, server_idx = msg.decode().split(":")[1:]
                
                socketio.emit('linux_connect', server_idx, namespace='/socket')
                
                linux_connection[server_idx] = [self.request, "", ""]
                
                
            msg = self.request.recv(1024)
            
            if msg.decode() == "check_finish":
                linux_connection[server_idx][2] = msg.decode()
                
            elif "linux_info;" in msg.decode():
                linux_connection[server_idx][2] = msg.decode()
            
            else:
                linux_connection[server_idx][1] = msg.decode()

        print('[%s] 접속종료' %self.client_address[0])
        socketio.emit('linux_disconnect', server_idx, namespace='/socket')
        
        if server_idx in linux_connection.keys():
            del linux_connection[server_idx]

# class ListenerServer(socketserver.ThreadingTCPServer):
class ListenerServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, host_port_tuple, streamhandler, Controllers):
        super().__init__(host_port_tuple, streamhandler)
        self.linux_connect_dict = Controllers
    pass


def runListenerServer():
    global linux_connection
    
    try:
        print('--- 소켓 리스너 서버를 시작합니다.')
        
        # server = ListenerServer((HOST, LISTEN_PORT), TcpHandler)
        server = ListenerServer((HOST, LISTEN_PORT), TcpHandler, linux_connection)
        
        server.serve_forever() # shutdown() 요청이 있을때까지 요청을 처리함.
        # poll_interval=0.5 이며, poll_interval 초마다 shutdown을 확인함.
    
    except KeyboardInterrupt:
        print('--- 소켓 리스너 서버를 종료합니다.')
        server.shutdown() # serve_forever() 루프가 정지하도록 하고 기다림
        server.server_close()
        
    except OSError:
        print("중복 실행 금지")
        pass


def run_flask_server():
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        print("메인일때만 나오는 로직")
    
        socket_server = threading.Thread(target = runListenerServer)
        socket_server.daemon = True
        socket_server.start()
    
    
    context = ('./cert/server.crt', './cert/server.key')
    socketio.run(app_flask, host = "0.0.0.0", debug = True, ssl_context=context)