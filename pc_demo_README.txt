PC 端演示代码包
================
包含：
- pc_demo.py        ：升级版演示脚本（时序确认 + 疲劳分级 + 玩手机/打电话区分 + 中文横幅 + 语音预警）
- best_soham_yolo11n.pt ：模型（开源预训练模型，来源 AlbatrossC/Driver-Monitoring-System，YOLO11n，8 类驾驶员行为）

运行环境：
- Anaconda 环境 yolo（Python 3.10）
- 依赖：pip install ultralytics pyttsx3 pywin32

运行方法：
  conda activate yolo
  python pc_demo.py
（模型路径在脚本顶部 MODEL_PATH，若模型位置不同请修改为实际路径）

功能一览：
- 8 类检测：Distracted/Drinking/Drowsy/Eating/PhoneUse/SafeDriving/Seatbelt/Smoking
- 时序确认：行为连续 8 帧才触发预警（防单帧误报）
- 疲劳分级：闭眼>=1秒一级(注意力下降)/ >=2秒二级(疑似疲劳)/ >=4秒三级(严重疲劳)，眨眼免疫
- 玩手机 vs 通话：按手机框位置区分（贴近头部=通话）
- 预警方式：画面中文横幅 + 语音播报
- 界面：顶部中文预警横幅 + 右上角信息面板（行为/置信度/危险等级指示灯/帧率/推理耗时）+ 底部状态栏
按 q 退出。