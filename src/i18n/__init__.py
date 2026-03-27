"""多语言支持模块"""
import json
import os
import locale

# 内置翻译
TRANSLATIONS = {
    "zh_CN": {
        # 窗口标题
        "app_name": "番茄钟",
        # 侧边栏
        "nav_focus": "专注",
        "nav_tasks": "任务",
        "nav_notes": "笔记",
        "nav_stats": "统计",
        "nav_settings": "设置",
        # 计时器
        "ready": "准备开始",
        "focus": "正在专注",
        "break": "正在休息",
        "long_break": "正在长休息",
        "abandoned": "已放弃",
        "start_focus": "开始专注",
        "abandon_focus": "放弃专注",
        # 任务
        "add_task": "添加任务...",
        "task_matrix": "任务矩阵 (四象限)",
        "q1": "🔥 重要且紧急",
        "q2": "📅 重要不紧急",
        "q3": "⚡ 紧急不重要",
        "q4": "☕ 不重要不紧急",
        "completed": "✅ 已完成任务",
        # 笔记
        "new_note": "新建笔记",
        "search_note": "🔍 搜索笔记标题或内容...",
        "edit_note": "笔记编辑",
        "title": "标题",
        "content": "正文",
        "save": "保存笔记",
        "daily_quote": "每日一句",
        "getting_quote": "正在获取灵感...",
        # 设置
        "settings_timer": "计时器",
        "settings_notify": "通知",
        "settings_system": "系统",
        "settings_about": "关于",
        "focus_duration": "专注时长",
        "focus_duration_desc": "每轮专注工作时长",
        "short_break": "短休息",
        "short_break_desc": "专注轮结束后的短暂休息",
        "long_break": "长休息",
        "long_break_desc": "每隔若干轮后的长休息时长",
        "long_break_interval": "长休息间隔",
        "long_break_interval_desc": "每隔几轮专注后触发长休息",
        "auto_hide": "自动隐藏侧边栏",
        "auto_hide_desc": "专注开始时折叠侧边栏",
        "auto_start": "自动开始下一阶段",
        "auto_start_desc": "阶段结束后自动开始休息/工作",
        "sound": "开启提示音",
        "sound_desc": "阶段结束时播放提示音",
        "tick_work": "工作时段滴答声",
        "tick_break": "休息时段滴答声",
        "about": "关于",
        "about_app": "FanqieClock · 番茄钟",
        "about_author": "作者：饿梦",
        "sponsor": "我要赞助 ❤️",
        # 统计
        "total_pomos": "累计番茄",
        "focus_time": "专注时长",
        "total_days": "累计天数",
        "interruptions": "打断次数",
        "today_stats": "今日专注",
        "recent_records": "最近记录",
        "export_pdf": "导出报告 (PDF)",
        "history_7days": "近 7 天番茄数",
        "heatmap": "历史打卡热力图",
        # 消息
        "confirm_abandon": "放弃当前番茄钟？",
        "confirm_abandon_desc": "根据番茄工作法，番茄钟一旦开始就不应暂停。确定要放弃当前这一组计时吗？",
        "confirm_delete": "确认删除",
        "confirm_delete_desc": "您确定要删除这条笔记吗？此操作无法撤销。",
        # 快捷键
        "global_hotkey": "[快捷键] 全局热键已注册：空格=开始/暂停",
    },
    "en_US": {
        # Window title
        "app_name": "Pomodoro Clock",
        # Navigation
        "nav_focus": "Focus",
        "nav_tasks": "Tasks",
        "nav_notes": "Notes",
        "nav_stats": "Stats",
        "nav_settings": "Settings",
        # Timer
        "ready": "Ready",
        "focus": "Focusing",
        "break": "Short Break",
        "long_break": "Long Break",
        "abandoned": "Abandoned",
        "start_focus": "Start Focus",
        "abandon_focus": "Abandon",
        # Tasks
        "add_task": "Add task...",
        "task_matrix": "Task Matrix (Eisenhower)",
        "q1": "🔥 Urgent & Important",
        "q2": "📅 Important",
        "q3": "⚡ Urgent",
        "q4": "☕ Neither",
        "completed": "✅ Completed",
        # Notes
        "new_note": "New Note",
        "search_note": "🔍 Search notes...",
        "edit_note": "Edit Note",
        "title": "Title",
        "content": "Content",
        "save": "Save",
        "daily_quote": "Daily Quote",
        "getting_quote": "Getting inspiration...",
        # Settings
        "settings_timer": "Timer",
        "settings_notify": "Notifications",
        "settings_system": "System",
        "settings_about": "About",
        "focus_duration": "Focus Duration",
        "focus_duration_desc": "Work session length",
        "short_break": "Short Break",
        "short_break_desc": "Rest after focus session",
        "long_break": "Long Break",
        "long_break_desc": "Extended rest after multiple sessions",
        "long_break_interval": "Long Break Interval",
        "long_break_interval_desc": "Sessions before long break",
        "auto_hide": "Auto-hide Sidebar",
        "auto_hide_desc": "Collapse sidebar when focusing",
        "auto_start": "Auto-start Next Phase",
        "auto_start_desc": "Automatically start break/focus",
        "sound": "Sound Enabled",
        "sound_desc": "Play sound when session ends",
        "tick_work": "Work Tick Sound",
        "tick_break": "Break Tick Sound",
        "about": "About",
        "about_app": "FanqieClock · Pomodoro Timer",
        "about_author": "By: Hungerdream",
        "sponsor": "Sponsor ❤️",
        # Stats
        "total_pomos": "Total Pomodoros",
        "focus_time": "Focus Time",
        "total_days": "Total Days",
        "interruptions": "Interruptions",
        "today_stats": "Today",
        "recent_records": "Recent Records",
        "export_pdf": "Export PDF",
        "history_7days": "Last 7 Days",
        "heatmap": "Activity Heatmap",
        # Messages
        "confirm_abandon": "Abandon Pomodoro?",
        "confirm_abandon_desc": "Are you sure you want to abandon this session?",
        "confirm_delete": "Confirm Delete",
        "confirm_delete_desc": "Are you sure you want to delete this note? This cannot be undone.",
        # Hotkey
        "global_hotkey": "[Hotkey] Global hotkey registered: Space=start/pause",
    },
    "zh_TW": {
        "app_name": "番茄鐘",
        "nav_focus": "專注",
        "nav_tasks": "任務",
        "nav_notes": "筆記",
        "nav_stats": "統計",
        "nav_settings": "設定",
        "ready": "準備開始",
        "focus": "正在專注",
        "break": "正在休息",
        "long_break": "正在長休息",
        "abandoned": "已放棄",
        "start_focus": "開始專注",
        "abandon_focus": "放棄專注",
        "add_task": "添加任務...",
        "task_matrix": "任務矩陣 (四象限)",
        "new_note": "新建筆記",
        "search_note": "🔍 搜尋筆記標題或內容...",
        "edit_note": "筆記編輯",
        "title": "標題",
        "content": "內容",
        "save": "儲存筆記",
        "daily_quote": "每日一句",
        "getting_quote": "正在獲取靈感...",
        "total_pomos": "累計番茄",
        "focus_time": "專注時長",
        "total_days": "累計天數",
        "interruptions": "打斷次數",
        "today_stats": "今日專注",
        "export_pdf": "匯出報告 (PDF)",
        "history_7days": "近 7 天番茄數",
        "heatmap": "歷史打卡熱力圖",
        "confirm_delete": "確認刪除",
        "confirm_delete_desc": "您確定要刪除這條筆記嗎？此操作無法撤銷。",
        "about_app": "FanqieClock · 番茄鐘",
        "about_author": "作者：餓夢",
        "sponsor": "我要贊助 ❤️",
    },
}


