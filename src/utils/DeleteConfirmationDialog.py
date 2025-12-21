# -*- coding: utf-8 -*-
# @Author: 神无月可乐
# @Create at: 2025/12/13 01:00
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QPushButton

from i18n import t


class DeleteConfirmationDialog(QDialog):
	def __init__(self, records_to_delete, operation_type_text):
		super().__init__(None)
		self.setWindowTitle(t('confirm_operation', operation=operation_type_text))

		# 布局
		layout = QVBoxLayout()

		# 信息标签
		info_label = QLabel(t('records_to_operate', operation=operation_type_text))
		layout.addWidget(info_label)

		# 列表显示要删除的记录
		self.record_list = QListWidget()
		for record in records_to_delete:
			self.record_list.addItem(f"{record['full_text']}")
		layout.addWidget(self.record_list)

		# 按钮
		self.confirm_button = QPushButton(t('confirm_btn', operation=operation_type_text))
		self.cancel_button = QPushButton(t('cancel'))
		layout.addWidget(self.confirm_button)
		layout.addWidget(self.cancel_button)

		# 信号连接
		self.confirm_button.clicked.connect(self.accept)
		self.cancel_button.clicked.connect(self.reject)

		self.setLayout(layout)
