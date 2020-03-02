#!/usr/bin/python3
# pip3 install -r requirements.txt
import signal
import threading
import os
import sys
from subprocess import check_output
import time
import random
from datetime import date
import json
import socket

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.template
import tornado.options
import tornado.autoreload
import tornado.gen
from loguru import logger
from tornado.options import options, define
from tornado.gen import coroutine

from PIL import Image
from io import BytesIO

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
HostName = "192.168.1.108"
HostPort = 9090
save_img = True
try:
    s.connect(("8.8.8.8", 80))
    #print(s.getsockname()[0])
    HostName = s.getsockname()[0]
except:
    print("Error take server ip") 
    pass
define("host", default=HostName, help="app host", type=str)
define("port", default=HostPort, help="app port", type=int)
s.close()
serverUrl = "http://"+options.host+":"+str(options.port)
print("Server url: ", serverUrl)
root_dir = os.path.dirname(__file__)
# os.path.abspath(
data_dir = os.path.join(root_dir, "img")
suit = None
# clients = []
clientsCam = []
clientsCamName = {}
control_conn = []

class InfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("camera control Server")

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render(os.path.join("static", "cameras.html"), host=options.host, port=options.port)

class WsCamHandler(tornado.websocket.WebSocketHandler):
    # global control_conn
    def open(self):
        logger.info("WS command connected")
        try:
            # self.write_message("test")
            print("new cam")
            if not self in clientsCam:
                clientsCam.append(self)
                print("new cam index: ", len(clientsCam))
            else:
                print("!!!already exist")
            
        except:
            print("can not connect client")
            pass

    async def sendToAll(self, cmd):
        ans = False
        try:
            for client in clientsCam:
                client.write_message(cmd)
                print("send:"+cmd)
            ans = True
        except:
            ans = False
        return ans

    async def on_message(self, message):
        ans = ""
        start = time.time()
        # start = time.time()   
        # String strBase64 = bytes.base64();
        # byte[] decodedString = Base64.decode(
        # strBase64, Base64.DEFAULT);
        # print("ws message: ", type(message))
        if isinstance(message, bytes):
            # print("bytes recieved")
            # print("cam_id counter: ", len(clientsCam))
            cam_id = clientsCam.index(self)
            print("recieved data from: ", cam_id)
            if(save_img):
                stream = BytesIO(message)
                image = Image.open(stream).convert("RGB")
                stream.close()
                # image.show()
                image.save(os.path.join(data_dir, str(time.time())+"_cam_"+str(cam_id)+".jpg"))
                # print("control_conn=", time.time()-start)
            if(len(control_conn)):
                d = bytearray(message)
                id = (cam_id).to_bytes(1, byteorder='little')
                d.extend(id)
                control_conn[0].write_message(bytes(d), binary=True)
            else:
                print("No web clients")
        else:
            if isinstance(message, str):
                if(message.startswith("test")): pass
                elif(message.startswith("__name=")):                    
                    cam_id = clientsCam.index(self)
                    # print(cam_id)
                    new_name = message[7:]
                    delList=[]
                    for i, name in enumerate(clientsCamName):
                        if name == new_name:
                            if i != cam_id: delList.append(i)
                    for x in delList:  del clientsCamName[x]
                    clientsCamName[cam_id] = new_name
                    # print("msg: ", clientsCamName[cam_id])
                else: print("unknow command: "+message)
        # if(len(clientsCam)):
        #     ans = await self.sendToAll(message)
        #     print("ans:", ans)
        # else: 
        #     print("No cams")
        #     self.write_message("error! No camers!!")

    def on_close(self):
        # try: self.write_message(json.dumps({"source":"server", "msg":"stoptWS", "dt":0, "data":["ok"]}))
        # print("old cams number", len(clientsCam))
        print("close", self.close_code, self.close_reason, self._reason)
        try:
            cam_id = clientsCam.index(self)
            for x in range(cam_id, len(clientsCamName)):
                if ((x+1) in clientsCamName):
                    clientsCamName[x] = clientsCamName[x+1]
            del clientsCamName[len(clientsCamName)-1]
            # print("end", clientsCamName)
        except Exception as e:
            print(e) 
            # print("wrong cam id")        
        clientsCam.remove(self)
        print("new cams number", len(clientsCam))
        logger.info('ws command connection closed...')

