function to_post_without_form(data){
    
    var result = "";
    
    for (i = 0 ; i < data.length ; i+=2){
        result += data[i] + "=" + data[i+1] + "&"; 
    }
    
    result = result.substr(0, result.length - 1);
    
    return result;
}

self.addEventListener('message', function(e) {
    
    var xhr = new XMLHttpRequest();
    
    xhr.onload = function() {
        if (this.status == 200 && this.readyState == this.DONE){
            
            got_data = xhr.responseText;
    
            postMessage(got_data);
        }
    }
    
    index = e.data.split(":")[0];
    id = e.data.split(":")[1];
    user_id = e.data.split(":")[2];
    
    // IE, Edge
    if(typeof FormData == "undefined"){
        var data = [];
        
        data.push('monitoring', user_id);
        data.push('index', index);
        data.push('id', id);
        
        data = to_post_without_form(data);
        console.log(data);
        
        xhr.open("POST", "/get_info");
        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    }
    // Chrome
    else{
        var data = new FormData();
        data.append('monitoring', user_id);
        data.append('index', index);
        data.append('id', id);
    
        xhr.open("POST", "/get_info");
    }
    
    xhr.send(data);
});