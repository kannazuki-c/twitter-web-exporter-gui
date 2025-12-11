import os
import re
import sys
import json
from PySide6.QtWidgets import (
	QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
	QProgressBar, QPushButton, QTableWidget, QTableWidgetItem, QDialog, QHBoxLayout,
	QMessageBox, QTextEdit, QListWidget, QCheckBox, QProgressDialog, QLineEdit, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QByteArray
from PySide6.QtGui import QScreen, QIcon, QPixmap, QFont
from tinydb import TinyDB, Query
from threading import Lock
from downloader import init_global_aria2_manager, shutdown_global_aria2_manager, load_config, save_config

# 全局配置
config = load_config()

# 初始化数据库（从配置文件读取）
db = TinyDB(config.get('database', 'main_db'))  # main db
ddb = TinyDB(config.get('database', 'deleted_db'))  # deleted db


class JSONProcessorThread(QThread):
	progress = Signal(int)
	completed = Signal(int)

	def __init__(self, file_path):
		super().__init__()
		self.file_path = file_path

	def run(self):
		try:
			# 1) 预加载 main db 与 deleted db 的所有 id（保证性能：集合 O(1) 查询）
			existing_ids = set()
			for store in (db, ddb):
				for rec in store.all():
					_id = rec.get('id')
					if _id is not None:
						existing_ids.add(_id)

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

			# 4) 批量插入（保持原来的逆序逻辑）
			if new_entries_list:
				db.insert_multiple(new_entries_list[::-1])

			self.progress.emit(100)
			self.completed.emit(len(new_entries_list))

		except Exception:
			self.completed.emit(-1)


class DeleteConfirmationDialog(QDialog):
	def __init__(self, records_to_delete, operation_type_text):
		super().__init__(None)
		self.setWindowTitle(f"确认{operation_type_text}记录")

		# 布局
		layout = QVBoxLayout()

		# 信息标签
		info_label = QLabel(f"以下记录将被{operation_type_text}，请确认：")
		layout.addWidget(info_label)

		# 列表显示要删除的记录
		self.record_list = QListWidget()
		for record in records_to_delete:
			self.record_list.addItem(f"{record['full_text']}")
		layout.addWidget(self.record_list)

		# 按钮
		self.confirm_button = QPushButton(f"确认{operation_type_text}")
		self.cancel_button = QPushButton("取消")
		layout.addWidget(self.confirm_button)
		layout.addWidget(self.cancel_button)

		# 信号连接
		self.confirm_button.clicked.connect(self.accept)
		self.cancel_button.clicked.connect(self.reject)

		self.setLayout(layout)

class SyncProgressDialog(QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("操作进行中")
		self.setWindowModality(Qt.ApplicationModal)  # 阻止与其他窗口交互
		self.setFixedSize(300, 100)

		layout = QVBoxLayout()
		label = QLabel("请稍候，正在执行操作...")
		layout.addWidget(label)

		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 0)  # 设置进度条为不确定模式
		layout.addWidget(self.progress_bar)

		self.setLayout(layout)

class DeleteRecordsThread(QThread):
	finished = Signal(int)  # 传递删除的记录数量

	def __init__(self, records, db):
		super().__init__()
		self.records = records
		self.db = db

	def run(self):
		need_delete_record_ids = [
			record.doc_id for record in self.records if record.get("_need_download") == 1
		]
		for record_id in need_delete_record_ids:
			self.db.remove(doc_ids=[record_id])

		self.finished.emit(len(need_delete_record_ids))  # 发送删除数量

class MoveRecordsThread(QThread):
	finished = Signal(int)  # 传递移动的记录数量

	def __init__(self, records, main_db, deleted_db_path='deleted.db'):
		super().__init__()
		self.records = records
		self.main_db = main_db
		self.deleted_db = TinyDB(deleted_db_path)

	def run(self):
		need_move_records = [
			record for record in self.records if record.get("_need_download") == 1
		]
		self.deleted_db.insert_multiple(need_move_records[::-1])

		need_move_record_ids = [record.doc_id for record in need_move_records]
		for record_id in need_move_record_ids:
			self.main_db.remove(doc_ids=[record_id])

		self.finished.emit(len(need_move_records))  # 发送移动数量

class DatabaseViewerDialog(QDialog):
	def __init__(self):
		super().__init__()
		self.records = []
		self.downloaded_files = None
		self.progress_dialog = None
		self.setWindowTitle("数据库记录")
		self.resize(900, 400)

		# 添加提示标签
		self.info_label = QLabel("所有数据可双击复制，但更改不会保存。")
		self.info_label.setAlignment(Qt.AlignCenter)

		# 添加提示标签
		self.info_label2 = QLabel("")
		self.info_label2.setAlignment(Qt.AlignCenter)

		# 设置表格
		self.table = QTableWidget()
		self.table.setColumnCount(8)
		self.table.setHorizontalHeaderLabels([
			"ID", "Created At", "Full Text", "Author", "浏览量", "Url", "已下载", "操作"
		])

		# 创建按钮
		self.refresh_btn = QPushButton("刷新")
		self.check_image_urls_btn = QPushButton("检查未下载的图片")
		self.check_video_urls_btn = QPushButton("检查未下载的视频")
		self.delete_outdated_record_btn = QPushButton("删除不需要的记录")

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
		self.exact_match_checkbox = QCheckBox("精准匹配(本地媒体文件名)")
		self.exact_match_checkbox.setChecked(exact_match_enabled)
		self.exact_match_checkbox.stateChanged.connect(self.on_exact_match_changed)

		path_layout = QHBoxLayout()
		path_label = QLabel("媒体扫描路径:")
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

		# 收集下载失败的record用于删除
		self.failed_record_list = []
		self.failed_record_lock = Lock()

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
		msg_box.setWindowTitle("删除不需要的记录")
		msg_box.setText(
			"你必须要知道你在做什么！\n\n此操作会检索包含未下载媒体的记录。如果你已经下载所有可被下载的媒体，那么剩下的就是失效的推文或你认为不需要的推文。\n\n你可以选择从库中彻底删除记录，或将它们移到另一个文件中：deleted.db\n\n这不是最终决定。在选择处理方式后，我们会收集所有符合条件的失效记录，然后等待你的再次确认。")

		# 添加按钮
		delete_button = msg_box.addButton("彻底删除记录", QMessageBox.AcceptRole)
		move_button = msg_box.addButton("移动到 deleted.db", QMessageBox.ActionRole)
		cancel_button = msg_box.addButton("取消", QMessageBox.RejectRole)

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

		operation_type_text = "删除" if operation_type == "del" else "移动"

		if not records_to_delete:
			QMessageBox.information(None, "提示", f"没有需要{operation_type_text}的记录。")
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

		self.delete_thread = DeleteRecordsThread(self.records, db)
		self.delete_thread.finished.connect(self.on_delete_finished)
		self.delete_thread.start()

	def on_delete_finished(self, count):
		self.progress_dialog.close()
		QMessageBox.information(self, "操作完成", f"{count} 条记录已删除")
		self.refresh_table()

	def start_move_records(self):
		self.progress_dialog = SyncProgressDialog(self)
		self.progress_dialog.show()

		self.move_thread = MoveRecordsThread(self.records, db)
		self.move_thread.finished.connect(self.on_move_finished)
		self.move_thread.start()

	def on_move_finished(self, count):
		self.progress_dialog.close()
		QMessageBox.information(self, "操作完成", f"{count} 条记录已移动到 deleted.db")
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

		self.dialog = QDialog(self)
		self.dialog.setWindowTitle(f"未下载图片URL ({len(urls)})")
		self.dialog.resize(400, 300)

		text_edit = QTextEdit()
		text_edit.setReadOnly(True)
		text_edit.setText("\n".join(urls))

		layout = QVBoxLayout()
		layout.addWidget(text_edit)

		# 创建按钮
		btn = QPushButton("全部下载")
		btn.setAutoDefault(False)
		btn.setEnabled(bool(urls))
		btn.clicked.connect(self.download_image_0)
		layout.addWidget(btn)

		# 创建按钮2
		btn2 = QPushButton("下载前 100 条")
		btn2.setAutoDefault(False)
		btn2.setEnabled(bool(urls))
		btn2.clicked.connect(self.download_image_100)
		layout.addWidget(btn2)

		self.dialog.setLayout(layout)
		self.dialog.exec()
		
		# dialog关闭后，如果进行了下载才刷新主窗口
		if self.download_occurred:
			self.refresh_table()

	def download_image_0(self):
		started = self.download_image(-1)
		if started:
			self.download_occurred = True

	def download_image_100(self):
		started = self.download_image(100)
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
		from downloader import DownloadWindow
		tasks_to_download = all_tasks if batch_size == -1 else all_tasks[:batch_size]
		download_window = DownloadWindow(tasks_to_download, base_path=self.base_path, parent=self)
		download_window.exec()
		
		# 返回是否进行了下载
		return download_window.download_started

	def add_to_failed_record_list(self, record_id):
		with self.failed_record_lock:
			if record_id not in self.failed_record_list:
				self.failed_record_list.append(record_id)

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

		self.dialog = QDialog(self)
		self.dialog.setWindowTitle(f"未下载视频URL ({len(urls)})")
		self.dialog.resize(400, 300)

		text_edit = QTextEdit()
		text_edit.setReadOnly(True)
		text_edit.setText("\n".join(urls))

		layout = QVBoxLayout()
		layout.addWidget(text_edit)

		# 创建按钮
		btn = QPushButton("下载")
		btn.setAutoDefault(False)
		btn.setEnabled(bool(urls))
		btn.clicked.connect(self.download_video_wrapper)
		layout.addWidget(btn)

		self.dialog.setLayout(layout)
		self.dialog.exec()
		
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
		from downloader import DownloadWindow
		download_window = DownloadWindow(all_tasks, base_path=self.base_path, parent=self)
		download_window.exec()
		
		# 返回是否进行了下载
		return download_window.download_started

	def is_need_download(self, idr):
		if self.exact_match_checkbox.isChecked():
			return idr not in self.downloaded_files
		else:
			return not any(idr in downloaded_file or downloaded_file in idr for downloaded_file in self.downloaded_files)

	def load_data(self):
		download_path = self.path_input.text()

		# 如果download文件夹不存在，则创建
		if not os.path.exists(download_path):
			os.makedirs(download_path)

		# 扫描/download/文件夹下的所有文件
		self.downloaded_files = []
		for root, dirs, files in os.walk(download_path):
			for file in files:
				# 去除文件扩展名
				file_name_without_extension = os.path.splitext(file)[0]
				self.downloaded_files.append(file_name_without_extension)

		self.records = db.all()[::-1]  # 按逆序加载
		self.table.setRowCount(len(self.records))

		# 设置每一行的高度，防止按钮被挤压
		row_height = 40  # 根据按钮大小调整行高
		for row in range(len(self.records)):
			self.table.setRowHeight(row, row_height)

		photos = []
		err_photo_url_list = []
		videos = []
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
								photos.append(identifier)
								record["_photos"].append(identifier)  # 建立映射
								record["_photo_download_tasks"].append({"url": url, "file_name": identifier+".jpg", "idr": identifier, "file_type": "photo", "record_id": record["id"]})
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
								videos.append(identifier)
								record["_videos"].append(identifier)  # 建立映射
								record["_video_download_tasks"].append({"url": url, "file_name": identifier+".mp4", "idr": identifier, "file_type": "video", "record_id": record["id"]})
						else:
							err_video_url_list.append(url)
					else:
						err_video_url_list.append(url)

			# 添加查看和删除按钮
			view_button = QPushButton("查看")
			view_button.clicked.connect(lambda _, r=record: self.view_record(r))
			delete_button = QPushButton("删除")
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
				if not record.get("media", []):
					record["_need_download"] = 0
					return "无媒体"
				if media_downloaded:
					record["_need_download"] = 0
					return "是"
				photos_count = len(record.get("_photos", []))
				videos_count = len(record.get("_videos", []))
				media_parts = []

				if photos_count > 0:
					media_parts.append(f"图片{photos_count}张")
				if videos_count > 0:
					media_parts.append(f"视频{videos_count}条")

				if media_parts:
					downloaded_status = "未下载(" + " ".join(media_parts) + ")"
				else:
					downloaded_status = "未下载"

				return downloaded_status

			self.table.setItem(row, 6, QTableWidgetItem(get_text()))

		# 更新提示标签信息
		text = f"已归档{len(self.records)}条推文。扫描到{len(photos)}张图片和{len(videos)}条视频。"

		count = sum(1 for record in self.records if record.get("_need_download"))

		if count == 0:
			text += "所有推文媒体均已下载！"
		else:
			text += f"{count}条推文包含未下载的媒体。"

		if self.failed_record_list:
			text += f"包含{len(self.failed_record_list)}条失效推文。"
		failed_num = len(err_photo_url_list) + len(err_video_url_list)
		if failed_num:
			text += f"正则匹配失败{failed_num}条。"
		self.info_label2.setText(text)
		# 数据加载完成，关闭进度对话框
		if self.progress_dialog:
			self.progress_dialog.close()

	def view_record(self, record):
		# 过滤掉以 _ 开头的键, 因为这是python的内部临时状态标记，不是原始推文数据
		filtered_record = {k: v for k, v in record.items() if not k.startswith('_')}
		self.view_text("查看记录", json.dumps(filtered_record, indent=4, ensure_ascii=False))

	def view_text(self, title, text):
		# 查看记录的窗口
		self.dialog = QDialog(self)
		self.dialog.setWindowTitle(title)
		self.dialog.resize(400, 300)

		text_edit = QTextEdit()
		text_edit.setReadOnly(True)
		text_edit.setText(text)

		layout = QVBoxLayout()
		layout.addWidget(text_edit)
		self.dialog.setLayout(layout)
		self.dialog.exec()

	def delete_record(self, record):
		# 删除记录确认
		reply = QMessageBox.question(
			self, "删除确认", "确定要删除该记录吗？",
			QMessageBox.Yes | QMessageBox.No, QMessageBox.No
		)
		if reply == QMessageBox.Yes:
			db.remove(Query().id == record['id'])
			self.refresh_table()  # 删除后刷新表格

	def refresh_table(self):
		"""刷新表格"""
		# 显示进度窗口
		self.show_loading_indicator()

		# 清空表格内容并加载数据
		self.table.clearContents()

		# 使用 QTimer 单独加载数据，以便进度窗口显示正常
		QTimer.singleShot(100, self.load_data)

	def show_loading_indicator(self):
		# 创建进度对话框
		self.progress_dialog = QProgressDialog("正在加载数据...", None, 0, 0, self)
		self.progress_dialog.setWindowModality(Qt.ApplicationModal)
		self.progress_dialog.setCancelButton(None)
		self.progress_dialog.setWindowTitle("请稍候")
		self.progress_dialog.show()


class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("twegui v0.1.0")
		self.resize(500, 350)
		self.center_window()

		# 加载配置
		self.config = load_config()

		# 初始化 aria2 管理器
		self.aria2_status_label = QLabel("正在启动 aria2c...")
		self.aria2_status_label.setAlignment(Qt.AlignCenter)

		self.label = QLabel("拖放一个 JSON 文件到窗口")
		self.label.setAlignment(Qt.AlignCenter)
		self.progress_bar = QProgressBar()
		self.progress_bar.setValue(0)
		self.progress_bar.setVisible(False)
		self.open_db_button = QPushButton("查看数据库记录")
		self.open_db_button.clicked.connect(self.open_database_viewer)

		# 数据库文件选择控件
		db_layout = QHBoxLayout()
		db_label = QLabel("主数据库:")
		self.db_path_label = QLabel(self.config.get('database', 'main_db'))
		self.db_path_label.setStyleSheet("color: blue;")
		self.db_select_button = QPushButton("切换...")
		self.db_select_button.clicked.connect(self.select_main_db)
		db_layout.addWidget(db_label)
		db_layout.addWidget(self.db_path_label)
		db_layout.addWidget(self.db_select_button)
		db_layout.addStretch()

		# deleted 数据库文件选择控件
		ddb_layout = QHBoxLayout()
		ddb_label = QLabel("删除库:")
		self.ddb_path_label = QLabel(self.config.get('database', 'deleted_db'))
		self.ddb_path_label.setStyleSheet("color: blue;")
		self.ddb_select_button = QPushButton("切换...")
		self.ddb_select_button.clicked.connect(self.select_deleted_db)
		ddb_layout.addWidget(ddb_label)
		ddb_layout.addWidget(self.ddb_path_label)
		ddb_layout.addWidget(self.ddb_select_button)
		ddb_layout.addStretch()

		layout = QVBoxLayout()
		layout.addWidget(self.aria2_status_label)
		layout.addLayout(db_layout)
		layout.addLayout(ddb_layout)
		layout.addWidget(self.label)
		layout.addWidget(self.progress_bar)
		layout.addWidget(self.open_db_button)

		container = QWidget()
		container.setLayout(layout)
		self.setCentralWidget(container)

		self.setAcceptDrops(True)
		self.thread = None

		# 延迟启动 aria2（避免阻塞 UI）
		QTimer.singleShot(500, self.init_aria2)

	def center_window(self):
		screen = QScreen.availableGeometry(QApplication.primaryScreen())
		x = (screen.width() - self.width()) // 2
		y = (screen.height() - self.height()) // 2
		self.move(x, y)

	def init_aria2(self):
		"""初始化 aria2 守护进程"""
		aria2_manager = init_global_aria2_manager()
		if aria2_manager and aria2_manager.api:
			self.aria2_status_label.setText("aria2c 已启动")
			self.aria2_status_label.setStyleSheet("color: green;")
		else:
			self.aria2_status_label.setText("aria2c 启动失败（下载功能不可用）")
			self.aria2_status_label.setStyleSheet("color: red;")

	def closeEvent(self, event):
		"""窗口关闭事件"""
		# 关闭 aria2 守护进程
		shutdown_global_aria2_manager()
		event.accept()

	def dragEnterEvent(self, event):
		if event.mimeData().hasUrls():
			event.accept()
		else:
			event.ignore()

	def dropEvent(self, event):
		urls = event.mimeData().urls()
		if urls:
			file_path = urls[0].toLocalFile()
			if file_path.endswith(".json"):
				self.process_json(file_path)
			else:
				self.label.setText("请拖放一个 JSON 文件")

	def process_json(self, file_path):
		self.thread = JSONProcessorThread(file_path)
		self.thread.progress.connect(self.update_progress)
		self.thread.completed.connect(self.on_processing_completed)

		self.progress_bar.setValue(0)
		self.progress_bar.setVisible(True)
		self.label.setText("正在处理 JSON 文件...")

		self.thread.start()

	def update_progress(self, value):
		self.progress_bar.setValue(value)

	def on_processing_completed(self, new_entries):
		self.progress_bar.setVisible(False)
		if new_entries == -1:
			self.label.setText("JSON 文件内容格式错误或读取失败")
		else:
			self.label.setText(f"处理完成，新添加了 {new_entries} 条记录")

	def select_main_db(self):
		"""选择主数据库文件"""
		file_path, _ = QFileDialog.getSaveFileName(
			self,
			"选择或创建主数据库文件",
			os.getcwd(),
			"数据库文件 (*.db);;所有文件 (*.*)"
		)
		
		if file_path:
			# 如果用户没有输入扩展名，自动添加 .db
			if not file_path.endswith('.db'):
				file_path += '.db'
			
			# 更新全局数据库实例
			global db
			db.close()
			db = TinyDB(file_path)
			
			# 保存到配置
			self.config.set('database', 'main_db', file_path)
			save_config(self.config)
			
			# 更新显示
			self.db_path_label.setText(file_path)
			
			# 判断是新建还是打开
			if os.path.exists(file_path):
				QMessageBox.information(self, "切换成功", f"已切换到数据库: {file_path}")
			else:
				QMessageBox.information(self, "创建成功", f"已创建并切换到新数据库: {file_path}")
	
	def select_deleted_db(self):
		"""选择删除数据库文件"""
		file_path, _ = QFileDialog.getSaveFileName(
			self,
			"选择或创建删除数据库文件",
			os.getcwd(),
			"数据库文件 (*.db);;所有文件 (*.*)"
		)
		
		if file_path:
			# 如果用户没有输入扩展名，自动添加 .db
			if not file_path.endswith('.db'):
				file_path += '.db'
			
			# 更新全局数据库实例
			global ddb
			ddb.close()
			ddb = TinyDB(file_path)
			
			# 保存到配置
			self.config.set('database', 'deleted_db', file_path)
			save_config(self.config)
			
			# 更新显示
			self.ddb_path_label.setText(file_path)
			
			# 判断是新建还是打开
			if os.path.exists(file_path):
				QMessageBox.information(self, "切换成功", f"已切换到数据库: {file_path}")
			else:
				QMessageBox.information(self, "创建成功", f"已创建并切换到新数据库: {file_path}")

	def open_database_viewer(self):
		self.db_viewer = DatabaseViewerDialog()
		self.db_viewer.exec()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	app.setFont(QFont("Cascadia Mono, Microsoft YaHei", 8))

	# 将 Base64 编码转换为 QIcon，并设置全局图标
	base64_icon_data = "AAABAAEAQEAAAAEAIAAoQgAAFgAAACgAAABAAAAAgAAAAAEAIAAAAAAAAEAAABMLAAATCwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADf378A3+C9AN/ktQDf28cA3tnOAN3bzgDd2s0A3NvNANzbzQDd28wA3NrNANzazQDd280A3dvOAN3bzgDd284A3dvOAN3bzgDd280A3NrNANzazQDc2c4A3NrNANzazQDc280A3NzNANnZywDW1tAA0tLYANTU1QDU1NQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAL+/vwC1tbkAAAAAANHRygDa2s0A3NvNANzazgDc2s0A3drOANzbzQDc2dEA5Nu5AN/YzgDc280A3drNANzbzQDb280A3NvMANzazQDc2s0A3dvNAN3bzgDd284A3dvOAN3bzgDd284A3dvNANzazQDc2s0A3NnOANzazQDc2c0A3NvNANvczADY2csAztDSAODeygDc284A3drNANzbzgDc2s4A29vOANvbzwDf384A7u7IAOfnywDl5cwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMzMzADDw8sA///QANfXzQDb280A3NrNAODfzwC3ucEA2trNANzbzQDc2c4A3NrNAN3azgDc284A3NrOANvb0wDi0c0B3NvNBd3ZzQjb3MwK29vNDNzbzA/c2s0Q3NrNEd3bzRLd284U3dvOFN3bzhTd284U3dvOFN3bzRLc2s0R3NrNENzZzg/c2c0N3NnNCtvczAfa3MsFz9XEAubhywDe3M0A3NvOAN3azQDc284A3NrOANvbzQDa288A4uTPANnWzgDd2s0A3NrOAN3czgDf4MwA3t7NAN7ezQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA2dnKANnZygDX2cgA2tjMAN/dzQDT1cwA29vNANzbzgDd3M4A4+HPANbZzAPb28wK3NnOENzazRfd2s4d3NvOIdzazSbd280v3drOPt3bzkzd2s5X3NvNYNzbzmnd281y3NrNeNzazXvd282B3dvOhd3bzoXd286F3dvOhd3bzoXd282A3NrNe9zazXnc2s5z3NrOa9zazWHc285W3NvNS9zazT/c2s4x3NvOJ9zbziLd2s0d3NvOGNzazhLa2s0L2NvQBNjTywDc2c0A3NrNANzZzgDd3M4A08rTANzbzgDf3c0AAAD/AOnqywDl5cwAAAAAAAAAAAAAAAAA29vNANrbzADa2ssAt8igANrZywDd280A5eHOANvbzQjd284U3NvNHtvazSzc281F3NvNYNzaznnc2s6S3drOqdzbzrvc2s3L3tvO197bztzf3M7f39zO4t/czeXg3M3n4NzN6eDczevg3M3s4NzN7eDcze7g3M3u4NzN7uDcze7g3M3u4NzN7eDczezg3M3r4NzN6uDczefg3M3l39zN4t/czt/f3M7c3tvO2N3bzc3c28683drOqtzbzpfc285+3NvOZNzbzkrd280x3drNIdzazRfc2c8M39/PAtvZzgDc284A397NANbR0ADh4M0A3tzOAN3azgAAAAAAAAAAANvbzQDb280A2tvMAN3c0ADZ2ckE29rNFtvazS3c285Z3dvOhdzbzazc283N3dvO3d3bzuXe287r39zO8t/czffg3M383tzO/9naz//T19D/ztbR/8vU0v/I09L/xtLT/8XS0//F0dP/xNHT/8PQ0//D0NP/w9DT/8PQ0//D0NP/w9DT/8PQ0//E0dP/xNHT/8XR0//G0tP/yNPS/8rU0v/N1dH/0dfQ/9bZz//c287/39zN/ODczfjf3M7z3tvO7d3bzubd287f3NrN1N3a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AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA////////////////////////////////////////////////////////////////////////////////////////AAAAAf///wAAAAAAAf/wAAAAAAAAH8AAAAAAAAADgAAAAAAAAAGAAAAAAAAAAYAAAAAAAAABgAAAAAAAAAGAAAAAAAAAAYAAAAAAAAABgAAAAAAAAAGAAAAAAAAAAYAAAAAAAAABwAAAAAAAAAPwAAAAAAAAD/8AAAAAAAD//4AAAAAAAf//gAAAAAAB///AAAAAAAP//8AAAAAAA///wAAAAAAD///AAAAAAAP//+AAAAAAB///4AAAAAAH///gAAAAAAf///AAAAAAD///8AAAAAAP///wAAAAAA////AAAAAAD///+AAAAAAf///4AAAAAB////gAAAAAH////AAAAAA////8AAAAAD////wAAAAAP////AAAAAA////+AAAAAH////4AAAAAf////8AAAAP///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8="

	icon_data = QByteArray.fromBase64(base64_icon_data.encode('utf-8'))
	pixmap = QPixmap()
	pixmap.loadFromData(icon_data)
	app_icon = QIcon(pixmap)
	app.setWindowIcon(app_icon)  # 设置为全局图标

	window = MainWindow()
	window.show()
	sys.exit(app.exec())
