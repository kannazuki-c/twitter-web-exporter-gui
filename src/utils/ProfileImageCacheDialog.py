# -*- coding: utf-8 -*-
# 头像缓存管理对话框
import os
import re
import time
from typing import List, Dict, Set
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QProgressBar, QComboBox,
    QHeaderView, QMessageBox, QGroupBox, QProgressDialog
)
from PySide6.QtGui import QScreen

from i18n import t
import src.utils.globals as globals_module
# 注意：必须使用 downloader 而非 src.downloader，因为 MainWindow 使用的是 downloader
# Python 会将不同路径的导入视为不同模块，导致全局变量不共享
import downloader as downloader_module


class ProfileImageDownloadThread(QThread):
    """头像下载线程 - 使用 aria2"""
    progress = Signal(int, int)  # 当前进度, 总数
    item_result = Signal(str, bool, str)  # user_id, 是否成功, 错误信息
    finished_download = Signal(int, int)  # 成功数, 失败数

    def __init__(self, users: List[Dict], save_dir: str, method: str = "official"):
        """
        初始化下载线程
        
        Args:
            users: 用户列表，每个用户包含 user_id, screen_name, profile_image_url
            save_dir: 保存目录
            method: 下载方式 "official" 或 "unavatar"
        """
        super().__init__()
        self.users = users
        self.save_dir = save_dir
        self.method = method
        self._is_cancelled = False
        
        # 获取全局 aria2 管理器（使用模块引用，确保获取最新的全局变量值）
        self.aria2_manager = downloader_module.global_aria2_manager
        if self.aria2_manager is None:
            self.cancel()

    def cancel(self):
        """取消下载"""
        self._is_cancelled = True

    def run(self):
        """执行下载"""
        os.makedirs(self.save_dir, exist_ok=True)
        
        # 检查 aria2 管理器是否可用
        if not self.aria2_manager or not self.aria2_manager.api:
            # aria2 不可用，直接返回失败
            for user in self.users:
                self.item_result.emit(user.get('user_id', ''), False, "aria2 未启动")
            self.finished_download.emit(0, len(self.users))
            return
        
        success_count = 0
        fail_count = 0
        total = len(self.users)
        
        # 加载 aria2 配置
        config = downloader_module.load_config()
        max_conn = config.get('aria2', 'max_connection_per_server')
        split = config.get('aria2', 'split')
        timeout = config.get('aria2', 'timeout')
        
        # 存储下载任务: {gid: {'user_id': str, 'completed': bool}}
        download_tasks = {}
        
        # 添加所有下载任务
        for user in self.users:
            if self._is_cancelled:
                break
            
            user_id = user.get('user_id', '')
            screen_name = user.get('screen_name', '')
            profile_image_url = user.get('profile_image_url', '')
            
            # 根据方法构建 URL
            if self.method == "official":
                # 去掉 _normal 获取完整图片
                url = re.sub(r'_normal(\.[a-zA-Z]+)$', r'\1', profile_image_url)
                # 从原始 URL 获取扩展名
                match = re.search(r'\.([a-zA-Z]+)$', profile_image_url)
                ext = f".{match.group(1)}" if match else ".jpg"
            else:
                # 使用 unavatar
                # fallback=false 禁用默认头像，找不到时返回 404 而不是返回默认图片
                url = f"https://unavatar.io/twitter/{screen_name}?fallback=false"
                ext = ".jpg"  # unavatar 默认返回 jpg
            
            file_name = f"{user_id}{ext}"
            
            try:
                # 使用 aria2 添加下载任务（应用配置中的设置）
                options = {
                    "dir": self.save_dir,
                    "out": file_name,
                    "continue": "true",
                    "max-connection-per-server": max_conn,
                    "split": split,
                    "min-split-size": "1M",
                    "timeout": timeout,
                    "max-tries": "1"
                }
                download = self.aria2_manager.api.add_uris([url], options=options)
                
                if download:
                    download_tasks[download.gid] = {
                        'user_id': user_id,
                        'completed': False
                    }
                else:
                    fail_count += 1
                    self.item_result.emit(user_id, False, t('add_failed'))
            except Exception as e:
                fail_count += 1
                self.item_result.emit(user_id, False, str(e))
        
        # 发送初始进度（添加任务阶段已完成）
        completed = success_count + fail_count
        self.progress.emit(completed, total)
        
        # 轮询检查下载状态
        while download_tasks and not self._is_cancelled:
            completed_gids = []
            
            # 复制字典进行迭代，避免迭代时修改的问题
            for gid, task_info in list(download_tasks.items()):
                if task_info['completed']:
                    continue
                
                try:
                    download = self.aria2_manager.get_download(gid)
                    if not download:
                        continue
                    
                    status = download.status
                    
                    if status == "complete":
                        success_count += 1
                        task_info['completed'] = True
                        completed_gids.append(gid)
                        self.item_result.emit(task_info['user_id'], True, "")
                    
                    elif status in ["error", "removed"]:
                        fail_count += 1
                        task_info['completed'] = True
                        completed_gids.append(gid)
                        error_msg = getattr(download, 'error_message', None) or t('download_failed', error='Unknown')
                        self.item_result.emit(task_info['user_id'], False, error_msg)
                except Exception:
                    # 查询状态失败，跳过
                    pass
            
            # 移除已完成的任务
            for gid in completed_gids:
                del download_tasks[gid]
            
            # 更新进度
            completed = success_count + fail_count
            self.progress.emit(completed, total)
            
            # 如果还有未完成的任务，等待一下再检查
            if download_tasks:
                time.sleep(0.3)
        
        # 如果取消了，记录剩余任务为失败
        if self._is_cancelled:
            for gid, task_info in download_tasks.items():
                if not task_info['completed']:
                    fail_count += 1
                    self.item_result.emit(task_info['user_id'], False, t('task_cancelled'))
        
        self.finished_download.emit(success_count, fail_count)


