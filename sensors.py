#!/usr/bin/python3
import time
import sensor
import smbus
import errno
import os
import subprocess
import re
import threading
import json
import traceback
import sys
# import requests
# from urllib.parse import urlencode
# TODO fff
# startStream check if run
# import numpy as np
#UDP server 
import socket
# sock.listen(max_connections)
class ServerUDP(threading.Thread):
    def __init__(self, bus=0, mux=0x70, channels=[], server=('192.168.1.100', 9091), client=('192.168.1.108', 44612)):
        self.sock = None
        self.channels = channels
        self.bus = bus
        self.serverIP = server
        self.mux_address = mux
        self.ch_codes = [0b00000001, 0b00000010, 0b00000100, 0b00001000, 0b00010000, 0b00100000, 0b01000000, 0b10000000]
        self.client = client
        print("client", client)
        self.isStreamRunning = False
        self.tik = 0.2
        self.data = {'id':0, 'dt':0, 's':[]}
        self.streamRunningTimer = time.time()
        self._stopevent = threading.Event()
        threading.Thread.__init__(self)

    def exit(self):
        self._stopevent.set()
        time.sleep(0.2)
        if(self.sock != None): self.sock.close()
        self.isStreamRunning = False

    def switchChannel(self, channel):
        cnt = 4 # number of attempts
        while(cnt):
            try:
                self.bus.write_byte_data(self.mux_address, 0x04, self.ch_codes[channel])
                return True
            except: 
                cnt -= 1
                time.sleep(self.tik)
        return False

    def run(self):
        cnt_frame = 0; cnt_skip = 0
        is_UDP_Ready = False
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # print("2 clients = ", self.client)
            self.sock.bind(self.serverIP)
            is_UDP_Ready = True
        except Exception:
            traceback.print_exc() 
            print("Error init stream server.")
        if is_UDP_Ready:
            self.isStreamRunning = True
            # print("start stream data")
            print("start UDP server on :", self.serverIP)
            for ch in self.channels:
                if self.switchChannel(ch[0]):
                    for sen in ch[1]:
                        sen.lastUpdate = time.perf_counter()
                        sen.updateQ()
            t1 = time.time()
            while (not self._stopevent.isSet()):
                if(cnt_frame < 10000): cnt_frame += 1
                else: cnt_frame = 0
                print("update", not self._stopevent.isSet(), cnt_frame, time.time() - self.streamRunningTimer )
                data = []
                try:
                    for ch in self.channels:
                        if(self.switchChannel(ch[0])):
                            for sen in ch[1]:
                                if(sen.updateQ()): data.append({"id":sen.name,"q":sen.q})
                                else: print("mux switch error")
                    t0 = t1
                    t1 = time.time()
                    delta = round((t1-t0), 5)
                    self.data = {'id':cnt_frame, 'dt':delta, 's':data}
                    ready_data = json.dumps(self.data).encode()
                    print("data", self.data, self.client)
                    # for client in self.clients.values():
                    #     print("udp", client[0], ready_data)
                    self.sock.sendto(ready_data, self.client)
                    # response = self.sock.recv(128)
                    # print(response)
                except Exception:
                    traceback.print_exc()
                    cnt_skip += 1
                    print("skip data send"+str(cnt_skip)+" for frame "+str(cnt_frame))
                    # pass
                time.sleep(self.tik)
            self.isStreamRunning = False
        else: print("can not start UDP")


