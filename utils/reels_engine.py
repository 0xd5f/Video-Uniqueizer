# utils/reels_engine.py
"""
Движок уникализации видео для Instagram Reels.

Для каждой копии случайно (в пределах выбранной интенсивности) меняются:
кроп краёв, скорость видео/аудио, яркость/контраст/насыщенность, зерно,
частота кадров, CRF и потолок битрейта, интервал ключевых кадров, громкость.
Все метаданные удаляются. Модуль не зависит от Qt — используется и из UI,
и из консольного скрипта reels_uniqueizer.py.
"""
import json
import os
import platform
import random
import shutil
import subprocess
from dataclasses import dataclass, asdict
from typing import Callable, Dict, List, Optional, Tuple

from .constants import FFMPEG_PATH

# ---------------------------------------------------------------------------
# Пресеты
# ---------------------------------------------------------------------------
INTENSITY_PRESETS: Dict[str, dict] = {
    "Мягкая": dict(crop=(0.004, 0.012), speed=(0.995, 1.008), brightness=0.006,
                   contrast=0.008, saturation=0.008, noise=(1, 2), volume_db=0.2),
    "Стандарт": dict(crop=(0.005, 0.025), speed=(0.99, 1.015), brightness=0.012,
                     contrast=0.015, saturation=0.015, noise=(1, 3), volume_db=0.3),
    "Сильная": dict(crop=(0.015, 0.04), speed=(0.98, 1.025), brightness=0.02,
                    contrast=0.025, saturation=0.03, noise=(2, 4), volume_db=0.5),
}

QUALITY_PRESETS: Dict[str, dict] = {
    "Максимальное": dict(crf=(16.0, 18.0), preset="slow"),
    "Высокое": dict(crf=(18.0, 20.0), preset="medium"),
    "Быстрое": dict(crf=(20.0, 22.0), preset="faster"),
}

RESOLUTION_ORIGINAL = "Исходное"
RESOLUTION_REELS = "Reels 1080×1920"
RESOLUTIONS = [RESOLUTION_ORIGINAL, RESOLUTION_REELS]

DEFAULT_INTENSITY = "Стандарт"
DEFAULT_QUALITY = "Максимальное"

# Частоты кадров: 59.94/60 предлагаются только для исходников > 50 fps,
# иначе ffmpeg просто дублирует кадры и раздувает файл без пользы.
FPS_NORMAL = ["30000/1001", "30", "30030/1000"]     # 29.97 / 30 / 30.03
FPS_HIGH = ["60000/1001", "60"]                      # 59.94 / 60
# Потолок битрейта для 1080×1920@30 (масштабируется по площади кадра и fps)
MAXRATE_RANGE_K = (9000, 14000)
AUDIO_BITRATES_K = [160, 192]
HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}        # PQ (HDR10) и HLG (iPhone)

ProgressCallback = Callable[[float], None]
StopCheck = Callable[[], bool]


class CancelledError(Exception):
    """Обработка остановлена пользователем."""


# ---------------------------------------------------------------------------
# Поиск ffmpeg / ffprobe
# ---------------------------------------------------------------------------
def _find_tool(name: str) -> str:
    local = FFMPEG_PATH.replace("ffmpeg.exe", f"{name}.exe") if name != "ffmpeg" else FFMPEG_PATH
    if platform.system() != "Windows":
        local = local[:-4] if local.endswith(".exe") else local
    if os.path.exists(local):
        return local
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(f"{name} не найден: положите его в ffmpeg/bin или добавьте в PATH.")


def _popen_kwargs() -> dict:
    """Скрывает консольное окно ffmpeg на Windows."""
    if platform.system() != "Windows":
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    return {"creationflags": subprocess.CREATE_NO_WINDOW, "startupinfo": si}


_zscale_cache: Optional[bool] = None


def _has_zscale(ffmpeg: str) -> bool:
    """Есть ли в сборке ffmpeg фильтр zscale (нужен для HDR → SDR)."""
    global _zscale_cache
    if _zscale_cache is None:
        out = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True,
                             text=True, errors="replace", **_popen_kwargs()).stdout
        _zscale_cache = " zscale " in out
    return _zscale_cache


# ---------------------------------------------------------------------------
# Анализ исходника
# ---------------------------------------------------------------------------
@dataclass
class SourceInfo:
    path: str
    width: int          # с учётом поворота
    height: int
    fps: float
    duration: float     # секунды
    has_audio: bool
    is_hdr: bool


