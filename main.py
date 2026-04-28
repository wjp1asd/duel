# main.py - Duel System + WS2812 LED Control (GPIO26	 + GPIO25)
import network
import socket
import re
import utime
from machine import Pin
# from ir_rx.nec import NEC8
import random
try:
    import neopixel
    HAS_NEOPIXEL = True
except Exception as e:
    print("neopixel err:", e)
    HAS_NEOPIXEL = False

try:
    from oled_big import Oled_big
    from audio import Audio
    HAS_OLED  = True
    HAS_AUDIO = True
except Exception as e:
    print("Module load error:", e)
    HAS_OLED  = False
    HAS_AUDIO = False

# === WS2812 配置 ===
LED_N     = 30   # 每条灯带灯珠数量，按需修改
LED_PIN1  = 27   # 灯带1 GPIO
LED_PIN2  = 14   # 灯带2 GPIO
LED_BRIGHT = 0.6  # 全局亮度 0.0-1.0

# === LED 状态 ===
led1_mode  = "off"; led2_mode  = "off"
led1_r = 0; led1_g = 0; led1_b = 0
led2_r = 0; led2_g = 0; led2_b = 0
led1_bright = 1.0; led2_bright = 1.0
rainbow_step1 = 0; rainbow_step2 = 0
breath_v1 = 0.0; breath_v2 = 0.0
breath_dir1 = 1; breath_dir2 = 1
strip = 2  # 0=左, 1=右, 2=同时
led_flash = 0  # 音乐闪烁计数
led_flash_color = (0, 0, 255)  # 闪烁颜色 RGB
led_flash_count = 0  # 总闪烁帧数

def led_music_flash(frames=30, color=(0, 0, 255)):
    """播放音乐时触发LED闪烁"""
    global led_flash, led_flash_color, led_flash_count
    led_flash = frames
    led_flash_count = frames
    led_flash_color = color
    print("[LED flash] %d frames" % frames)

# === LED 对象 ===
np1 = None; np2 = None

def _np(pin, n):
    p = Pin(pin, Pin.OUT)
    p.value(0)
    return neopixel.NeoPixel(p, n)

def _apply(np, r, g, b):
    np.fill((int(r * LED_BRIGHT), int(g * LED_BRIGHT), int(b * LED_BRIGHT)))
    np.write()

