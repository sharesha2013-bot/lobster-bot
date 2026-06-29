# -*- coding: utf-8 -*-
import os
import time
import requests
import traceback
from datetime import datetime

# ==============================================================================
# ⚙️ 系統設定：Unmerciful Lobster 00981A 專屬當沖自動化策略 (GitHub 專用版)
# ==============================================================================
# 恢復正確寫法：讓程式自動去讀取 GitHub Secrets 裡面的密碼！
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"
TARGET_STOCK = "00981A"
TRADE_VOLUME = 1

class LobsterTrailingStrategy:
    def __init__(self):
        self.session = requests.Session()
        self.has_position = False
        self.buy_price = 0.0
        self.highest_price = 0.0
        self.lowest_price_seen = 0.0
        self.is_falling = False
        self.day_trade_done = False
        self.open_price = 0.0
        self.is_mock_mode = False

    def send_telegram(self, text):
        """發送 Telegram 戰報"""
        if not BOT_TOKEN:
            print("⚠️ 未抓取到 BOT_TOKEN (GitHub Secrets 可能未設定)，顯示於終端機：\n" + text)
            return
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        try:
            self.session.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
        except Exception as e:
            print(f"TG 推播失敗: {e}")

    def get_tick_size(self, price):
        """台股檔位計算"""
        if price < 50: return 0.05
        return 0.1

    def check_rebound_signal(self, current_price, current_volume):
        """🎯 進場大腦：判斷是否跌深反彈且爆量"""
        if self.day_trade_done or self.has_position: return False
        
        if self.open_price == 0.0:
            self.open_price = current_price
            return False

        if current_price < self.open_price:
            if not self.is_falling:
                self.is_falling = True
                self.lowest_price_seen = current_price
            elif current_price < self.lowest_price_seen:
                self.lowest_price_seen = current_price
            return False

        if self.is_falling and current_price > self.lowest_price_seen:
            rebound_threshold = self.lowest_price_seen + (2 * self.get_tick_size(current_price))
            if current_price >= rebound_threshold and current_volume >= 300:
                return True
                
        return False

    def execute_mock_buy(self, price):
        """買進執行與發送第一則通知"""
        self.buy_price = price
        self.highest_price = price
        self.has_position = True
        stop_loss_price = price - (5 * self.get_tick_size(price))
        
        msg = f"🚨【Lobster Radar War Room】\n🎯 標的：{TARGET_STOCK}\n⚡️ 動作：模擬買進 (反彈爆量)\n💰 買入價：{price:.2f} 元\n🛡 絕對停損線：{stop_loss_price:.2f} 元"
        self.send_telegram(msg)
        print(f"✅ [進場] 買入價: {price:.2f}")

    def monitor_and_exit(self, current_price):
        """📈 出場大腦：監控移動防守線與強制清倉時間"""
        if not self.has_position: return
        
        tick_size = self.get_tick_size(self.buy_price)
        
        if current_price > self.highest_price:
            self.highest_price = current_price
            print(f"🔥 創新高: {self.highest_price:.2f}，防守線上移")

        stop_loss_line = self.buy_price - (5 * tick_size)
        trailing_profit_line = self.highest_price - (5 * tick_size)

        now_str = datetime.now().strftime("%H:%M")
        is_forced_time = (now_str >= "13:25") if not self.is_mock_mode else False

        triggered = False
        exit_reason = ""

        if current_price <= stop_loss_line:
            triggered, exit_reason = True, "無情停損 (撞擊固定 5 檔)"
        elif current_price <= trailing_profit_line and current_price > self.buy_price:
            triggered, exit_reason = True, "移動停利 (最高點回撤 5 檔)"
        elif is_forced_time:
            triggered, exit_reason = True, "當日銷帳紀律 (13:25 強制清倉)"

        if triggered:
            self.execute_mock_sell(current_price, exit_reason)

    def execute_mock_sell(self, price, reason):
        """賣出執行與發送最終戰報"""
        self.has_position = False
        self.day_trade_done = True
        
        net_profit = ((price - self.buy_price) * 1000) - 50
        profit_sign = "+" if net_profit >= 0 else ""
        
        msg = f"📊【Unmerciful Lobster 結算戰報】\n🎯 標的：{TARGET_STOCK}\n⚡️ 動作：模擬賣出 ({reason})\n💵 賣出價：{price:.2f} 元\n📉 買入價：{self.buy_price:.2f} 元\n📈 淨損益結算：{profit_sign}{int(net_profit)} 元"
        self.send_telegram(msg)
        print(f"✅ [出場] 原因: {reason}, 損益: {int(net_profit)}")

    def start_mock_test(self):
        """沙盒模擬測試器：灌入假劇本測試邏輯"""
        self.is_mock_mode = True
        self.send_telegram("✅ [系統測試] Lobster 戰術核心已上線，開始執行沙盒模擬...")
        print("🚀 開始執行沙盒模擬...")
        
        mock_data = [
            (30.00, 100), 
            (29.95, 50),  
            (29.80, 80),  
            (29.90, 400), 
            (30.10, 150), 
            (30.20, 100), 
            (29.90, 50)   
        ]
        
        for price, vol in mock_data:
            print(f"➡️ 收到報價: {price:.2f} (量: {vol})")
            time.sleep(2)
            if not self.day_trade_done:
                if not self.has_position:
                    if self.check_rebound_signal(price, vol):
                        self.execute_mock_buy(price)
                else:
                    self.monitor_and_exit(price)
                    
        print("➡️ 測試強制崩潰警報 (模擬當機)...")
        1 / 0  

# ==============================================================================
# 🛡️ 主程式執行與全域崩潰警報網
# ==============================================================================
if __name__ == "__main__":
    bot = LobsterTrailingStrategy()
    try:
        bot.start_mock_test()
    except Exception as e:
        error_details = traceback.format_exc()
        bot.send_telegram(f"💀【系統崩潰警報】\n你的機器人發生致命錯誤：\n{e}\n\n請登入主機檢查！")
        print("系統遭遇錯誤，已發送警報至 Telegram。")
