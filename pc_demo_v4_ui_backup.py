# -*- coding: utf-8 -*-
"""
升级版 PC 演示：驾驶员危险行为实时监测与主动预警
================================================================
在 v1（纯检测画框）基础上新增：
1. 时序确认   ：某行为连续出现 FRAME_THRESHOLD 帧才触发预警，防单帧误报
2. 玩手机/打电话区分：按手机框中心在画面中的高度启发式判断
   （手机举到脸旁/画面上部 = 正在通话；手机拿在手里/画面中下部 = 使用手机）
3. 疲劳分级   ：Drowsy 连续帧数 -> 一级(注意力下降) / 二级(疑似疲劳) / 三级(严重疲劳)
4. 主动预警   ：屏幕顶部大字横幅 + Windows TTS 语音（没有语音引擎时仅屏幕提示）

用法：
    conda activate yolo
    cd D:\A-Univ\Competition\term5\1-FPGA\competition_code
    python pc_demo.py
按 q 退出。

想要语音播报但没有声音时：
    pip install pyttsx3   （或安装 pywin32 后自动使用系统 SAPI 语音）
================================================================
"""
import cv2
import numpy as np
import threading
import time
from ultralytics import YOLO

# ---------------- 可调参数 ----------------
MODEL_PATH = r"D:\A-Univ\Competition\term5\1-FPGA\modelzoo\driver_monitor\best_soham_yolo11n.pt"
CONF = 0.35            # 置信度：漏检多调低(0.15~0.20)，误检多调高(0.40)
IOU = 0.45             # NMS 阈值
FRAME_THRESHOLD = 8    # 通用行为连续出现多少帧才确认（约 0.3 秒 @30fps）
DROWSY_FRAMES = 30     # 疲劳专用门槛：连续 >=30 帧（约 1 秒）才报一级，免疫眨眼
LEVEL2_FRAMES = 60     # 疲劳二级：Drowsy 连续 >=60 帧（约 2 秒）
LEVEL3_FRAMES = 120    # 疲劳三级：Drowsy 连续 >=120 帧（约 4 秒）
EAR_ZONE = 0.40        # 手机框中心 y < 画面高度 40%（画面上部=贴近头部）判为"通话"
SPEAK_COOLDOWN = 5.0   # 同一条语音最短播报间隔（秒）

# ---------------- 模型 ----------------
model = YOLO(MODEL_PATH)
names = model.names    # {0:'Distracted', 1:'Drinking', ...}

# ---------------- 语音（自动探测后端，都没有则只屏幕提示） ----------------
_tts_mode = None
_speaker = None
_engine = None

try:
    import win32com.client
    _speaker = win32com.client.Dispatch("SAPI.SpVoice")
    _tts_mode = 'sapi'
except Exception:
    try:
        import pyttsx3
        _engine = pyttsx3.init()
        _tts_mode = 'pyttsx3'
    except Exception:
        _tts_mode = None

if _tts_mode is None:
    print("语音：未找到引擎（仅屏幕提示），可用 pip install pywin32 或 pyttsx3 启用")
elif _tts_mode == 'sapi':
    print("语音：Windows SAPI 已启用")
elif _tts_mode == 'pyttsx3':
    print("语音：pyttsx3 已启用")

def _pt_speak(text):
    try:
        _engine.say(text)
        _engine.runAndWait()
    except Exception:
        pass

def speak(text):
    """带冷却时间的语音播报，绝不阻塞主循环"""
    if _tts_mode is None:
        return
    now = time.time()
    if text in _last_spoken and now - _last_spoken[text] < SPEAK_COOLDOWN:
        return
    _last_spoken[text] = now
    if _tts_mode == 'sapi':
        try:
            _speaker.Speak(text, 1)  # 1 = SPF_ASYNC，异步不阻塞
        except Exception:
            pass
    elif _tts_mode == 'pyttsx3':
        # pyttsx3 放在子线程经常不发声，改为主线程直接播（触发频率低，阻塞可接受）
        _pt_speak(text)

_last_spoken = {}

