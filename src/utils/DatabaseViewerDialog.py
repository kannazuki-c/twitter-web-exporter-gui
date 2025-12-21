# -*- coding: utf-8 -*-
# @Author: 神无月可乐
# @Create at: 2025/12/13 01:03
import gc
import json
import os
import re

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QLabel, QTableWidget, QPushButton, QHBoxLayout, QCheckBox, QLineEdit, \
	QVBoxLayout, QMessageBox, QTextEdit, QTableWidgetItem, QWidget, QProgressDialog

from downloader import load_config, save_config, DownloadWindow
from i18n import t

import src.utils.globals as globals_module
from src.utils.DeleteConfirmationDialog import DeleteConfirmationDialog
from src.utils.DeleteRecordsThread import DeleteRecordsThread
from src.utils.MoveRecordsThread import MoveRecordsThread
from src.utils.SyncProgressDialog import SyncProgressDialog


class DatabaseViewerDialog(QDialog):
	def __init__(self):
		super().__init__()
		self.records = []
		self.downloaded_files = None
		self.progress_dialog = None
		self.setWindowTitle(t('database_records'))
		# 设置关闭时自动销毁，防止内存泄漏
		self.setAttribute(Qt.WA_DeleteOnClose, True)
		self.resize(900, 400)

		# 添加提示标签
		self.info_label = QLabel(t('table_hint'))
		self.info_label.setAlignment(Qt.AlignCenter)

		# 添加提示标签
		self.info_label2 = QLabel("")
		self.info_label2.setAlignment(Qt.AlignCenter)

		# 设置表格
		self.table = QTableWidget()
		self.table.setColumnCount(8)
		self.table.setHorizontalHeaderLabels([
			t('col_id'), t('col_created_at'), t('col_full_text'), t('col_author'),
			t('col_views'), t('col_url'), t('col_downloaded'), t('col_actions')
		])

		# 创建按钮
		self.refresh_btn = QPushButton(t('refresh'))
		self.check_image_urls_btn = QPushButton(t('check_undownloaded_images'))
		self.check_video_urls_btn = QPushButton(t('check_undownloaded_videos'))
		self.delete_outdated_record_btn = QPushButton(t('delete_outdated_records'))

		# 连接按钮点击事件
		self.refresh_btn.clicked.connect(self.refresh_table)
		self.check_image_urls_btn.clicked.connect(self.check_image_urls)
		self.check_video_urls_btn.clicked.connect(self.check_video_urls)
		self.delete_outdated_record_btn.clicked.connect(self.delete_outdated_record)

		# 按钮水平布局
		buttons_layout = QHBoxLayout()
		buttons_layout.addWidget(self.refresh_btn)
		buttons_layout.addWidget(self.check_image_urls_btn)
		buttons_layout.addWidget(self.check_video_urls_btn)
		buttons_layout.addWidget(self.delete_outdated_record_btn)

		# 加载配置
		self.config = load_config()
		self.base_path = self.config.get('download', 'base_path')

		# 加载精准匹配设置
		exact_match_enabled = self.config.getboolean('download', 'exact_match', fallback=False)

		# 创建精准匹配勾选框，并设置初始值（在连接信号之前设置，避免触发刷新）
		self.exact_match_checkbox = QCheckBox(t('exact_match'))
		self.exact_match_checkbox.setChecked(exact_match_enabled)
		self.exact_match_checkbox.stateChanged.connect(self.on_exact_match_changed)

		path_layout = QHBoxLayout()
		path_label = QLabel(t('media_scan_path'))
		self.path_input = QLineEdit(self.base_path)
		# 连接路径变化信号
		self.path_input.textChanged.connect(self.on_path_changed)
		path_layout.addWidget(path_label)
		path_layout.addWidget(self.path_input)
		path_layout.addWidget(self.exact_match_checkbox)

		# 主布局
		layout = QVBoxLayout()
		layout.addWidget(self.table)
		layout.addLayout(path_layout)
		layout.addLayout(buttons_layout)  # 添加按钮布局
		layout.addWidget(self.info_label)
		layout.addWidget(self.info_label2)
		self.setLayout(layout)

		self.refresh_table()

	def on_path_changed(self, text):
		"""路径改变时保存到配置"""
		self.base_path = text
		self.config.set('download', 'base_path', text)
		save_config(self.config)

	def on_exact_match_changed(self, state):
		"""精准匹配状态改变时保存配置并刷新"""
		# 保存精准匹配状态到配置
		self.config.set('download', 'exact_match', str(self.exact_match_checkbox.isChecked()))
		save_config(self.config)
		self.refresh_table()

	def delete_outdated_record(self):
		# 创建一个消息框
		msg_box = QMessageBox()
		msg_box.setIcon(QMessageBox.Warning)
		msg_box.setWindowTitle(t('delete_records_title'))
		msg_box.setText(t('delete_records_msg'))

		# 添加按钮
		delete_button = msg_box.addButton(t('permanently_delete'), QMessageBox.AcceptRole)
		move_button = msg_box.addButton(t('move_to_deleted'), QMessageBox.ActionRole)
		cancel_button = msg_box.addButton(t('cancel'), QMessageBox.RejectRole)

		# 设置取消按钮为默认按钮
		msg_box.setDefaultButton(cancel_button)

		# 显示对话框并等待用户选择
		msg_box.exec()

		# 根据用户的选择执行相应的操作
		if msg_box.clickedButton() == delete_button:
			self.secondary_operation_confirmation("del")
		elif msg_box.clickedButton() == move_button:
			self.secondary_operation_confirmation("mov")

	def secondary_operation_confirmation(self, operation_type):
		# 收集需要删除的记录
		records_to_delete = [record for record in self.records if record.get("_need_download") == 1]

		operation_type_text = t('operation_delete') if operation_type == "del" else t('operation_move')

		if not records_to_delete:
			QMessageBox.information(None, t('hint'), t('no_records_to_operate', operation=operation_type_text))
			return

		# 显示确认窗口
		confirmation_dialog = DeleteConfirmationDialog(records_to_delete, operation_type_text)
		if confirmation_dialog.exec() == QDialog.Accepted:
			# 用户确认删除
			if operation_type == "del":
				self.start_delete_records()
			elif operation_type == "mov":
				self.start_move_records()

	def start_delete_records(self):
		self.progress_dialog = SyncProgressDialog(self)
		self.progress_dialog.show()

		self.delete_thread = DeleteRecordsThread(self.records, globals_module.db)
		self.delete_thread.finished.connect(self.on_delete_finished)
		self.delete_thread.start()

	def on_delete_finished(self, count):
		self.progress_dialog.close()
		# 清理线程对象
		if hasattr(self, 'delete_thread'):
			self.delete_thread.deleteLater()
			self.delete_thread = None
		QMessageBox.information(self, t('operation_complete'), t('records_deleted', count=count))
		self.refresh_table()

	def start_move_records(self):
		self.progress_dialog = SyncProgressDialog(self)
		self.progress_dialog.show()

		# 从配置读取反转插入设置
		config = load_config()
		reverse_insert = config.getboolean('general', 'reverse_insert', fallback=True)
		self.move_thread = MoveRecordsThread(self.records, globals_module.db, globals_module.ddb, reverse_insert=reverse_insert)
		self.move_thread.finished.connect(self.on_move_finished)
		self.move_thread.start()

	def on_move_finished(self, count):
		self.progress_dialog.close()
		# 清理线程对象
		if hasattr(self, 'move_thread'):
			self.move_thread.deleteLater()
			self.move_thread = None
		QMessageBox.information(self, t('operation_complete'), t('records_moved', count=count))
		self.refresh_table()

	def check_image_urls(self):
		urls = []
		for record in self.records:
			if record.get("_need_download"):  # 并不代表一定有要下载的图片，也可能是视频，所以要做二次判断
				tasks = record.get("_photo_download_tasks")
				if tasks:
					for task in tasks:
						if self.is_need_download(task['idr']):
							urls.append(task['url'])

		# 标记是否进行了下载
		self.download_occurred = False

		# 使用局部变量，设置自动销毁
		dialog = QDialog(self)
		dialog.setAttribute(Qt.WA_DeleteOnClose, True)
		dialog.setWindowTitle(t('undownloaded_images_title', count=len(urls)))
		dialog.resize(400, 300)

		text_edit = QTextEdit()
		text_edit.setReadOnly(True)
		text_edit.setText("\n".join(urls))

		layout = QVBoxLayout()
		layout.addWidget(text_edit)

		# 创建按钮
		btn = QPushButton(t('download_all'))
		btn.setAutoDefault(False)
		btn.setEnabled(bool(urls))
		btn.clicked.connect(self.download_image_0)
		layout.addWidget(btn)

		# 创建按钮2
		btn2 = QPushButton(t('download_first_50'))
		btn2.setAutoDefault(False)
		btn2.setEnabled(bool(urls))
		btn2.clicked.connect(self.download_image_50)
		layout.addWidget(btn2)

		dialog.setLayout(layout)
		dialog.exec()

		# dialog关闭后，如果进行了下载才刷新主窗口
		if self.download_occurred:
			self.refresh_table()

	def download_image_0(self):
		started = self.download_image(-1)
		if started:
			self.download_occurred = True

	def download_image_50(self):
		started = self.download_image(50)
		if started:
			self.download_occurred = True

	def download_image(self, batch_size=-1):
		all_tasks = []
		for record in self.records:
			if record.get("_need_download", 0):
				tasks = record.get("_photo_download_tasks")
				if tasks:
					for task in tasks:
						if self.is_need_download(task['idr']):
							all_tasks.append(task)
		tasks_to_download = all_tasks if batch_size == -1 else all_tasks[:batch_size]
		download_window = DownloadWindow(tasks_to_download, base_path=self.base_path, parent=self)
		download_window.exec()

		# 返回是否进行了下载
		return download_window.download_started

	def check_video_urls(self):
		urls = []
		for record in self.records:
			if record.get("_need_download"):  # 同上
				tasks = record.get("_video_download_tasks")
				if tasks:
					for task in tasks:
						if self.is_need_download(task['idr']):
							urls.append(task['url'])

		# 标记是否进行了下载
		self.download_occurred = False

		# 使用局部变量，设置自动销毁
		dialog = QDialog(self)
		dialog.setAttribute(Qt.WA_DeleteOnClose, True)
		dialog.setWindowTitle(t('undownloaded_videos_title', count=len(urls)))
		dialog.resize(400, 300)

		text_edit = QTextEdit()
		text_edit.setReadOnly(True)
		text_edit.setText("\n".join(urls))

		layout = QVBoxLayout()
		layout.addWidget(text_edit)

		# 创建按钮
		btn = QPushButton(t('download'))
		btn.setAutoDefault(False)
		btn.setEnabled(bool(urls))
		btn.clicked.connect(self.download_video_wrapper)
		layout.addWidget(btn)

		dialog.setLayout(layout)
		dialog.exec()

		# dialog关闭后，如果进行了下载才刷新主窗口
		if self.download_occurred:
			self.refresh_table()

	def download_video_wrapper(self):
		"""视频下载包装器，用于设置下载标志"""
		started = self.download_video()
		if started:
			self.download_occurred = True

	def download_video(self):
		all_tasks = []
		for record in self.records:
			if record.get("_need_download", 0):
				tasks = record.get("_video_download_tasks")
				if tasks:
					for task in tasks:
						if self.is_need_download(task['idr']):
							all_tasks.append(task)
		download_window = DownloadWindow(all_tasks, base_path=self.base_path, parent=self)
		download_window.exec()

		# 返回是否进行了下载
		return download_window.download_started

	def is_need_download(self, idr):
		if self.exact_match_checkbox.isChecked():
			return idr not in self.downloaded_files
		else:
			return not any(
				idr in downloaded_file or downloaded_file in idr for downloaded_file in self.downloaded_files)

	def _extract_media_from_legacy(self, legacy: dict, record_id: str, photos: set, videos: set, 
								   err_photo_url_list: list, err_video_url_list: list) -> tuple:
		"""
		从 legacy 数据中提取媒体信息（用于引用推文）
		
		Args:
			legacy: legacy 数据字典
			record_id: 记录ID（用于下载任务）
			photos: 全局图片集合（用于去重）
			videos: 全局视频集合（用于去重）
			err_photo_url_list: 错误图片URL列表
			err_video_url_list: 错误视频URL列表
			
		Returns:
			(photo_ids, video_ids, photo_tasks, video_tasks) 元组
		"""
		photo_ids = []
		video_ids = []
		photo_tasks = []
		video_tasks = []
		
		# 优先使用 extended_entities，没有则使用 entities
		entities = legacy.get('extended_entities', legacy.get('entities', {}))
		media_list = entities.get('media', [])
		
		for media in media_list:
			media_type = media.get('type')
			if media_type == 'photo':
				media_url = media.get('media_url_https', '')
				if media_url:
					# 构造原图 URL
					url = f"{media_url}?format=jpg&name=orig"
					# 提取图片标识符
					match = re.search(r"/media/([A-Za-z0-9_-]+)\.", media_url)
					if match:
						identifier = match.group(1)
						if len(identifier) == 15:
							if identifier not in photos:
								photos.add(identifier)
								photo_ids.append(identifier)
								photo_tasks.append({
									"url": url, "file_name": identifier + ".jpg", "idr": identifier,
									"file_type": "photo", "record_id": record_id
								})
						else:
							err_photo_url_list.append(url)
					else:
						err_photo_url_list.append(media_url)
			elif media_type == 'video':
				# 视频需要从 video_info 中获取最高质量的 URL
				video_info = media.get('video_info', {})
				variants = video_info.get('variants', [])
				mp4_variants = [v for v in variants if v.get('content_type') == 'video/mp4']
				if mp4_variants:
					best_variant = max(mp4_variants, key=lambda x: x.get('bitrate', 0))
					url = best_variant.get('url', '')
					match = re.search(r"vid/[a-zA-Z0-9_/-]+/([A-Za-z0-9_-]+)\.mp4", url)
					if match:
						identifier = match.group(1)
						if len(identifier) == 16:
							if identifier not in videos:
								videos.add(identifier)
								video_ids.append(identifier)
								video_tasks.append({
									"url": url, "file_name": identifier + ".mp4", "idr": identifier,
									"file_type": "video", "record_id": record_id
								})
						else:
							err_video_url_list.append(url)
					else:
						err_video_url_list.append(url)
		
		return photo_ids, video_ids, photo_tasks, video_tasks

	def load_data(self):
		download_path = self.path_input.text()

		# 如果download文件夹不存在，则创建
		if not os.path.exists(download_path):
			os.makedirs(download_path)

		# 扫描/download/文件夹下的所有文件，使用 set 提升查找性能
		self.downloaded_files = set()
		for root, dirs, files in os.walk(download_path):
			for file in files:
				# 去除文件扩展名
				file_name_without_extension = os.path.splitext(file)[0]
				self.downloaded_files.add(file_name_without_extension)

		self.records = globals_module.db.all()[::-1]  # 按逆序加载
		self.table.setRowCount(len(self.records))

		# 设置每一行的高度，防止按钮被挤压
		row_height = 40  # 根据按钮大小调整行高
		for row in range(len(self.records)):
			self.table.setRowHeight(row, row_height)

		# 使用 set 进行去重检查，O(1) 查找
		photos = set()
		videos = set()
		err_photo_url_list = []
		err_video_url_list = []
		for row, record in enumerate(self.records):
			# 填入数据
			self.table.setItem(row, 0, QTableWidgetItem(str(record.get("id", ""))))
			self.table.setItem(row, 1, QTableWidgetItem(record.get("created_at", "")))
			self.table.setItem(row, 2, QTableWidgetItem(record.get("full_text", "")))
			self.table.setItem(row, 3, QTableWidgetItem(record.get("name", "")))
			self.table.setItem(row, 4, QTableWidgetItem(str(record.get("views_count", ""))))
			self.table.setItem(row, 5, QTableWidgetItem(record.get("url", "")))

			# 初始化临时映射变量
			record["_photos"] = []
			record["_videos"] = []
			record["_need_download"] = 1  # 内部标记 先记1 已下完就设0
			record["_photo_download_tasks"] = []
			record["_video_download_tasks"] = []

			# 手写匹配
			medias = record.get("media", [])
			for media in medias:
				if media.get("type") == "photo":
					url = media.get("original")
					match = re.search(r"media/([A-Za-z0-9_-]+)\?format=", url)

					if match:
						identifier = match.group(1)
						if len(identifier) == 15:
							if identifier not in photos:
								photos.add(identifier)
								record["_photos"].append(identifier)  # 建立映射
								record["_photo_download_tasks"].append(
									{"url": url, "file_name": identifier + ".jpg", "idr": identifier,
									 "file_type": "photo", "record_id": record["id"]})
						else:
							err_photo_url_list.append(url)
					else:
						err_photo_url_list.append(url)

				elif media.get("type") == "video":
					url = media.get("original")
					match = re.search(r"vid/[a-zA-Z0-9_/-]+/([A-Za-z0-9_-]+)\.mp4", url)

					if match:
						identifier = match.group(1)
						if len(identifier) == 16:
							if identifier not in videos:
								videos.add(identifier)
								record["_videos"].append(identifier)  # 建立映射
								record["_video_download_tasks"].append(
									{"url": url, "file_name": identifier + ".mp4", "idr": identifier,
									 "file_type": "video", "record_id": record["id"]})
						else:
							err_video_url_list.append(url)
					else:
						err_video_url_list.append(url)

			# 处理引用推文中的媒体
			metadata = record.get("metadata", {})
			quoted_result = metadata.get("quoted_status_result", {}).get("result", {})
			if quoted_result:
				quoted_legacy = quoted_result.get("legacy", {})
				if quoted_legacy:
					q_photo_ids, q_video_ids, q_photo_tasks, q_video_tasks = self._extract_media_from_legacy(
						quoted_legacy, record["id"], photos, videos, err_photo_url_list, err_video_url_list
					)
					record["_photos"].extend(q_photo_ids)
					record["_videos"].extend(q_video_ids)
					record["_photo_download_tasks"].extend(q_photo_tasks)
					record["_video_download_tasks"].extend(q_video_tasks)

			# 添加查看和删除按钮
			view_button = QPushButton(t('view'))
			view_button.clicked.connect(lambda _, r=record: self.view_record(r))
			delete_button = QPushButton(t('delete'))
			delete_button.clicked.connect(lambda _, r=record: self.delete_record(r))

			# 将按钮加入水平布局
			button_layout = QHBoxLayout()
			button_layout.addWidget(view_button)
			button_layout.addWidget(delete_button)
			button_widget = QWidget()
			button_widget.setLayout(button_layout)

			self.table.setCellWidget(row, 7, button_widget)

		# 更新“已下载”列
		for row, record in enumerate(self.records):
			media_downloaded = False
			if self.exact_match_checkbox.isChecked():
				media_downloaded = all(
					identifier in self.downloaded_files
					for identifier in record.get("_photos", []) + record.get("_videos", [])
				)
			else:
				media_downloaded = all(
					any(identifier in downloaded_file or downloaded_file in identifier
						for downloaded_file in self.downloaded_files)
					for identifier in record.get("_photos", []) + record.get("_videos", [])
				)

			def get_text():
				# 检查是否有媒体（包括引用推文的媒体）
				if not record.get("_photos", []) and not record.get("_videos", []):
					record["_need_download"] = 0
					return t('no_media')
				if media_downloaded:
					record["_need_download"] = 0
					return t('yes')
				photos_count = len(record.get("_photos", []))
				videos_count = len(record.get("_videos", []))
				media_parts = []

				if photos_count > 0:
					media_parts.append(t('images_count', count=photos_count))
				if videos_count > 0:
					media_parts.append(t('videos_count', count=videos_count))

				if media_parts:
					downloaded_status = t('not_downloaded') + "(" + " ".join(media_parts) + ")"
				else:
					downloaded_status = t('not_downloaded')

				return downloaded_status

			self.table.setItem(row, 6, QTableWidgetItem(get_text()))

		# 更新提示标签信息
		text = t('archived_stats', tweets=len(self.records), photos=len(photos), videos=len(videos))

		count = sum(1 for record in self.records if record.get("_need_download"))

		if count == 0:
			text += t('all_downloaded')
		else:
			text += t('tweets_need_download', count=count)

		failed_num = len(err_photo_url_list) + len(err_video_url_list)
		if failed_num:
			text += t('regex_failed', count=failed_num)
		self.info_label2.setText(text)
		# 数据加载完成，关闭进度对话框
		if self.progress_dialog:
			self.progress_dialog.close()

	def view_record(self, record):
		# 过滤掉以 _ 开头的键, 因为这是python的内部临时状态标记，不是原始推文数据
		filtered_record = {k: v for k, v in record.items() if not k.startswith('_')}
		self.view_text(t('view_record'), json.dumps(filtered_record, indent=4, ensure_ascii=False))

	def view_text(self, title, text):
		# 查看记录的窗口，使用局部变量，设置自动销毁
		dialog = QDialog(self)
		dialog.setAttribute(Qt.WA_DeleteOnClose, True)
		dialog.setWindowTitle(title)
		dialog.resize(400, 300)

		text_edit = QTextEdit()
		text_edit.setReadOnly(True)
		text_edit.setText(text)

		layout = QVBoxLayout()
		layout.addWidget(text_edit)
		dialog.setLayout(layout)
		dialog.exec()

	def delete_record(self, record):
		# 删除记录确认
		reply = QMessageBox.question(
			self, t('delete_confirm_title'), t('delete_confirm_msg'),
			QMessageBox.Yes | QMessageBox.No, QMessageBox.No
		)
		if reply == QMessageBox.Yes:
			globals_module.db.remove(tweet_id=record['id'])
			self.refresh_table()  # 删除后刷新表格

	def refresh_table(self):
		"""刷新表格"""
		# 显示进度窗口
		self.show_loading_indicator()

		# 先清理旧的 cellWidget，防止内存泄漏
		for row in range(self.table.rowCount()):
			widget = self.table.cellWidget(row, 7)
			if widget:
				widget.deleteLater()

		# 清空表格内容并加载数据
		self.table.clearContents()
		self.table.setRowCount(0)

		# 清空旧的 records 数据，释放内存
		self.records.clear()

		# 使用 QTimer 单独加载数据，以便进度窗口显示正常
		QTimer.singleShot(100, self.load_data)

	def show_loading_indicator(self):
		# 创建进度对话框
		self.progress_dialog = QProgressDialog(t('loading_data'), None, 0, 0, self)
		self.progress_dialog.setWindowModality(Qt.ApplicationModal)
		self.progress_dialog.setCancelButton(None)
		self.progress_dialog.setWindowTitle(t('please_wait_title'))
		self.progress_dialog.show()

	def closeEvent(self, event):
		"""关闭事件，清理内存"""
		# 清理表格中的 cellWidget
		for row in range(self.table.rowCount()):
			widget = self.table.cellWidget(row, 7)
			if widget:
				widget.deleteLater()
		self.table.clearContents()
		self.table.setRowCount(0)

		# 清空大数据，帮助垃圾回收
		self.records.clear()
		if self.downloaded_files:
			self.downloaded_files.clear()

		# 清理配置对象引用
		self.config = None

		event.accept()

		# 强制垃圾回收
		gc.collect()
