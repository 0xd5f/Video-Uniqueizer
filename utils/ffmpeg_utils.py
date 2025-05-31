# utils/ffmpeg_utils.py
import os
import subprocess
import random
import platform
import shlex
import shutil
import ffmpeg
from typing import List, Optional, Tuple
from .constants import (
    FFMPEG_PATH, FILTERS, OVERLAY_POSITIONS,
    REELS_WIDTH, REELS_HEIGHT, REELS_FORMAT_NAME
)

FFMPEG_PATH_EFFECTIVE = FFMPEG_PATH
if not os.path.exists(FFMPEG_PATH_EFFECTIVE):
    print(f"Info: FFmpeg not found at specified path '{FFMPEG_PATH}'. Trying system PATH...")
    ffmpeg_cmd_in_path = shutil.which("ffmpeg")
    if ffmpeg_cmd_in_path:
        FFMPEG_PATH_EFFECTIVE = ffmpeg_cmd_in_path
        print(f"Info: Using FFmpeg found in system PATH: {FFMPEG_PATH_EFFECTIVE}")
    else:
        print(
            f"Warning: FFmpeg not found in system PATH either. Processing might fail if '{FFMPEG_PATH}' is incorrect.")

def has_audio_stream(video_path: str) -> bool:
    try:
        probe = ffmpeg.probe(video_path)
        for stream in probe['streams']:
            if stream['codec_type'] == 'audio':
                return True
    except Exception:
            pass
    return False

def run_ffmpeg(cmd: List[str], input_file_for_log: str = "input"):
    """
    Запускает FFmpeg с заданной командой и обрабатывает вывод.
    """
    if not os.path.exists(FFMPEG_PATH_EFFECTIVE) and not shutil.which("ffmpeg"):
        raise FileNotFoundError(
            f"FFmpeg executable not found at '{FFMPEG_PATH_EFFECTIVE}' or in system PATH. Cannot run command.")
    creationflags = 0
    startupinfo = None
    if platform.system() == "Windows":
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    final_cmd = [FFMPEG_PATH_EFFECTIVE]
    if "-hide_banner" not in cmd:
        final_cmd.append("-hide_banner")
    if "-loglevel" not in cmd:
        final_cmd.extend(["-loglevel", "warning"])
    args_to_add = cmd[1:] if cmd and (cmd[0] in (FFMPEG_PATH, FFMPEG_PATH_EFFECTIVE)) else cmd
    final_cmd.extend(args_to_add)
    print(f"Running FFmpeg command: {' '.join(shlex.quote(str(c)) for c in final_cmd)}")
    try:
        process = subprocess.Popen(
            final_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace',
            creationflags=creationflags, startupinfo=startupinfo
        )
        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line: break
            line = line.strip()
            if line:
                print(f"FFmpeg: {line}")
                output_lines.append(line)
        process.stdout.close()
        return_code = process.wait()
        if return_code != 0:
            error_message = (
                    f"FFmpeg failed with exit code {return_code} for file '{os.path.basename(input_file_for_log)}'.\n"
                    f"Command: {' '.join(shlex.quote(str(c)) for c in final_cmd)}\n"
                    "Last lines of output:\n" + "\n".join(output_lines[-15:])
            )
            raise subprocess.CalledProcessError(return_code, final_cmd,
                                                output="\n".join(output_lines),
                                                stderr="\n".join(output_lines))
        print(f"FFmpeg successfully processed '{os.path.basename(input_file_for_log)}'")
    except FileNotFoundError:
        raise FileNotFoundError(
            f"FFmpeg executable not found at '{FFMPEG_PATH_EFFECTIVE}'. Please ensure FFmpeg is installed and accessible.")
    except Exception as e:
        raise RuntimeError(
            f"An error occurred while running FFmpeg for file '{os.path.basename(input_file_for_log)}': {e}")


