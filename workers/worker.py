import subprocess
from PyQt5.QtCore import QThread, pyqtSignal
import os
import random
from typing import List, Optional
from utils.ffmpeg_utils import process_single, get_video_dimensions


class Worker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    file_processing = pyqtSignal(str)

    def __init__(
            self,
            files: List[str],
            filters: List[str],
            zoom_mode: str,
            zoom_min: int,
            zoom_max: int,
            speed_mode: str,
            speed_min: int,
            speed_max: int,
            overlay_file: Optional[str],
            overlay_pos: str,
            out_dir: str,
            mute_audio: bool,
            output_format: str,
            blur_background: bool,
            strip_metadata: bool,
    ):
        super().__init__()
        self.files = list(files)
        self.filters = list(filters)
        self.zoom_mode = zoom_mode
        self.zoom_min = zoom_min
        self.zoom_max = zoom_max
        self.speed_mode = speed_mode
        self.speed_min = speed_min
        self.speed_max = speed_max
        self.overlay_file = overlay_file
        self.overlay_pos = overlay_pos
        self.out_dir = out_dir
        self.mute_audio = mute_audio
        self.output_format = output_format
        self.blur_background = blur_background
        self.strip_metadata = strip_metadata
        self._is_running = True

    def pick_zoom(self) -> int:
        """Выбирает значение Zoom в зависимости от режима."""
        if self.zoom_mode == "dynamic" and self.zoom_max >= self.zoom_min:
            try:
                return random.randint(self.zoom_min, self.zoom_max)
            except ValueError:
                return self.zoom_min
        return self.zoom_min

    def pick_speed(self) -> int:
        """Выбирает значение скорости в зависимости от режима."""
        if self.speed_mode == "dynamic" and self.speed_max >= self.speed_min:
            try:
                return random.randint(self.speed_min, self.speed_max)
            except ValueError:
                return self.speed_min
        return self.speed_min

    def stop(self):
        self._is_running = False
        print("Worker stop requested.")

    def run(self):
        """Основной цикл обработки файлов."""
        total_files = len(self.files)
        if total_files == 0:
            self.finished.emit()
            return

        try:
            os.makedirs(self.out_dir, exist_ok=True)
        except OSError as e:
            self.error.emit(f"Не удалось создать выходную папку: {self.out_dir}\nОшибка: {e}")
            return

        for i, in_file_path in enumerate(self.files):
            if not self._is_running:
                print("Worker stopped.")
                break

            base_name = os.path.basename(in_file_path)
            name_part, _ = os.path.splitext(base_name)
            suffix = "_reels" if self.output_format != "Оригинальный" else "_processed"
            out_file_name = f"{name_part}{suffix}.mp4"
            out_file_path = os.path.join(self.out_dir, out_file_name)

            if os.path.abspath(in_file_path) == os.path.abspath(out_file_path):
                alt_out_file_name = f"{name_part}{suffix}_output.mp4"
                out_file_path = os.path.join(self.out_dir, alt_out_file_name)
                print(f"Warning: Output path is same as input. Saving to: {alt_out_file_name}")

            self.file_processing.emit(base_name)

            try:
                current_zoom = self.pick_zoom()
                current_speed = self.pick_speed()

                process_single(
                    in_path=in_file_path,
                    out_path=out_file_path,
                    filters=self.filters,
                    zoom_p=current_zoom,
                    speed_p=current_speed,
                    overlay_file=self.overlay_file,
                    overlay_pos=self.overlay_pos,
                    output_format=self.output_format,
                    blur_background=self.blur_background,
                    mute_audio=self.mute_audio,
                    strip_metadata=self.strip_metadata,
                )
                self.progress.emit(i + 1, total_files)

            except Exception as e:
                error_msg = f"Ошибка при обработке файла '{base_name}':\n{type(e).__name__}: {e}"
                if isinstance(e, subprocess.CalledProcessError) and e.output:
                    error_msg += f"\n\nFFmpeg output:\n{e.output[-500:]}"
                print(f"Error in worker thread: {error_msg}")
                self.error.emit(error_msg)
                continue

        if self._is_running:
            print("Worker finished processing all files.")
            self.finished.emit()
        else:
            print("Worker finished due to stop request.")
