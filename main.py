import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603" 

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

try:
    # 🕒 從今天開始往回找有開盤的日子
    target_date = datetime.now()
    
    for _ in range(7):
        # 證交所網址要的日期格式是 YYYYMMDD
        d_str = target_date.strftime('%Y%m%d')
        
        # 🎯 直接打證交所官方每日結算網頁 (最穩定的源頭)
        url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
        
        # 🎭 戴上面具：偽裝成真人用 Google Chrome 上網，避免被擋
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        res = requests.get(url, headers=headers).json()
        
        # 如果這天有資料 (stat == 'OK')
        if res.get('stat') == 'OK':
            fields = res['fields']
            data = res['data']
            df = pd.DataFrame(data, columns=fields)
            
            # 🔍 自動鎖定欄位名稱 (防呆機制)
            col_id = [c for c in fields if '代號' in c][0]
            col_name = [c for c in fields if '名稱' in c][0]
            col_foreign = [c for c in fields if '外' in c and '買賣超' in c][0]
            col_trust = [c for c in fields if '投信買賣超' in c][0]
            
            # 把帶有逗號的字串洗乾淨，轉成數字
            df[col_foreign] = df[col_foreign].astype(str).str.replace(',', '').astype(float)
            df[col_trust] = df[col_trust].astype(str).str.replace(',', '').astype(float)
            
            # 計算外資+投信的「合計淨買超」
            df['total_net'] = df[col_foreign] + df[col_trust]
            
            # 👑 抓出全市場淨買超「前 10 名」
            top10 = df.nlargest(10, 'total_net')
            
            msg = f"🦞【無情法人全場掃描｜{target_date.strftime('%Y-%m-%d')}】\n"
            msg += f"⚔️ 證交所主機直連！外資投信合買 Top 10：\n\n"
            
            for _, row in top10.iterrows():
                net_buy = int(row['total_net'] / 1000) # 轉成張數
                if net_buy > 0:
                    msg += f"🔥 {row[col_name]} ({row[col_id]}): 狂買 {net_buy} 張\n"
                
            msg += "\n💡 將軍視角：全市場真實底牌已揭曉，請配合月線篩選游擊目標！"
            
            send_msg(msg)
            break # 拿到資料就收工跳出迴圈
            
        # 如果沒資料(假日)，往前推一天，並休息3秒避免被證交所封鎖
        target_date -= timedelta(days=1)
        time.sleep(3)

    else:
        send_msg("🦞 龍蝦雷達：連線證交所失敗，或近期七天皆無資料。")

except Exception as e:
    send_msg(f"🦞 龍蝦系統異常：{str(e)}")
