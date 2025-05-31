# utils/file_utils.py
import os
import mimetypes
import logging
from typing import List
from .constants import VIDEO_EXTENSIONS, GIF_EXTENSIONS, VALID_INPUT_EXTENSIONS

mimetypes.init()


def is_video_file(path: str) -> bool:
    """Проверяет, является ли файл видео по расширению или MIME-типу."""
    if not os.path.isfile(path):
        logging.debug(f"Файл не найден: {path}")
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        logging.debug(f"Файл {path} определён как видео по расширению")
        return True
    try:
        mime_type, _ = mimetypes.guess_type(path)
        result = mime_type is not None and mime_type.startswith("video")
        logging.debug(f"Проверка MIME для {path}: {mime_type}, результат: {result}")
        return result
    except Exception as e:
        logging.warning(f"Не удалось определить MIME-тип для {path}: {e}")
        return False


def is_gif_file(path: str) -> bool:
    """Проверяет, является ли файл GIF по расширению."""
    if not os.path.isfile(path):
        logging.debug(f"Файл не найден: {path}")
        return False
    ext = os.path.splitext(path)[1].lower()
    result = ext in GIF_EXTENSIONS
    logging.debug(f"Проверка GIF для {path}: расширение {ext}, результат: {result}")
    return result


def find_videos_in_folder(folder: str, include_gifs: bool = False) -> List[str]:
    """Находит видео (и опционально GIF) файлы в папке и подпапках."""
    found = []
    valid_extensions = VIDEO_EXTENSIONS
    if include_gifs:
        valid_extensions = valid_extensions.union(GIF_EXTENSIONS)

    if not os.path.isdir(folder):
        logging.error(f"Папка не найдена: {folder}")
        return found

    try:
        for root, dirs, files in os.walk(folder):
            for name in files:
                fp = os.path.join(root, name)
                ext = os.path.splitext(name)[1].lower()
                if ext in valid_extensions:
                    try:
                        if os.access(fp, os.R_OK):
                            found.append(fp)
                            logging.debug(f"Найден видеофайл: {fp}")
                        else:
                            logging.warning(f"Нет доступа для чтения файла: {fp}")
                    except Exception as e:
                        logging.warning(f"Не удалось получить доступ к файлу {fp}: {e}")
    except Exception as e:
        logging.error(f"Ошибка при обходе папки {folder}: {e}")

    logging.info(f"Найдено {len(found)} видеофайлов в папке {folder}")
    return found
