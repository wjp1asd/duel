# boot.py - 启动配置
# 此文件在 main.py 之前自动执行

import machine
import utime

# 禁用启动消息（可选）
# machine.freq(160000000)  # ESP32-C3 默认 160MHz

print("Boot complete")
