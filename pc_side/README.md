# 驾驶状态监测 · PC 端演示

## 包内文件

- `web_demo.py`：FastAPI 后端、电脑摄像头采集、YOLO 模型推理、MJPEG 视频流、网页和 REST 接口。
- `pc_demo.py`：桌面版检测主程序，带检测面板 UI。
- `capture_viewer.py`：HDMI 采集卡收流与录制工具。
- `requirements.txt`：Python 依赖清单。
- `start_demo.bat`：Windows 一键启动脚本。

## 模型说明

检测模型权重位于：`../board_side/model/best_soham_yolo11n.pt`（8 类驾驶员行为检测）。

## 环境准备

需要 Python 3.8+ 环境，安装依赖：

```cmd
pip install -r requirements.txt
```

依赖包括：ultralytics、fastapi、uvicorn、opencv-python、numpy。

## 快速启动

### 方式一：一键启动（推荐）

在已激活环境的 CMD 中运行：

```cmd
start_demo.bat
```

### 方式二：手动启动

```cmd
python web_demo.py --model ../board_side/model/best_soham_yolo11n.pt --camera 0
```

浏览器打开 `http://127.0.0.1:8000` 即可查看实时检测画面。

### 指定其他模型路径

```cmd
python web_demo.py --model "D:\路径\到\best.pt" --camera 0
```

## 桌面版演示

```cmd
python pc_demo.py
```

支持实时检测、疲劳分级预警、中文横幅与语音播报。

## HDMI 采集卡录制

```cmd
python capture_viewer.py [设备号]
```

自动探测可用视频设备；按键 `R` 开始/停止录制，`Q` 退出。

## 网页与后端接口

- `GET  /` 返回监测网页
- `GET  /api/health` 查询服务、模型类别和摄像头状态
- `GET  /api/state` 获取当前状态、检测框摘要、置信度、FPS 和事件记录
- `GET  /video_feed` 获取标注后的 MJPEG 实时视频流
- `POST /api/events/clear` 清空告警事件
- `POST /api/predict` 对单张 JPEG/PNG 图片做一次模型推理并返回 JSON 检测框
- `GET  /docs` FastAPI 自动生成的接口说明

## 注意事项

- 默认只监听 `127.0.0.1`，仅本机浏览器可访问，不会自动公开到互联网或局域网。
- 若网页显示"服务未连接"，确认 CMD 中 Python 服务仍在运行，并查看该窗口的报错。
- 若摄像头打不开，关闭其他正在使用摄像头的程序，再试 `--camera 1`。
- 页面语音由浏览器的中文 TTS 播放。首次使用时先点击"试听当前提醒"；浏览器策略可能要求用户先交互。
- 类别列表由权重文件自动读取，共 8 类：Distracted / Drinking / Drowsy / Eating / PhoneUse / SafeDriving / Seatbelt / Smoking。
- 本地 PC 程序使用 YOLO 系列 .pt 做推理；它不是已部署在悟净板上的 iCraft ZG330 模型文件，也不连接开发板。