def get_video_dimensions(path: str) -> Tuple[int, int]:
    """Получает ширину и высоту видео с помощью ffprobe."""
    ffprobe_path_effective = FFMPEG_PATH_EFFECTIVE.replace("ffmpeg.exe", "ffprobe.exe").replace("ffmpeg", "ffprobe")
    if not os.path.exists(ffprobe_path_effective):
        print(f"Info: ffprobe not found near '{FFMPEG_PATH_EFFECTIVE}'. Trying system PATH...")
        ffprobe_cmd_in_path = shutil.which("ffprobe")
        if ffprobe_cmd_in_path:
            ffprobe_path_effective = ffprobe_cmd_in_path
            print(f"Info: Using ffprobe found in system PATH: {ffprobe_path_effective}")
        else:
            print(f"Warning: ffprobe not found in system PATH either. Cannot get video dimensions.")
            return 0, 0
    cmd = [
        ffprobe_path_effective, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", path
    ]
    try:
        creationflags = 0
        startupinfo = None
        if platform.system() == "Windows":
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True,
            encoding='utf-8', errors='replace',
            creationflags=creationflags, startupinfo=startupinfo
        )
        dims = result.stdout.strip().split('x')
        if len(dims) == 2:
            return int(dims[0]), int(dims[1])
        print(f"Warning: Could not parse dimensions from ffprobe output: '{result.stdout.strip()}'")
        return 0, 0
    except subprocess.CalledProcessError as e:
        print(f"Error running ffprobe for '{os.path.basename(path)}': {e.stderr.strip()}")
        return 0, 0
    except FileNotFoundError:
        print(f"Error: ffprobe executable not found at '{ffprobe_path_effective}'.")
        return 0, 0
    except Exception as e:
        print(f"Unexpected error getting dimensions for '{os.path.basename(path)}': {e}")
        return 0, 0


