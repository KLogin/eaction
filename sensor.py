#!/usr/bin/python3
# coding: utf-8
# mpu9250 registers https://cdn.sparkfun.com/assets/learn_tutorials/5/5/0/MPU-9250-Register-Map.pdf
# Madgwick filter
import smbus
import sys
import time
import math

class MPU9250:
    def __init__(self, bus, ch=0, dev=0):
        self.status = "start init"; self.lastError = '' # device status
        self.isReady = False; self.bus = bus; self.ADDRESSES = [0x68, 0x69]
        self.name = "sen_"+str(ch)+"_"+str(dev) # sensor name
        self.address = self.ADDRESSES[dev] # device address
        self.magMin = [32767, 32767, 32767]; self.magMax = [-32767, -32767, -32767]
        self.ch = ch; self.dev = dev # mux channel and dev number
        ## MPU9250I2C addresses and registers
        self.SMPLRT_DIV = 0x19; self.CONFIG = 0x1A; self.GYRO_CONFIG = 0x1B; self.INT_STATUS = 0x3A
        self.ACCEL_CONFIG = 0x1C; self.PWR_MGMT_1 = 0x6B; self.ACCEL_OUT = 0x3B
        self.WHO_AM_I = 0x75; self.USER_CTRL = 0x6A #  Bit 7 enable DMP, bit 3 reset DMP
        # i2c control registers
        self.I2C_MST_CTRL = 0x24; self.I2C_SLV0_ADDR = 0x25; self.I2C_SLV0_REG = 0x26; self.I2C_SLV0_DO = 0x63
        self.I2C_SLV0_CTRL = 0x27; self.EXT_SENS_DATA_00 = 0x49 # AK8963 data as internal MPU9250 register data
        ## AK8963 I2C slave address and registers
        self.AK8963_ASAX = 0x10; self.AK8963_ADDRESS = 0x0C; self.AK8963_DATA_OUT = 0x03; self.WHO_AM_I_AK8963 = 0x00
        self.AK8963_CNTL = 0x0A; self.AK8963_CNTL2 = 0x0B #// # Down and Reset
        self.q = [1, 0, 0, 0]; self.beta = 0.98 # Madg filter parameters
        # Sensor config data
        self.gfs = 0x01; self.afs = 0x01; self.gres = 500.0/32768.0; self.ares = 4.0/32768.0 # Imu settings for GFS_500, AFS_4G
        self.mfs = 0x16; self.mres = 10.0*4912.0/32760.0 # #AK8963_BIT_16 100Hz 16 bit -4912.0/8190.0 #??????????
        self.aBias = [0, 0, 0]; self.gBias = [0, 0, 0]; self.mBias = [0, 0, 0]; self.mScale = [1, 1, 1] # current biases
        # Temp variables
        self.tikSleep = 0.05; self.tik = 0.012; self.lastUpdate = time.perf_counter()  # delays between config update and data requests
        self.a = [0, 0, 0]; self.g = [0, 0, 0]; self.m = [0, 0, 0]; self.calibCnt = 0; self.errCnt = 0
        self.t = 0; self.data = []; self.datam = []; self.angles = [0, 0, 0] # raw sensors data
        self.mCoef = [0, 0, 0] # fabric chip magnitometer coefs

    def InitIMU(self):
        self.status = "accel & gyro start init"
        try:
            # self.status ="imuinit 0 "+str(self.address)
            self.bus.write_byte_data(self.address, self.PWR_MGMT_1, 0x00)
            # self.bus.write_byte_data(0x68, 0x6B, 0x00)
            # self.status ="imuinit 1"
            time.sleep(self.tikSleep)
            # self.bus.write_byte_data(self.address, PWR_MGMT_1, 0x01) # auto select clock source
            # self.bus.write_byte_data(self.address, CONFIG, 0x03) # DLPF_CFG
            # self.bus.write_byte_data(self.address, SMPLRT_DIV, 0x04) # sample rate divider
            self.bus.write_byte_data(self.address, self.GYRO_CONFIG, self.gfs << 3)
            # self.status ="imuinit 2"
            time.sleep(self.tikSleep)
            self.bus.write_byte_data(self.address, self.ACCEL_CONFIG, self.afs << 3)
            # self.status ="imuinit 3"
            # self.bus.write_byte_data(self.address, INT_PIN_CFG, 0x02) # BYPASS_EN
            # time.sleep(self.tikSleep)
            self.status = "accel & gyro start are ready"
            return True
        except:
            self.lastError = "g&a init"
            return False

    def InitMag(self): # Init mag to save data in MPU9250 internal register
        self.status = "mag start init"
        try:
            self.bus.write_byte_data(self.address, self.USER_CTRL, 0x20)  # Enable I2C Master mode
            self.bus.write_byte_data(self.address, self.I2C_MST_CTRL, 0x0D)   # I2C configuration multi-master I2C 400KHz
            self.bus.write_byte_data(self.address, self.I2C_SLV0_ADDR, self.AK8963_ADDRESS | 0x80)    # Set the I2C slave address of AK8963 and set for read.
            self.bus.write_byte_data(self.address, self.I2C_SLV0_REG, self.WHO_AM_I_AK8963)      # I2C slave 0 register address from where to begin data transfer
            self.bus.write_byte_data(self.address, self.I2C_SLV0_CTRL, 0x81)            # Enable I2C and transfer 1 byte
            time.sleep(self.tikSleep)
            whoAmI = self.bus.read_byte_data(self.address, self.EXT_SENS_DATA_00)
            # print("mag whoAmI",whoAmI,0x48,self.EXT_SENS_DATA_00)
            if(whoAmI == 0x48):# Connection is good! Begin the true initialization
                self.bus.write_byte_data(self.address, self.I2C_SLV0_ADDR, self.AK8963_ADDRESS)   # Set the I2C slave address of AK8963 and set for write.
                self.bus.write_byte_data(self.address, self.I2C_SLV0_REG, self.AK8963_CNTL2)   # I2C slave 0 register address from where to begin data transfer
                self.bus.write_byte_data(self.address, self.I2C_SLV0_DO, 0x01)      # Reset AK8963
                self.bus.write_byte_data(self.address, self.I2C_SLV0_CTRL, 0x81)   # Enable I2C and write 1 byte
                time.sleep(self.tikSleep)
                self.bus.write_byte_data(self.address, self.I2C_SLV0_ADDR, self.AK8963_ADDRESS)  # Set the I2C slave address of AK8963 and set for write.
                self.bus.write_byte_data(self.address, self.I2C_SLV0_REG, self.AK8963_CNTL)   # I2C slave 0 register address from where to begin data transfer
                self.bus.write_byte_data(self.address, self.I2C_SLV0_DO, 0x00)         # Power down magnetometer
                self.bus.write_byte_data(self.address, self.I2C_SLV0_CTRL, 0x81)         # Enable I2C and transfer 1 byte
                time.sleep(self.tikSleep)
                self.bus.write_byte_data(self.address, self.I2C_SLV0_ADDR, self.AK8963_ADDRESS)  # Set the I2C slave address of AK8963 and set for write.
                self.bus.write_byte_data(self.address, self.I2C_SLV0_REG, self.AK8963_CNTL)   # I2C slave 0 register address from where to begin data transfer
                self.bus.write_byte_data(self.address, self.I2C_SLV0_DO, 0x0F)     # Enter fuze mode
                self.bus.write_byte_data(self.address, self.I2C_SLV0_CTRL, 0x81)     # Enable I2C and write 1 byte
                time.sleep(self.tikSleep)
                self.bus.write_byte_data(self.address, self.I2C_SLV0_ADDR, self.AK8963_ADDRESS | 0x80) # Set the I2C slave address of AK8963 and set for read.
                self.bus.write_byte_data(self.address, self.I2C_SLV0_REG, self.AK8963_ASAX)  # I2C slave 0 register address from where to begin data transfer
                self.bus.write_byte_data(self.address, self.I2C_SLV0_CTRL, 0x83)       # Enable I2C and read 3 bytes
                time.sleep(self.tikSleep) # Read the x, y, and z axis calibration values
                self.mdata = self.bus.read_i2c_block_data(self.address, self.EXT_SENS_DATA_00, 3)
                self.mCoef = [(self.mdata[0]-128)/256.0+1.0, (self.mdata[1]-128)/256.0+1.0, (self.mdata[2]-128)/256.0+1.0]
                # print(self.mCoef)
                self.bus.write_byte_data(self.address, self.I2C_SLV0_ADDR, self.AK8963_ADDRESS)     # Set the I2C slave address of AK8963 and set for write.
                self.bus.write_byte_data(self.address, self.I2C_SLV0_REG, self.AK8963_CNTL)      # I2C slave 0 register address from where to begin data transfer
                self.bus.write_byte_data(self.address, self.I2C_SLV0_DO, 0x00)          # Power down magnetometer
                self.bus.write_byte_data(self.address, self.I2C_SLV0_CTRL, 0x81)      # Enable I2C and write 1 byte
                time.sleep(self.tikSleep)
                self.bus.write_byte_data(self.address, self.I2C_SLV0_ADDR, self.AK8963_ADDRESS)   # Set the I2C slave address of AK8963 and set for write.
                self.bus.write_byte_data(self.address, self.I2C_SLV0_REG, self.AK8963_CNTL)   # I2C slave 0 register address from where to begin data transfer
                self.bus.write_byte_data(self.address, self.I2C_SLV0_DO, self.mfs)  # Set magnetometer for 16 bit continous 100 Hz sample rates
                self.bus.write_byte_data(self.address, self.I2C_SLV0_CTRL, 0x81)      # Enable I2C and transfer 1 byte
                time.sleep(self.tikSleep)
                self.bus.write_byte_data(self.address, self.I2C_SLV0_ADDR, self.AK8963_ADDRESS | 0x80)  # Set the I2C slave address of AK8963 and set for read.
                self.bus.write_byte_data(self.address, self.I2C_SLV0_REG, self.AK8963_DATA_OUT)  # I2C slave 0 register address from where to begin data transfer
                self.bus.write_byte_data(self.address, self.I2C_SLV0_CTRL, 0x87)   # Enable I2C for transfer 7 bytes
                # time.sleep(self.tikSleep)
                # self.datam = self.bus.read_i2c_block_data(self.address, self.EXT_SENS_DATA_00,7)
                # print(self.datam)
                self.status = "mag is ready"
                return True
            else: 
                self.lastError = "mag init"
                return False
        except: 
            self.lastError = "mag init"
            return False

    def update_raw(self, type): # type: 'gyro', 'mag', 'accel'
        # print("update_raw ",type)
        if(type == 'mag'):
            try:
                self.datam = self.bus.read_i2c_block_data(self.address, self.EXT_SENS_DATA_00, 7)
                if not (self.datam[6] & 0x08):
                    self.m = [self.dataConv(self.datam[0], self.datam[1]), self.dataConv(self.datam[2], self.datam[3]), self.dataConv(self.datam[4], self.datam[5])]
                    return True
                else: return False
            except: return False
        else:
            try: 
                # if(bus.read_byte_data(self.address, self.INT_STATUS) & 0x01):
                self.data = self.bus.read_i2c_block_data(self.address, self.ACCEL_OUT, 14)
                self.a = [self.dataConv(self.data[1], self.data[0]), self.dataConv(self.data[3], self.data[2]), self.dataConv(self.data[5], self.data[4])]
                self.g = [self.dataConv(self.data[9], self.data[8]), self.dataConv(self.data[11], self.data[10]), self.dataConv(self.data[13], self.data[12])]
                return True
            except: return False
        return False

    def updateIMU(self):
        try:
            # if(bus.read_byte_data(self.address, self.INT_STATUS) & 0x01):
            self.data = self.bus.read_i2c_block_data(self.address, self.ACCEL_OUT, 14)
            self.a = [self.dataConv(self.data[1], self.data[0])*self.ares, self.dataConv(self.data[3], self.data[2])*self.ares, self.dataConv(self.data[5], self.data[4])*self.ares]
            self.g = [(self.dataConv(self.data[9], self.data[8])-self.gBias[0])*self.gres, (self.dataConv(self.data[11], self.data[10])-self.gBias[1])*self.gres, (self.dataConv(self.data[13], self.data[12])-self.gBias[2])*self.gres]
            # else:
            #     print("sensor is not ready")
            #     return False
        except: return False
        return True

    def updateTemp(self):
        self.t = round((self.dataConv(self.data[7], self.data[6]) / 333.87 + 21.0), 3)
        return self.t

    def updateMag(self):
        try:
            self.datam = self.bus.read_i2c_block_data(self.address, self.EXT_SENS_DATA_00, 7)
            # print(self.datam,self.mres,self.mCoef)
            self.m = [(self.dataConv(self.datam[0], self.datam[1])*self.mres*self.mCoef[0]-self.mBias[0])*self.mScale[0] \
            , (self.dataConv(self.datam[2], self.datam[3])*self.mres*self.mCoef[1]-self.mBias[1])*self.mScale[1] \
            , (self.dataConv(self.datam[4], self.datam[5])*self.mres*self.mCoef[2]-self.mBias[2])*self.mScale[2]]
            # print(self.m)
        except:
            # print("mag convert error")
            return False
        return True

    def dataConv(self, data1, data2): # convert two uint8 in one uint16
        val = data1 | (data2 << 8) # val=(data2 << 8)+data1
        if(val & (1 << 16-1)): val -= (1 << 16) # convert uint16(0 to 65535) to int16(-32768 to +32767)
        return val

    def madgwickFilter(self, dt): # Madgwick Filter
        try:
            #(-ax, ay, az, gx*pi/180.0f, -gy*pi/180.0f, -gz*pi/180.0f,  my,  -mx, mz);
            # BMP280 (-ax, ay, az, gx*pi/180.0f, -gy*pi/180.0f, -gz*pi/180.0f,  my,  -mx, mz);
            # MPU9250 ax, ay, az, gx*PI/180.0f, gy*PI/180.0f, gz*PI/180.0f,  my,  mx, mz
            ax = self.a[0]; ay = -self.a[1]; az = self.a[2]; mx = self.m[1]; my = -self.m[0]; mz = self.m[2]
            gx = math.radians(self.g[0]); gy = -math.radians(self.g[1]); gz = -math.radians(self.g[2])
            q1 = self.q[0]; q2 = self.q[1]; q3 = self.q[2]; q4 = self.q[3]
            q1x2 = 2*q1; q2x2 = 2*q2; q3x2 = 2*q3; q4x2 = 2*q4; q1q3x2 = 2*q1*q3; q3q4x2 = 2*q3*q4
            q1q1 = q1*q1; q1q2 = q1*q2; q1q3 = q1*q3; q1q4 = q1*q4; q2q2 = q2*q2; q2q3 = q2*q3
            q2q4 = q2*q4; q3q3 = q3*q3; q3q4 = q3*q4; q4q4 = q4*q4
            norm = math.sqrt(ax * ax + ay * ay + az * az)
            if norm is 0: return
            norm = math.sqrt(mx * mx + my * my + mz * mz)
            if norm is 0: return
            mx /= norm; my /= norm; mz /= norm
            hx = mx*q1q1-(2*q1*my)*q4+(2*q1*mz)*q3+mx*q2q2+q2x2*my*q3+q2x2*mz*q4-mx*q3q3-mx*q4q4
            hy = (2*q1*mx)*q4+my*q1q1-(2*q1*mz)*q2+(2*q2*mx)*q3-my*q2q2+my*q3q3+q3x2*mz*q4-my*q4q4
            bx_2 = math.sqrt(hx*hx+hy*hy)
            bz_2 = -(2*q1*mx)*q3+(2*q1*my)*q2+mz*q1q1+(2*q2*mx)*q4-mz*q2q2+q3x2*my*q4-mz*q3q3+mz*q4q4
            bx_4 = 2*bx_2; bz_4 = 2*bz_2
            s1 = -q3x2*(2*q2q4-q1q3x2-ax)+q2x2*(2*q1q2+q3q4x2-ay)-bz_2*q3*(bx_2*(0.5-q3q3-q4q4)+bz_2*(q2q4-q1q3)-mx)+(-bx_2*q4+bz_2*q2)*(bx_2*(q2q3-q1q4)+bz_2*(q1q2+q3q4)-my)+bx_2*q3*(bx_2*(q1q3+q2q4)+bz_2*(0.5-q2q2-q3q3)-mz)
            s2 = q4x2*(2*q2q4-q1q3x2-ax)+q1x2*(2*q1q2+q3q4x2-ay)-4*q2*(1-2*q2q2-2*q3q3-az)+bz_2*q4 *(bx_2*(0.5-q3q3-q4q4)+bz_2*(q2q4-q1q3)-mx)+(bx_2*q3+bz_2*q1)*(bx_2*(q2q3-q1q4)+bz_2*(q1q2+q3q4)-my)+(bx_2*q4-bz_4*q2)*(bx_2*(q1q3+q2q4)+bz_2*(0.5-q2q2-q3q3)-mz)
            s3 = -q1x2*(2*q2q4-q1q3x2-ax)+q4x2*(2*q1q2+q3q4x2-ay)-4*q3*(1-2*q2q2-2*q3q3-az)+(-bx_4*q3-bz_2*q1)*(bx_2*(0.5-q3q3-q4q4)+bz_2*(q2q4-q1q3)-mx)+(bx_2*q2+bz_2*q4)*(bx_2*(q2q3-q1q4)+bz_2*(q1q2+q3q4)-my)+(bx_2*q1-bz_4*q3)*(bx_2*(q1q3+q2q4)+bz_2*(0.5-q2q2-q3q3)-mz)
            s4 = q2x2*(2*q2q4-q1q3x2-ax)+q3x2*(2*q1q2+q3q4x2-ay)+(-bx_4*q4+bz_2*q2)*(bx_2*(0.5-q3q3-q4q4)+bz_2*(q2q4-q1q3)-mx)+(-bx_2*q1+bz_2*q3)*(bx_2*(q2q3-q1q4)+bz_2*(q1q2+q3q4)-my)+bx_2*q2*(bx_2*(q1q3+q2q4)+bz_2*(0.5-q2q2-q3q3)-mz)
            norm = math.sqrt(s1 * s1 + s2 * s2 + s3 * s3 + s4 * s4)
            s1 /= norm; s2 /= norm; s3 /= norm; s4 /= norm
            qDot1 = 0.5 * (-q2 * gx - q3 * gy - q4 * gz) - self.beta * s1
            qDot2 = 0.5 * (q1 * gx + q3 * gz - q4 * gy) - self.beta * s2
            qDot3 = 0.5 * (q1 * gy - q2 * gz + q4 * gx) - self.beta * s3
            qDot4 = 0.5 * (q1 * gz + q2 * gy - q3 * gx) - self.beta * s4 # Integrate to yield quaternion
            q1 += qDot1 * dt; q2 += qDot2 * dt; q3 += qDot3 * dt; q4 += qDot4 * dt
            norm = math.sqrt(q1 * q1 + q2 * q2 + q3 * q3 + q4 * q4)
            self.q[0] = q1/norm; self.q[1] = q2/norm; self.q[2] = q3/norm; self.q[3] = q4/norm
        except: pass
        # return self.q

    def eulerAngels(self):
        a12 = 2*(self.q[1]*self.q[2]+self.q[0]*self.q[3])
        a22 = self.q[0]*self.q[0]+self.q[1]*self.q[1]-self.q[2]*self.q[2]-self.q[3]*self.q[3]
        a31 = 2*(self.q[0]*self.q[1]+self.q[2]*self.q[3])
        a32 = 2*(self.q[1]*self.q[3]-self.q[0]*self.q[2])
        a33 = self.q[0]*self.q[0]-self.q[1]*self.q[1]-self.q[2]*self.q[2]+self.q[3]*self.q[3]
        self.angles[0] = math.degrees(math.atan2(a31, a33))+180 #roll -180 - +180 # 
        self.angles[1] = -math.degrees(math.asin(a32))+180      #pitch -180 - +180
        self.angles[2] = math.degrees(math.atan2(a12, a22))+180  # yaw 0 - +360

    def updateQ(self):
        if(self.updateIMU()):
            self.updateMag()
            now = time.perf_counter()
            deltat = ((now - self.lastUpdate))
            self.lastUpdate = now
            # print(deltat,"a=",sen.a,"g=",sen.g,"m=",sen.m)
            self.madgwickFilter(deltat)
            return True
        return False

