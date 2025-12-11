## twitter-web-exporter-gui

[简体中文](README.md) | English

A third-party GUI for archiving and organizing data exported by [twitter-web-exporter](https://github.com/prinsss/twitter-web-exporter) (in JSON format). Scans for undownloaded media files in Tweets and downloads them for easy migration.

![https://github.com/kannazuki-c/twitter-web-exporter-gui/releases](https://img.shields.io/github/v/release/kannazuki-c/twitter-web-exporter-gui) ![](https://img.shields.io/badge/license-GPLv3-c) ![](https://img.shields.io/badge/python-a?logo=python&logoColor=white&labelColor=gray&color=blue)

![](https://github.com/user-attachments/assets/86c6c9c1-8ea4-42dd-97f7-1caaee35e72b)

## ✨ v0.1.0 Update Highlights

### 🚀 Built-in Downloader Refactored (Recommended)

The built-in downloader has been refactored using [aria2](https://github.com/aria2/aria2), and is now **fully functional and recommended**!

**Smart Categorized Storage:** Downloaded media files are automatically organized by year and batch in the download directory, with images and videos stored separately:

```
Your specified root download directory/
├── 2025.G1/          (Represents the first batch of 2025)
│   ├── xxx.mp4
│   └── Images/
│       └── xxx.jpg
└── 2025.G2/
    ├── xxx.mp4
    └── Images/
        └── xxx.jpg
```

> 💡 **Tip:** Batch number increment requires manual operation, please don't forget!

**Out of the Box:** The release includes the latest build of aria2 (aria2 1.37.0), no additional configuration needed. The aria2c RPC daemon starts and stops automatically with the program, and you can freely replace `aria2c.exe`.

### 🗂️ Database Switching Feature

You can now switch between database files in the main interface. The program will automatically remember the last used filename. By default, it still creates `a.db` and `deleted.db`.

### 🧹 Optimized "Delete Unnecessary Records" Feature

Further optimized the cleanup function for organizing unwanted bookmarks. If you want your record library and download library to contain only bookmarks of a specific theme, you can:

1. Download all media then delete unwanted media
2. Click "Delete Unnecessary Records"
3. Select "Move to deleted.db" (recommended)

This way, deleted records will be automatically **not inserted and not downloaded**, keeping your record and download libraries clean.

### 📦 Other Improvements

- Added `requirements.txt` for quick development environment setup
- Build from source: Run `pyinstaller twegui.spec`

### 💭 Developer's Note

Overall, I'm very satisfied with this program now. Except for still using TinyDB (.db files are actually plaintext JSON string storage, resulting in slightly lower retrieval performance, may consider refactoring to SQLite in the future), but overall usability is great. **Highly recommended for organizing bookmarks and maintaining media libraries**!

## Basic Directory Structure

- twegui.exe Main program
- src/aria2-1.37.0-win-64bit/ aria2 download engine
- downloads/ Stores downloaded media
- a.db Database
- deleted.db Deleted records database

## 🔍 How Are My Tweets Saved?

All Tweets are saved in an a.db file (powered by [TinyDB](https://github.com/msiemens/tinydb)) and can be incrementally updated by dragging and dropping JSON files. When you drag in an exported JSON, the GUI will insert new Tweets into the library.

## 💾 Incremental Updates

Through multiple imports, your Tweets will be saved by addition time. The newest will be at the top. Just maintain one a.db file, pack it up and take it anywhere 🚚, no duplicates.

![](https://github.com/user-attachments/assets/a5052a9f-087b-42ff-aca9-b42332c500fc)

## 📦 Download All Media Files!

The GUI also integrates scanning and downloading functionality for images and videos in Tweets. After importing Tweets, the "Downloaded" column will show whether the media associated with this Tweet already exists on your hard drive.

**For undownloaded media, you can choose:**

- 1. Use the built-in downloader (recommended) - Based on aria2, with automatic categorized storage
- 2. Export all image/video URLs and copy them to a queue download tool (such as IDM, FDM, [AB Download Manager](https://github.com/amir1376/ab-download-manager)) for batch downloading

## ❓ How Does the GUI Detect if Associated Media is Downloaded?

You can select the directory to be scanned. As long as you keep the original media filenames, they can be detected. The rules are as follows:

- According to Twitter(X) rules, images have a 15-character random key, videos have 16 characters
- Independent of file extension
- Independent of directory structure

## License

GPLv3

