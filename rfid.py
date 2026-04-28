# RC522 测试 - 引脚: SDA=16, SCK=15, MOSI=2, MISO=4, RST=17
from machine import Pin, SPI
import utime

SDA = 16 # CS
SCK = 15 # SCK
MOSI = 2 # MOSI
MISO = 4 # MISO
RST = 21 # RST

# SPI 初始化
spi = SPI(
 1,
 baudrate=1000000,
 polarity=0,
 phase=0,
 sck=Pin(SCK),
 mosi=Pin(MOSI),
 miso=Pin(MISO)
)
print("SPI1 OK sck=%d mosi=%d miso=%d" % (SCK, MOSI, MISO))

# RC522 初始化
try:
     from mfrc522 import MFRC522
     rdr = MFRC522(Pin(SCK), Pin(MOSI), Pin(MISO), Pin(RST), Pin(SDA))
     print("MFRC522 OK sda=%d sck=%d mosi=%d miso=%d rst=%d" % (SDA, SCK, MOSI, MISO, RST))
except Exception as e:
     print("mfrc522 ERR:", e)
     raise

print("\n=== 刷卡测试 ===")
LED = Pin(13, Pin.OUT)
LED.value(0)

while True:
 try:
     stat, uid = rdr.read_card()
     if stat == rdr.OK and uid:
         uid_str = ':'.join('%02X' % b for b in uid)
         print(">>> CARD: " + uid_str)
         for _ in range(3):
             LED.toggle()
             utime.sleep_ms(100)
             LED.value(0)
             utime.sleep_ms(80)
 except Exception as e:
     print("Err:", e)
 utime.sleep_ms(500)
