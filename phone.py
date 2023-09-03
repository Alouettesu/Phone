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

def findAnyOf(where, what: list, start=None, finish=None):
    idx = [where.find(sym, start, finish) for sym in what]
    return min([i for i in idx if i >= 0], default=-1)


def transact(port, msg):
    port.write(msg)
    rcv = port.read(150)
    print(rcv)
    start = 0
    lines = []
    while True:
        finish = findAnyOf(rcv, [b'\r', b'\n'], start)
        if finish == start:
            start = finish + 1
            continue
        if finish != -1:
            lines.append(rcv[start:finish])
        else:
            if len(rcv) > start + 1:
                lines.append(rcv[start:])
            break
        start = finish + 1
    return lines

def send_sms(port, phoneNum, text):
    rcv = transact(port, b'AT+CMGS="' + phoneNum.encode() + b'"\r')
    print (rcv)
    rcv = transact(port, text.encode() + b'\x1a')
    print(rcv)

def get_sms_list(port):
    rcv = transact(port, b'AT+CMGL="ALL",1\r\n')
    #rcv = transact(port, b'AT+CMGL=?\r\n')
    print(rcv)

def call(port, phoneNum):
    rcv = transact(port, b'ATD' + phoneNum.encode() + b';\r\n')
    print (rcv)

# sim_switch_on()
port = serial.Serial("/dev/serial0", baudrate=19200, timeout=0.5, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)

call(port, "+79122283538")

#send_sms(port, "+79122283538", "sms")

#port.write(b'AT+CPOWD=1\r\n')
#rcv = port.read(15)
#print (rcv)

# GPIO.cleanup(SIM_POWER_PIN)