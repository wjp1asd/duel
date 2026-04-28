from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import config
import time
import random

# 7段数码管段位表 (a,b,c,d,e,f,g)
# 标准顺序：0=a, 1=b, 2=c, 3=d, 4=e, 5=f, 6=g
SEGS = [
    '1111110',  # 0: a,b,c,d,e,f
    '0110000',  # 1: b,c
    '1101101',  # 2: a,b,g,e,d
    '1111001',  # 3: a,b,c,d,g
    '0110011',  # 4: f,g,b,c
    '1011011',  # 5: a,f,g,c,d
    '1011111',  # 6: a,f,g,c,d,e
    '1110000',  # 7: a,b,c
    '1111111',  # 8: a,b,c,d,e,f,g
    '1111011',  # 9: a,b,c,d,f,g
]
class Oled_big:
    def __init__(self):
        self.i2c = I2C(scl=Pin(config.I2C_SCL), sda=Pin(config.I2C_SDA), freq=400000)
        self.oled = SSD1306_I2C(128, 32, self.i2c)
    def _char_width(self, ch):
        if ch in CN:
            return 16
        return 6  # ASCII: 5col + 1px spacing
    
    def draw_7seg(self, d, x, y, w, h):
        seg = SEGS[d]
        bw = max(3, w // 5)
        bh = max(3, h // 6)
        mid = h // 2
        
        # a - 上横
        if seg[0] == '1': 
            self.oled.fill_rect(x + bw, y, w - 2*bw, bh, 1)
        # b - 右上竖
        if seg[1] == '1': 
            self.oled.fill_rect(x + w - bw, y + bh, bw, mid - bh, 1)
        # c - 右下竖
        if seg[2] == '1': 
            self.oled.fill_rect(x + w - bw, y + mid, bw, mid - bh, 1)
        # d - 下横
        if seg[3] == '1': 
            self.oled.fill_rect(x + bw, y + h - bh, w - 2*bw, bh, 1)
        # e - 左下竖
        if seg[4] == '1': 
            self.oled.fill_rect(x, y + mid, bw, mid - bh, 1)
        # f - 左上竖
        if seg[5] == '1': 
            self.oled.fill_rect(x, y + bh, bw, mid - bh, 1)
        # g - 中横
        if seg[6] == '1': 
            self.oled.fill_rect(x + bw, y + mid - bh//2, w - 2*bw, bh, 1)

    def show_number(self, num):
        s = str(int(num))
        digits = [int(c) for c in s]
        n = len(digits)
        
        gap = 2
        dw = (128 - gap * (n - 1)) // n
        dh = 30
        
        ox = (128 - (n * dw + (n - 1) * gap)) // 2
        oy = (32 - dh) // 2

        self.oled.fill(0)
        for i, d in enumerate(digits):
            self.draw_7seg(d, ox + i * (dw + gap), oy, dw, dh)
        self.oled.show()
    def show_text(self, text, x=0, y=0, clear=True):
            """显示文本"""
            if clear:
                self.oled.fill(0)
            self.oled.text(text, x, y, 1)
            self.oled.show()
    def show_big_text(self, text, x=0, y=0, scale=2, clear=True):
            """显示放大文字
            text: 字符串
            x, y: 起始坐标
            scale: 放大倍数（2=16x16, 3=24x24...）
            """
            if clear:
                self.oled.fill(0)
            ox = x
            for ch in text:
                code = ord(ch)
                if 32 <= code <= 47:
                    idx = (code - 32) * 8
                    glyph = FONT8[idx:idx + 8]
                elif 48 <= code <= 57:
                    # 数字用 7 段管显示
                    d = code - 48
                    dw = 8 * scale
                    dh = 10 * scale
                    # 临时画数字
                    self._draw_big_digit(d, ox, y, 8 * scale, 10 * scale)
                    ox += dw + scale
                    continue
                else:
                    glyph = bytes([0] * 8)  # 未知字符留空
                for row in range(8):
                    byte = glyph[row]
                    for col in range(8):
                        if byte & (0x80 >> col):
                            self.oled.fill_rect(
                                ox + col * scale,
                                y + row * scale,
                                scale, scale, 1
                            )
                ox += 8 * scale + scale
            self.oled.show()
    def clear(self):
        self.oled.fill(0)
        self.oled.show()
    def show_number_slot_machine(self, target_num, duration_ms=2000):
        """
        老虎机效果：所有位同时快速滚动，从左到右依次停止
        target_num: 目标数字
        duration_ms: 总动画时间（默认2秒）
        """
        s = str(int(target_num))
        n = len(s)
        target_digits = [int(c) for c in s]
        
        # 布局计算
        gap = 2
        dw = (128 - gap * (n - 1)) // n
        dh = 30
        ox = (128 - (n * dw + (n - 1) * gap)) // 2
        oy = (32 - dh) // 2
        
        # 动画阶段配置
        # 阶段1：全速滚动（0-60%时间）
        # 阶段2：从左到右依次停止（60%-100%时间）
        spin_duration = int(duration_ms * 0.6)
        stop_duration = duration_ms - spin_duration
        
        # 每位停止的时间点（从左到右依次停止）
        stop_times = []
        for i in range(n):
            # 线性分布停止时间，或指数分布（左边先停）
            t = spin_duration + (stop_duration * i // n)
            stop_times.append(t)
        
        # 滚动速度（每位可以不同，制造混乱感）
        speeds = [random.randint(80, 150) for _ in range(n)]  # ms per change
        
        # 上次变化时间
        last_change = [0] * n
        # 当前显示值
        current_display = [random.randint(0, 9) for _ in range(n)]
        # 是否已停止
        stopped = [False] * n
        
        start_time = time.ticks_ms()
        
        while True:
            elapsed = time.ticks_diff(time.ticks_ms(), start_time)
            
            # 检查是否全部停止
            if all(stopped):
                break
            
            # 更新每位数字
            for i in range(n):
                if stopped[i]:
                    continue
                
                # 检查是否到达停止时间
                if elapsed >= stop_times[i]:
                    # 减速效果：最后几个数快速闪过然后定格
                    if elapsed - stop_times[i] < 100:  # 停止前100ms的减速动画
                        # 快速闪过2-3个数后定格
                        if (elapsed // 30) % 2 == 0:
                            current_display[i] = random.randint(0, 9)
                        else:
                            current_display[i] = target_digits[i]
                    else:
                        # 定格
                        current_display[i] = target_digits[i]
                        stopped[i] = True
                else:
                    # 全速滚动阶段
                    if elapsed - last_change[i] > speeds[i]:
                        current_display[i] = random.randint(0, 9)
                        last_change[i] = elapsed
                        # 随机改变速度，更有混乱感
                        speeds[i] = random.randint(50, 120)
            
            # 绘制
            self.oled.fill(0)
            for i in range(n):
                self.draw_7seg(current_display[i], ox + i * (dw + gap), oy, dw, dh)
            self.oled.show()
            
            time.sleep_ms(15)  # ~66fps
        
        # 最终定格确保正确
        self.oled.fill(0)
        for i in range(n):
            self.draw_7seg(target_digits[i], ox + i * (dw + gap), oy, dw, dh)
        self.oled.show()   
# 测试所有数字
#show_number(oled, 4000)
    