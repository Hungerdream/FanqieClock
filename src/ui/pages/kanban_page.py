"""看板页面 - 四象限任务管理"""
import uuid
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFrame, QGridLayout
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from ui.widgets import KanbanList


class KanbanPage(QWidget):
    """四象限看板页面"""
    
    focus_task = pyqtSignal(dict)  # 请求专注某个任务
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.kanban_cols = {}
        self.task_location = {}  # {task_id: (col_key, row_index)} for O(1) lookup
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("任务矩阵 (四象限)")
        title.setProperty("class", "KanbanTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Quadrant Grid
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        
        # Quadrant Config: (key, title, row, col, bg_color)
        quadrants = [
            ("q1", "🔥 重要且紧急", 0, 0, "#FFEBEE"),
            ("q2", "📅 重要不紧急", 0, 1, "#E3F2FD"),
            ("q3", "⚡ 紧急不重要", 1, 0, "#FFF3E0"),
            ("q4", "☕ 不重要不紧急", 1, 1, "#F3E5F5")
        ]
        
        for key, title, r, c, bg_color in quadrants:
            frame = QFrame()
            frame.setObjectName(f"Quadrant_{key}")
            frame.setStyleSheet(f"""
                #Quadrant_{key} {{
                    background-color: {bg_color};
                    border-radius: 12px;
                    border: 1px solid transparent;
                }}
            """)
            v_layout = QVBoxLayout(frame)
            v_layout.setContentsMargins(10, 10, 10, 10)
            
            header_lbl = QLabel(title)
            header_lbl.setStyleSheet("font-weight: bold; font-size: 15px; color: #555; margin-bottom: 5px;")
            v_layout.addWidget(header_lbl)
            
            # Input for this quadrant
            input_field = QLineEdit()
            input_field.setPlaceholderText("＋ 添加任务...")
            input_field.setStyleSheet("background: rgba(255,255,255,0.7); border: none; border-radius: 5px; padding: 5px;")
            # Use closure to capture key
            input_field.returnPressed.connect(lambda k=key, f=input_field: self.add_task(k, f))
            v_layout.addWidget(input_field)
            
            list_widget = KanbanList(self.data_manager, key)
            list_widget.item_deleted.connect(self.save_state)
            list_widget.order_changed.connect(self.save_state)
            list_widget.focus_task.connect(self.focus_task.emit)
            
            v_layout.addWidget(list_widget)
            self.kanban_cols[key] = list_widget
            
            grid_layout.addWidget(frame, r, c)
            
        layout.addLayout(grid_layout, 1)
        
        # Completed Section (Collapsible-like)
        comp_frame = QFrame()
        comp_frame.setStyleSheet("background-color: #FAFAFA; border-radius: 10px; border: 1px solid #EEE;")
        comp_layout = QVBoxLayout(comp_frame)
        comp_layout.setContentsMargins(10, 10, 10, 10)
        
        comp_header = QLabel("✅ 已完成任务")
        comp_header.setStyleSheet("font-weight: bold; color: #888;")
        comp_layout.addWidget(comp_header)
        
        self.completed_list = KanbanList(self.data_manager, "completed")
        self.completed_list.setMaximumHeight(150)  # Limit height
        self.completed_list.item_deleted.connect(self.save_state)
        self.completed_list.order_changed.connect(self.save_state)
        self.kanban_cols["completed"] = self.completed_list
        
        comp_layout.addWidget(self.completed_list)
        layout.addWidget(comp_frame)
    
    def add_task(self, key, input_field):
        """添加任务到指定象限"""
        text = input_field.text().strip()
        if text:
            task_data = {
                "id": str(uuid.uuid4()),
                "content": text,
                "pomodoros": 0,
                "created_at": QDate.currentDate().toString(Qt.DateFormat.ISODate)
            }
            
            self.kanban_cols[key].add_task_item(task_data)
            # Update lookup table: new task goes to the end
            row_index = self.kanban_cols[key].count() - 1
            self.task_location[task_data["id"]] = (key, row_index)
            
            input_field.clear()
            self.save_state()
    
    def save_state(self):
        """保存看板状态"""
        tasks_dict = {}
        # Rebuild task location lookup table
        self.task_location.clear()
        for key, col in self.kanban_cols.items():
            tasks = []
            for i in range(col.count()):
                item = col.item(i)
                task_data = item.data(Qt.ItemDataRole.UserRole)
                if task_data:
                    tasks.append(task_data)
                    # Update lookup table
                    if task_data.get('id'):
                        self.task_location[task_data['id']] = (key, i)
            tasks_dict[key] = tasks
        self.data_manager.update_tasks(tasks_dict)
    
    def load_data(self, tasks):
        """加载任务数据"""
        # Rebuild task location lookup table
        self.task_location.clear()
        for key, items in tasks.items():
            if key in self.kanban_cols:
                self.kanban_cols[key].clear()
                for idx, item_data in enumerate(items):
                    # item_data is a dict now
                    self.kanban_cols[key].add_task_item(item_data)
                    # Register in lookup table
                    if item_data.get('id'):
                        self.task_location[item_data['id']] = (key, idx)
    
    def update_task_pomo_count(self, task_id):
        """更新任务番茄计数"""
        # O(1) lookup using task_location table
        location = self.task_location.get(task_id)
        if not location:
            return False
        key, row_index = location
        col = self.kanban_cols.get(key)
        if not col:
            return False
        
        item = col.item(row_index)
        if not item:
            return False
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            data['pomodoros'] = data.get('pomodoros', 0) + 1
            item.setData(Qt.ItemDataRole.UserRole, data)
            # Refresh widget display
            widget = col.itemWidget(item)
            if widget:
                widget.pomo_label.setText(f"🍅 {data['pomodoros']}")
                widget.task_data = data
            self.save_state()
            return True
        return False
