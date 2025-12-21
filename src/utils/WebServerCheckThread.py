# -*- coding: utf-8 -*-
# @Author: 神无月可乐
# @Create at: 2025/12/13 01:04
import time

from PySide6.QtCore import QThread, Signal

from webserver import is_cache_ready


class WebServerCheckThread(QThread):
	"""Web 服务器就绪检测线程"""
	# 信号：phase（1=服务可访问, 2=缓存就绪）, success
	phase_completed = Signal(int)
	timeout = Signal()

	def __init__(self, port: int, timeout_seconds: int = 20):
		super().__init__()
		self.port = port
		self.timeout_seconds = timeout_seconds
		self._stop_flag = False

	def stop(self):
		"""停止检测"""
		self._stop_flag = True

	def run(self):
		import urllib.request
		import urllib.error

		start_time = time.time()
		phase = 1  # 1: 检测服务可访问, 2: 检测缓存就绪

		while not self._stop_flag:
			elapsed = time.time() - start_time

			# 超时检测
			if elapsed > self.timeout_seconds:
				self.timeout.emit()
				return

			if phase == 1:
				# 第一阶段：检测服务是否可访问
				try:
					url = f"http://127.0.0.1:{self.port}/"
					req = urllib.request.Request(url, method='HEAD')
					with urllib.request.urlopen(req, timeout=0.5) as response:
						if response.status == 200:
							# 服务可访问，进入第二阶段
							phase = 2
							self.phase_completed.emit(1)
				except (urllib.error.URLError, urllib.error.HTTPError, OSError):
					# 服务尚未就绪，继续等待
					pass

			elif phase == 2:
				# 第二阶段：检测缓存是否构建完成
				if is_cache_ready():
					self.phase_completed.emit(2)
					return

			# 短暂休眠，避免过度占用 CPU
			time.sleep(0.1)
