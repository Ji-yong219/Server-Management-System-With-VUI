$(document).ready(function(){
    // 팝업 검은부분 눌렀을 때
    $('#layer_popup').click(function(){
        $(this).hide();
        $('#popup_window').children().css("display", "none");
        $('#popup_window').css("display", "none");
    });

    // 팝업 X버튼 눌렀을 때
    $('#popup_close_button').click(function(){
        $("#layer_popup").hide();
        $('#popup_window').children().css("display", "none");
        $('#popup_window').css("display", "none");
    });
});

function popup_on(job){
    var maskHeight = $(document).height();
    var maskWidth = $(window).width();
    
    $('#layer_popup').css({'width':maskWidth, 'height':maskHeight});
    $('#layer_popup').fadeTo("slow", 0.8);
    
    $('#'+job).css("display", "block");
    $('#popup_window').css("display", "block");
    $('#popup_window span').css("display", "block");
}

function print_session(){
    $.ajax({ //session 출력 ajax
        type:"POST",
        url:"/",
        datatype:"json",
        data:"session:1",
        async:false,
        success:function(data){
            window.location.replace("/");
        }
    })
}

function regist_account(){
    popup_on('regist_window');
    $('#popup_title').text('회원 가입');
    
    $.ajax({ //session 출력 ajax
        type:"POST",
        url:"/",
        datatype:"json",
        data:"session:1",
        async:false,
        success:function(data){
            //window.location.replace("/");
        }
    })
}

// 비밀번호 확인 일치 함수
function is_pw_correct(target1, target2){
    if(target1 == document.getElementById("user_pw")) {
        if(target1.value != target2.value)
            $(".error_msg").text("비밀번호가 일치하지 않습니다.");
        else
            $(".error_msg").text("");
    }
}

// 회원가입 정보 이상 여부 함수
function check_regist_data(){
    var id_chk = $("#is_id_ok").val();
    var id = $("#user_id").val();
    var pw = $("#user_pw").val();
    var name = $("#user_name").val();
    $.ajax({
        type:"POST",
        url:"/regist",
        datatype:"json",
        data:{"id":id, "pw":pw, "name":name},
        success:function(data){
            id_chk = data;
            
            if(id_chk == "0"){
                $(".error_msg").text("");
                
                $('#popup_close_button').trigger("click");
                
                popup_on('insert_server');
                $('#popup_title').text('서버 추가');
            }
            else if(id_chk == "1"){
                $(".error_msg").text("이미 사용중인 아이디입니다.");
            }
            else if(id_chk == "2"){
                $(".error_msg").text("아이디는 최소 4자 이상 설정해야합니다.");
            }
            else{
                $(".error_msg").text("잘못된 입력입니다.");
            }
        }
    })
}