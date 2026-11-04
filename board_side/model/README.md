本目录存放模型文件：

- `best_soham_yolo11n.pt`：开源预训练 YOLO11n 8 类模型权重（来源：AlbatrossC/Driver-Monitoring-System，使用遵守原仓库许可协议）
- `Yolo11s_ZG.json` / `Yolo11s_ZG.raw`：Icraft INT8 量化编译后的板端模型文件

模型已完成从 PyTorch 权重到板端 NPU 的量化转换流程，生成板端可加载的 .json/.raw 模型文件。
