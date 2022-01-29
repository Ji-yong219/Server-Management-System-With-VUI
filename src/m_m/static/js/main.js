
function go_logout(){
    $.ajax({ //로그아웃 전송 ajax
        type:"POST",
        url:"/logout",
        datatype:"json",
        data:"logout:1",
        async:false,
        success:function(data){
            window.location.replace("/");
        }
    })
}
    
<!-- 서버 목록 생성 -->
function print_user_servers(server_list){
    //var server_list = "{{user_servers}}";
    server_list = server_list.split(",");
    
    var icon = "red.png";
    
    for (i = 0 ; i < server_list.length ; i++){
    
        if( linux_connection.split(",").indexOf(server_list[i].split(":")[1]) != -1 ){
            icon = "green.png";
        }
        else{
            icon = "red.png";
        }
    
        var tbody = document.getElementById("server_list_tbody");
        var tr = document.createElement("tr");
        
        tr.innerHTML = "<td class = 'server_lists' colspan = 2>"+
            "<img src='/static/img/"+icon+"'>&nbsp;"+
            server_list[i].split(":")[0] + 
            "<button class = 'server_remove' colspan = 2 style='display:none'>X</button>"+
            "</td>" + "<span class = 'server_id'>" + server_list[i].split(":")[1] + "</span>";
        
        tbody.appendChild(tr);
        
        // 세부 정보 서버 목록
        var select_box = document.getElementById("server_select_box");
        
        var op = document.createElement("option");
        
        op.value = server_list[i].split(":")[1];
        op.innerHTML = server_list[i].split(":")[0];
        
        select_box.appendChild(op);
    }
}

function resizeIframe(obj) {
    obj.style.height = obj.contentWindow.document.documentElement.scrollHeight + 'px';
  }

