# -*- coding: utf-8 -*-
# @Author: 神无月可乐
# @Create at: 2025/12/13 01:04
import os
import re

from PySide6.QtCore import QThread, Signal


class MediaDownloadCheckThread(QThread):
	"""检测是否有未下载的媒体"""
	# 信号：has_undownloaded (是否有未下载的媒体)
	result = Signal(bool)

	def __init__(self, database, media_path: str, exact_match: bool = False):
		super().__init__()
		self.database = database
		self.media_path = media_path
		self.exact_match = exact_match

	def _check_identifier(self, identifier: str, downloaded_files: set) -> bool:
		"""
		检查标识符是否已下载
		
		Returns:
			True 表示未下载，False 表示已下载
		"""
		if self.exact_match:
			return identifier not in downloaded_files
		else:
			return not any(identifier in f or f in identifier for f in downloaded_files)

	def _extract_media_from_legacy(self, legacy: dict, downloaded_files: set) -> bool:
		"""
		从 legacy 数据中检查是否有未下载的媒体（用于引用推文）
		
		Returns:
			True 表示有未下载的媒体，False 表示都已下载
		"""
		entities = legacy.get('extended_entities', legacy.get('entities', {}))
		media_list = entities.get('media', [])
		
		for media in media_list:
			media_type = media.get('type')
			identifier = None
			
			if media_type == 'photo':
				media_url = media.get('media_url_https', '')
				if media_url:
					match = re.search(r"/media/([A-Za-z0-9_-]+)\.", media_url)
					if match:
						identifier = match.group(1)
			elif media_type == 'video':
				video_info = media.get('video_info', {})
				variants = video_info.get('variants', [])
				mp4_variants = [v for v in variants if v.get('content_type') == 'video/mp4']
				if mp4_variants:
					best_variant = max(mp4_variants, key=lambda x: x.get('bitrate', 0))
					url = best_variant.get('url', '')
					match = re.search(r"vid/[a-zA-Z0-9_/-]+/([A-Za-z0-9_-]+)\.mp4", url)
					if match:
						identifier = match.group(1)
			
			if identifier and self._check_identifier(identifier, downloaded_files):
				return True
		
		return False

	def run(self):
		try:
			# 扫描本地已下载的文件
			downloaded_files = set()
			if os.path.exists(self.media_path):
				for root, dirs, files in os.walk(self.media_path):
					for file in files:
						# 去除文件扩展名
						file_name_without_extension = os.path.splitext(file)[0]
						downloaded_files.add(file_name_without_extension)

			# 获取所有记录
			records = self.database.all()

			# 检查是否有未下载的媒体
			for record in records:
				# 检查主推文的媒体
				medias = record.get("media", [])
				for media in medias:
					identifier = None
					if media.get("type") == "photo":
						url = media.get("original", "")
						match = re.search(r"media/([A-Za-z0-9_-]+)\?format=", url)
						if match:
							identifier = match.group(1)
					elif media.get("type") == "video":
						url = media.get("original", "")
						match = re.search(r"vid/[a-zA-Z0-9_/-]+/([A-Za-z0-9_-]+)\.mp4", url)
						if match:
							identifier = match.group(1)

					if identifier and self._check_identifier(identifier, downloaded_files):
						self.result.emit(True)
						return

				# 检查引用推文的媒体
				metadata = record.get("metadata", {})
				quoted_result = metadata.get("quoted_status_result", {}).get("result", {})
				if quoted_result:
					quoted_legacy = quoted_result.get("legacy", {})
					if quoted_legacy and self._extract_media_from_legacy(quoted_legacy, downloaded_files):
						self.result.emit(True)
						return

			# 所有媒体都已下载
			self.result.emit(False)
		except Exception as e:
			print(f"检测未下载媒体时出错: {e}")
			self.result.emit(False)
