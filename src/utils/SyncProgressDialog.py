# -*- coding: utf-8 -*-
# @Author: 神无月可乐
# @Create at: 2025/12/13 01:02
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar

from i18n import t


class SyncProgressDialog(QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle(t('operation_in_progress'))
		self.setWindowModality(Qt.ApplicationModal)  # 阻止与其他窗口交互
		self.setFixedSize(300, 100)

		layout = QVBoxLayout()
		label = QLabel(t('please_wait'))
		layout.addWidget(label)

		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 0)  # 设置进度条为不确定模式
		layout.addWidget(self.progress_bar)

		self.setLayout(layout)
