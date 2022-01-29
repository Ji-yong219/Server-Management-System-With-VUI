function click_monitoring() {
    var now_status = $("#monitoring_button").text();

    if (now_status == "모니터링 시작"){
        $("#monitoring_button").text("모니터링 중지");
        send_get_monitoring();
        
        var monitoring_job = setInterval(function(){
            if( $("#monitoring_button").text() == "모니터링 중지"){
                send_get_monitoring();
            }
            else{
                clearInterval(monitoring_job);
            }
        }, 1000);
        
    } else{
        $("#monitoring_button").text("모니터링 시작");
    }
};