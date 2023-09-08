import asyncio
import serial_asyncio
import serial
from enum import Enum
import threading
from datetime import datetime
import vksend
import RPi.GPIO as GPIO
import time
import config

CheckSmsInterval = 10

class Stage(Enum):
    Startup = 1
    CheckSimPower = 2
    Work = 3

class Status(Enum):
    Idle = 1
    Wait = 2
    Send = 3
    Timeout = 4

def findAnyOf(where, what: list, start=None, finish=None):
    idx = [where.find(sym, start, finish) for sym in what]
    return min([i for i in idx if i >= 0], default=-1)

def sim_switch_on():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(config.SIM_POWER_PIN, GPIO.OUT, initial=GPIO.LOW)
    time.sleep(1)
    GPIO.output(config.SIM_POWER_PIN, GPIO.HIGH)
    time.sleep(2)
    GPIO.output(config.SIM_POWER_PIN, GPIO.LOW)
    time.sleep(2)

class Sms(object):
    def __init__(self):
        self.Num = None
        self.Stat = None
        self.Sender = None
        self.Alpha = None
        self.Timer = None
        self.Text = None

class SmsList(object):
    def __init__(self, smsRecord: list):
        for i, record in enumerate(smsRecord):
            if record.startswith(b'+CMGL'):
                smsRecord = smsRecord[i:]
                break

        if len(smsRecord) == 2:
            return
        if (len(smsRecord)-1) % 2 != 0:
            raise ValueError('SMS record must have 2 elements')
        self.smsList = []
        for recNum in range((len(smsRecord) - 1) // 2):
            sms = Sms()
            cmgl = smsRecord[recNum * 2].decode().split(',"')
            sms.Num = int(cmgl[0][7:])
            sms.Stat = cmgl[1][:-1]
            sms.Sender = cmgl[2][:-1]
            sms.Alpha = cmgl[3][:-1]
            sms.Time = datetime.strptime(cmgl[4][:17], '%y/%m/%d,%H:%M:%S')
            sms.Text = smsRecord[recNum * 2 + 1].decode()
            try:
                sms.Text = bytes.fromhex(sms.Text)
                sms.Text = sms.Text.decode(encoding='utf-16-be')
            except:
                pass
            self.smsList.append(sms)
            print(sms.Text)


class OutputProtocol(asyncio.Protocol):
    def __init__(self):
        super().__init__()
        self.stage = Stage.Startup
        self.status = Status.Idle
        self.lines = []
        self.buffer = b''

    def connection_made(self, transport):
        self.transport = transport
        self.stage = Stage.CheckSimPower
        self.checkSimPower()

    def checkSimPower(self):
        self.transport.write(b'AT\r\n')
        self.powerTimer = threading.Timer(2, self.simPowerTimeout)
        self.powerTimer.start()

    def simPowerTimeout(self):
        sim_switch_on()
        self.checkSimPower()

    def data_received(self, data):
        self.buffer += data
        start = 0
        while True:
            finish = findAnyOf(self.buffer, [b'\r', b'\n', b'>'], start)
            if finish == start:
                start = finish + 1
                continue
            if finish != -1:
                self.lines.append(self.buffer[start:finish])
            else:
                self.buffer = self.buffer[start:]
                break
            start = finish + 1
        self.processLines()
        
    def processLines(self):
        while self.lines:
            line = self.lines[0]
            if b'AT' in line and self.stage == Stage.CheckSimPower:
                self.powerTimer.cancel()
                self.stage = Stage.Work
                self.checkSms()
            print(line)
            if b'+CMTI:' in line:
                self.checkSms()
                del self.lines[0]
            elif b'+CMGL' in line:
                foundFinish = False
                for j in range(len(self.lines)):
                    if b'OK' in self.lines[j] or b'ERROR' in self.lines[j]:
                        foundFinish = True
                        sms = SmsList(self.lines[:j+1])
                        if vksend.send_sms(sms):
                            self.deleteSms()
                        del self.lines[:j+1]
                if not foundFinish:
                    break
            elif b'RING' in line:
                self.transport.write(b'ATH0\r\n') #Decline call
                del self.lines[0]
            #elif b'NO CARRIER in line':
                #pass
            else:
                del self.lines[0]

    def deleteSms(self):
        self.transport.write(b'AT+CMGDA="DEL READ"\r\n')

    def checkSms(self):
        self.transport.write(b'AT+CMGL="ALL",0\r\n')
        if hasattr(self, 'checkSmsTimer') and self.checkSmsTimer is not None:
            self.checkSmsTimer.cancel()
        self.checkSmsTimer = threading.Timer(CheckSmsInterval, self.checkSms)
        self.checkSmsTimer.start()

    def connection_lost(self, exc):
        self.transport.loop.stop()



loop = asyncio.get_event_loop()
coro = serial_asyncio.create_serial_connection(loop, OutputProtocol, "/dev/serial0", baudrate=19200, timeout=1, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
transport, protocol = loop.run_until_complete(coro)
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
protocol.checkSmsTimer.cancel()
loop.close()
