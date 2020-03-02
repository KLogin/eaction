#!/usr/bin/python3
# coding: utf-8

## @package MPU9250
#  This is a FaBo9Axis_MPU9250 library for the FaBo 9AXIS I2C Brick.
#  http://fabo.io/202.html
#  Released under APACHE LICENSE, VERSION 2.0
#  http://www.apache.org/licenses/
#  FaBo <info@fabo.io>
import smbus
import sys
import time
import math
# import numpy as np
import madgwickahrs

## MPU9250I2C addresses
ADDRESS        = [0x68,0x69]
## AK8963 I2C slave address
AK8963_SLAVE_ADDRESS = 0x0C
# MPU 9250 registers
# https://www.invensense.com/wp-content/uploads/2015/02/RM-MPU-9250A-00-v1.6.pdf
## sample rate driver
# 0x13 - XG_OFFSET register for gyro offset
SMPLRT_DIV     = 0x19
CONFIG         = 0x1A
GYRO_CONFIG    = 0x1B
ACCEL_CONFIG   = 0x1C
ACCEL_CONFIG_2 = 0x1D
LP_ACCEL_ODR   = 0x1E
WOM_THR        = 0x1F
FIFO_EN        = 0x23
I2C_MST_CTRL   = 0x24
I2C_MST_STATUS = 0x36
INT_PIN_CFG    = 0x37
INT_ENABLE     = 0x38
INT_STATUS     = 0x3A
ACCEL_OUT      = 0x3B
TEMP_OUT       = 0x41
GYRO_OUT       = 0x43
I2C_MST_DELAY_CTRL = 0x67
SIGNAL_PATH_RESET  = 0x68
MOT_DETECT_CTRL    = 0x69
USER_CTRL          = 0x6A
PWR_MGMT_1         = 0x6B # 
PWR_MGMT_2         = 0x6C
FIFO_R_W           = 0x74
WHO_AM_I           = 0x75
## Gyro Full Scale Select in dps
GFS_250  = 0x00
GFS_500  = 0x01
GFS_1000 = 0x02
GFS_2000 = 0x03
## Accel Full Scale Select
AFS_2G   = 0x00
AFS_4G   = 0x01
AFS_8G   = 0x02
AFS_16G  = 0x03
# AK8963 Register Addresses
AK8963_ST1        = 0x02
AK8963_MAGNET_OUT = 0x03
AK8963_CNTL1      = 0x0A
AK8963_CNTL2      = 0x0B
AK8963_ASAX       = 0x10
# CNTL1 Mode select
## Power down mode
AK8963_MODE_DOWN   = 0x00
## One shot data output
AK8963_MODE_ONE    = 0x01
## Continous mag data output
AK8963_MODE_C8HZ   = 0x02
AK8963_MODE_C100HZ = 0x06
# Magneto Scale Select
AK8963_BIT_14 = 0x00
AK8963_BIT_16 = 0x01
bus = smbus.SMBus(1)
class MPU9250:
    def __init__(self, ch=0, dev=0, isMag=0, rate=0.02):
        self.status ="start init"
        self.name = "sensor_"+str(ch)+"_"+str(dev)
        self.isMag = isMag # is magnotometer actived
        self.address = ADDRESS[dev]
        self.toDeg =  57.2957795131
        self.rate = rate # update rate
        self.rate_real = rate # update rate
        self.madg =  None#madgwickahrs.MadgwickAHRS(self.rate,beta=0.8)
        # print(self.madg.beta)
        self.ch = ch # mux channel
        self.dev = dev # device number on channel 
        self.CalCounter = 500
        self.mag_coef = [0,0,0] # fabric magnitometer coefs
        self.ares = 0 # correction accel coef 
        self.gres = 0 # correction gyro coef
        self.mres = 0 # correction magnitometer coef
        self.gAngles = [0,0,0] # cur gyro angles
        self.a = [0,0,0] # cur delta accel data
        self.g = [0,0,0] # cur delta gyro data
        self.m = [0,0,0] # cur delta mag data
        self.t = 0 # cur temperature
        self.aData = [0,0,0] # tmp calibation accel data
        self.gData = [0,0,0] # tmp calibation gyro data
        self.mData = [0,0,0] # tmp calibation mag data
        self.aBias = [0,0,0] # cur accel biases
        self.gBias = [0,0,0] # cur gyro biases
        self.mBias = [0,0,0] # cur mag biases
        self.AA = 0.98 #  complementary filter alfa value
        self._AA = 1-self.AA
        self.compl = [0,0,0]  # complementary filter angles value
        # print(self.address)
        self.configMPU9250(GFS_500, AFS_4G)
        if(isMag): self.configAK8963(AK8963_MODE_C100HZ, AK8963_BIT_16)
        # self.startFrame = time.time()
    def configMPU9250(self, gfs, afs):
        self.status ="accel & gyro start init"
        if gfs == GFS_250: self.gres = 250.0/32768.0 # 0.00762939453=1/131 - 131.072000021
        elif gfs == GFS_500: self.gres = 500.0/32768.0 #  = 0.01525878906=1/65.5  - 65.5360000107
        elif gfs == GFS_1000: self.gres = 1000.0/32768.0 # 1000.0/32768.0 = 0.03051757812
        else: self.gres = 2000.0/32768.0 # gfs == GFS_2000  0.06103515625
        if afs == AFS_2G: self.ares = 2.0/32768.0
        elif afs == AFS_4G: self.ares = 4.0/32768.0
        elif afs == AFS_8G: self.ares = 8.0/32768.0
        else: self.ares = 16.0/32768.0 # afs == AFS_16G:
        # print("self.gres %f self.ares %f"%(self.gres,self.ares))
        # sleep off
        bus.write_byte_data(self.address, PWR_MGMT_1, 0x00)
        time.sleep(0.2)
        # auto select clock source
        bus.write_byte_data(self.address, PWR_MGMT_1, 0x01)
        # DLPF_CFG 
        bus.write_byte_data(self.address, CONFIG, 0x03)
        # sample rate divider
        bus.write_byte_data(self.address, SMPLRT_DIV, 0x04)
        # gyro full scale select
        # Bits [4:3] Gyro Full Scale Select: 00 = +250dps  01= +500 dps 10 = +1000 dps 11 = +2000 dps
        # 2:  [16384.0, 0x00], 4:  [8192.0,  0x08], 8:  [4096.0,  0x10], 16: [2048.0,  0x18]
        bus.write_byte_data(self.address, GYRO_CONFIG, gfs << 3)
        # accel full scale select
        time.sleep(0.1)
        bus.write_byte_data(self.address, ACCEL_CONFIG, afs << 3)
        # A_DLPFCFG
        # bus.write_byte_data(self.address, ACCEL_CONFIG_2, 0x03)
        
        # BYPASS_EN
        # bus.write_byte_data(self.address, INT_PIN_CFG, 0x02)
        # time.sleep(0.1)
    def configAK8963(self, mode, mfs):
        self.status ="mag config start init"
        if mfs == AK8963_BIT_14: self.mres = 4912.0/8190.0
        else: self.mres = 4912.0/32760.0 #  mfs == AK8963_BIT_16:
        print(mode,mfs,self.mres)
        whoAmI = bus.read_byte_data(0x0C, 0x00)
        print("whoAmI mag =",0x0C, 0x00, whoAmI,0x48)
        bus.write_byte_data(AK8963_SLAVE_ADDRESS, AK8963_CNTL1, 0x00)
        time.sleep(0.01)
        # set read FuseROM mode
        bus.write_byte_data(AK8963_SLAVE_ADDRESS, AK8963_CNTL1, 0x0F)
        time.sleep(0.01)
        # read coef data
        data = bus.read_i2c_block_data(AK8963_SLAVE_ADDRESS, AK8963_ASAX, 3)
        self.mag_coef[0] = (data[0] - 128) / 256.0 + 1.0
        self.mag_coef[1] = (data[1] - 128) / 256.0 + 1.0
        self.mag_coef[2] = (data[2] - 128) / 256.0 + 1.0
        # set power down mode
        bus.write_byte_data(AK8963_SLAVE_ADDRESS, AK8963_CNTL1, 0x00)
        time.sleep(0.01)
        # set scale&continous mode
        bus.write_byte_data(AK8963_SLAVE_ADDRESS, AK8963_CNTL1, (mfs<<4|mode))
        time.sleep(0.01)
    # def checkDataReady(self):
    #     drdy = bus.read_byte_data(self.address, INT_STATUS)
    #     if drdy & 0x01: return True
    #     else: return False
    # def readAccel(self):
    #     data = bus.read_i2c_block_data(self.address, ACCEL_OUT, 6)
    #     x = self.dataConv(data[1], data[0])*self.ares
    #     y = self.dataConv(data[3], data[2])*self.ares
    #     z = self.dataConv(data[5], data[4])*self.ares
    #     return [x,y,z]
    # def readGyro(self):
    #     data = bus.read_i2c_block_data(self.address, GYRO_OUT, 6)
    #     x = self.dataConv(data[1], data[0])*self.gres
    #     y = self.dataConv(data[3], data[2])*self.gres
    #     z = self.dataConv(data[5], data[4])*self.gres
    #     return [x,y,z]
    # def readMag(self):
    #     x,y,z = 0,0,0
    #     # check data ready
    #     drdy = bus.read_byte_data(AK8963_SLAVE_ADDRESS, AK8963_ST1)
    #     if drdy & 0x01 :
    #         data = bus.read_i2c_block_data(AK8963_SLAVE_ADDRESS, AK8963_MAGNET_OUT, 7)
    #         # check overflow
    #         if (data[6] & 0x08)!=0x08:
    #             x = self.dataConv(data[0], data[1])
    #             y = self.dataConv(data[2], data[3])
    #             z = self.dataConv(data[4], data[5])
    #             x = round(x * self.mag_coef[0]*self.mres, 3)
    #             y = round(y * self.mag_coef[1]*self.mres, 3)
    #             z = round(z * self.mag_coef[2]*self.mres, 3)
    #     return [x,y,z]
    # ## Read temperature
    # #  @param [out] temperature temperature(degrees C)
    # def readTemperature(self):
    #     data = bus.read_i2c_block_data(self.address, TEMP_OUT, 2)
    #     temp = self.dataConv(data[1], data[0])
    #     temp = round((temp / 333.87 + 21.0), 3)
    #     return temp
    def update(self):
        code= 'start'
        try: 
            # if(self.checkDataReady()):
            data = bus.read_i2c_block_data(self.address, ACCEL_OUT, 14)
            code = 'data ok'
            self.a = [self.dataConv(data[1], data[0]),self.dataConv(data[3], data[2]),self.dataConv(data[5], data[4])]
            code = 'accel ok'
            self.g = [self.dataConv(data[9], data[8]),self.dataConv(data[11], data[10]),self.dataConv(data[13], data[12])]
            # print(self.a,self.g)
            code = 'gyro ok'
            if(self.isMag):
                code = 'isMag ok'
                drdy = bus.read_byte_data(AK8963_SLAVE_ADDRESS, AK8963_ST1)
                code = 'mag ready ok'
                if drdy & 0x01 :
                    datam = bus.read_i2c_block_data(AK8963_SLAVE_ADDRESS, AK8963_MAGNET_OUT, 7)
                    code = 'datam ok'
                    # print(datam) *self.mres*self.mag_coef[2]-self.mBias[2]
                    self.m = [self.dataConv(datam[0],datam[1]),self.dataConv(datam[2],datam[3]),self.dataConv(datam[4],datam[5])]
                else: print("skip mag reading")
        except:
            print("update sensor error "+code) 
            # pass    
    def readgAngles(self,dt):
        self.gAngles[0] = self.gAngles[0]+self.g[0]*dt
        self.gAngles[1] = self.gAngles[1]+self.g[1]*dt
        self.gAngles[2] = self.gAngles[2]+self.g[2]*dt
        return self.gAngles
    def readRaw(self):
        raw = []
        if(self.isMag): raw = [self.a,self.g,self.m]
        else: raw = [self.a,self.g]
        return raw
    ## Data Convert
    # @param [in] self The object pointer.
    # @param [in] data1 LSB
    # @param [in] data2 MSB
    # @retval Value MSB+LSB(int 16bit)
    def dataConv(self, data1, data2):
        value = data1 | (data2 << 8)
        if(value & (1 << 16 - 1)): value -= (1<<16)
        return value
    def readComplementary(self,dt):
        # x = roll y = pitch z = yaw 
        # self.compl[0] = ((self.AA*(self.compl[0]-self.g[0]*dt) + self._AA*self.a[0]))#*self.toDeg
        self.compl[0] = self.AA*(self.compl[0]-self.g[0]*dt) + self._AA*self.toDeg*math.atan2(self.a[0],self.a[2])#*self.toDeg
        self.compl[1] = self.AA*(self.compl[1]+self.g[1]*dt) + self._AA*self.toDeg*math.atan2(self.a[1],self.a[2])
        self.compl[2] = self.compl[2]+self.g[2]*dt
        return self.compl
    def readMadg(self):
        # self.madg.update_imu(self.g,self.a)
        self.madg.update(self.g,self.a,self.m)
        return self.madg.quaternion.to_euler_angles()
        # return self.madg.quaternion._get_q2()
    
    def calibrate(self):
        print("start calibrate sensor")
        t0 = time.time()
        counter = self.CalCounter
        skipCounter = 0
        tik = 0.0002
        deltaTik =  self.rate -tik*1.01
        t1 = t0
        t3 = t0
        nextRun = t0
        sumDt = 0
        while counter>0:
            counter-=1
            t3 = time.time()
            while(t3 < nextRun):
                # cnt +=1
                time.sleep(tik) # !!!!!!!!! if too hot than turn on ;)
                t3 = time.time()
            nextRun = t3+deltaTik
            try: 
                self.update()
                self.aData[0]+=self.a[0]
                self.aData[1]+=self.a[1]
                self.aData[2]+=self.a[2]
                self.gData[0]+=self.g[0]
                self.gData[1]+=self.g[1]
                self.gData[2]+=self.g[2]
                if(self.isMag):
                    self.mData[0]+=self.m[0]
                    self.mData[1]+=self.m[1]
                    self.mData[2]+=self.m[2]
                t1 = t0
                t0 = time.time()
                dt = t0-t1
                sumDt += dt
            except:
                skipCounter += 1
        self.aBias[0]=self.aData[0]/self.CalCounter
        self.aBias[1]=self.aData[1]/self.CalCounter
        self.aBias[2]=self.aData[2]/self.CalCounter
        # print(self.gData[0]/self.CalCounter)
        self.gBias[0]=self.gData[0]/self.CalCounter
        self.gBias[1]=self.gData[1]/self.CalCounter
        self.gBias[2]=self.gData[2]/self.CalCounter
        if(self.isMag):
            self.mBias[0]=self.mData[0]/self.CalCounter
            self.mBias[1]=self.mData[1]/self.CalCounter
            self.mBias[2]=self.mData[2]/self.CalCounter
        self.aData = [0,0,0]
        self.gData = [0,0,0]
        self.mData = [0,0,0]
        self.rate_real = round(sumDt/self.CalCounter,5)
        print("Finish calibrate sensors average delta time=%1.5f skip %d frames"%(self.rate_real,skipCounter))
        #end test block

