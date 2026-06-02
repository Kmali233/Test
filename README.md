# Test

这是一个已初始化的测试仓库。

## 开始

```bash
python main.py
```

## 结构

- `main.py`：简单的 Python 入口文件
- `.gitignore`：常见 Python/系统临时文件忽略规则

## 生成的视频

本仓库不提交生成后的视频二进制文件；请使用脚本在本地生成 16 秒 AVI 动画视频，避免代码托管平台因二进制文件而拒绝提交。

- 输出文件：`media/anime_programmer_daily_life.avi`（已加入 `.gitignore`）。
- 视频内容：紫发二次元程序员少女的日常生活分镜，包含清晨读 Java、桌前写代码、傍晚科技园散步三个场景。
- 生成脚本：`scripts/generate_anime_daily_life_video.py`，使用 Python 标准库，无需 Pillow、ffmpeg 或网络访问。

生成视频：

```bash
python scripts/generate_anime_daily_life_video.py
```
