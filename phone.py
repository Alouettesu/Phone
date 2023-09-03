import RPi.GPIO as GPIO
import time
import serial

SIM_POWER_PIN = 18

def sim_switch_on():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SIM_POWER_PIN, GPIO.OUT, initial=GPIO.LOW)
    time.sleep(1)
    GPIO.output(SIM_POWER_PIN, GPIO.HIGH)
    time.sleep(2)
    GPIO.output(SIM_POWER_PIN, GPIO.LOW)
    time.sleep(2)

sim_switch_on()
port = serial.Serial("/dev/serial0", baudrate=19200, timeout=1)
port.write(b'AT\r\n')
rcv = port.read(15)
print (rcv.decode())

port.write(b'AT+CPOWD=1\r\n')
rcv = port.read(15)
print (rcv.decode())

GPIO.cleanup(SIM_POWER_PIN)