# pip install -r requirements.txt
import signal
import threading
import time
#import json
import os
import sys
from subprocess import check_output
import time
import random
from datetime import date
# import cv2
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
import sensor as Sensor

# import pickle

# json format Ctrl+Shift+I 
print(socket.gethostbyname(socket.gethostname()))
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
print(s.getsockname()[0])
define("host", default=s.getsockname()[0], help="app host", type=str)
define("port", default=9090, help="app port", type=int)
s.close()
serverUrl = "http://"+options.host+":"+str(options.port)

root_dir = os.path.dirname(__file__)
data_dir = os.path.join(root_dir,"data")
sensors = None

class InfoHandler(tornado.web.RequestHandler):
  def get(self):
      self.write("eaServer")

class IdHandler(tornado.web.RequestHandler):
  def get(self):
      self.write("1")

class MainHandler(tornado.web.RequestHandler):
  def get(self):
    self.render(os.path.join("static","index.html"), host=options.host, port=options.port)

class WsHandler(tornado.websocket.WebSocketHandler):
  def open(self):
    logger.info("WS connected")
    self.write_message(json.dumps(['ok']))

  def on_message(self, message):
    self.write_message(json.dumps(sensors.data))

  def on_close(self):
    logger.info('ws connection closed...')

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
            try:
                logger.debug("start exit")
                if(sensors):
                    sensors.exit()
                    # time.sleep(2)
                    sensors.join()
                tornado.ioloop.IOLoop.instance().stop()
                logger.debug("exit ok")
                #print(time.strftime('%Y-%m-%d %H:%M:%S '))
            except Exception as e: 
                print(e)
                # logger.error("Stop function has some troubles")

application = MyApplication([
        (r'/', MainHandler),
        (r'/info', InfoHandler),
        (r'/id', IdHandler),
        # (r"/cameraReady", CameraReadyHandler),  ?P<param1>[^\/]+)/?(?P<param2>[^\/]+)?/?(?P<param3>[^\/]+)?" r"/users/key=(?P<key>\w+)"
        (r"/data", WsHandler),
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
    signal.signal(signal.SIGINT, application.signal_handler)
    try:
        application.listen(options.port)
        logger.info("start websocketServer on port: "+str(options.port))
        tornado.ioloop.PeriodicCallback(application.try_exit, 1000).start()
        logger.info("Press Ctrl-C for stop the server.")
        tornado.autoreload.watch(os.path.join(root_dir,"eaServer.py"))
        tornado.autoreload.watch(os.path.join(root_dir,"index.html"))
        for dir, _, files in os.walk('static/js'):
            for f in files:                
                if not f.startswith('.'):
                    #logger.debug(dir + '/' +f)
                    tornado.autoreload.watch(dir + '/' + f)
        # background update every x seconds
        sensors = Sensor.Sensor()
        sensors.start()
        tornado.ioloop.IOLoop.instance().start()
    except Exception as e:
        logger.error(e)
