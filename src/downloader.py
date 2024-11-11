import os
import sys
import requests
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout,
    QPushButton, QProgressBar, QLabel, QTableWidget, QTableWidgetItem, QSpinBox, QDialog, QHBoxLayout, QLineEdit
)
from PySide6.QtCore import Signal, QObject
from concurrent.futures import ThreadPoolExecutor
failed_record_list = []
class DownloadWorker(QObject):
    progress = Signal(int, int)  # 发射下载进度 (任务ID, 进度)
    status_update = Signal(int, str)  # 更新状态 (任务ID, 状态)
    finished = Signal()  # 新增 finished 信号，表示任务完成

    def __init__(self, task_id, url, record_id, file_path, file_name, file_type, parent=None):
        super().__init__(parent)
        self.url = url
        self.record_id = record_id
        self.file_path = file_path
        self.file_name = file_name
        self.file_type = file_type
        self.task_id = task_id

    def run(self):
        try:
            self.status_update.emit(self.task_id, "下载中")
            response = requests.get(self.url, stream=True)

            # 检查响应状态码
            if response.status_code != 200:
                self.status_update.emit(self.task_id, "下载失败：URL无效或文件不存在")
                if self.parent():
                    self.parent().add_to_failed_record_list(self.record_id)
                return  # 直接返回，停止下载

            total_size = int(response.headers.get("content-length", 0))
            downloaded_size = 0

            # 设置下载路径
            file_path = os.path.join(self.file_path, self.file_type, self.file_name)

            # 检查并创建路径
            download_dir = os.path.dirname(file_path)
            os.makedirs(download_dir, exist_ok=True)

            # 保存文件
            with open(file_path, "wb") as f:
                for data in response.iter_content(1024):
                    downloaded_size += len(data)
                    f.write(data)
                    progress_percent = int((downloaded_size / total_size) * 100)
                    self.progress.emit(self.task_id, progress_percent)
            self.progress.emit(self.task_id, 100)

            self.status_update.emit(self.task_id, "已完成")
        except Exception as e:
            self.status_update.emit(self.task_id, f"错误: {e}")
        finally:
            self.finished.emit()  # 任务完成后，发射 finished 信号

            # if self.parent(): # 如果错误, 可能是程序问题导致。而不是推文被删除。
            #     self.parent().add_to_failed_record_list(self.record_id)


class DownloadWindow(QDialog):
    def __init__(self, tasks, parent=None):
        super().__init__(parent)
        self.setWindowTitle("下载管理器")
        self.setGeometry(200, 200, 600, 400)
        self.tasks = tasks
        self.initUI()

    def initUI(self):
        # 主布局
        layout = QVBoxLayout(self)

        # 进度条和标签
        self.progress_label = QLabel("准备下载...")
        self.progress_label.setText(f" {len(self.tasks)} 个任务已被添加。")
        layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # 表格初始化
        self.table = QTableWidget(len(self.tasks), 3)  # 去除ID列
        self.table.setHorizontalHeaderLabels(["URL", "进度", "状态"])
        # 设置每列的宽度
        self.table.setColumnWidth(0, 300)  # URL列宽度
        self.table.setColumnWidth(1, 100)  # 进度列宽度
        self.table.setColumnWidth(2, 150)  # 状态列宽度
        for i, task in enumerate(self.tasks):
            self.table.setItem(i, 0, QTableWidgetItem(task['url']))
            self.table.setItem(i, 1, QTableWidgetItem("0%"))
            self.table.setItem(i, 2, QTableWidgetItem("等待中"))
        layout.addWidget(self.table)

        # 开始按钮
        self.start_button = QPushButton("开始下载")
        self.start_button.clicked.connect(self.start_download)
        layout.addWidget(self.start_button)

        # 最大并发下载数输入框 (左右排列)
        max_workers_layout = QHBoxLayout()
        max_workers_label = QLabel("最大并发下载数:")
        max_workers_layout.addWidget(max_workers_label)
        self.max_workers_input = QSpinBox()
        self.max_workers_input.setRange(1, 20)
        self.max_workers_input.setValue(20)
        max_workers_layout.addWidget(self.max_workers_input)
        layout.addLayout(max_workers_layout)

        path_layout = QHBoxLayout()
        path_label = QLabel("下载目标路径:")
        path_layout.addWidget(path_label)
        self.path_input = QLineEdit(str(os.path.join(os.getcwd(), "download")))
        path_layout.addWidget(self.path_input)
        layout.addLayout(path_layout)

        # 设置对话框的布局
        self.setLayout(layout)
        self.update_start_button_state()

    def update_start_button_state(self):
        # 检查任务队列是否为空
        self.start_button.setEnabled(any(
            self.table.item(i, 2).text() != "已完成" for i in range(self.table.rowCount())
        ))

    def start_download(self):
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("下载中...")

        self.max_workers_input.setEnabled(False)
        self.path_input.setEnabled(False)

        max_workers = self.max_workers_input.value()
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)

        # 创建并发任务队列
        for i, task in enumerate(self.tasks):
            file_path = self.path_input.text()
            worker = DownloadWorker(i, task['url'], task['record_id'], file_path, task['file_name'], task['file_type'], parent=self.parent())
            worker.progress.connect(self.update_task_progress)
            worker.status_update.connect(self.update_task_status)
            worker.finished.connect(lambda: self.cleanup_worker(worker))
            self.thread_pool.submit(worker.run)

    def cleanup_worker(self, worker):
        worker.progress.disconnect(self.update_task_progress)
        worker.status_update.disconnect(self.update_task_status)
        worker.finished.disconnect()


    def update_task_progress(self, task_id, progress):
        # 更新任务进度
        self.table.setItem(task_id, 1, QTableWidgetItem(f"{progress}%"))

        # 计算已完成和下载中的任务的进度，不包含失败任务
        completed_progress = sum(
            int(self.table.item(i, 1).text().replace("%", ""))
            for i in range(len(self.tasks))
            if not self.table.item(i, 2).text().startswith("下载失败") and not self.table.item(i, 2).text().startswith(
                "错误")
        )

        valid_task_count = sum(
            1 for i in range(len(self.tasks))
            if not self.table.item(i, 2).text().startswith("下载失败") and not self.table.item(i, 2).text().startswith(
                "错误")
        )

        overall_progress = int(completed_progress / valid_task_count) if valid_task_count > 0 else 100

        # 检查是否所有有效任务完成
        if all(self.table.item(i, 2).text() == "已完成" or
               self.table.item(i, 2).text().startswith("下载失败") or
               self.table.item(i, 2).text().startswith("错误")
               for i in range(len(self.tasks))):
            self.progress_bar.setValue(100)
            self.progress_label.setText("所有下载完成")
            self.all_task_done()
        else:
            self.progress_bar.setValue(overall_progress)
            self.progress_label.setText(f"总体进度: {overall_progress}%")

    def update_task_status(self, task_id, status):
        # 更新任务状态
        self.table.setItem(task_id, 2, QTableWidgetItem(status))
        if all(self.table.item(i, 2).text() == "已完成" for i in range(len(self.tasks))):
            self.progress_label.setText("所有下载完成")
            self.update_start_button_state()

    def all_task_done(self):
        # 在所有任务完成后手动释放线程池
        self.thread_pool.shutdown(wait=True)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 任务列表
    tasks = [
        {"url": "http://example.com/", "file_name": "test.html", "idr": "identifier", "file_type": "photo", "record_id": ""},
    ]

    window = DownloadWindow(tasks)
    window.show()
    sys.exit(app.exec())
