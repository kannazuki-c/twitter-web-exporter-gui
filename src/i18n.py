# 国际化模块

# 当前语言
_current_lang = 'en'

# 翻译字典
_translations = {
    'en': {
        # ===== main.py =====
        # 主窗口
        'app_title': 'twegui v0.1.2',
        'starting_aria2': 'Starting aria2c...',
        'aria2_started': 'aria2c started',
        'aria2_failed': 'aria2c failed to start (download unavailable)',
        'drop_json_hint': 'Drop a JSON file here',
        'view_database': 'View Database Records',
        'main_db_label': 'Main Database:',
        'deleted_db_label': 'Deleted DB:',
        'switch_btn': 'Switch...',
        'select_main_db_title': 'Select or create main database file',
        'select_deleted_db_title': 'Select or create deleted database file',
        'db_filter': 'Database Files (*.db);;All Files (*.*)',
        'switch_success': 'Switch Successful',
        'switched_to_db': 'Switched to database: {path}',
        'create_success': 'Created Successfully',
        'created_db': 'Created and switched to new database: {path}',
        'drop_json_file': 'Please drop a JSON file',
        'processing_json': 'Processing JSON file...',
        'json_error': 'JSON file format error or read failed',
        'process_complete': 'Processing complete, added {count} new records',
        
        # 数据库查看器
        'database_records': 'Database Records',
        'table_hint': 'All data can be copied by double-clicking, but changes will not be saved.',
        'col_id': 'ID',
        'col_created_at': 'Created At',
        'col_full_text': 'Full Text',
        'col_author': 'Author',
        'col_views': 'Views',
        'col_url': 'URL',
        'col_downloaded': 'Downloaded',
        'col_actions': 'Actions',
        'refresh': 'Refresh',
        'check_undownloaded_images': 'Check Undownloaded Images',
        'check_undownloaded_videos': 'Check Undownloaded Videos',
        'delete_outdated_records': 'Delete Outdated Records',
        'exact_match': 'Exact Match (local media filename)',
        'media_scan_path': 'Media Scan Path:',
        
        # 删除记录对话框
        'confirm_operation': 'Confirm {operation} Records',
        'records_to_operate': 'The following records will be {operation}, please confirm:',
        'confirm_btn': 'Confirm {operation}',
        'cancel': 'Cancel',
        'operation_delete': 'delete',
        'operation_move': 'move',
        
        # 操作进度
        'operation_in_progress': 'Operation In Progress',
        'please_wait': 'Please wait, executing operation...',
        
        # 删除不需要的记录
        'delete_records_title': 'Delete Outdated Records',
        'delete_records_msg': 'You must know what you are doing!\n\nThis operation will search for records containing undownloaded media. If you have downloaded all downloadable media, the remaining ones are invalid tweets or tweets you consider unnecessary.\n\nYou can choose to completely delete records from the database or move them to another file: deleted.db\n\nThis is not a final decision. After selecting a processing method, we will collect all matching invalid records and wait for your confirmation again.',
        'permanently_delete': 'Permanently Delete Records',
        'move_to_deleted': 'Move to deleted.db',
        'hint': 'Hint',
        'no_records_to_operate': 'No records need to be {operation}.',
        'operation_complete': 'Operation Complete',
        'records_deleted': '{count} records have been deleted',
        'records_moved': '{count} records have been moved to deleted.db',
        
        # URL对话框
        'undownloaded_images_title': 'Undownloaded Image URLs ({count})',
        'undownloaded_videos_title': 'Undownloaded Video URLs ({count})',
        'download_all': 'Download All',
        'download_first_100': 'Download First 100',
        'download': 'Download',
        
        # 表格内容
        'no_media': 'No Media',
        'yes': 'Yes',
        'not_downloaded': 'Not Downloaded',
        'images_count': '{count} images',
        'videos_count': '{count} videos',
        'view': 'View',
        'delete': 'Delete',
        
        # 统计信息
        'archived_stats': 'Archived {tweets} tweets. Scanned {photos} images and {videos} videos.',
        'all_downloaded': 'All tweet media downloaded!',
        'tweets_need_download': '{count} tweets contain undownloaded media.',
        'invalid_tweets': 'Contains {count} invalid tweets.',
        'regex_failed': 'Regex match failed for {count} items.',
        
        # 其他
        'please_wait_title': 'Please Wait',
        'loading_data': 'Loading data...',
        'view_record': 'View Record',
        'delete_confirm_title': 'Delete Confirmation',
        'delete_confirm_msg': 'Are you sure you want to delete this record?',
        
        # 语言设置
        'language': 'Language:',
        
        # ===== downloader.py =====
        'download_manager_title': 'Download Manager (Aria2)',
        'preparing_download': 'Preparing download...',
        'tasks_added': '{count} tasks have been added. Current batch: G{batch}',
        'col_url_download': 'URL',
        'col_progress': 'Progress',
        'col_status': 'Status',
        'waiting': 'Waiting',
        'start_download': 'Start Download',
        'batch_label': 'Batch:',
        'adding_tasks': 'Adding download tasks...',
        'aria2_not_started': 'aria2c not started!',
        'added_to_queue': 'Added to queue',
        'add_failed': 'Add failed',
        'downloading_progress': 'Downloading... ({completed}/{total})',
        'downloading_speed': 'Downloading ({speed:.2f} MB/s)',
        'completed': 'Completed',
        'download_failed': 'Download failed: {error}',
        'task_cancelled': 'Task cancelled',
        'all_downloads_complete': 'All downloads complete! ({completed}/{total})',
    },
    
    'zh-CN': {
        # ===== main.py =====
        # 主窗口
        'app_title': 'twegui v0.1.2',
        'starting_aria2': '正在启动 aria2c...',
        'aria2_started': 'aria2c 已启动',
        'aria2_failed': 'aria2c 启动失败（下载功能不可用）',
        'drop_json_hint': '拖放一个 JSON 文件到窗口',
        'view_database': '查看数据库记录',
        'main_db_label': '主数据库:',
        'deleted_db_label': '删除库:',
        'switch_btn': '切换...',
        'select_main_db_title': '选择或创建主数据库文件',
        'select_deleted_db_title': '选择或创建删除数据库文件',
        'db_filter': '数据库文件 (*.db);;所有文件 (*.*)',
        'switch_success': '切换成功',
        'switched_to_db': '已切换到数据库: {path}',
        'create_success': '创建成功',
        'created_db': '已创建并切换到新数据库: {path}',
        'drop_json_file': '请拖放一个 JSON 文件',
        'processing_json': '正在处理 JSON 文件...',
        'json_error': 'JSON 文件内容格式错误或读取失败',
        'process_complete': '处理完成，新添加了 {count} 条记录',
        
        # 数据库查看器
        'database_records': '数据库记录',
        'table_hint': '所有数据可双击复制，但更改不会保存。',
        'col_id': 'ID',
        'col_created_at': 'Created At',
        'col_full_text': 'Full Text',
        'col_author': 'Author',
        'col_views': '浏览量',
        'col_url': 'URL',
        'col_downloaded': '已下载',
        'col_actions': '操作',
        'refresh': '刷新',
        'check_undownloaded_images': '检查未下载的图片',
        'check_undownloaded_videos': '检查未下载的视频',
        'delete_outdated_records': '删除不需要的记录',
        'exact_match': '精准匹配(本地媒体文件名)',
        'media_scan_path': '媒体扫描路径:',
        
        # 删除记录对话框
        'confirm_operation': '确认{operation}记录',
        'records_to_operate': '以下记录将被{operation}，请确认：',
        'confirm_btn': '确认{operation}',
        'cancel': '取消',
        'operation_delete': '删除',
        'operation_move': '移动',
        
        # 操作进度
        'operation_in_progress': '操作进行中',
        'please_wait': '请稍候，正在执行操作...',
        
        # 删除不需要的记录
        'delete_records_title': '删除不需要的记录',
        'delete_records_msg': '你必须要知道你在做什么！\n\n此操作会检索包含未下载媒体的记录。如果你已经下载所有可被下载的媒体，那么剩下的就是失效的推文或你认为不需要的推文。\n\n你可以选择从库中彻底删除记录，或将它们移到另一个文件中：deleted.db\n\n这不是最终决定。在选择处理方式后，我们会收集所有符合条件的失效记录，然后等待你的再次确认。',
        'permanently_delete': '彻底删除记录',
        'move_to_deleted': '移动到 deleted.db',
        'hint': '提示',
        'no_records_to_operate': '没有需要{operation}的记录。',
        'operation_complete': '操作完成',
        'records_deleted': '{count} 条记录已删除',
        'records_moved': '{count} 条记录已移动到 deleted.db',
        
        # URL对话框
        'undownloaded_images_title': '未下载图片URL ({count})',
        'undownloaded_videos_title': '未下载视频URL ({count})',
        'download_all': '全部下载',
        'download_first_100': '下载前 100 条',
        'download': '下载',
        
        # 表格内容
        'no_media': '无媒体',
        'yes': '是',
        'not_downloaded': '未下载',
        'images_count': '图片{count}张',
        'videos_count': '视频{count}条',
        'view': '查看',
        'delete': '删除',
        
        # 统计信息
        'archived_stats': '已归档{tweets}条推文。扫描到{photos}张图片和{videos}条视频。',
        'all_downloaded': '所有推文媒体均已下载！',
        'tweets_need_download': '{count}条推文包含未下载的媒体。',
        'invalid_tweets': '包含{count}条失效推文。',
        'regex_failed': '正则匹配失败{count}条。',
        
        # 其他
        'please_wait_title': '请稍候',
        'loading_data': '正在加载数据...',
        'view_record': '查看记录',
        'delete_confirm_title': '删除确认',
        'delete_confirm_msg': '确定要删除该记录吗？',
        
        # 语言设置
        'language': '语言:',
        
        # ===== downloader.py =====
        'download_manager_title': '下载管理器 (Aria2)',
        'preparing_download': '准备下载...',
        'tasks_added': '{count} 个任务已被添加。当前批号: G{batch}',
        'col_url_download': 'URL',
        'col_progress': '进度',
        'col_status': '状态',
        'waiting': '等待中',
        'start_download': '开始下载',
        'batch_label': '批号:',
        'adding_tasks': '正在添加下载任务...',
        'aria2_not_started': 'aria2c 未启动！',
        'added_to_queue': '已添加到队列',
        'add_failed': '添加失败',
        'downloading_progress': '下载中... ({completed}/{total})',
        'downloading_speed': '下载中 ({speed:.2f} MB/s)',
        'completed': '已完成',
        'download_failed': '下载失败: {error}',
        'task_cancelled': '任务已取消',
        'all_downloads_complete': '所有下载完成！({completed}/{total})',
    }
}


def set_language(lang):
    """设置当前语言"""
    global _current_lang
    if lang in _translations:
        _current_lang = lang


def get_language():
    """获取当前语言"""
    return _current_lang


def t(key, **kwargs):
    """获取翻译文本
    
    Args:
        key: 翻译键
        **kwargs: 格式化参数
    
    Returns:
        翻译后的文本
    """
    text = _translations.get(_current_lang, {}).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text


def get_available_languages():
    """获取可用的语言列表"""
    return {
        'en': 'English',
        'zh-CN': '简体中文'
    }
