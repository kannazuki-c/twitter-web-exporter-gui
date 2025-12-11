## twitter-web-exporter-gui

简体中文 | [English](README.en.md)

一个第三方 gui 用于归档或整理 [twitter-web-exporter](https://github.com/prinsss/twitter-web-exporter) 导出的数据（以JSON文件格式）。扫描 Tweets 中的未下载媒体文件，并下载它们，以便随时迁移。

![https://github.com/kannazuki-c/twitter-web-exporter-gui/releases](https://img.shields.io/github/v/release/kannazuki-c/twitter-web-exporter-gui) ![](https://img.shields.io/badge/license-GPLv3-c) ![](https://img.shields.io/badge/python-a?logo=python&logoColor=white&labelColor=gray&color=blue)

![](https://github.com/user-attachments/assets/86c6c9c1-8ea4-42dd-97f7-1caaee35e72b)

## ✨ v0.1.0 更新亮点

### 🚀 内建下载器重构（推荐使用）

使用 [aria2](https://github.com/aria2/aria2) 重构了内建下载器，现在内建下载器可用并且**推荐使用**！

**智能分类存储：** 下载的媒体文件会在下载目录下按年份和批次自动分类，图片和视频分开保存：

```
您指定的根下载目录/
├── 2025.G1/          （代表2025年的第一批）
│   ├── xxx.mp4
│   └── 图/
│       └── xxx.jpg
└── 2025.G2/
    ├── xxx.mp4
    └── 图/
        └── xxx.jpg
```

> 💡 **提示：** 批次号提升需手动操作，请不要忘记！

**开箱即用：** 发布产物中自带 aria2 最新构建版本（aria2 1.37.0），无需额外配置。aria2c RPC 守护进程会随程序自动启动和关闭，可自由替换 `aria2c.exe`。

### 🗂️ 数据库切换功能

现在可以在主界面切换您要使用的数据库文件，程序会自动记住上次使用的文件名。默认仍会创建 `a.db` 和 `deleted.db`。

### 🧹 优化"删除不需要的记录"功能

进一步优化了清理功能，用于整理您不需要的书签。如果您希望记录库和下载库仅包含某一主题的书签，可以：

1. 下载所有媒体后删除不需要的媒体
2. 点击"删除不需要的记录"
3. 选择"移动到 deleted.db"（推荐）

这样被删除的记录会被自动**不插入、不下载**，保持您的记录库和下载库纯洁。

### 📦 其他改进

- 增加了 `requirements.txt` 以便快速配置开发环境
- 从源码构建：运行 `pyinstaller twegui.spec`

### 💭 开发者的话

总体来讲，我现在对本程序非常满意了。除了仍使用 TinyDB（.db 文件其实是明文的 JSON 字符串存储，导致检索性能略低，后续可能会考虑重构到 SQLite），但总体可用性很好，**非常推荐您用来整理书签和维护媒体库**！

## 基本目录结构

- twegui.exe 主程序
- src/aria2-1.37.0-win-64bit/ aria2 下载引擎
- downloads/ 存放下载的媒体
- a.db 数据库
- deleted.db 已删除记录数据库

## 🔍我的 Tweets 如何保存？

所有 Tweets 将保存在一个 a.db 文件（由 [TinyDB](https://github.com/msiemens/tinydb) 驱动）中，并可通过拖拽 JSON 文件进行增量更新。当你拖入一段导出的 JSON，gui 会将新增 Tweets 插入库中。

## 💾增量更新

通过多次导入，你的 Tweets 会被按加入时间保存。最新的会在最上方。仅需维护一个 a.db 文件，随时打包带走🚚，不会有重复。

![](https://github.com/user-attachments/assets/a5052a9f-087b-42ff-aca9-b42332c500fc)

## 📦下载所有媒体文件！

gui 还集成了 Tweets 中图片与视频的扫描、下载功能，在导入 Tweets 后，"已下载" 列会显示关联此 Tweets 的媒体是否已存在您的硬盘当中。

**对于未下载的媒体，你可以选择：**

- 1.使用内建下载器（推荐）- 基于 aria2，自动分类存储
- 2.导出所有图片/视频的 URL，复制到队列下载工具（如 IDM、FDM、[AB Download Manager](https://github.com/amir1376/ab-download-manager)）中批量下载

## ❓gui 如何检测关联媒体是否已下载？

您可选择被扫描的目录，只要保持原始的媒体文件名就可以被扫描到。规则如下：

- 按照 Twitter(X) 的规则，图片 15 位随机 key ，视频 16 位
- 与后缀无关
- 与目录结构无关

## 许可证

GPLv3