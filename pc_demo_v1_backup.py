import cv2
from ultralytics import YOLO

# 1. 加载模型（soham YOLO11n，8 类：Distracted/Drinking/Drowsy/Eating/PhoneUse/SafeDriving/Seatbelt/Smoking）
model = YOLO(r"D:\A-Univ\Competition\term5\1-FPGA\modelzoo\driver_monitor\best_soham_yolo11n.pt")

# 置信度阈值：漏检太多就调低（如 0.15~0.20），误检太多就调高（如 0.40）
CONF = 0.20 

# 2. 打开电脑自带摄像头 (0代表默认摄像头)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("无法打开摄像头！")
    exit()

print("系统启动，按 'q' 键退出画面...")

# 3. 循环读取每一帧画面
while True:
    ret, frame = cap.read()
    if not ret:
        break
        
    # 4. 将画面送入模型进行推理 (verbose=False 关闭终端刷屏)
    results = model(frame, verbose=False, conf=CONF)
    
    # 5. 获取画好框的画面
    annotated_frame = results[0].plot()
    
    # 6. 显示在屏幕上
    cv2.imshow("Driver Monitor - PC Baseline", annotated_frame)
    
    # 7. 如果按下 q 键，则退出循环
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 8. 释放资源，关闭窗口
cap.release()
cv2.destroyAllWindows()