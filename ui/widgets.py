# ui/widgets.py
import os
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QListWidget, QAbstractItemView, QListWidgetItem
from utils.file_utils import is_video_file, find_videos_in_folder


class DropListWidget(QListWidget):
    files_dropped = pyqtSignal()

    def __init__(self, parent=None, allow_gifs: bool = True):
        super().__init__(parent)
        self.allow_gifs = allow_gifs
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
                        if is_video_file(v):
                            added |= self.add_path(v)
                elif is_video_file(fp) or (self.allow_gifs and fp.lower().endswith('.gif')):
                    added |= self.add_path(fp)
            if added:
                self.files_dropped.emit()
        else:
            event.ignore()

    def add_path(self, file_path: str) -> bool:
        """Добавляет файл, если его ещё нет в списке. Возвращает True при добавлении."""
        if self.is_already_added(file_path):
            return False
        it = QListWidgetItem(file_path)
        it.setData(Qt.UserRole, file_path)
        self.addItem(it)
        return True

    def paths(self):
        return [self.item(i).data(Qt.UserRole) for i in range(self.count())]

    def is_already_added(self, file_path):
        return any(self.item(i).data(Qt.UserRole) == file_path for i in range(self.count()))
