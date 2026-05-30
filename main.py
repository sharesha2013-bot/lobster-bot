import os
import requests
import json

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

def clean_num(val):
    try:
        return int(val.replace(',', ''))
    except:
        return 0

try:
    # 強制指定 05/29 驗證
    url = "https://www.twse.com.tw/fund/T86?response=json&date=20260529&selectType=ALL"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
    
    if res.get('stat') == 'OK':
        data = res['data']
        stocks = []
        
        for row in data:
            # 確保這是一行有效的股票資料 (代號通常是4-6碼，若長度不對直接跳過)
            if len(row) > 8:
                try:
                    name = row[1]
                    f_buy = clean_num(row[4])
                    t_buy = clean_num(row[8])
                    vol = clean_num(row[7])
                    net = f_buy + t_buy
                    stocks.append({'name': name, 'net': net, 'vol': vol})
                except: continue
        
        # 排序
        stocks.sort(key=lambda x: x['net'], reverse=True)
        
        # 產出訊息
        msg = "🦞【完全體戰情室｜20260529】\n"
        
        msg += "\n🔥 買超 Top 10:\n"
        for s in stocks[:10]:
            msg += f"• {s['name']}: {int(s['net']/1000)} 張\n"
            
        msg += "\n⚠️ 倒貨 Top 10:\n"
        for s in stocks[-10:][::-1]:
            msg += f"• {s['name']}: {int(s['net']/1000)} 張\n"
            
        msg += "\n🎯【主力狙擊鏡】:\n"
        # 篩選邏輯：買超需為正，成交量需大於0，且法人佔比 > 5%
        count = 0
        for s in stocks:
            if s['vol'] > 5000000 and s['net'] > 500000:
                ratio = s['net'] / s['vol']
                if ratio > 0.05:
                    msg += f"⚡ {s['name']}: {round(ratio*100, 1)}% 主力鎖碼\n"
                    count += 1
            if count >= 5: break
            
        send_msg(msg)
    else:
        send_msg("❌ 證交所 API 回傳異常")
except Exception as e:
    send_msg(f"⚠️ 程式修復錯誤: {str(e)}")
