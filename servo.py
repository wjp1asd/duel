from machine import Pin, PWM
import time

# ========== 配置区 ==========
SERVO_PIN = 15        # 修改为你的实际引脚
FREQ = 50             # 标准舵机频率50Hz

# 不同舵机的脉宽范围可能不同
MIN_US = 500          # 0度脉宽 (0.5ms)
MAX_US = 2500         # 180度脉宽 (2.5ms)
# 如果无反应，尝试改为: MIN_US=1000, MAX_US=2000 (SG90常见)

# 计算duty (ESP32 duty范围0-1023对应0%-100%)
def us_to_duty(us):
    return int(us / 20000 * 1023)  # 20ms周期 = 20000us

# 初始化
servo = PWM(Pin(SERVO_PIN), freq=FREQ)

print(f"舵机测试 - 引脚GPIO{SERVO_PIN}, 频率{FREQ}Hz")
print(f"0度 duty={us_to_duty(MIN_US)}, 180度 duty={us_to_duty(MAX_US)}")

# 测试1: 直接输出中间位置
print("\n测试1: 90度位置")
servo.duty(us_to_duty(1500))  # 1500us = 90度
time.sleep(1)

# 测试2: 缓慢扫描
print("测试2: 0->180->0扫描")
try:
    while True:
        # 0度
        print(" -> 0度")
        servo.duty(us_to_duty(MIN_US))
        time.sleep(1)
        
        # 90度
        print(" -> 90度")
        servo.duty(us_to_duty(1500))
        time.sleep(1)
        
        # 180度
        print(" -> 180度")
        servo.duty(us_to_duty(MAX_US))
        time.sleep(1)
        
        # 回90度
        print(" -> 90度")
        servo.duty(us_to_duty(1500))
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\n停止")
    servo.deinit()  # 释放PWM 