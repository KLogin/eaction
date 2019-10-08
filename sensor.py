import time
import mpu9250
import smbus
import errno
import os
import subprocess
import re
import threading

class Sensor(threading.Thread):
	def __init__(self):
		self.sensors = []
		self.mux_address = 0x70
		self.list_ch = [0b00000001 , 0b00000010, 0b00000100, 0b00001000, 0b00010000, 0b00100000, 0b01000000, 0b10000000]
		self.I2C_bus_number = 1
		self.bus = smbus.SMBus(self.I2C_bus_number)
		self.data = ["77"]
		self.startTime = time.time()
		self.devices = [0x68,0x69]
		self.counter = 0
		for ch in range(len(self.list_ch)):
			res = []
			self.bus.write_byte_data(self.mux_address,0x04,self.list_ch[ch])
			#print("test ch "+str(ch))
			for dev in range(len(self.devices)):
					#print(devices[dev])
					try:
						sensor = mpu9250.MPU9250(self.devices[dev],'None')
						time.sleep(0.1)
						s=sensor.readRow()
						# print(s)
						res.append(sensor)
						print('Initialized on line {0} sensor {1}'.format(ch,dev+1))
					except Exception as e:
						#print(e)
						pass
			self.sensors.append(res)
		print(self.sensors)
		self._stopevent = threading.Event()
		threading.Thread.__init__(self)

	def exit(self):
		self._stopevent.set()
	
	def run(self):
		print("start sensor")
		while not self._stopevent.isSet():
			# start = time.time()
			data = []
			for ch in range(len(self.sensors)):
				#print(len(sensors[ch]))
				if(len(self.sensors[ch])):
					res = []
					self.bus.write_byte_data(self.mux_address,0x04,self.list_ch[ch])
					for sensor in self.sensors[ch]:
						res.append(sensor.readRow())
						data.append(res)
			self.data=[self.counter, time.time(),data]
			self.counter += 1
			# print(data)
			# print(time.time()-start)

# sen = Sensor()
#scanSystem()
# initSensors()
# readData()

#output 
# [[[20, 0, 205, 254, 220, 154, 1, 96, 0, 50, 1, 207, 255, 228]], 
# [[7, 154, 208, 154, 44, 141, 2, 233, 1, 88, 0, 175, 255, 243]], 
# [[6, 62, 43, 223, 205, 125, 1, 66, 2, 242, 3, 70, 0, 179]], 
# [[217, 53, 239, 63, 205, 191, 1, 95, 255, 214, 3, 132, 255, 218]], 
# [[255, 35, 216, 225, 51, 69, 2, 136, 0, 252, 2, 246, 0, 152]], 
# [[2, 242, 254, 60, 190, 81, 2, 152, 1, 202, 3, 183, 1, 41]], 
# [[253, 5, 20, 129, 63, 34, 3, 61, 0, 159, 1, 47, 0, 102], [232, 22, 252, 243, 53, 251, 2, 52, 0, 43, 3, 220, 0, 229]], 
# [[249, 107, 5, 55, 194, 96, 1, 129, 255, 232, 2, 244, 0, 25], [3, 18, 194, 130, 235, 249, 4, 249, 0, 14, 2, 159, 255, 152]]]
