# -*- coding: utf-8 -*-
"""Local YOLO11 + webcam dashboard. Run: python web_demo.py --model path/to/best.pt"""
from __future__ import annotations

import sys
import argparse
import asyncio
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

# Windows 下强制使用 selector event loop，避免 WinError 10014
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from ultralytics import YOLO
import uvicorn


FRAME_THRESHOLD = 8
PHONE_EAR_ZONE = 0.40
CONF = 0.35
IOU = 0.45

PAGE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>驾驶状态监测 · 本机联调</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0b1420;color:#edf4fb;font:14px "Segoe UI","Microsoft YaHei",sans-serif}.wrap{max-width:1400px;margin:auto;padding:24px}.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}.brand{font-size:20px;font-weight:700}.sub{font-size:12px;color:#91a4b9;margin-top:5px}.pill{border:1px solid #294057;border-radius:20px;padding:8px 12px;color:#a9bdcf;font-size:12px}.dot{display:inline-block;width:8px;height:8px;background:#49d7a1;border-radius:50%;margin-right:7px}.grid{display:grid;grid-template-columns:1.7fr .85fr;gap:16px}.card{background:#111e2d;border:1px solid #26384d;border-radius:15px;padding:18px}.head{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;font-weight:700}.muted{color:#8195aa;font-size:11px;font-weight:400}.video{width:100%;aspect-ratio:16/9;object-fit:contain;background:#070c12;border:1px solid #25394d;border-radius:10px}.status{font-size:24px;font-weight:700;margin:12px 0 8px}.desc{color:#afbdcc;line-height:1.6;font-size:12px}.badge{display:inline-block;border-radius:20px;padding:6px 9px;background:#43351f;color:#ffd17d;font-size:11px}.progress{height:5px;background:#26364a;border-radius:6px;margin:13px 0 7px}.progress i{display:block;height:100%;background:linear-gradient(90deg,#ffbf5f,#ff6e70);border-radius:6px;width:0}.threshold{display:flex;justify-content:space-between;color:#8295a8;font-size:10px}.voice{display:flex;align-items:center;justify-content:space-between;margin-top:16px;padding-top:15px;border-top:1px solid #26384d}.toggle{border:0;border-radius:20px;width:39px;height:22px;padding:3px;background:#39516a}.toggle:after{content:"";display:block;width:16px;height:16px;border-radius:50%;background:white;transition:.2s}.toggle.on{background:#18ad93}.toggle.on:after{transform:translateX(17px)}button.action{background:#173149;border:1px solid #31516a;color:#d9e8f5;border-radius:9px;padding:9px 12px;cursor:pointer}button.action:hover{background:#20435e}.bottom{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}.classes{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.chip{border:1px solid #26384d;background:#0e1926;padding:8px;border-radius:8px;color:#9fb1c3;font-size:11px}.chip.on{border-color:#725a32;background:#2b271e;color:#ffd17d}.events{display:grid;gap:8px;max-height:230px;overflow:auto}.event{border-bottom:1px solid #26384d;padding:9px 0;color:#c8d4df;font-size:12px}.event small{display:block;color:#8195aa;margin-top:4px}.warning{color:#ffab82}.good{color:#56d8a7}.err{color:#ff7885}.tools{display:flex;gap:8px;align-items:center}.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:#193247;border:1px solid #326079;padding:10px 15px;border-radius:9px;opacity:0;transition:.2s}.toast.show{opacity:1}@media(max-width:850px){.grid,.bottom{grid-template-columns:1fr}.wrap{padding:14px}.classes{grid-template-columns:repeat(2,1fr)}}
</style></head><body><main class="wrap">
<header class="top"><div><div class="brand">守望 · 驾驶状态监测</div><div class="sub">本机 YOLO11 推理联调 · 视频与状态来自 Python 模型</div></div><div class="pill"><i class="dot" id="dot"></i><span id="run">连接中</span></div></header>
<section class="grid"><div class="card"><div class="head"><span>实时检测画面</span><span class="muted">电脑摄像头 · MJPEG</span></div><img class="video" src="/video_feed" alt="本机摄像头推理画面"></div>
<div class="card"><div class="head"><span>当前驾驶状态</span><span class="badge" id="badge">等待识别</span></div><div class="status" id="label">启动中…</div><div class="desc" id="message">正在加载模型和摄像头。</div><div class="progress"><i id="bar"></i></div><div class="threshold"><span>1 秒：注意力下降</span><span>2 秒：疑似疲劳</span><span>4 秒：严重疲劳</span></div><div class="voice"><div><b>网页语音播报</b><div class="muted" id="voiceText" style="margin-top:4px">新告警时使用浏览器语音</div></div><button class="toggle on" id="toggle" aria-label="切换语音"></button></div><div class="tools" style="margin-top:13px"><button class="action" id="test">试听当前提醒</button><span class="muted" id="stats">FPS — · 置信度 —</span></div></div></section>
<section class="bottom"><div class="card"><div class="head"><span id="classTitle">模型行为类别</span><span class="muted">模型检测结果</span></div><div class="classes" id="classes"></div><p class="muted" style="line-height:1.6;margin:12px 0 0">普通行为连续出现 8 帧后确认；疲劳预警按连续检测时长分级。手机通话判断沿用演示脚本的位置启发式规则。</p></div><div class="card"><div class="head"><span>告警事件</span><button class="action" id="clear">清空</button></div><div class="events" id="events"></div></div></section>
<p class="muted" style="text-align:center;margin-top:18px">此页面在本机运行；停止终端服务后网页断开。若摄像头被其他程序占用，请先关闭原来的 pc_demo.py。</p>
</main><div class="toast" id="toast"></div><script>
let names=[];const cn={Distracted:'分心驾驶',Drinking:'喝水',Drowsy:'疲劳',Eating:'吃东西',PhoneUse:'使用手机',SafeDriving:'正常驾驶',Seatbelt:'安全带',Smoking:'吸烟'};let voice=true,lastEvent=-1,previousLabel='';const $=x=>document.getElementById(x);const classes=$('classes');function setClasses(list){const next=JSON.stringify(list);if(classes.dataset.names===next)return;classes.dataset.names=next;classes.innerHTML='';names=list;names.forEach(n=>{const e=document.createElement('div');e.className='chip';e.id='c_'+n;e.textContent=(cn[n]||n)+' · '+n;classes.appendChild(e)})}function toast(t){$('toast').textContent=t;$('toast').classList.add('show');setTimeout(()=>$('toast').classList.remove('show'),2200)}function speak(t){if(!voice||!t)return;if(!('speechSynthesis'in window)){toast('浏览器不支持语音合成');return}speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(t);u.lang='zh-CN';u.rate=.92;speechSynthesis.speak(u)}function esc(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML}async function poll(){try{const r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);const s=await r.json();setClasses(s.class_names||[]);$('classTitle').textContent=(s.class_names||[]).length+' 类驾驶行为';$('run').textContent='模型运行中';$('dot').style.background='#49d7a1';$('label').textContent=s.label;$('message').textContent=s.message;$('badge').textContent=s.level_text;$('stats').textContent='FPS '+(s.fps||0).toFixed(1)+' · 置信度 '+(s.confidence*100).toFixed(0)+'%';$('bar').style.width=Math.min(100,(s.duration_s||0)/4*100)+'%';$('badge').className='badge '+(s.level>0?'warning':'good');names.forEach(n=>{const e=$('c_'+n);if(e)e.classList.toggle('on',(s.detections||[]).some(x=>x.name===n))});if(s.event_id!==lastEvent&&lastEvent!==-1&&s.level>0&&voice)speak(s.message);lastEvent=s.event_id;if(s.label!==previousLabel&&s.label){previousLabel=s.label}if(s.error){$('run').textContent='摄像头/推理异常';$('dot').style.background='#ff6577';$('message').textContent=s.error}if(s.events){$('events').innerHTML=s.events.map(e=>'<div class="event"><span class="'+(e.level>0?'warning':'good')+'">'+esc(e.label)+'</span><small>'+esc(e.time)+' · '+esc(e.message)+'</small></div>').join('')||'<div class="muted">暂无事件</div>'}}catch(e){$('run').textContent='服务未连接';$('dot').style.background='#ff6577';$('message').textContent='无法连接本机推理服务：'+e.message}}setInterval(poll,400);poll();$('toggle').onclick=()=>{voice=!voice;$('toggle').classList.toggle('on',voice);$('voiceText').textContent=voice?'新告警时使用浏览器语音':'已关闭，只显示文字预警';if(!voice&&'speechSynthesis'in window)speechSynthesis.cancel()};$('test').onclick=()=>speak($('message').textContent);$('clear').onclick=async()=>{await fetch('/api/events/clear',{method:'POST'});$('events').innerHTML='<div class="muted">暂无事件</div>'};
</script></body></html>'''


MESSAGES = {
    "正常驾驶": "状态良好，请保持专注。",
    "注意力下降": "检测到驾驶员注意力下降。",
    "疑似疲劳驾驶": "检测到疑似疲劳驾驶，请注意休息。",
    "严重疲劳驾驶": "检测到严重疲劳驾驶，请立即停车休息。",
    "正在通话": "检测到驾驶员正在通话，请注意驾驶安全。",
    "使用手机": "检测到驾驶员使用手机，请勿分心驾驶。",
    "喝水": "检测到驾驶员喝水，请注意行车安全。",
    "吸烟": "检测到驾驶员吸烟，请勿在车内吸烟。",
    "吃东西": "检测到驾驶员吃东西，请注意行车安全。",
    "分心驾驶": "检测到驾驶员分心，请集中注意力。",
    "安全带提醒": "请系好安全带。",
}


class Monitor:
    def __init__(self, model_path: str, camera_index: int):
        path = Path(model_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"找不到模型文件：{path.resolve()}")
        print(f"加载模型：{path.resolve()}")
        self.model = YOLO(str(path))
        self.model_path = str(path.resolve())
        self.names = self.model.names
        raw_names = list(self.names.values()) if isinstance(self.names, dict) else list(self.names)
        self.class_names = [self._canon(str(n)) for n in raw_names]
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW) if hasattr(cv2, "CAP_DSHOW") else cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 index={camera_index}。先关闭正在占用摄像头的程序，或尝试 --camera 1。")
        self.lock = threading.Lock()
        self.model_lock = threading.Lock()
        self.jpeg: bytes | None = None
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.consecutive = {self._canon(str(n)): 0 for n in raw_names}
        self.detected_since: dict[str, float] = {}
        self.drowsy_since: float | None = None
        self.last_key = None
        self.event_id = 0
        self.events = deque(maxlen=20)
        self.state = {"label":"等待识别", "message":"摄像头已连接，等待第一帧。", "level":0, "level_text":"启动中", "duration_s":0.0, "confidence":0.0, "fps":0.0, "event_id":0, "class_names":self.class_names, "detections":[], "events":[], "error":None}

    def start(self):
        self.thread = threading.Thread(target=self._loop, name="yolo-webcam-inference", daemon=True)
        self.thread.start()

    def _loop(self):
        previous = time.perf_counter()
        while not self.stop_event.is_set():
            ok, frame = self.cap.read()
            if not ok:
                with self.lock:
                    self.state["error"] = "摄像头未能读取画面；检查连接，或尝试更换 --camera 编号。"
                time.sleep(.2)
                continue
            try:
                now = time.monotonic()
                with self.model_lock:
                    result = self.model(frame, verbose=False, conf=CONF, iou=IOU)[0]
                annotated = result.plot()
                det: dict[str, list[tuple[list[float], float]]] = {}
                boxes = result.boxes
                if boxes is not None:
                    for i in range(len(boxes)):
                        cid = int(boxes.cls[i].item())
                        name = self._canon(str(self.names.get(cid, cid) if isinstance(self.names, dict) else self.names[cid]))
                        conf = float(boxes.conf[i].item())
                        xyxy = boxes.xyxy[i].tolist()
                        det.setdefault(name, []).append((xyxy, conf))
                all_names = self.class_names
                for name in all_names:
                    if name in det:
                        self.consecutive[name] = self.consecutive.get(name, 0) + 1
                        self.detected_since.setdefault(name, now)
                    else:
                        self.consecutive[name] = 0
                        self.detected_since.pop(name, None)
                label, level, duration, conf = self._decide(det, frame.shape[0], now)
                message = MESSAGES.get(label, f"检测到{label}，请注意驾驶安全。")
                loop_now = time.perf_counter()
                fps = 1.0 / max(loop_now - previous, 1e-6)
                previous = loop_now
                ok_jpg, encoded = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 82])
                if ok_jpg:
                    with self.lock:
                        self.jpeg = encoded.tobytes()
                key = (label, level)
                with self.lock:
                    if key != self.last_key:
                        self.event_id += 1
                        if level > 0:
                            self.events.appendleft({"label":label, "message":message, "level":level, "time":datetime.now().strftime("%H:%M:%S")})
                        self.last_key = key
                    self.state.update({"label":label, "message":message, "level":level, "level_text":self._level_text(level), "duration_s":duration, "confidence":conf, "fps":fps, "event_id":self.event_id, "class_names":self.class_names, "detections":[{"name":n, "confidence":max(c for _, c in entries)} for n, entries in det.items()], "events":list(self.events), "error":None})
            except Exception as exc:
                with self.lock:
                    self.state["error"] = f"推理错误：{type(exc).__name__}: {exc}"
                time.sleep(.1)

    def _decide(self, det, height, now):
        if "Drowsy" in det:
            if self.drowsy_since is None:
                self.drowsy_since = now
            duration = now - self.drowsy_since
            if duration >= 4:
                label, level = "严重疲劳驾驶", 3
            elif duration >= 2:
                label, level = "疑似疲劳驾驶", 2
            elif duration >= 1:
                label, level = "注意力下降", 1
            else:
                label, level = "正常驾驶", 0
            return label, level, duration, max(c for _, c in det["Drowsy"])
        self.drowsy_since = None
        priority = [("PhoneUse", "使用手机"), ("Drinking", "喝水"), ("Smoking", "吸烟"), ("Eating", "吃东西"), ("Distracted", "分心驾驶"), ("Seatbelt", "安全带提醒")]
        for name, label in priority:
            if self.consecutive.get(name, 0) < FRAME_THRESHOLD or name not in det:
                continue
            duration = now - self.detected_since.get(name, now)
            if name == "PhoneUse":
                near_face = any(((box[1] + box[3]) / 2 / height) < PHONE_EAR_ZONE for box, _ in det[name])
                if near_face:
                    label = "正在通话"
            return label, 1, duration, max(c for _, c in det[name])
        if "SafeDriving" in det:
            return "正常驾驶", 0, 0.0, max(c for _, c in det["SafeDriving"])
        return "正常驾驶", 0, 0.0, 0.0

    @staticmethod
    def _canon(name):
        key = name.lower().replace("_", "").replace(" ", "").replace("-", "")
        aliases = {"drowsy":"Drowsy", "sleepy":"Drowsy", "drowsiness":"Drowsy", "drinking":"Drinking", "eating":"Eating", "distracted":"Distracted", "phoneuse":"PhoneUse", "phone":"PhoneUse", "safedriving":"SafeDriving", "seatbelt":"Seatbelt", "smoking":"Smoking", "cigarette":"Smoking"}
        return aliases.get(key, name)

    @staticmethod
    def _level_text(level):
        return {0:"状态正常", 1:"一级提醒", 2:"二级预警", 3:"三级预警"}.get(level, "状态正常")

    def snapshot(self):
        with self.lock:
            return {**self.state, "events":list(self.events)}

    def clear_events(self):
        with self.lock:
            self.events.clear()

    def close(self):
        self.stop_event.set()
        self.cap.release()


monitor: Monitor | None = None
app = FastAPI(title="Driver Monitoring Local Demo")


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


@app.get("/api/state")
def api_state():
    if monitor is None:
        raise HTTPException(status_code=503, detail="模型服务尚未启动")
    return monitor.snapshot()


@app.get("/api/health")
def api_health():
    """Return service status, loaded model classes, and camera state."""
    if monitor is None:
        return {"ok": False, "model_loaded": False, "camera_open": False}
    return {
        "ok": True,
        "model_loaded": monitor.model is not None,
        "model_path": monitor.model_path,
        "camera_open": monitor.cap.isOpened(),
        "class_names": monitor.class_names,
    }


@app.post("/api/predict")
async def api_predict(request: Request):
    """Run one image through the loaded YOLO model.

    Send the raw JPEG or PNG file bytes as the request body. Example:
    curl -X POST http://127.0.0.1:8000/api/predict -H "Content-Type: image/jpeg" --data-binary @frame.jpg
    """
    if monitor is None:
        raise HTTPException(status_code=503, detail="模型服务尚未启动")
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in {"image/jpeg", "image/png", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="请以 image/jpeg、image/png 或 application/octet-stream 上传图片字节")
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="请求体为空，请上传 JPEG 或 PNG 图片")
    if len(body) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="图片超过 12 MiB 限制")
    frame = cv2.imdecode(np.frombuffer(body, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="图片无法解码，请检查文件格式")
    try:
        with monitor.model_lock:
            result = monitor.model(frame, verbose=False, conf=CONF, iou=IOU)[0]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"模型推理失败：{type(exc).__name__}: {exc}") from exc
    detections = []
    boxes = result.boxes
    if boxes is not None:
        for i in range(len(boxes)):
            class_id = int(boxes.cls[i].item())
            raw_name = monitor.names.get(class_id, str(class_id)) if isinstance(monitor.names, dict) else monitor.names[class_id]
            detections.append({
                "class_id": class_id,
                "name": monitor._canon(str(raw_name)),
                "confidence": float(boxes.conf[i].item()),
                "xyxy": [round(float(v), 2) for v in boxes.xyxy[i].tolist()],
            })
    return {
        "model": monitor.model_path,
        "image": {"width": int(frame.shape[1]), "height": int(frame.shape[0])},
        "count": len(detections),
        "detections": detections,
    }


@app.post("/api/events/clear")
def clear_events():
    if monitor is None:
        raise HTTPException(status_code=503, detail="模型服务尚未启动")
    monitor.clear_events()
    return {"ok":True}


@app.get("/video_feed")
async def video_feed():
    if monitor is None:
        raise HTTPException(status_code=503, detail="模型服务尚未启动")

    async def stream():
        while True:
            with monitor.lock:
                jpg = monitor.jpeg
            if jpg:
                yield b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-cache\r\n\r\n" + jpg + b"\r\n"
            await asyncio.sleep(.04)

    return StreamingResponse(stream(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.on_event("shutdown")
def shutdown():
    if monitor is not None:
        monitor.close()


def main():
    global monitor
    parser = argparse.ArgumentParser(description="用本地 YOLO11 模型驱动网页实时演示")
    parser.add_argument("--model", required=True, help="YOLO .pt 权重文件路径")
    parser.add_argument("--camera", type=int, default=0, help="摄像头编号，默认 0")
    parser.add_argument("--host", default="127.0.0.1", help="默认只监听本机")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    monitor = Monitor(args.model, args.camera)
    monitor.start()
    print(f"网页已启动：http://{args.host}:{args.port}")
    print("按 Ctrl+C 停止；语音由浏览器播放，不会调用 pc_demo.py 的系统 TTS。")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
