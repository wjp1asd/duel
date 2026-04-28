# duel_net.py - WiFi + App 通信模块
import network
import socket
import config
import utime

class duel_net:
    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.sock = None
        self.connected = False

    def connect_wifi(self, timeout=10):
        """连接 WiFi"""
        print(f"Connecting to {config.WIFI_SSID}...")
        self.wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        start = utime.time()
        while not self.wlan.isconnected():
            if utime.time() - start > timeout:
                print("WiFi connection timeout")
                return False
            utime.sleep(1)
        print(f"WiFi connected: {self.wlan.ifconfig()[0]}")
        return True

    def connect_app(self):
        """连接 Android App"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((config.APP_HOST, config.APP_PORT))
            self.connected = True
            print(f"Connected to App: {config.APP_HOST}:{config.APP_PORT}")
            return True
        except Exception as e:
            print(f"App connection failed: {e}")
            return False

    def send(self, data):
        """发送数据到 App"""
        if self.connected and self.sock:
            try:
                if isinstance(data, str):
                    data = data.encode()
                self.sock.send(data)
                return True
            except Exception as e:
                print(f"Send error: {e}")
                self.connected = False
        return False

    def recv(self, bufsize=1024):
        """接收数据"""
        if self.connected and self.sock:
            try:
                return self.sock.recv(bufsize)
            except:
                pass
        return None

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
        self.connected = False