def _fraction(value: str) -> float:
    num, _, den = str(value).partition("/")
    try:
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def probe(path: str) -> SourceInfo:
    ffprobe = _find_tool("ffprobe")
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=True, **_popen_kwargs(),
    ).stdout
    data = json.loads(out)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise ValueError("В файле нет видеодорожки")

    width, height = int(video["width"]), int(video["height"])
    rotation = 0
    for sd in video.get("side_data_list", []):
        if "rotation" in sd:
            rotation = int(sd["rotation"])
    rotation = int(video.get("tags", {}).get("rotate", rotation))
    if abs(rotation) % 180 == 90:
        width, height = height, width

    fps = _fraction(video.get("avg_frame_rate", "0")) or _fraction(video.get("r_frame_rate", "30"))
    duration = float(data.get("format", {}).get("duration") or video.get("duration") or 0)

    return SourceInfo(
        path=path, width=width, height=height, fps=fps or 30.0, duration=duration,
        has_audio=any(s.get("codec_type") == "audio" for s in streams),
        is_hdr=video.get("color_transfer") in HDR_TRANSFERS,
    )


# ---------------------------------------------------------------------------
# Случайные параметры копии
# ---------------------------------------------------------------------------
@dataclass
class Variant:
    index: int
    crop_w: float          # доля обрезки по ширине
    crop_h: float          # доля обрезки по высоте
    crop_x_shift: float    # 0..1 — положение окна кропа
    crop_y_shift: float
    speed: float
    brightness: float
    contrast: float
    saturation: float
    sharpen: float         # сила unsharp по яркости
    noise: int             # сила зерна
    fps: str
    crf: float
    maxrate_k: int
    gop: int
    preset: str
    audio_bitrate_k: int
    volume_db: float


def make_variants(src: SourceInfo, count: int, intensity: str, quality: str,
                  target_size: Tuple[int, int]) -> List[Variant]:
    ip = INTENSITY_PRESETS[intensity]
    qp = QUALITY_PRESETS[quality]
    fps_pool = FPS_HIGH + ["30000/1001"] if src.fps > 50 else FPS_NORMAL

    # Потолок битрейта пропорционален площади кадра и частоте
    w, h = target_size
    scale = (w * h) / (1080 * 1920)

    variants, used_maxrates = [], set()
    for i in range(count):
        fps = random.choice(fps_pool)
        fps_value = _fraction(fps)
        maxrate = int(random.uniform(*MAXRATE_RANGE_K) * scale * (1.5 if fps_value > 50 else 1.0))
        while maxrate in used_maxrates:          # битрейт у каждой копии свой
            maxrate += random.randint(7, 61)
        used_maxrates.add(maxrate)
        variants.append(Variant(
            index=i + 1,
            crop_w=random.uniform(*ip["crop"]),
            crop_h=random.uniform(*ip["crop"]),
            crop_x_shift=random.random(),
            crop_y_shift=random.random(),
            speed=random.uniform(*ip["speed"]),
            brightness=random.uniform(-ip["brightness"], ip["brightness"]),
            contrast=1 + random.uniform(-ip["contrast"], ip["contrast"]),
            saturation=1 + random.uniform(-ip["saturation"], ip["saturation"]),
            sharpen=random.uniform(0.15, 0.35),
            noise=random.randint(*ip["noise"]),
            fps=fps,
            crf=round(random.uniform(*qp["crf"]), 1),
            maxrate_k=maxrate,
            gop=round(fps_value * random.uniform(1.5, 3.0)),
            preset=qp["preset"],
            audio_bitrate_k=random.choice(AUDIO_BITRATES_K),
            volume_db=random.uniform(-ip["volume_db"], ip["volume_db"]),
        ))
    return variants