class WsComHandler(tornado.websocket.WebSocketHandler):
    # global control_conn
    def open(self):
        logger.info("WS command connected")
        try:
            self.write_message("{\"cmd\":\"test\",\"data\":"+str(len(clientsCam))+"}")
            control_conn.append(self)
            print("control connected")
        except:
            print("can not connect client")
            pass

    async def sendToAll(self, cmd):
        ans = False
        try:
            for client in clientsCam:
                client.write_message(cmd)
                print("send:"+cmd)
            ans = True
        except:
            ans = False
        return ans

    async def on_message(self, message):
        # start = time.time()
        # print("ws message: ", message)
        # if(message)
        # 
        if(message=='test'):
            # print(clientsCamName)
            new_msg = {
                "cmd": "test",
                "data": len(clientsCam),
                "names": clientsCamName
            }
            self.write_message(json.dumps(new_msg))
        else:
            if( len(clientsCam) ):
                ans = await self.sendToAll(message)
                # print(ans)
            else: 
                print("Error")
                self.write_message("{\"cmd\":\"error\",\"data\":\"No cams!!\"}")

    def on_close(self):
        # try: self.write_message(json.dumps({"source":"server", "msg":"stoptWS", "dt":0, "data":["ok"]}))
        # clientsCam.remove(self)
        
        control_conn.remove(self)
        logger.info('data command connection closed...')

class NotFoundHandler(tornado.web.RequestHandler):
    def get(self):
        logger.debug("Not founded page "+self.request.body)
        self.write('{"error":"404"}')

class MyApplication(tornado.web.Application):
    is_closing = False

    def signal_handler(self, signum, frame):
        logger.debug("\nexiting..."+str(self.is_closing) )
        self.is_closing = True

    def try_exit(self):
        # logger.debug("\nexiting 2..."+str(self.is_closing) )
        if self.is_closing:
            # print("closing 1")
            try:
                logger.debug("start exit")
                # if(suit != None):
                #     logger.debug("stopping suit")
                #     suit.exit()
                #     # time.sleep(1)
                #     # suit.join()
                tornado.ioloop.IOLoop.instance().stop()
                logger.debug("exit ok")
                #print(time.strftime('%Y-%m-%d %H:%M:%S '))
            except Exception as e:
                print(e)
                # logger.error("Stop function has some troubles")

application = MyApplication([
        (r'/', MainHandler),
        (r'/info', InfoHandler),
        (r'/cam', WsCamHandler),
        (r'/com', WsComHandler),
        (r"/static/(.*)",tornado.web.StaticFileHandler, {"path": "static"},),
        # (r"/images/(.*)",tornado.web.StaticFileHandler, {"path": "static/images"},),
        # (r"/js/(.*)",tornado.web.StaticFileHandler, {"path": "static/js"},)
        ],
	  debug=True,
	  static_hash_cache=False
)

if __name__ == "__main__":
    # listDirs = ['static/logs']
    # for directory in listDirs:
    #     if not os.path.exists(directory):
    #         print("create new dir " + directory)
    directory = "".join((random.choice('1234567890asdfghjklqwertyuiopzxcvbnm') for i in range(10)))
    print("new directory: ",directory)
    data_dir = os.path.join("img",directory)
    os.makedirs(data_dir)
    tornado.options.parse_command_line()
    signal.signal(signal.SIGINT, application.signal_handler)
    try:
        # suit = sensors.Sensors(options.host, options.port)
        # suit.isDaemon = True
        # suit.start()
        application.listen(options.port)
        logger.info("start websocketServer on port: " + str(options.port))
        tornado.ioloop.PeriodicCallback(application.try_exit, 1000).start()
        logger.info("Press Ctrl-C for stop the server.")
        tornado.autoreload.watch("camServer.py")
        tornado.autoreload.watch("static/cameras.html")
        for dir, _, files in os.walk('static/js'):
            for f in files:                
                if not f.startswith('.'):
                    #logger.debug(dir + '/' +f)
                    tornado.autoreload.watch(dir + '/' + f)
        # logger.debug("start Sensors thread")
        tornado.ioloop.IOLoop.instance().start()
        logger.debug("start main thread")
    except Exception as e:
        # logger.error(e)
        logger.warning("Stop server")
        tornado.ioloop.IOLoop.instance().stop()
