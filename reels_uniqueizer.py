"""
Reels Uniqueizer (консольная версия) — генерирует N уникальных копий видео.
Та же логика, что во вкладке «Уникализация Reels» приложения (utils/reels_engine.py).

Использование:
    python reels_uniqueizer.py input.mp4
    python reels_uniqueizer.py input.mp4 -o output_folder -n 10 --intensity Стандарт \
        --quality Максимальное --reels
"""
import argparse
import os
import sys
from dataclasses import asdict

from utils import reels_engine as engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Уникализация видео для Instagram Reels")
    parser.add_argument("input", help="Путь к исходному видео")
    parser.add_argument("-o", "--output", help="Папка для результатов (по умолчанию <имя>_unique)")
    parser.add_argument("-n", "--count", type=int, default=10, help="Количество копий (10)")
    parser.add_argument("--intensity", choices=list(engine.INTENSITY_PRESETS),
                        default=engine.DEFAULT_INTENSITY)
    parser.add_argument("--quality", choices=list(engine.QUALITY_PRESETS),
                        default=engine.DEFAULT_QUALITY)
    parser.add_argument("--reels", action="store_true", help="Привести к 1080×1920")
    args = parser.parse_args()

    src_path = os.path.abspath(args.input)
    if not os.path.isfile(src_path):
        sys.exit(f"[ошибка] Файл не найден: {src_path}")
    stem = os.path.splitext(os.path.basename(src_path))[0]
    out_dir = os.path.abspath(args.output or os.path.join(os.path.dirname(src_path), f"{stem}_unique"))
    os.makedirs(out_dir, exist_ok=True)

    resolution = engine.RESOLUTION_REELS if args.reels else engine.RESOLUTION_ORIGINAL
    src = engine.probe(src_path)
    size = engine.target_size(src, resolution)
    print(f"Исходник: {os.path.basename(src_path)} | {src.width}x{src.height} @ {src.fps:.2f} fps"
          f"{' | HDR' if src.is_hdr else ''} → {size[0]}x{size[1]}")

    rows = []
    for v in engine.make_variants(src, args.count, args.intensity, args.quality, size):
        dst = os.path.join(out_dir, f"{stem}_{v.index:02d}.mp4")
        print(f"[{v.index}/{args.count}] {os.path.basename(dst)}: {engine.describe(v)}")
        try:
            engine.render_variant(src, v, dst, resolution,
                                  on_progress=lambda p: print(f"\r  {p * 100:5.1f}%", end=""))
            print()
            rows.append({"file": os.path.basename(dst), **asdict(v)})
        except RuntimeError as e:
            print(f"\n[ошибка] {e}")

    engine.save_report(os.path.join(out_dir, f"{stem}_params.json"), src, rows)
    print(f"Готово: {len(rows)}/{args.count} копий в {out_dir}")


if __name__ == "__main__":
    main()