# ---------------------------------------------------------------------------
# Сборка команды ffmpeg
# ---------------------------------------------------------------------------
def _even(n: float) -> int:
    """H.264 + yuv420p требует чётных размеров."""
    return max(2, int(round(n)) // 2 * 2)


def target_size(src: SourceInfo, resolution: str) -> Tuple[int, int]:
    if resolution == RESOLUTION_REELS:
        return 1080, 1920
    return _even(src.width), _even(src.height)


def _video_filter(src: SourceInfo, v: Variant, out_w: int, out_h: int, ffmpeg: str) -> str:
    pre = []
    # HDR (iPhone HLG / HDR10) → SDR BT.709, иначе в Reels картинка выцветает
    if src.is_hdr and _has_zscale(ffmpeg):
        pre.append("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
                   "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv")

    # Микро-кроп в случайном месте кадра
    cw = _even(src.width * (1 - v.crop_w))
    ch = _even(src.height * (1 - v.crop_h))
    cx = int((src.width - cw) * v.crop_x_shift)
    cy = int((src.height - ch) * v.crop_y_shift)
    pre.append(f"crop={cw}:{ch}:{cx}:{cy}")

    scale_opts = "flags=lanczos+accurate_rnd+full_chroma_int:out_color_matrix=bt709:out_range=tv"
    post = [
        "setsar=1",
        f"eq=brightness={v.brightness:.4f}:contrast={v.contrast:.4f}:saturation={v.saturation:.4f}",
        # Микро-резкость компенсирует мягкость после масштабирования
        f"unsharp=5:5:{v.sharpen:.3f}:5:5:0",
        # Едва заметное зерно: меняет perceptual hash и маскирует бэндинг
        # после пережатия Instagram
        f"noise=c0s={v.noise}:c0f=t",
        f"setpts=PTS/{v.speed:.5f}",
        f"fps={v.fps}",
        "format=yuv420p",
        # Явная маркировка BT.709 — иначе Instagram может «угадать» цвет неверно
        "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv",
    ]

    aspect_src = cw / ch
    aspect_dst = out_w / out_h
    if abs(aspect_src - aspect_dst) / aspect_dst < 0.03:
        # Пропорции совпадают — просто масштабируем
        return ",".join(pre + [f"scale={out_w}:{out_h}:{scale_opts}"] + post)

    # Пропорции разные — видео по центру на размытом фоне
    return (
        f"{','.join(pre)},split[fg0][bg0];"
        f"[bg0]scale={out_w // 4}:{out_h // 4}:force_original_aspect_ratio=increase,"
        f"crop={out_w // 4}:{out_h // 4},gblur=sigma=12,scale={out_w}:{out_h}[bg];"
        f"[fg0]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease:{scale_opts}[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,{','.join(post)}"
    )


def build_command(src: SourceInfo, v: Variant, out_path: str, resolution: str) -> List[str]:
    ffmpeg = _find_tool("ffmpeg")
    out_w, out_h = target_size(src, resolution)
    level = "4.2" if _fraction(v.fps) > 50 else "4.1"

    cmd = [
        ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
        "-progress", "pipe:1", "-nostats",
        "-i", src.path,
        "-filter_complex", f"[0:v:0]{_video_filter(src, v, out_w, out_h, ffmpeg)}[vout]",
        "-map", "[vout]",
        # Видео: CRF даёт стабильное качество, maxrate/bufsize — уникальный битрейт
        "-c:v", "libx264", "-preset", v.preset, "-tune", "film",
        "-crf", f"{v.crf}", "-maxrate", f"{v.maxrate_k}k", "-bufsize", f"{v.maxrate_k * 2}k",
        "-profile:v", "high", "-level:v", level, "-pix_fmt", "yuv420p",
        "-g", str(v.gop), "-keyint_min", str(max(1, v.gop // 2)), "-r", v.fps,
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-color_range", "tv",
    ]

    if src.has_audio:
        cmd += [
            "-map", "0:a:0",
            "-af", f"atempo={v.speed:.5f},volume={v.volume_db:.2f}dB,aresample=48000",
            "-c:a", "aac", "-b:a", f"{v.audio_bitrate_k}k", "-ac", "2",
            "-shortest",
        ]

    cmd += [
        # Полная очистка метаданных и подписи энкодера
        "-map_metadata", "-1", "-map_metadata:s:v", "-1", "-map_metadata:s:a", "-1",
        "-map_chapters", "-1",
        "-metadata:s:v", "encoder=", "-metadata:s:a", "encoder=",
        "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact",
        "-movflags", "+faststart",
        out_path,
    ]
    return cmd


# ---------------------------------------------------------------------------
# Рендер
# ---------------------------------------------------------------------------
def render_variant(src: SourceInfo, v: Variant, out_path: str, resolution: str,
                   on_progress: Optional[ProgressCallback] = None,
                   should_stop: Optional[StopCheck] = None) -> None:
    """Кодирует одну копию. Прогресс 0..1 передаётся в on_progress."""
    cmd = build_command(src, v, out_path, resolution)
    expected = src.duration / v.speed if src.duration else 0
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace", **_popen_kwargs())
    stderr_lines: List[str] = []
    try:
        for line in proc.stdout:
            if should_stop and should_stop():
                proc.kill()
                proc.wait()
                _remove_quietly(out_path)
                raise CancelledError()
            key, _, value = line.strip().partition("=")
            if key == "out_time_us" and expected and on_progress and value.isdigit():
                on_progress(min(1.0, int(value) / 1_000_000 / expected))
        stderr_lines = proc.stderr.read().splitlines()
        code = proc.wait()
    finally:
        if proc.poll() is None:
            proc.kill()
    if code != 0:
        _remove_quietly(out_path)
        tail = "\n".join(stderr_lines[-10:])
        raise RuntimeError(f"ffmpeg завершился с кодом {code}:\n{tail}")
    if on_progress:
        on_progress(1.0)


def _remove_quietly(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def describe(v: Variant) -> str:
    """Короткое описание копии для лога."""
    return (f"скорость {v.speed:.4f}x · {_fraction(v.fps):.2f} fps · CRF {v.crf} · "
            f"≤{v.maxrate_k}k · кроп {v.crop_w * 100:.2f}%×{v.crop_h * 100:.2f}%")


def save_report(path: str, src: SourceInfo, rows: List[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"source": asdict(src), "copies": rows}, f, indent=2, ensure_ascii=False)
