<h4 align="right"><a href="README.md">English</a> | 简体中文</h4>
<p align="center">
    <img src=https://github.com/user-attachments/assets/ddde58c9-df14-4cbd-a344-f8357764c31e width=138/>
</p>
<h1 align="center">twegui</h1>
<p align="center"><strong>使用 <a href="https://github.com/prinsss/twitter-web-exporter">twitter-web-exporter</a> 导出推文 JSON 后的最佳下一步。</strong></p>
<div align="center">
    <a href="https://github.com/kannazuki-c/twitter-web-exporter-gui/releases" target="_blank">
    <img src="https://img.shields.io/github/v/release/kannazuki-c/twitter-web-exporter-gui"></a>
    <a href="" target="_blank">
    <img src="https://img.shields.io/badge/python-a?logo=python&logoColor=white&labelColor=gray&color=blue"></a>
<p align="center">
    <img src=https://github.com/user-attachments/assets/fc4fe04c-06c6-4c2b-9535-cc9cf4d00c2d width=500/>
</p>

</div>

## 简介

twegui 帮助你整理、下载和浏览从 twitter-web-exporter 导出的推文数据。我几乎每周都用它维护自己的书签和媒体库，并备份到 NAS 中。

支持多语言界面，欢迎贡献翻译！

## ✨ 主要功能

### 📦 归档推文

- 导入 JSON 文件时自动去重，数据存储在 SQLite 数据库中
- 支持还原点功能，可回滚到任意历史状态
- 无需手动处理数据冲突

### 📥 下载媒体

- 内置 aria2 下载器（附带 aria2 1.37.0），开箱即用
- 自动检测未下载的媒体，一键补全
- aria2c RPC 守护进程随程序自动启停，可自由替换 `aria2c.exe`

**智能分类存储：** 下载的媒体按年份和批次自动分类，图片与视频分开保存：

```
下载根目录/
├── 2025.G1/              # 2025年第一批
│   ├── xxx.mp4
│   └── 图/
│       └── xxx.jpg
└── 2025.G2/              # 2025年第二批
    ├── xxx.mp4
    └── 图/
        └── xxx.jpg
```

> 💡 **提示：** 批次号需手动提升，请记得操作！

### 🌐 本地浏览

启动内置 Web 服务器后，可在局域网内使用任意设备（PC、手机、平板）访问网页，浏览所有已归档的推文。你的电脑将作为后端和媒体服务器。

### ⏪ 还原点

类似 Hyper-V 的快照功能，每次修改数据库前可自动创建还原点，随时恢复到任意历史时间点。

### 🗑️ 删除库

将不需要的推文移入删除库后，后续导入 JSON 时会自动跳过这些记录，不再导入也不再下载，保持数据库和媒体库的整洁。

## 🛠️ 技术栈

- **桌面端：** Python + PySide6 + PyInstaller + SQLite3 + Flask + aria2
- **Web 前端：** HTMX + Tailwind CSS + Alpine.js + PhotoSwipe

## 📋 平台支持

目前主要在 Windows 上开发和测试，Mac 和 Linux 的兼容性未经验证。
