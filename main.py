# main.py
import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from ui.main_window import VideoUnicApp

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

if sys.platform.startswith('win'):
    try:
        os.system("chcp 65001")
        os.environ["PYTHONIOENCODING"] = "utf-8"
        logging.debug("Установлена кодировка консоли: 65001")
    except Exception as e:
        logging.warning(f"Не удалось установить кодировку консоли: {e}")

def main():
    logging.info("Запуск приложения...")
    app = QApplication(sys.argv)
    script_dir = os.path.dirname(os.path.realpath(__file__))
    resources_dir = os.path.join(script_dir, 'resources')
    ffmpeg_path_check = os.path.join(script_dir, 'ffmpeg', 'bin', 'ffmpeg.exe')

    if not os.path.isdir(resources_dir):
        logging.warning(f"Папка 'resources' не найдена по пути: {resources_dir}")

    if sys.platform.startswith('win') and not os.path.exists(ffmpeg_path_check):
        logging.error(f"ffmpeg.exe не найден по пути: {ffmpeg_path_check}")
        logging.error("Пожалуйста, скачайте FFmpeg и поместите его в папку 'ffmpeg/bin'.")

    try:
        w = VideoUnicApp()
        w.show()
        logging.info("Главное окно запущено")
        exit_code = app.exec_()
        logging.info(f"Приложение завершилось с кодом: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        logging.exception("Неперехваченная ошибка в основном цикле приложения:")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске приложения: {e}", exc_info=True)
        sys.exit(1)