$(document).ready(function(){
    var total_height = $("#i_window").outerHeight()+$("#i_detail").outerHeight();
    $("article").attr("style", "height:"+total_height+"px");
    $(".menu_tab_box").attr("style", "height:100%");
    $(".server_list_box").attr("style", "height:100%");

    //음성 인식 결과 명령어 왔을 때
    web_socket.on('voice_command', function(data){
        var target_num = data.window;

        if(target_num == 'last'){
            target_num = last_win;
        }
        else if( isNaN(target_num) ){
            data.type = "error";
            data.action = "잘못 된 입력입니다.";
        }


        // 새 창 여는 명령어
        if ( data.type == "n" ){
            if(data.window == 'last')
                target_num = getNextWindowNum();
            create_window(data.action, target_num);
        }
        
        // 창 닫는 명령어
        else if(data.type == 'x'){
            // 해당 창이 존재하는 경우에만 실행
            if( window_list.hasOwnProperty(target_num) ){
                window_list[target_num][0].close();
            }
        }
        
        // 페이지 이동 명령어
        else if(data.type == 'g'){
            // 이미 창이 존재하는 경우 경로 변경
            if( window_list.hasOwnProperty(target_num) ){
                window_list[target_num][0].location.href = data.action;
            }
            // 창이 존재하지 않는 경우 새로 생성
            else{
                create_window(data.action, target_num);
            }
        }

        // 자바스크립트 명령어
        else if(data.type == 'c'){
            try {
                if (data.action.length > 1){
                    // console.log(data);
                    window_list[target_num][0].location.href = data.action[0];
    
                    setTimeout(function(){
                        window_list[target_num][0].eval(data.action[1]);
                    }, 2000);
                }
                else{
                    console.log(window_list);
                    window_list[target_num][0].eval(data.action);
                }
            }
            catch (e) {
                if(e.name === 'RangeError') {
                    alert(`배열 생성자에 잘못된 인수가 입력되었습니다.`)
                }
                else if (e.name === `ReferenceError`) {
                    alert(`선언되지 않은 변수가 사용되고 있습니다.`)
                }
                else if (e.name === 'TypeError'){
                    alert('해당 '+ target_num+ '번 창은 존재하지 않습니다. 새 창을 생성해주세요.');
                }
            }
        }

        // 데이터 출력 명령어
        else if(data.type == 's'){
            var data_title = data.action[0];
            var data_length = data.action[1];
            var col = data.action[2];
            // var result_list = data.action[3].slice(1, data_length);
            var result_list = data.action[3];
            var win = null;

            // 이미 창이 존재하는 경우 경로 변경
            if( window_list.hasOwnProperty(target_num) ){
                win = window_list[target_num][0];
            }
            // 창이 존재하지 않는 경우 새로 생성
            else{
                win = create_window('/show', target_num);
            }
            
            // 1초 뒤 실행 (창 생성 대기)
            setTimeout(function(){
                win.location.href = "/show";
            }, 1000);
            
            // 2초 뒤 실행 (페이지 이동 대기)
            setTimeout(function(){
                var title = win.document.getElementById("title");
                title.innerHTML = data_title;
                var result_box = win.document.getElementById("result_box");
                
                result_box.innerHTML = '\
                    <table class="check_table table table-striped" style="margin:0 auto">\
                        <thead>\
                            <tr id = "table_title">\
                            </tr>\
                        </thead>\
                        <tbody id = "table_body">\
                        </tbody>\
                    </table>';
                
                var tr = win.document.getElementById("table_title");

                if (result_list == "1"){
                    result_box.innerHTML = '기록이 없습니다.';
                    return;
                }

                // 표 헤드 생성
                for( i=0 ; i < col.length ; i++){
                    var td = win.document.createElement("td");
                    
                    td.innerHTML = col[i];
                    tr.appendChild(td);
                }

                // 데이터 생성 (줄)
                for( i=0 ; i < data_length ; i++ ){

                    if(result_list[i] == null){
                        continue;
                    }

                    var row = result_list[i].replace("\r", "").split(",");
                    
                    tr = win.document.createElement("tr");
                    tr.className = "check_table_contain";
                    
                    var tbody = win.document.getElementById("table_body");
                    tbody.appendChild(tr);
                    
                    // 데이터 생성 (열)
                    for (j = 0 ; j < col.length ; j++){
                        td = win.document.createElement("td");
                        
                        td.className = "check_element";
                        td.innerHTML = row[j];
                        
                        if(j==0){
                            td.style.textAlign = "left";
                        }
                        else if(j==2 && data_title == "보안 점검 결과"){
                            if(row[j] == "안전"){
                                td.style.background = "green";
                                td.style.color = "white";
                                td.style.fontWeight = "bold";
                            }
                            else if(row[j] == "확인"){
                                td.style.background = "orange";
                                td.style.fontWeight = "bold";
                            }
                            else{
                                td.style.background = "red";
                                td.style.fontWeight = "bold";
                            }
                        }
                        else if(j==3 && data_title == "보안 점검 결과")
                            td.style.textAlign = "left";

                        else if(j==3 && data_title.indexOf("로그인")!=-1){
                            td.style.width = "400px";
                            td.innerHTML = [row[3], row[4], row[5], row[6], row[7], row[8], row[9]].join(' ');

                            tr.appendChild(td);
                            break;
                        }
                        
                        tr.appendChild(td);
                    }
                }
            }, 2000);
        }
        
        // 에러
        else if(data.type == "error"){
            $('#voice_result span').html(data.action);
            if (data.action.indexOf('성공적으로') == -1){
                var audio = new Audio('/static/audio/beep.mp3');
                audio.volume = 0.1;
                var promise = audio.play();

                if (promise !== undefined) {
                    promise.then(_ => {
                        // Autoplay started!
                    }).catch(error => {
                        // Autoplay was prevented.
                        // Show a "Play" button so that user can start playback.
                    });
                }    
            }
            
            setTimeout(function(){
                $('#voice_result span').html('듣고 있어요..');
            }, 2000);
            
        }
        
        last_win = target_num;
    });
    
    // 리눅스 서버 연결 됐을 때
    web_socket.on('linux_connect', function(msg){
        connection_list = msg.split(",");
        
        for(i=0 ; i<connection_list.length ; i++){
    
        server_idx = connection_list[i];
        
        var pre_item;
        
        $("#server_list_tbody tr").children().each(function(idx, item){
            
            if ( $(this).attr('class') == 'server_id'){
                if ($(this).text() == server_idx){
                    $(pre_item).children('img').attr('src', '/static/img/green.png');
                    
                    if (window.location.pathname == "/work"){
                        $(".check_single").each(function send_get_info_thread(i) {
                            var td = $("#server_table_body .server_table_contain")[i];
                            var this_server_name = $(td).children()[3].innerHTML;
                            
                            str = $(pre_item).text().substring(1, $(pre_item).text().length-2);
                            
                            if ( str == this_server_name) {
                                $(td).find("input").attr("disabled", false);
                                return false;
                            }
                        });
                    }
                    
                    return false;
                }
            }
            
            pre_item = item;
        });
        
        }
    });
    
    // 리눅스 서버 연결 해제됐을 때
    web_socket.on('linux_disconnect', function(msg){
        server_idx = msg;
        
        var pre_item;
        
        $("#server_list_tbody tr").children().each(function(idx, item){
            
            if ( $(this).attr('class') == 'server_id'){
                if ($(this).text() == server_idx){
                    if (window.location.pathname == "/work"){
                        $(".check_single").each(function send_get_info_thread(i) {
                            var td = $("#server_table_body .server_table_contain")[i];
                            var this_server_name = $(td).children()[3].innerHTML;
                            
                            str = $(pre_item).text().substring(1, $(pre_item).text().length-2);
                            
                            if ( str == this_server_name) {
                                $(td).find("input").attr("disabled", true);
                                return false;
                            }
                        });
                    }
                    
                    $(pre_item).children('img').attr('src', '/static/img/red.png');
                    return false;
                }
            }
            
            pre_item = item;
        });
    });
    
           
    web_socket.on('check_result', function(data){// 세부정보 페이지 보안점검 결과
        var result_list = data.data.slice(1, data.data.length);
        
        reseult_box = document.getElementById("s_check_result_box");
        
        reseult_box.innerHTML = '\
            <table class="check_table" style="margin:0 auto">\
                <thead>\
                    <tr class = "check_table_title">\
                        <td>항목 코드</td>\
                        <td>분류</td>\
                        <td>판단 결과</td>\
                        <td>점검 항목 결과</td>\
                    </tr>\
                </thead>\
                <tbody id = "check_table_body">\
                </tbody>\
            </table>';
            
        for( i=0 ; i < result_list.length ; i++ ){
            var row = result_list[i].replace("\r", "").split(",");
            
            var tr = document.createElement("tr");
            tr.className = "check_table_contain";
            
            var tbody = document.getElementById("check_table_body");
            tbody.appendChild(tr);
            
            for (j = 0 ; j < 4 ; j++){
                var td = document.createElement("td");
                
                td.className = "check_element";
                td.innerHTML = row[j];
                
                if(j==2){
                    if(row[j] == "안전"){
                        td.style.background = "green";
                        td.style.color = "white";
                        td.style.fontWeight = "bold";
                    }
                    else if(row[j] == "확인"){
                        td.style.background = "orange";
                        td.style.fontWeight = "bold";
                    }
                    else{
                        td.style.background = "red";
                        td.style.fontWeight = "bold";
                    }
                }
                else if(j==3)
                    td.style.textAlign = "left";
                
                tr.appendChild(td);
            }
        }
        $("#popup_window").css("width", screen.width-100);
        $("#s_check_result_box").css("width", "auto");
        $("#s_check_result_box").css("height", 500);
        $("#s_check_result_box").css("overflow-y", "scroll");
    });
     
    // 팝업 검은부분 눌렀을 때
    $('#layer_popup').click(function(){
        $(this).hide();
        $('#popup_window').children().css("display", "none");
        $('#popup_window').css("display", "none");
        $('#voice_popup').css("display", "none");
        popup_listening = false;
    });

    // 팝업 X버튼 눌렀을 때
    $('#popup_close_button').click(function(){
        $("#layer_popup").hide();
        $('#popup_window').children().css("display", "none");
        $('#popup_window').css("display", "none");
    });

    // 서버 추가 눌렀을 때
    $("#insert_server_button").click(function(){
        popup_on('insert_server');
        $('#popup_title').text('서버 추가');
    });
    
    // 서버 새로고침 눌렀을 때
    $("#refresh_server_button").click(function(){
        web_socket.emit('refresh_server_list');
    });
    
    // 세부 정보 눌렀을 때
    $("#detail_button").click(function(){
        popup_on('detail_window');
        $('#popup_title').text('세부정보 서버 선택');
    });
                
    // 서버 목록 직접 눌렀을 때
    $(".server_lists").click(function(){
        var server_id = $(this).next().text();
        var url = "/detail?select_server="+server_id;
        
        $('#i_window').attr('src',  url);
    });
    
    // 서버 목록 직접 눌렀을 때 (모니터링 페이지 테이블)
    $("#i_window").load(function(){
        var iframe_check =     setInterval(function(){
            iframe_item = $("#i_window").contents().find(".server_name");
            
            if (iframe_item.length > 0){
                $("#i_window").contents().find(".server_name").on("click", function(event){
                    var server_id = $(this).prev().text();
                    var url = "/detail?select_server="+server_id;
                    
                    // $("#i_detail").attr("src", url);
                    // $("#i_detail").attr('style', 'visibility:visible');
                });
                clearInterval(iframe_check);
            }
        }, 100);
    });
    

    // 서버목록 마우스 올리면 삭제 버튼
    $('.server_lists').mouseover(function(){ 
        $(this).children('.server_remove').css("display", "inline-block");
    });

    // 마우스 다시 떼면 삭제버튼 사라짐
    $('.server_lists').mouseleave(function(){ 
        $(this).children('.server_remove').css("display", "None");
    });

    // 서버 삭제 눌렀을 때
    $('.server_remove').click(function(){
        var this_id = $(this).parent().next().text();
        $(this).parent().remove();
        
        $.ajax({ // 서버 삭제 요청
            type:"POST",
            url:"/delete_server",
            datatype:"json",
            data:"delete_server_id="+this_id,
            async:false,
            success:function(data) {
                window.location.replace("/main");
            }
        })
    });

});