# ---------------- 中文绘制（PIL，自动降级） ----------------
def cn_banner(frame, text, bgr, zone='top', font_px=40):
    """在画面顶部/底部绘制半透明底条 + 中文大字，返回新画面"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        h, w = frame.shape[:2]
        bar_h = int(h * 0.12)
        y0 = 0 if zone == 'top' else h - bar_h

        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert('RGBA')
        overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rectangle([0, y0, w, y0 + bar_h], fill=(bgr[2], bgr[1], bgr[0], 180))
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)

        font = None
        for fp in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
                   "C:/Windows/Fonts/simsun.ttc"):
            try:
                font = ImageFont.truetype(fp, font_px)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = (w - tw) // 2 - bbox[0]
        ty = y0 + (bar_h - th) // 2 - bbox[1]
        draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
        return cv2.cvtColor(np.array(img.convert('RGB')), cv2.COLOR_RGB2BGR)
    except Exception:
        # 降级：中文渲染失败时保留原画面（不影响检测主流程）
        return frame

# ---------------- 颜色（BGR） ----------------
GREEN  = (60, 180, 75)
YELLOW = (0, 200, 255)
ORANGE = (0, 140, 255)
RED    = (0, 0, 255)

# ---------------- 主循环 ----------------
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("无法打开摄像头！请检查摄像头是否被占用。")
    exit()

print("系统启动（升级版：时序确认 + 分级预警 + 语音），按 'q' 退出画面...")
if _tts_mode is None:
    print("提示：未找到语音引擎，当前仅屏幕提示。想启用语音可执行 pip install pyttsx3")
elif _tts_mode == 'sapi':
    print("语音：Windows SAPI 已启用")

consec = {n: 0 for n in names.values()}   # 每个类别的连续出现帧数
alert_key = None                          # 当前生效预警标识（用于判断状态变化）
alert_msg = ""
alert_color = GREEN

while True:
    ret, frame = cap.read()
    if not ret:
        break
    H, W = frame.shape[:2]

    # 1) 推理
    results = model(frame, verbose=False, conf=CONF, iou=IOU)
    boxes = results[0].boxes
    annotated = results[0].plot()

    # 2) 统计本帧检测到的类别 -> 框列表
    det_now = {}
    if boxes is not None and len(boxes) > 0:
        for i in range(len(boxes)):
            cname = names.get(int(boxes.cls[i]), str(int(boxes.cls[i])))
            det_now.setdefault(cname, []).append(boxes.xyxy[i].tolist())

    # 3) 更新连续帧计数
    for n in names.values():
        consec[n] = consec[n] + 1 if n in det_now else 0

    # 4) 行为判定（优先级：疲劳 > 手机 > 其他）
    level = 0
    label = ""
    msg = ""

    if consec.get('Drowsy', 0) >= DROWSY_FRAMES:
        f = consec['Drowsy']
        if f >= LEVEL3_FRAMES:
            level, label, msg, color = 3, "严重疲劳驾驶", "检测到严重疲劳驾驶，请立即停车休息", RED
        elif f >= LEVEL2_FRAMES:
            level, label, msg, color = 2, "疑似疲劳驾驶", "检测到疑似疲劳驾驶，请注意休息", ORANGE
        else:
            level, label, msg, color = 1, "注意力下降", "检测到驾驶员注意力下降", YELLOW
    elif consec.get('PhoneUse', 0) >= FRAME_THRESHOLD and 'PhoneUse' in det_now:
        # 手机框中心高度启发式：贴耳通话 vs 低头玩手机
        cy = [(b[1] + b[3]) / 2 / H for b in det_now['PhoneUse']]
        if any(c < EAR_ZONE for c in cy):
            label, msg, color = "正在通话", "检测到驾驶员正在通话，请注意驾驶安全", ORANGE
        else:
            label, msg, color = "使用手机", "检测到驾驶员使用手机，请勿分心驾驶", YELLOW
    elif consec.get('Drinking', 0) >= FRAME_THRESHOLD:
        label, msg, color = "喝水", "检测到驾驶员喝水，请注意行车安全", YELLOW
    elif consec.get('Smoking', 0) >= FRAME_THRESHOLD:
        label, msg, color = "吸烟", "检测到驾驶员吸烟，请勿在车内吸烟", YELLOW
    elif consec.get('Eating', 0) >= FRAME_THRESHOLD:
        label, msg, color = "吃东西", "检测到驾驶员吃东西，请注意行车安全", YELLOW
    elif consec.get('Distracted', 0) >= FRAME_THRESHOLD:
        label, msg, color = "分心驾驶", "检测到驾驶员分心驾驶，请集中注意力", YELLOW
    elif consec.get('Seatbelt', 0) >= FRAME_THRESHOLD:
        label, msg, color = "安全带提醒", "请系好安全带", YELLOW
    else:
        label, msg, color = "正常驾驶", "状态良好，请保持专注", GREEN

    # 5) 状态变化时播报语音
    key = (label, level)
    if key != alert_key and level > 0 or (key != alert_key and label not in ("正常驾驶",)):
        speak(msg)
    alert_key = key

    # 6) 绘制：顶部预警横幅 + 底部状态栏
    if label == "正常驾驶":
        annotated = cn_banner(annotated, "正常驾驶 · 状态良好", GREEN, zone='top')
    else:
        banner = f"{label}（{'一级' if level==1 else '二级' if level==2 else '三级' if level>0 else ''}）" if level > 0 else label
        annotated = cn_banner(annotated, banner, color, zone='top')
    status = "当前：{}  连续 {} 帧".format(label, max(consec.values(), default=0))
    annotated = cn_banner(annotated, status, (40, 40, 40), zone='bottom', font_px=22)

    cv2.imshow("Driver Warning System - 实时监测预警演示", annotated)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("演示结束。")
