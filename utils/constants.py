# utils/constants.py
import os

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FFMPEG_PATH = os.path.join(_base_dir, "ffmpeg", "bin", "ffmpeg.exe")
DEFAULT_OUTPUT_DIR = os.path.join(_base_dir, "output")
RESOURCES_DIR = os.path.join(_base_dir, "resources")

REELS_WIDTH = 1080
REELS_HEIGHT = 1920
REELS_FORMAT_NAME = f"Reels/TikTok ({REELS_WIDTH}x{REELS_HEIGHT})"

YouTube_WIDTH = 1080
YouTube_HEIGHT = 1920
YouTube_FORMAT_NAME = f"YouTube Shorts ({YouTube_WIDTH}x{YouTube_HEIGHT})"

Instagram_WIDTH = 1080
Instagram_HEIGHT = 1920
Instagram_FORMAT_NAME = f"Instagram Story ({Instagram_WIDTH}x{Instagram_HEIGHT})"

InstagramPost_WIDTH = 1080
InstagramPost_HEIGHT = 1080
InstagramPost_FORMAT_NAME = f"Instagram Post ({InstagramPost_WIDTH}x{InstagramPost_HEIGHT})"

InstagramLandscape_WIDTH = 1920
InstagramLandscape_HEIGHT = 1080
InstagramLandscape_FORMAT_NAME = f"Instagram Landscape ({InstagramLandscape_WIDTH}x{InstagramLandscape_HEIGHT})"

InstagramPortrait_WIDTH = 1080
InstagramPortrait_HEIGHT = 1350
InstagramPortrait_FORMAT_NAME = f"Instagram Portrait ({InstagramPortrait_WIDTH}x{InstagramPortrait_HEIGHT})"

VKClip_WIDTH = 1080
VKClip_HEIGHT = 1920
VKClip_FORMAT_NAME = f"VK Clip ({VKClip_WIDTH}x{VKClip_HEIGHT})"

TelegramStory_WIDTH = 1080
TelegramStory_HEIGHT = 1920
TelegramStory_FORMAT_NAME = f"Telegram Story ({TelegramStory_WIDTH}x{TelegramStory_HEIGHT})"

TelegramPost_WIDTH = 1280
TelegramPost_HEIGHT = 720
TelegramPost_FORMAT_NAME = f"Telegram Post ({TelegramPost_WIDTH}x{TelegramPost_HEIGHT})"

YouTubeNormal_WIDTH = 1920
YouTubeNormal_HEIGHT = 1080
YouTubeNormal_FORMAT_NAME = f"YouTube ({YouTubeNormal_WIDTH}x{YouTubeNormal_HEIGHT})"

YouTubeVertical_WIDTH = 1080
YouTubeVertical_HEIGHT = 1920
YouTubeVertical_FORMAT_NAME = f"YouTube Vertical ({YouTubeVertical_WIDTH}x{YouTubeVertical_HEIGHT})"

FacebookStory_WIDTH = 1080
FacebookStory_HEIGHT = 1920
FacebookStory_FORMAT_NAME = f"Facebook Story ({FacebookStory_WIDTH}x{FacebookStory_HEIGHT})"

FacebookPost_WIDTH = 1200
FacebookPost_HEIGHT = 630
FacebookPost_FORMAT_NAME = f"Facebook Post ({FacebookPost_WIDTH}x{FacebookPost_HEIGHT})"

TwitterPost_WIDTH = 1600
TwitterPost_HEIGHT = 900
TwitterPost_FORMAT_NAME = f"Twitter Post ({TwitterPost_WIDTH}x{TwitterPost_HEIGHT})"

TwitterPortrait_WIDTH = 1080
TwitterPortrait_HEIGHT = 1350
TwitterPortrait_FORMAT_NAME = f"Twitter Portrait ({TwitterPortrait_WIDTH}x{TwitterPortrait_HEIGHT})"

Snapchat_WIDTH = 1080
Snapchat_HEIGHT = 1920
Snapchat_FORMAT_NAME = f"Snapchat ({Snapchat_WIDTH}x{Snapchat_HEIGHT})"

Pinterest_WIDTH = 1000
Pinterest_HEIGHT = 1500
Pinterest_FORMAT_NAME = f"Pinterest ({Pinterest_WIDTH}x{Pinterest_HEIGHT})"

OUTPUT_FORMATS = [
    "Оригинальный",
    REELS_FORMAT_NAME,
]

FILTERS = {
    "Нет фильтра": "",
    "Случ. цвет (яркость/контраст/...)": "eq=brightness={br}:contrast={ct}:saturation={sat},hue=h={hue}",
    "Черно-белое": "hue=s=0",
    "Сепия": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131:0",
    "Инверсия": "negate",
    "Размытие (легкое)": "gblur=sigma=2",
    "Размытие (сильное)": "gblur=sigma=10",
    "Отразить по горизонтали": "hflip",
    "Отразить по вертикали": "vflip",
    "Пикселизация": "scale=iw/10:ih/10,scale=iw*10:ih*10:flags=neighbor",
    "VHS (шум, сдвиг)": "chromashift=1:1,noise=alls=20:allf=t+u",
    "Повыш. контрастность": "eq=contrast=1.5",
    "Пониж. контрастность": "eq=contrast=0.7",
    "Повыш. насыщенность": "eq=saturation=1.5",
    "Пониж. насыщенность": "eq=saturation=0.5",
    "Повыш. яркость": "eq=brightness=0.15",
    "Пониж. яркость": "eq=brightness=-0.15",
    "Холодный фильтр": "curves=b='0/0 0.4/0.5 1/1':g='0/0 0.4/0.4 1/1'",
    "Теплый фильтр": "curves=r='0/0 0.4/0.5 1/1':g='0/0 0.6/0.6 1/1'",
    "Случайный фильтр": "RANDOM_PLACEHOLDER"
}

OVERLAY_POSITIONS = {
    "Верх-Лево": "x=20:y=140",
    "Верх-Центр": "x=(W-w)/2:y=140",
    "Верх-Право": "x=W-w-10:y=140",
    "Середина-Лево": "x=10:y=(H-h)/2",
    "Середина-Центр": "x=(W-w)/2:y=(H-h)/2+270",
    "Середина-Право": "x=W-w-10:y=(H-h)/2",
    "Низ-Лево": "x=10:y=H-h-10",
    "Низ-Центр": "x=(W-w)/2:y=H-h-10",
    "Низ-Право": "x=W-w-10:y=H-h-10"
}

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".m4v"}
GIF_EXTENSIONS = {".gif"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}
OVERLAY_EXTENSIONS = GIF_EXTENSIONS.union(IMAGE_EXTENSIONS)
VALID_INPUT_EXTENSIONS = VIDEO_EXTENSIONS.union(GIF_EXTENSIONS)
