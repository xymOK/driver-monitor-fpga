# -*- coding: utf-8 -*-
"""Scan the driver-fatigue dataset with the soham 8-class model,
pick one representative image per action class, copy them into
3_deploy/io/input and rewrite list.txt."""
import glob
import os
import random
import shutil

from ultralytics import YOLO

MODEL = r"D:\A-Univ\Competition\term5\1-FPGA\modelzoo\driver_monitor\best_soham_yolo11n.pt"
IMG_DIR = r"D:\A-Univ\Competition\term5\1-FPGA\datasets\driver-fatigue-dataset-main\train\images"
IO_INPUT = r"D:\A-Univ\Competition\term5\1-FPGA\modelzoo\yolo11\yolo11_icraft\yolo11_icraft\3_deploy\io\input"
LIST_TXT = r"D:\A-Univ\Competition\term5\1-FPGA\modelzoo\yolo11\yolo11_icraft\yolo11_icraft\3_deploy\io\list.txt"

WANT = ["Drinking", "Smoking", "Eating", "PhoneUse", "Drowsy", "Distracted", "Seatbelt", "SafeDriving"]
CONF = 0.20
MAX_SCAN = 3000  # safety cap; usually finishes earlier

def main():
    model = YOLO(MODEL)
    imgs = glob.glob(os.path.join(IMG_DIR, "*.jpg"))
    random.seed(2026)
    random.shuffle(imgs)
    print("total images:", len(imgs))

    found = {}  # class -> image path
    scanned = 0
    for p in imgs:
        scanned += 1
        if scanned > MAX_SCAN:
            break
        try:
            r = model(p, conf=CONF, verbose=False)
        except Exception as e:
            print("ERR", p, e)
            continue
        for box in r[0].boxes:
            cls = model.names[int(box.cls)]
            if cls in WANT and cls not in found:
                found[cls] = p
        if len(found) >= len(WANT):
            break
        if scanned % 200 == 0:
            print("scanned", scanned, "found", list(found.keys()))

    print("scanned:", scanned)
    print("found:", {k: os.path.basename(v) for k, v in found.items()})

    # copy picks into io/input as driver_<class>.jpg
    lines = []
    for cls in WANT:
        if cls not in found:
            print("!! not found:", cls)
            continue
        src = found[cls]
        dst = os.path.join(IO_INPUT, "demo_" + cls + ".jpg")
        shutil.copyfile(src, dst)
        lines.append("demo_" + cls + ".jpg")
        print("copied:", cls, "<-", os.path.basename(src))

    # rewrite list.txt
    with open(LIST_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("list.txt updated:", lines)

if __name__ == "__main__":
    main()
