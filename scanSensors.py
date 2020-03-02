import time
import mpu9250_1
import smbus
import errno
import os
import subprocess
import re

mux_address = 0x70
list_ch = [0b00000001 , 0b00000010, 0b00000100, 0b00001000, 0b00010000, 0b00100000, 0b01000000, 0b10000000]
I2C_bus_number = 1
device_count = 0
sensor1 = 0
sensor2 = 0
active_channels = [0,3]
bus = smbus.SMBus(I2C_bus_number)
sensors = []
sensors2 = []

def initSensors():
    print("start init sensors")
    for ch in range(len(list_ch)):
        devices = [0x68,0x69]
        res = []
        bus.write_byte_data(mux_address,0x04,list_ch[ch])
        # print("test ch "+str(ch)+" "+str(list_ch[ch]))
        for dev in range(len(devices)):
                # print("init dev ",dev,devices[dev])
                try:
                     sensor = mpu9250_1.MPU9250(ch,dev)
                    #  sensor = mpu9250.MPU9250(ch,devices[dev],'test')
                    #  print("sensor",sensor)
                     time.sleep(0.1)
                     s =sensor.readRaw()
                    #  print(s)
                     res.append(sensor)
                     print('Initialized on line {0} sensor {1}'.format(ch,dev+1))
                except Exception as e: # time.sleep(0.1)
                    #  print(e)
                     pass
            #        #if e.errno != errno.EREMOTEIO:
            #        #    print("Error: {0} on address {1} {2}".format(e, ch,dev))
            #    except Exception as e: # exception if read_byte fails
            #        print("Error unk: {0} on address {1} {2}".format(e, ch,dev))
            #        pass
        sensors2.append(res)
        time.sleep(0.1)
        #except Exception as e: # exception if read_byte fails
        #    print("Error multiplexer: {0} on address {1}".format(e,mux_address))
    print(sensors2)
    #sensors.append(result)

def scanSystem():
    print("start system scan")
    result = []
    for ch in range(len(list_ch)):
#        print(list_ch[ch])
        try:
            bus.write_byte_data(mux_address,0x04,list_ch[ch])
            # print("test ch "+str(ch)+" "+str(list_ch[ch]))
            res = []
            p = subprocess.Popen(['i2cdetect', '-y','1'],stdout=subprocess.PIPE,)
            #cmdout = str(p.communicate())
            #print(p)
            for i in range(0,9):
                line = str(p.stdout.readline()).strip()
                line = line.translate({ord('-'):None})
                for match in re.finditer("[0-9][0-9]:.*[0-9][0-9]", line):
                    s = match.group()[4:].strip()
                    if(s != '70'): res.append(s)
            result.append({ch:res})
        except Exception as e:
            print(e)
            print("Error multiplexer: {0} on address {1}".format(e,mux_address))
    print(result)
    sensors.append(result)

def readData():
   while True:
      start = time.time()
      data = []
      for ch in range(len(sensors)):
         #print(len(sensors[ch]))
         if(len(sensors[ch])):
            res = []
            bus.write_byte_data(mux_address,0x04,list_ch[ch])
            for sensor in sensors[ch]:
               res.append(sensor.readRow())
            data.append(res)
      print(data)
      print(time.time()-start)

if __name__ == '__main__':
    print("Start scans")
    scanSystem()
    initSensors()
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
