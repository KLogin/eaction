var hostCmd = null;

// function setHost(host,port){ 
//   console.log("start set up server data: "+ host);
//   console.log(location.host);
//   // hostCmd = 'ws://'+host+':'+port+'/data'; 
//   hostCmd = 'ws://'+location.host+'/data'; 
// }

$(document).ready(function(){
  hostCmd = 'ws://'+location.host+'/data';
    var updateTimers = false; // update or not timers data from camera
    var updateFrame = false; // update or not picture from camera
    var timeNow = 0; // value for fps calculation
    // var isSpinOn = false;

    if (!("WebSocket" in window)) {alert("Your browser does not support web sockets");
    }else{
    // !!!!!!!!!!!!! main start script
    // console.log($('#isDetect')[0])
      console.log((new Date).toLocaleTimeString()+' start main script');
      socketCmd = new WebSocket(hostCmd);
        if(socketCmd){
          socketCmd.onopen = function(){console.log("Server started"); 
          // $('#test').html("ddd");
          // $('#table_data tbody').append("<tr id='tr0'><td id='td_0_0'>ddd</td></tr>");
          socketCmd.send(0); 
         }

          socketCmd.onmessage = function(msg){

                console.log((Date.now()-timeNow).toString()+"server says: "+msg.data);
                timeNow = Date.now()
                socketCmd.send(0);
                // data =  JSON.parse(msg.data)
                // console.log(data[0]);
                // for (let i in data) { 
                //   console.log(i);
                //   for (let j in data[i]) { 
                //   $('#'+i+'_'+j).html(data[i][j]); 
                // }
            }
          }

          socketCmd.onclose = function(){
            console.log("server close connection!");
        }
      }
    

});


