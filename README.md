# 基于视觉感知的驾驶员危险行为实时监测与主动预警系统

全国大学生嵌入式芯片与系统设计竞赛 · 复旦微赛道参赛作品

## 项目背景

据统计，驾驶员分心、疲劳、接打电话等危险行为是交通事故的主要诱因之一。本项目面向车载场景，基于视觉感知与边缘 AI 计算，实现驾驶员危险行为的实时检测与主动预警，旨在提升驾驶安全。

系统采用"PC 端完整闭环 + 板端 NPU 边缘推理"双轨方案：

- **PC 端**：YOLO 实时检测，多帧时序防误检、疲劳三级分级、中文横幅与语音播报分级预警，构成端到端闭环；
- **板端**：复旦微 ZG330（悟净开发板）NPU 部署 Icraft INT8 量化模型，SDI 摄像头输入、NPU 低功耗实时推理、HDMI 输出，不依赖云端算力。

## 核心成果

| 指标 | 实测数据 |
|---|---|
| NPU 推理延迟（自定义模型） | ≈ 20 ms / 帧 |
| NPU 推理延迟（基线模型） | ≈ 12~14 ms / 帧 |
| 实时性 | 满足 30 FPS 实时性要求 |
| 模型量化后体积 | ≈ 9 MB（INT8） |
| 输入分辨率 | 1920×1080（SDI） |
| 输出分辨率 | 1920×1080（HDMI） |

## 目录结构

```
driver-monitor-fpga-code/
├── README.md                   项目说明（本文件）
├── pc_side/                    PC 端实时检测与预警
│   ├── web_demo.py             FastAPI 网页版实时检测演示
│   ├── pc_demo.py              实时检测主程序（含检测面板 UI）
│   ├── capture_viewer.py       HDMI 采集卡收流与录制工具
│   ├── requirements.txt        Python 依赖
│   ├── start_demo.bat          一键启动脚本
│   └── README.md               运行说明
└── board_side/                 板端部署
    ├── BOARD_SETUP.md          板端部署详细说明
    ├── README.md
    └── model/
        └── best_soham_yolo11n.pt  检测模型权重
```

## 系统架构

```
SDI 摄像头(1920×1080@60)
        ↓
  板端 PL 预处理 (ImageMake)
        ↓
  ZG330 NPU 推理 (Icraft INT8 量化)
        ↓
  板端后处理（PL 硬件加速）
        ↓
HDMI 输出(1920×1080@60)
        ↓
  采集卡 → PC 端录制/展示
```

## 快速开始

### 环境准备

需要 Python 3.8+ 环境，安装依赖：

```bash
pip install -r pc_side/requirements.txt
```

### 网页版演示（推荐）

```cmd
cd pc_side
start_demo.bat
```

浏览器打开 `http://localhost:8000` 即可查看实时检测画面。

### 桌面版演示

```bash
python pc_side/pc_demo.py
```

支持实时检测、疲劳分级预警、中文横幅与语音播报。

### HDMI 采集卡收流与录制

```bash
python pc_side/capture_viewer.py [设备号]
```

自动探测可用视频设备；按键 `R` 开始/停止录制，`Q` 退出。

## 板端部署

基于复旦微悟净开发板（FMQL30TAI，ZG330 iCore NPU），采用 Icraft 3.33.1 工具链完成模型 INT8 量化部署：

- **输入**：3G-SDI 摄像头，1920×1080@60fps
- **推理**：NPU 实时推理，基线模型实测 ≈ 12~14ms/帧，自定义模型 ≈ 20ms/帧
- **输出**：HDMI 1920×1080@60fps
- **后处理**：PL 侧 DetPost 硬件加速后处理

详细部署步骤与模型切换说明见 [`board_side/BOARD_SETUP.md`](board_side/BOARD_SETUP.md)。

## 支持检测类别

Distracted / Drinking / Drowsy / Eating / PhoneUse / SafeDriving / Seatbelt / Smoking

## 技术栈

- 硬件：复旦微悟净开发板（FMQL30TAI + ZG330 NPU）
- 工具链：Icraft 3.33.1（INT8 量化编译）
- 前端：FastAPI + HTML5
- 模型：YOLO 系列 INT8 量化模型
