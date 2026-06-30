# -*- coding: utf-8 -*-
import json
import csv
import os
from datetime import datetime

class Logger:
    def __init__(self):
        self.config = self.load_config()
        # 每天啟動產生一次 session_id
        self.session_id = datetime.now().strftime("%Y%m%d")
        self.signal_file = "signal_log.csv"
        self.trade_file = "trade_log.csv"
        self.init_logs()

    def load_config(self):
        """讀取外部 config.json"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️ 找不到 config.json，系統將以空殼運行，請確認檔案位置！")
            return {}

    def init_logs(self):
        """初始化日誌檔案與完整表頭 (加入 session_id)"""
        try:
            # 初始化 Signal Log
            if not os.path.exists(self.signal_file):
                with open(self.signal_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "session_id", "time", "price", "vwap", "volume_1m", "bid_ask_ratio", 
                        "cond_a", "cond_b", "cond_c", "decision", "reject_reason"
                    ])

            # 初始化 Trade Log
            if not os.path.exists(self.trade_file):
                with open(self.trade_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "session_id", "entry_time", "symbol", "entry_reason", "vwap", "volume_1m", 
                        "bid_ask_ratio", "entry_price", "stop_loss", "take_profit",
                        "exit_time", "exit_price", "profit", "mfe", "mae", "exit_reason"
                    ])
        except Exception as e:
            print(f"🚨 Log Init Error (無法建立檔案): {e}")

    def log_signal(self, data: dict):
        """寫入每一次的訊號檢查紀錄 (防呆版)"""
        try:
            with open(self.signal_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    self.session_id,
                    data.get("time", ""),
                    data.get("price", ""),
                    data.get("vwap", ""),
                    data.get("volume_1m", ""),
                    data.get("bid_ask_ratio", ""),
                    data.get("cond_a", ""),
                    data.get("cond_b", ""),
                    data.get("cond_c", ""),
                    data.get("decision", ""),
                    data.get("reject_reason", "")
                ])
        except Exception as e:
            print(f"🚨 Log Error (Signal 寫入失敗): {e}")

    def log_trade(self, data: dict):
        """寫入完成的交易紀錄 (防呆版)"""
        try:
            with open(self.trade_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    self.session_id,
                    data.get("entry_time", ""),
                    data.get("symbol", ""),
                    data.get("entry_reason", ""),
                    data.get("vwap", ""),
                    data.get("volume_1m", ""),
                    data.get("bid_ask_ratio", ""),
                    data.get("entry_price", ""),
                    data.get("stop_loss", ""),
                    data.get("take_profit", ""),
                    data.get("exit_time", ""),
                    data.get("exit_price", ""),
                    data.get("profit", ""),
                    data.get("mfe", ""),
                    data.get("mae", ""),
                    data.get("exit_reason", "")
                ])
        except Exception as e:
            print(f"🚨 Log Error (Trade 寫入失敗): {e}")

# ==========================================
# 🚀 執行 Milestone 1 驗收測試
# ==========================================
if __name__ == "__main__":
    print("啟動 Milestone 1 驗證模組...")
    logger = Logger()
    print(f"✅ 設定檔讀取成功！ PAPER_MODE = {logger.config.get('PAPER_MODE')}")
    
    # 取得含日期的完整時間格式
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 寫入測試用 Signal 紀錄
    logger.log_signal({
        "time": current_time,
        "price": 30.15,
        "vwap": 30.08,
        "volume_1m": 420,
        "bid_ask_ratio": 1.82,
        "cond_a": True,
        "cond_b": True,
        "cond_c": False,
        "decision": "REJECT",
        "reject_reason": "NO_IGNITION"
    })
    print("✅ 測試訊號已發送至寫入佇列")

    # 寫入測試用 Trade 紀錄
    logger.log_trade({
        "entry_time": current_time,
        "symbol": "00981A",
        "entry_reason": "VWAP_BOUNCE",
        "vwap": 30.10,
        "volume_1m": 350,
        "bid_ask_ratio": 1.6,
        "entry_price": 30.10,
        "stop_loss": 29.85,
        "take_profit": 30.50,
        "exit_time": current_time,
        "exit_price": 30.32,
        "profit": 220,
        "mfe": 250,
        "mae": -50,
        "exit_reason": "TRAILING_STOP"
    })
    print("✅ 測試交易已發送至寫入佇列")
    print("🚀 請進行 4 項驗收並嘗試連續執行兩次程式！")
