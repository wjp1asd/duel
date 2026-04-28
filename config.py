# config.py - 项目配置

# === WiFi 配置 ===
WIFI_SSID = "YourWiFiSSID"
WIFI_PASSWORD = "YourWiFiPassword"

# === App 通信配置 ===
APP_HOST = "192.168.1.100"  # Android App IP（动态获取或固定）
APP_PORT = 8888

# === I2C 配置 (OLED) ===
I2C_SDA = 5
I2C_SCL = 17
I2C_FREQ = 400000

# # === I2S 配置 (MAX98357A 音频) ===
# I2S_BCLK = 12   # 位时钟
# I2S_LRC = 14    # 左右声道时钟
# I2S_DIN = 13    # 数据输入

DFPLAYER_UART = 1
DFPLAYER_TX = 13
DFPLAYER_RX = 12
DFPLAYER_BUSY_PIN = None  # 可选 BUSY 引脚，不接则留 None


# === SPI 配置 (RC522 射频卡) ===
SPI_SCK = 15
SPI_MOSI = 2
SPI_MISO = 4
SPI_CS = 16
RFID_RST = 0

# === OLED 配置 ===
OLED_WIDTH = 128
OLED_HEIGHT = 32
# === 舵机 配置 ===
SERVO_PIN =27