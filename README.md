## twitter-web-exporter-gui

一个第三方 gui 用于归档或整理 [twitter-web-exporter](https://github.com/prinsss/twitter-web-exporter) 导出的数据（以JSON文件格式）。扫描 Tweets 中的未下载媒体文件，并下载它们，以便随时迁移。

![GitHub commits since latest release](https://img.shields.io/github/commits-since/unikevin/twitter-web-exporter-gui/latest) ![Static Badge](https://img.shields.io/badge/license-GPLv3-c) ![Static Badge](https://img.shields.io/badge/python-a?logo=python&logoColor=white&labelColor=gray&color=blue)

![](https://github.com/user-attachments/assets/13c40789-2b71-4c0b-8624-cfd216fb8f87)

## 基本目录结构

- twegui.exe 主程序
- download/ 存放下载的媒体
- a.db 数据库

## 🔍我的Tweets如何保存？

所有 Tweets 将保存在一个 a.db 文件（由 [TinyDB](https://github.com/msiemens/tinydb) 驱动）中，并可通过拖拽 JSON 文件进行增量更新。当你拖入一段导出的 JSON，gui 会将新增书签插入库中。

![](https://github.com/user-attachments/assets/eb82e9b3-5301-4715-b101-6a54c9d523ed)

## 💾增量更新

通过多次导入，你的 Tweets 会被按加入时间保存。最新的会在最上方。仅需维护一个 a.db 文件，随时打包带走🚚，不会有重复。

![](https://github.com/user-attachments/assets/a5052a9f-087b-42ff-aca9-b42332c500fc)

## 📦下载所有媒体文件！

gui 还集成了 Tweets 中图片与视频的扫描、下载功能，在导入 Tweets 后，“已下载” 列会显示关联此 Tweets 的媒体是否已存在您的硬盘当中(*)。对于未下载的媒体，你可以选择：
1.使用内建下载
2.导出所有图片/视频的 URL ，复制到队列下载工具（如IDM，FDM）中批量下载

![](https://github.com/user-attachments/assets/3e231781-00f6-45b5-9813-cbbc69bc0f58)

## *gui如何检测关联媒体是否已下载？

您可选择被扫描的目录，只要保持原始的媒体文件名就可以被扫描到。规则如下：

- 按照 Twitter(X) 的规则，图片 15 位随机 key ，视频 16 位
- 与后缀无关
- 与目录结构无关

## 许可证

GPLv3