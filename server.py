# -*- coding: utf-8 -*-
"""
LobeAudio v2 - 低延迟版本
- 主通道: WebSocket 推送原始 PCM (48kHz/16bit/立体声), 浏览器用 ScriptProcessor 播放, 延迟约 0.1 秒
- 回退通道: /stream MP3 (WebSocket 不可用时使用)

用法: python server.py
手机浏览器打开: http://<电脑IP>:8787
"""
import socket
import threading
import queue
import time
import asyncio

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import soundcard as sc
import lameenc
import websockets

PORT_HTTP = 8787
PORT_WS = 8788

SR = 48000          # 采样率
CHANNELS = 2        # 立体声
FRAME = 1024        # 采集块: 1024帧 ≈ 21.3ms
BITRATE = 160       # MP3 回退通道码率

mp3_clients = []
mp3_lock = threading.Lock()

ws_loop = None
ws_queues = set()
ws_lock = threading.Lock()


PAGE = ("""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>LobeAudio · 电脑声音同步</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{min-height:100vh;display:flex;align-items:center;justify-content:center;
       background:linear-gradient(160deg,#0f172a 0%,#1e293b 60%,#0f172a 100%);
       font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;color:#e2e8f0;padding:24px}
  .card{width:100%;max-width:420px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);
        border-radius:24px;padding:32px 24px;text-align:center;backdrop-filter:blur(12px);
        box-shadow:0 20px 60px rgba(0,0,0,.45)}
  .icon{font-size:52px;margin-bottom:12px;filter:drop-shadow(0 4px 12px rgba(56,189,248,.5))}
  h1{font-size:20px;font-weight:600;margin-bottom:8px;letter-spacing:.5px}
  .sub{font-size:13px;color:#94a3b8;line-height:1.7;margin-bottom:24px}
  .dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#22c55e;
       margin-right:6px;animation:pulse 1.6s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
  #start{width:100%;padding:16px;font-size:17px;font-weight:600;color:#fff;border:none;
         border-radius:16px;cursor:pointer;background:linear-gradient(135deg,#0ea5e9,#6366f1);
         box-shadow:0 10px 28px rgba(14,165,233,.4);margin-bottom:16px}
  #start:active{transform:scale(.98)}
  #start.hidden{display:none}
  audio{width:100%;margin-top:4px;display:none}
  .hint{margin-top:18px;font-size:12px;color:#64748b;line-height:1.6}
  #stat{margin-top:14px;font-size:12px;color:#38bdf8;min-height:16px}
</style>
</head>
<body>
<div class="card">
  <div class="icon">🎧</div>
  <h1>电脑声音同步</h1>
  <div class="sub"><span class="dot"></span>电脑上正在播放的音乐会实时传到这里</div>
  <button id="start">▶ 开始收听</button>
  <audio id="player" controls preload="none"></audio>
  <div id="stat"></div>
  <div class="hint">需与电脑处于同一 WiFi<br>低延迟通道 ≈ 0.1 秒</div>
</div>

<script>
(function(){
  var btn = document.getElementById('start');
  var player = document.getElementById('player');
  var stat = document.getElementById('stat');
  var ctx = null, sp = null, ws = null, started = false, retryTimer = null;
  var pending = [];
  var offset = 0;
  var totalSamples = 0;
  var playing = false;
  var PREBUF_SAMPLES = 48000 * 2 * 0.20;
  var MAX_SAMPLES = 48000 * 2 * 0.60;

  function setStat(t){ stat.textContent = t; }

  function pushPcm(i16){
    pending.push(i16);
    totalSamples += i16.length;
    while (totalSamples > MAX_SAMPLES && pending.length > 1) {
      var c = pending.shift();
      totalSamples -= c.length;
      offset = 0;
    }
  }

  function handleAudio(e){
    var L = e.outputBuffer.getChannelData(0);
    var R = e.outputBuffer.getChannelData(1);
    var need = L.length, w = 0;
    if (!playing) {
      if (totalSamples >= PREBUF_SAMPLES) { playing = true; }
      else {
        for (var z = 0; z < need; z++) { L[z] = 0; R[z] = 0; }
        return;
      }
    }
    while (w < need && pending.length) {
      var c = pending[0];
      var remainFrames = (c.length - offset) >> 1;
      var takeFrames = Math.min(remainFrames, need - w);
      var k = offset;
      for (var i = 0; i < takeFrames; i++) {
        L[w] = c[k] / 32768;
        R[w] = c[k + 1] / 32768;
        k += 2; w++;
      }
      offset += takeFrames * 2;
      totalSamples -= takeFrames * 2;
      if (offset >= c.length) { pending.shift(); offset = 0; }
    }
    for (; w < need; w++) { L[w] = 0; R[w] = 0; }
  }

  var bufTimer = null;
  function startBufTimer(){
    if (bufTimer) { clearInterval(bufTimer); }
    bufTimer = setInterval(function(){
      if (!playing) { setStat('\\u23F3 正在缓冲…'); return; }
      setStat('\\u{1F4E1} 缓冲 ' + Math.round(totalSamples / 96) + 'ms');
    }, 500);
  }

  function wsConnect(){
    var url = 'ws://' + location.hostname + ':' + PORTWS;
    ws = new WebSocket(url);
    ws.binaryType = 'arraybuffer';
    ws.onopen = function(){ setStat('\\u{1F4E1} 低延迟通道已连接'); startBufTimer(); };
    ws.onmessage = function(ev){ pushPcm(new Int16Array(ev.data)); };
    ws.onclose = function(){
      setStat('连接中断,正在重连…');
      if (started) { clearTimeout(retryTimer); retryTimer = setTimeout(boot, 1200); }
    };
    ws.onerror = function(){ try { ws.close(); } catch(e){} };
  }

  function fallbackMp3(){
    setStat('\\u26A0\\uFE0F 已切换兼容模式(延迟略高)');
    player.style.display = 'block';
    player.src = '/stream?' + Date.now();
    player.play().catch(function(){});
  }

  function boot(){
    try {
      if (!('WebSocket' in window)) { throw new Error('no-websocket'); }
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) { throw new Error('no-audioctx'); }
      if (ctx) { try { ctx.close(); } catch(e){} }
      ctx = new AC({ sampleRate: 48000, latencyHint: 'interactive' });
      if (ctx.state === 'suspended') { ctx.resume(); }
      sp = ctx.createScriptProcessor(1024, 0, 2);
      sp.onaudioprocess = handleAudio;
      sp.connect(ctx.destination);
      pending = []; offset = 0; totalSamples = 0; playing = false;
      wsConnect();
    } catch (e) {
      fallbackMp3();
    }
  }

  btn.addEventListener('click', function(){
    if (started) { return; }
    started = true;
    btn.classList.add('hidden');
    boot();
  });
})();
</script>
</body>
</html>""").encode('utf-8')

