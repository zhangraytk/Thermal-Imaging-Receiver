# Thermal-Imaging-Receiver
热成像接收器项目, [点此下载](https://github.com/umeiko/Thermal-Imaging-Receiver/releases/tag/v0.0.2)

基于[pygame_gui](https://pygame-gui.readthedocs.io/en/latest/quick_start.html)完成, [演示视频在这里](https://www.bilibili.com/video/BV1tr421K7qp)
可保存测温数据，提供温度矩阵数据，以及测温图像，可记录测温曲线。

![image](https://github.com/user-attachments/assets/748314cb-d5ad-47ab-b445-a449ff93472f)

- 用法
  - 选择热成像仪的设备号
  - 鼠标左键可留下测温点
  - 鼠标右键清除测温点

## 运行

```bash
pip install -r requirements.txt
python main.py
```

也可以用可编辑安装获得命令行入口：

```bash
pip install -e .
thermal-receiver
thermal-plotter
```

## 数据保存位置

保存的温度帧、截图和曲线默认写入系统应用数据目录：

- Windows: `%LOCALAPPDATA%\Thermal-Imaging-Receiver\data`
- macOS: `~/Library/Application Support/Thermal-Imaging-Receiver/data`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/Thermal-Imaging-Receiver/data`

可通过配置文件覆盖：

- Windows: `%APPDATA%\Thermal-Imaging-Receiver\config.json`
- macOS: `~/Library/Preferences/Thermal-Imaging-Receiver/config.json`
- Linux: `${XDG_CONFIG_HOME:-~/.config}/Thermal-Imaging-Receiver/config.json`

示例：

```json
{
  "baudrate": 921600,
  "record_interval": 0.25,
  "data_dir": "~/Thermal-Imaging-Receiver/data"
}
```

