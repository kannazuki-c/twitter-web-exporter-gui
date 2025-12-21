import os
import sys
import subprocess
import socket
import time
import datetime
import configparser
from PySide6.QtWidgets import (
	QApplication, QVBoxLayout,
	QPushButton, QProgressBar, QLabel, QTableWidget, QTableWidgetItem, QDialog, QHBoxLayout, QLineEdit,
	QSpinBox, QCheckBox, QMessageBox
)
from PySide6.QtCore import Signal, QObject, QTimer
from PySide6.QtGui import QScreen
import aria2p
from i18n import t, get_language

# 全局 aria2 管理器实例
global_aria2_manager = None


class Aria2Manager:
	"""管理 aria2c RPC 进程"""
	def __init__(self):
		self.process = None
		self.port = None
		self.api = None

	def find_free_port(self):
		"""查找一个可用的随机端口"""
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
			s.bind(('', 0))
			s.listen(1)
			port = s.getsockname()[1]
		return port

	def start(self):
		"""启动 aria2c RPC 服务"""
		if self.process:
			return True

		self.port = self.find_free_port()

		try:
			# 加载配置
			config = load_config()
			max_concurrent = config.get('aria2', 'max_concurrent_downloads')
			max_speed = config.get('aria2', 'max_overall_download_limit')
			max_conn = config.get('aria2', 'max_connection_per_server')
			split = config.get('aria2', 'split')
			timeout = config.get('aria2', 'timeout')

			# 构建速度限制字符串
			speed_limit_str = f"{max_speed}M" if int(max_speed) > 0 else "0"

			# 获取资源路径（兼容开发环境和打包后环境）
			if getattr(sys, 'frozen', False):
				# 打包后的环境，资源在 _internal 目录下
				base_path = sys._MEIPASS
			else:
				# 开发环境
				base_path = os.path.dirname(os.path.abspath(__file__))

			bundled_aria2c = os.path.join(base_path, "aria2-1.37.0-win-64bit", "aria2c.exe")

			if os.path.exists(bundled_aria2c):
				aria2c_path = bundled_aria2c
			else:
				return False

			# 启动 aria2c RPC 服务
			cmd = [
				aria2c_path,
				"--enable-rpc=true",
				f"--rpc-listen-port={self.port}",
				"--rpc-listen-all=false",
				"--continue=true",
				f"--max-connection-per-server={max_conn}",
				"--min-split-size=1M",
				f"--split={split}",
				f"--max-concurrent-downloads={max_concurrent}",
				f"--max-overall-download-limit={speed_limit_str}",
				f"--timeout={timeout}",
				"--max-tries=1",
				"--disable-ipv6=true",
				"--quiet=true"
			]

			# 在 Windows 上隐藏控制台窗口
			startupinfo = None
			if sys.platform == 'win32':
				startupinfo = subprocess.STARTUPINFO()
				startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
				startupinfo.wShowWindow = subprocess.SW_HIDE

			self.process = subprocess.Popen(
				cmd,
				stdout=subprocess.DEVNULL,
				stderr=subprocess.DEVNULL,
				startupinfo=startupinfo
			)

			# 创建 aria2p API 实例
			client = aria2p.Client(host="http://127.0.0.1", port=self.port)
			self.api = aria2p.API(client)

			# 等待 aria2c 启动
			max_retries = 10
			for i in range(max_retries):
				time.sleep(0.3)
				try:
					# 测试连接
					self.api.get_global_options()
					print(f"aria2c RPC 服务已启动，端口: {self.port}")
					return True
				except:
					continue

			print("aria2c RPC 服务启动超时")
			self.stop()
			return False

		except Exception as e:
			print(f"启动 aria2c 失败: {e}")
			return False

	def stop(self):
		"""停止 aria2c RPC 服务"""
		if self.process:
			try:
				# 尝试通过 API 优雅地关闭
				if self.api:
					self.api.client.shutdown()
				time.sleep(0.5)
			except:
				pass

			# 强制终止进程
			if self.process.poll() is None:
				self.process.terminate()
				try:
					self.process.wait(timeout=3)
				except:
					self.process.kill()

			self.process = None
			self.port = None
			self.api = None
			print("aria2c RPC 服务已停止")

	def add_download(self, url, download_dir, file_name):
		"""添加下载任务"""
		if not self.api:
			return None

		try:
			# 加载配置
			config = load_config()
			max_conn = config.get('aria2', 'max_connection_per_server')
			split = config.get('aria2', 'split')
			timeout = config.get('aria2', 'timeout')

			options = {
				"dir": download_dir,
				"out": file_name,
				"continue": "true",
				"max-connection-per-server": max_conn,
				"split": split,
				"min-split-size": "1M",
				"timeout": timeout,
				"max-tries": "1"
			}

			# 使用 API 添加下载
			download = self.api.add_uris([url], options=options)
			return download

		except Exception as e:
			print(f"添加下载任务失败: {e}")
			return None

	def get_download(self, gid):
		"""获取下载状态"""
		if not self.api:
			return None

		try:
			downloads = self.api.get_downloads()
			for download in downloads:
				if download.gid == gid:
					return download
			return None
		except Exception as e:
			print(f"查询下载状态失败: {e}")
			return None


