# ui/reels_tab.py
import os
import subprocess
import sys

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QSpinBox, QComboBox, QGroupBox, QFormLayout, QLineEdit, QProgressBar,
    QPlainTextEdit, QMessageBox, QMenu
)

from ui.widgets import DropListWidget
from utils import reels_engine as engine
from utils.constants import DEFAULT_OUTPUT_DIR
from utils.file_utils import find_videos_in_folder
from workers.reels_worker import ReelsWorker

INTENSITY_HINTS = {
    "Мягкая": "Кроп 0.4–1.2%, скорость ±0.5%. Минимальные изменения.",
    "Стандарт": "Кроп 0.5–2.5%, скорость 0.99–1.015x. Баланс незаметности и уникальности.",
    "Сильная": "Кроп 1.5–4%, скорость 0.98–1.025x. Максимальная уникальность.",
}
QUALITY_HINTS = {
    "Максимальное": "CRF 16–18, preset slow. Лучшее качество, кодирование дольше.",
    "Высокое": "CRF 18–20, preset medium.",
    "Быстрое": "CRF 20–22, preset faster. Для черновых прогонов.",
}


class ReelsTab(QWidget):
    """Вкладка пакетной уникализации: N копий каждого видео."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.init_ui()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(15)

        # --- Левая колонка: исходники ---
        left = QVBoxLayout()
        buttons = QHBoxLayout()
        btn_add = QPushButton("Добавить видео")
        btn_folder = QPushButton("Добавить папку")
        btn_clear = QPushButton("Очистить")
        for b in (btn_add, btn_folder, btn_clear):
            buttons.addWidget(b)
        left.addLayout(buttons)

        self.file_list = DropListWidget(self, allow_gifs=False)
        self.file_list.customContextMenuRequested.connect(self.on_list_menu)
        self.file_list.files_dropped.connect(self.refresh_list)
        left.addWidget(self.file_list)

        hint = QLabel("Перетащите видео или папки сюда")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: gray; font-style: italic;")
        left.addWidget(hint)
        root.addLayout(left, 3)

        # --- Правая колонка: настройки и запуск ---
        right = QVBoxLayout()
        right.setSpacing(10)

        settings = QGroupBox("Параметры уникализации")
        form = QFormLayout(settings)

        self.copies_spin = QSpinBox()
        self.copies_spin.setRange(1, 50)
        self.copies_spin.setValue(10)
        self.copies_spin.setSuffix(" шт.")
        form.addRow("Копий на видео:", self.copies_spin)

        self.intensity_combo = QComboBox()
        self.intensity_combo.addItems(list(engine.INTENSITY_PRESETS))
        self.intensity_combo.setCurrentText(engine.DEFAULT_INTENSITY)
        form.addRow("Интенсивность:", self.intensity_combo)
        self.intensity_hint = self._hint_label()
        form.addRow("", self.intensity_hint)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(list(engine.QUALITY_PRESETS))
        self.quality_combo.setCurrentText(engine.DEFAULT_QUALITY)
        form.addRow("Качество:", self.quality_combo)
        self.quality_hint = self._hint_label()
        form.addRow("", self.quality_hint)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(engine.RESOLUTIONS)
        self.resolution_combo.setToolTip(
            "Reels 1080×1920: вертикальные видео масштабируются,\n"
            "остальные ставятся по центру на размытый фон.")
        form.addRow("Разрешение:", self.resolution_combo)

        out_row = QHBoxLayout()
        self.out_edit = QLineEdit(DEFAULT_OUTPUT_DIR)
        btn_out = QPushButton("Обзор...")
        out_row.addWidget(self.out_edit)
        out_row.addWidget(btn_out)
        form.addRow("Папка вывода:", out_row)
        right.addWidget(settings)

        info = QLabel(
            "Для каждой копии случайно меняются: кроп, скорость, цвет, зерно, FPS, "
            "битрейт, структура GOP и громкость. Метаданные удаляются. "
            "HDR-видео с iPhone автоматически переводятся в SDR.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        right.addWidget(info)

        run_row = QHBoxLayout()
        self.start_btn = QPushButton("🚀 Уникализировать")
        self.start_btn.setFixedHeight(40)
        self.stop_btn = QPushButton("⏹ Стоп")
        self.stop_btn.setFixedHeight(40)
        self.stop_btn.setEnabled(False)
        self.open_btn = QPushButton("📂 Открыть папку")
        self.open_btn.setFixedHeight(40)
        run_row.addWidget(self.start_btn, 2)
        run_row.addWidget(self.stop_btn, 1)
        run_row.addWidget(self.open_btn, 1)
        right.addLayout(run_row)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray;")
        right.addWidget(self.status_label)
        self.copy_bar = QProgressBar()
        self.copy_bar.setFormat("Текущая копия: %p%")
        right.addWidget(self.copy_bar)
        self.total_bar = QProgressBar()
        self.total_bar.setFormat("Всего: %p%")
        right.addWidget(self.total_bar)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Здесь появится журнал обработки")
        right.addWidget(self.log_view, 1)
        root.addLayout(right, 4)

        # --- Сигналы ---
        btn_add.clicked.connect(self.on_add_files)
        btn_folder.clicked.connect(self.on_add_folder)
        btn_clear.clicked.connect(self.on_clear)
        btn_out.clicked.connect(self.on_select_out)
        self.start_btn.clicked.connect(self.on_start)
        self.stop_btn.clicked.connect(self.on_stop)
        self.open_btn.clicked.connect(self.on_open_out)
        self.intensity_combo.currentTextChanged.connect(
            lambda t: self.intensity_hint.setText(INTENSITY_HINTS.get(t, "")))
        self.quality_combo.currentTextChanged.connect(
            lambda t: self.quality_hint.setText(QUALITY_HINTS.get(t, "")))
        self.intensity_hint.setText(INTENSITY_HINTS[self.intensity_combo.currentText()])
        self.quality_hint.setText(QUALITY_HINTS[self.quality_combo.currentText()])

    @staticmethod
    def _hint_label() -> QLabel:
        lbl = QLabel()
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: gray; font-size: 11px;")
        return lbl

    # ----------------------------------------------------------- Список файлов
    def on_add_files(self):
        fs, _ = QFileDialog.getOpenFileNames(
            self, "Выберите видео", "",
            "Видео (*.mp4 *.mov *.avi *.mkv *.m4v *.webm);;Все файлы (*)")
        if any([self.file_list.add_path(f) for f in fs]):
            self.refresh_list()

    def on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку", "")
        if folder and any([self.file_list.add_path(v) for v in find_videos_in_folder(folder)]):
            self.refresh_list()

    def on_clear(self):
        self.file_list.clear()

    def on_list_menu(self, pos: QPoint):
        menu = QMenu()
        act_del = menu.addAction("Удалить выделенное")
        act_clear = menu.addAction("Очистить список")
        chosen = menu.exec_(self.file_list.viewport().mapToGlobal(pos))
        if chosen == act_del:
            for it in reversed(self.file_list.selectedItems()):
                self.file_list.takeItem(self.file_list.row(it))
            self.refresh_list()
        elif chosen == act_clear:
            self.on_clear()

    def refresh_list(self):
        for i in range(self.file_list.count()):
            it = self.file_list.item(i)
            it.setText(f"{i + 1}. {os.path.basename(it.data(Qt.UserRole))}")

    def on_select_out(self):
        folder = QFileDialog.getExistingDirectory(self, "Папка для результатов", self.out_edit.text())
        if folder:
            self.out_edit.setText(folder)

    def on_open_out(self):
        path = self.out_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.information(self, "Папка не найдена", "Папка вывода ещё не создана.")
            return
        if sys.platform.startswith("win"):
            os.startfile(path)
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])

    # --------------------------------------------------------------- Обработка
    def is_running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def on_start(self):
        files = self.file_list.paths()
        if not files:
            QMessageBox.warning(self, "Нет файлов", "Добавьте хотя бы одно видео.")
            return
        out_dir = self.out_edit.text().strip()
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать папку вывода:\n{e}")
            return

        self.worker = ReelsWorker(
            files=files, out_dir=out_dir, copies=self.copies_spin.value(),
            intensity=self.intensity_combo.currentText(),
            quality=self.quality_combo.currentText(),
            resolution=self.resolution_combo.currentText(),
        )
        self.worker.overall_progress.connect(self.on_overall)
        self.worker.copy_progress.connect(self.copy_bar.setValue)
        self.worker.current_copy.connect(self.on_current)
        self.worker.log.connect(self.log_view.appendPlainText)
        self.worker.done.connect(self.on_done)

        self.log_view.clear()
        self.copy_bar.setValue(0)
        self.total_bar.setValue(0)
        self.set_running(True)
        self.worker.start()

    def on_stop(self):
        if self.is_running():
            self.worker.stop()
            self.status_label.setText("Останавливаю...")
            self.stop_btn.setEnabled(False)

    def stop_and_wait(self):
        """Вызывается при закрытии окна."""
        if self.is_running():
            self.worker.stop()
            self.worker.wait(5000)

    def on_overall(self, done: int, total: int):
        self.total_bar.setValue(int(done * 100 / total) if total else 0)
        self.total_bar.setFormat(f"Всего: %p% ({done}/{total})")

    def on_current(self, text: str):
        fm = QFontMetrics(self.status_label.font())
        self.status_label.setText(fm.elidedText(f"Кодирую: {text}", Qt.ElideMiddle,
                                                max(100, self.status_label.width() - 10)))

    def on_done(self, ok: int, total: int, stopped: bool):
        self.set_running(False)
        if stopped:
            self.status_label.setText(f"Остановлено. Готово {ok} из {total}.")
            return
        self.status_label.setText(f"Готово: {ok} из {total}")
        self.copy_bar.setValue(100)
        if ok == total:
            QMessageBox.information(self, "Готово", f"Создано {ok} уникальных копий.")
        else:
            QMessageBox.warning(self, "Завершено с ошибками",
                                f"Создано {ok} из {total}. Подробности — в журнале.")

    def set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        for w in (self.copies_spin, self.intensity_combo, self.quality_combo,
                  self.resolution_combo, self.out_edit):
            w.setEnabled(not running)
