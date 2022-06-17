import threading
# from socket import *
import socket
import sys, os
from time import sleep
from commands import getstatusoutput as get_output
import platform

try :
    import pymysql, pexpect
except :
    os.system("curl -O -k https://bootstrap.pypa.io/get-pip.py")
    os.system("python get-pip.py")
    os.system("pip --trusted-host pypi.org \
        --trusted-host files.pythonhosted.org install pexpect pymysql")
    os.system("rm -f get-pip.py")
    import pymysql, pexpect
    
clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    clientSock.connect(('0.0.0.0', int(sys.argv[1])))
    
except socket.error as e:
    if e.errno != socket.errno.ECONNRESET:
        raise
    os.system("wall %s"%e)
    pass
    
except Exception as e:
    print('Connect Error : ', e)
    os.system("wall %s"%e)
    
else:
    print('Connected')
   
    connect_data = "connect:%s:%s"%(sys.argv[2], sys.argv[3])
    clientSock.send(connect_data)
    
    while True:
        try:
            recv = clientSock.recv(1024)    
            
        except Exception as e:
            print('Recv() Error :', e)                
            break
            
        else:           
            try:
                command = recv.decode()
                
                if command is None or command == "":
                    continue
                
                elif "mysql_install" in command:
                    ver = command.split(":")[1]
                    
                    clientSock.send("0%")
                    
                    os.system("systemctl stop mysqld > /dev/null 2>&1")
                    os.system("rpm -e $(rpm -qa | grep mysql) \
                        --nodeps > /dev/null 2>&1")
                    os.system("rm -rf /var/lib/mysql")
                    os.system("rm -f /var/log/mysqld.log")

                    os.system("firewall-cmd --zone=public --permanent \
                        --add-port=3306/tcp > /dev/null 2>&1")
                    os.system("firewall-cmd --reload > /dev/null 2>&1")

                    clientSock.send("5%")

                    if ver == "5.7":
                        os.system("rpm -Uvh http://dev.mysql.com/get/mysql57-community-release-el7-11.noarch.rpm")
                        
                    elif ver == "8.0":
                        os.system("rpm -Uvh https://dev.mysql.com/get/mysql80-community-release-el7-3.noarch.rpm")
                    
                    clientSock.send("70%")
                    
                    os.system("yum -y install mysql-community-server")
                    os.system("sed -i '4a\\port=3306' /etc/my.cnf")

                    os.system("echo {0} >> mysql_install.log".format("\nstarting mysql"))
                    os.system("systemctl start mysqld")
                    os.system("echo {0} >> mysql_install.log".format("\nsuccess\n"))

                    clientSock.send("80%")

                    temp, initial_passwd = get_output("grep 'temporary password'\
                         /var/log/mysqld.log")
                    initial_passwd = initial_passwd.split()
                    initial_passwd = initial_passwd[len(initial_passwd)-1]

                    mysql = pexpect.spawn("mysql -uroot -p")

                    mysql.expect("Enter password: ")
                    mysql.sendline(initial_passwd)

                    clientSock.send("90%")

                    mysql.expect("mysql> ")
                    mysql.sendline("ALTER USER 'root'@'localhost' \
                        IDENTIFIED BY 'Mymonitor123!';")

                    mysql.expect("mysql> ")
                    mysql.sendline("flush privileges;")

                    mysql.expect("mysql> ")
                    mysql.sendline("quit")

                    mysql.close()
                    
                    clientSock.send("100%")
                
                elif "get_monitoring_data" in command:
                    KERNEL = platform.platform().strip()
                    
                    CPU = get_output("echo -e $(top -n 1 -b | grep -i cpu\(s\) \
                        | awk '{print $2+$4+$6+$10+$12+$14+$16}') ")[-1]
                    
                    mem = str(os.popen('free -t -m').readlines())
                    T_ind = mem.index('T')
                    mem_G = mem[T_ind+14:-4].strip()
                    S1_ind = mem_G.index(' ')
                    mem_T = mem_G[0:S1_ind]
                    
                    mem_G1 = mem_G[S1_ind+8:].strip()
                    S2_ind = mem_G1.index(' ')
                    mem_U = mem_G1[0:S2_ind]

                    mem_F = mem_G1[S2_ind+8:].strip()
                    
                    RAM = str( round( float(mem_T) / float(mem_U), 2) ) + "%"
                    
                    DISK_TOTAL = str( get_output("fdisk -l | grep -i 'disk /dev'\
                         | awk '{sum+=$5} END {print sum}'")[-1].split("\n")[-1] )

                    DISK_USED = str(get_output("df -B1 | grep -v ^Filesystem \
                        | awk '{sum += $3} END {print sum}'")[-1].split("\n")[-1] )

                    DISK_PER = get_output("echo '"+DISK_USED+" "+DISK_TOTAL+" ' \
                        | awk '{printf \"%.1f\",$1/$2*100}'")[-1]

                    clientSock.send( f"{KERNEL},{RAM},{CPU},{DISK_PER}" )
                
                elif "get_usage" in command:
                    CPU = get_output("echo -e $(top -n 1 -b | grep -i cpu\(s\) |\
                         awk '{print $2+$4+$6+$10+$12+$14+$16}') ")[-1]

                    
                    mem = str(os.popen('free -t -m').readlines())
                    T_ind = mem.index('M')
                    mem_G = mem[T_ind+14:-4].strip()
                    S1_ind = mem_G.index(' ')
                    RAM_TOTAL = "%.1f"%( float(mem_G[0:S1_ind]) /1024 )
                    
                    mem_G1 = mem_G[S1_ind+8:].strip()
                    S2_ind = mem_G1.index(' ')
                    RAM_USED = "%.1f"%( float(mem_G1[0:S2_ind]) /1024 )

                    # RAM_FREE = mem_G1[S2_ind+8:].strip()
                    RAM_PER = "%.1f"%(float(RAM_USED) / float(RAM_TOTAL) * 100)
                    
                    
                    DISK_TOTAL = str( get_output("fdisk -l | grep -i 'disk /dev' \
                        | awk '{sum+=$5} END {print sum}'")[-1].split("\n")[-1] )

                    DISK_USED = str(get_output("df -B1 | grep -v ^Filesystem \
                        | awk '{sum += $3} END {print sum}'")[-1].split("\n")[-1] )

                    DISK_PER = get_output("echo '"+DISK_USED+" "+DISK_TOTAL+" ' \
                        | awk '{printf \"%.1f\",$1/$2*100}'")[-1]

                    DISK_TOTAL=get_output("echo "+DISK_TOTAL+" \
                        | awk '{printf \"%.1f\",($1/1024/1024/1024)}'")[-1]

                    DISK_USED=get_output("echo "+DISK_USED+" \
                        | awk '{printf \"%.1f\",($1/1024/1024/1024)}'")[-1]

                    clientSock.send(f"{CPU},{RAM_USED}:{RAM_TOTAL}:{RAM_PER},{DISK_USED}:{DISK_TOTAL}:{DISK_PER}")

                elif "get_detail" in command:
                    idx = len(platform.system())+len(platform.release())+1
                
                    OS = platform.platform().strip()[:idx]
                    KER = platform.platform().strip()[idx+1:]
                    ARCH = platform.architecture()[0]
                
                    CPU = get_output("grep -i 'model name' /proc/cpuinfo | sort -u | awk -F':' '{print $2}'")[-1].strip()
                    
                    RAM = get_output("free -ht | grep -i mem | awk '{print $2}'")[-1]
                    
                    STO = get_output("echo $(fdisk -l | grep -i 'disk /dev' | awk '{sum+=$5} END {print sum}')")[-1]
                    STO = f"{int(STO.split('\n')[-1])/1024/1024/1024}GB"
                    
                    try :
                        mysql_log = get_output("grep 'Version: ' /var/log/mysqld.log")[-1]
                        mysql_log = mysql_log.split("\n")
                        mysql_log = mysql_log[len(mysql_log)-1]
                        mysql_log = mysql_log.split()

                        ### version ###
                        mysql_ver = mysql_log[mysql_log.index("Version:")+1]

                        ### port ###
                        mysql_port = get_output("grep 'port=' /etc/my.cnf \
                            | awk -F'=' '{print $NF}'")[-1]
                        if len(mysql_port) == 0 :
                            mysql_port="3306"

                        ### status ###
                        active_check = get_output("systemctl is-active mysqld")[-1]

                        ### initial passwd ###
                        initial_passwd = get_output("grep 'temporary password' \
                            /var/log/mysqld.log")[-1]
                        initial_passwd = initial_passwd.split()
                        initial_passwd = initial_passwd[len(initial_passwd)-1]

                    except IndexError :
                        mysql_ver = "unknown"
                        mysql_port = "unknown"
                        initial_passwd = "unknown"
                        active_check = "unknown"
                        
                    except ValueError:
                        mysql_ver = "Not installed"
                        mysql_port = "Not installed"
                        active_check = "Not installed"

                    MYSQL = f"{mysql_ver}:{mysql_port}:{active_check}"
                    
                    result = f"{OS},{KER},{ARCH},{CPU},{RAM},{STO},{MYSQL}"
                    
                    clientSock.send( result.encode() )

                elif "mysql_policy_output" in command:
                    try:
                        idx = command.index(":")+1
                        mysql_pw = command[idx:]
                        
                        temp = f"""echo -e $(mysql -uroot -p'{mysql_pw}' mysql \
                            -e "SHOW VARIABLES LIKE 'validate_password%';")"""
                        
                        content = get_output(f"""echo -e $(mysql -uroot \
                            -p{mysql_pw} mysql -e "SHOW VARIABLES \
                            LIKE 'validate_password%';")""")[-1]
                        content = content.split("\n")[1]
                        content = content.split(" ")[2:]
                        
                        # print("\nplz TTTT\n", content)
                        # os.system("wall plz TTTT %s"%content)
                        
                        content = ";".join( [
                            content[1],
                            "",
                            content[4],
                            content[6],
                            content[8],
                            content[10],
                            content[12]
                        ] )
                    
                    except IndexError as e:
                        _, _, tb = sys.exc_info()
                        os.system(f"wall Error file_name!!!!{__file__}")
                        os.system(f"wall Error line No!!!!{tb.tb_lineno}")
                        os.system(f"wall Error!!!!{e}")
                        content = "Not installed;;Not installed;Not installed;\
                            Not installed;Not installed;Not installed"
                    
                    clientSock.send( content.encode() )
                    
                elif "security_check" in command:
                    os.system(f"/root/M_M/security_list.sh {sys.argv[3]}")
                    os.system("wall finish")
                    
                    clientSock.send("check_finish")
                
                elif "linux_info:" in command:
                    os.system(f"wall Command is {command}")
                    work = command.split(":")[1]
                    
                    if "last.sh" in work:
                        result = get_output("echo -e $(last -10 | grep -wvP \
                            'wtmp|^$' | tr  '\n' '\!' | tr -s ' ' ',')")[-1]
                        
                    elif "lastb.sh" in work:
                        result = get_output("echo -e $(lastb -10 | grep -wvP \
                            'btmp|^$' | tr  '\n' '\!' | tr -s ' ' ',')")[-1]
                    
                    elif "ip_ban_list.sh" in work:
                        result = get_output("echo -e $(firewall-cmd \
                            --list-rich-rules | awk -F'\"' '{print $4}' \
                            | tr '\n' ' ')$(grep -vP '#|^$' \
                            /etc/hosts.deny | awk -F':' '{print $NF}')")[-1]
                    
                    elif "user_list.sh" in work:
                        result = get_output("echo -e $(awk -F':' '{print $1}' \
                            /etc/passwd | tr '\n' ',')")[-1]
                    
                    elif "mysql_backup_list.sh" in work:
                        if os.path.isdir("/etc/mysql_back.d"):
                            result = get_output("ls /etc/mysql_back.d \
                                | tr '\n' ','")[-1]
                            
                        else:
                            result = "no"
                    
                    if result == "":
                        result = "1"
                        
                    clientSock.send(f"linux_info;{result}")
                    
                else:
                    os.system(f"wall run this command: {command}")
                    os.system(command)
                    
            except Exception as e:
                _, _, tb = sys.exc_info()
                os.system(f"wall Error file_name!!!!{__file__}")
                os.system(f"wall Error line No!!!!%s"%tb.tb_lineno)
                os.system(f"wall Error!!!!{e}")
                os.system(f"echo -e {e} > /root/M_M/m_m_socket_error.txt")