# -*- coding: utf-8 -*-
# @Author: 神无月可乐
# @Create at: 2025/12/13 01:04
from PySide6.QtCore import QThread, Signal


class MoveRecordsThread(QThread):
	finished = Signal(int)  # 传递移动的记录数量

	def __init__(self, records, main_db, deleted_db, reverse_insert=True):
		super().__init__()
		self.records = records
		self.main_db = main_db
		self.deleted_db = deleted_db
		self.reverse_insert = reverse_insert

	def run(self):
		need_move_records = [
			record for record in self.records if record.get("_need_download") == 1
		]

		# 清理临时字段后插入到删除数据库
		clean_records = []
		for record in need_move_records:
			clean_record = {k: v for k, v in record.items() if not k.startswith('_') and k != 'doc_id'}
			clean_records.append(clean_record)

		# 根据设置决定是否反转顺序插入
		if self.reverse_insert:
			self.deleted_db.insert_multiple(clean_records)
		else:
			self.deleted_db.insert_multiple(clean_records[::-1])

		# 批量删除
		need_move_record_ids = [record.get('doc_id') for record in need_move_records]
		if need_move_record_ids:
			self.main_db.remove(doc_ids=need_move_record_ids)

		self.finished.emit(len(need_move_records))  # 发送移动数量
