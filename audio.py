import random
import time
from machine import UART
import config
# 定义全局变量 是否播放过楼层到达，是否正在播放音乐
has_played_bgmusic=False
playing1 = False
playing = False

class Audio:
    def __init__(self):
        self.uart = UART(1, baudrate=9600, tx=config.DFPLAYER_TX, rx=config.DFPLAYER_RX)
        print("UART initialized successfully:", self.uart)
    # 十进制转十六进制
    def decimal_to_hex(self,num):
        return hex(num)
    # 播放楼层音乐
    def play_music1(self,num):
        hex_num = self.decimal_to_hex(num)
        global playing
        if playing:
            return
        playing = True
        print(hex_num)
        try:
            instruction = bytearray([0x7E, 0xFF, 0x06, 0x12, 0x00, 0x00, int(hex_num, 16), 0xEF])
            self.uart.write(instruction)
            time.sleep(2)
        except Exception as e:
            print("播放音频时出错:", e)
        finally:
            playing = False
    # 播放儿歌
    def play_music2(self,num):
        hex_num = self.decimal_to_hex(num)
        global playing1,has_played_floor,start_time
        if playing1:
           
            return
        playing1 = True
        has_played_floor=True
        try:
            instruction = bytearray([0x7E, 0xFF, 0x06, 0x12, 0x00, 0x00, int(hex_num, 16), 0xEF])
            self.uart.write(instruction)
           
        except Exception as e:
            print("播放音频时出错:", e)
        finally:
            playing1 = False    
    # 播放背景音乐
    def play_bgmusic(self):
            global playing1,has_played_bgmusic,start_time  
            has_played_bgmusic = True
            random_number = random.randint(5, 28)
            instruction = bytearray([0x7E, 0xFF, 0x06, 0x12, 0x00, 0x00, random_number, 0xEF])
            print("Sending instruction:", " ".join("{:02X}".format(byte) for byte in instruction))
            self.uart.write(instruction)
            #time.sleep(300)
            
            

    # 设置音量
    def set_volume(self, vol):
        vol = max(0, min(30, vol))
        instruction = bytearray([0x7E, 0xFF, 0x06, 0x06, 0x00, 0x00, vol, 0xEF])
        self.uart.write(instruction)
        print('Volume set to:', vol)