PAGE = PAGE.replace(b"PORTWS", str(PORT_WS).encode())


def broadcast_mp3(data: bytes):
    with mp3_lock:
        dead = []
        for q in mp3_clients:
            try:
                q.put_nowait(data)
            except queue.Full:
                dead.append(q)
        for q in dead:
            try:
                mp3_clients.remove(q)
            except ValueError:
                pass


def _put_nowait(q, data):
    try:
        q.put_nowait(data)
    except asyncio.QueueFull:
        pass
    except Exception:
        pass


def broadcast_pcm(pcm_bytes: bytes):
    loop = ws_loop
    if loop is None:
        return
    with ws_lock:
        queues = list(ws_queues)
    if not queues:
        return
    for q in queues:
        try:
            loop.call_soon_threadsafe(_put_nowait, q, pcm_bytes)
        except RuntimeError:
            pass


def capture_loop():
    speaker = sc.default_speaker()
    mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
    enc = lameenc.Encoder()
    enc.set_bit_rate(BITRATE)
    enc.set_in_sample_rate(SR)
    enc.set_channels(CHANNELS)
    enc.set_quality(2)
    print("[capture] 捕获扬声器: %s" % speaker.name, flush=True)
    with mic.recorder(samplerate=SR, channels=CHANNELS, blocksize=FRAME) as rec:
        while True:
            try:
                data = rec.record(numframes=FRAME)
            except Exception as e:
                print("[capture] 读取错误: %r" % (e,), flush=True)
                time.sleep(1)
                continue
            pcm_f = np.clip(data, -1.0, 1.0)
            pcm16 = (pcm_f * 32767).astype(np.int16)
            raw = pcm16.tobytes()
            broadcast_pcm(raw)
            if mp3_clients:
                mp3 = enc.encode(raw)
                if mp3:
                    broadcast_mp3(bytes(mp3))


async def ws_handler(ws):
    q = asyncio.Queue(maxsize=200)
    with ws_lock:
        ws_queues.add(q)
    peer = getattr(ws, 'remote_address', ('?', 0))
    print("[ws] 低延迟听众接入: %s:%s, 共 %d 位" % (peer[0], peer[1], len(ws_queues)), flush=True)

    try:
        while True:
            data = await q.get()
            await ws.send(data)
    except Exception:
        pass
    finally:
        with ws_lock:
            ws_queues.discard(q)
        print("[ws] 听众断开, 剩余 %d 位" % len(ws_queues), flush=True)


async def ws_main():
    global ws_loop
    ws_loop = asyncio.get_running_loop()
    async with websockets.serve(ws_handler, '0.0.0.0', PORT_WS, max_size=None, ping_interval=20):
        await asyncio.Future()


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        if self.path == '/' or self.path.startswith('/index'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(PAGE)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(PAGE)
        elif self.path.startswith('/stream'):
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.end_headers()
            q = queue.Queue(maxsize=300)
            with mp3_lock:
                mp3_clients.append(q)
            print("[stream] MP3 回退听众接入", flush=True)
            try:
                while True:
                    try:
                        chunk = q.get(timeout=15)
                    except queue.Empty:
                        continue
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except Exception:
                pass
            finally:
                with mp3_lock:
                    if q in mp3_clients:
                        mp3_clients.remove(q)
        else:
            self.send_error(404)

    def log_message(self, fmt, *args):
        pass


def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def main():
    ip = get_lan_ip()
    print("=" * 52, flush=True)
    print("  LobeAudio v2 (低延迟) 已启动", flush=True)
    print("  手机浏览器:  http://%s:%d" % (ip, PORT_HTTP), flush=True)
    print("  低延迟通道:  ws://%s:%d" % (ip, PORT_WS), flush=True)
    print("=" * 52, flush=True)

    threading.Thread(target=capture_loop, daemon=True).start()

    httpd = ThreadingHTTPServer(('0.0.0.0', PORT_HTTP), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    try:
        asyncio.run(ws_main())
    except KeyboardInterrupt:
        print("已停止", flush=True)


if __name__ == '__main__':
    main()
