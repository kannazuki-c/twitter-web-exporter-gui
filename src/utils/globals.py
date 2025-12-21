# -*- coding: utf-8 -*-
# 全局数据库实例
# 用于避免循环导入问题

import os
from database import TweetDatabase, is_tinydb_file
from downloader import load_config

# 初始化数据库（从配置文件读取）- 使用 SQLite
# 如果配置的数据库文件扩展名是 .db 但内容是 TinyDB 格式，提示用户迁移
config = load_config()
main_db_path = config.get('database', 'main_db')
deleted_db_path = config.get('database', 'deleted_db')


def get_sqlite_path(path):
	"""获取 SQLite 数据库路径（扩展名为 .sqlite）"""
	base, ext = os.path.splitext(path)
	if ext.lower() == '.db':
		return base + '.sqlite'
	return path


# 如果是旧的 TinyDB 文件，使用新的 SQLite 路径
if is_tinydb_file(main_db_path):
	# 保持旧路径以便迁移，使用新路径创建 SQLite 数据库
	main_db_path = get_sqlite_path(main_db_path)
elif not os.path.exists(main_db_path):
	# 新建数据库时使用 .sqlite 扩展名
	main_db_path = get_sqlite_path(main_db_path)

if is_tinydb_file(deleted_db_path):
	deleted_db_path = get_sqlite_path(deleted_db_path)
elif not os.path.exists(deleted_db_path):
	deleted_db_path = get_sqlite_path(deleted_db_path)

db = TweetDatabase(main_db_path)  # main db (SQLite)
ddb = TweetDatabase(deleted_db_path)  # deleted db (SQLite)