if __name__ == '__main__':
    bus.write_byte_data(0x70,0x04,0b00001000)
    print(0b00001000)
    sen = MPU9250(ch=3,dev=0,isMag=False)
    rate = 0.02
    # print("sen rate %f a %f,g %f,m %f,xCoef %f,yCoef %f,zCoef %f"%(rate,sen.ares,sen.gres,sen.mres,sen.magXcoef,sen.magYcoef,sen.magZcoef))
    # print(rate,sen.ares,sen.gres,sen.mres,sen.magXcoef,sen.magYcoef,sen.magZcoef)
    # print([sen.rate,sen.ares,sen.gres,sen.mres,sen.mag_coef[0],sen.mag_coef[1],sen.mag_coef[2]])
    sen.calibrate()
    print(sen.name,sen.rate_real,sen.gBias) 
    # print(sen.aBias)
    print(sen.gBias)
    # print(sen.mBias)
    allData = [] 
    tik = 0.002
    deltaTik =  sen.rate - tik*1.01
    counter = 10
    counterEnd = counter
    t0 = time.time()
    start = t0
    nextRun = t0
    while 0:
        counter -= 1
        t3 = time.time() 
        while (t3<nextRun):
            time.sleep(tik)
            t3 = time.time()
        nextRun = t3+deltaTik
        try:
            sen.update()
            # data = sen.readRaw()
            dt = time.time()-t0
            t0 = time.time()
            # data =  sen.readgAngles(dt)
            data = sen.readComplementary(dt)
            print ("dt=%1.5f roll %3.1f pitch %3.1f yaw %3.1f "%(dt,data[0],data[1],data[2]))
            # print(dt,sen.readMadg())
            # data.append(round(dt,5))
            # print(data)
            # allData.append(data)
        except:
            print("skip take data")
        # print(counter,dt)
    # time.sleep(0.01)
    
    print((time.time()-start)/counterEnd)
    # np.save('allData', np.array(allData))
    