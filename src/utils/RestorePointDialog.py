# -*- coding: utf-8 -*-
# @Author: 神无月可乐
# @Create at: 2025/12/15
# 还原点相关对话框

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView
)

from i18n import t
from src.utils.RestorePointManager import RestorePointManager


class RestorePointInputDialog(QDialog):
    """创建还原点输入对话框"""
    
    def __init__(self, parent=None, default_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle(t('restore_point_input_title'))
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # 名称输入
        label = QLabel(t('restore_point_input_label'))
        layout.addWidget(label)
        
        self.name_input = QLineEdit()
        self.name_input.setText(default_name)
        self.name_input.selectAll()
        layout.addWidget(self.name_input)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.ok_btn = QPushButton(t('web_confirm'))
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        btn_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton(t('cancel'))
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def get_name(self) -> str:
        """获取输入的名称"""
        return self.name_input.text().strip()


class RestorePointListDialog(QDialog):
    """还原点列表对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('restore_point_list_title'))
        self.setMinimumSize(700, 400)
        
        self.manager = RestorePointManager()
        self.selected_point = None
        
        layout = QVBoxLayout()
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            t('restore_point_col_name'),
            t('restore_point_col_time'),
            t('restore_point_col_main_db'),
            t('restore_point_col_deleted_db'),
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.itemSelectionChanged.connect(self._update_button_state)
        layout.addWidget(self.table)
        
        # 按钮行
        btn_layout = QHBoxLayout()
        
        self.delete_btn = QPushButton(t('restore_point_delete_btn'))
        self.delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton(t('cancel'))
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.restore_btn = QPushButton(t('restore_point_restore_btn_real'))
        self.restore_btn.clicked.connect(self._on_restore)
        self.restore_btn.setDefault(True)
        btn_layout.addWidget(self.restore_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
        # 加载数据
        self._load_restore_points()
    
    def _load_restore_points(self):
        """加载还原点列表"""
        self.restore_points = self.manager.list_restore_points()
        self.table.setRowCount(len(self.restore_points))
        
        for row, point in enumerate(self.restore_points):
            # 名称
            name_item = QTableWidgetItem(point["name"])
            if not point["is_valid"]:
                name_item.setForeground(Qt.gray)
            self.table.setItem(row, 0, name_item)
            
            # 创建时间
            created_at = point["created_at"]
            if created_at:
                time_str = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = "-"
            time_item = QTableWidgetItem(time_str)
            self.table.setItem(row, 1, time_item)
            
            # 主数据库
            main_db_status = "✓" if point["main_db_exists"] else "✗"
            main_db_item = QTableWidgetItem(f"{main_db_status} {point['main_db_filename']}")
            if not point["main_db_exists"]:
                main_db_item.setForeground(Qt.red)
            self.table.setItem(row, 2, main_db_item)
            
            # 删除库
            deleted_db_status = "✓" if point["deleted_db_exists"] else "✗"
            deleted_db_item = QTableWidgetItem(f"{deleted_db_status} {point['deleted_db_filename']}")
            if not point["deleted_db_exists"]:
                deleted_db_item.setForeground(Qt.red)
            self.table.setItem(row, 3, deleted_db_item)
        
        # 更新按钮状态
        self._update_button_state()
    
    def _update_button_state(self):
        """更新按钮状态"""
        has_selection = len(self.table.selectedItems()) > 0
        self.restore_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def _on_double_click(self):
        """双击还原点"""
        self._on_restore()
    
    def _on_restore(self):
        """点击还原按钮"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        point = self.restore_points[row]
        
        if not point["is_valid"]:
            QMessageBox.warning(
                self,
                t('error'),
                t('restore_point_invalid')
            )
            return
        
        # 确认还原
        reply = QMessageBox.question(
            self,
            t('restore_point_restore_confirm_title'),
            t('restore_point_restore_confirm_msg', name=point["name"]),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.selected_point = point
            self.accept()
    
    def _on_delete(self):
        """点击删除按钮"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        point = self.restore_points[row]
        
        # 确认删除
        reply = QMessageBox.question(
            self,
            t('restore_point_delete_confirm_title'),
            t('restore_point_delete_confirm_msg', name=point["name"]),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, error = self.manager.delete_restore_point(point["folder_path"])
            if success:
                QMessageBox.information(
                    self,
                    t('hint'),
                    t('restore_point_delete_success', name=point["name"])
                )
                self._load_restore_points()
            else:
                QMessageBox.warning(
                    self,
                    t('error'),
                    error
                )
    
    def get_selected_point(self):
        """获取选中的还原点"""
        return self.selected_point
