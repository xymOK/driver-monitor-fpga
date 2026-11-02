# -*- coding: utf-8 -*-
"""
采集卡画面查看 + 录制工具（替代 OBS 的最小方案）
- 自动探测可用的摄像头/采集卡设备号
- 优先选择"非内置摄像头"（内置通常是 0，采集卡通常是 1/2/3）
- 按 R 开始/停止录制 MP4，按 Q 退出
用法:
    D:\software\ANACONDA\envs\yolo\python.exe capture_viewer.py
    或指定设备号:  ...\python.exe capture_viewer.py 1
"""
import cv2
import sys
import time
from datetime import datetime

OUT_DIR = r"D:\A-Univ\Competition\term5\1-FPGA\competition_code\recordings"


def find_cameras(max_idx=5):
    avail = []
    for i in range(max_idx):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                avail.append(i)
        cap.release()
    return avail


def main():
    import os
    os.makedirs(OUT_DIR, exist_ok=True)

    avail = find_cameras()
    print("可用视频设备号:", avail if avail else "无")

    if not avail:
        print("没找到任何摄像头/采集卡，请确认采集卡已插入笔记本 USB 口")
        return

    idx = None
    if len(sys.argv) > 1:
        idx = int(sys.argv[1])
    else:
        # 优先尝试索引最小的设备（本机实测采集卡=0、内置摄像头=1）
        idx = avail[0]
    if idx not in avail:
        print(f"设备号 {idx} 不在可用列表 {avail} 中，改用 {avail[0]}")
        idx = avail[0]
    if len(sys.argv) <= 1:
        print(f"提示：若窗口显示的是电脑内置摄像头画面，请用参数指定采集卡设备号，如: capture_viewer.py {avail[-1]}")

    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"设备 {idx} 打开失败")
        return
    # 不强制指定分辨率，交由采集卡/驱动协商（强制 1920x1080 会导致部分采集卡黑帧）
    ok, probe = cap.read()
    if ok:
        h, w = probe.shape[:2]
        print(f"已打开设备 {idx}，实际画面分辨率 {w}x{h}，按 R 开始/停止录制，按 Q 退出")
    else:
        print(f"设备 {idx} 打开成功但读不到帧，按 Q 退出")

    writer = None
    out_name = None
    fps = 0.0
    last_t = time.time()
    frames = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frames += 1
        now = time.time()
        if now - last_t >= 1.0:
            fps = frames / (now - last_t)
            frames = 0
            last_t = now

        if writer is not None:
            writer.write(frame)

        info = f"设备{idx}  FPS:{fps:.0f}"
        if writer is not None:
            info += "  [REC]" 
        cv2.putText(frame, info, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                    (0, 0, 255) if writer else (0, 255, 0), 2)

        cv2.imshow("Board View - R: record/stop, Q: quit", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            if writer is None:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_name = os.path.join(OUT_DIR, f"board_capture_{ts}.mp4")
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(out_name, fourcc, 20.0,
                                         (frame.shape[1], frame.shape[0]))
                print("开始录制 ->", out_name)
            else:
                writer.release()
                writer = None
                print("停止录制 ->", out_name)

    cap.release()
    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()
    print("已退出")


if __name__ == "__main__":
    main()