function popup_on(job, popup_title=null, idx=null){
    var maskHeight = $(document).height();
    var maskWidth = $(window).width();
    
    $('#layer_popup').css({'width':maskWidth, 'height':maskHeight});
    $('#layer_popup').fadeTo("slow", 0.8);
    
    $('#popup_title').text(popup_title);
    $('#popup_server_idx').text(idx);

    $('#'+job).css("display", "block");
    $('#popup_window').css("display", "block");
    $('#popup_window span').css("display", "block");
    $('#popup_server_idx').css("display", "none");

    if(popup_title == "리눅스 보안 점검"){
        $('#s_check_result_box').text('보안 점검 버튼을 누르시면 점검을 시작합니다.');
        $('#popup_window').css('width', '500px');
        $('#popup_window').css('height', 'auto');
        $('#s_check_result_box').css('width', '400px');
        $('#s_check_result_box').css('height', 'auto');
        $('#s_check_result_box').css('overflow-y', 'hidden');
    }
}

function send_work(work_name, idx=null, single=false){
    var server_list = new Array();

    if(single==true){
        web_socket.emit('send_command', {user_id:user_id, server_list:idx, command:work_name});
    }
    else{
        $("#i_window").contents().find(".check_single").each(function() {
            var opt = $(this).prop("disabled");
            
            if(!opt && $(this).prop("checked") == true)
                server_list.push( $(this).parent().next().next().text() );
        });
        
        if (server_list.join(',') != ""){
            web_socket.emit('send_command', {user_id:'{{user_id}}', server_list:server_list.join(','), command:work_name});
        }
    }
};

            
// 포트인지 판별후 아니면 초기화
function is_port(target){
    if(isNaN(target.val())){
        target.val("");
        $(".error_msg").text("숫자만 입력할 수 있습니다.");
    }
    else if(target.val() > 65535 || target.val() < 0){
        target.val("");
        $(".error_msg").text("포트 범위는 0 ~ 65535입니다.");
    }
    else{
        $(".error_msg").text("");
    }
}

