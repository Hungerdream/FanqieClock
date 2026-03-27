"""笔记页面 - 笔记管理功能"""
import uuid
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QTextEdit, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QDialog, QFrame, QMessageBox, QMenu)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from utils import get_resource_path


class NotesPage(QWidget):
    """笔记管理页面"""
    
    quote_label: QLabel
    quote_author: QLabel
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Daily Quote Card
        quote_card = QFrame()
        quote_card.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border-radius: 15px;
                border: 1px solid #EEE;
            }
        """)
        quote_layout = QVBoxLayout(quote_card)
        quote_layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("每日一句")
        title.setStyleSheet("font-size: 14px; color: #999; font-weight: bold; margin-bottom: 5px;")
        
        self.quote_label = QLabel("正在获取灵感...")
        self.quote_label.setWordWrap(True)
        self.quote_label.setStyleSheet("font-size: 18px; color: #333; font-family: 'Kaiti', 'Microsoft YaHei'; line-height: 1.5;")
        
        self.quote_author = QLabel("")
        self.quote_author.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.quote_author.setStyleSheet("font-size: 14px; color: #666; margin-top: 10px;")
        
        quote_layout.addWidget(title)
        quote_layout.addWidget(self.quote_label)
        quote_layout.addWidget(self.quote_author)
        
        layout.addWidget(quote_card)
        layout.addSpacing(30)
        
        # Header: New, Search, Filter
        header = QHBoxLayout()
        self.new_note_btn = QPushButton("新建笔记")
        self.new_note_btn.setObjectName("PrimaryButton")
        self.new_note_btn.clicked.connect(self.show_note_dialog)
        
        self.note_search = QLineEdit()
        self.note_search.setPlaceholderText("🔍 搜索笔记标题或内容...")
        self.note_search.textChanged.connect(self.filter_notes)
        
        header.addWidget(self.new_note_btn)
        header.addSpacing(20)
        header.addWidget(self.note_search, 1)
        
        # Notes Table
        self.notes_table = QTableWidget(0, 2)
        self.notes_table.setObjectName("NotesTable")
        self.notes_table.setHorizontalHeaderLabels(["标题", "摘要"])
        self.notes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.notes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.notes_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.notes_table.verticalHeader().setVisible(False)
        self.notes_table.setShowGrid(False)
        self.notes_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.notes_table.itemDoubleClicked.connect(self.edit_note)
        
        # Context Menu
        self.notes_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.notes_table.customContextMenuRequested.connect(self.show_note_context_menu)
        
        layout.addLayout(header)
        layout.addWidget(self.notes_table)
    
    def update_quote(self, content, author):
        """更新每日一句"""
        if hasattr(self, 'quote_label'):
            self.quote_label.setText(content)
        if hasattr(self, 'quote_author'):
            self.quote_author.setText(author)
    
    def refresh_table(self, filter_text=""):
        """刷新笔记表格"""
        notes = self.data_manager.data.get("notes", [])
        self.notes_table.setRowCount(0)
        
        for note in notes:
            # Ensure note has an id
            if 'id' not in note:
                note['id'] = str(uuid.uuid4())
            
            # Filtering logic
            if filter_text and filter_text.lower() not in note['title'].lower() and filter_text.lower() not in note['content'].lower():
                continue
                
            self.notes_table.insertRow(self.notes_table.rowCount())
            row = self.notes_table.rowCount() - 1
            
            # Title item - store note id instead of index
            title_item = QTableWidgetItem(note['title'])
            title_item.setData(Qt.ItemDataRole.UserRole, note['id'])
            self.notes_table.setItem(row, 0, title_item)
            
            # Summary item
            content_summary = note['content'][:60].replace("\n", " ")
            if len(note['content']) > 60: 
                content_summary += "..."
            self.notes_table.setItem(row, 1, QTableWidgetItem(content_summary))
    
    def show_note_context_menu(self, pos):
        """显示笔记右键菜单"""
        item = self.notes_table.itemAt(pos)
        if item:
            row = item.row()
            # Select the row first
            self.notes_table.selectRow(row)
            
            # Create menu
            menu = QMenu(self.notes_table)
            
            delete_action = QAction("删除笔记", self)
            delete_action.setIcon(QIcon(get_resource_path("resources/icon_delete_new.svg")))
            # Retrieve note id from the item (stored via UserRole)
            title_item = self.notes_table.item(row, 0)
            note_id = title_item.data(Qt.ItemDataRole.UserRole)
            
            delete_action.triggered.connect(lambda: self.delete_note(note_id))
            
            menu.addAction(delete_action)
            menu.exec(self.notes_table.mapToGlobal(pos))
    
    def show_note_dialog(self, note_id=None):
        """显示笔记编辑对话框"""
        # Handle signal sending boolean (False) when clicked
        if isinstance(note_id, bool):
            note_id = None
            
        notes = self.data_manager.data.get("notes", [])
        note_data = None
        if note_id is not None:
            for note in notes:
                if note.get('id') == note_id:
                    note_data = note
                    break
        
        dialog = QDialog(self)
        dialog.setWindowTitle("笔记编辑" if note_data else "新建笔记")
        dialog.setMinimumSize(600, 500)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        
        title_edit = QLineEdit()
        title_edit.setPlaceholderText("💡 这里写标题...")
        title_edit.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        
        content_edit = QTextEdit()
        content_edit.setPlaceholderText("✍️ 记录此刻的想法、灵感或复盘...")
        content_edit.setStyleSheet("font-size: 15px; line-height: 1.5;")
        
        if note_data:
            title_edit.setText(note_data['title'])
            content_edit.setPlainText(note_data['content'])
            
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        save_btn = QPushButton("保存笔记")
        save_btn.setObjectName("PrimaryButton")
        save_btn.setMinimumWidth(120)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        def save():
            new_note = {
                "id": note_id if note_id else str(uuid.uuid4()),
                "title": title_edit.text() or "未命名笔记",
                "content": content_edit.toPlainText(),
                "date": QDate.currentDate().toString(Qt.DateFormat.ISODate)
            }
            if note_id:
                # Update existing note by id
                for i, note in enumerate(notes):
                    if note.get('id') == note_id:
                        notes[i] = new_note
                        break
            else:
                notes.insert(0, new_note)
            
            self.data_manager.update_notes(notes)
            self.refresh_table()
            dialog.accept()
            
        save_btn.clicked.connect(save)
        cancel_btn.clicked.connect(dialog.reject)
        
        layout.addWidget(QLabel("标题"))
        layout.addWidget(title_edit)
        layout.addWidget(QLabel("正文"))
        layout.addWidget(content_edit)
        layout.addLayout(btn_layout)
        dialog.exec()
    
    def edit_note(self, item):
        """编辑笔记"""
        # Get the title item of the row to retrieve the note id
        row = item.row()
        title_item = self.notes_table.item(row, 0)
        note_id = title_item.data(Qt.ItemDataRole.UserRole)
        self.show_note_dialog(note_id)
    
    def delete_note(self, note_id):
        """删除笔记"""
        # Confirmation Dialog
        reply = QMessageBox.question(self, '确认删除', 
                                     '您确定要删除这条笔记吗？此操作无法撤销。',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            notes = self.data_manager.data.get("notes", [])
            notes[:] = [n for n in notes if n.get('id') != note_id]
            self.data_manager.update_notes(notes)
            self.refresh_table()
    
    def filter_notes(self):
        """过滤笔记"""
        self.refresh_table(self.note_search.text())