class DownloadMonitor(QObject):
	"""监控 aria2 下载进度"""
	progress = Signal(int, int)  # 任务ID, 进度百分比
	status_update = Signal(int, str)  # 任务ID, 状态
	finished = Signal(int)  # 任务ID

	def __init__(self, task_id, gid, aria2_manager, parent=None):
		super().__init__(parent)
		self.task_id = task_id
		self.gid = gid
		self.aria2_manager = aria2_manager
		self.is_running = True
		self.timer = QTimer()
		self.timer.timeout.connect(self.check_status)
		self.timer.start(500)  # 每500ms检查一次

	def check_status(self):
		"""检查下载状态"""
		if not self.is_running:
			return

		download = self.aria2_manager.get_download(self.gid)
		if not download:
			return

		status = download.status

		if status == "active":
			# 下载中
			if download.total_length > 0:
				progress = int((download.completed_length / download.total_length) * 100)
				self.progress.emit(self.task_id, progress)

				# 显示速度信息
				speed_mb = download.download_speed / 1024 / 1024
				self.status_update.emit(self.task_id, t('downloading_speed', speed=speed_mb))

		elif status == "complete":
			# 下载完成
			self.progress.emit(self.task_id, 100)
			self.status_update.emit(self.task_id, t('completed'))
			self.stop()
			self.finished.emit(self.task_id)

		elif status == "error":
			# 下载失败
			error_msg = download.error_message or "Unknown error"
			self.status_update.emit(self.task_id, t('download_failed', error=error_msg))
			self.stop()
			self.finished.emit(self.task_id)

		elif status == "removed":
			# 任务被移除
			self.status_update.emit(self.task_id, t('task_cancelled'))
			self.stop()
			self.finished.emit(self.task_id)

	def stop(self):
		"""停止监控"""
		self.is_running = False
		self.timer.stop()


def init_global_aria2_manager():
	"""初始化全局 aria2 管理器"""
	global global_aria2_manager
	if global_aria2_manager is None:
		global_aria2_manager = Aria2Manager()
		global_aria2_manager.start()
	return global_aria2_manager


def shutdown_global_aria2_manager():
	"""关闭全局 aria2 管理器"""
	global global_aria2_manager
	if global_aria2_manager:
		global_aria2_manager.stop()
		global_aria2_manager = None


def get_config_path():
	"""获取配置文件路径"""
	return os.path.join(os.getcwd(), "twegui_conf.ini")


