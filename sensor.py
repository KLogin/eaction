import time
# import board
# import busio
# import adafruit_tsl2591
import multiplexer
import mpu9250

# Create I2C bus as normal
# i2c = busio.I2C(board.SCL, board.SDA)
# i2cdetect -y 1
# i2cset -y 1 0x70 3
# Mine is at 0x74. The Rpi has one built in at 0x70 so avoid that address.
# To select bus #0:
# i2cset -y 1 0x74 0x04 0x04
# To select mux bus #1
# i2cset -y 1 0x74 0x04 0x05
# To select mux bus #3
# s

# Create the TCA9548A object and give it the I2C bus
#tca = adafruit_tca9548a.TCA9548A(i2c)
numSens = 2

tca = multiplexer.I2C_SW('I2C switch 0',0x70,1)
tsl = []
for i in range(numSens):
	print(i)
	tca.chn(i)
	tsl.append(mpu9250.MPU9250())
	
# For each sensor, create it using the TCA9548A channel instead of the I2C object
# tsl1 = FaBo9Axis_MPU9250.MPU9250(tc[0])
# tsl2 = FaBo9Axis_MPU9250.MPU9250(tc[1])
# adafruit_tsl2591.TSL2591(tca[0])
# tsl2 = adafruit_tsl2591.TSL2591(tca[1])

# Loop and profit!
while True:
	data = []
	for i in range(numSens):
		tca.chn(i)
		data.append([i])
		data.append(tsl[i].readAccel()) # 
		data.append(tsl[i].readGyro())
		data.append(tsl[i].readMagnet())
		print(data)
		
#	print(tsl1.lux, tsl2.lux)
#	time.sleep(0.1)