def process_single(
        in_path: str,
        out_path: str,
        filters: List[str],
        zoom_p: int,
        speed_p: int,
        overlay_file: Optional[str],
        overlay_pos: str,
        output_format: str,
        blur_background: bool,
        mute_audio: bool = False,
        strip_metadata: bool = False,
        hardware: str = "cpu"
):
    is_gif_input = in_path.lower().endswith('.gif')
    is_gif_overlay = overlay_file and overlay_file.lower().endswith('.gif')
    cmd = [FFMPEG_PATH_EFFECTIVE, "-y"]
    input_streams = []

    if is_gif_input:
        cmd.extend(["-stream_loop", "-1", "-i", in_path])
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])
        main_video_stream_label = "[0:v]"
        main_audio_stream_label = "[1:a]"
        has_real_audio = False
    else:
        cmd.extend(["-i", in_path])
        main_video_stream_label = "[0:v]"
        main_audio_stream_label = "[0:a]"
        has_real_audio = has_audio_stream(in_path)

    overlay_stream_label = None
    if overlay_file and os.path.exists(overlay_file):
        if is_gif_overlay:
            cmd.extend(["-stream_loop", "-1", "-i", overlay_file])
        else:
            cmd.extend(["-i", overlay_file])
        overlay_stream_label = f"[{len(cmd) // 2 - 1}:v]"

    target_w, target_h = REELS_WIDTH, REELS_HEIGHT
    is_reels_format = (output_format == REELS_FORMAT_NAME)
    filter_complex_parts = []
    last_video_node = main_video_stream_label

    if is_reels_format:
        if blur_background:
            filter_complex_parts.append(
                f"{main_video_stream_label}split[original][original_copy];"
                f"[original_copy]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
                f"crop={target_w}:{target_h}:(in_w-{target_w})/2:(in_h-{target_h})/2,"
                f"gblur=sigma=25[bg];"
                f"[original]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=x=(W-w)/2:y=(H-h)/2:shortest=1[formatted]"
            )
        else:
            filter_complex_parts.append(
                f"{main_video_stream_label}scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black[formatted]"
            )
        last_video_node = "[formatted]"

    # Цветовые фильтры
    applied_color_filters = []
    for f_name in filters:
        f_template = FILTERS.get(f_name)
        if not f_template or f_name == "Нет фильтра":
            continue
        if f_name == "Случайный фильтр":
            possible_filters = [
                k for k, v in FILTERS.items()
                if v and k not in ("Нет фильтра", "Случайный фильтр", "Случ. цвет (яркость/контраст/...)")
            ]
            if possible_filters:
                chosen = random.choice(possible_filters)
                tmpl = FILTERS[chosen]
                if tmpl.startswith("eq=brightness="):
                    br = random.uniform(-0.15, 0.15)
                    ct = random.uniform(0.8, 1.2)
                    sat = random.uniform(0.8, 1.3)
                    hue = random.uniform(-5, 5)
                    applied_color_filters.append(tmpl.format(br=br, ct=ct, sat=sat, hue=hue))
                else:
                    applied_color_filters.append(tmpl)
        elif f_name == "Случ. цвет (яркость/контраст/...)":
            br = random.uniform(-0.15, 0.15)
            ct = random.uniform(0.8, 1.2)
            sat = random.uniform(0.8, 1.3)
            hue = random.uniform(-5, 5)
            applied_color_filters.append(f_template.format(br=br, ct=ct, sat=sat, hue=hue))
        else:
            applied_color_filters.append(f_template)

    if applied_color_filters:
        chain = ",".join(applied_color_filters)
        filter_complex_parts.append(f"{last_video_node}{chain}[filtered]")
        last_video_node = "[filtered]"

    # Zoom
    zoom_factor = zoom_p / 100.0
    if abs(zoom_factor - 1.0) > 1e-5:
        zm = []
        zm.append(f"scale=iw*{zoom_factor}:ih*{zoom_factor}:flags=bicubic")
        if is_reels_format:
            zm.append(f"crop={target_w}:{target_h}:(in_w-{target_w})/2:(in_h-{target_h})/2")
        else:
            zm.append(f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black")
        filter_complex_parts.append(f"{last_video_node}{','.join(zm)}[zoomed]")
        last_video_node = "[zoomed]"

    # Скорость
    speed_factor = speed_p / 100.0
    last_audio_node = main_audio_stream_label
    audio_speed_applied = False
    if abs(speed_factor - 1.0) > 1e-5:
        filter_complex_parts.append(f"{last_video_node}setpts=PTS/{speed_factor}[speed_v]")
        last_video_node = "[speed_v]"
        if has_real_audio:
            tempo = []
            cur = speed_factor
            while cur > 2.0:
                tempo.append("atempo=2.0")
                cur /= 2.0
            min_tempo = 0.5
            while cur < min_tempo:
                tempo.append(f"atempo={min_tempo}")
                cur /= min_tempo
            if abs(cur - 1.0) > 1e-5 and min_tempo <= cur <= 2.0:
                tempo.append(f"atempo={cur}")
            if tempo:
                af = ",".join(tempo)
                filter_complex_parts.append(f"{main_audio_stream_label}{af}[speed_a]")
                last_audio_node = "[speed_a]"
                audio_speed_applied = True

    # Обработка аудио (условная)
    if has_real_audio and not mute_audio:
        if audio_speed_applied:
            filter_complex_parts.append(f"{last_audio_node}anull[audio_final]")
            last_audio_node = "[audio_final]"
        else:
            filter_complex_parts.append(f"{main_audio_stream_label}anull[audio_final]")
            last_audio_node = "[audio_final]"
    else:
        last_audio_node = None  # звука нет или отключён

    # Наложение
    if overlay_stream_label:
        pos = OVERLAY_POSITIONS.get(overlay_pos, "x=(W-w)/2:y=(H-h)/2")
        filter_complex_parts.append(f"{overlay_stream_label}format=rgba[ovl_alpha]")
        filter_complex_parts.append(f"{last_video_node}[ovl_alpha]overlay={pos}:shortest=1[overlayed]")
        last_video_node = "[overlayed]"

    filter_complex_parts.append(f"{last_video_node}format=pix_fmts=yuv420p[vout]")
    fc_string = ";".join(filter_complex_parts)
    cmd.extend(["-filter_complex", fc_string])
    cmd.extend(["-map", "[vout]"])

    if last_audio_node:
        cmd.extend(["-map", last_audio_node, "-c:a", "aac", "-b:a", "128k"])
    else:
        cmd.append("-an")  # отключить аудиодорожку

    cmd.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "24"])

    if strip_metadata:
        cmd.extend(["-map_metadata", "-1", "-map_chapters", "-1"])

    if not is_gif_input:
        cmd.append("-shortest")

    cmd.append(out_path)
    run_ffmpeg(cmd, input_file_for_log=in_path)
