import os
import sys
import subprocess
import socket
import time
import datetime
import configparser
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout,
    QPushButton, QProgressBar, QLabel, QTableWidget, QTableWidgetItem, QDialog, QHBoxLayout, QLineEdit
)
from PySide6.QtCore import Signal, QObject, QTimer
from PySide6.QtGui import QScreen
import aria2p

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
                print(f"使用内置的 aria2c: {aria2c_path}")
            else:
                print("未找到 aria2c，请确认已将 aria2c 添加到系统环境变量，或检查内置 aria2c 是否存在")
                return False
            
            # 启动 aria2c RPC 服务
            cmd = [
                aria2c_path,
                "--enable-rpc=true",
                f"--rpc-listen-port={self.port}",
                "--rpc-listen-all=false",
                "--continue=true",
                "--max-connection-per-server=16",
                "--min-split-size=1M",
                "--split=16",
                "--max-concurrent-downloads=20",
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
            options = {
                "dir": download_dir,
                "out": file_name,
                "continue": "true",
                "max-connection-per-server": "16",
                "split": "16",
                "min-split-size": "1M"
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
    
    def __init__(self, task_id, gid, aria2_manager, record_id, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.gid = gid
        self.aria2_manager = aria2_manager
        self.record_id = record_id
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
                self.status_update.emit(self.task_id, f"下载中 ({speed_mb:.2f} MB/s)")
        
        elif status == "complete":
            # 下载完成
            self.progress.emit(self.task_id, 100)
            self.status_update.emit(self.task_id, "已完成")
            self.stop()
            self.finished.emit(self.task_id)
        
        elif status == "error":
            # 下载失败
            error_msg = download.error_message or "未知错误"
            self.status_update.emit(self.task_id, f"下载失败: {error_msg}")
            if self.parent():
                self.parent().add_to_failed_record_list(self.record_id)
            self.stop()
            self.finished.emit(self.task_id)
        
        elif status == "removed":
            # 任务被移除
            self.status_update.emit(self.task_id, "任务已取消")
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
        config.set('database', 'main_db', 'a.db')
    
    if not config.has_option('database', 'deleted_db'):
        config.set('database', 'deleted_db', 'deleted.db')
    
    return config


def save_config(config):
    """保存配置文件"""
    config_path = get_config_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        config.write(f)


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
        # 图片路径: base_path/年份.G批号/图
        return os.path.join(base_path, batch_dir, "图")
    else:
        # 视频路径: base_path/年份.G批号
        return os.path.join(base_path, batch_dir)


class DownloadWindow(QDialog):
    # 自定义信号，用于通知下载完成
    download_completed = Signal()
    
    def __init__(self, tasks, base_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("下载管理器 (Aria2)")
        self.resize(600, 400)
        self.tasks = tasks
        self.aria2_manager = global_aria2_manager
        self.monitors = []
        self.completed_count = 0
        self.base_path = base_path or os.path.join(os.getcwd(), "downloads")
        
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
        self.progress_label = QLabel("准备下载...")
        self.progress_label.setText(f" {len(self.tasks)} 个任务已被添加。当前批号: G{self.batch_number}")
        layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # 表格初始化
        self.table = QTableWidget(len(self.tasks), 3)
        self.table.setHorizontalHeaderLabels(["URL", "进度", "状态"])
        # 设置每列的宽度
        self.table.setColumnWidth(0, 300)  # URL列宽度
        self.table.setColumnWidth(1, 100)  # 进度列宽度
        self.table.setColumnWidth(2, 200)  # 状态列宽度
        for i, task in enumerate(self.tasks):
            self.table.setItem(i, 0, QTableWidgetItem(task['url']))
            self.table.setItem(i, 1, QTableWidgetItem("0%"))
            self.table.setItem(i, 2, QTableWidgetItem("等待中"))
        layout.addWidget(self.table)

        # 开始按钮
        self.start_button = QPushButton("开始下载")
        self.start_button.clicked.connect(self.start_download)
        layout.addWidget(self.start_button)

        # 批号输入
        batch_layout = QHBoxLayout()
        batch_label = QLabel("批号:")
        batch_layout.addWidget(batch_label)
        self.batch_input = QLineEdit(self.batch_number)
        self.batch_input.setMaximumWidth(100)
        self.batch_input.textChanged.connect(self.on_batch_changed)
        batch_layout.addWidget(self.batch_input)
        batch_layout.addStretch()
        layout.addLayout(batch_layout)

        # 设置对话框的布局
        self.setLayout(layout)
        self.update_start_button_state()
    
    def on_batch_changed(self, text):
        """批号改变时更新"""
        self.batch_number = text
        self.progress_label.setText(f" {len(self.tasks)} 个任务已被添加。当前批号: G{self.batch_number}")

    def update_start_button_state(self):
        # 检查任务队列是否为空
        self.start_button.setEnabled(any(
            self.table.item(i, 2).text() not in ["已完成", "任务已取消"] and 
            not self.table.item(i, 2).text().startswith("下载失败")
            for i in range(self.table.rowCount())
        ))

    def start_download(self):
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("正在添加下载任务...")
        
        self.batch_input.setEnabled(False)

        # 检查 aria2 是否已启动
        if not self.aria2_manager or not self.aria2_manager.api:
            self.progress_label.setText("aria2c 未启动！")
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
                self.table.setItem(i, 2, QTableWidgetItem("已添加到队列"))
                # 创建监控器
                monitor = DownloadMonitor(i, download.gid, self.aria2_manager, task['record_id'], parent=self.parent())
                monitor.progress.connect(self.update_task_progress)
                monitor.status_update.connect(self.update_task_status)
                monitor.finished.connect(self.on_task_finished)
                self.monitors.append(monitor)
            else:
                self.table.setItem(i, 2, QTableWidgetItem("添加失败"))
                self.completed_count += 1
        
        self.progress_label.setText(f"下载中... (0/{len(self.tasks)})")

    def on_task_finished(self, task_id):
        """任务完成回调"""
        self.completed_count += 1
        
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

    def update_overall_progress(self):
        """更新总体进度"""
        # 计算已完成和下载中的任务的进度
        total_progress = 0
        valid_count = 0
        
        for i in range(len(self.tasks)):
            status = self.table.item(i, 2).text()
            if not status.startswith("下载失败") and status != "添加失败" and status != "任务已取消":
                progress_text = self.table.item(i, 1).text().replace("%", "")
                try:
                    total_progress += int(progress_text)
                    valid_count += 1
                except:
                    pass
        
        if valid_count > 0:
            overall_progress = int(total_progress / valid_count)
            self.progress_bar.setValue(overall_progress)
            self.progress_label.setText(f"下载中... ({self.completed_count}/{len(self.tasks)}) - {overall_progress}%")

    def all_task_done(self):
        """所有任务完成"""
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"所有下载完成！({self.completed_count}/{len(self.tasks)})")
        
        # 停止所有监控器
        for monitor in self.monitors:
            monitor.stop()
        self.monitors.clear()

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
    
    def add_to_failed_record_list(self, record_id):
        """添加失败记录到父窗口"""
        if self.parent():
            self.parent().add_to_failed_record_list(record_id)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 任务列表（示例）
    tasks = [
        {"url": "https://speed.hetzner.de/100MB.bin", "file_name": "test1.bin", "idr": "test1", "file_type": "test", "record_id": "1"},
        {"url": "https://speed.hetzner.de/100MB.bin", "file_name": "test2.bin", "idr": "test2", "file_type": "test", "record_id": "2"},
    ]

    window = DownloadWindow(tasks)
    window.show()
    sys.exit(app.exec())