// 비밀번호, 비밀번호 확인 일치 확인 후 후 초기화
function is_pw_correct(target1, target2){
    if(target1 == document.getElementById("now_pw")){
        if(target1.value != target2.value)
            $(".error_msg").text("현재 비밀번호가 일치하지 않습니다.");
        else
            $(".error_msg").text("");
    }
    if(target1 == document.getElementById("new_pw")) {
        if(target1.value != target2.value)
            $(".error_msg").text("바꿀 비밀번호가 일치하지 않습니다.");
        else
            $(".error_msg").text("");
    }
}

// 입력 내용이 ON 또는 OFF인지 확인 후 초기화
function is_on_off(target){
    var temp = target.value;
    
    if(temp=="ON" || temp=="OFF"){
        $(".error_msg").text("");
    }
    else{
        $(".error_msg").text("잘못된 입력입니다.");
    }
}

// 입력 내용이 ON 또는 OFF인지 확인 후 초기화
function is_low_medium_high(target){
    var temp = target.value;
    
    if(temp=="LOW" || temp=="MEDIUM"){
        $(".error_msg").text("");
    }
    else{
        $(".error_msg").text("잘못된 입력 또는 대문자로 입력하지 않았습니다.");
    }
}

// 입력 내용이 숫자인지 확인 후 초기화
function is_num(target){
    var temp = target.value;
    
    if( !isNaN(temp) ){
        $(".error_msg").text("");
    }
    else{
        target.value = "";
        $(".error_msg").text("숫자만 입력 가능합니다.");
    }
}

