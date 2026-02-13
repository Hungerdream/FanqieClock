from PyQt6.QtCore import QThread, pyqtSignal
import requests

class QuoteWorker(QThread):
    quote_fetched = pyqtSignal(str, str) # content, author

    def run(self):
        try:
            # Hitokoto API (c=d for literature, c=i for poetry/inspiration, c=k for philosophy)
            response = requests.get("https://v1.hitokoto.cn/?c=i&c=d&c=k", timeout=5)
            if response.status_code == 200:
                data = response.json()
                content = data.get("hitokoto", "Loading...")
                from_who = data.get("from_who")
                from_source = data.get("from")
                
                author = ""
                if from_who and from_source:
                    author = f"—— {from_who} 《{from_source}》"
                elif from_who:
                    author = f"—— {from_who}"
                elif from_source:
                    author = f"—— 《{from_source}》"
                else:
                    author = "—— 佚名"
                    
                self.quote_fetched.emit(content, author)
            else:
                self.quote_fetched.emit("生活原本沉闷，但跑起来就有风。", "—— 佚名")
        except Exception:
            self.quote_fetched.emit("生活原本沉闷，但跑起来就有风。", "—— 佚名")
