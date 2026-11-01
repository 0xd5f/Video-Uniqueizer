# workers/reels_worker.py
import os
from dataclasses import asdict
from typing import List

from PyQt5.QtCore import QThread, pyqtSignal

from utils import reels_engine as engine


class ReelsWorker(QThread):
    """Генерирует N уникальных копий для каждого исходного видео."""
    overall_progress = pyqtSignal(int, int)   # готово копий, всего копий
    copy_progress = pyqtSignal(int)           # 0..100 для текущей копии
    current_copy = pyqtSignal(str)            # имя текущего файла
    log = pyqtSignal(str)
    done = pyqtSignal(int, int, bool)         # успешно, всего, остановлено

    def __init__(self, files: List[str], out_dir: str, copies: int,
                 intensity: str, quality: str, resolution: str):
        super().__init__()
        self.files = list(files)
        self.out_dir = out_dir
        self.copies = copies
        self.intensity = intensity
        self.quality = quality
        self.resolution = resolution
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        total = len(self.files) * self.copies
        finished = ok = 0
        for path in self.files:
            if self._stop:
                break
            name = os.path.basename(path)
            stem = os.path.splitext(name)[0]
            try:
                src = engine.probe(path)
            except Exception as e:
                self.log.emit(f"✖ {name}: не удалось прочитать файл — {e}")
                finished += self.copies
                self.overall_progress.emit(finished, total)
                continue

            size = engine.target_size(src, self.resolution)
            dst_dir = os.path.join(self.out_dir, f"{stem}_unique")
            os.makedirs(dst_dir, exist_ok=True)
            self.log.emit(f"▶ {name}: {src.width}×{src.height} @ {src.fps:.2f} fps"
                          f"{' · HDR → SDR' if src.is_hdr else ''} → {size[0]}×{size[1]}")

            rows = []
            for v in engine.make_variants(src, self.copies, self.intensity, self.quality, size):
                if self._stop:
                    break
                dst = os.path.join(dst_dir, f"{stem}_{v.index:02d}.mp4")
                self.current_copy.emit(f"{os.path.basename(dst)} ({finished + 1}/{total})")
                self.copy_progress.emit(0)
                try:
                    engine.render_variant(
                        src, v, dst, self.resolution,
                        on_progress=lambda p: self.copy_progress.emit(int(p * 100)),
                        should_stop=lambda: self._stop,
                    )
                    ok += 1
                    rows.append({"file": os.path.basename(dst), **asdict(v)})
                    self.log.emit(f"  ✔ {os.path.basename(dst)}: {engine.describe(v)}")
                except engine.CancelledError:
                    break
                except Exception as e:
                    self.log.emit(f"  ✖ {os.path.basename(dst)}: {e}")
                finished += 1
                self.overall_progress.emit(finished, total)

            if rows:
                engine.save_report(os.path.join(dst_dir, f"{stem}_params.json"), src, rows)

        self.done.emit(ok, total, self._stop)