// 비밀번호 정책에 맞는지 검사
function check_pw_verify(new_passwd){
    <!-- var new_passwd = $("#new_pw").val(); -->
    <!-- var policy_values = $('.pw_policy_output').text().split("\n"); -->
    var policy_values = [0, 0, 0, 0, 0, 0];
    
    for( i = 0 ; i < $('.mysql_policy_contain').length ; i++ ){
        policy_values[i] = $($('.mysql_policy_contain')[i]).text();
    }
    
    if(policy_values == ""){
        return "현재 비밀번호가 올바르지 않습니다.";
    }
    
    var special_chr = /[!"#$%&'()*+,-.\/:;<=>?@[\]^_`{|}]/; // 특수문자
    var num = /[0-9]/; // 숫자
    var s_letter= /[a-z]/; //소문자
    var b_letter= /[A-Z]/; //대문자
    var count1 = 0;
    var count2 = 0;
    
    <!-- for( i = 0 ; i < policy_values.length ; i++ ){ -->
        <!-- policy_values[i] = policy_values[i].split(" ")[1]; -->
    <!-- } -->
    
    
    if(policy_values[4] == "LOW"){
        // length //
        if(new_passwd.length < policy_values[1]){
            return "비밀번호의 길이는 "+policy_values[1]+"자 이상 설정해주세요.";
        }
    }

    if(policy_values[4] == "MEDIUM"){
        // check_user_name //					
        if(policy_values[0] == "ON"){
            if(new_passwd == "root"){
                return "비밀번호는 ID와 같을 수 없습니다.";
            }
        }
    }

    // length //
    if(new_passwd.length < policy_values[1]){
        return "비밀번호의 길이는 "+policy_values[1]+"자 이상 설정해주세요.";
    }

    // mixed_case_count //
    for(i=0; i<new_passwd.length; i++){	    //대소문자 판별
        if(s_letter.test(new_passwd[i])){	//대문자가 정책에 맞게 있으면 카운트 증가
            count1 += 1 
        }
        else if(b_letter.test(new_passwd[i])){//소문자가 정책에 맞게 있으면 카운트 증가
            count2 += 1
        }
    }

    if (count1 >= policy_values[2] && count2 >= policy_values[2]){
        count1 = 0
        count2 = 0
    }
    else{
        return "대소문자가 포함되어 있지 않습니다."
    }

    // special_char_count //
    for(i=0; i<new_passwd.length; i++){
        if(special_chr.test(new_passwd[i])){	//특수문자 판별
            count1 += 1 						//특수문자 일시 카운트 증가
        }
    }

    if (count1 >= policy_values[5]){			//특수문자수가 정책에 맞으면 통과
        count1 = 0
    }
    else{										//특수문자수가 정책에 맞지 않으면 false 전송 후 종료
        return "특수문자가 포함되어 있지 않습니다.";
    }

    // number_count //
    for(i=0; i<new_passwd.length; i++){			//숫자가 있는지 판별
        if(num.test(new_passwd[i])){
            count1 += 1 						//숫자가 있으면 카운트 증가
        }
    }
    if (count1 < policy_values[3]){
        return "숫자가 포함되어 있지 않습니다.";
    }
    <!-- $(".error_msg").text(""); -->
    return "success";
}


//  음성 프롬프트 닫는 함수 (리스너상태로 돌아감)
function close_voice_prompt(){
    popup_listening = false;
    $('#voice_img').css("display", "none");
    $('#voice_result span').html('대기상태');
}

// 새 창 만드는 함수
function create_window(url="/popup", window_num=null){
    //var window_num =getNextWindowNum();
    if(window_num==null){
        window_num=getNextWindowNum();
    }
    target_num = window_num;
    
    var option = "width = 800, height = 800, location=no, menubar=no";
    
    window_list[window_num] = [window.open(url, window_num+"번", option)];
    window_list[window_num].push(
        window.setInterval(function(){
        checkWindow(window_num, window_list[window_num])
    }, 3000));
    
    // 팝업 차단 기능 확인
    var win = window_list[window_num][0];
    if (win == null || typeof(win) == "undefined" || (win == null && win.outerWidth == 0) || (win != null && win.outerHeight == 0) || win.test == "undefined")  {
        alert("팝업 차단 기능이 설정되어있습니다\n\n차단 기능을 해제(팝업 허용) 해주세요.");

        if(win){
            win.close();
        }
    }
    
    win.onload = function(){      // 페이지 로딩 후 실행
        win.document.title = window_num+"번";
        win.document.href=url;
    }
    return win;
}

// 다음에 띄울 창 번호 반환 함수
function getNextWindowNum(){
    var i;
    for(i=1 ; i<Object.keys(window_list).length+1 ; i++){
        for(var key in window_list){
            target = Number(key);
            if(i!=target && i<target){
                return i;
            }
            else if(i==target){
                break;
            }
        }
    }
    return i;
}

// 창 닫혔는지 확인 하는 함수
function checkWindow(window_num, win) {

    //창이 닫혔을 경우
    if (win[0] && win[0].closed) {
        window.clearInterval(win[1]);
        delete window_list[window_num];
    }
    else{
        win[0].document.title = window_num+"번";
    }
}