import os
import sys

# 将项目根目录添加到 Python 路径，支持 src.xxx 的导入方式
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import QApplication

from downloader import load_config
from i18n import set_language
from src.utils.MainWindow import MainWindow

# 全局配置
config = load_config()

# 初始化语言设置
set_language(config.get('general', 'language'))


if __name__ == "__main__":
	app = QApplication(sys.argv)
	app.setFont(QFont("Cascadia Mono, Microsoft YaHei", 8))

	# 从文件路径加载图标（兼容开发环境和 PyInstaller 打包后环境）
	if getattr(sys, 'frozen', False):
		# PyInstaller 打包后的环境，资源在 _MEIPASS 目录下
		base_path = sys._MEIPASS
	else:
		# 开发环境，获取项目根目录
		base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	
	ico_path = os.path.join(base_path, 'app.ico')
	if os.path.exists(ico_path):
		app_icon = QIcon(ico_path)
		app.setWindowIcon(app_icon)  # 设置为全局图标

	window = MainWindow()
	window.show()
	sys.exit(app.exec())
