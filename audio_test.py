import _thread
import random
import time
from machine import UART
# 定义全局变量 是否播放过楼层到达，是否正在播放音乐
has_played_floor= False
has_played_bgmusic=False
playing1 = False
is_loop = False
is_open = False
is_arrive = False
current_floor = 1
set_floor = -1
playing = False
uart = UART(1, baudrate=9600, tx=13, rx=12)
print("UART initialized successfully:", uart)

# 播放音乐
def play_music(text, vol=0.5):
    play_wav_with_volume1(text)

# 播放楼层音乐
def play_music1(num=1):
    play_wav_with_volume1(num)

# 播放儿歌
def play_music2(num=1):
    play_wav_with_volume2(num)

# 十进制转十六进制
def decimal_to_hex(num):
    return hex(num)

# 播放音频
def play_wav_with_volume1(num):
    hex_num = decimal_to_hex(num)
    global playing
    if playing:
        return
    playing = True
    print(hex_num)
    try:
        instruction = bytearray([0x7E, 0xFF, 0x06, 0x12, 0x00, 0x00, int(hex_num, 16), 0xEF])
        uart.write(instruction)
        time.sleep(2)
    except Exception as e:
        print("播放音频时出错:", e)
    finally:
        playing = False
       

# 播放音频（儿歌）
def play_wav_with_volume2(num):
    hex_num = decimal_to_hex(num)
    global playing1,has_played_floor,start_time
    if playing1:
       
        return
    playing1 = True
    has_played_floor=True
    try:
        instruction = bytearray([0x7E, 0xFF, 0x06, 0x12, 0x00, 0x00, int(hex_num, 16), 0xEF])
        uart.write(instruction)
       
    except Exception as e:
        print("播放音频时出错:", e)
    finally:
        playing1 = False
        has_played_floor = True
        start_time=time.time()
        print(f"到达时间{start_time}:")

# 播放背景音乐
def play_bgmusic():
        global playing1,has_played_bgmusic,start_time  
        has_played_bgmusic = True
        random_number = random.randint(50, 72)
        instruction = bytearray([0x7E, 0xFF, 0x06, 0x12, 0x00, 0x00, random_number, 0xEF])
        print("Sending instruction:", " ".join("{:02X}".format(byte) for byte in instruction))
        uart.write(instruction)
        #time.sleep(300)
        
        

# 初始化
play_music1(30)