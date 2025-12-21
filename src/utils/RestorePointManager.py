# -*- coding: utf-8 -*-
# @Author: 神无月可乐
# @Create at: 2025/12/15
# 还原点管理模块

import os
import json
import shutil
from datetime import datetime, date
from typing import List, Optional, Dict, Any


class RestorePointManager:
    """还原点管理器"""
    
    MANIFEST_FILENAME = "manifest.json"
    
    def __init__(self, base_dir: str = None):
        """初始化还原点管理器
        
        Args:
            base_dir: 还原点存储的基础目录，默认为运行目录下的 restore_point
        """
        if base_dir is None:
            base_dir = os.path.join(os.getcwd(), "restore_point")
        self.base_dir = base_dir
    
    def ensure_base_dir(self):
        """确保基础目录存在"""
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
    
    def get_today_count(self) -> int:
        """获取今日已创建的还原点数量
        
        通过读取所有还原点的清单文件，统计今天创建的还原点数量
        """
        today = date.today().isoformat()
        count = 0
        
        if not os.path.exists(self.base_dir):
            return 0
        
        for folder_name in os.listdir(self.base_dir):
            folder_path = os.path.join(self.base_dir, folder_name)
            if os.path.isdir(folder_path):
                manifest = self.read_manifest(folder_path)
                if manifest:
                    # 从时间戳中提取日期
                    timestamp = manifest.get("created_at", 0)
                    if timestamp:
                        created_date = datetime.fromtimestamp(timestamp).date().isoformat()
                        if created_date == today:
                            count += 1
        
        return count
    
    def create_restore_point(
        self, 
        name: str, 
        main_db_path: str, 
        deleted_db_path: str
    ) -> tuple[bool, str]:
        """创建还原点
        
        Args:
            name: 还原点名称（同时作为文件夹名）
            main_db_path: 主数据库文件路径
            deleted_db_path: 删除库文件路径
        
        Returns:
            (成功与否, 错误信息或还原点路径)
        """
        try:
            self.ensure_base_dir()
            
            # 清理名称中的非法字符
            safe_name = self._sanitize_folder_name(name)
            restore_point_dir = os.path.join(self.base_dir, safe_name)
            
            # 如果目录已存在，添加时间戳后缀
            if os.path.exists(restore_point_dir):
                timestamp = datetime.now().strftime("%H%M%S")
                safe_name = f"{safe_name}_{timestamp}"
                restore_point_dir = os.path.join(self.base_dir, safe_name)
            
            os.makedirs(restore_point_dir)
            
            # 复制数据库文件
            main_db_filename = os.path.basename(main_db_path)
            deleted_db_filename = os.path.basename(deleted_db_path)
            
            main_db_dest = os.path.join(restore_point_dir, main_db_filename)
            deleted_db_dest = os.path.join(restore_point_dir, deleted_db_filename)
            
            if os.path.exists(main_db_path):
                shutil.copy2(main_db_path, main_db_dest)
            
            if os.path.exists(deleted_db_path):
                shutil.copy2(deleted_db_path, deleted_db_dest)
            
            # 创建清单文件
            manifest = {
                "name": name,
                "created_at": datetime.now().timestamp(),
                "main_db_filename": main_db_filename,
                "deleted_db_filename": deleted_db_filename,
            }
            
            manifest_path = os.path.join(restore_point_dir, self.MANIFEST_FILENAME)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            return True, restore_point_dir
        
        except Exception as e:
            return False, str(e)
    
    def list_restore_points(self) -> List[Dict[str, Any]]:
        """列出所有有效的还原点
        
        Returns:
            还原点信息列表，按创建时间倒序排列
        """
        restore_points = []
        
        if not os.path.exists(self.base_dir):
            return restore_points
        
        for folder_name in os.listdir(self.base_dir):
            folder_path = os.path.join(self.base_dir, folder_name)
            if os.path.isdir(folder_path):
                manifest = self.read_manifest(folder_path)
                if manifest:
                    # 验证数据库文件是否存在
                    main_db_exists = os.path.exists(
                        os.path.join(folder_path, manifest.get("main_db_filename", ""))
                    )
                    deleted_db_exists = os.path.exists(
                        os.path.join(folder_path, manifest.get("deleted_db_filename", ""))
                    )
                    
                    restore_points.append({
                        "folder_name": folder_name,
                        "folder_path": folder_path,
                        "name": manifest.get("name", folder_name),
                        "created_at": manifest.get("created_at", 0),
                        "main_db_filename": manifest.get("main_db_filename", ""),
                        "deleted_db_filename": manifest.get("deleted_db_filename", ""),
                        "main_db_exists": main_db_exists,
                        "deleted_db_exists": deleted_db_exists,
                        "is_valid": main_db_exists or deleted_db_exists,
                    })
        
        # 按创建时间倒序排列
        restore_points.sort(key=lambda x: x["created_at"], reverse=True)
        return restore_points
    
    def restore_from_point(
        self, 
        folder_path: str, 
        main_db_path: str, 
        deleted_db_path: str,
        db_instance,
        ddb_instance
    ) -> tuple[bool, str]:
        """从还原点还原
        
        Args:
            folder_path: 还原点文件夹路径
            main_db_path: 目标主数据库路径
            deleted_db_path: 目标删除库路径
            db_instance: 主数据库实例（需要先关闭）
            ddb_instance: 删除库实例（需要先关闭）
        
        Returns:
            (成功与否, 错误信息或成功消息)
        """
        try:
            manifest = self.read_manifest(folder_path)
            if not manifest:
                return False, "Invalid restore point"
            
            # 关闭数据库连接
            db_instance.close()
            ddb_instance.close()
            
            # 复制还原点中的数据库文件到目标位置
            main_db_filename = manifest.get("main_db_filename", "")
            deleted_db_filename = manifest.get("deleted_db_filename", "")
            
            main_db_src = os.path.join(folder_path, main_db_filename)
            deleted_db_src = os.path.join(folder_path, deleted_db_filename)
            
            if os.path.exists(main_db_src):
                shutil.copy2(main_db_src, main_db_path)
            
            if os.path.exists(deleted_db_src):
                shutil.copy2(deleted_db_src, deleted_db_path)
            
            return True, manifest.get("name", "")
        
        except Exception as e:
            return False, str(e)
    
    def delete_restore_point(self, folder_path: str) -> tuple[bool, str]:
        """删除还原点
        
        Args:
            folder_path: 还原点文件夹路径
        
        Returns:
            (成功与否, 错误信息或成功消息)
        """
        try:
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def read_manifest(self, folder_path: str) -> Optional[Dict[str, Any]]:
        """读取还原点清单文件
        
        Args:
            folder_path: 还原点文件夹路径
        
        Returns:
            清单内容字典，如果读取失败返回 None
        """
        manifest_path = os.path.join(folder_path, self.MANIFEST_FILENAME)
        if not os.path.exists(manifest_path):
            return None
        
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    
    def _sanitize_folder_name(self, name: str) -> str:
        """清理文件夹名称中的非法字符
        
        Args:
            name: 原始名称
        
        Returns:
            清理后的名称
        """
        # Windows 文件名不允许的字符
        invalid_chars = '<>:"/\\|?*'
        result = name
        for char in invalid_chars:
            result = result.replace(char, '_')
        # 去除首尾空格和点
        result = result.strip(' .')
        # 如果结果为空，使用默认名称
        if not result:
            result = "restore_point"
        return result