def load_config():
	"""加载配置文件"""
	config = configparser.ConfigParser()
	config_path = get_config_path()

	if os.path.exists(config_path):
		config.read(config_path, encoding='utf-8')

	# 下载配置节
	if not config.has_section('download'):
		config.add_section('download')

	# 设置默认值
	if not config.has_option('download', 'batch_number'):
		config.set('download', 'batch_number', '1')

	if not config.has_option('download', 'base_path'):
		config.set('download', 'base_path', os.path.join(os.getcwd(), "downloads"))

	if not config.has_option('download', 'exact_match'):
		config.set('download', 'exact_match', 'False')

	# 数据库配置节
	if not config.has_section('database'):
		config.add_section('database')

	if not config.has_option('database', 'main_db'):
		config.set('database', 'main_db', 'tweets.sqlite')

	if not config.has_option('database', 'deleted_db'):
		config.set('database', 'deleted_db', 'deleted.sqlite')

	# 通用配置节
	if not config.has_section('general'):
		config.add_section('general')

	# 语言设置，默认为英文
	if not config.has_option('general', 'language'):
		config.set('general', 'language', 'en')

	# Web 服务器配置节
	if not config.has_section('webserver'):
		config.add_section('webserver')

	# 自动启动设置，默认为 False
	if not config.has_option('webserver', 'auto_start'):
		config.set('webserver', 'auto_start', 'False')

	# 端口设置，默认为 5001
	if not config.has_option('webserver', 'port'):
		config.set('webserver', 'port', '5001')

	# aria2 配置节
	if not config.has_section('aria2'):
		config.add_section('aria2')

	# 最大并发下载数
	if not config.has_option('aria2', 'max_concurrent_downloads'):
		config.set('aria2', 'max_concurrent_downloads', '20')

	# 全局速度限制 (0=不限制，单位MB/s)
	if not config.has_option('aria2', 'max_overall_download_limit'):
		config.set('aria2', 'max_overall_download_limit', '0')

	# 每服务器连接数
	if not config.has_option('aria2', 'max_connection_per_server'):
		config.set('aria2', 'max_connection_per_server', '16')

	# 文件分片数
	if not config.has_option('aria2', 'split'):
		config.set('aria2', 'split', '16')

	# 超时时间（秒）
	if not config.has_option('aria2', 'timeout'):
		config.set('aria2', 'timeout', '60')

	return config


def save_config(config):
	"""保存配置文件"""
	config_path = get_config_path()
	with open(config_path, 'w', encoding='utf-8') as f:
		config.write(f)


