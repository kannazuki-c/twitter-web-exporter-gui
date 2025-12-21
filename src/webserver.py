# -*- coding: utf-8 -*-
"""
Web 服务器模块
用于在局域网内提供推文浏览服务
"""

import os
import re
import json
import sys
import socket
import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory, abort
from werkzeug.serving import make_server
from database import TweetDatabase
from i18n import get_language, get_translations

# Web 服务器实例
_web_server = None
_server_thread = None
_http_server = None  # werkzeug 服务器实例，用于优雅关闭
_is_running = False
_cache_ready = False  # 媒体缓存是否已构建完成
_cache_building = False  # 媒体缓存是否正在构建
_profile_images_dir = None  # 头像缓存目录


class WebServer:
    """Web 服务器类"""
    
    def __init__(self, db: TweetDatabase, media_path: str, host: str = '0.0.0.0', port: int = 5001, deleted_db: TweetDatabase = None, allow_delete: bool = False):
        """
        初始化 Web 服务器
        
        Args:
            db: 数据库实例
            media_path: 媒体文件路径
            host: 监听地址
            port: 监听端口
            deleted_db: 删除库实例，用于过滤已删除的推文
            allow_delete: 是否允许远程删除推文
        """
        self.db = db
        self.deleted_db = deleted_db
        self.media_path = media_path
        self.host = host
        self.port = port
        self.allow_delete = allow_delete
        
        # 头像目录（在当前工作目录下）
        self.profile_images_dir = os.path.join(os.getcwd(), 'profile_images')
        
        # 缓存相关
        self._deleted_ids_cache = None
        self._cache_timestamp = 0
        self._cache_lock = threading.Lock()
        self._cache_ttl = 60  # 缓存60秒
        
        # 初始化媒体缓存为空，确保每次启动都会重新构建
        self._media_cache = None
        
        # 头像缓存（user_id -> 文件路径）
        self._profile_cache = None
        
        # 获取 web 文件夹路径（兼容开发环境和 PyInstaller 打包后环境）
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后的环境，资源在 _MEIPASS 目录下
            base_path = sys._MEIPASS
        else:
            # 开发环境，获取当前文件所在目录
            base_path = os.path.dirname(__file__)
        
        template_path = os.path.join(base_path, 'web')
        static_path = os.path.join(base_path, 'web', 'static')
        
        self.app = Flask(__name__, 
                        template_folder=template_path,
                        static_folder=static_path)
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        
        @self.app.route('/favicon.ico')
        def favicon():
            """提供 favicon 图标"""
            # 获取 app.ico 文件路径（兼容开发环境和 PyInstaller 打包后环境）
            if getattr(sys, 'frozen', False):
                # PyInstaller 打包后的环境，资源在 _MEIPASS 目录下
                base_path = sys._MEIPASS
            else:
                # 开发环境，获取项目根目录
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            ico_path = os.path.join(base_path, 'app.ico')
            if os.path.exists(ico_path):
                return send_from_directory(base_path, 'app.ico', mimetype='image/x-icon')
            abort(404)
        
        @self.app.route('/')
        def index():
            """主页"""
            # 获取当前语言和翻译字典
            current_lang = get_language()
            translations = get_translations(current_lang)
            # 将 allow_delete 状态和国际化信息注入到模板中，供前端使用
            return render_template('index.html', 
                                 allow_delete=self.allow_delete,
                                 current_lang=current_lang,
                                 translations=translations)
        
        @self.app.route('/api/tweets')
        def get_tweets():
            """获取推文列表 API（使用数据库分页和缓存）"""
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            
            # 搜索参数
            search_keyword = request.args.get('q', None, type=str)
            search_in_name = request.args.get('in_name', '0') == '1'
            search_in_screen_name = request.args.get('in_screen_name', '0') == '1'
            search_in_text = request.args.get('in_text', '0') == '1'
            
            # 筛选参数：包含未下载的媒体
            has_undownloaded_media = request.args.get('has_undownloaded_media', '0') == '1'
            
            # 限制每页数量
            per_page = min(per_page, 200)
            
            # 获取已删除的推文ID（使用缓存）
            deleted_ids = self._get_deleted_ids()
            
            # 如果需要筛选未下载媒体，需要特殊处理
            if has_undownloaded_media:
                # 获取所有符合搜索条件的推文，然后在应用层过滤
                all_tweets, _ = self.db.get_paginated(
                    page=1, 
                    per_page=999999,  # 获取所有
                    exclude_ids=deleted_ids,
                    search_keyword=search_keyword,
                    search_in_name=search_in_name,
                    search_in_screen_name=search_in_screen_name,
                    search_in_text=search_in_text
                )
                
                # 过滤出包含未下载媒体的推文
                filtered_tweets = []
                for tweet in all_tweets:
                    if self._has_undownloaded_media(tweet):
                        filtered_tweets.append(tweet)
                
                # 手动分页
                total = len(filtered_tweets)
                total_pages = (total + per_page - 1) // per_page if total > 0 else 1
                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page
                paged_tweets = filtered_tweets[start_idx:end_idx]
                
                # 处理推文数据
                processed_tweets = []
                for tweet in paged_tweets:
                    processed = self._process_tweet(tweet)
                    processed_tweets.append(processed)
                
                return jsonify({
                    'tweets': processed_tweets,
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'total_pages': total_pages,
                    'has_prev': page > 1,
                    'has_next': page < total_pages,
                    'allow_delete': self.allow_delete
                })
            
            # 普通分页查询（无未下载媒体筛选）
            tweets, total = self.db.get_paginated(
                page=page, 
                per_page=per_page, 
                exclude_ids=deleted_ids,
                search_keyword=search_keyword,
                search_in_name=search_in_name,
                search_in_screen_name=search_in_screen_name,
                search_in_text=search_in_text
            )
            
            # 计算总页数
            total_pages = (total + per_page - 1) // per_page if total > 0 else 1
            
            # 处理推文数据，添加媒体信息
            processed_tweets = []
            for tweet in tweets:
                processed = self._process_tweet(tweet)
                processed_tweets.append(processed)
            
            return jsonify({
                'tweets': processed_tweets,
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages,
                'allow_delete': self.allow_delete
            })
        
        @self.app.route('/api/config')
        def get_config():
            """获取服务器配置 API"""
            # 通过方法获取最新值，确保读取到最新的状态
            return jsonify({
                'allow_delete': self.get_allow_delete()
            })
        
        @self.app.route('/api/tweet/<tweet_id>')
        def get_tweet(tweet_id):
            """获取单条推文 API"""
            # 检查是否在删除库中
            deleted_ids = self._get_deleted_ids()
            if tweet_id in deleted_ids:
                return jsonify({'error': 'Tweet not found'}), 404
            
            tweet = self.db.get_by_id(tweet_id)
            if tweet:
                return jsonify(self._process_tweet(tweet))
            return jsonify({'error': 'Tweet not found'}), 404
        
        @self.app.route('/api/tweet/<tweet_id>', methods=['DELETE'])
        def delete_tweet(tweet_id):
            """删除推文 API"""
            if not self.allow_delete:
                return jsonify({'error': 'Delete operation is not allowed'}), 403
            
            # 获取删除方式：permanent（彻底删除）或 move（移动到deleted.db）
            delete_type = request.args.get('type', 'move')  # 默认移动到deleted.db
            # 是否同时删除媒体文件
            delete_media = request.args.get('delete_media', '0') == '1'
            
            # 检查推文是否存在
            tweet = self.db.get_by_id(tweet_id)
            if not tweet:
                return jsonify({'error': 'Tweet not found'}), 404
            
            # 检查是否已在删除库中
            deleted_ids = self._get_deleted_ids()
            if tweet_id in deleted_ids:
                return jsonify({'error': 'Tweet already deleted'}), 400
            
            # 如果需要删除媒体文件，先获取媒体文件路径
            media_files_to_delete = []
            if delete_media:
                processed = self._process_tweet(tweet)
                media_files_to_delete = processed.get('media_paths', [])
            
            try:
                if delete_type == 'permanent':
                    # 彻底删除
                    self.db.remove(tweet_id=tweet_id)
                    # 清除缓存，因为总数可能变化
                    self._invalidate_cache()
                else:
                    # 移动到deleted.db
                    if self.deleted_db:
                        # 清理临时字段后插入到删除数据库
                        clean_tweet = {k: v for k, v in tweet.items() if not k.startswith('_') and k != 'doc_id'}
                        self.deleted_db.insert(clean_tweet)
                        # 从主数据库删除
                        self.db.remove(tweet_id=tweet_id)
                        # 清除缓存
                        self._invalidate_cache()
                    else:
                        return jsonify({'error': 'Deleted database not configured'}), 500
                
                # 删除媒体文件
                deleted_media_count = 0
                if delete_media and media_files_to_delete:
                    for file_path in media_files_to_delete:
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                deleted_media_count += 1
                                # 从媒体缓存中移除
                                if self._media_cache:
                                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                                    if base_name in self._media_cache:
                                        del self._media_cache[base_name]
                        except Exception as e:
                            # 媒体文件删除失败不影响整体结果，只记录日志
                            print(f"删除媒体文件失败: {file_path}, 错误: {e}")
                
                return jsonify({
                    'success': True, 
                    'message': 'Tweet deleted successfully',
                    'deleted_media_count': deleted_media_count
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/tweet/<tweet_id>/locate')
        def locate_tweet(tweet_id):
            """定位推文在非搜索模式下的页码 API"""
            per_page = request.args.get('per_page', 10, type=int)
            per_page = min(per_page, 200)
            
            # 检查推文是否存在
            tweet = self.db.get_by_id(tweet_id)
            if not tweet:
                return jsonify({'error': 'Tweet not found'}), 404
            
            # 检查是否在删除库中
            deleted_ids = self._get_deleted_ids()
            if tweet_id in deleted_ids:
                return jsonify({'error': 'Tweet not found'}), 404
            
            # 获取推文在非搜索模式下的位置
            position = self.db.get_tweet_position(tweet_id, exclude_ids=deleted_ids)
            if position < 0:
                return jsonify({'error': 'Tweet not found'}), 404
            
            # 计算页码
            page = (position - 1) // per_page + 1
            
            return jsonify({
                'success': True,
                'page': page,
                'position': position
            })
        
        @self.app.route('/api/tweet/<tweet_id>/clear_quote', methods=['POST'])
        def clear_quote(tweet_id):
            """清除引用推文数据 API"""
            if not self.allow_delete:
                return jsonify({'error': 'This operation is not allowed'}), 403
            
            # 获取推文
            tweet = self.db.get_by_id(tweet_id)
            if not tweet:
                return jsonify({'error': 'Tweet not found'}), 404
            
            # 检查是否有引用推文
            quoted_status = tweet.get('quoted_status')
            metadata = tweet.get('metadata', {})
            quoted_result = metadata.get('quoted_status_result', {}).get('result', {})
            
            if not quoted_status and not quoted_result:
                return jsonify({'error': 'This tweet has no quoted content'}), 400
            
            try:
                # 清除引用推文相关数据
                # 1. 清除 quoted_status
                if 'quoted_status' in tweet:
                    del tweet['quoted_status']
                
                # 2. 清除 metadata.quoted_status_result.result
                if 'metadata' in tweet and 'quoted_status_result' in tweet['metadata']:
                    del tweet['metadata']['quoted_status_result']
                
                # 3. 清除 full_text 中的引用链接（可选，通常以 https://t.co/xxx 结尾）
                # 这里不做处理，保留原文本
                
                # 更新数据库
                success = self.db.update(tweet_id, tweet)
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': 'Quote data cleared successfully'
                    })
                else:
                    return jsonify({'error': 'Failed to update database'}), 500
                    
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/media/<path:filename>')
        def serve_media(filename):
            """提供媒体文件服务"""
            if not self.media_path or not os.path.exists(self.media_path):
                abort(404)
            
            # 安全检查：防止路径遍历攻击
            safe_path = os.path.normpath(filename)
            if safe_path.startswith('..') or safe_path.startswith('/') or safe_path.startswith('\\'):
                abort(404)
            
            # 获取文件名（不带路径和扩展名）
            base_name = os.path.splitext(os.path.basename(safe_path))[0]
            
            # 递归搜索媒体目录
            found_file = self._find_media_file(base_name)
            if found_file:
                # 返回找到的文件
                file_dir = os.path.dirname(found_file)
                file_name = os.path.basename(found_file)
                return send_from_directory(file_dir, file_name)
            
            abort(404)
        
        @self.app.route('/profile/<user_id>')
        def serve_profile_image(user_id):
            """提供本地头像服务"""
            # 确保头像缓存已构建
            if self._profile_cache is None:
                self._build_profile_cache()
            
            # 从缓存中查找
            if self._profile_cache and user_id in self._profile_cache:
                file_path = self._profile_cache[user_id]
                file_dir = os.path.dirname(file_path)
                file_name = os.path.basename(file_path)
                return send_from_directory(file_dir, file_name)
            
            # 未找到，返回 404 让前端处理回退逻辑
            # 这样在混合模式下，前端的 onerror 事件会被触发，可以回退到 Twitter CDN
            abort(404)
        
        @self.app.route('/res/<path:filename>')
        def serve_res(filename):
            """提供静态资源"""
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(__file__)
            
            res_path = os.path.join(base_path, 'web', 'res')
            
            # 安全检查
            safe_path = os.path.normpath(filename)
            if safe_path.startswith('..') or safe_path.startswith('/') or safe_path.startswith('\\'):
                abort(404)
            
            file_path = os.path.join(res_path, safe_path)
            if os.path.exists(file_path):
                return send_from_directory(res_path, safe_path)
            
            abort(404)
        
        @self.app.route('/api/reload', methods=['POST'])
        def reload_server():
            """重载服务器（刷新媒体缓存）API"""
            try:
                # 刷新媒体缓存
                self.refresh_media_cache()
                # 刷新头像缓存
                self._build_profile_cache()
                return jsonify({
                    'success': True,
                    'message': 'Server reloaded successfully'
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def _has_undownloaded_media(self, tweet: dict) -> bool:
        """
        检查推文是否包含未下载的媒体（包括引用推文中的媒体）
        
        Args:
            tweet: 原始推文数据
            
        Returns:
            如果有任何媒体未下载返回 True，否则返回 False
        """
        # 确保媒体缓存已构建
        if self._media_cache is None:
            self._build_media_cache()
        
        # 检查主推文的媒体
        media_list = tweet.get('media', [])
        for media in media_list:
            media_type = media.get('type')
            if media_type == 'photo':
                url = media.get('original', '')
                # 提取图片标识符
                match = re.search(r"media/([A-Za-z0-9_-]+)\?format=", url)
                if match:
                    identifier = match.group(1)
                    # 检查是否已下载
                    if not self._media_cache or identifier not in self._media_cache:
                        return True
            elif media_type == 'video':
                url = media.get('original', '')
                # 提取视频标识符
                match = re.search(r"vid/[a-zA-Z0-9_/-]+/([A-Za-z0-9_-]+)\.mp4", url)
                if match:
                    identifier = match.group(1)
                    # 检查是否已下载
                    if not self._media_cache or identifier not in self._media_cache:
                        return True
        
        # 检查引用推文的媒体
        metadata = tweet.get('metadata', {})
        quoted_result = metadata.get('quoted_status_result', {}).get('result', {})
        if quoted_result:
            quoted_legacy = quoted_result.get('legacy', {})
            if quoted_legacy:
                # 优先使用 extended_entities，没有则使用 entities
                entities = quoted_legacy.get('extended_entities', quoted_legacy.get('entities', {}))
                quoted_media_list = entities.get('media', [])
                
                for media in quoted_media_list:
                    media_type = media.get('type')
                    if media_type == 'photo':
                        media_url = media.get('media_url_https', '')
                        if media_url:
                            # 提取图片标识符
                            match = re.search(r"/media/([A-Za-z0-9_-]+)\.", media_url)
                            if match:
                                identifier = match.group(1)
                                # 检查是否已下载
                                if not self._media_cache or identifier not in self._media_cache:
                                    return True
                    elif media_type == 'video':
                        # 视频需要从 video_info 中获取
                        video_info = media.get('video_info', {})
                        variants = video_info.get('variants', [])
                        mp4_variants = [v for v in variants if v.get('content_type') == 'video/mp4']
                        if mp4_variants:
                            best_variant = max(mp4_variants, key=lambda x: x.get('bitrate', 0))
                            url = best_variant.get('url', '')
                            match = re.search(r"vid/[a-zA-Z0-9_/-]+/([A-Za-z0-9_-]+)\.mp4", url)
                            if match:
                                identifier = match.group(1)
                                # 检查是否已下载
                                if not self._media_cache or identifier not in self._media_cache:
                                    return True
        
        return False
    
    def _find_media_file(self, base_name: str) -> str:
        """
        在媒体目录中递归搜索文件
        
        Args:
            base_name: 文件名（不含扩展名）
            
        Returns:
            找到的文件完整路径，如果没找到返回 None
        """
        # 使用缓存提高性能
        # 如果缓存不存在或为空，重新构建
        if self._media_cache is None:
            self._build_media_cache()
        
        # 从缓存中查找
        if self._media_cache and base_name in self._media_cache:
            return self._media_cache[base_name]
        
        return None
    
    def _build_media_cache(self):
        """构建媒体文件缓存"""
        global _cache_ready, _cache_building
        _cache_building = True
        _cache_ready = False
        
        # 强制重新构建缓存，清空旧缓存
        self._media_cache = {}
        extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mov'}
        
        if not self.media_path or not os.path.exists(self.media_path):
            _cache_building = False
            _cache_ready = True
            return
        
        # 递归遍历媒体目录
        for root, dirs, files in os.walk(self.media_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in extensions:
                    base_name = os.path.splitext(file)[0]
                    full_path = os.path.join(root, file)
                    # 如果同名文件已存在，优先保留已有的
                    if base_name not in self._media_cache:
                        self._media_cache[base_name] = full_path
        
        _cache_building = False
        _cache_ready = True
    
    def refresh_media_cache(self):
        """刷新媒体文件缓存"""
        if hasattr(self, '_media_cache'):
            del self._media_cache
        self._build_media_cache()
    
    def _build_profile_cache(self):
        """构建头像文件缓存"""
        self._profile_cache = {}
        extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        
        if not self.profile_images_dir or not os.path.exists(self.profile_images_dir):
            return
        
        # 遍历头像目录
        for file in os.listdir(self.profile_images_dir):
            ext = os.path.splitext(file)[1].lower()
            if ext in extensions:
                # 文件名就是 user_id
                user_id = os.path.splitext(file)[0]
                full_path = os.path.join(self.profile_images_dir, file)
                self._profile_cache[user_id] = full_path
    
    def _get_deleted_ids(self) -> set:
        """
        获取已删除的推文ID集合（带缓存）
        
        Returns:
            已删除推文ID的集合
        """
        with self._cache_lock:
            current_time = time.time()
            # 如果缓存有效，直接返回
            if self._deleted_ids_cache is not None and (current_time - self._cache_timestamp) < self._cache_ttl:
                return self._deleted_ids_cache
            
            # 重新加载缓存
            if self.deleted_db:
                self._deleted_ids_cache = self.deleted_db.get_all_ids()
            else:
                self._deleted_ids_cache = set()
            
            self._cache_timestamp = current_time
            return self._deleted_ids_cache
    
    def _invalidate_cache(self):
        """使缓存失效"""
        with self._cache_lock:
            self._deleted_ids_cache = None
            self._cache_timestamp = 0
    
    def get_allow_delete(self) -> bool:
        """获取是否允许删除的状态"""
        return self.allow_delete
    
    def _get_full_profile_image_url(self, url: str) -> str:
        """
        获取完整尺寸的头像 URL（去掉 _normal 后缀）
        
        Args:
            url: 原始头像 URL，如 https://pbs.twimg.com/profile_images/xxx/abc_normal.jpg
            
        Returns:
            完整尺寸的头像 URL，如 https://pbs.twimg.com/profile_images/xxx/abc.jpg
        """
        if not url:
            return url
        # 去掉 _normal 后缀（在扩展名之前）
        # 例如: abc_normal.jpg -> abc.jpg
        return re.sub(r'_normal(\.[a-zA-Z]+)$', r'\1', url)
    
    def _parse_twitter_date(self, date_str: str) -> int:
        """
        解析日期字符串并转换为毫秒时间戳
        
        Args:
            date_str: 日期字符串，支持以下格式：
                - "2023-06-20 21:20:39 +08:00" （数据库存储格式）
                - "Sun Jun 09 21:43:26 +0000 2024" （Twitter 原始格式）
            
        Returns:
            毫秒时间戳，解析失败返回 0
        """
        if not date_str:
            return 0
        
        # 尝试多种日期格式
        formats = [
            "%Y-%m-%d %H:%M:%S %z",      # 数据库格式: "2023-06-20 21:20:39 +08:00"
            "%a %b %d %H:%M:%S %z %Y",   # Twitter 格式: "Sun Jun 09 21:43:26 +0000 2024"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return int(dt.timestamp() * 1000)
            except ValueError:
                continue
        
        return 0
    
    def _extract_media_from_legacy(self, legacy: dict) -> tuple:
        """
        从 legacy 数据中提取媒体信息
        
        Args:
            legacy: legacy 数据字典
            
        Returns:
            (photos, videos, media_paths) 元组
        """
        photos = []
        videos = []
        media_paths = []
        
        # 优先使用 extended_entities，没有则使用 entities
        entities = legacy.get('extended_entities', legacy.get('entities', {}))
        media_list = entities.get('media', [])
        
        for media in media_list:
            media_type = media.get('type')
            if media_type == 'photo':
                # 构造原图 URL
                media_url = media.get('media_url_https', '')
                if media_url:
                    # 转换为原图 URL 格式
                    url = f"{media_url}?format=jpg&name=orig"
                    # 提取图片标识符
                    match = re.search(r"/media/([A-Za-z0-9_-]+)\.", media_url)
                    if match:
                        identifier = match.group(1)
                        photos.append({
                            'id': identifier,
                            'original_url': url,
                            'local_url': f'/media/{identifier}'
                        })
                        # 获取媒体文件完整路径
                        if self._media_cache and identifier in self._media_cache:
                            media_paths.append(self._media_cache[identifier])
            elif media_type == 'video':
                # 视频需要从 video_info 中获取最高质量的 URL
                video_info = media.get('video_info', {})
                variants = video_info.get('variants', [])
                # 过滤出 mp4 格式并按比特率排序
                mp4_variants = [v for v in variants if v.get('content_type') == 'video/mp4']
                if mp4_variants:
                    # 选择比特率最高的
                    best_variant = max(mp4_variants, key=lambda x: x.get('bitrate', 0))
                    url = best_variant.get('url', '')
                    # 提取视频标识符
                    match = re.search(r"vid/[a-zA-Z0-9_/-]+/([A-Za-z0-9_-]+)\.mp4", url)
                    if match:
                        identifier = match.group(1)
                        videos.append({
                            'id': identifier,
                            'original_url': url,
                            'local_url': f'/media/{identifier}.mp4'
                        })
                        # 获取媒体文件完整路径
                        if self._media_cache and identifier in self._media_cache:
                            media_paths.append(self._media_cache[identifier])
        
        return photos, videos, media_paths
    
    def _extract_quoted_tweet(self, tweet: dict) -> dict:
        """
        从推文中提取引用推文信息
        
        Args:
            tweet: 原始推文数据
            
        Returns:
            引用推文信息字典，如果没有引用则返回 None
        """
        # 检查 quoted_status 字段（只是ID）
        quoted_status_id = tweet.get('quoted_status')
        if not quoted_status_id:
            return None
        
        # 从 metadata.quoted_status_result.result 获取完整数据
        metadata = tweet.get('metadata', {})
        quoted_result = metadata.get('quoted_status_result', {}).get('result', {})
        
        if not quoted_result:
            # 没有完整数据，只返回 ID
            return {
                'id': quoted_status_id,
                'has_full_data': False
            }
        
        # 提取原作者信息
        core = quoted_result.get('core', {})
        user_result = core.get('user_results', {}).get('result', {})
        user_core = user_result.get('core', {})
        user_avatar = user_result.get('avatar', {})
        
        # 提取原推文内容
        legacy = quoted_result.get('legacy', {})
        
        # 提取原推文媒体
        photos, videos, media_paths = self._extract_media_from_legacy(legacy)
        
        # 检查是否有嵌套引用（第二层只有ID）
        nested_quoted_id = None
        nested_quoted_ref = quoted_result.get('quotedRefResult', {}).get('result', {})
        if nested_quoted_ref:
            nested_quoted_id = nested_quoted_ref.get('rest_id')
        # 也检查 legacy 中的 quoted_status_id_str
        if not nested_quoted_id:
            nested_quoted_id = legacy.get('quoted_status_id_str')
        
        # 获取引用推文作者的 user_id
        quoted_user_id = user_result.get('rest_id', '')
        
        return {
            'id': quoted_result.get('rest_id', quoted_status_id),
            'has_full_data': True,
            'full_text': legacy.get('full_text', ''),
            'name': user_core.get('name', ''),
            'screen_name': user_core.get('screen_name', ''),
            'user_id': quoted_user_id,
            'profile_image_url': self._get_full_profile_image_url(user_avatar.get('image_url', '')),
            'photos': photos,
            'videos': videos,
            'media_count': len(photos) + len(videos),
            'media_paths': media_paths,
            'url': f"https://twitter.com/{user_core.get('screen_name', '')}/status/{quoted_result.get('rest_id', quoted_status_id)}",
            'nested_quoted_id': nested_quoted_id  # 嵌套引用的ID（如果有）
        }
    
    def _process_tweet(self, tweet: dict) -> dict:
        """
        处理推文数据，提取关键信息
        
        Args:
            tweet: 原始推文数据
            
        Returns:
            处理后的推文数据
        """
        # 提取媒体信息
        media_list = tweet.get('media', [])
        photos = []
        videos = []
        media_paths = []  # 媒体文件完整路径列表
        
        for media in media_list:
            media_type = media.get('type')
            if media_type == 'photo':
                url = media.get('original', '')
                # 提取图片标识符
                match = re.search(r"media/([A-Za-z0-9_-]+)\?format=", url)
                if match:
                    identifier = match.group(1)
                    photos.append({
                        'id': identifier,
                        'original_url': url,
                        'local_url': f'/media/{identifier}'
                    })
                    # 获取媒体文件完整路径
                    if self._media_cache and identifier in self._media_cache:
                        media_paths.append(self._media_cache[identifier])
            elif media_type == 'video':
                url = media.get('original', '')
                # 提取视频标识符
                match = re.search(r"vid/[a-zA-Z0-9_/-]+/([A-Za-z0-9_-]+)\.mp4", url)
                if match:
                    identifier = match.group(1)
                    videos.append({
                        'id': identifier,
                        'original_url': url,
                        'local_url': f'/media/{identifier}.mp4'
                    })
                    # 获取媒体文件完整路径
                    if self._media_cache and identifier in self._media_cache:
                        media_paths.append(self._media_cache[identifier])
        
        # 提取引用推文信息
        quoted_tweet = self._extract_quoted_tweet(tweet)
        
        # 如果有引用推文，将其媒体路径也加入到 media_paths 中
        if quoted_tweet and quoted_tweet.get('has_full_data'):
            media_paths.extend(quoted_tweet.get('media_paths', []))
        
        # 获取用户 ID（用于本地头像）
        user_id = tweet.get('user_id', '')
        if not user_id:
            # 尝试从 metadata 中获取
            metadata = tweet.get('metadata', {})
            user_result = metadata.get('user_results', {}).get('result', {})
            user_id = user_result.get('rest_id', '')
        
        result = {
            'id': tweet.get('id', ''),
            'doc_id': tweet.get('doc_id', ''),
            'created_at_ts': self._parse_twitter_date(tweet.get('created_at', '')),
            'full_text': tweet.get('full_text', ''),
            'name': tweet.get('name', ''),
            'screen_name': tweet.get('screen_name', ''),
            'user_id': user_id,
            'profile_image_url': self._get_full_profile_image_url(tweet.get('profile_image_url', '')),
            'views_count': tweet.get('views_count', 0),
            'favorite_count': tweet.get('favorite_count', 0),
            'retweet_count': tweet.get('retweet_count', 0),
            'bookmark_count': tweet.get('bookmark_count', 0),
            'url': tweet.get('url', ''),
            'photos': photos,
            'videos': videos,
            'media_count': len(photos) + len(videos),
            'media_paths': media_paths,
            'raw': json.dumps(tweet, ensure_ascii=False, indent=2)
        }
        
        # 添加引用推文信息
        if quoted_tweet:
            result['quoted_tweet'] = quoted_tweet
        
        return result
    
    def get_local_ip(self) -> str:
        """获取本机局域网 IP 地址"""
        try:
            # 获取所有网络接口的 IP 地址
            hostname = socket.gethostname()
            all_ips = socket.gethostbyname_ex(hostname)[2]
            
            # 过滤出有效的局域网 IP
            valid_ips = []
            for ip in all_ips:
                # 排除 localhost
                if ip.startswith('127.'):
                    continue
                # 排除代理软件常用的 IP 段（如 Clash/Meta 的 198.18.x.x）
                if ip.startswith('198.18.'):
                    continue
                # 排除 APIPA 地址（169.254.x.x）
                if ip.startswith('169.254.'):
                    continue
                valid_ips.append(ip)
            
            if not valid_ips:
                # 如果没有找到有效 IP，回退到原来的方法
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            
            # 优先选择常见的局域网 IP 段
            # 优先级：192.168.x.x > 10.x.x.x > 172.16-31.x.x > 其他
            for prefix in ['192.168.', '10.']:
                for ip in valid_ips:
                    if ip.startswith(prefix):
                        return ip
            
            # 检查 172.16.x.x - 172.31.x.x
            for ip in valid_ips:
                if ip.startswith('172.'):
                    parts = ip.split('.')
                    if len(parts) >= 2:
                        second_octet = int(parts[1])
                        if 16 <= second_octet <= 31:
                            return ip
            
            # 返回第一个有效 IP
            return valid_ips[0]
            
        except Exception:
            return '127.0.0.1'
    
    def run(self):
        """启动服务器"""
        global _http_server
        
        # 禁用 Flask 的日志输出
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        # 修复 Windows 上 socket.getfqdn() 导致的启动慢问题
        # werkzeug 的 make_server 内部会调用 getfqdn() 进行 DNS 反向解析，
        # 在某些 Windows 网络配置下会耗时 10+ 秒
        # 解决方案：用 gethostname() 替换 getfqdn()，避免 DNS 查询
        _original_getfqdn = socket.getfqdn
        socket.getfqdn = lambda name='': socket.gethostname()
        
        try:
            # 在启动 Flask 前，用另一个线程异步构建媒体缓存
            cache_thread = threading.Thread(target=self._build_media_cache, daemon=True)
            cache_thread.start()
            
            # 同时构建头像缓存
            profile_cache_thread = threading.Thread(target=self._build_profile_cache, daemon=True)
            profile_cache_thread.start()
            
            # 使用 make_server 创建可关闭的服务器
            _http_server = make_server(self.host, self.port, self.app, threaded=True)
        finally:
            # 恢复原始函数
            socket.getfqdn = _original_getfqdn
        
        _http_server.serve_forever()
    
    def shutdown(self):
        """关闭服务器"""
        global _http_server
        if _http_server:
            _http_server.shutdown()


def start_web_server(db: TweetDatabase, media_path: str, port: int = 5001, deleted_db: TweetDatabase = None, allow_delete: bool = False) -> tuple:
    """
    启动 Web 服务器
    
    Args:
        db: 数据库实例
        media_path: 媒体文件路径
        port: 监听端口
        deleted_db: 删除库实例，用于过滤已删除的推文
        allow_delete: 是否允许远程删除推文
        
    Returns:
        (成功, 错误信息或访问URL)
    """
    global _web_server, _server_thread, _is_running
    
    if _is_running:
        return False, "服务器已在运行"
    
    try:
        _web_server = WebServer(db, media_path, port=port, deleted_db=deleted_db, allow_delete=allow_delete)
        local_ip = _web_server.get_local_ip()
        
        _server_thread = threading.Thread(target=_web_server.run, daemon=True)
        _server_thread.start()
        _is_running = True
        
        return True, f"http://{local_ip}:{port}"
    except Exception as e:
        return False, str(e)


def stop_web_server():
    """停止 Web 服务器"""
    global _web_server, _server_thread, _http_server, _is_running, _cache_ready, _cache_building
    
    if not _is_running:
        return
    
    # 关闭 HTTP 服务器
    if _web_server:
        _web_server.shutdown()
        # 清理媒体缓存，确保下次启动时重新构建
        if hasattr(_web_server, '_media_cache'):
            _web_server._media_cache = None
    
    # 重置状态
    _is_running = False
    _web_server = None
    _server_thread = None
    _http_server = None
    _cache_ready = False
    _cache_building = False


def is_server_running() -> bool:
    """检查服务器是否在运行"""
    return _is_running


def get_server_url() -> str:
    """获取服务器访问 URL"""
    global _web_server
    if _web_server and _is_running:
        local_ip = _web_server.get_local_ip()
        return f"http://{local_ip}:{_web_server.port}"
    return ""


def set_allow_delete(allow: bool):
    """设置是否允许远程删除推文"""
    global _web_server, _is_running
    if _web_server and _is_running:
        _web_server.allow_delete = allow


def is_cache_ready() -> bool:
    """检查媒体缓存是否已构建完成"""
    return _cache_ready


def is_cache_building() -> bool:
    """检查媒体缓存是否正在构建"""
    return _cache_building