class I18n:
    """国际化管理器"""
    
    def __init__(self):
        self.current_lang = "zh_CN"
        self._detect_language()
    
    def _detect_language(self):
        """检测系统语言"""
        try:
            # 获取系统语言
            system_lang = locale.getdefaultlocale()[0]
            if system_lang:
                system_lang = system_lang.replace('-', '_')
                
            # 映射系统语言到支持的语言
            lang_map = {
                'zh_CN': 'zh_CN',
                'zh_TW': 'zh_TW',
                'zh_HK': 'zh_TW',
                'en_US': 'en_US',
                'en_GB': 'en_US',
                'en_AU': 'en_US',
            }
            
            for key, value in lang_map.items():
                if system_lang and system_lang.startswith(key):
                    self.current_lang = value
                    return
            
            # 默认英文
            if not system_lang or not system_lang.startswith('zh'):
                self.current_lang = 'en_US'
                
        except Exception:
            pass
    
    def set_language(self, lang):
        """设置语言"""
        if lang in TRANSLATIONS:
            self.current_lang = lang
    
    def get_language(self):
        """获取当前语言代码"""
        return self.current_lang
    
    def t(self, key, **kwargs):
        """翻译文本"""
        texts = TRANSLATIONS.get(self.current_lang, TRANSLATIONS['zh_CN'])
        text = texts.get(key, TRANSLATIONS['zh_CN'].get(key, key))
        
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text
    
    def get_all_languages(self):
        """获取所有支持的语言"""
        return {
            'zh_CN': '简体中文',
            'zh_TW': '繁體中文',
            'en_US': 'English',
        }


# 全局实例
_i18n = None

def get_i18n():
    """获取 i18n 实例"""
    global _i18n
    if _i18n is None:
        _i18n = I18n()
    return _i18n

def t(key, **kwargs):
    """快捷翻译函数"""
    return get_i18n().t(key, **kwargs)