class Aria2SettingsDialog(QDialog):
	"""aria2 下载设置对话框"""
	def __init__(self, aria2_manager=None, parent=None):
		super().__init__(parent)
		self.aria2_manager = aria2_manager
		self.setWindowTitle(t('aria2_settings_title'))
		self.resize(450, 300)
		self.config = load_config()
		self.initUI()

	def _create_hint_label(self, text):
		"""创建提示标签"""
		hint_label = QLabel(text)
		hint_label.setStyleSheet("color: gray; font-size: 11px; margin-left: 10px; margin-bottom: 8px;")
		hint_label.setWordWrap(True)
		return hint_label

	def initUI(self):
		layout = QVBoxLayout(self)

		# 最大并发下载数
		concurrent_layout = QHBoxLayout()
		concurrent_label = QLabel(t('aria2_max_concurrent'))
		self.concurrent_spin = QSpinBox()
		self.concurrent_spin.setRange(1, 50)
		self.concurrent_spin.setValue(int(self.config.get('aria2', 'max_concurrent_downloads')))
		concurrent_layout.addWidget(concurrent_label)
		concurrent_layout.addWidget(self.concurrent_spin)
		concurrent_layout.addStretch()
		layout.addLayout(concurrent_layout)
		layout.addWidget(self._create_hint_label(t('aria2_max_concurrent_hint')))

		# 全局速度限制
		speed_layout = QHBoxLayout()
		speed_label = QLabel(t('aria2_speed_limit'))
		self.speed_spin = QSpinBox()
		self.speed_spin.setRange(0, 1000)
		self.speed_spin.setValue(int(self.config.get('aria2', 'max_overall_download_limit')))
		speed_layout.addWidget(speed_label)
		speed_layout.addWidget(self.speed_spin)
		speed_layout.addStretch()
		layout.addLayout(speed_layout)
		layout.addWidget(self._create_hint_label(t('aria2_speed_limit_hint')))

		# 每服务器连接数
		conn_layout = QHBoxLayout()
		conn_label = QLabel(t('aria2_conn_per_server'))
		self.conn_spin = QSpinBox()
		self.conn_spin.setRange(1, 16)
		self.conn_spin.setValue(int(self.config.get('aria2', 'max_connection_per_server')))
		conn_layout.addWidget(conn_label)
		conn_layout.addWidget(self.conn_spin)
		conn_layout.addStretch()
		layout.addLayout(conn_layout)
		layout.addWidget(self._create_hint_label(t('aria2_conn_per_server_hint')))

		# 文件分片数
		split_layout = QHBoxLayout()
		split_label = QLabel(t('aria2_split'))
		self.split_spin = QSpinBox()
		self.split_spin.setRange(1, 16)
		self.split_spin.setValue(int(self.config.get('aria2', 'split')))
		split_layout.addWidget(split_label)
		split_layout.addWidget(self.split_spin)
		split_layout.addStretch()
		layout.addLayout(split_layout)
		layout.addWidget(self._create_hint_label(t('aria2_split_hint')))

		# 超时时间
		timeout_layout = QHBoxLayout()
		timeout_label = QLabel(t('aria2_timeout'))
		self.timeout_spin = QSpinBox()
		self.timeout_spin.setRange(10, 600)
		self.timeout_spin.setValue(int(self.config.get('aria2', 'timeout')))
		timeout_layout.addWidget(timeout_label)
		timeout_layout.addWidget(self.timeout_spin)
		timeout_layout.addStretch()
		layout.addLayout(timeout_layout)
		layout.addWidget(self._create_hint_label(t('aria2_timeout_hint')))

		layout.addStretch()

		# 保存按钮
		self.save_btn = QPushButton(t('aria2_save'))
		self.save_btn.clicked.connect(self.save_settings)
		layout.addWidget(self.save_btn)

		# 状态标签
		self.status_label = QLabel()
		layout.addWidget(self.status_label)

	def save_settings(self):
		"""保存设置并立即应用"""
		# 保存到配置文件
		self.config.set('aria2', 'max_concurrent_downloads', str(self.concurrent_spin.value()))
		self.config.set('aria2', 'max_overall_download_limit', str(self.speed_spin.value()))
		self.config.set('aria2', 'max_connection_per_server', str(self.conn_spin.value()))
		self.config.set('aria2', 'split', str(self.split_spin.value()))
		self.config.set('aria2', 'timeout', str(self.timeout_spin.value()))
		save_config(self.config)

		# 动态修改全局选项（不需要重启aria2）
		if self.aria2_manager and self.aria2_manager.api:
			try:
				# 构建速度限制字符串
				speed_limit = self.speed_spin.value()
				speed_limit_str = f"{speed_limit}M" if speed_limit > 0 else "0"

				self.aria2_manager.api.set_global_options({
					"max-concurrent-downloads": str(self.concurrent_spin.value()),
					"max-overall-download-limit": speed_limit_str
				})
			except Exception as e:
				print(f"动态修改aria2选项失败: {e}")

		self.status_label.setText(t('aria2_saved'))
		self.status_label.setStyleSheet("color: green;")


def get_download_path(base_path, file_type, batch_number):
	"""获取下载路径

	Args:
		base_path: 基础路径
		file_type: 文件类型 (photo/video)
		batch_number: 批号

	Returns:
		完整的下载路径
	"""
	year = datetime.datetime.now().year
	batch_dir = f"{year}.G{batch_number}"

	if file_type == "photo":
		# 图片路径: base_path/年份.G批号/图(或Images)
		# 根据当前语言选择文件夹名称
		folder_name = "图" if get_language() == "zh-CN" else "Images"
		return os.path.join(base_path, batch_dir, folder_name)
	else:
		# 视频路径: base_path/年份.G批号
		return os.path.join(base_path, batch_dir)


