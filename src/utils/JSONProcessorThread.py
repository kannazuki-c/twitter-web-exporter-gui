# -*- coding: utf-8 -*-
# @Author: 神无月可乐
# @Create at: 2025/12/13 01:00
import json

from PySide6.QtCore import QThread, Signal

import src.utils.globals as globals_module


class JSONProcessorThread(QThread):
	progress = Signal(int)
	completed = Signal(int)

	def __init__(self, file_path, reverse_insert=True):
		super().__init__()
		self.file_path = file_path
		self.reverse_insert = reverse_insert

	def run(self):
		try:
			# 1) 预加载 main db 与 deleted db 的所有 id（使用高性能方法）
			existing_ids = globals_module.db.get_all_ids() | globals_module.ddb.get_all_ids()

			# 2) 读取 JSON 文件
			with open(self.file_path, "r", encoding="utf-8") as f:
				data = json.load(f)

			if not isinstance(data, list):
				self.completed.emit(-1)
				return

			new_entries_list = []
			total_entries = len(data) or 1  # 防止除零

			# 3) 只添加：不在 main db 且不在 deleted db 的条目
			for i, entry in enumerate(data):
				_id = entry.get('id')
				if _id and _id not in existing_ids:
					new_entries_list.append(entry)
					# 写入前就把 id 放进集合，避免 JSON 内部重复
					existing_ids.add(_id)

				if i % 10 == 0:
					self.progress.emit(int(i * 100 / total_entries))

			# 4) 批量插入
			if new_entries_list:
				# 根据设置决定是否反转顺序插入
				if self.reverse_insert:
					globals_module.db.insert_multiple(new_entries_list)
				else:
					globals_module.db.insert_multiple(new_entries_list[::-1])

			self.progress.emit(100)
			self.completed.emit(len(new_entries_list))

		except Exception:
			self.completed.emit(-1)