class ProfileImageCacheDialog(QDialog):
    """头像缓存管理对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('profile_cache_title'))
        self.resize(700, 500)
        
        # 获取头像保存目录（在当前工作目录下）
        self.profile_images_dir = os.path.join(os.getcwd(), 'profile_images')
        
        # 下载线程
        self._download_thread = None
        
        # 用户数据
        self.all_users = []  # 所有需要头像的用户
        self.pending_users = []  # 未下载的用户
        
        # 加载进度对话框
        self.loading_dialog = None
        
        self.initUI()
        self.center_window()
        self.refresh_users()

    def center_window(self):
        """窗口居中"""
        from PySide6.QtWidgets import QApplication
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def initUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 状态信息组
        status_group = QGroupBox(t('profile_cache_status'))
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel(t('profile_cache_loading'))
        status_layout.addWidget(self.status_label)
        
        self.dir_label = QLabel(t('profile_cache_dir', path=self.profile_images_dir))
        self.dir_label.setStyleSheet("color: gray; font-size: 11px;")
        self.dir_label.setWordWrap(True)
        status_layout.addWidget(self.dir_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # 未下载列表
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            t('profile_cache_col_name'),
            t('profile_cache_col_screen_name'),
            t('profile_cache_col_user_id'),
            t('profile_cache_col_status')
        ])
        # 允许用户自由拖动列宽
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        # 设置初始列宽
        self.table.setColumnWidth(0, 150)  # 名称
        self.table.setColumnWidth(1, 120)  # Screen Name
        self.table.setColumnWidth(2, 150)  # User ID
        self.table.setColumnWidth(3, 200)  # 状态（宽一点显示错误信息）
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 操作区域
        action_layout = QHBoxLayout()
        
        # 获取方案选择
        action_layout.addWidget(QLabel(t('profile_cache_method')))
        self.method_combo = QComboBox()
        self.method_combo.addItem(t('profile_cache_method_official'), "official")
        self.method_combo.addItem(t('profile_cache_method_unavatar'), "unavatar")
        action_layout.addWidget(self.method_combo)
        
        action_layout.addStretch()
        
        # 刷新按钮
        self.refresh_btn = QPushButton(t('refresh'))
        self.refresh_btn.clicked.connect(self.refresh_users)
        action_layout.addWidget(self.refresh_btn)
        
        # 更新全部按钮
        self.update_all_btn = QPushButton(t('profile_cache_update_all'))
        self.update_all_btn.clicked.connect(self.start_download)
        action_layout.addWidget(self.update_all_btn)
        
        layout.addLayout(action_layout)

        # 关闭按钮
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        self.close_btn = QPushButton(t('close'))
        self.close_btn.clicked.connect(self.close)
        close_layout.addWidget(self.close_btn)
        layout.addLayout(close_layout)

    def refresh_users(self):
        """刷新用户列表（带加载指示器）"""
        # 显示加载对话框
        self.loading_dialog = QProgressDialog(t('loading_data'), None, 0, 0, self)
        self.loading_dialog.setWindowModality(Qt.ApplicationModal)
        self.loading_dialog.setCancelButton(None)
        self.loading_dialog.setWindowTitle(t('please_wait_title'))
        self.loading_dialog.show()
        
        # 清空表格
        self.table.clearContents()
        self.table.setRowCount(0)
        
        # 使用 QTimer 延迟加载数据，让加载对话框有时间显示
        QTimer.singleShot(100, self.load_users)

    def load_users(self):
        """加载所有用户信息并检查哪些头像未下载"""
        self.status_label.setText(t('profile_cache_loading'))
        
        # 从数据库获取所有用户信息
        all_tweets = globals_module.db.all()
        
        # 去重，收集所有用户
        users_dict: Dict[str, Dict] = {}  # user_id -> user_info
        
        for tweet in all_tweets:
            user_id = tweet.get('user_id', '')
            if not user_id:
                # 尝试从 metadata 中获取
                metadata = tweet.get('metadata', {})
                user_result = metadata.get('user_results', {}).get('result', {})
                user_id = user_result.get('rest_id', '')
            
            if user_id and user_id not in users_dict:
                users_dict[user_id] = {
                    'user_id': user_id,
                    'name': tweet.get('name', ''),
                    'screen_name': tweet.get('screen_name', ''),
                    'profile_image_url': tweet.get('profile_image_url', '')
                }
        
        self.all_users = list(users_dict.values())
        
        # 检查哪些头像已下载
        downloaded_ids = self._get_downloaded_profile_ids()
        
        self.pending_users = []
        for user in self.all_users:
            if user['user_id'] not in downloaded_ids:
                self.pending_users.append(user)
        
        # 更新状态
        total = len(self.all_users)
        downloaded = len(downloaded_ids)
        pending = len(self.pending_users)
        
        self.status_label.setText(t('profile_cache_stats', total=total, downloaded=downloaded, pending=pending))
        
        # 填充表格
        self.table.setRowCount(len(self.pending_users))
        for i, user in enumerate(self.pending_users):
            self.table.setItem(i, 0, QTableWidgetItem(user.get('name', '')))
            self.table.setItem(i, 1, QTableWidgetItem(user.get('screen_name', '')))
            self.table.setItem(i, 2, QTableWidgetItem(user.get('user_id', '')))
            self.table.setItem(i, 3, QTableWidgetItem(t('profile_cache_pending')))
        
        # 更新按钮状态
        self.update_all_btn.setEnabled(pending > 0)
        
        # 关闭加载对话框
        if self.loading_dialog:
            self.loading_dialog.close()
            self.loading_dialog = None

    def _get_downloaded_profile_ids(self) -> Set[str]:
        """获取已下载的头像 user_id 集合"""
        downloaded = set()
        if os.path.exists(self.profile_images_dir):
            for file in os.listdir(self.profile_images_dir):
                # 文件名就是 user_id（不含扩展名）
                name, ext = os.path.splitext(file)
                if ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    downloaded.add(name)
        return downloaded

    def start_download(self):
        """开始下载头像"""
        if not self.pending_users:
            return
        
        # 禁用按钮
        self.update_all_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.method_combo.setEnabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self.pending_users))
        
        # 获取方法
        method = self.method_combo.currentData()
        
        # 创建并启动下载线程
        self._download_thread = ProfileImageDownloadThread(
            self.pending_users,
            self.profile_images_dir,
            method
        )
        self._download_thread.progress.connect(self._on_progress)
        self._download_thread.item_result.connect(self._on_item_result)
        self._download_thread.finished_download.connect(self._on_download_finished)
        self._download_thread.start()

    def _on_progress(self, current: int, total: int):
        """进度更新"""
        self.progress_bar.setValue(current)

    def _on_item_result(self, user_id: str, success: bool, error: str):
        """单个项目结果"""
        # 更新表格中对应行的状态
        for i in range(self.table.rowCount()):
            if self.table.item(i, 2).text() == user_id:
                if success:
                    self.table.setItem(i, 3, QTableWidgetItem(t('profile_cache_success')))
                    self.table.item(i, 3).setForeground(Qt.green)
                else:
                    self.table.setItem(i, 3, QTableWidgetItem(t('profile_cache_failed', error=error)))
                    self.table.item(i, 3).setForeground(Qt.red)
                break

    def _on_download_finished(self, success_count: int, fail_count: int):
        """下载完成"""
        self.progress_bar.setVisible(False)
        
        # 重新启用按钮
        self.refresh_btn.setEnabled(True)
        self.method_combo.setEnabled(True)
        
        # 显示结果
        QMessageBox.information(
            self,
            t('profile_cache_complete_title'),
            t('profile_cache_complete_msg', success=success_count, failed=fail_count)
        )
        
        # 刷新列表（移除成功下载的项）
        self.refresh_users()

    def closeEvent(self, event):
        """关闭事件"""
        # 取消正在进行的下载
        if self._download_thread and self._download_thread.isRunning():
            self._download_thread.cancel()
            self._download_thread.wait(2000)
        event.accept()