if __name__ == '__main__':
    print("Start init sensor")
    def calibrate(sen, points=100, type='gyro'):
        cnt = 0; counterErr = 0; sen.status = "start calibrate gyro sensor"
        print("start calib: ", type)
        while(cnt < points):
            if(sen.update_raw(type)):
                if(type == 'gyro'):
                    for i in range(3):	sen.gBias[i] += sen.g[i]; sen.aBias[i] += sen.a[i]
                elif(type == 'accel'):
                    for i in range(3):	sen.aBias[i] += sen.a[i]
                elif(type == 'mag'):
                    # print("mag 00", sen.m)
                    for j in range(3):
                        if(sen.m[j] > sen.magMax[j]): sen.magMax[j] = sen.m[j]
                        if(sen.m[j] < sen.magMin[j]): sen.magMin[j] = sen.m[j]
                # print("---",sen.magMax,sen.magMin)
                cnt += 1
            else:
                counterErr += 1
                if(counterErr > 50):
                    sen.lastError = 'gyro calib'
                    return False
            time.sleep(sen.tik)
        if(type == 'mag'):
            mChord = [0, 0, 0]; avgChord = 0
            for i in range(3):
                sen.mBias[i] = ((sen.magMax[i]+sen.magMin[i])/2)*sen.mres*sen.mCoef[i]
                mChord[i] = (sen.magMax[i]-sen.magMin[i])/2
                avgChord += mChord[i]
            avgChord /= 3
            sen.mScale = [avgChord/mChord[0], avgChord/mChord[1], avgChord/mChord[2]]
            print("new mag Biases:", sen.mBias, sen.mScale)
        else:
            for i in range(3): sen.aBias[i] /= points; sen.gBias[i] /= points
            print("new Biases:", type, " ", sen.gBias, sen.aBias)
        sen.status = "End calibrate  "+type+". Skip frames:"+str(counterErr)
        return True

    def calibrateGyro(sen, points=500):
        cnt = 0; counterErr = 0; sen.status = "start calibrate accel sensor"
        while(cnt < points):
            if(sen.update_raw("gyro")):
                sen.aBias[0] += sen.a[0]; sen.aBias[1] += sen.a[1]; sen.aBias[2] += sen.a[2]
                sen.gBias[0] += sen.g[0]; sen.gBias[1] += sen.g[1]; sen.gBias[2] += sen.g[2]
                cnt += 1
            else: 
                counterErr += 1
                if(counterErr > 50):
                    sen.lastError = "accel calib"
                    return False
            time.sleep(sen.tik)
        sen.aBias = [sen.aBias[0]/points, sen.aBias[1]/points, sen.aBias[2]/points]
        sen.gBias = [sen.gBias[0]/points, sen.gBias[1]/points, sen.gBias[2]/points]
        print("old Biases:", sen.gBias, sen.aBias, sen.mBias, sen.mScale)
        sen.status = "End calibrate accel. Skip frames:"+str(counterErr)
        return True

    def calibrateMag(sen, N):
        cnt = 0; counterErr = 0; sen.status = "start calibrate mag sensor" #; magMin = [32767, 32767, 32767]; magMax = [-32767, -32767, -32767]
        while(cnt < N):
            if(sen.update_raw("mag")): # update raw data from sensor
                for j in range(3): # Search data min&max
                    if(sen.m[j] > sen.magMax[j]): sen.magMax[j] = sen.m[j]
                    if(sen.m[j] < sen.magMin[j]): sen.magMin[j] = sen.m[j]
                cnt += 1
            else:
                counterErr += 1
                # print("errCounter: ",counterErr,cnt)
                if(counterErr > 50):
                    sen.lastError = 'mag calib'
                    return False
            time.sleep(sen.tik)
        mChord = [0, 0, 0]; avgChord = 0
        for i in range(3):
            sen.mBias[i] = ((sen.magMax[i]+sen.magMin[i])/2)*sen.mres*sen.mCoef[i]
            mChord[i] = (sen.magMax[i]-sen.magMin[i])/2
            avgChord += mChord[i]
        avgChord /= 3
        sen.mScale = [avgChord/mChord[0],avgChord/mChord[1], avgChord/mChord[2]]
        sen.status = "old End calibrate mag. Skip frames:"+str(counterErr)
        return True

    channel = 4
    device = 0
    ch_codes = [0b00000001, 0b00000010, 0b00000100, 0b00001000, 0b00010000, 0b00100000, 0b01000000, 0b10000000]
    bus = smbus.SMBus(1); muxTCA9548A = 0x70; errCounter = 3
    isMuxReady = False; tmpCounter = errCounter
    print("start init mux ", channel, ch_codes[channel])
    while(tmpCounter and not isMuxReady):
        try:
            bus.write_byte_data(muxTCA9548A, 0x04, ch_codes[channel])
            isMuxReady = True
        except: tmpCounter -= 1
        time.sleep(0.1)
    print("isMuxReady=", isMuxReady)
    if(isMuxReady):
    # if(0):
        print("start create sensor object")
        sen = MPU9250(bus, ch=channel, dev=device)
        time.sleep(0.1)
        tmpCounter = errCounter
        print("start init sensor ", sen.name)
        # try:
        #     bus.write_byte_data(0x68, 0x6B, 0x00)
        # except Exception as e: print(e)
        if(sen.InitIMU()):
            while(tmpCounter and not sen.isReady):
                print("try init mag")
                if(sen.InitMag()):
                    sen.isReady = True
                    print("mag is ok")
                tmpCounter -= 1; time.sleep(sen.tikSleep)
        else: print("Error init IMU ", sen.status)
        if(sen.isReady):
            # rate = 0.02
            # print("sen rate %f a %f,g %f,m %f,xCoef %f,yCoef %f,zCoef %f"%(rate,sen.ares,sen.gres,sen.mres,sen.magXcoef,sen.magYcoef,sen.magZcoef))
            # print(rate,sen.ares,sen.gres,sen.mres,sen.magXcoef,sen.magYcoef,sen.magZcoef)
            # print([sen.rate,sen.ares,sen.gres,sen.mres,sen.mag_coef[0],sen.mag_coef[1],sen.mag_coef[2]])
            print("Start calibre gyro sensor. Don't move device!!!!!")
            calibrate(sen, 100, 'gyro')
            # calibrateGyro(sen, 500)
            print("Gyro: ", sen.status, ". Last error: ", sen.lastError)
            # print("\t",sen.name,sen.isReady,sen.gres,sen.gBias)
            # print("Start magnetometer calibration. Wave and rotate device in a figure eight until notified.\n")
            # time.sleep(3)
            # calibrate(sen,500,'mag')
            # calibrateMag(sen,500)
            # print("Mag: ",sen.status,". Last error: ", sen.lastError)
            # sen.mBias = [145, 145, -155] ; sen.mScale = [1.10, 1.05, 1.05]
            # print("\t",sen.mres,sen.mCoef,sen.mBias,sen.mScale)
            sen.lastUpdate = time.perf_counter()
            while 1:
                try:
                    if(sen.updateQ()):
                    # if(sen.updateIMU()):
                    #     sen.updateMag()
                        now = time.perf_counter()
                        deltat = ((now - sen.lastUpdate))
                        sen.lastUpdate = now
                    #     # print(deltat,"a=",sen.a,"g=",sen.g,"m=",sen.m)
                    #     sen.madgwickFilter(deltat)
                        # Print results to screen
                        sen.eulerAngels()
                        # Print data
                        # print(deltat, sen.a,sen.g,sen.m)
                        sys.stdout.write('\r dt:{:1.5f} R: {:<8.1f} P: {:<8.1f} Y: {:<8.1f}'.format(deltat,sen.angles[0],sen.angles[1],sen.angles[2]))
                        # sys.stdout.write('\r dt:{:1.5f} R: {:<8.1f} P: {:<8.1f} Y: {:<8.1f}'.format(deltat,sen.q[3],sen.q[1],sen.q[2]))
                        sys.stdout.flush()
                        # print('R: {:<8.1f} P: {:<8.1f} Y: {:<8.1f}'.format(sen.roll,sen.pitch,sen.yaw))
                    else:
                        print("skip frame")
                except Exception as e: print(e)
                # print(counter,dt)
                time.sleep(sen.tik)
                # print('dt:{:1.5f} R: {:<8.1f} P: {:<8.1f} Y: {:<8.1f}'.format(round(sen.lastUpdate,4),sen.angles[0],sen.angles[1],sen.angles[2]))
                # print((time.time()-start)/counterEnd)
                # np.save('allData', np.array(allData))
        else: print("can not start sensor")
    else: print("Mux is not ready")
