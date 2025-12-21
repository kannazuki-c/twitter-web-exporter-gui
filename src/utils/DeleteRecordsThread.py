# -*- coding: utf-8 -*-
# @Author: 神无月可乐
# @Create at: 2025/12/13 01:04
from PySide6.QtCore import QThread, Signal


class DeleteRecordsThread(QThread):
	finished = Signal(int)  # 传递删除的记录数量

	def __init__(self, records, db):
		super().__init__()
		self.records = records
		self.db = db

	def run(self):
		need_delete_record_ids = [
			record.get('doc_id') for record in self.records if record.get("_need_download") == 1
		]
		# 批量删除
		if need_delete_record_ids:
			self.db.remove(doc_ids=need_delete_record_ids)

		self.finished.emit(len(need_delete_record_ids))  # 发送删除数量
