# -*- coding: utf-8 -*-
# @Author: 神无月可乐
# @Create at: 2025/12/13 01:05
import os

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QGroupBox, QComboBox, QPushButton, QProgressBar, \
	QHBoxLayout, QFileDialog, QMessageBox

from database import MigrationHelper, is_tinydb_file
from i18n import t
import src.utils.globals as globals_module


class MigrationDialog(QDialog):
	"""数据迁移对话框"""

	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle(t('migration_dialog_title'))
		self.setMinimumWidth(500)
		self.migration_thread = None

		layout = QVBoxLayout()

		# 说明标签
		info_label = QLabel(t('migration_info'))
		info_label.setWordWrap(True)
		layout.addWidget(info_label)

		# TinyDB 文件选择
		source_group = QGroupBox(t('migration_source_group'))
		source_layout = QVBoxLayout()

		# 自动检测
		self.detected_files = MigrationHelper.detect_tinydb_files()

		if self.detected_files:
			self.source_combo = QComboBox()
			for f in self.detected_files:
				self.source_combo.addItem(os.path.basename(f), f)
			source_layout.addWidget(self.source_combo)
		else:
			self.source_combo = None
			no_file_label = QLabel(t('migration_no_files'))
			source_layout.addWidget(no_file_label)

		# 手动选择按钮
		self.browse_btn = QPushButton(t('browse'))
		self.browse_btn.clicked.connect(self.browse_source)
		source_layout.addWidget(self.browse_btn)

		self.source_path_label = QLabel("")
		self.source_path_label.setStyleSheet("color: gray;")
		source_layout.addWidget(self.source_path_label)

		source_group.setLayout(source_layout)
		layout.addWidget(source_group)

		# 目标数据库选择
		target_group = QGroupBox(t('migration_target_group'))
		target_layout = QVBoxLayout()

		self.target_combo = QComboBox()
		self.target_combo.addItem(t('migration_target_main'), "main")
		self.target_combo.addItem(t('migration_target_deleted'), "deleted")
		target_layout.addWidget(self.target_combo)

		target_group.setLayout(target_layout)
		layout.addWidget(target_group)

		# 进度条
		self.progress_bar = QProgressBar()
		self.progress_bar.setVisible(False)
		layout.addWidget(self.progress_bar)

		# 状态标签
		self.status_label = QLabel("")
		layout.addWidget(self.status_label)

		# 按钮
		btn_layout = QHBoxLayout()
		self.migrate_btn = QPushButton(t('migration_start'))
		self.migrate_btn.clicked.connect(self.start_migration)
		self.close_btn = QPushButton(t('close'))
		self.close_btn.clicked.connect(self.close)
		btn_layout.addWidget(self.migrate_btn)
		btn_layout.addWidget(self.close_btn)
		layout.addLayout(btn_layout)

		self.setLayout(layout)
		self.custom_source_path = None

	def browse_source(self):
		"""浏览选择源文件"""
		file_path, _ = QFileDialog.getOpenFileName(
			self,
			t('migration_select_source'),
			os.getcwd(),
			t('db_filter')
		)
		if file_path:
			self.custom_source_path = file_path
			self.source_path_label.setText(t('migration_selected', path=file_path))

	def get_source_path(self):
		"""获取源文件路径"""
		if self.custom_source_path:
			return self.custom_source_path
		if self.source_combo and self.source_combo.currentData():
			return self.source_combo.currentData()
		return None

	def start_migration(self):
		"""开始迁移"""
		source_path = self.get_source_path()
		if not source_path:
			QMessageBox.warning(self, t('error'), t('migration_no_source'))
			return

		if not os.path.exists(source_path):
			QMessageBox.warning(self, t('error'), t('migration_file_not_found', path=source_path))
			return

		if not is_tinydb_file(source_path):
			QMessageBox.warning(self, t('error'), t('migration_invalid_file'))
			return

		# 确定目标数据库
		target = self.target_combo.currentData()
		target_db = globals_module.db if target == "main" else globals_module.ddb

		# 开始迁移
		self.migrate_btn.setEnabled(False)
		self.progress_bar.setVisible(True)
		self.progress_bar.setValue(0)
		self.status_label.setText(t('migration_in_progress'))

		self.migration_thread = MigrationThread(source_path, target_db)
		self.migration_thread.progress.connect(self.on_progress)
		self.migration_thread.completed.connect(self.on_completed)
		self.migration_thread.start()

	def on_progress(self, current, total):
		"""更新进度"""
		if total > 0:
			self.progress_bar.setValue(int(current * 100 / total))
			self.status_label.setText(t('migration_progress', current=current, total=total))

	def on_completed(self, migrated, skipped, errors):
		"""迁移完成"""
		self.migrate_btn.setEnabled(True)
		self.progress_bar.setValue(100)

		if migrated == -1:
			self.status_label.setText(t('migration_failed'))
			QMessageBox.critical(self, t('error'), t('migration_error'))
		else:
			self.status_label.setText(t('migration_complete_status', migrated=migrated, skipped=skipped, errors=errors))
			QMessageBox.information(
				self, t('migration_complete'),
				t('migration_result', migrated=migrated, skipped=skipped, errors=errors)
			)
class MigrationThread(QThread):
	"""数据迁移线程"""
	progress = Signal(int, int)  # current, total
	completed = Signal(int, int, int)  # migrated, skipped, errors

	def __init__(self, tinydb_path, sqlite_db):
		super().__init__()
		self.tinydb_path = tinydb_path
		self.sqlite_db = sqlite_db

	def run(self):
		try:
			migrated, skipped, errors = MigrationHelper.migrate_from_tinydb(
				self.tinydb_path,
				self.sqlite_db,
				progress_callback=lambda c, t: self.progress.emit(c, t)
			)
			self.completed.emit(migrated, skipped, errors)
		except Exception as e:
			print(f"迁移失败: {e}")
			self.completed.emit(-1, -1, -1)
