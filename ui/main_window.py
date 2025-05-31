# ui/main_window.py
import os
import sys
import random
from typing import List
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QFontMetrics, QIcon
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QAbstractItemView, QFileDialog, QSpinBox,
    QLineEdit, QMessageBox, QProgressBar, QComboBox,
    QGroupBox, QRadioButton, QButtonGroup, QCheckBox, QListWidgetItem, QMenu
)
from workers.worker import Worker
from utils.file_utils import is_video_file, find_videos_in_folder
from utils.constants import FILTERS, OVERLAY_POSITIONS, REELS_FORMAT_NAME

OUTPUT_FORMATS = [
    "Оригинальный",
    "Reels/TikTok (1080x1920)",
    "YouTube Shorts (1080x1920)",
    "Instagram Story (1080x1920)",
    "Instagram Post (1080x1080)",
    "Instagram Landscape (1920x1080)",
    "Instagram Portrait (1080x1350)",
    "VK Clip (1080x1920)",
    "Telegram Story (1080x1920)",
    "Telegram Post (1280x720)",
    "YouTube (1920x1080)",
    "YouTube Vertical (1080x1920)",
    "Facebook Story (1080x1920)",
    "Facebook Post (1200x630)",
    "Twitter Post (1600x900)",
    "Twitter Portrait (1080x1350)",
    "Snapchat (1080x1920)",
    "Pinterest (1000x1500)"
]


class DropListWidget(QListWidget):
    files_dropped = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            added = False
            for url in event.mimeData().urls():
                fp = url.toLocalFile()
                if os.path.isdir(fp):
                    for v in find_videos_in_folder(fp):
                        if is_video_file(v) and not self.is_already_added(v):
                            it = QListWidgetItem(v)
                            it.setData(Qt.UserRole, v)
                            self.addItem(it)
                            added = True
                else:
                    if (is_video_file(fp) or fp.lower().endswith('.gif')) and not self.is_already_added(fp):
                        it = QListWidgetItem(fp)
                        it.setData(Qt.UserRole, fp)
                        self.addItem(it)
                        added = True
            if added:
                self.files_dropped.emit()
        else:
            event.ignore()

    def is_already_added(self, file_path):
        return any(self.item(i).data(Qt.UserRole) == file_path for i in range(self.count()))


class MainProcessingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()

    def init_ui(self):
        self.ly = QHBoxLayout()
        self.ly.setContentsMargins(15, 15, 15, 15)
        self.ly.setSpacing(15)
        self.setLayout(self.ly)

        self.left_panel = QVBoxLayout()
        self.left_panel.setSpacing(10)
        add_layout = QHBoxLayout()
        btn_add = QPushButton("Добавить видео/GIF")
        btn_folder = QPushButton("Добавить папку")
        btn_clear = QPushButton("Очистить список")
        add_layout.addWidget(btn_add)
        add_layout.addWidget(btn_folder)
        add_layout.addWidget(btn_clear)
        self.left_panel.addLayout(add_layout)

        self.video_list_widget = DropListWidget(parent=self)
        self.video_list_widget.customContextMenuRequested.connect(self.on_list_menu)
        self.left_panel.addWidget(self.video_list_widget)

        dnd_label = QLabel("Перетащите файлы или папки сюда")
        dnd_label.setAlignment(Qt.AlignCenter)
        dnd_label.setStyleSheet("color: gray; font-style: italic;")
        self.left_panel.addWidget(dnd_label)

        self.ly.addLayout(self.left_panel, 3)

        self.right_panel = QVBoxLayout()
        self.right_panel.setSpacing(10)

        common = QGroupBox("Общие настройки")
        cl = QVBoxLayout()
        common.setLayout(cl)
        sm_layout = QHBoxLayout()
        self.strip_meta_checkbox = QCheckBox("Очистить метаданные")
        self.strip_meta_checkbox.setChecked(True)
        sm_layout.addWidget(self.strip_meta_checkbox)
        sm_layout.addStretch()
        self.style_label = QLabel("Стиль:")
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Light", "Dark", "Lolz"]) 
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        sm_layout.addWidget(self.style_label)
        sm_layout.addWidget(self.style_combo)
        cl.addLayout(sm_layout)
        self.right_panel.addWidget(common)

        fmt_group = QGroupBox("Формат вывода")
        fmt_layout = QVBoxLayout()
        fmt_group.setLayout(fmt_layout)
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(OUTPUT_FORMATS)
        self.output_format_combo.currentTextChanged.connect(self.on_output_format_changed)
        fmt_layout.addWidget(QLabel("Формат:"))
        fmt_layout.addWidget(self.output_format_combo)
        self.blur_background_checkbox = QCheckBox("Размыть фон")
        self.blur_background_checkbox.setToolTip("Заполняет черные полосы размытой версией видео (только для Reels)")
        self.blur_background_checkbox.setEnabled(False)
        fmt_layout.addWidget(self.blur_background_checkbox)
        self.right_panel.addWidget(fmt_group)

        filter_group = QGroupBox("Фильтры")
        fl = QVBoxLayout()
        filter_group.setLayout(fl)
        self.filter_list = QListWidget()
        self.filter_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for fn in FILTERS:
            self.filter_list.addItem(fn)
        self.filter_list.setFixedHeight(120)
        fl.addWidget(QLabel("Выберите фильтры (можно несколько через Ctrl/Shift):"))
        fl.addWidget(self.filter_list)
        self.right_panel.addWidget(filter_group)

        zoom_group = QGroupBox("Zoom (приближение)")
        zg = QVBoxLayout()
        zoom_group.setLayout(zg)
        zm_layout = QHBoxLayout()
        self.zoom_static_radio = QRadioButton("Статическое (%):")
        self.zoom_dynamic_radio = QRadioButton("Диапазон (%):")
        self.zoom_static_radio.setChecked(True)
        zb = QButtonGroup()
        zb.addButton(self.zoom_static_radio)
        zb.addButton(self.zoom_dynamic_radio)
        zb.buttonClicked.connect(self.on_zoom_mode_changed)
        zm_layout.addWidget(self.zoom_static_radio)
        zm_layout.addWidget(self.zoom_dynamic_radio)
        zg.addLayout(zm_layout)

        self.zoom_static_widget = QWidget()
        zs_l = QHBoxLayout()
        self.zoom_static_widget.setLayout(zs_l)
        self.zoom_static_spin = QSpinBox()
        self.zoom_static_spin.setRange(50, 300)
        self.zoom_static_spin.setValue(100)
        self.zoom_static_spin.setFixedWidth(80)
        zs_l.addWidget(self.zoom_static_spin)
        zs_l.addStretch()
        zg.addWidget(self.zoom_static_widget)

        self.zoom_dynamic_widget = QWidget()
        zd_l = QHBoxLayout()
        self.zoom_dynamic_widget.setLayout(zd_l)
        self.zoom_min_spin = QSpinBox()
        self.zoom_min_spin.setRange(50, 300)
        self.zoom_min_spin.setValue(80)
        self.zoom_max_spin = QSpinBox()
        self.zoom_max_spin.setRange(50, 300)
        self.zoom_max_spin.setValue(120)
        zd_l.addWidget(QLabel("Мин:"))
        zd_l.addWidget(self.zoom_min_spin)
        zd_l.addWidget(QLabel("Макс:"))
        zd_l.addWidget(self.zoom_max_spin)
        zd_l.addStretch()
        zg.addWidget(self.zoom_dynamic_widget)
        self.zoom_dynamic_widget.setVisible(False)
        self.right_panel.addWidget(zoom_group)

        speed_group = QGroupBox("Скорость")
        sg = QVBoxLayout()
        speed_group.setLayout(sg)
        sp_layout = QHBoxLayout()
        self.speed_static_radio = QRadioButton("Статическое (%):")
        self.speed_dynamic_radio = QRadioButton("Диапазон (%):")
        self.speed_static_radio.setChecked(True)
        sb = QButtonGroup()
        sb.addButton(self.speed_static_radio)
        sb.addButton(self.speed_dynamic_radio)
        sb.buttonClicked.connect(self.on_speed_mode_changed)
        sp_layout.addWidget(self.speed_static_radio)
        sp_layout.addWidget(self.speed_dynamic_radio)
        sg.addLayout(sp_layout)

        self.speed_static_widget = QWidget()
        ss_l = QHBoxLayout()
        self.speed_static_widget.setLayout(ss_l)
        self.speed_static_spin = QSpinBox()
        self.speed_static_spin.setRange(50, 200)
        self.speed_static_spin.setValue(100)
        self.speed_static_spin.setFixedWidth(80)
        ss_l.addWidget(self.speed_static_spin)
        ss_l.addStretch()
        sg.addWidget(self.speed_static_widget)

        self.speed_dynamic_widget = QWidget()
        sd_l = QHBoxLayout()
        self.speed_dynamic_widget.setLayout(sd_l)
        self.speed_min_spin = QSpinBox()
        self.speed_min_spin.setRange(50, 200)
        self.speed_min_spin.setValue(90)
        self.speed_max_spin = QSpinBox()
        self.speed_max_spin.setRange(50, 200)
        self.speed_max_spin.setValue(110)
        sd_l.addWidget(QLabel("Мин:"))
        sd_l.addWidget(self.speed_min_spin)
        sd_l.addWidget(QLabel("Макс:"))
        sd_l.addWidget(self.speed_max_spin)
        sd_l.addStretch()
        sg.addWidget(self.speed_dynamic_widget)
        self.speed_dynamic_widget.setVisible(False)
        self.right_panel.addWidget(speed_group)

        overlay_group = QGroupBox("Наложение файла (картинка/GIF)")
        og = QVBoxLayout()
        overlay_group.setLayout(og)
        row_ol = QHBoxLayout()
        self.overlay_path = QLineEdit()
        self.overlay_path.setPlaceholderText("Путь к файлу PNG, JPG, GIF...")
        btn_ol = QPushButton("Обзор...")
        btn_clear_ol = QPushButton("X")
        btn_clear_ol.setFixedWidth(30)
        btn_clear_ol.setToolTip("Очистить поле наложения")
        row_ol.addWidget(QLabel("Файл:"))
        row_ol.addWidget(self.overlay_path)
        row_ol.addWidget(btn_ol)
        row_ol.addWidget(btn_clear_ol)
        og.addLayout(row_ol)
        row_pos = QHBoxLayout()
        row_pos.addWidget(QLabel("Расположение:"))
        self.overlay_pos_combo = QComboBox()
        for pos in OVERLAY_POSITIONS:
            self.overlay_pos_combo.addItem(pos)
        self.overlay_pos_combo.setCurrentText("Середина-Центр")
        row_pos.addWidget(self.overlay_pos_combo)
        row_pos.addStretch()
        og.addLayout(row_pos)
        self.right_panel.addWidget(overlay_group)

        mute_group = QGroupBox("Аудио")
        mg = QVBoxLayout()
        mute_group.setLayout(mg)
        self.mute_checkbox = QCheckBox("Удалить звук из видео")
        mg.addWidget(self.mute_checkbox)
        self.right_panel.addWidget(mute_group)

        self.process_button = QPushButton("🚀 Обработать")
        self.process_button.setFixedHeight(40)
        self.right_panel.addWidget(self.process_button)

        self.progress_label = QLabel("")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray;")

        pl = QHBoxLayout()
        pl.addWidget(self.progress_label)
        pl.addWidget(self.progress_bar, 1)
        self.right_panel.addLayout(pl)
        self.right_panel.addWidget(self.status_label)
        self.right_panel.addStretch()
        self.ly.addLayout(self.right_panel, 4)

        btn_add.clicked.connect(self.on_add_files)
        btn_folder.clicked.connect(self.on_add_folder)
        btn_clear.clicked.connect(self.on_clear_list)
        btn_ol.clicked.connect(self.on_select_overlay)
        btn_clear_ol.clicked.connect(lambda: self.overlay_path.clear())

        self.on_output_format_changed(self.output_format_combo.currentText())
        self.on_zoom_mode_changed()
        self.on_speed_mode_changed()
        self.video_list_widget.files_dropped.connect(self.refresh_video_list_display)

    def on_output_format_changed(self, format_text):
        is_reels = (format_text == REELS_FORMAT_NAME)
        self.blur_background_checkbox.setEnabled(is_reels)
        if not is_reels:
            self.blur_background_checkbox.setChecked(False)

    def on_list_menu(self, pos: QPoint):
        menu = QMenu()
        act_del = menu.addAction("Удалить выделенное")
        act_clear = menu.addAction("Очистить список")
        chosen = menu.exec_(self.video_list_widget.viewport().mapToGlobal(pos))
        if chosen == act_del:
            for it in reversed(self.video_list_widget.selectedItems()):
                self.video_list_widget.takeItem(self.video_list_widget.row(it))
            self.refresh_video_list_display()
        elif chosen == act_clear:
            self.on_clear_list()

    def on_clear_list(self):
        self.video_list_widget.clear()
        self.refresh_video_list_display()

    def on_select_overlay(self):
        fs, _ = QFileDialog.getOpenFileNames(
            self, "Выберите файл для наложения (PNG, JPG, GIF)",
            "", "Файлы наложения (*.png *.jpg *.jpeg *.bmp *.gif);;Все файлы (*)"
        )
        if fs:
            self.overlay_path.setText(fs[0])

    def on_add_files(self):
        fs, _ = QFileDialog.getOpenFileNames(
            self, "Выберите видео или GIF", "",
            "Видео и GIF (*.mp4 *.mov *.avi *.mkv *.flv *.wmv *.gif);;Все файлы (*)"
        )
        if not fs:
            return
        added = False
        for f in fs:
            if (is_video_file(f) or f.lower().endswith('.gif')) and not self.video_list_widget.is_already_added(f):
                it = QListWidgetItem(f)
                it.setData(Qt.UserRole, f)
                self.video_list_widget.addItem(it)
                added = True
        if added:
            self.refresh_video_list_display()

    def on_add_folder(self):
        fol = QFileDialog.getExistingDirectory(self, "Выберите папку", "")
        if not fol:
            return
        vs = find_videos_in_folder(fol, include_gifs=True)
        added = False
        for v in vs:
            if not self.video_list_widget.is_already_added(v):
                it = QListWidgetItem(v)
                it.setData(Qt.UserRole, v)
                self.video_list_widget.addItem(it)
                added = True
        if added:
            self.refresh_video_list_display()

    def refresh_video_list_display(self):
        for i in range(self.video_list_widget.count()):
            it = self.video_list_widget.item(i)
            f = it.data(Qt.UserRole)
            base = os.path.basename(f)
            it.setText(f"{i + 1}. {base}")

    def on_zoom_mode_changed(self):
        dyn = self.zoom_dynamic_radio.isChecked()
        self.zoom_static_widget.setVisible(not dyn)
        self.zoom_dynamic_widget.setVisible(dyn)

    def on_speed_mode_changed(self):
        dyn = self.speed_dynamic_radio.isChecked()
        self.speed_static_widget.setVisible(not dyn)
        self.speed_dynamic_widget.setVisible(dyn)

    def on_style_changed(self, style_name: str):
        if self.parent_window:
            self.parent_window.apply_stylesheet(style_name.lower())
        else:
            print("Warning: Cannot apply style, parent window not found.")


class VideoUnicApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Uniqueizer | @oxd5f")
        self.resize(1100, 750)
        script_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(script_dir, '..', 'resources', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"Warning: Icon not found at {icon_path}")
        self.main_widget = MainProcessingWidget(parent=self)
        self.setCentralWidget(self.main_widget)
        self.apply_stylesheet("light")
        self.main_widget.process_button.clicked.connect(self.start_processing)
        self.thread = None

    def apply_stylesheet(self, mode):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        base_path = os.path.join(script_dir, '..', 'resources')
        if mode == "lolz":
            fname = "lolz_theme.qss"
        else:
            fname = f"styles_{mode}.qss"
        path = os.path.join(base_path, fname)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
            except Exception as e:
                print(f"Error reading stylesheet {path}: {e}")
                self.setStyleSheet("")
        else:
            print(f"Stylesheet not found: {path}")
            self.setStyleSheet("")

    def start_processing(self):
        video_files = [self.main_widget.video_list_widget.item(i).data(Qt.UserRole)
                       for i in range(self.main_widget.video_list_widget.count())]
        if not video_files:
            QMessageBox.warning(self, "Нет файлов", "Добавьте хотя бы один видео или GIF файл.")
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения результатов")
        if not out_dir:
            return
        strip_metadata = self.main_widget.strip_meta_checkbox.isChecked()
        output_format = self.main_widget.output_format_combo.currentText()
        blur_background = (self.main_widget.blur_background_checkbox.isChecked()
                           if output_format == REELS_FORMAT_NAME else False)
        selected_filters = [item.text() for item in self.main_widget.filter_list.selectedItems()]

        zoom_mode = "dynamic" if self.zoom_dynamic_radio.isChecked() else "static"
        zoom_min = (self.zoom_min_spin.value() if zoom_mode == "dynamic"
                    else self.zoom_static_spin.value())
        zoom_max = (self.zoom_max_spin.value() if zoom_mode == "dynamic"
                    else self.zoom_static_spin.value())

        speed_mode = "dynamic" if self.speed_dynamic_radio.isChecked() else "static"
        speed_min = (self.speed_min_spin.value() if speed_mode == "dynamic"
                     else self.speed_static_spin.value())
        speed_max = (self.speed_max_spin.value() if speed_mode == "dynamic"
                     else self.speed_static_spin.value())

        overlay_file = self.main_widget.overlay_path.text().strip() or None
        if overlay_file and not os.path.exists(overlay_file):
            QMessageBox.warning(self, "Файл не найден", f"Файл наложения не найден:\n{overlay_file}")
            overlay_file = None

        overlay_pos = self.main_widget.overlay_pos_combo.currentText()
        mute_audio = self.main_widget.mute_checkbox.isChecked()

        if zoom_mode == "dynamic" and zoom_min > zoom_max:
            QMessageBox.warning(self, "Ошибка Zoom", "Минимальный Zoom не может быть больше максимального.")
            return
        if speed_mode == "dynamic" and speed_min > speed_max:
            QMessageBox.warning(self, "Ошибка Скорости", "Минимальная скорость не может быть больше максимальной.")
            return

        self.thread = Worker(
            files=video_files,
            filters=selected_filters,
            zoom_mode=zoom_mode, zoom_min=zoom_min, zoom_max=zoom_max,
            speed_mode=speed_mode, speed_min=speed_min, speed_max=speed_max,
            overlay_file=overlay_file, overlay_pos=overlay_pos,
            out_dir=out_dir, mute_audio=mute_audio,
            output_format=output_format, blur_background=blur_background,
            strip_metadata=strip_metadata
        )

        self.thread.progress.connect(self.on_prog)
        self.thread.file_processing.connect(self.on_file_processing)
        self.thread.finished.connect(self.on_done)
        self.thread.error.connect(self.on_err)

        self.main_widget.progress_bar.setValue(0)
        self.main_widget.progress_label.setText(f"0 / {len(video_files)}")
        self.main_widget.status_label.setText("Подготовка...")
        self.main_widget.process_button.setEnabled(False)

        self.thread.start()

    def on_prog(self, done, total):
        prc = int(done * 100 / total) if total else 0
        self.main_widget.progress_bar.setValue(prc)
        self.main_widget.progress_label.setText(f"{done} / {total}")
        self.main_widget.progress_bar.setFormat(f"%p% ({done}/{total})")

    def on_file_processing(self, fname):
        try:
            fm = QFontMetrics(self.main_widget.status_label.font())
            el = fm.elidedText(f"Обрабатываю: {fname}", Qt.ElideMiddle,
                               self.main_widget.status_label.width() - 20)
            self.main_widget.status_label.setText(el)
        except Exception:
            self.main_widget.status_label.setText(f"Обрабатываю: ...{fname[-30:]}")

    def on_done(self):
        QMessageBox.information(self, "Готово", "Обработка успешно завершена!")
        self.main_widget.progress_label.setText("Готово")
        self.main_widget.progress_bar.setValue(100)
        self.main_widget.progress_bar.setFormat("100%")
        self.main_widget.status_label.setText("")
        self.main_widget.process_button.setEnabled(True)

    def on_err(self, msg):
        title = "Ошибка обработки"
        current = self.main_widget.status_label.text()
        if current.startswith("Обрабатываю:"):
            title = "Ошибка при обработке файла"
            msg = f"{current}\n\n{msg}"
        QMessageBox.critical(self, title, f"Произошла ошибка:\n\n{msg}")
        self.main_widget.progress_label.setText("Ошибка")
        self.main_widget.status_label.setText("Прервано из-за ошибки")
        self.main_widget.process_button.setEnabled(True)

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            reply = QMessageBox.question(
                self, 'Подтверждение',
                "Идет обработка видео. Вы уверены, что хотите выйти?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                try:
                    self.thread.quit()
                    self.thread.wait(1000)
                    if self.thread.isRunning():
                        self.thread.terminate()
                        self.thread.wait(500)
                        print("Warning: Worker thread terminated forcibly.")
                except Exception as e:
                    print(f"Error stopping worker thread: {e}")
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
