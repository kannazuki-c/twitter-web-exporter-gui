# -*- coding: utf-8 -*-
# @Author: 神无月可乐
# @Create at: 2025/12/13 01:18
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QScreen
from PySide6.QtWidgets import (
	QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
	QProgressBar, QPushButton, QHBoxLayout,
	QMessageBox, QCheckBox, QFileDialog,
	QComboBox, QGroupBox, QSpinBox, QFrame, QMenu
)

from database import TweetDatabase, is_tinydb_file
from downloader import init_global_aria2_manager, shutdown_global_aria2_manager, load_config, save_config, Aria2SettingsDialog, global_aria2_manager
from i18n import t, set_language, get_language, get_available_languages
import src.utils.globals as globals_module
from src.utils.DatabaseViewerDialog import DatabaseViewerDialog
from src.utils.JSONProcessorThread import JSONProcessorThread
from src.utils.MediaDownloadCheckThread import MediaDownloadCheckThread
from src.utils.Migration import MigrationDialog
from src.utils.WebServerCheckThread import WebServerCheckThread
from src.utils.ProfileImageCacheDialog import ProfileImageCacheDialog
from src.utils.RestorePointManager import RestorePointManager
from src.utils.RestorePointDialog import RestorePointInputDialog, RestorePointListDialog
from webserver import start_web_server, stop_web_server, is_server_running, get_server_url, set_allow_delete


