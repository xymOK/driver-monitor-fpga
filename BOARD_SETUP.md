# 板端部署说明（复旦微 ZG330 / 悟净开发板）

## 1. 硬件链路

```
SDI 摄像头(BNC) ──> 板子 SDI IN ──> NPU 推理 ──> HDMI OUT ──> 毕亚兹采集卡(USB) ──> 电脑 capture_viewer.py
```

- 摄像头输出经 SDI 进入板子，板子完成采集、推理、绘制后经 HDMI 输出；
- 电脑端只负责接收 HDMI 画面并显示/录制，不参与计算。

## 2. 登录与运行

- 串口：COM5 / 115200，root 直接登录；
- Demo 目录（注意路径含两个 `+`）：

```
cd /home/root/fpai_demo_app/fpai_demo_app/examples/1_single_input+ai/PLin+SingleNet+HDMI
./sdicamera+yolov5+hdmi configs/ZG/sdicamera+yolov5+hdmi.yaml
```

正常日志标志：`status=<Input:ok, ps_frame_ok>`、`[ICORE] wait=..+icore=..ms`。

## 3. 模型（双模型结构，可切换）

| 模型 | 类别数 | 说明 | 状态 |
|---|---|---|---|
| `imodel/ZG/Yolo11s_ZG.json/.raw` | 8 | 目标部署模型（INT8），640×640 | 推理正常(约20ms)，后处理待修复 |
| `imodel/ZG/yolov5s_352x640_ZG.json/.raw` | 80 (COCO) | 官方 demo 自带模型，验证用，352×640 | 出框正常(12~14ms) |

> ⚠️ 不可用：`yolov5s_plin_352x640_ZG` 为 2 输入模型，demo 管道只喂 1 路，不兼容（崩溃）。

## 4. 配置文件与类别名（切换核心）

```
configs/ZG/sdicamera+yolov5+hdmi.yaml       当前配置
configs/ZG/sdicamera+yolov5+hdmi.yaml.y11   YOLO11 配置（json/raw=Yolo11s_ZG、net_h 640、class 8）
configs/ZG/sdicamera+yolov5+hdmi.yaml.v5    v5s 配置（json/raw=yolov5s_352x640、net_h 352、class 80）

names/coco.names    当前生效（yaml 的 names_path 指向它）
names/coco80.names  COCO 80 类（v5s 用）
names/coco8.names   8 类（YOLO11 用）
```

**切换 YOLO11：**

```
cp configs/ZG/sdicamera+yolov5+hdmi.yaml.y11 configs/ZG/sdicamera+yolov5+hdmi.yaml
cp names/coco8.names names/coco.names
```

**切换 v5s：**

```
cp configs/ZG/sdicamera+yolov5+hdmi.yaml.v5 configs/ZG/sdicamera+yolov5+hdmi.yaml
cp names/coco80.names names/coco.names
```

⚠️ **类别名必须与模型对应**：names 文件只有一份且被两个模型共用，切换模型时必须同步切换 names，否则检测标签错误或越界崩溃（`basic_string::_M_create`）。

⚠️ **待核对**：PC 端 8 类模型 `best_soham_yolo11n.pt` 内嵌类别为 `Distracted / Drinking / Drowsy / Eating / PhoneUse / SafeDriving / Seatbelt / Smoking`；板端 `coco8.names` 现内容为 `SafeDriving / Drowsy / PhoneUse / Drinking / ReachingBehind / OperatingRadio / Yawning / TurnAndLookBack`，两组不一致。若 `Yolo11s_ZG` 由 Soham 模型转换而来，`coco8.names` 应改为与 PC 端一致（待与转换源核对后修正）。

## 5. 实测性能（板端 NPU 推理，icore 字段）

| 配置 | icore 单帧推理 | 来源 |
|---|---|---|
| YOLO11（640×640，INT8） | 约 20ms（19.7~20.1ms） | YOLO11 配置时段实测日志 |
| v5s（352×640，80类） | 12~14ms | v5s 配置时段实测日志 |

## 6. 已知问题与解决方向

**YOLO11 后处理 0 框**：推理正常（icore≈20ms），但每帧 `Post NMS num: 0`。根因：`Yolo11s_ZG.json` 自带 DetPost 后处理算子（日志 `Has detpost: Yes`、`DetPostZG_op_idx: 211`），该算子由 icraft 3.36.1 编译，而 demo 二进制为 icraft/xir 3.33.1，版本不匹配导致解析不出结果；v5s 非 plin 版 json 为 `Has detpost: No`，走 demo 内置同版本后处理，故出框正常。

解决方向：在 PC 端用 **icraft 3.33.1**（与 demo 匹配版本）重新转换 YOLO11 8 类模型，使 json 后处理与 demo 二进制同版本。

## 7. 收尾操作

```
Ctrl+C    # 停止 demo
sync      # 落盘
# 如需拷贝文件到 U 盘：
mount /dev/sda /mnt/usb
```
