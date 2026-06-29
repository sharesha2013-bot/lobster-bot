# -*- coding: utf-8 -*-
import os
import time
import requests
import traceback
from datetime import datetime

# ==============================================================================
# ⚙️ 系統設定：Unmerciful Lobster 00981A 專屬當沖自動化策略 (完整測試版)
# ==============================================================================
# ⚠️ 上傳前，請務必把下面這行換成你真實的 Telegram BOT_TOKEN
BOT_TOKEN = "你的_BOT_TOKEN_放這裡"
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
        self.is_mock_mode = False  # 用於區分是否為沙盒測試，避免晚上測試時觸發強制清倉

    def send_telegram(self, text):
        """發送 Telegram 戰報"""
        if not BOT_TOKEN or BOT_TOKEN == "你的_BOT_TOKEN_放這裡":
            print("⚠️ 未設定 BOT_TOKEN，TG 推播略過，顯示於終端機：\n" + text)
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
        
        # 記錄開盤價
        if self.open_price == 0.0:
            self.open_price = current_price
            return False

        # 如果跌破開盤價，記錄下墜過程的最低點
        if current_price < self.open_price:
            if not self.is_falling:
                self.is_falling = True
                self.lowest_price_seen = current_price
            elif current_price < self.lowest_price_seen:
                self.lowest_price_seen = current_price
            return False

        # 如果正在下跌中，且現在價格大於看過的最低點 (尋找反彈)
        if self.is_falling and current_price > self.lowest_price_seen:
            # 條件：反彈超過 2 檔
            rebound_threshold = self.lowest_price_seen + (2 * self.get_tick_size(current_price))
            # 條件：成交量突破 300 張
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
        
        # 股價創新高，移動防守線跟著上移
        if current_price > self.highest_price:
            self.highest_price = current_price
            print(f"🔥 創新高: {self.highest_price:.2f}，防守線上移")

        # 計算兩道防線 (固定 5 檔停損 vs 移動 5 檔停利)
        stop_loss_line = self.buy_price - (5 * tick_size)
        trailing_profit_line = self.highest_price - (5 * tick_size)

        # 檢查 13:25 強制清倉 (若在沙盒測試模式則略過此檢查)
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
        
        # 損益計算
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
        
        # 測試劇本：(價格, 單分鐘成交量)
        mock_data = [
            (30.00, 100), # 記錄開盤
            (29.95, 50),  # 開始下跌
            (29.80, 80),  # 探底
            (29.90, 400), # 反彈且爆量 -> 觸發買進 (30.00 - 5檔 = 29.75 停損)
            (30.10, 150), # 獲利奔跑 -> 防守線拉到 29.85
            (30.20, 100), # 繼續奔跑 -> 防守線拉到 29.95
            (29.90, 50)   # 跌破 29.95 -> 觸發移動停利！
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
                    
        # 測試崩潰警報功能
        print("➡️ 測試強制崩潰警報 (模擬當機)...")
        1 / 0  

# ==============================================================================
# 🛡️ 主程式執行與全域崩潰警報網
# ==============================================================================
if __name__ == "__main__":
    bot = LobsterTrailingStrategy()
    try:
        # 執行沙盒測試
        bot.start_mock_test()
    except Exception as e:
        # 捕捉所有錯誤並發送警報
        error_details = traceback.format_exc()
        bot.send_telegram(f"💀【系統崩潰警報】\n你的機器人發生致命錯誤：\n{e}\n\n請登入主機檢查！")
        print("系統遭遇錯誤，已發送警報至 Telegram。")
