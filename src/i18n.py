# 国际化模块

# 当前语言
_current_lang = 'en'

# 翻译字典
_translations = {
    'en': {
        # ===== main.py =====
        # 主窗口
        'app_title': 'twegui v0.1.4',
        'starting_aria2': 'Starting aria2c...',
        'aria2_started': 'aria2c started',
        'aria2_failed': 'aria2c failed to start (download unavailable)',
        'import_json_btn': 'Import Tweets from JSON',
        'drop_json_hint': ', or drop a JSON file here',
        'view_database': 'View Database Records',
        'main_db_label': 'Main Database:',
        'deleted_db_label': 'Deleted DB:',
        'switch_btn': 'Switch...',
        'select_main_db_title': 'Select or create main database file',
        'select_deleted_db_title': 'Select or create deleted database file',
        'db_filter': 'Database Files (*.sqlite);;All Files (*.*)',
        'switch_success': 'Switch Successful',
        'switched_to_db': 'Switched to database: {path}',
        'create_success': 'Created Successfully',
        'created_db': 'Created and switched to new database: {path}',
        'drop_json_file': 'Please drop a JSON file',
        'reverse_insert_order': 'Reverse Insert',
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
        'delete_records_msg': 'You must know what you are doing!\n\nThis operation will search for records containing undownloaded media. If you have downloaded all downloadable media, the remaining ones are invalid tweets.\n\nYou can choose to completely delete records from the database or move them to another file: deleted.sqlite (Recommended, because doing so will automatically remove duplicates the next time you import JSON data.)\n\nThis is not a final decision. After selecting a processing method, we will collect all matching invalid records and wait for your confirmation again.',
        'permanently_delete': 'Permanently Delete Records',
        'move_to_deleted': 'Move to deleted.sqlite',
        'hint': 'Hint',
        'no_records_to_operate': 'No records need to be {operation}.',
        'operation_complete': 'Operation Complete',
        'records_deleted': '{count} records have been deleted',
        'records_moved': '{count} records have been moved to deleted.sqlite',
        
        # URL对话框
        'undownloaded_images_title': 'Undownloaded Image URLs ({count})',
        'undownloaded_videos_title': 'Undownloaded Video URLs ({count})',
        'download_all': 'Download All',
        'download_first_50': 'Download First 50',
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
        
        # 数据迁移
        'migrate_from_old_data': 'Migrate from Old Data (TinyDB → SQLite)',
        'migration_dialog_title': 'Migrate from Old Data (TinyDB → SQLite)',
        'migration_info': 'This feature can migrate TinyDB databases (JSON format) used in older versions\nto the new SQLite database for better performance.',
        'migration_source_group': 'Select TinyDB File to Migrate',
        'migration_no_files': 'No TinyDB files detected',
        'browse': 'Browse...',
        'migration_selected': 'Selected: {path}',
        'migration_target_group': 'Target SQLite Database',
        'migration_target_main': 'Main Database (main)',
        'migration_target_deleted': 'Deleted Database (deleted)',
        'migration_start': 'Start Migration',
        'close': 'Close',
        'migration_select_source': 'Select TinyDB Database File',
        'error': 'Error',
        'migration_no_source': 'Please select a TinyDB file to migrate',
        'migration_file_not_found': 'File does not exist: {path}',
        'migration_invalid_file': 'Selected file is not a valid TinyDB database file',
        'migration_in_progress': 'Migrating...',
        'migration_progress': 'Migrating... ({current}/{total})',
        'migration_failed': 'Migration failed, please check file format',
        'migration_error': 'Migration failed. Please ensure tinydb library is installed and file format is correct',
        'migration_complete': 'Migration Complete',
        'migration_complete_status': 'Migration complete! Success: {migrated}, Skipped: {skipped}, Errors: {errors}',
        'migration_result': 'Data migration completed!\n\nSuccessfully migrated: {migrated} records\nSkipped (already exists): {skipped} records\nErrors: {errors} records',
        'migration_detected_title': 'Old Data Detected',
        'migration_detected_msg': 'The following TinyDB format database files were detected:\n\n{files}\n\nThe new version uses SQLite database for better performance.\nWould you like to migrate the data now?',
        
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
        'failed_count': 'Failed: {count} task(s)',
        'failed_info': 'This may indicate that the tweet has expired/is invalid/was deleted by the author. You may need to retry or manually verify. If confirmed inaccessible, you can only use the "Delete Outdated Records" feature.',
        'retry_failed': 'Retry Failed Tasks',
        'no_failed_tasks': 'No failed tasks to retry',
        'retrying_tasks': 'Retrying {count} failed tasks...',
        'hide_completed': 'Hide Completed',
        'show_completed': 'Show Completed',
        
        # 更多菜单
        'more_menu': 'More',
        
        # aria2 设置
        'aria2_settings': 'Download Settings',
        'aria2_settings_title': 'Aria2 Download Settings',
        'aria2_max_concurrent': 'Max Concurrent Downloads:',
        'aria2_max_concurrent_hint': 'Number of downloads running at the same time (1-50)',
        'aria2_speed_limit': 'Global Speed Limit (MB/s):',
        'aria2_speed_limit_hint': '0 means unlimited',
        'aria2_conn_per_server': 'Connections Per Server:',
        'aria2_conn_per_server_hint': 'Connections per download task (1-16)',
        'aria2_split': 'File Split Count:',
        'aria2_split_hint': 'Split file into multiple parts for parallel download. Files smaller than 1MB will not be split.',
        'aria2_timeout': 'Timeout (seconds):',
        'aria2_timeout_hint': 'If no data is received for this duration, the connection is considered timed out and the download fails.',
        'aria2_save': 'Save',
        'aria2_saved': 'Settings saved and applied',
        
        # ===== webserver.py =====
        'web_server_btn': 'Start Local Web Server',
        'web_server_stop_btn': 'Stop Web Server',
        'web_server_status_off': 'Web Server: Stopped',
        'web_server_status_on': 'Web Server: Running',
        'web_server_starting': 'Starting...',
        'web_server_building_cache': 'Building media cache...',
        'web_server_timeout': 'Web server startup timeout (20s). Please check if the port is occupied.',
        'web_server_started': 'Web server started! Access URL:',
        'web_server_stopped': 'Web server stopped',
        'web_server_error': 'Failed to start web server: {error}',
        'web_server_port_label': 'Port:',
        'web_server_copy_url': 'Copy URL',
        'web_server_open_url': 'Open',
        'web_server_url_copied': 'URL copied to clipboard',
        'allow_remote_delete': 'Allow visitors to delete tweets remotely',
        'auto_start_web_server': 'Auto-start with program',
        'media_check_title': 'Media Status',
        'media_check_checking': 'Checking media library...',
        'media_check_has_undownloaded': 'Some media has not been downloaded. View database records to download.',
        'media_check_all_downloaded': 'All media downloaded',
        'media_check_refresh': 'Refresh',
        
        # ===== index.html (Web UI) =====
        'web_total_tweets': 'Total {count} tweets',
        'web_loading_tweets': 'Loading tweets...',
        'web_image': 'Image {index}',
        'web_video_not_supported': 'Your browser does not support video playback',
        'web_media_count': '{count} media',
        'web_delete': 'Delete',
        'web_no_tweets': 'No tweet data',
        'web_first_page': 'First Page',
        'web_prev_page': 'Previous',
        'web_next_page': 'Next',
        'web_last_page': 'Last Page',
        'web_jump_to': 'Jump to',
        'web_page': 'page',
        'web_delete_tweet': 'Delete Tweet',
        'web_delete_confirm': 'Are you sure you want to delete this tweet?',
        'web_delete_move': 'Move to deleted database (Recommended, will never appear again)',
        'web_delete_permanent': 'Permanently delete (May be re-inserted by JSON next time)',
        'web_cancel': 'Cancel',
        'web_just_now': 'Just now',
        'web_minutes_ago': '{mins} minutes ago',
        'web_hours_ago': '{hours} hours ago',
        'web_days_ago': '{days} days ago',
        'web_delete_failed': 'Delete failed: {error}',
        'web_unknown_error': 'Unknown error',
        'web_per_page': 'Per page',
        'web_tweets': 'tweets',
        'web_traveler_mode': 'Traveler Mode',
        'web_traveler_hint': '← Swipe left/right to select page →',
        'web_traveler_drag_cancel': '↓ Swipe here to cancel',
        'web_traveler_release_cancel': 'Release to cancel',
        'web_traveler_you_are_here': 'You are here',
        'web_powered_by': 'Powered by twitter-web-exporter-gui ♥',
        'web_menu_detail': 'Details',
        'web_detail_tweet_id': 'Tweet ID',
        'web_detail_media_paths': 'Media File Paths',
        'web_detail_no_media': 'No media files',
        'web_detail_favorites': 'Favorites',
        'web_detail_retweets': 'Retweets',
        'web_detail_bookmarks': 'Bookmarks',
        'web_close': 'Close',
        'web_delete_media_files': 'Also delete media files',
        'web_search': 'Search',
        'web_search_result': 'Search results: ',
        'web_search_items': ' items',
        'web_search_clear': 'Clear Search',
        'web_search_placeholder': 'Enter keywords...',
        'web_search_author_name': 'Author Name',
        'web_search_author_id': 'Author ID',
        'web_search_content': 'Tweet Text',
        'web_search_current': 'Current search: ',
        'web_search_filter': 'Filter',
        'web_filter_undownloaded_media': 'Has Undownloaded Media',
        'web_filter_mode': 'Filtering: Has Undownloaded Media',
        'web_locate_tweet': 'Locate Tweet',
        'web_locate_failed': 'Failed to locate tweet: {error}',
        
        # 引用推文相关
        'web_quoted_tweet': 'Quoted Tweet',
        'web_quoted_no_data': 'Quoted content unavailable',
        'web_quoted_nested': 'Has parent quote, click to view on X (Twitter)',
        'web_quoted_view_original': 'View original on Twitter',
        
        # 清除引用推文
        'web_clear_quote': 'Clear Quote Data',
        'web_clear_quote_title': 'Clear Quote Data',
        'web_clear_quote_confirm': 'Are you sure you want to clear the quote data of this tweet? This will remove the quoted tweet reference and convert it to a normal tweet. This action cannot be undone. \n\nThis feature is mainly used when the media in the quoted tweet has expired but you want to keep this tweet.',
        'web_clear_quote_success': 'Quote data cleared successfully',
        'web_clear_quote_failed': 'Failed to clear quote data: {error}',
        'web_confirm': 'Confirm',
        
        # 头像来源选项
        'web_avatar_source': 'Avatar Source',
        'web_avatar_source_local': 'Local',
        'web_avatar_source_twitter': 'Twitter CDN',
        'web_avatar_source_mixed': 'Mixed (Local first)',
        
        # 重置设置
        'web_reset_settings': 'Reset Settings',
        
        # 重载服务器
        'web_reload_server': 'Reload Web Server',
        # 'web_reload_success': 'Server reloaded successfully, refreshing page...',
        'web_reload_failed': 'Reload failed: {error}',
        'web_reloading': 'Reloading...',
        
        # 头像缓存管理
        'profile_cache_btn': 'Profile Image Cache',
        'profile_cache_title': 'Profile Image Cache Manager',
        'profile_cache_status': 'Status',
        'profile_cache_loading': 'Loading user data...',
        'profile_cache_dir': 'Save Directory: {path}',
        'profile_cache_stats': 'Total {total} users, {downloaded} cached, {pending} pending',
        'profile_cache_col_name': 'Name',
        'profile_cache_col_screen_name': 'Screen Name',
        'profile_cache_col_user_id': 'User ID',
        'profile_cache_col_status': 'Status',
        'profile_cache_method': 'Method:',
        'profile_cache_method_official': 'Official URL',
        'profile_cache_method_unavatar': 'unavatar.io',
        'profile_cache_update_all': 'Download All',
        'profile_cache_pending': 'Pending',
        'profile_cache_success': 'Success',
        'profile_cache_failed': 'Failed: {error}',
        'profile_cache_complete_title': 'Download Complete',
        'profile_cache_complete_msg': 'Downloaded {success} profile images, {failed} failed.',
        
        # 还原点功能
        'restore_point_group': 'Restore Point',
        'restore_point_auto_create': 'Auto create before import',
        'restore_point_create_btn': 'Create Restore Point',
        'restore_point_restore_btn': 'Restore from...',
        'restore_point_restore_btn_real': 'Restore',
        'restore_point_input_title': 'Create Restore Point',
        'restore_point_input_label': 'Restore point name:',
        'restore_point_default_name': '{date} Restore Point #{num}',
        'restore_point_date_format': '%B %d, %Y',
        'restore_point_success': 'Restore Point Created',
        'restore_point_success_msg': 'Restore point "{name}" has been created successfully.',
        'restore_point_failed': 'Failed to create restore point: {error}',
        'restore_point_list_title': 'Restore from Restore Point',
        'restore_point_col_name': 'Name',
        'restore_point_col_time': 'Created At',
        'restore_point_col_main_db': 'Main DB',
        'restore_point_col_deleted_db': 'Deleted DB',
        'restore_point_restore_confirm_title': 'Confirm Restore',
        'restore_point_restore_confirm_msg': 'Are you sure you want to restore from "{name}"?\n\nThis will overwrite your current databases. This action cannot be undone!',
        'restore_point_restore_success': 'Restore Complete',
        'restore_point_restore_success_msg': 'Databases have been restored from "{name}".',
        'restore_point_restore_failed': 'Restore failed: {error}',
        'restore_point_no_points': 'No restore points available.',
        'restore_point_invalid': 'Invalid restore point (missing manifest or database files)',
        'restore_point_delete_btn': 'Delete',
        'restore_point_delete_confirm_title': 'Delete Restore Point',
        'restore_point_delete_confirm_msg': 'Are you sure you want to delete restore point "{name}"?',
        'restore_point_delete_success': 'Restore point "{name}" has been deleted.',
        'restore_point_continue_import': 'Continue importing?',
        'restore_point_stop_server_first': 'Please stop the web server first.',
    },
    
    'zh-CN': {
        # ===== main.py =====
        # 主窗口
        'app_title': 'twegui v0.1.4',
        'starting_aria2': '正在启动 aria2c...',
        'aria2_started': 'aria2c 已启动',
        'aria2_failed': 'aria2c 启动失败（下载功能不可用）',
        'import_json_btn': '从 JSON 文件导入推文',
        'drop_json_hint': '，或拖放一个 JSON 文件到窗口',
        'view_database': '查看数据库记录',
        'main_db_label': '主数据库:',
        'deleted_db_label': '删除库:',
        'switch_btn': '切换...',
        'select_main_db_title': '选择或创建主数据库文件',
        'select_deleted_db_title': '选择或创建删除数据库文件',
        'db_filter': '数据库文件 (*.sqlite);;所有文件 (*.*)',
        'switch_success': '切换成功',
        'switched_to_db': '已切换到数据库: {path}',
        'create_success': '创建成功',
        'created_db': '已创建并切换到新数据库: {path}',
        'drop_json_file': '请拖放一个 JSON 文件',
        'reverse_insert_order': '插入时反转顺序',
        'processing_json': '正在处理 JSON 文件...',
        'json_error': 'JSON 文件内容格式错误或读取失败',
        'process_complete': '处理完成，新添加了 {count} 条记录',
        
        # 数据库查看器
        'database_records': '数据库记录',
        'table_hint': '所有数据可双击复制，但更改不会保存。',
        'col_id': 'ID',
        'col_created_at': '发布时间',
        'col_full_text': '正文内容',
        'col_author': '作者',
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
        'delete_records_msg': '你必须要知道你在做什么！\n\n此操作会检索包含未下载媒体的记录。如果你已经下载所有可被下载的媒体，那么剩下的就是失效的推文。\n\n你可以选择从库中彻底删除记录，或将它们移到另一个文件中：deleted.sqlite (推荐，因为这样做会让下次导入 JSON 时自动去重)\n\n这不是最终决定。在选择处理方式后，我们会收集所有符合条件的失效记录，然后等待你的再次确认。',
        'permanently_delete': '彻底删除记录',
        'move_to_deleted': '移动到 deleted.sqlite',
        'hint': '提示',
        'no_records_to_operate': '没有需要{operation}的记录。',
        'operation_complete': '操作完成',
        'records_deleted': '{count} 条记录已删除',
        'records_moved': '{count} 条记录已移动到 deleted.sqlite',
        
        # URL对话框
        'undownloaded_images_title': '未下载图片URL ({count})',
        'undownloaded_videos_title': '未下载视频URL ({count})',
        'download_all': '全部下载',
        'download_first_50': '下载前 50 条',
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
        
        # 数据迁移
        'migrate_from_old_data': '从旧数据迁移 (TinyDB → SQLite)',
        'migration_dialog_title': '从旧数据迁移 (TinyDB → SQLite)',
        'migration_info': '此功能可以将旧版本使用的 TinyDB 数据库（JSON 格式）\n迁移到新的 SQLite 数据库，以获得更好的性能。',
        'migration_source_group': '选择要迁移的 TinyDB 文件',
        'migration_no_files': '未检测到 TinyDB 文件',
        'browse': '浏览...',
        'migration_selected': '已选择: {path}',
        'migration_target_group': '目标 SQLite 数据库',
        'migration_target_main': '主数据库 (main)',
        'migration_target_deleted': '删除库 (deleted)',
        'migration_start': '开始迁移',
        'close': '关闭',
        'migration_select_source': '选择 TinyDB 数据库文件',
        'error': '错误',
        'migration_no_source': '请选择要迁移的 TinyDB 文件',
        'migration_file_not_found': '文件不存在: {path}',
        'migration_invalid_file': '所选文件不是有效的 TinyDB 数据库文件',
        'migration_in_progress': '正在迁移...',
        'migration_progress': '正在迁移... ({current}/{total})',
        'migration_failed': '迁移失败，请检查文件格式',
        'migration_error': '迁移失败。请确保已安装 tinydb 库并且文件格式正确',
        'migration_complete': '迁移完成',
        'migration_complete_status': '迁移完成！成功: {migrated}, 跳过: {skipped}, 错误: {errors}',
        'migration_result': '数据迁移已完成！\n\n成功迁移: {migrated} 条记录\n跳过（已存在）: {skipped} 条记录\n错误: {errors} 条记录',
        'migration_detected_title': '检测到旧数据',
        'migration_detected_msg': '检测到以下 TinyDB 格式的数据库文件:\n\n{files}\n\n新版本使用 SQLite 数据库以提升性能。\n是否现在迁移数据？',
        
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
        'failed_count': '失败: {count} 个任务',
        'failed_info': '这可能意味着推文过期/失效/被作者删除。您可能需要重试或人工确认，如果确认无法访问，只能使用「删除过期记录」功能。',
        'retry_failed': '重试失败任务',
        'no_failed_tasks': '没有需要重试的失败任务',
        'retrying_tasks': '正在重试 {count} 个失败任务...',
        'hide_completed': '隐藏已完成',
        'show_completed': '显示已完成',
        
        # 更多菜单
        'more_menu': '更多',
        
        # aria2 设置
        'aria2_settings': '下载设置',
        'aria2_settings_title': 'Aria2 下载设置',
        'aria2_max_concurrent': '最大并发下载数:',
        'aria2_max_concurrent_hint': '同时下载的任务数量 (1-50)',
        'aria2_speed_limit': '全局速度限制 (MB/s):',
        'aria2_speed_limit_hint': '0 表示不限速',
        'aria2_conn_per_server': '每服务器连接数:',
        'aria2_conn_per_server_hint': '每个下载任务的连接数 (1-16)',
        'aria2_split': '文件分片数:',
        'aria2_split_hint': '将文件分成多个部分并行下载。小于1MB的文件不会被分片。',
        'aria2_timeout': '超时时间 (秒):',
        'aria2_timeout_hint': '若在该时间内没有收到任何数据，则视为超时，下载失败。',
        'aria2_save': '保存',
        'aria2_saved': '设置已保存并应用',
        
        # ===== webserver.py =====
        'web_server_btn': '启动本地 Web 服务器',
        'web_server_stop_btn': '停止 Web 服务器',
        'web_server_status_off': 'Web 服务器: 已停止',
        'web_server_status_on': 'Web 服务器: 运行中',
        'web_server_starting': '正在启动...',
        'web_server_building_cache': '正在构建媒体缓存...',
        'web_server_timeout': 'Web 服务器启动超时（20秒）。请检查端口是否被占用。',
        'web_server_started': 'Web 服务器已启动！访问地址:',
        'web_server_stopped': 'Web 服务器已停止',
        'web_server_error': '启动 Web 服务器失败: {error}',
        'web_server_port_label': '端口:',
        'web_server_copy_url': '复制链接',
        'web_server_open_url': '打开',
        'web_server_url_copied': '链接已复制到剪贴板',
        'allow_remote_delete': '允许访问者远程删除推文',
        'auto_start_web_server': '随程序自动启动',
        'media_check_title': '媒体状态',
        'media_check_checking': '检查媒体库中...',
        'media_check_has_undownloaded': '库中有未下载的媒体，建议查看数据库记录并下载',
        'media_check_all_downloaded': '所有媒体已下载',
        'media_check_refresh': '刷新',
        
        # ===== index.html (Web UI) =====
        'web_total_tweets': '共 {count} 条推文',
        'web_loading_tweets': '正在加载推文...',
        'web_image': '图片 {index}',
        'web_video_not_supported': '您的浏览器不支持视频播放',
        'web_media_count': '{count} 个媒体',
        'web_delete': '删除',
        'web_no_tweets': '暂无推文数据',
        'web_first_page': '第一页',
        'web_prev_page': '上一页',
        'web_next_page': '下一页',
        'web_last_page': '最后一页',
        'web_jump_to': '跳转到',
        'web_page': '页',
        'web_delete_tweet': '删除推文',
        'web_delete_confirm': '确定要删除这条推文吗？',
        'web_delete_move': '移动到删除库（推荐，永远不会再出现）',
        'web_delete_permanent': '彻底删除（下次可能又被JSON插入）',
        'web_cancel': '取消',
        'web_just_now': '刚刚',
        'web_minutes_ago': '{mins}分钟前',
        'web_hours_ago': '{hours}小时前',
        'web_days_ago': '{days}天前',
        'web_delete_failed': '删除失败: {error}',
        'web_unknown_error': '未知错误',
        'web_per_page': '每页显示',
        'web_tweets': '条推文',
        'web_traveler_mode': '穿越模式',
        'web_traveler_hint': '← 左右滑动选择页面 →',
        'web_traveler_drag_cancel': '↓ 滑动到此处取消',
        'web_traveler_release_cancel': '松开取消',
        'web_traveler_you_are_here': '你在这里',
        'web_powered_by': '由 twitter-web-exporter-gui 驱动 ♥',
        'web_menu_detail': '详细信息',
        'web_detail_tweet_id': '推特 ID',
        'web_detail_media_paths': '媒体文件路径',
        'web_detail_no_media': '无媒体文件',
        'web_detail_favorites': '点赞数',
        'web_detail_retweets': '转推数',
        'web_detail_bookmarks': '书签数',
        'web_close': '关闭',
        'web_delete_media_files': '删除对应的媒体文件',
        'web_search': '搜索',
        'web_search_result': '搜索结果：',
        'web_search_items': ' 条',
        'web_search_clear': '清除搜索',
        'web_search_placeholder': '输入关键词...',
        'web_search_author_name': '作者昵称',
        'web_search_author_id': '作者ID',
        'web_search_content': '正文',
        'web_search_current': '当前搜索：',
        'web_search_filter': '筛选',
        'web_filter_undownloaded_media': '包含未下载的媒体',
        'web_filter_mode': '筛选中：包含未下载的媒体',
        'web_locate_tweet': '定位到推文',
        'web_locate_failed': '定位推文失败: {error}',
        
        # 引用推文相关
        'web_quoted_tweet': '引用推文',
        'web_quoted_no_data': '引用内容不可用',
        'web_quoted_nested': '包含上级引用，无法预览，点击访问 X (Twitter) 查看',
        'web_quoted_view_original': '在 Twitter 查看原文',
        
        # 清除转推数据
        'web_clear_quote': '清除转推数据',
        'web_clear_quote_title': '清除转推数据',
        'web_clear_quote_confirm': '确定要清除这条推文的转推数据吗？这将移除转推的关联，使其变为普通推文。此操作无法撤销。\n\n此功能主要用于转推中的媒体已失效但您想保留本条推文的情况。',
        'web_clear_quote_success': '转推数据已清除',
        'web_clear_quote_failed': '清除转推数据失败: {error}',
        'web_confirm': '确认',
        
        # 头像来源选项
        'web_avatar_source': '头像来源',
        'web_avatar_source_local': '本地',
        'web_avatar_source_twitter': 'Twitter CDN',
        'web_avatar_source_mixed': '混合（优先本地）',
        
        # 重置设置
        'web_reset_settings': '重置设置',
        
        # 重载服务器
        'web_reload_server': '重载 Web 服务器',
        # 'web_reload_success': '服务器已重载，正在刷新页面...',
        'web_reload_failed': '重载失败: {error}',
        'web_reloading': '正在重载...',
        
        # 头像缓存管理
        'profile_cache_btn': '头像缓存管理',
        'profile_cache_title': '头像缓存管理',
        'profile_cache_status': '状态',
        'profile_cache_loading': '正在加载用户数据...',
        'profile_cache_dir': '保存目录: {path}',
        'profile_cache_stats': '共 {total} 个用户，已缓存 {downloaded} 个，待下载 {pending} 个',
        'profile_cache_col_name': '昵称',
        'profile_cache_col_screen_name': 'Screen Name',
        'profile_cache_col_user_id': '用户 ID',
        'profile_cache_col_status': '状态',
        'profile_cache_method': '获取方案:',
        'profile_cache_method_official': '官方-记录中的url',
        'profile_cache_method_unavatar': 'unavatar',
        'profile_cache_update_all': '全部下载',
        'profile_cache_pending': '待下载',
        'profile_cache_success': '成功',
        'profile_cache_failed': '失败: {error}',
        'profile_cache_complete_title': '下载完成',
        'profile_cache_complete_msg': '成功下载 {success} 个头像，失败 {failed} 个。',
        
        # 还原点功能
        'restore_point_group': '还原点',
        'restore_point_auto_create': '插入前自动创建还原点',
        'restore_point_create_btn': '创建还原点',
        'restore_point_restore_btn': '从还原点还原...',
        'restore_point_restore_btn_real': '还原',
        'restore_point_input_title': '创建还原点',
        'restore_point_input_label': '还原点名称:',
        'restore_point_default_name': '{date}第{num}次还原点',
        'restore_point_date_format': '%Y年%m月%d日',
        'restore_point_success': '创建成功',
        'restore_point_success_msg': '还原点 "{name}" 已成功创建。',
        'restore_point_failed': '创建还原点失败: {error}',
        'restore_point_list_title': '从还原点还原',
        'restore_point_col_name': '名称',
        'restore_point_col_time': '创建时间',
        'restore_point_col_main_db': '主数据库',
        'restore_point_col_deleted_db': '删除库',
        'restore_point_restore_confirm_title': '确认还原',
        'restore_point_restore_confirm_msg': '确定要从 "{name}" 还原吗？\n\n这将覆盖您当前的数据库，此操作无法撤销！',
        'restore_point_restore_success': '还原完成',
        'restore_point_restore_success_msg': '数据库已从 "{name}" 还原。',
        'restore_point_restore_failed': '还原失败: {error}',
        'restore_point_no_points': '暂无可用的还原点。',
        'restore_point_invalid': '无效的还原点（缺少清单文件或数据库文件）',
        'restore_point_delete_btn': '删除',
        'restore_point_delete_confirm_title': '删除还原点',
        'restore_point_delete_confirm_msg': '确定要删除还原点 "{name}" 吗？',
        'restore_point_delete_success': '还原点 "{name}" 已删除。',
        'restore_point_continue_import': '是否继续导入？',
        'restore_point_stop_server_first': '请先停止 Web 服务器。',
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


def get_translations(lang=None):
    """获取指定语言的完整翻译字典
    
    Args:
        lang: 语言代码，如果为 None 则返回当前语言的翻译
    
    Returns:
        翻译字典
    """
    if lang is None:
        lang = _current_lang
    return _translations.get(lang, {})