def _rainbow(np, step):
    n = len(np)
    for i in range(n):
        h = (i * 256 // n + step) & 255
        if h < 85:
            np[i] = (int(LED_BRIGHT * (h * 3 // 85 * 85 // 3)), int(LED_BRIGHT * (255 - h * 3 // 85)), 0)
        elif h < 170:
            h -= 85
            np[i] = (0, int(LED_BRIGHT * (h * 3 // 85)), int(LED_BRIGHT * (255 - h * 3 // 85)))
        else:
            h -= 170
            np[i] = (int(LED_BRIGHT * (255 - h * 3 // 85)), 0, int(LED_BRIGHT * (h * 3 // 85)))
    np.write()

def _breath(np, v, r, g, b):
    np.fill((int(r * LED_BRIGHT * v), int(g * LED_BRIGHT * v), int(b * LED_BRIGHT * v)))
    np.write()

def led_tick1():
    global rainbow_step1, breath_v1, breath_dir1, led_flash
    # 音乐闪烁优先
    if led_flash > 0 and np1:
        flash_on = (led_flash % 6) < 3  # 每6帧切换，约100ms周期
        if flash_on:
            np1.fill(led_flash_color)
        else:
            np1.fill((0, 0, 0))
        np1.write()
        led_flash -= 1
        return
    # 普通模式
    if led1_mode == "solid":
        _apply(np1, led1_r, led1_g, led1_b)
    elif led1_mode == "rainbow":
        _rainbow(np1, rainbow_step1)
        rainbow_step1 = (rainbow_step1 + 2) & 255
    elif led1_mode == "breath":
        _breath(np1, breath_v1, led1_r, led1_g, led1_b)
        breath_v1 += 0.04 * breath_dir1
        if breath_v1 >= 1.0 or breath_v1 <= 0.05:
            breath_dir1 *= -1
    else:  # off
        if np1: np1.fill((0, 0, 0)); np1.write()

def led_tick2():
    global rainbow_step2, breath_v2, breath_dir2, led_flash
    # 音乐闪烁优先
    if led_flash > 0 and np2:
        flash_on = (led_flash % 6) < 3
        if flash_on:
            np2.fill(led_flash_color)
        else:
            np2.fill((0, 0, 0))
        np2.write()
        led_flash -= 1
        return
    if led2_mode == "solid":
        _apply(np2, led2_r, led2_g, led2_b)
    elif led2_mode == "rainbow":
        _rainbow(np2, rainbow_step2)
        rainbow_step2 = (rainbow_step2 + 2) & 255
    elif led2_mode == "breath":
        _breath(np2, breath_v2, led2_r, led2_g, led2_b)
        breath_v2 += 0.04 * breath_dir2
        if breath_v2 >= 1.0 or breath_v2 <= 0.05:
            breath_dir2 *= -1
    else:
        if np2: np2.fill((0, 0, 0)); np2.write()

# === 全局状态 ===
lifevalue   = 4000
musicindex    = 5
volume      = 20
music_queue = []
ir_cmd      = None
ap_ip       = "0.0.0.0"
AP_SSID     = "DuelAP"
AP_PASSWORD = ""

# === 外设对象 ===
oled  = None
audio = None

def start_ap():
    global ap_ip
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID)
    ap_ip = ap.ifconfig()[0]
    print("AP:", AP_SSID, " -> http://" + ap_ip)

def respond(sock, code, ct, body):
    if isinstance(body, str):
        body = body.encode("utf-8")
    hdr = ("HTTP/1.1 {}\r\nContent-Type: {}\r\nContent-Length: {}\r\n"
           "Connection: close\r\nAccess-Control-Allow-Origin: *\r\n\r\n").format(
               code, ct, len(body))
    try:
        sock.send(hdr.encode())
        sock.send(body)
    except:
        pass

def handle(path, method, body, addr):
    global lifevalue, music_queue, ir_cmd, volume, led_flash, led_flash_color
    global led1_mode, led2_mode, led1_r, led1_g, led1_b
    global led2_r, led2_g, led2_b, strip

    p = path.strip()

    if method == "GET" and p == "/lp":
        return "200", "application/json", '{"lp":%d,"ip":"%s"}' % (lifevalue, ap_ip)
    
    if method == "POST" and p == "/up":
         t =musicindex-1
         music_queue.append(t)
         return "302", "text/plain", ""
    
    if method == "POST" and p == "/down":
         t =musicindex+1
         music_queue.append(t)
         return "302", "text/plain", ""
    
    if method == "POST" and p == "/lp":
        m = re.search(r"lp=(\d+)", body)
        if m:
            lifevalue = max(0, min(9999, int(m.group(1))))
            if oled:
                try: oled.show_number_slot_machine(lifevalue)
                except: pass
            if audio:
                music_queue.append(2)
        return "302", "text/plain", ""

    if method == "POST" and p == "/lp_delta":
        m = re.search(r"delta=(-?\d+)", body)
        if m:
            lifevalue = max(0, min(9999, lifevalue + int(m.group(1))))
            if oled:
                try: oled.show_number_slot_machine(lifevalue)
                except: pass
            if audio:
                music_queue.append(2)
        return "302", "text/plain", ""

    m = re.match(r"/music/(\d+)", p)
    if m:
        t = int(m.group(1))
        if 1 <= t <= 30:
            music_queue.append(t)
        return "302", "text/plain", ""

    if method == "POST" and p == "/volume":
        m = re.search(r"n=(\d+)", body)
        if m and audio:
            try:
                vol = int(m.group(1))
                audio.set_volume(vol)
                volume = vol
            except Exception as e:
                print("Vol err:", e)
        return "302", "text/plain", ""

    if method == "GET" and p == "/volume":
        return "200", "application/json", '{"volume":%d}' % volume

    # LED 控制 POST /led
    if method == "POST" and p == "/led":
        m = re.search(r"strip=(\d)", body)
        m2 = re.search(r"mode=(\w+)", body)
        m3 = re.search(r"r=(\d+)", body)
        m4 = re.search(r"g=(\d+)", body)
        m5 = re.search(r"b=(\d+)", body)
        if m:  strip = int(m.group(1))
        if m2:
            mode = m2.group(1)
            if strip == 0 or strip == 2:
                led1_mode = mode
            if strip == 1 or strip == 2:
                led2_mode = mode
        if m3 and m4 and m5:
            r = int(m3.group(1)); g = int(m4.group(1)); b = int(m5.group(1))
            if strip == 0 or strip == 2:
                led1_r = r; led1_g = g; led1_b = b
            if strip == 1 or strip == 2:
                led2_r = r; led2_g = g; led2_b = b
        return "302", "text/plain", ""

    # LED 查询 GET /led
    if method == "GET" and p == "/led":
        return "200", "application/json", (
            '{"s1":{"mode":"%s","r":%d,"g":%d,"b":%d},'
            '"s2":{"mode":"%s","r":%d,"g":%d,"b":%d},'
            '"strip":%d}') % (
            led1_mode, led1_r, led1_g, led1_b,
            led2_mode, led2_r, led2_g, led2_b,
            strip)

    if method == "POST" and p == "/servo":
        return "302", "text/plain", ""

    if method == "GET" and p == "/ir":
        cmd = ir_cmd
        ir_cmd = None
        s = '"0x%02X"' % cmd if cmd is not None else "null"
        return "200", "application/json", '{"cmd":%s}' % s

    html = (HTML_PAGE
        .replace("__LP__", str(lifevalue))
        .replace("__VOL__", str(volume))
        .replace("__LED_MODE__", led1_mode)
        .replace("__LED_R__", str(led1_r))
        .replace("__LED_G__", str(led1_g))
        .replace("__LED_B__", str(led1_b)))
    return "200", "text/html; charset=utf-8", html

HTML_PAGE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Duel Control</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0f0f1a;color:#e0e0e0;
  min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:20px}
h1{font-size:1.5em;margin-bottom:16px;color:#ffd700;text-shadow:0 0 12px rgba(255,215,0,.4)}
.card{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:12px;
  padding:18px;width:100%;max-width:400px;margin-bottom:14px}
.lp{font-size:3em;font-weight:bold;text-align:center;color:#ff4d4d;
  text-shadow:0 0 16px rgba(255,77,77,.5);background:#111;padding:10px 20px;
  border-radius:8px;margin-bottom:10px;letter-spacing:4px}
.row{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-bottom:8px}
button{flex:1;min-width:70px;padding:9px 4px;border:none;border-radius:8px;
  font-size:.86em;cursor:pointer;font-weight:bold;transition:all .15s}
.lp-btn{background:#2a2a4a;color:#e0e0e0}
.lp-btn:hover{background:#3a3a6a}
.lp-btn.g{background:#14332a;color:#6fcf97}
.lp-btn.r{background:#4a1b1b;color:#eb5757}
.mu{background:#1b2a4a;color:#74b9ff}
.mu:hover{background:#2a3a6a}
.sv{background:#4a2a1b;color:#f2994a}
.sv:hover{background:#6a3a2b}
.color-btn{background:#1a1a2e;border:2px solid #2a2a4a;color:#fff;padding:7px 2px}
.color-btn:hover{border-color:#555}
.color-btn.active{border-color:#ffd700}
.color-btn.on{background:#2a2a4a;border-color:#ffd700}
#t{position:fixed;top:10px;right:10px;background:#1b4332;color:#6fcf97;
  padding:7px 14px;border-radius:6px;font-size:.84em;display:none;transition:opacity:.3s}
.info{font-size:.72em;color:#555;text-align:center;margin-top:8px}
.led-strip{display:flex;gap:6px;margin-bottom:10px}
.strip-btn{padding:6px 12px;border:none;border-radius:6px;font-size:.8em;
  cursor:pointer;background:#2a2a4a;color:#aaa;font-weight:bold}
.strip-btn.active{background:#ffd700;color:#111}
.mode-row{display:flex;gap:6px;margin-bottom:10px}
.mode-btn{padding:7px 4px;flex:1;border:none;border-radius:6px;font-size:.78em;
  cursor:pointer;background:#2a2a4a;color:#aaa;font-weight:bold;text-align:center}
.mode-btn.active{background:#4a2a8a;color:#c9a0ff}
.color-pick{margin-bottom:10px}
.color-pick label{font-size:.8em;color:#aaa;margin-right:6px}
.color-pick input[type=range]{flex:1;accent-color:#ffd700}
.color-pick span{font-size:.8em;color:#fff;min-width:30px;text-align:center}
.preset-row{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px}
</style>
</head>
<body>
<h1>Duel System</h1>
<h2>Must Design</h2>
<div class="card">
  <div class="lp" id="lp">LP: __LP__</div>
  <div class="row">
    <button class="lp-btn g" onclick="delta(+1000)">+1000</button>
    <button class="lp-btn r" onclick="delta(-1000)">-1000</button>
    <button class="lp-btn g" onclick="delta(+500)">+500</button>
    <button class="lp-btn r" onclick="delta(-500)">-500</button>
    <button class="lp-btn g" onclick="delta(+200)">+200</button>
    <button class="lp-btn r" onclick="delta(-200)">-200</button>
    <button class="lp-btn g" onclick="delta(+100)">+100</button>
    <button class="lp-btn r" onclick="delta(-100)">-100</button>
  </div>
  <div class="row">
    
    <button class="lp-btn" onclick="delta(50)">+50</button>
    <button class="lp-btn" onclick="delta(-50)">-50</button>
    <button class="lp-btn" onclick="delta(10)">+10</button>
    <button class="lp-btn" onclick="delta(-10)">-10</button>
     <button class="lp-btn" onclick="delta(5)">+5</button>
    <button class="lp-btn" onclick="delta(-5)">-5</button>
     <button class="lp-btn" onclick="delta(1)">+1</button>
    <button class="lp-btn" onclick="delta(-1)">-1</button>
    <button class="lp-btn" onclick="setlp(4000)">RESET</button>
  </div>
</div>
<div class="card">
  <div style="text-align:center;margin-bottom:8px;color:#aaa;font-size:.85em">Volume</div>
  <div class="row">
    <button class="mu" onclick="vol(-5)">-5</button>
    <button class="mu" onclick="vol(-1)">-1</button>
    <span id="vol" style="flex:1;text-align:center;line-height:36px;font-weight:bold;color:#74b9ff">__VOL__</span>
    <button class="mu" onclick="vol(1)">+1</button>
    <button class="mu" onclick="vol(5)">+5</button>
  </div>
</div>
<div class="card">
<div style="text-align:center;margin-bottom:8px;color:#aaa;font-size:.85em">Music</div>

  <div class="row">
    <button class="mu" onclick="mu(1)">BGM</button>
    <button class="mu" onclick="mu(2)">ATK</button>
    <button class="mu" onclick="mu(3)">Draw</button>
    <button class="mu" onclick="up()">UP</button>
    <button class="mu" onclick="down()">DOWN</button>
    <button class="mu" onclick="mu(5)">Rand</button>
  </div>
</div>

<div class="card">
<div style="text-align:center;margin-bottom:8px;color:#aaa;font-size:.85em">Action</div>
  <div class="row">
    <button class="sv" onclick="sv()">CLAW</button>
  </div>
</div>



<div class="card">
  <div style="text-align:center;margin-bottom:10px;color:#ffd700;font-size:.9em;font-weight:bold">LED Strip</div>
  <div class="led-strip">
    <button class="strip-btn active" id="btn-s0" onclick="setStrip(0)">GPIO33</button>
    <button class="strip-btn" id="btn-s1" onclick="setStrip(1)">GPIO25</button>
    <button class="strip-btn" id="btn-s2" onclick="setStrip(2)">BOTH</button>
  </div>
  <div class="mode-row">
    <button class="mode-btn active" id="btn-off" onclick="setMode('off')">OFF</button>
    <button class="mode-btn" id="btn-solid" onclick="setMode('solid')">SOLID</button>
    <button class="mode-btn" id="btn-rainbow" onclick="setMode('rainbow')">RAINBOW</button>
    <button class="mode-btn" id="btn-breath" onclick="setMode('breath')">BREATH</button>
  </div>
  <div class="preset-row">
    <button class="color-btn" style="background:#ff0000" onclick="setColor(255,0,0)">R</button>
    <button class="color-btn" style="background:#ff8800" onclick="setColor(255,136,0)">O</button>
    <button class="color-btn" style="background:#ffff00" onclick="setColor(255,255,0)">Y</button>
    <button class="color-btn" style="background:#00ff00" onclick="setColor(0,255,0)">G</button>
    <button class="color-btn" style="background:#00ffff" onclick="setColor(0,255,255)">C</button>
    <button class="color-btn" style="background:#0088ff" onclick="setColor(0,136,255)">B</button>
    <button class="color-btn" style="background:#8800ff" onclick="setColor(136,0,255)">P</button>
    <button class="color-btn" style="background:#ff00ff" onclick="setColor(255,0,255)">M</button>
    <button class="color-btn" style="background:#ffffff" onclick="setColor(255,255,255)">W</button>
    <button class="color-btn" style="background:#ff0044" onclick="setColor(255,0,68)">RD</button>
  </div>
  <div class="color-pick" id="colorPick">
    <div class="row" style="margin-bottom:4px">
      <label>R</label>
      <input type="range" id="r" min="0" max="255" value="__LED_R__">
      <span id="rv">__LED_R__</span>
    </div>
    <div class="row" style="margin-bottom:4px">
      <label>G</label>
      <input type="range" id="g" min="0" max="255" value="__LED_G__">
      <span id="gv">__LED_G__</span>
    </div>
    <div class="row">
      <label>B</label>
      <input type="range" id="b" min="0" max="255" value="__LED_B__">
      <span id="bv">__LED_B__</span>
    </div>
  </div>
</div>

<div id="t"></div>
<div class="info" id="info">--</div>

<script>
var lp = __LP__;
var curStrip = 2;
var curMode = '__LED_MODE__';
var curR = __LED_R__, curG = __LED_G__, curB = __LED_B__;
function $(id){return document.getElementById(id);}
function t(msg){var e=$('t');e.textContent=msg;e.style.display='block';setTimeout(function(){e.style.display='none'},1800);}
function r(){fetch('/lp').then(function(x){return x.json()}).then(function(d){lp=d.lp;$('lp').textContent='LP: '+lp;$('info').textContent=d.ip}).catch(function(){})}
function delta(d){lp=Math.max(0,Math.min(9999,lp+d));$('lp').textContent='LP: '+lp;
  fetch('/lp_delta',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'delta='+d}).then(function(){t('LP: '+lp)}).catch(function(){})}
function setlp(v){lp=v;$('lp').textContent='LP: '+lp;
  fetch('/lp',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'lp='+v}).then(function(){t('LP: '+v)}).catch(function(){})}
function mu(n){fetch('/music/'+n).then(function(){t('Track '+n)}).catch(function(){})}
function up(){fetch('/up',{method:'POST'}).then(function(){t('up')}).catch(function(){})}
function down(){fetch('/down',{method:'POST'}).then(function(){t('down')}).catch(function(){})}
function sv(){fetch('/servo',{method:'POST'}).then(function(){t('Claw!')}).catch(function(){})}
function vol(d){var v=$('vol');var x=parseInt(v.textContent)+d;x=Math.max(0,Math.min(30,x));v.textContent=x;
  fetch('/volume',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'n='+x}).then(function(){t('Vol: '+x)}).catch(function(){})}
function ledCmd(mode,r,g,b){
  fetch('/led',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:'strip='+curStrip+'&mode='+mode+'&r='+r+'&g='+g+'&b='+b}).then(function(){t(mode+' ('+r+','+g+','+b+')')}).catch(function(){})}
function setStrip(s){curStrip=s;
  document.querySelectorAll('.strip-btn').forEach(function(b){b.classList.remove('active')});
  $('btn-s'+s).classList.add('active');
  document.getElementById('colorPick').style.display=s===2?'none':'block';}
function setMode(m){curMode=m;
  document.querySelectorAll('.mode-btn').forEach(function(b){b.classList.remove('active')});
  $('btn-'+m).classList.add('active');
  ledCmd(m,curR,curG,curB);}
function setColor(r,g,b){curR=r;curG=g;curB=b;
  $('r').value=r;$('g').value=g;$('b').value=b;
  $('rv').textContent=r;$('gv').textContent=g;$('bv').textContent=b;
  if(curMode==='solid'){ledCmd('solid',r,g,b);}else{curMode='solid';setMode('solid');}}
['r','g','b'].forEach(function(c){
  var el = $(c);
  el.addEventListener('input',function(){
    var v=this.value;
    if(c==='r'){$('rv').textContent=v;curR=parseInt(v);}
    if(c==='g'){$('gv').textContent=v;curG=parseInt(v);}
    if(c==='b'){$('bv').textContent=v;curB=parseInt(v);}
    if(curMode==='solid'){ledCmd('solid',curR,curG,curB);}
  });
});
setInterval(r,2000);r();
</script>
</body>
</html>"""

def ir_callback(cmd, addr, nec):
    global ir_cmd
    ir_cmd = cmd
    print("[IR] 0x%02X" % cmd)

def main():
    global lifevalue, volume, music_queue, oled, audio
    global np1, np2, led1_mode, led2_mode

    print("=== Duel System vLED ===")
    start_ap()

    # 初始化 WS2812
    if HAS_NEOPIXEL:
        try:
            np1 = _np(LED_PIN1, LED_N)
            np2 = _np(LED_PIN2, LED_N)
            print("LED: GPIO%d+%dx%d OK" % (LED_PIN1, LED_PIN2, LED_N))
        except Exception as e:
            print("LED init err:", e)
    else:
        print("LED: neopixel not available")

    oled  = Oled_big() if HAS_OLED else None
    audio = Audio()    if HAS_AUDIO else None
    if audio:
        audio.set_volume(volume)
       # audio.play_music1(1)
    if oled:
        oled.show_number_slot_machine(lifevalue)
# 
#     try:
#         NEC8(Pin(15, Pin.IN), ir_callback)
#         print("IR OK on GPIO15")
#     except Exception as e:
#         print("IR err:", e)

    sock = None
    try:
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", 80))
        sock.listen(1)
        sock.settimeout(0.1)
        print("HTTP server ready")
    except Exception as e:
        print("Socket err:", e)

    tick = 0
    while True:
        # LED 动画（非阻塞，每帧更新）
        if tick % 4 == 0:
            if np1: led_tick1()
            if np2: led_tick2()
        tick += 1

        # HTTP 请求处理
        if sock:
            try:
                cl, addr = sock.accept()
                cl.settimeout(1.0)
                try:
                    d = cl.recv(1024).decode("utf-8", "ignore")
                    if d:
                        lines = d.split("\r\n")
                        req   = lines[0].split()
                        m     = req[0]
                        p     = req[1] if len(req) > 1 else "/"
                        body  = ""
                        idx   = d.find("\r\n\r\n")
                        if idx >= 0:
                            body = d[idx + 4:]
                        code, ct, bdy = handle(p, m, body, addr)
                        respond(cl, code, ct, bdy)
                except Exception as e:
                    print("Req err:", e)
                finally:
                    try: cl.close()
                    except: pass
            except OSError:
                pass

        # 音乐队列
        if music_queue and audio:
            t = music_queue.pop(0)
            led_music_flash(15, (random.randint(0, 255),random.randint(0, 255), 255))  # 音乐响LED闪烁30帧
            try:
                    if 1 <= t <= 4:
                       audio.play_music1(t)
                    else:
                       audio.play_bgmusic()     
            except Exception as e:
                    print("Audio err:", e)
            utime.sleep_ms(80)

        utime.sleep_ms(10)

if __name__ == "__main__":
    main()
