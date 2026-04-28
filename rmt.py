from machine import Pin, SPI
import utime
SDA,SCK,MOSI,MISO,RST=16,15,2,4,21
spi=SPI(1,baudrate=1000000,polarity=0,phase=0,sck=Pin(SCK),mosi=Pin(MOSI),miso=Pin(MISO))
cs=Pin(SDA,Pin.OUT,value=1)
rst_pin=Pin(RST,Pin.OUT,value=1)
def wr(reg,val):
 cs.value(0);spi.write(bytes([(reg<<1)&0x7E,val]));cs.value(1)
def rd(reg):
 cs.value(0);spi.write(bytes([((reg<<1)&0x7E)|0x80]));r=spi.read(1);cs.value(1);return r[0]
def rdbuf(reg,n):
 cs.value(0);spi.write(bytes([((reg<<1)&0x7E)|0x80]));data=spi.read(n);cs.value(1);return data
rst_pin.value(0);utime.sleep_ms(50);rst_pin.value(1);utime.sleep_ms(50)
wr(0x01,0x0F);utime.sleep_ms(50)
wr(0x14,0x03);wr(0x2A,0x8D);wr(0x2B,0x4E);wr(0x2D,0x87);wr(0x15,0x40);wr(0x11,0x3D);wr(0x0A,0x07)
print("RC522 OK ver=0x%02X"%rd(0x37))
def wrcmd(cmd,send=b''):
 wr(0x04,0x7F);wr(0x08,0x80)
 for b in send:wr(0x09,b)
 wr(0x01,cmd)
 for _ in range(200):
 if rd(0x04)&0x31:break
 utime.sleep_ms(1)
 return rd(0x06)
def read_block(block,key_a=b'\xFF\xFF\xFF\xFF\xFF\xFF'):
 wrcmd(0x26,bytes([0x26]));utime.sleep_ms(2)
 wr(0x08,0x80);wr(0x09,0x93);wr(0x09,0x20);wr(0x01,0x93);utime.sleep_ms(5)
 uid=rdbuf(0x09,5)[:4]
 wr(0x08,0x80);wr(0x09,0x93);wr(0x09,0x70)
 for b in uid:wr(0x09,b)
 wr(0x01,0x93);utime.sleep_ms(5)
 wr(0x08,0x80);wr(0x09,0x60);wr(0x09,block)
 for b in key_a:wr(0x09,b)
 for b in uid:wr(0x09,b)
 wr(0x01,0x60);utime.sleep_ms(10)
 if rd(0x06)&0x08:return None
 wr(0x08,0x80);wr(0x09,0x30);wr(0x09,block);wr(0x01,0x30);utime.sleep_ms(10)
 n=rd(0x0A)&0x0F
 if n>=16:return rdbuf(0x09,16)
 return None
print("\n===刷卡测试===")
while True:
 err=wrcmd(0x26,bytes([0x26]))
 if err&0x13:utime.sleep_ms(200);continue
 utime.sleep_ms(5)
 wr(0x08,0x80);wr(0x09,0x93);wr(0x09,0x20);wr(0x0A,0x00);wr(0x01,0x93);utime.sleep_ms(10)
 uid=rdbuf(0x09,5)
 if len(uid)>=5 and uid[4]==uid[0]^uid[1]^uid[2]^uid[3]:
 print("\nUID: "+uid[:4].hex().upper())
 for blk in range(1,7):
 data=read_block(blk)
 if data:
 print("块%d: %s"%(blk,data.hex()))
 try:
 txt=data.decode('utf-8',errors='ignore').strip('\x00')
 if txt:print(" 文本: %s"%repr(txt))
 except:pass
 else:print("块%d: 失败"%blk)
 utime.sleep_ms(2000)
 utime.sleep_ms(100)
