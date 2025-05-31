
Уникализатор видео для Reels, TikTok, Shorts, Instagram, VK, Telegram и других соцсетей.

## Возможности
- Массовая обработка видео и GIF
- Поддержка drag-and-drop и работы с папками
- Выбор популярных форматов и размеров под соцсети (Reels, Shorts, Instagram, VK, Telegram, Facebook, Twitter, Snapchat, Pinterest)
- Фильтры: цвет, контраст, ч/б, сепия, инверсия, размытие, пикселизация и др.
- Наложение изображений и GIF
- Очистка метаданных
- Удаление звука
- Размытие фона для вертикальных форматов
- Современный UI с поддержкой тем (Light, Dark, Lolz)
- Логирование в файл и консоль

## Запуск
1. Установите Python 3.10+
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Скачайте [FFmpeg](https://ffmpeg.org/download.html) и поместите бинарники в `ffmpeg/bin/`
4. Запустите приложение:
   ```bash
   python main.py
   ```

## Структура проекта
- `main.py` — точка входа, логирование, запуск UI
- `ui/main_window.py` — основное окно, логика интерфейса
- `utils/constants.py` — константы, форматы, фильтры
- `workers/worker.py` — обработка видео в отдельном потоке
- `resources/` — стили, иконки, темы
- `ffmpeg/` — бинарники ffmpeg

## Форматы соцсетей
- Reels/TikTok: 1080x1920
- YouTube Shorts: 1080x1920
- Instagram Story: 1080x1920
- Instagram Post: 1080x1080
- Instagram Landscape: 1920x1080
- Instagram Portrait: 1080x1350
- VK Clip: 1080x1920
- Telegram Story: 1080x1920
- Telegram Post: 1280x720
- YouTube: 1920x1080
- Facebook Story: 1080x1920
- Facebook Post: 1200x630
- Twitter Post: 1600x900
- Twitter Portrait: 1080x1350
- Snapchat: 1080x1920
- Pinterest: 1000x1500

**Автор:** [0xd5f](https://github.com/0xd5f)
---
BTC: `bc1q20yn32a9ykkgcf7r8g23n7gwqzzfj9u932w4ww`