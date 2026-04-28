# mfrc522.py - MFRC522 RFID 驱动 (SPI)
from machine import Pin
import utime

class MFRC522:
    OK = 0
    NOTAGERR = 1
    ERR = 2

    REQIDL = 0x26
    REQALL = 0x52
    AUTHENT1A = 0x60
    AUTHENT1B = 0x61

    def __init__(self, sck, mosi, miso, rst, cs):
        self.sck = Pin(sck, Pin.OUT)
        self.mosi = Pin(mosi, Pin.OUT)
        self.miso = Pin(miso, Pin.IN)
        self.rst = Pin(rst, Pin.OUT)
        self.cs = Pin(cs, Pin.OUT)
        self.rst.value(0)
        utime.sleep_ms(50)
        self.rst.value(1)
        utime.sleep_ms(50)
        self._init()

    def _init(self):
        self._write(0x2A, 0x8D)  # Timer
        self._write(0x2B, 0x3E)
        self._write(0x2D, 30)
        self._write(0x15, 0x40)  # Rx
        self._write(0x16, 0x00)
        self._write(0x18, 0x32)  # Serial speed
        self._write(0x01, 0x00)  # Mode idle
        self._write(0x04, 0x00)  # CRC
        self._write(0x0A, 0x00)  # Tx
        self._write(0x0B, 0x00)

    def _write(self, addr, val):
        self.cs.value(0)
        self.sck.value(0)
        self._transfer((addr << 1) & 0x7E)
        self._transfer(val)
        self.cs.value(1)

    def _read(self, addr):
        self.cs.value(0)
        self.sck.value(0)
        self._transfer(((addr << 1) & 0x7E) | 0x80)
        val = self._transfer(0)
        self.cs.value(1)
        return val

    def _transfer(self, data):
        res = 0
        for i in range(8):
            self.mosi.value((data >> (7 - i)) & 1)
            self.sck.value(1)
            res = (res << 1) | self.miso.value()
            self.sck.value(0)
        return res

    def _command(self, cmd):
        self._write(0x01, cmd)
        while self._read(0x01) & 0x80:
            pass

    def _anticoll(self):
        self._write(0x0E, 0x00)
        self._write(0x08, 0x93)
        self._write(0x09, 0x20)
        self._command(0x1C)
        if self._read(0x06) & 0x1F != 5:
            return self.ERR, []
        uid = []
        for i in range(4):
            uid.append(self._read(0x0A + i))
        return self.OK, uid

    def request(self, mode):
        self._write(0x0D, 0x07)
        self._write(0x08, mode)
        self._write(0x09, 0x00)
        self._command(0x1E)
        if self._read(0x06) & 0x1F != 0:
            return self.NOTAGERR, 0
        return self.OK, self._read(0x0A)

    def select(self):
        self._write(0x0E, 0x00)
        self._write(0x08, 0x93)
        self._write(0x09, 0x70)
        uid = []
        for i in range(4):
            val = self._read(0x0A + i)
            self._write(0x09, val)
            uid.append(val)
        self._command(0x1C)
        if self._read(0x06) & 0x1F != 5:
            return self.ERR, []
        return self.OK, uid

    def read_card(self):
        """读取卡片UID，返回 (status, uid_bytes)"""
        status, _ = self.request(self.REQIDL)
        if status != self.OK:
            return self.NOTAGERR, None
        status, uid = self._anticoll()
        if status != self.OK:
            return self.ERR, None
        return self.OK, uid
