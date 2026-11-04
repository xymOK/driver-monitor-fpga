# 板端部署说明（复旦微 ZG330 / 悟净开发板）

## 1. 硬件连接

```
SDI 摄像头(BNC) ──> 开发板 SDI IN ──> NPU 推理 ──> HDMI OUT ──> USB 采集卡 ──> 电脑
```

- 摄像头输出经 SDI 进入开发板，板子完成采集、推理、绘制后经 HDMI 输出；
- 电脑端通过 USB 采集卡接收 HDMI 画面并显示/录制，不参与计算。

## 2. 登录与运行

- 串口登录：波特率 115200，root 用户直接登录；
- Demo 目录（注意路径含两个 `+`）：

```bash
cd /home/root/fpai_demo_app/fpai_demo_app/examples/1_single_input+ai/PLin+SingleNet+HDMI
./sdicamera+yolov5+hdmi configs/ZG/sdicamera+yolov5+hdmi.yaml
```

正常运行标志：日志显示 `status=<Input:ok, ps_frame_ok>`，以及 `[ICORE] wait=..+icore=..ms` 推理耗时。

## 3. 模型配置

| 模型 | 类别数 | 输入分辨率 | 说明 |
|---|---|---|---|
| `imodel/ZG/yolov5s_352x640_ZG.json/.raw` | 80 (COCO) | 352×640 | 基线检测模型，INT8 量化 |
| `imodel/ZG/Yolo11s_ZG.json/.raw` | 8 | 640×640 | 自定义 8 类检测模型，INT8 量化 |

配置文件位于 `configs/ZG/` 目录下，切换模型时修改 yaml 中的模型路径、输入尺寸和类别数参数，并同步切换对应的类别名文件（`names/coco.names`）。

模型已完成 Icraft INT8 量化编译流程：从 PyTorch 权重（.pt）转换为板端 NPU 可加载的 .json/.raw 模型文件，量化后体积约 9 MB。

## 4. 支持检测类别

自定义 8 类驾驶员行为检测：

```
Distracted / Drinking / Drowsy / Eating
PhoneUse / SafeDriving / Seatbelt / Smoking
```

## 5. 实测性能

板端 NPU 推理性能（icore 单帧耗时）：

| 模型 | 输入分辨率 | 推理延迟 |
|---|---|---|
| YOLO 基线模型 | 352×640 | ≈ 12~14 ms / 帧 |
| YOLO 自定义模型 | 640×640 | ≈ 20 ms / 帧 |

满足 30 FPS 实时性要求。

## 6. 结束运行

```bash
Ctrl+C    # 停止 demo
sync      # 落盘
```

如需拷贝文件到 U 盘：

```bash
mount /dev/sda /mnt/usb
```
