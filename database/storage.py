# database/storage.py
import json
import os
from telethon import TelegramClient

class Storage:
    def __init__(self):
        self.accounts = {}
        self.targets = {}
        self.drafts = []
        self.scheduled_messages = []
        self.stats = {"sent": 0, "last_send": None}
        self.account_stats = {}
        

        os.makedirs("data", exist_ok=True)
        os.makedirs("sessions", exist_ok=True)
    
    def load_all(self):
        from config import ACCOUNTS_FILE, TARGETS_FILE, SCHEDULED_FILE, DRAFTS_FILE, STATS_FILE
        
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                accounts_data = json.load(f)
                for name, data in accounts_data.items():
                    self.accounts[name] = {
                        "api_id": data["api_id"],
                        "api_hash": data["api_hash"],
                        "phone": data.get("phone", ""),
                        "client": TelegramClient(f"sessions/{name}", data["api_id"], data["api_hash"])
                    }
        
        if os.path.exists(TARGETS_FILE):
            with open(TARGETS_FILE, 'r', encoding='utf-8') as f:
                self.targets = json.load(f)
        
        if os.path.exists(SCHEDULED_FILE):
            with open(SCHEDULED_FILE, 'r', encoding='utf-8') as f:
                self.scheduled_messages = json.load(f)
        
        if os.path.exists(DRAFTS_FILE):
            with open(DRAFTS_FILE, 'r', encoding='utf-8') as f:
                self.drafts = json.load(f)
        
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                loaded_stats = json.load(f)
                self.stats = loaded_stats.get("general", {})
                self.account_stats = loaded_stats.get("accounts", {})
    
    def save_accounts(self):
        from config import ACCOUNTS_FILE
        data = {}
        for name, acc in self.accounts.items():
            data[name] = {
                "api_id": acc["api_id"],
                "api_hash": acc["api_hash"],
                "phone": acc.get("phone", "")
            }
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def save_targets(self):
        from config import TARGETS_FILE
        with open(TARGETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.targets, f, ensure_ascii=False, indent=2)
    
    def save_scheduled(self):
        from config import SCHEDULED_FILE
        with open(SCHEDULED_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.scheduled_messages, f, ensure_ascii=False, indent=2)
    
    def save_drafts(self):
        from config import DRAFTS_FILE
        with open(DRAFTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.drafts, f, ensure_ascii=False, indent=2)
    
    def save_stats(self):
        from config import STATS_FILE
        data = {
            "general": self.stats,
            "accounts": self.account_stats
        }
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def save_all(self):
        self.save_accounts()
        self.save_targets()
        self.save_scheduled()
        self.save_drafts()
        self.save_stats()

storage = Storage()