class DownloadWindow(QDialog):
	# 自定义信号，用于通知下载完成
	download_completed = Signal()

	def __init__(self, tasks, base_path=None, parent=None):
		super().__init__(parent)
		self.setWindowTitle(t('download_manager_title'))
		self.resize(600, 400)
		self.tasks = tasks
		self.aria2_manager = global_aria2_manager
		self.monitors = []
		self.completed_count = 0
		self.base_path = base_path or os.path.join(os.getcwd(), "downloads")
		self.failed_count = 0  # 失败任务计数
		self.failed_tasks = []  # 失败任务列表，用于重试
		self.hide_completed = True  # 是否隐藏已完成的任务

		# 标记是否已经开始下载
		self.download_started = False

		# 加载配置
		self.config = load_config()
		self.batch_number = self.config.get('download', 'batch_number')

		self.initUI()
		self.center_window()

	def center_window(self):
		"""窗口居中"""
		screen = QScreen.availableGeometry(QApplication.primaryScreen())
		x = (screen.width() - self.width()) // 2
		y = (screen.height() - self.height()) // 2
		self.move(x, y)

	def initUI(self):
		# 主布局
		layout = QVBoxLayout(self)

		# 进度条和标签
		self.progress_label = QLabel(t('preparing_download'))
		self.progress_label.setText(t('tasks_added', count=len(self.tasks), batch=self.batch_number))
		layout.addWidget(self.progress_label)
		self.progress_bar = QProgressBar()
		layout.addWidget(self.progress_bar)

		# 表格初始化
		self.table = QTableWidget(len(self.tasks), 3)
		self.table.setHorizontalHeaderLabels([t('col_url_download'), t('col_progress'), t('col_status')])
		# 设置每列的宽度
		self.table.setColumnWidth(0, 300)  # URL列宽度
		self.table.setColumnWidth(1, 100)  # 进度列宽度
		self.table.setColumnWidth(2, 200)  # 状态列宽度
		for i, task in enumerate(self.tasks):
			self.table.setItem(i, 0, QTableWidgetItem(task['url']))
			self.table.setItem(i, 1, QTableWidgetItem("0%"))
			self.table.setItem(i, 2, QTableWidgetItem(t('waiting')))
		layout.addWidget(self.table)

		# 按钮行
		button_layout = QHBoxLayout()

		# 开始按钮
		self.start_button = QPushButton(t('start_download'))
		self.start_button.clicked.connect(self.start_download)
		button_layout.addWidget(self.start_button)

		# 重试按钮
		self.retry_button = QPushButton(t('retry_failed'))
		self.retry_button.clicked.connect(self.retry_failed_tasks)
		self.retry_button.setEnabled(False)
		button_layout.addWidget(self.retry_button)

		# 设置按钮
		self.settings_button = QPushButton(t('aria2_settings'))
		self.settings_button.clicked.connect(self.open_settings)
		button_layout.addWidget(self.settings_button)

		layout.addLayout(button_layout)

		# 批号和隐藏选项行
		batch_layout = QHBoxLayout()
		batch_label = QLabel(t('batch_label'))
		batch_layout.addWidget(batch_label)
		self.batch_input = QLineEdit(self.batch_number)
		self.batch_input.setMaximumWidth(100)
		self.batch_input.textChanged.connect(self.on_batch_changed)
		batch_layout.addWidget(self.batch_input)

		# 隐藏已完成复选框
		self.hide_completed_checkbox = QCheckBox(t('hide_completed'))
		self.hide_completed_checkbox.setChecked(True)
		self.hide_completed_checkbox.stateChanged.connect(self.toggle_completed_visibility)
		batch_layout.addWidget(self.hide_completed_checkbox)

		batch_layout.addStretch()
		layout.addLayout(batch_layout)

		# 失败提示标签（红色）
		self.failed_label = QLabel()
		self.failed_label.setStyleSheet("color: red; font-weight: bold;")
		self.failed_label.setVisible(False)  # 初始隐藏
		layout.addWidget(self.failed_label)

		# 失败说明标签（白色）
		self.failed_info_label = QLabel(t('failed_info'))
		self.failed_info_label.setStyleSheet("color: white;")
		self.failed_info_label.setWordWrap(True)  # 允许自动换行
		self.failed_info_label.setVisible(False)  # 初始隐藏
		layout.addWidget(self.failed_info_label)

		# 设置对话框的布局
		self.setLayout(layout)
		self.update_start_button_state()

	def on_batch_changed(self, text):
		"""批号改变时更新"""
		self.batch_number = text
		self.progress_label.setText(t('tasks_added', count=len(self.tasks), batch=self.batch_number))

	def update_start_button_state(self):
		# 检查任务队列是否为空
		self.start_button.setEnabled(any(
			self.table.item(i, 2).text() not in [t('completed'), t('task_cancelled')] and
			not self.table.item(i, 2).text().startswith(t('download_failed', error='').split(':')[0])
			for i in range(self.table.rowCount())
		))

	def start_download(self):
		self.start_button.setEnabled(False)
		self.progress_bar.setValue(0)
		self.progress_label.setText(t('adding_tasks'))

		self.batch_input.setEnabled(False)

		# 检查 aria2 是否已启动
		if not self.aria2_manager or not self.aria2_manager.api:
			self.progress_label.setText(t('aria2_not_started'))
			return

		# 标记已开始下载
		self.download_started = True

		# 保存批号到配置
		self.config.set('download', 'batch_number', self.batch_number)
		save_config(self.config)

		# 添加所有下载任务
		self.completed_count = 0
		for i, task in enumerate(self.tasks):
			# 使用新的路径逻辑
			download_dir = get_download_path(self.base_path, task['file_type'], self.batch_number)

			# 确保目录存在
			os.makedirs(download_dir, exist_ok=True)

			# 添加下载任务
			download = self.aria2_manager.add_download(task['url'], download_dir, task['file_name'])

			if download:
				self.table.setItem(i, 2, QTableWidgetItem(t('added_to_queue')))
				# 创建监控器
				monitor = DownloadMonitor(i, download.gid, self.aria2_manager, parent=self)
				monitor.progress.connect(self.update_task_progress)
				monitor.status_update.connect(self.update_task_status)
				monitor.finished.connect(self.on_task_finished)
				self.monitors.append(monitor)
			else:
				self.table.setItem(i, 2, QTableWidgetItem(t('add_failed')))
				self.completed_count += 1

		self.progress_label.setText(t('downloading_progress', completed=0, total=len(self.tasks)))

	def on_task_finished(self, task_id):
		"""任务完成回调"""
		self.completed_count += 1

		# 检查任务是否失败
		status = self.table.item(task_id, 2).text()
		if status.startswith(t('download_failed', error='').split(':')[0]):
			self.failed_count += 1
			# 记录失败的任务以便重试
			self.failed_tasks.append(self.tasks[task_id])
			self.update_failed_label()
		elif status == t('completed'):
			# 下载成功，如果勾选了隐藏已完成则隐藏该行
			if self.hide_completed:
				self.table.setRowHidden(task_id, True)

		# 更新总体进度
		self.update_overall_progress()

		# 检查是否所有任务完成
		if self.completed_count >= len(self.tasks):
			self.all_task_done()

	def update_task_progress(self, task_id, progress):
		"""更新任务进度"""
		self.table.setItem(task_id, 1, QTableWidgetItem(f"{progress}%"))
		self.update_overall_progress()

	def update_task_status(self, task_id, status):
		"""更新任务状态"""
		self.table.setItem(task_id, 2, QTableWidgetItem(status))

	def update_failed_label(self):
		"""更新失败提示标签"""
		if self.failed_count > 0:
			self.failed_label.setText(t('failed_count', count=self.failed_count))
			self.failed_label.setVisible(True)
			self.failed_info_label.setVisible(True)
			# 调整窗口高度以容纳新增的标签，保持宽度不变
			# 计算失败标签需要的额外高度
			extra_height = self.failed_label.sizeHint().height() + self.failed_info_label.sizeHint().height() + 20
			new_height = self.height() + extra_height
			# 限制最大高度为600
			if new_height > 600:
				new_height = 600
			self.resize(self.width(), new_height)
		else:
			self.failed_label.setVisible(False)
			self.failed_info_label.setVisible(False)

	def update_overall_progress(self):
		"""更新总体进度"""
		# 计算已完成和下载中的任务的进度
		total_progress = 0
		valid_count = 0

		for i in range(len(self.tasks)):
			status = self.table.item(i, 2).text()
			# 使用翻译后的文本进行比较
			if not status.startswith(t('download_failed', error='').split(':')[0]) and status != t('add_failed') and status != t('task_cancelled'):
				progress_text = self.table.item(i, 1).text().replace("%", "")
				try:
					total_progress += int(progress_text)
					valid_count += 1
				except:
					pass

		if valid_count > 0:
			overall_progress = int(total_progress / valid_count)
			self.progress_bar.setValue(overall_progress)
			self.progress_label.setText(t('downloading_progress', completed=self.completed_count, total=len(self.tasks)) + f" - {overall_progress}%")

	def all_task_done(self):
		"""所有任务完成"""
		self.progress_bar.setValue(100)
		self.progress_label.setText(t('all_downloads_complete', completed=self.completed_count, total=len(self.tasks)))

		# 停止所有监控器
		for monitor in self.monitors:
			monitor.stop()
		self.monitors.clear()

		# 如果有失败任务，启用重试按钮
		if len(self.failed_tasks) > 0:
			self.retry_button.setEnabled(True)

	def closeEvent(self, event):
		"""窗口关闭事件"""
		# 停止所有监控器
		for monitor in self.monitors:
			monitor.stop()
		self.monitors.clear()

		# 发送下载完成信号（不在这里刷新，等所有dialog关闭后再刷新）
		self.download_completed.emit()

		# 注意：不关闭 aria2c，因为它是全局的，会在主程序关闭时关闭

		event.accept()

	def open_settings(self):
		"""打开aria2设置对话框"""
		dialog = Aria2SettingsDialog(self.aria2_manager, self)
		dialog.exec()

	def toggle_completed_visibility(self, state):
		"""切换已完成任务的可见性"""
		self.hide_completed = state == 2  # Qt.Checked = 2

		# 遍历所有行，根据状态显示/隐藏
		for i in range(self.table.rowCount()):
			status = self.table.item(i, 2).text()
			if status == t('completed'):
				self.table.setRowHidden(i, self.hide_completed)

	def retry_failed_tasks(self):
		"""重试失败的任务"""
		if not self.failed_tasks:
			return

		# 重置失败计数
		retry_count = len(self.failed_tasks)
		self.progress_label.setText(t('retrying_tasks', count=retry_count))

		# 禁用重试按钮
		self.retry_button.setEnabled(False)

		# 重置计数器
		self.failed_count = 0
		self.completed_count = len(self.tasks) - retry_count

		# 获取失败任务的索引
		failed_task_indices = []
		for failed_task in self.failed_tasks:
			for i, task in enumerate(self.tasks):
				if task['url'] == failed_task['url'] and task['file_name'] == failed_task['file_name']:
					failed_task_indices.append(i)
					break

		# 清空失败任务列表（准备重新收集）
		self.failed_tasks.clear()

		# 重新添加失败的任务
		for i in failed_task_indices:
			task = self.tasks[i]

			# 重置行状态
			self.table.setItem(i, 1, QTableWidgetItem("0%"))
			self.table.setItem(i, 2, QTableWidgetItem(t('waiting')))
			self.table.setRowHidden(i, False)

			# 使用新的路径逻辑
			download_dir = get_download_path(self.base_path, task['file_type'], self.batch_number)

			# 确保目录存在
			os.makedirs(download_dir, exist_ok=True)

			# 添加下载任务
			download = self.aria2_manager.add_download(task['url'], download_dir, task['file_name'])

			if download:
				self.table.setItem(i, 2, QTableWidgetItem(t('added_to_queue')))
				# 创建监控器
				monitor = DownloadMonitor(i, download.gid, self.aria2_manager, parent=self)
				monitor.progress.connect(self.update_task_progress)
				monitor.status_update.connect(self.update_task_status)
				monitor.finished.connect(self.on_task_finished)
				self.monitors.append(monitor)
			else:
				self.table.setItem(i, 2, QTableWidgetItem(t('add_failed')))
				self.completed_count += 1

		# 更新失败标签
		self.update_failed_label()
