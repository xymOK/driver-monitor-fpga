# 基于视觉感知的驾驶员危险行为实时监测与主动预警系统

面向车载场景的驾驶员行为实时监测与预警系统，采用"PC 端完整闭环 + 板端 NPU 边缘推理"双轨方案：

- **PC 端**：YOLO11（8 类驾驶员行为）实时检测，多帧时序防误检、疲劳三级分级、中文横幅与语音播报分级预警，构成端到端闭环；
- **板端**：复旦微 ZG330（悟净开发板）NPU 部署 Icraft INT8 量化模型，SDI 摄像头输入、NPU 低功耗实时推理、HDMI 输出，不依赖云端算力。

## 目录结构

```
competition_code/
├── pc_demo.py              PC 端实时检测主程序（含检测面板 UI）
├── capture_viewer.py       HDMI 采集卡收流与录制工具（自动探测设备号）
├── best_soham_yolo11n.pt   8 类驾驶员行为检测权重（YOLO11n）
├── requirements.txt        Python 依赖
├── pc_demo_README.txt      PC 端运行与参数说明
└── .gitignore
```

## PC 端运行

```bash
pip install -r requirements.txt
python pc_demo.py
```

检测 8 类行为：SafeDriving / Drowsy / PhoneUse / Drinking / ReachingBehind / OperatingRadio / Yawning / TurnAndLookBack。连续多帧确认防误检，疲劳状态按持续时间三级分级，触发中文横幅与语音预警。

## HDMI 采集卡收流

```bash
python capture_viewer.py [设备号]
```

自动探测可用视频设备；画面含板端 SDI 信号时即为采集卡（Windows 枚举设备号不固定，需以画面内容判断）。按键：`R` 开始/停止录制（输出至 `recordings/`），`Q` 退出。

## 板端部署（摘要）

YOLO11 8 类模型经 Icraft 工具链 INT8 量化压缩至约 9.5MB，部署于板载 NPU：

```
SDI 摄像头(1920×1080@60) → 640×640 输入 → NPU 推理(实测约20ms/帧) → 后处理 → HDMI(1920×1080@60) 输出
```

大体积模型文件与板端配置位于板端部署包内，不在本仓库分发。

## 演示流程建议

1. 板端上电并运行 NPU 推理 demo，SDI 画面经 HDMI 输出；
2. 电脑运行 `capture_viewer.py` 接收板端画面并录制；
3. PC 端运行 `pc_demo.py` 演示 8 类行为检测与分级预警闭环。
