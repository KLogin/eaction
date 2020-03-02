var hostCmd = null;
var socketCmd = null;
var camNames = null;
var start = new Date().getTime();
function serverCmd(cmd){
    console.log("Cmd:"+cmd);
    if(socketCmd){
        socketCmd.send(cmd); 
    }
}
var pingTimer = setInterval(mTimer, 1000);

function mTimer() {
    // console.log(socketCmd);
    if(!socketCmd){
        console.log("try connect to server.");
        connectToServer();
        console.log("Error connect to server.");
    }else{
        socketCmd.send("test");
    }
}

function connectToServer() {
    try{
        socketCmd = new WebSocket(hostCmd);
        if(socketCmd){
            socketCmd.onopen = function(){console.log("Server started"); 
            $('#server_online').html("Ok");
            $('#server_online').removeClass("badge badge-danger").addClass("badge badge-success");
            // $('#test').html("ddd");
            // $('#table_data tbody').append("<tr id='tr0'><td id='td_0_0'>ddd</td></tr>");
            //   socketCmd.send(0); 
            }

            socketCmd.onmessage = function(msg){
                // console.log("server says: "+msg.data);
                // console.log(typeof msg.data);
                if(msg.data instanceof Blob){
                    (msg.data).arrayBuffer().then(value =>{
                        // ,value.getBytes(value.length-1,value.length-1)
                        // console.log(value.byteLength);
                        let arr = new Uint8Array(value);
                        // console.log(arr[arr.length-1]);
                        $('#photo_'+arr[arr.length-1]).attr('src', URL.createObjectURL(msg.data));
                        let id = null;
                        console.log("time: ",1000/(new Date().getTime()-start));
                        start = new Date().getTime();
                    }
                    ).catch(error => {console.log(error);});
                    // var value = await (msg.data).arrayBuffer();
                    // console.log(value.length);
                }else{
                    let data =  JSON.parse(msg.data);
                    if(data["cmd"]){
                        switch(data["cmd"]) {
                            case "test":
                                // console.log("test is Ok.");
                                // $('#cams_online').html("3");
                                $('#cams_online').html(data["data"]);
                                if(data["data"]>0){
                                    $('#cams_online').removeClass("badge badge-danger").addClass("badge badge-success");
                                }else{
                                    $('#cams_online').removeClass("badge badge-success").addClass("badge badge-danger");
                                }
                                let counter = 0;
                                // console.log(camNames, JSON.stringify(data["names"]));
                                if (camNames !== JSON.stringify(data["names"])){
                                    console.log("cams are changed ", data["names"]);
                                    for (let key in data["names"]){
                                        console.log("key: "+key+"val: "+data["names"][key] +' #photo_label_'+key+" old:"+$('#photo_label_'+key).text);
                                        $('#photo_label_'+key).text(data["names"][key]);
                                        $('#photo_'+key).attr('src', "")
                                        counter++; 
                                    } 
                                    camNames =  JSON.stringify(data["names"]);
                                    while(counter<4){
                                        $('#photo_label_'+counter).text("");
                                        $('#photo_'+counter).attr('src', "")
                                        counter++;}

                                }
                                // code block
                                break;
                            case "new camera":
                                // code block
                                break;
                            case "new camera":
                                // code block
                                break;
                            case "error":
                                console.log("Error "+data["data"]);
                                // code block
                                break;
                            default:
                                // code block
                            }
                    }else{
                        console.log("Wrong command");
                    }
                }
            }

            socketCmd.onclose = function(){
                
                socketCmd = null;
                $('#cams_online').html(0);
                $('#server_online').html("No");
                $('#cams_online').removeClass("badge badge-success").addClass("badge badge-danger");
                $('#server_online').removeClass("badge badge-success").addClass("badge badge-danger");                console.log("server close connection!");
            }
            socketCmd.onerror=function(){
                socketCmd.close();
                socketCmd = null;
                $('#cams_online').html(0);
                $('#server_online').html("No");
                $('#cams_online').removeClass("badge badge-success").addClass("badge badge-danger");
                $('#server_online').removeClass("badge badge-success").addClass("badge badge-danger");
                console.log("Error");
            }
        }
    }catch(er){
        console.log("error open websocket.");
    }
}

$(document).ready(function(){
  hostCmd = 'ws://'+location.host+'/com';
    var updateTimers = false; // update or not timers data from camera
    var updateFrame = false; // update or not picture from camera
    var timeNow = 0; // value for fps calculation
    if (!("WebSocket" in window)) {alert("Your browser does not support web sockets");
    }else{
        // !!!!!!!!!!!!! main start script
        console.log((new Date).toLocaleTimeString()+' start main script');
        connectToServer();
    }
});


