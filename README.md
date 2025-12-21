<h4 align="right"><strong>English</strong> | <a href="README.zh-CN.md">简体中文</a></h4>
<p align="center">
    <img src=https://github.com/user-attachments/assets/ddde58c9-df14-4cbd-a344-f8357764c31e width=138/>
</p>
<h1 align="center">twegui</h1>
<p align="center"><strong>The best next step after exporting tweets as JSON files using <a href="https://github.com/prinsss/twitter-web-exporter">twitter-web-exporter</a>.</strong></p>
<div align="center">
    <a href="https://github.com/kannazuki-c/twitter-web-exporter-gui/releases" target="_blank">
    <img src="https://img.shields.io/github/v/release/kannazuki-c/twitter-web-exporter-gui"></a>
    <a href="" target="_blank">
    <img src="https://img.shields.io/badge/python-a?logo=python&logoColor=white&labelColor=gray&color=blue"></a>
<p align="center">
    <img src=https://github.com/user-attachments/assets/fc4fe04c-06c6-4c2b-9535-cc9cf4d00c2d width=500/>
</p>

</div>

## Introduction

twegui helps you organize, download, and browse tweet data exported from twitter-web-exporter. I use it almost weekly to maintain my bookmarks and media library, backing everything up to my NAS.

Multi-language interface supported. Contributions for translations are welcome!

## ✨ Features

### 📦 Archive Tweets

- Automatic deduplication when importing JSON files, stored in SQLite database
- Restore point support for rollback to any historical state
- No manual data conflict handling needed

### 📥 Download Media

- Built-in aria2 downloader (includes aria2 1.37.0), works out of the box
- Automatically detects missing media and downloads them in one click
- aria2c RPC daemon starts and stops with the application; `aria2c.exe` can be freely replaced

**Smart Storage Organization:** Downloaded media is automatically organized by year and batch, with images and videos stored separately:

```
Download Root/
├── 2025.G1/              # First batch of 2025
│   ├── xxx.mp4
│   └── Images/
│       └── xxx.jpg
└── 2025.G2/              # Second batch of 2025
    ├── xxx.mp4
    └── Images/
        └── xxx.jpg
```

> 💡 **Tip:** Batch numbers need to be manually incremented. Don't forget!

### 🌐 Local Browsing

Start the built-in web server to browse all archived tweets from any device on your local network (PC, phone, tablet). Your computer serves as both the backend and media server.

### ⏪ Restore Points

Similar to Hyper-V snapshots, restore points can be automatically created before each database modification, allowing you to revert to any point in history.

### 🗑️ Deletion Library

Move unwanted tweets to the deletion library. Future JSON imports will automatically skip these records—they won't be imported or downloaded again, keeping your database and media library clean.

## 🛠️ Tech Stack

- **Desktop:** Python + PySide6 + PyInstaller + SQLite3 + Flask + aria2
- **Web Frontend:** HTMX + Tailwind CSS + Alpine.js + PhotoSwipe

## 📋 Platform Support

Primarily developed and tested on Windows. Compatibility with Mac and Linux has not been verified.
