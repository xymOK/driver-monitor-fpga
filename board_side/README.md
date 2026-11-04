# 板端部署

本目录包含板端部署相关的说明文档和模型文件。

- `BOARD_SETUP.md`：板端硬件连接、登录方式、运行步骤与模型切换说明
- `model/`：PC 端检测模型权重（YOLO 系列 .pt）

板端 NPU 部署基于复旦微悟净开发板（FMQL30TAI，ZG330 iCore NPU），采用 Icraft 工具链完成 INT8 量化推理。
