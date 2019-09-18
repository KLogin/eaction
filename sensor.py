#RPi Pinouts

#I2C Pins 
#GPIO2 -> SDA
#GPIO3 -> SCL
# sudo apt-get install -y i2c-tools
# sudo apt-get install -y python-smbus
# List all available I2C busses:
# i2cdetect -l
# Immediately scan the standard addresses on I2C bus 1 (i2c-1), using the default method for each address (no user confirmation):
# i2cdetect -y 1
# Query the functionalities of I2C bus 1 (i2c-1):
# i2cdetect -F 1
# sudo i2cget -y 1 0x30 0

#Import the Library Requreid 
# import smbus
from smbus2 import SMBus
import time

# for RPI version 1, use "bus = smbus.SMBus(0)"
# bus = smbus.SMBus(1)

# This is the address we setup in the Arduino Program
#Slave Address 1
address = 50

#Slave Address 2
address_2 = 0x05

while True:
    with SMBus(1) as bus:
        b = bus.read_byte_data(address, 0)
        print(b)

#End of the Script