class Sensors(threading.Thread):
    def __init__(self, server_ip='192.168.1.100', server_port=9090):
        start = time.time()
        # MESSAGE = str.encode("Hello, World!")
        self.bufferSize  = 1024
        self.bufferSize2  = 20
        self.server_ip = server_ip
        self.server_port = server_port
        self.max_connections = 5
        self.channels = []
        self.tik = 0.01
        # self.clients = {'1':[('192.168.1.105', 44612), 1572921753.9270492]}
        self.clients = {}
        self.CalCounter = 500
        self.cnt_skip = 0
        self.mux_address = 0x70 # multiplexer TCA9548A
        self.ch_codes = [0b00000001, 0b00000010, 0b00000100, 0b00001000, 0b00010000, 0b00100000, 0b01000000, 0b10000000]
        self.I2C_bus_number = 1
        self.bus = smbus.SMBus(self.I2C_bus_number)
        self.config = {"configs":[]}
        self.startTime = time.time()
        self.devices = [0x68, 0x69]
        self.devices_not_ready = []
        self.data_server = None
        self.isCalibRunning = False
        self.isStreamRunning = False
        self.streamRunningTimer = 0
        self.isRun = False
        # print(self.channels)
        # self.sendMessage({"source":"sensors","msg":"initStart","dt":0,"data":["0"]})
        self._stopevent = threading.Event()
        print("start to init sensors")
        # time.sleep(1)
        threading.Thread.__init__(self)

    def exit(self):
        try:
            start = time.time()
            self.stopStream()
            # self.sendMessage({"source":"sensors", "msg":"Exit", "dt":time.time()-start, "data":["suitExit"]})
        except: print("Error exit sensors.")

    def stopStream(self, ip=""):
        print("try stop data_server ")
        start = time.time()
        if(self.data_server != None):
            self.data_server .exit()
            self.data_server = None
            # self.is_UDP_Ready = False
        self.isStreamRunning = False
        self.clients = {}
        print("data_server is stoped")
        # self.sendMessage({"source":"sensors","msg":"Stop","dt":time.time()-start,"data":["streamDataStoped"]})
        return ["stream", "stop"]

    def isRunning(self):
        return not self._stopevent.isSet()

    def startStream(self, client=('192.168.1.108', 44612)): #
        answer = [""]
        # self.clients.update(client)
        # print(clients)
        if(len(self.channels)):
            print("sream and calib are running", self.isStreamRunning, self.isCalibRunning)
            if(not self.isStreamRunning and not self.isCalibRunning):
                self.data_server = ServerUDP(bus=self.bus, mux=self.mux_address, channels=self.channels, server=(self.server_ip, self.server_port+1), client=client)
                self.data_server.isDaemon = True
                self.data_server.start()
                time.sleep(0.5)
                self.isStreamRunning = self.data_server.isStreamRunning
                print("self.isStreamRunning=", self.isStreamRunning)
                answer = ["started", str(self.isStreamRunning)]
                # else: print("ckibration or sream is running")
            else: answer = ["started", "alredy"]
        else: answer = ["started", "0_sensors"]
        return answer

    def deleteFromCahnnels(self, sen, desc):
        # print("start delete device")
        self.devices_not_ready.append([sen.name, desc, sen]) # add to list with not ready sensors
        for ch in self.channels: # find device name in all exist and remove it
            for dev in ch[1]:
                if(sen.name == dev.name):
                    self.channels.remove(dev)
                    if(len(ch) == 0): self.channels.remove(ch)
                    if(len(self.channels) == 0): return False
        return True

    def switchChannel(self, channel):
        # if(not self.isRunning()):
        cnt = 4 # number of attempts
        while(cnt):	
            try:
                self.bus.write_byte_data(self.mux_address, 0x04, self.ch_codes[channel])
                return True
            except: 
                cnt -= 1
                time.sleep(self.tik)
        return False
        # print("Is running stream data.")
        # return False
        
    def calibrate(self, CalCounter=100, errCounter=10, maxTime=10, calibName='gyro'):
        if(not self.isStreamRunning and not self.isCalibRunning):
            self.isCalibRunning = True
            start = time.time()
            print("Start calibrate "+calibName+". Max time for it (s):", maxTime, " Sensors:", self.getReadySensors())
            tEnd = time.time()+maxTime; isNotReady = True; curSensors = []
            for ch_index in range(len(self.channels)): # fill calibration sensors list
                curSensors.append([self.channels[ch_index][0], []])
                for dev_index in range(len(self.channels[ch_index][1])):
                    curSensors[ch_index][1].append([self.channels[ch_index][1][dev_index], 0, 0]) # create counters
                    sen = self.channels[ch_index][1][dev_index] # init start values
                    if(calibName == 'gyro'): sen.gBias = [0, 0, 0]
                    elif(calibName == 'accel'): sen.aBias = [0, 0, 0]
                    elif(calibName == 'mag'):
                        sen.mBias = [0, 0, 0]; sen.mScale = [0, 0, 0] 
                        sen.magMax = [-32767, -32767, -32767]; sen.magMin = [32767, 32767, 32767]
            # print("result ",self.channels,curSensors)
            while(not self._stopevent.isSet() and isNotReady):
                if(time.time() < tEnd): # check if it is not too long procees
                    for ch in curSensors:
                        if(self.switchChannel(ch[0])):
                            for dev in ch[1]:
                                dev[1] += 1
                                # print(dev[0].name)
                                if(dev[1] < CalCounter):
                                    if(dev[0].update_raw(calibName)):
                                        if(calibName == 'gyro'):
                                            for i in range(3):	dev[0].gBias[i] += dev[0].g[i]
                                        elif(calibName == 'accel'):
                                            for i in range(3):	dev[0].aBias[i] += dev[0].a[i]
                                        elif(calibName == 'mag'):
                                            for j in range(3):
                                                if(dev[0].m[j] > dev[0].magMax[j]): dev[0].magMax[j] = dev[0].m[j]
                                                if(dev[0].m[j] < dev[0].magMin[j]): dev[0].magMin[j] = dev[0].m[j]
                                        else: pass
                                    else: 
                                        dev[2]+=1
                                        if(dev[2]>errCounter): # finish update because it has to many errors
                                            if(calibName == 'gyro'): dev[0].gBias = [0, 0, 0] # remove temp data
                                            elif(calibName == 'accel'): dev[0].aBias = [0, 0, 0]
                                            elif(calibName == 'mag'): dev[0].mBias = [0, 0, 0]
                                            else: print("Error clear data")
                                            if(self.deleteFromCahnnels(dev[0], calibName)): # remove from ready sensor because not pass calibration
                                                ch[1].remove(dev) # remove from list for calibration
                                                if(len(ch[1]) == 0): curSensors.remove(ch)
                                                if(len(curSensors) == 0): isNotReady = False
                                            else: isNotReady = False
                                else: # # finish update because it's ready
                                    ch[1].remove(dev)
                                    if(len(ch[1]) == 0): curSensors.remove(ch)
                                    if(len(curSensors) == 0): isNotReady = False
                        else: # ("Can't access to chanell: ",ch[1])
                            curSensors.remove(ch)
                            if(len(curSensors) == 0): isNotReady = False
                else: 	# ("Aborted because too long process")
                    isNotReady = False
                    time.sleep(0.3)
                    for ch in curSensors: # check if exist not checked sensors and delete from ready sensors list
                        for dev in ch[1]: self.deleteFromCahnnels(dev[0], calibName+"_time")
                    curSensors = []
                time.sleep(self.tik)
            # print("not ready devices: ",self.devices_not_ready)
            # print("start calculate biases for ready devices: ",self.channels)
            if(True):
                for ch in self.channels:
                    for sen in ch[1]:
                        print(sen)
                        if(calibName == 'gyro'):
                            for i in range(3): sen.gBias[i] /= CalCounter
                        elif(calibName == 'mag'):
                            mChord = [0, 0, 0]; avgChord = 0
                            for i in range(3):
                                sen.mBias[i] = ((sen.magMax[i] + sen.magMin[i]) / 2) * sen.mres * sen.mCoef[i]
                                mChord[i] = (sen.magMax[i] - sen.magMin[i]) / 2
                                avgChord += mChord[i]
                            avgChord /= 3
                            sen.mScale = [avgChord/mChord[0], avgChord/mChord[1], avgChord/mChord[2]]
                        elif(calibName == 'accel'):
                            for i in range(3): sen.aBias[i] /= CalCounter
                        else: pass
                        print("Finish calibrate sensor (a/g/m/sc): ", sen.name, sen.aBias, sen.gBias, sen.mBias, sen.mScale)
                # !!!!!!!!send calibration result to App
                dt = time.time()-start
                print(self.getReadySensors())
                self.isCalibRunning = False
                # self.sendMessage({"source":"sensors", "msg":calibName, "dt":dt, "data":self.getReadySensors()})
                return self.getReadySensors()
            self.isCalibRunning = False
            return {}

    def getReadySensors(self):
        names = []
        # print(self.channels)
        for ch in self.channels: # find device name in all exist and add to list
            for dev in ch[1]: names.append(dev.name)
        return names

    def getSensorsTemps(self):
        start = time.time(); data = []
        for ch in self.channels:
            if self.switchChannel(ch[0]):
                for sen in ch[1]: data.append(sen.name+"="+str(sen.updateTemp()))
        return data

    def run(self):
        start = time.time()
        for ch in range(8):
            if self.switchChannel(ch):
                curDevices = []
                for dev in range(len(self.devices)):
                    sen = sensor.MPU9250(self.bus, ch=ch, dev=dev)
                    try:
                        if sen.InitIMU():
                            if sen.InitMag():
                                res = sen.update_raw("gyro")
                                print(res, 3)
                                sen.updateTemp()
                                curDevices.append(sen)
                                # print('Line {0} sensor {1} cur Temp={2}'.format(ch,dev+1,sen.t))
                    except:
                        # print("skip sensor "+str(ch)+" "+str(dev))
                        pass
                if len(curDevices): self.channels.append([ch, curDevices])
            else: print("skip mux channel ", ch)
        print("InitSensors", self.getReadySensors())
        time.sleep(2)
        self.isRun = True
        time.sleep(3)
        print({"source":"sensors", "msg":"InitSensors", "dt":time.time() - start, "data":self.getReadySensors()})

if __name__ == '__main__':
    print("start")
    sensors = Sensors()
    # sensors.isDaemon = True
    sensors.start()
    print("0 start calibrate sensors 5 sec")
    # sensors.startStream('127.0.0.1',9898)
    # sensors.calibrate(CalCounter=500, errCounter=10, maxTime=30, calibName='accel')
    time.sleep(1)
    # sensors.calibrate(CalCounter=100,errCounter=10,maxTime=5,calibName='gyro')
    # sensors.calibrate(100, 10, 30, 'gyro')
    # time.sleep(5)
    print("1 start stream", sensors.isRunning())
    # client = ('192.168.1.108', 44612)
    # print("client ", client)
    sensors.startStream()
    # counter = 2000
    # time.sleep(3)
    # print("2 stop stream", sensors.isRunning())
    # sensors.stopStream()
    # time.sleep(1)
    # print("3 start stream", sensors.isRunning())
    # sensors.startStream()
    # # counter = 2000
    # time.sleep(3)
    # sensors.exit()
    # print("4 stop stream", sensors.isRunning())
    try:
        while True: time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sensors.stopStream()
        time.sleep(1)
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
