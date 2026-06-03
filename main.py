import os
import time
import requests
import traceback
import concurrent.futures
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

# ==========================================
# ⚙️ 系統設定區
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

def send_msg(text):
    if not BOT_TOKEN:
        print("⚠️ 未設定 BOT_TOKEN，轉為終端輸出:\n")
        print(text)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print(f"Telegram 推播失敗: {e}")

# ==========================================
# 🦅 獵殺級：不死鳥濾網 (直接計算抗跌係數)
# ==========================================
def get_undying_bird_tag(stock_id):
    try:
        df = yf.Ticker(f"{stock_id}.TW").history(period="5d")
        if df.empty or len(df) < 2: return None
        
        pct_change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
        # 只要跌幅小於 1.0%，即觸發獵殺標籤
        if pct_change >= -1.0:
            return f"🦅[不死鳥 {pct_change:+.1f}%]"
        return None
    except:
        return None

# ==========================================
# 🚀 主程式啟動區
# ==========================================
if __name__ == "__main__":
    try:
        target_date = datetime.now()
        data_found = False
        
        for _ in range(3): # 搜尋近3日資料
            d_str = target_date.strftime('%Y%m%d')
            url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
            res = requests.get(url, headers=HEADERS, timeout=10)
            
            if res.status_code == 200 and 'data' in res.json():
                res_json = res.json()
                stocks = []
                for row in res_json['data']:
                    if len(row) > 18:
                        try:
                            s_id = row[0].strip()
                            if s_id.startswith('00'): continue 
                            net = int(row[4].replace(',', '')) + int(row[10].replace(',', ''))
                            stocks.append({'id': s_id, 'name': row[1].strip(), 'net': net})
                        except: continue
                
                stocks.sort(key=lambda x: x['net'], reverse=True)
                
                msg = f"🦞【戰情室獵殺版｜{target_date.strftime('%Y-%m-%d')}】\n"
                msg += "\n🔥 買超熱點 (主力點火):\n"
                for s in stocks[:10]:
                    msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張\n"
                    
                msg += "\n⚠️ 倒貨警報 (只列出抗跌不死鳥):\n"
                found_bird = False
                for s in stocks[-10:][::-1]:
                    bird_tag = get_undying_bird_tag(s['id'])
                    if bird_tag:
                        msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張 {bird_tag}\n"
                        found_bird = True
                
                if not found_bird:
                    msg += "今日無符合條件的不死鳥標的。\n"
                    
                send_msg(msg)
                data_found = True
                break
            target_date -= timedelta(days=1)
            
    except Exception as e:
        send_msg(f"⚠️ 獵殺系統崩潰: {str(e)}")
