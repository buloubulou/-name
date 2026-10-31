# 🎧 LobeAudio

> 把电脑正在播放的声音，实时同步到局域网内的所有手机和平板 —— 无需安装 App，浏览器打开就能听。

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.9%2B-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ 特性

- **超低延迟**：约 0.2 秒（WebSocket 裸 PCM 传输 + ScriptProcessor 播放）
- **零客户端安装**：手机 / 平板 / 电视只需打开浏览器
- **多设备同时收听**：连接数不限，一台电脑广播，N 台设备接听
- **通吃所有音源**：网易云、QQ 音乐、浏览器、视频、游戏……只要是电脑发出的声音
- **完全本地**：不经过任何服务器，数据不出局域网
- **一键脚本**：`install.bat` 安装依赖，`启动服务.bat` 开跑

## 🔧 工作原理

```
电脑扬声器声音
   ↓ WASAPI 环回采集 (soundcard)
原始 PCM 数据 (48kHz / 16bit / 立体声)
   ↓ WebSocket 广播 (端口 8788)
手机浏览器
   ↓ ScriptProcessor 低延迟播放
   🔊 同步出声（预缓冲 200ms 抗抖动）
```

备用通道：MP3 over HTTP（端口 8787 的 `/stream`），用于不支持 WebSocket 的浏览器。

## 🚀 快速开始（Windows）

### 方式一：一键脚本

1. 确保已安装 [Python 3.9+](https://www.python.org/downloads/)（安装时勾选 **Add Python to PATH**）
2. 双击 **`install.bat`** 安装依赖（仅首次）
3. 双击 **`启动服务.bat`** 启动，窗口会显示访问地址，例如：
   ```
   http://192.168.1.100:8787
   ```
4. 手机连接**同一个 WiFi**，浏览器打开该地址 → 点「开始收听」🎵

> 如果手机打不开页面：右键 `放行防火墙.bat` → 以管理员身份运行（放行 8787 / 8788 端口）

### 方式二：命令行

```bash
pip install -r requirements.txt
python server.py
```

## 📱 使用说明

| 场景 | 操作 |
|---|---|
| 首次使用 | `install.bat` → `启动服务.bat` |
| 日常使用 | 双击 `启动服务.bat`，保持窗口开启 |
| 停止 | 双击 `停止服务.bat` 或关闭窗口 |
| 多台设备 | 各自打开同一地址即可，互不影响 |

## ❓ 常见问题

**Q: 声音断断续续？**
手机 WiFi 信号问题。靠近路由器，或连接 5GHz 频段。程序已内置 200ms 预缓冲抗抖动。

**Q: 延迟有点大？**
正常约 0.2 秒。无线传输必经之路，想更低需要专业音频设备。

**Q: 手机息屏后没声音？**
浏览器后台播放限制，保持页面在前台即可。

**Q: 能在外网（不同 WiFi / 4G）访问吗？**
默认只能局域网。需要外网访问可配合内网穿透工具（Cloudflare Tunnel、frp 等）。

**Q: 页面显示「已切换兼容模式」？**
代表走了 MP3 备用通道，延迟会高一些，刷新页面重连即可恢复。

## 📂 项目结构

```
LobeAudio/
├── server.py          # 核心服务：音频采集 + WebSocket 广播 + HTTP 页面
├── requirements.txt   # Python 依赖
├── install.bat        # 一键安装依赖
├── 启动服务.bat        # 启动服务
├── 停止服务.bat        # 停止服务
├── 放行防火墙.bat      # 防火墙放行（管理员运行）
├── 使用说明.txt        # 面向普通用户的中文说明
├── README.md          # 本项目说明
└── LICENSE            # MIT 协议
```

## ⚠️ 说明

- 仅供**个人/家庭局域网**使用
- 请勿用于公开传播受版权保护的音乐内容
- 服务窗口关闭即停止，无后台常驻

## 📄 License

[MIT](LICENSE)

---

⭐ 如果这个项目对你有用，欢迎点个 Star！