class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle(t('app_title'))
		self.resize(500, 480)
		self.center_window()

		# 加载配置
		self.config = load_config()

		# 语言选择控件
		lang_layout = QHBoxLayout()
		lang_label = QLabel(t('language'))
		self.lang_combo = QComboBox()
		available_langs = get_available_languages()
		for lang_code, lang_name in available_langs.items():
			self.lang_combo.addItem(lang_name, lang_code)
		# 设置当前语言
		current_lang = get_language()
		index = self.lang_combo.findData(current_lang)
		if index >= 0:
			self.lang_combo.setCurrentIndex(index)
		self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
		lang_layout.addWidget(lang_label)
		lang_layout.addWidget(self.lang_combo)
		
		# "更多"菜单按钮
		self.more_menu_btn = QPushButton(t('more_menu'))
		self.more_menu = QMenu(self)
		self.download_settings_action = self.more_menu.addAction(t('aria2_settings'))
		self.download_settings_action.triggered.connect(self.open_download_settings)
		self.profile_cache_action = self.more_menu.addAction(t('profile_cache_btn'))
		self.profile_cache_action.triggered.connect(self.open_profile_cache_dialog)
		self.more_menu_btn.setMenu(self.more_menu)
		
		# Github 按钮
		self.github_btn = QPushButton("Github")
		self.github_btn.clicked.connect(self.open_github)
		lang_layout.addStretch()
		lang_layout.addWidget(self.more_menu_btn)
		lang_layout.addWidget(self.github_btn)


		# 初始化 aria2 管理器
		self.aria2_status_label = QLabel(t('starting_aria2'))
		self.aria2_status_label.setAlignment(Qt.AlignCenter)

		# 导入 JSON 按钮和拖放提示
		import_layout = QHBoxLayout()
		import_layout.addStretch()
		self.import_json_btn = QPushButton(t('import_json_btn'))
		self.import_json_btn.clicked.connect(self.import_json_file)
		import_layout.addWidget(self.import_json_btn)
		self.label = QLabel(t('drop_json_hint'))
		import_layout.addWidget(self.label)
		import_layout.addStretch()

		# 插入时反转顺序勾选框
		self.reverse_insert_checkbox = QCheckBox(t('reverse_insert_order'))
		reverse_insert_default = self.config.getboolean('general', 'reverse_insert', fallback=True)
		self.reverse_insert_checkbox.setChecked(reverse_insert_default)
		self.reverse_insert_checkbox.stateChanged.connect(self.on_reverse_insert_changed)
		self.progress_bar = QProgressBar()
		self.progress_bar.setValue(0)
		self.progress_bar.setVisible(False)
		self.open_db_button = QPushButton(t('view_database'))
		self.open_db_button.clicked.connect(self.open_database_viewer)

		# 数据库文件选择控件
		db_layout = QHBoxLayout()
		self.db_label = QLabel(t('main_db_label'))
		self.db_path_label = QLabel(globals_module.main_db_path)
		self.db_path_label.setStyleSheet("color: blue;")
		self.db_select_button = QPushButton(t('switch_btn'))
		self.db_select_button.clicked.connect(self.select_main_db)
		db_layout.addWidget(self.db_label)
		db_layout.addWidget(self.db_path_label)
		db_layout.addWidget(self.db_select_button)
		db_layout.addStretch()

		# deleted 数据库文件选择控件
		ddb_layout = QHBoxLayout()
		self.ddb_label = QLabel(t('deleted_db_label'))
		self.ddb_path_label = QLabel(globals_module.deleted_db_path)
		self.ddb_path_label.setStyleSheet("color: blue;")
		self.ddb_select_button = QPushButton(t('switch_btn'))
		self.ddb_select_button.clicked.connect(self.select_deleted_db)
		ddb_layout.addWidget(self.ddb_label)
		ddb_layout.addWidget(self.ddb_path_label)
		ddb_layout.addWidget(self.ddb_select_button)
		ddb_layout.addStretch()

		# 数据迁移按钮
		self.migrate_button = QPushButton(t('migrate_from_old_data'))
		self.migrate_button.clicked.connect(self.open_migration_dialog)

		# Web 服务器控制面板
		self.web_server_group = QGroupBox(t('web_server_btn'))
		web_server_layout = QVBoxLayout()

		# 第一行：端口和状态指示器
		web_row1 = QHBoxLayout()

		# 状态指示灯
		self.web_status_indicator = QLabel("●")
		self.web_status_indicator.setStyleSheet("color: #666666; font-size: 16px;")
		self.web_status_indicator.setFixedWidth(20)
		web_row1.addWidget(self.web_status_indicator)

		# 状态文本
		self.web_status_label = QLabel(t('web_server_status_off'))
		self.web_status_label.setStyleSheet("color: gray;")
		web_row1.addWidget(self.web_status_label)

		web_row1.addStretch()

		# 端口标签和输入
		self.port_label = QLabel(t('web_server_port_label'))
		web_row1.addWidget(self.port_label)

		self.web_port_spinbox = QSpinBox()
		self.web_port_spinbox.setRange(1024, 65535)
		# 从配置读取端口值（默认5001）
		port_default = self.config.getint('webserver', 'port', fallback=5001)
		self.web_port_spinbox.setValue(port_default)
		self.web_port_spinbox.setFixedWidth(80)
		self.web_port_spinbox.valueChanged.connect(self.on_port_changed)
		web_row1.addWidget(self.web_port_spinbox)

		web_server_layout.addLayout(web_row1)

		# 第二行：允许删除勾选框和自动启动勾选框
		web_row2 = QHBoxLayout()
		self.allow_delete_checkbox = QCheckBox(t('allow_remote_delete'))
		# 从配置读取默认值（默认False）
		allow_delete_default = self.config.getboolean('webserver', 'allow_delete', fallback=False)
		self.allow_delete_checkbox.setChecked(allow_delete_default)
		self.allow_delete_checkbox.stateChanged.connect(self.on_allow_delete_changed)
		web_row2.addWidget(self.allow_delete_checkbox)

		self.auto_start_checkbox = QCheckBox(t('auto_start_web_server'))
		# 从配置读取默认值（默认False）
		auto_start_default = self.config.getboolean('webserver', 'auto_start', fallback=False)
		self.auto_start_checkbox.setChecked(auto_start_default)
		self.auto_start_checkbox.stateChanged.connect(self.on_auto_start_changed)
		web_row2.addWidget(self.auto_start_checkbox)

		web_row2.addStretch()
		web_server_layout.addLayout(web_row2)

		# 第三行：启动/停止按钮
		web_row3 = QHBoxLayout()

		self.web_server_btn = QPushButton(t('web_server_btn'))
		self.web_server_btn.clicked.connect(self.toggle_web_server)
		web_row3.addWidget(self.web_server_btn)

		web_server_layout.addLayout(web_row3)

		# 第三行：访问 URL
		self.web_url_frame = QFrame()
		web_url_layout = QHBoxLayout()
		web_url_layout.setContentsMargins(0, 0, 0, 0)

		self.web_url_label = QLabel("")
		self.web_url_label.setStyleSheet("color: #3B82F6; font-weight: bold;")
		self.web_url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
		web_url_layout.addWidget(self.web_url_label)

		self.open_url_btn = QPushButton(t('web_server_open_url'))
		self.open_url_btn.setFixedWidth(60)
		self.open_url_btn.clicked.connect(self.open_web_url)
		web_url_layout.addWidget(self.open_url_btn)

		self.copy_url_btn = QPushButton(t('web_server_copy_url'))
		self.copy_url_btn.setFixedWidth(80)
		self.copy_url_btn.clicked.connect(self.copy_web_url)
		web_url_layout.addWidget(self.copy_url_btn)

		self.web_url_frame.setLayout(web_url_layout)
		self.web_url_frame.setVisible(False)
		web_server_layout.addWidget(self.web_url_frame)

		self.web_server_group.setLayout(web_server_layout)

		# 媒体检查状态容器（使用 QGroupBox 以匹配原生系统样式）
		self.media_check_group = QGroupBox(t('media_check_title'))
		media_check_layout = QHBoxLayout()

		# 状态指示灯
		self.media_check_indicator = QLabel("●")
		self.media_check_indicator.setFixedWidth(20)
		media_check_layout.addWidget(self.media_check_indicator)

		# 状态标签
		self.media_check_label = QLabel(t('media_check_checking'))
		self.media_check_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
		media_check_layout.addWidget(self.media_check_label, 1)

		# 刷新按钮
		self.media_check_refresh_btn = QPushButton(t('media_check_refresh'))
		self.media_check_refresh_btn.clicked.connect(self.check_undownloaded_media)
		media_check_layout.addWidget(self.media_check_refresh_btn)

		self.media_check_group.setLayout(media_check_layout)
		self.media_check_group.setVisible(False)  # 默认隐藏
		# 默认样式（检查中 - 灰色）
		self._media_check_state = 'checking'  # 保存当前状态
		self._update_media_check_style('checking')

		# 还原点管理器
		self.restore_point_manager = RestorePointManager()

		# 还原点容器
		self.restore_point_group = QGroupBox(t('restore_point_group'))
		restore_point_layout = QHBoxLayout()

		# 自动创建还原点勾选框
		self.auto_restore_checkbox = QCheckBox(t('restore_point_auto_create'))
		# 从配置读取默认值
		auto_restore_default = self.config.getboolean('restore_point', 'auto_create', fallback=False)
		self.auto_restore_checkbox.setChecked(auto_restore_default)
		self.auto_restore_checkbox.stateChanged.connect(self.on_auto_restore_changed)
		restore_point_layout.addWidget(self.auto_restore_checkbox)

		restore_point_layout.addStretch()

		# 创建还原点按钮
		self.create_restore_btn = QPushButton(t('restore_point_create_btn'))
		self.create_restore_btn.clicked.connect(lambda: self.create_restore_point(show_dialog=True))
		restore_point_layout.addWidget(self.create_restore_btn)

		# 从还原点还原按钮
		self.restore_from_btn = QPushButton(t('restore_point_restore_btn'))
		self.restore_from_btn.clicked.connect(self.restore_from_point)
		restore_point_layout.addWidget(self.restore_from_btn)

		self.restore_point_group.setLayout(restore_point_layout)

		layout = QVBoxLayout()
		layout.addLayout(lang_layout)
		layout.addWidget(self.aria2_status_label)
		layout.addLayout(db_layout)
		layout.addLayout(ddb_layout)
		layout.addLayout(import_layout)
		reverse_layout = QHBoxLayout()
		reverse_layout.addStretch()
		reverse_layout.addWidget(self.reverse_insert_checkbox)
		reverse_layout.addStretch()
		layout.addLayout(reverse_layout)
		layout.addWidget(self.progress_bar)
		layout.addWidget(self.restore_point_group)
		layout.addWidget(self.web_server_group)
		layout.addWidget(self.media_check_group)
		layout.addWidget(self.migrate_button)
		layout.addWidget(self.open_db_button)

		container = QWidget()
		container.setLayout(layout)
		self.setCentralWidget(container)

		self.setAcceptDrops(True)
		self.thread = None

		# Web 服务器启动检测相关
		self._web_check_thread = None
		self._web_server_url = ""

		# 媒体下载检测线程
		self._media_check_thread = None

		# 延迟启动 aria2（避免阻塞 UI）
		QTimer.singleShot(500, self.init_aria2)

		# 检查是否有旧数据需要迁移
		QTimer.singleShot(1000, self.check_migration_needed)

		# 检查是否需要自动启动 Web 服务器
		QTimer.singleShot(1500, self.check_auto_start_web_server)

	def on_language_changed(self, index):
		"""语言切换事件"""
		lang_code = self.lang_combo.itemData(index)
		set_language(lang_code)
		# 保存到配置
		self.config.set('general', 'language', lang_code)
		save_config(self.config)
		# 刷新界面文本
		self.refresh_ui_text()

	def open_github(self):
		"""在浏览器中打开 Github 仓库"""
		import webbrowser
		webbrowser.open("https://github.com/kannazuki-c/twitter-web-exporter-gui")

	def open_download_settings(self):
		"""打开下载设置对话框"""
		dialog = Aria2SettingsDialog(global_aria2_manager, self)
		dialog.exec()

	def refresh_ui_text(self):
		"""刷新界面文本"""
		self.setWindowTitle(t('app_title'))
		self.import_json_btn.setText(t('import_json_btn'))
		self.label.setText(t('drop_json_hint'))
		self.open_db_button.setText(t('view_database'))
		self.db_label.setText(t('main_db_label'))
		self.ddb_label.setText(t('deleted_db_label'))
		self.db_select_button.setText(t('switch_btn'))
		self.ddb_select_button.setText(t('switch_btn'))
		self.migrate_button.setText(t('migrate_from_old_data'))
		# 更新"更多"菜单按钮和菜单项
		self.more_menu_btn.setText(t('more_menu'))
		self.download_settings_action.setText(t('aria2_settings'))
		self.profile_cache_action.setText(t('profile_cache_btn'))
		# 更新 aria2 状态
		if self.aria2_status_label.styleSheet() == "color: green;":
			self.aria2_status_label.setText(t('aria2_started'))
		elif self.aria2_status_label.styleSheet() == "color: red;":
			self.aria2_status_label.setText(t('aria2_failed'))
		else:
			self.aria2_status_label.setText(t('starting_aria2'))
		# 更新 Web 服务器 UI
		self.web_server_group.setTitle(t('web_server_btn'))
		if is_server_running():
			self.web_status_label.setText(t('web_server_status_on'))
			self.web_server_btn.setText(t('web_server_stop_btn'))
		else:
			self.web_status_label.setText(t('web_server_status_off'))
			self.web_server_btn.setText(t('web_server_btn'))
		self.open_url_btn.setText(t('web_server_open_url'))
		self.copy_url_btn.setText(t('web_server_copy_url'))
		# 更新端口标签
		self.port_label.setText(t('web_server_port_label'))
		# 更新复选框文本
		self.allow_delete_checkbox.setText(t('allow_remote_delete'))
		self.auto_start_checkbox.setText(t('auto_start_web_server'))
		# 更新媒体检查组标题和刷新按钮
		self.media_check_group.setTitle(t('media_check_title'))
		self.media_check_refresh_btn.setText(t('media_check_refresh'))
		# 更新媒体检查状态文本
		self._update_media_check_style(self._media_check_state)
		# 更新还原点 UI
		self.restore_point_group.setTitle(t('restore_point_group'))
		self.auto_restore_checkbox.setText(t('restore_point_auto_create'))
		self.create_restore_btn.setText(t('restore_point_create_btn'))
		self.restore_from_btn.setText(t('restore_point_restore_btn'))
		# 更新插入反转勾选框文本
		self.reverse_insert_checkbox.setText(t('reverse_insert_order'))

	# 更新语言标签
	# 注意：语言下拉框本身不需要更新，因为语言名称是固定的

	def center_window(self):
		screen = QScreen.availableGeometry(QApplication.primaryScreen())
		x = (screen.width() - self.width()) // 2
		y = (screen.height() - self.height()) // 2
		self.move(x, y)

	def init_aria2(self):
		"""初始化 aria2 守护进程"""
		aria2_manager = init_global_aria2_manager()
		if aria2_manager and aria2_manager.api:
			self.aria2_status_label.setText(t('aria2_started'))
			self.aria2_status_label.setStyleSheet("color: green;")
		else:
			self.aria2_status_label.setText(t('aria2_failed'))
			self.aria2_status_label.setStyleSheet("color: red;")

	def closeEvent(self, event):
		"""窗口关闭事件"""
		# 停止检测线程
		if self._web_check_thread and self._web_check_thread.isRunning():
			self._web_check_thread.stop()
			self._web_check_thread.wait(1000)
		# 停止 Web 服务器
		if is_server_running():
			stop_web_server()
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
				self.label.setText(t('drop_json_file'))

	def import_json_file(self):
		"""通过文件对话框选择 JSON 文件导入"""
		file_path, _ = QFileDialog.getOpenFileName(
			self,
			t('import_json_btn'),
			os.getcwd(),
			"JSON Files (*.json);;All Files (*.*)"
		)
		if file_path:
			self.process_json(file_path)

	def process_json(self, file_path):
		# 如果需要，自动创建还原点
		if not self.auto_create_restore_point_if_needed():
			# 还原点创建失败，询问用户是否继续
			reply = QMessageBox.question(
				self,
				t('error'),
				t('restore_point_failed', error='') + '\n\n' + t('restore_point_continue_import'),
				QMessageBox.Yes | QMessageBox.No,
				QMessageBox.No
			)
			if reply == QMessageBox.No:
				return

		reverse_insert = self.reverse_insert_checkbox.isChecked()
		self.thread = JSONProcessorThread(file_path, reverse_insert=reverse_insert)
		self.thread.progress.connect(self.update_progress)
		self.thread.completed.connect(self.on_processing_completed)

		self.progress_bar.setValue(0)
		self.progress_bar.setVisible(True)
		self.label.setText(t('processing_json'))

		self.thread.start()

	def update_progress(self, value):
		self.progress_bar.setValue(value)

	def on_processing_completed(self, new_entries):
		self.progress_bar.setVisible(False)
		if new_entries == -1:
			self.label.setText(t('json_error'))
		else:
			self.label.setText(t('process_complete', count=new_entries))
			# 如果 web server 正在运行，检测是否有未下载的媒体
			if is_server_running():
				self.check_undownloaded_media()

	def select_main_db(self):
		"""选择主数据库文件"""
		file_path, _ = QFileDialog.getSaveFileName(
			self,
			t('select_main_db_title'),
			os.getcwd(),
			t('db_filter')
		)

		if file_path:
			# 如果用户没有输入扩展名，自动添加 .sqlite
			if not file_path.endswith('.sqlite'):
				file_path += '.sqlite'

			# 更新全局数据库实例
			globals_module.db.close()
			globals_module.db = TweetDatabase(file_path)

			# 保存到配置
			self.config.set('database', 'main_db', file_path)
			save_config(self.config)

			# 更新显示
			self.db_path_label.setText(file_path)

			# 判断是新建还是打开
			if os.path.exists(file_path):
				QMessageBox.information(self, t('switch_success'), t('switched_to_db', path=file_path))
			else:
				QMessageBox.information(self, t('create_success'), t('created_db', path=file_path))

	def select_deleted_db(self):
		"""选择删除数据库文件"""
		file_path, _ = QFileDialog.getSaveFileName(
			self,
			t('select_deleted_db_title'),
			os.getcwd(),
			t('db_filter')
		)

		if file_path:
			# 如果用户没有输入扩展名，自动添加 .sqlite
			if not file_path.endswith('.sqlite'):
				file_path += '.sqlite'

			# 更新全局数据库实例
			globals_module.ddb.close()
			globals_module.ddb = TweetDatabase(file_path)

			# 保存到配置
			self.config.set('database', 'deleted_db', file_path)
			save_config(self.config)

			# 更新显示
			self.ddb_path_label.setText(file_path)

			# 判断是新建还是打开
			if os.path.exists(file_path):
				QMessageBox.information(self, t('switch_success'), t('switched_to_db', path=file_path))
			else:
				QMessageBox.information(self, t('create_success'), t('created_db', path=file_path))

	def check_migration_needed(self):
		"""检查是否有旧数据需要迁移"""
		old_main_db = self.config.get('database', 'main_db')
		old_deleted_db = self.config.get('database', 'deleted_db')

		tinydb_files = []
		if is_tinydb_file(old_main_db):
			tinydb_files.append(old_main_db)
		if is_tinydb_file(old_deleted_db):
			tinydb_files.append(old_deleted_db)

		if tinydb_files:
			reply = QMessageBox.question(
				self,
				t('migration_detected_title'),
				t('migration_detected_msg', files='\n'.join(tinydb_files)),
				QMessageBox.Yes | QMessageBox.No,
				QMessageBox.Yes
			)
			if reply == QMessageBox.Yes:
				self.open_migration_dialog()

	def open_migration_dialog(self):
		"""打开数据迁移对话框"""
		dialog = MigrationDialog(self)
		dialog.exec()

	def check_auto_start_web_server(self):
		"""检查配置并自动启动 Web 服务器"""
		auto_start = self.config.getboolean('webserver', 'auto_start', fallback=False)
		if auto_start and not is_server_running():
			# 自动启动 Web 服务器
			port = self.web_port_spinbox.value()
			# 重新从配置文件加载路径，确保获取最新值
			fresh_config = load_config()
			media_path = fresh_config.get('download', 'base_path')
			allow_delete = self.allow_delete_checkbox.isChecked()

			success, result = start_web_server(globals_module.db, media_path, port, deleted_db=globals_module.ddb, allow_delete=allow_delete)

			if success:
				# 显示黄灯，进入第一阶段检测
				self._web_server_url = result
				self.update_web_server_ui_starting(t('web_server_starting'))

				# 启动检测线程
				self._web_check_thread = WebServerCheckThread(port, timeout_seconds=20)
				self._web_check_thread.phase_completed.connect(self._on_web_check_phase_completed)
				self._web_check_thread.timeout.connect(self._on_web_check_timeout)
				self._web_check_thread.start()

	def toggle_web_server(self):
		"""切换 Web 服务器状态"""
		if is_server_running():
			# 停止服务器
			# 先停止检测线程（如果有）
			if self._web_check_thread and self._web_check_thread.isRunning():
				self._web_check_thread.stop()
				self._web_check_thread.wait(1000)  # 等待最多1秒
				self._web_check_thread = None
			stop_web_server()
			self.update_web_server_ui(False)
		else:
			# 启动服务器
			port = self.web_port_spinbox.value()
			# 重新从配置文件加载路径，因为用户可能在数据库记录窗口中修改了路径
			fresh_config = load_config()
			media_path = fresh_config.get('download', 'base_path')
			allow_delete = self.allow_delete_checkbox.isChecked()

			success, result = start_web_server(globals_module.db, media_path, port, deleted_db=globals_module.ddb, allow_delete=allow_delete)

			if success:
				# 显示黄灯，进入第一阶段检测
				self._web_server_url = result
				self.update_web_server_ui_starting(t('web_server_starting'))

				# 启动检测线程
				self._web_check_thread = WebServerCheckThread(port, timeout_seconds=20)
				self._web_check_thread.phase_completed.connect(self._on_web_check_phase_completed)
				self._web_check_thread.timeout.connect(self._on_web_check_timeout)
				self._web_check_thread.start()
			else:
				QMessageBox.warning(
					self,
					t('error'),
					t('web_server_error', error=result)
				)

	def on_allow_delete_changed(self, state):
		"""允许删除状态改变时保存配置并更新服务器"""
		# 使用 isChecked() 方法获取当前状态，更可靠
		allow_delete = self.allow_delete_checkbox.isChecked()

		# 保存到配置
		if 'webserver' not in self.config.sections():
			self.config.add_section('webserver')
		self.config.set('webserver', 'allow_delete', str(allow_delete))
		save_config(self.config)

		# 如果服务器正在运行，更新设置
		if is_server_running():
			set_allow_delete(allow_delete)

	def on_auto_start_changed(self, state):
		"""自动启动状态改变时保存配置"""
		auto_start = self.auto_start_checkbox.isChecked()

		# 保存到配置
		if 'webserver' not in self.config.sections():
			self.config.add_section('webserver')
		self.config.set('webserver', 'auto_start', str(auto_start))
		save_config(self.config)

	def on_port_changed(self, value):
		"""端口改变时保存配置"""
		# 保存到配置
		if 'webserver' not in self.config.sections():
			self.config.add_section('webserver')
		self.config.set('webserver', 'port', str(value))
		save_config(self.config)

	def on_reverse_insert_changed(self, state):
		"""插入时反转顺序状态改变时保存配置"""
		reverse_insert = self.reverse_insert_checkbox.isChecked()

		# 保存到配置
		self.config.set('general', 'reverse_insert', str(reverse_insert))
		save_config(self.config)

	def _on_web_check_phase_completed(self, phase: int):
		"""检测阶段完成回调"""
		if phase == 1:
			# 服务可访问，进入第二阶段
			self.update_web_server_ui_starting(t('web_server_building_cache'))
		elif phase == 2:
			# 缓存已就绪，显示绿灯
			self._web_check_thread = None
			self.update_web_server_ui(True, self._web_server_url)
			# 检测是否有未下载的媒体
			self.check_undownloaded_media()

	def _on_web_check_timeout(self):
		"""检测超时回调"""
		self._web_check_thread = None
		stop_web_server()
		self.update_web_server_ui(False)
		QMessageBox.warning(
			self,
			t('error'),
			t('web_server_timeout')
		)

	def update_web_server_ui_starting(self, status_text: str):
		"""更新 Web 服务器 UI 为启动中状态（黄灯）"""
		self.web_status_indicator.setStyleSheet("color: #EAB308; font-size: 16px;")  # 黄色
		self.web_status_label.setText(status_text)
		self.web_status_label.setStyleSheet("color: #EAB308;")
		self.web_server_btn.setText(t('web_server_stop_btn'))
		self.web_server_btn.setEnabled(True)  # 允许用户取消启动
		self.web_port_spinbox.setEnabled(False)
		self.open_url_btn.setEnabled(False)
		self.copy_url_btn.setEnabled(False)
		self.web_url_label.setText(self._web_server_url)
		self.web_url_frame.setVisible(True)
		# 禁用数据库切换按钮
		self.db_select_button.setEnabled(False)
		self.ddb_select_button.setEnabled(False)

	def update_web_server_ui(self, running: bool, url: str = ""):
		"""更新 Web 服务器 UI 状态"""
		if running:
			self.web_status_indicator.setStyleSheet("color: #22C55E; font-size: 16px;")  # 绿色
			self.web_status_label.setText(t('web_server_status_on'))
			self.web_status_label.setStyleSheet("color: #22C55E;")
			self.web_server_btn.setText(t('web_server_stop_btn'))
			self.web_server_btn.setEnabled(True)
			self.web_port_spinbox.setEnabled(False)
			self.open_url_btn.setEnabled(True)
			self.copy_url_btn.setEnabled(True)
			self.web_url_label.setText(url)
			self.web_url_frame.setVisible(True)
			# 禁用数据库切换按钮
			self.db_select_button.setEnabled(False)
			self.ddb_select_button.setEnabled(False)
		else:
			self.web_status_indicator.setStyleSheet("color: #666666; font-size: 16px;")  # 灰色
			self.web_status_label.setText(t('web_server_status_off'))
			self.web_status_label.setStyleSheet("color: gray;")
			self.web_server_btn.setText(t('web_server_btn'))
			self.web_server_btn.setEnabled(True)
			self.web_port_spinbox.setEnabled(True)
			self.open_url_btn.setEnabled(True)
			self.copy_url_btn.setEnabled(True)
			self.web_url_label.setText("")
			self.web_url_frame.setVisible(False)
			# 启用数据库切换按钮
			self.db_select_button.setEnabled(True)
			self.ddb_select_button.setEnabled(True)

	def open_web_url(self):
		"""在浏览器中打开 Web 服务器 URL"""
		import webbrowser
		url = get_server_url()
		if url:
			webbrowser.open(url)

	def copy_web_url(self):
		"""复制 Web 服务器 URL 到剪贴板"""
		url = get_server_url()
		if url:
			clipboard = QApplication.clipboard()
			clipboard.setText(url)
			# 短暂改变按钮文本作为反馈
			self.copy_url_btn.setText("✓")
			QTimer.singleShot(1000, lambda: self.copy_url_btn.setText(t('web_server_copy_url')))

	def check_undownloaded_media(self):
		"""检测是否有未下载的媒体"""
		# 如果数据库中没有有效推文记录，不显示媒体检查控件
		if globals_module.db.count() == 0:
			self.media_check_group.setVisible(False)
			return

		# 如果已经有检测线程在运行，先停止它
		if self._media_check_thread and self._media_check_thread.isRunning():
			self._media_check_thread.wait(500)

		# 显示检查中状态
		self._update_media_check_style('checking')
		self.media_check_group.setVisible(True)
		self.media_check_refresh_btn.setEnabled(False)

		# 从配置获取媒体路径和精准匹配设置
		fresh_config = load_config()
		media_path = fresh_config.get('download', 'base_path')
		exact_match = fresh_config.getboolean('download', 'exact_match', fallback=False)

		# 启动检测线程
		self._media_check_thread = MediaDownloadCheckThread(globals_module.db, media_path, exact_match)
		self._media_check_thread.result.connect(self._on_media_check_result)
		self._media_check_thread.start()

	def _on_media_check_result(self, has_undownloaded: bool):
		"""媒体检测完成回调"""
		self.media_check_refresh_btn.setEnabled(True)
		if has_undownloaded:
			self._update_media_check_style('warning')
		else:
			self._update_media_check_style('success')

	def _update_media_check_style(self, state: str):
		"""更新媒体检查状态样式

		Args:
			state: 'checking' | 'warning' | 'success'
		"""
		self._media_check_state = state  # 保存当前状态
		if state == 'checking':
			self.media_check_indicator.setText("●")
			self.media_check_indicator.setStyleSheet("color: #666666; font-size: 16px;")  # 灰色
			self.media_check_label.setText(t('media_check_checking'))
			self.media_check_label.setStyleSheet("color: gray;")
		elif state == 'warning':
			self.media_check_indicator.setText("●")
			self.media_check_indicator.setStyleSheet("color: #EAB308; font-size: 16px;")  # 黄色
			self.media_check_label.setText(t('media_check_has_undownloaded'))
			self.media_check_label.setStyleSheet("color: #EAB308;")
		elif state == 'success':
			self.media_check_indicator.setText("●")
			self.media_check_indicator.setStyleSheet("color: #22C55E; font-size: 16px;")  # 绿色
			self.media_check_label.setText(t('media_check_all_downloaded'))
			self.media_check_label.setStyleSheet("color: #22C55E;")

	def open_profile_cache_dialog(self):
		"""打开头像缓存管理对话框"""
		dialog = ProfileImageCacheDialog(self)
		dialog.exec()

	def open_database_viewer(self):
		# 使用局部变量而非实例属性，对话框关闭后可被正确回收
		db_viewer = DatabaseViewerDialog()
		db_viewer.exec()
		# 数据库记录窗口关闭后，如果 web server 正在运行，重新检测媒体状态
		if is_server_running():
			self.check_undownloaded_media()

	def on_auto_restore_changed(self, state):
		"""自动创建还原点状态改变时保存配置"""
		auto_restore = self.auto_restore_checkbox.isChecked()

		# 保存到配置
		if 'restore_point' not in self.config.sections():
			self.config.add_section('restore_point')
		self.config.set('restore_point', 'auto_create', str(auto_restore))
		save_config(self.config)

	def get_default_restore_point_name(self) -> str:
		"""获取默认的还原点名称"""
		from datetime import datetime
		today = datetime.now()
		# 使用国际化的日期格式
		date_format = t('restore_point_date_format')
		date_str = today.strftime(date_format)
		# 获取今日已创建的还原点数量
		count = self.restore_point_manager.get_today_count()
		num = count + 1
		return t('restore_point_default_name', date=date_str, num=num)

	def create_restore_point(self, show_dialog: bool = True) -> bool:
		"""创建还原点
		
		Args:
			show_dialog: 是否显示输入对话框，False 时使用默认名称
		
		Returns:
			是否成功创建
		"""
		from PySide6.QtWidgets import QDialog
		default_name = self.get_default_restore_point_name()

		if show_dialog:
			dialog = RestorePointInputDialog(self, default_name)
			if dialog.exec() != QDialog.Accepted:
				return False
			name = dialog.get_name()
			if not name:
				name = default_name
		else:
			name = default_name

		# 创建还原点
		success, result = self.restore_point_manager.create_restore_point(
			name,
			globals_module.main_db_path,
			globals_module.deleted_db_path
		)

		if success:
			if show_dialog:
				QMessageBox.information(
					self,
					t('restore_point_success'),
					t('restore_point_success_msg', name=name)
				)
			return True
		else:
			QMessageBox.warning(
				self,
				t('error'),
				t('restore_point_failed', error=result)
			)
			return False

	def restore_from_point(self):
		"""从还原点还原"""
		# 检查 Web 服务器是否正在运行
		if is_server_running():
			QMessageBox.warning(
				self,
				t('error'),
				t('web_server_status_on') + '\n\n' + t('restore_point_stop_server_first')
			)
			return

		from PySide6.QtWidgets import QDialog
		dialog = RestorePointListDialog(self)
		if dialog.exec() != QDialog.Accepted:
			return

		point = dialog.get_selected_point()
		if not point:
			return

		# 执行还原
		success, result = self.restore_point_manager.restore_from_point(
			point["folder_path"],
			globals_module.main_db_path,
			globals_module.deleted_db_path,
			globals_module.db,
			globals_module.ddb
		)

		if success:
			# 重新打开数据库
			from database import TweetDatabase
			globals_module.db = TweetDatabase(globals_module.main_db_path)
			globals_module.ddb = TweetDatabase(globals_module.deleted_db_path)

			QMessageBox.information(
				self,
				t('restore_point_restore_success'),
				t('restore_point_restore_success_msg', name=result)
			)
		else:
			# 还原失败时也需要重新打开数据库
			from database import TweetDatabase
			globals_module.db = TweetDatabase(globals_module.main_db_path)
			globals_module.ddb = TweetDatabase(globals_module.deleted_db_path)

			QMessageBox.warning(
				self,
				t('error'),
				t('restore_point_restore_failed', error=result)
			)

	def auto_create_restore_point_if_needed(self) -> bool:
		"""如果需要，自动创建还原点
		
		Returns:
			是否成功（如果不需要创建也返回 True）
		"""
		if self.auto_restore_checkbox.isChecked():
			return self.create_restore_point(show_dialog=False)
		return True
