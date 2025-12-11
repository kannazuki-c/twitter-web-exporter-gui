# -*- coding: utf-8 -*-
"""
SQLite 数据库管理模块
用于替代 TinyDB，提升数据处理性能
"""

import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from threading import Lock


class TweetDatabase:
    """推文数据库管理类"""
    
    def __init__(self, db_path: str):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._lock = Lock()
        self._conn = None
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（线程安全）"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def _init_db(self):
        """初始化数据库表结构"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 创建推文表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tweets (
                    doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT UNIQUE NOT NULL,
                    created_at TEXT,
                    full_text TEXT,
                    name TEXT,
                    screen_name TEXT,
                    views_count INTEGER,
                    url TEXT,
                    media TEXT,
                    raw_data TEXT
                )
            ''')
            
            # 创建索引以提升查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tweets_id ON tweets(id)')
            
            conn.commit()
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为字典格式（兼容 TinyDB 格式）"""
        if row is None:
            return None
        
        # 从 raw_data 恢复完整数据
        raw_data = json.loads(row['raw_data']) if row['raw_data'] else {}
        
        # 添加 doc_id（兼容 TinyDB）
        raw_data['doc_id'] = row['doc_id']
        
        return raw_data
    
    def all(self) -> List[Dict[str, Any]]:
        """
        获取所有记录
        
        Returns:
            所有推文记录的列表
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tweets ORDER BY doc_id ASC')
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def get_all_ids(self) -> set:
        """
        获取所有记录的 id 集合（高性能方法）
        
        Returns:
            所有推文 id 的集合
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM tweets')
            return {row[0] for row in cursor.fetchall()}
    
    def insert(self, data: Dict[str, Any]) -> int:
        """
        插入单条记录
        
        Args:
            data: 推文数据字典
            
        Returns:
            插入记录的 doc_id
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO tweets (id, created_at, full_text, name, screen_name, views_count, url, media, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data.get('id'),
                    data.get('created_at'),
                    data.get('full_text'),
                    data.get('name'),
                    data.get('screen_name'),
                    data.get('views_count'),
                    data.get('url'),
                    json.dumps(data.get('media', []), ensure_ascii=False),
                    json.dumps(data, ensure_ascii=False)
                ))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # id 重复，跳过
                return -1
    
    def insert_multiple(self, data_list: List[Dict[str, Any]]) -> int:
        """
        批量插入记录
        
        Args:
            data_list: 推文数据字典列表
            
        Returns:
            成功插入的记录数
        """
        if not data_list:
            return 0
        
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            inserted_count = 0
            
            for data in data_list:
                try:
                    cursor.execute('''
                        INSERT INTO tweets (id, created_at, full_text, name, screen_name, views_count, url, media, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        data.get('id'),
                        data.get('created_at'),
                        data.get('full_text'),
                        data.get('name'),
                        data.get('screen_name'),
                        data.get('views_count'),
                        data.get('url'),
                        json.dumps(data.get('media', []), ensure_ascii=False),
                        json.dumps(data, ensure_ascii=False)
                    ))
                    inserted_count += 1
                except sqlite3.IntegrityError:
                    # id 重复，跳过
                    continue
            
            conn.commit()
            return inserted_count
    
    def remove(self, doc_ids: List[int] = None, tweet_id: str = None) -> int:
        """
        删除记录
        
        Args:
            doc_ids: 要删除的 doc_id 列表
            tweet_id: 要删除的推文 id
            
        Returns:
            删除的记录数
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if doc_ids:
                placeholders = ','.join('?' * len(doc_ids))
                cursor.execute(f'DELETE FROM tweets WHERE doc_id IN ({placeholders})', doc_ids)
            elif tweet_id:
                cursor.execute('DELETE FROM tweets WHERE id = ?', (tweet_id,))
            else:
                return 0
            
            conn.commit()
            return cursor.rowcount
    
    def get_by_id(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """
        通过推文 id 获取记录
        
        Args:
            tweet_id: 推文 id
            
        Returns:
            推文数据字典，如果不存在返回 None
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tweets WHERE id = ?', (tweet_id,))
            row = cursor.fetchone()
            return self._row_to_dict(row)
    
    def get_by_doc_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """
        通过 doc_id 获取记录
        
        Args:
            doc_id: 文档 id
            
        Returns:
            推文数据字典，如果不存在返回 None
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tweets WHERE doc_id = ?', (doc_id,))
            row = cursor.fetchone()
            return self._row_to_dict(row)
    
    def count(self) -> int:
        """
        获取记录总数
        
        Returns:
            记录总数
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM tweets')
            return cursor.fetchone()[0]
    
    def exists(self, tweet_id: str) -> bool:
        """
        检查推文 id 是否存在
        
        Args:
            tweet_id: 推文 id
            
        Returns:
            是否存在
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM tweets WHERE id = ? LIMIT 1', (tweet_id,))
            return cursor.fetchone() is not None
    
    def close(self):
        """关闭数据库连接"""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
    
    def __del__(self):
        """析构函数，确保关闭连接"""
        self.close()


class MigrationHelper:
    """数据迁移辅助类：从 TinyDB 迁移到 SQLite"""
    
    @staticmethod
    def migrate_from_tinydb(tinydb_path: str, sqlite_db: TweetDatabase, 
                           progress_callback=None) -> tuple:
        """
        从 TinyDB 数据库迁移数据到 SQLite
        
        Args:
            tinydb_path: TinyDB 数据库文件路径
            sqlite_db: SQLite 数据库实例
            progress_callback: 进度回调函数 (current, total)
            
        Returns:
            (迁移成功数, 跳过数, 错误数)
        """
        try:
            # 动态导入 tinydb（仅在迁移时需要）
            from tinydb import TinyDB
        except ImportError:
            raise ImportError("TinyDB 未安装，无法进行数据迁移。请先安装: pip install tinydb")
        
        if not os.path.exists(tinydb_path):
            raise FileNotFoundError(f"TinyDB 数据库文件不存在: {tinydb_path}")
        
        # 打开 TinyDB 数据库
        old_db = TinyDB(tinydb_path)
        all_records = old_db.all()
        total = len(all_records)
        
        # 获取已存在的 id
        existing_ids = sqlite_db.get_all_ids()
        
        migrated = 0
        skipped = 0
        errors = 0
        
        for i, record in enumerate(all_records):
            try:
                tweet_id = record.get('id')
                
                if tweet_id and tweet_id not in existing_ids:
                    doc_id = sqlite_db.insert(record)
                    if doc_id > 0:
                        migrated += 1
                        existing_ids.add(tweet_id)
                    else:
                        skipped += 1
                else:
                    skipped += 1
                    
            except Exception as e:
                errors += 1
                print(f"迁移记录时出错: {e}")
            
            # 进度回调
            if progress_callback and (i + 1) % 100 == 0:
                progress_callback(i + 1, total)
        
        # 最终进度回调
        if progress_callback:
            progress_callback(total, total)
        
        old_db.close()
        
        return (migrated, skipped, errors)
    
    @staticmethod
    def detect_tinydb_files(directory: str = None) -> List[str]:
        """
        检测目录中的 TinyDB 数据库文件
        
        Args:
            directory: 要检测的目录，默认为当前目录
            
        Returns:
            TinyDB 数据库文件路径列表
        """
        if directory is None:
            directory = os.getcwd()
        
        tinydb_files = []
        
        for file in os.listdir(directory):
            if file.endswith('.db'):
                file_path = os.path.join(directory, file)
                # 检查是否是 TinyDB 格式（JSON 格式）
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(100)  # 读取前100个字符
                        if content.strip().startswith('{'):
                            tinydb_files.append(file_path)
                except:
                    continue
        
        return tinydb_files


def get_db_extension(db_path: str) -> str:
    """
    获取数据库文件扩展名
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        文件扩展名（小写）
    """
    return os.path.splitext(db_path)[1].lower()


def is_sqlite_db(db_path: str) -> bool:
    """
    检查文件是否是 SQLite 数据库
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        是否是 SQLite 数据库
    """
    if not os.path.exists(db_path):
        return False
    
    try:
        with open(db_path, 'rb') as f:
            header = f.read(16)
            return header.startswith(b'SQLite format 3')
    except:
        return False


def is_tinydb_file(db_path: str) -> bool:
    """
    检查文件是否是 TinyDB 数据库（JSON 格式）
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        是否是 TinyDB 数据库
    """
    if not os.path.exists(db_path):
        return False
    
    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            content = f.read(100)
            return content.strip().startswith('{')
    except:
        return False

