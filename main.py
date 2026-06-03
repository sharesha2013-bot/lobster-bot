import os
import time
import requests
import traceback
import yfinance as yf
import pandas as pd

# ==========================================
# ⚙️ 系統設定
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_msg(text):
    if not BOT_TOKEN:
        print(text)
        return
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                  json={"chat_id": CHAT_ID, "text": text}, timeout=10)

# ==========================================
# 🦅 不死鳥濾網 (已優化：抗跌係數 1%)
# ==========================================
def get_undying_bird_tag(stock_id):
    try:
        df = yf.Ticker(f"{stock_id}.TW").history(period="5d")
        if df.empty or len(df) < 2: return ""
        pct_change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
        
        # 只要跌幅小於 1%，即觸發不死鳥標籤
        if pct_change >= -1.0:
            return f" 🦅[不死鳥 {pct_change:+.1f}%]"
        return ""
    except:
        return ""

# ==========================================
# 🚀 主程式：籌碼獵殺鏡
# ==========================================
if __name__ == "__main__":
    try:
        target_date = datetime.now().strftime('%Y%m%d')
        # 這裡簡化抓取流程，專注在籌碼與軋空邏輯
        url = f"https://www.twse.com.tw/fund/T86?response=json&date={target_date}&selectType=ALL"
        res = requests.get(url, timeout=10).json()
        
        if res.get('stat') == 'OK':
            stocks = []
            for row in res['data']:
                # 這裡篩選買超與主力動向
                s_id, name = row[0].strip(), row[1].strip()
                f_net = int(row[4].replace(',', ''))
                t_net = int(row[10].replace(',', ''))
                stocks.append({'id': s_id, 'name': name, 'net': f_net + t_net})
            
            stocks.sort(key=lambda x: x['net'], reverse=True)
            
            msg = f"🦞【龍蝦獵殺戰報｜{datetime.now().strftime('%Y-%m-%d')}】\n"
            
            msg += "\n🔥 買超熱點 (主力點火):\n"
            for s in stocks[:10]:
                msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張\n"
            
            msg += "\n⚠️ 倒貨警報 (不死鳥監控):\n"
            for s in stocks[-10:][::-1]:
                bird_tag = get_undying_bird_tag(s['id'])
                if bird_tag: # 只顯示有觸發不死鳥的，過濾掉雜訊
                    msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張{bird_tag}\n"
            
            send_msg(msg)
            
    except Exception as e:
        print(f"系統故障: {e}")
