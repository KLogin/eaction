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
import sensors


# json format Ctrl+Shift+I
# print(socket.gethostbyname(socket.gethostname()))
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
HostName = "192.168.1.112"
HostPort = 9090
try:
    s.connect(("8.8.8.8", 80))
    #print(s.getsockname()[0])
    HostName = s.getsockname()[0]
except: pass
define("host", default=HostName, help="app host", type=str)
define("port", default=HostPort, help="app port", type=int)
s.close()
serverUrl = "http://"+options.host+":"+str(options.port)
print("Server url: ", serverUrl)
root_dir = os.path.dirname(__file__)
data_dir = os.path.join(root_dir, "data")
suit = None
clients = []
clientsCam = []

class InfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("eaServer")

class IdHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("1")

class ConfigHandler(tornado.web.RequestHandler):
    def get(self):
        if(suit):
            print(json.dumps(suit.config))
            self.write(json.dumps(suit.config))
        else: self.write(0)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render(os.path.join("static", "index.html"), host=options.host, port=options.port)

class WsCommandHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        logger.info("WS command connected")
        try:
            self.write_message(json.dumps({"source":"server", "msg":"startWS", "dt":0, "data":["ok"]}))
            clients.append(self)
        except:
            print("can not connect client")
            pass

    async def getReadySensors(self):
        return suit.getReadySensors()

    async def startStream(self, action, ip_tuple):
        # sd = suit.calibrate(CalCounter, errCounter, maxTime, calibName)
        print("start", action, ip_tuple)
        ans = []
        if(action == 'stopStream'): ans = suit.stopStream(ip_tuple)
        elif(action == 'startStream'): ans = suit.startStream(ip_tuple)
        else: ans = ["streamCntl", "unknow command"]
        return ans

    async def calibrate(self, CalCounter, errCounter, maxTime, calibName):
        ans = suit.calibrate(CalCounter, errCounter, maxTime, calibName)
        # print("end calib", sd)
        return ans

    async def on_message(self, message):
        start = time.time()
        if(1):
          print("ws message: ", message)
          if(message == b'0'): pass
          else:
            data = json.loads(message)
            print("ws json: ", data)
            if(suit):
              if(data['cmd'] == 'startCalib'):
                # print("calib 1")
                # print(data["data"]["loopsCounter"])
                str_ans = await self.calibrate(data["data"]["loopsCounter"], data["data"]["errCounter"], data["data"]["timeForAction"], data["data"]["calibName"]) # 'gyro'
                str1 = json.dumps({"source":"server", "msg":"startCalib", "dt":time.time()-start, "data":str_ans})
                self.write_message(str1)
                # print("calib 3 ", "ok")
              elif(data['cmd'] == 'streamCntl'):
                  ip_tuple = (self.request.remote_ip, data['data']['port'])
                  answer = await self.startStream(data['action'], ip_tuple)
                  self.write_message(json.dumps({"source":"server", "msg":"stopSensors", "dt":time.time() - start, "data":answer}))
              elif(data['cmd'] == 'status'):
                if(data['action'] == 'takeReadySensors'):
                  dataArr = await self.getReadySensors()
                  dt = time.time() - start
                  srtAns = {"source":"sensors", "msg":"readySensors", "dt":dt, "data":dataArr}
                  self.write_message(json.dumps(srtAns))
                elif(data['action'] == 'takeConfig'):
                  self.write_message(json.dumps({"source":"sensors", "msg":"readySensors", "dt":time.time()-start, "data":suit.config}))
              else: self.write_message(json.dumps({"source":"server", "msg":"errorNotFoundCmd", "dt":time.time()-start, "data":[message]}))
            else: self.write_message(json.dumps({"source":"server", "msg":"errorNotReadySuit", "dt":time.time()-start, "data":[""]}))
        # except:
        #   print("error ws command", message)
        #   self.write_message(json.dumps({"source":"server", "msg":"errorExceeption", "dt":time.time()-start, "data":[message]}))

    def on_close(self):
        # try: self.write_message(json.dumps({"source":"server", "msg":"stoptWS", "dt":0, "data":["ok"]}))
        clients.remove(self)
        logger.info('ws command connection closed...')

class MsgHandler(tornado.web.RequestHandler):
    print("!!start send from sensor")
    # def get(self):

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
        logger.debug("\nexiting 2..."+str(self.is_closing) )
        if self.is_closing:
            print("closing 1")
            try:
                logger.debug("start exit")
                if(suit != None):
                    logger.debug("stopping suit")
                    suit.exit()
                    # time.sleep(1)
                    # suit.join()
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
        # (r'/msg', MsgHandler),
        (r'/id', IdHandler),
        (r'/config', ConfigHandler),
        # (r"/cameraReady", CameraReadyHandler),  ?P<param1>[^\/]+)/?(?P<param2>[^\/]+)?/?(?P<param3>[^\/]+)?" r"/users/key=(?P<key>\w+)"
        # (r"/data", WsDataHandler),
        (r"/cmd", WsCommandHandler),
        (r"/static/(.*)",tornado.web.StaticFileHandler, {"path": "static"},),
        # (r"/images/(.*)",tornado.web.StaticFileHandler, {"path": "static/images"},),
        # (r"/js/(.*)",tornado.web.StaticFileHandler, {"path": "static/js"},)
        ],
	  debug=False,
	  static_hash_cache=False
)

if __name__ == "__main__":
    listDirs = ['static/logs']
    for directory in listDirs:
        if not os.path.exists(directory):
            print("create new dir " + directory)
            os.makedirs(directory)
    tornado.options.parse_command_line()
    # signal.signal(signal.SIGINT, application.signal_handler)
    try:
        suit = sensors.Sensors(options.host, options.port)
        suit.isDaemon = True
        suit.start()
        application.listen(options.port)
        logger.info("start websocketServer on port: " + str(options.port))
        # tornado.ioloop.PeriodicCallback(application.try_exit, 1000).start()
        logger.info("Press Ctrl-C for stop the server.")
        tornado.autoreload.watch(os.path.join(root_dir, "eaServer.py"))
        tornado.autoreload.watch(os.path.join(root_dir, "index.html"))
        for dir, _, files in os.walk('static/js'):
            for f in files:                
                if not f.startswith('.'):
                    #logger.debug(dir + '/' +f)
                    tornado.autoreload.watch(dir + '/' + f)
        logger.debug("start Sensors thread")
        tornado.ioloop.IOLoop.instance().start()
        logger.debug("start main thread")
    except Exception as e:
        # logger.error(e)
        logger.warning("Stop server")
        tornado.ioloop.IOLoop.instance().stop()
