from machine import I2C, Pin
from ssd1306 import SSD1306_I2C
import config
i2c = I2C(0, scl=Pin(config.I2C_SCL), sda=Pin(config.I2C_SDA), freq=400000)
oled = SSD1306_I2C(128, 32, i2c)

# 简单测试
oled.fill(0)
oled.text("Test", 0, 0, 1)
oled.show()
