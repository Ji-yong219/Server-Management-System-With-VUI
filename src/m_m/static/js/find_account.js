function display_chk(name_chk){
	
	if (name_chk==null){
		name_chk="no";
	}
		
	var yes = document.getElementById("display_id");
	var no = document.getElementById("input_name");
	if (name_chk=="yes"){
		yes.style.display  = '';
		no.style.display = 'none';
	}
	else {
		yes.style.display  = 'none';
		no.style.display = '';
	}
}
function check_name(){
	var chk_name = document.getElementById("name").value;
	if (chk_name==''){
		return false;
	}
	else{return  true;}
}
function check_id(id_result){
	if (id_result=='no'){
		document.getElementById("error").innerHTML="아이디가 존재하지 않습니다.";}
	else{
		document.getElementById("error").innerHTML="";}
}
function chk_pw(){
	var pw=document.getElementById("pw").value;
	var pwa=document.getElementById("pwa").value;

	if(pw.length<6){
		document.getElementById("error2").innerHTML='비밀번호를 최소 6자 이상 입력해주세요';
		return false;
	}
	else{
		if(pw==pwa){
			document.getElementById("error2").innerHTML='';
			return true;
		}
	
		else{
			document.getElementById("error2").innerHTML='비밀번호가 일치하지 않습니다';
			return false;
		}
	}
}
