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
import tornado.gen
from datetime import date
import cv2
import json

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.template
import tornado.options
import tornado.autoreload
from loguru import logger
from tornado.options import options, define
from tornado.gen import coroutine

# import pickle

# json format Ctrl+Shift+I 
define("host", default="localhost", help="app host", type=str)
define("port", default=9090, help="app port", type=int)

serverUrl = "http://"+options.host+":"+str(options.port)

root_dir = os.path.dirname(__file__)
data_dir = os.path.join(root_dir,"data")
sensor = None
# cur_data = [[3,3,3,3],[2,4,5,6]]


class MainHandler(tornado.web.RequestHandler):
  def get(self):
    #loader = tornado.template.Loader(".")
    #self.write(loader.load("test.html").generate())
    self.render(os.path.join("static","index.html"), host=options.host, port=options.port)

class WsHandler(tornado.websocket.WebSocketHandler):
  def open(self):
    logger.info("connected")

  def on_message(self, message):
    self.write_message(json.dumps(sensor.data))

  def on_close(self):
    logger.info('ws connection closed...')

class NotFoundHandler(tornado.web.RequestHandler):
	def get(self):
		logger.debug("Not founded page "+self.request.body)
		self.write('{"error":"404"}')

executor = tornado.concurrent.futures.ThreadPoolExecutor()
class AsyncHandler(tornado.web.RequestHandler):
    @coroutine
    def get(self):
        ans = yield executor.submit(self.do_slow)
        self.write(ans)

    def do_slow(self):
        time.sleep(2)
        a = 'okww2'
        return a

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
                sensor.exit()
                # time.sleep(2)
                sensor.join()
                tornado.ioloop.IOLoop.instance().stop()
                logger.debug("exit ok")
                #print(time.strftime('%Y-%m-%d %H:%M:%S '))
            except Exception as e: 
                print(e)
                logger.error("Stop function has some troubles")

application = MyApplication([
        (r'/', MainHandler),
        (r'/a', AsyncHandler),
        # (r"/cameraReady", CameraReadyHandler),  ?P<param1>[^\/]+)/?(?P<param2>[^\/]+)?/?(?P<param3>[^\/]+)?" r"/users/key=(?P<key>\w+)"
        (r"/data", WsHandler),
        (r"/static/(.*)",tornado.web.StaticFileHandler, {"path": "static"},),
        # (r"/images/(.*)",tornado.web.StaticFileHandler, {"path": "static/images"},),
        # (r"/js/(.*)",tornado.web.StaticFileHandler, {"path": "static/js"},)
        ],
	    debug=True,
	    static_hash_cache=False
    )

def periodic_update():
    print('tik')

class Sensor(threading.Thread):
    def __init__(self, id):
        self.id = id
        self.data=[[0,0],[0,2,2,2],[5,5,5,5]]
        self._stopevent = threading.Event()
        self.time_start  = time.time()
        threading.Thread.__init__(self)
    def run(self):
        print('start')
        while not self._stopevent.isSet():
            start = time.time()
            time.sleep(.5)
            self.data[0][0] += 1
            self.data[0][1] = time.time()-start
            # print(self.data[0])
    def exit(self):
        # self.log.info("pause camera")
        self._stopevent.set()

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
        tornado.ioloop.PeriodicCallback(application.try_exit, 100).start()
        logger.info("Press Ctrl-C for stop the server.")
        tornado.autoreload.watch(os.path.join(root_dir,"eaServer.py"))
        tornado.autoreload.watch(os.path.join(root_dir,"index.html"))
        for dir, _, files in os.walk('static/js'):
            for f in files:                
                if not f.startswith('.'):
                    #logger.debug(dir + '/' +f)
                    tornado.autoreload.watch(dir + '/' + f)
        # background update every x seconds
        # task = tornado.ioloop.PeriodicCallback(periodic_update, 1000)
        # task.start()
        sensor = Sensor("01")
        sensor.start()
        tornado.ioloop.IOLoop.instance().start()
    except Exception as e:
        logger.error(e)
