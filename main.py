import os
import requests

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

try:
    # 依然用 2026/05/29 進行基準測試
    url = "https://www.twse.com.tw/fund/T86?response=json&date=20260529&selectType=ALL"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
    
    if res.get('stat') == 'OK':
        data = res['data']
        stocks = []
        for row in data:
            if len(row) > 8:
                try:
                    # 抓取代號與名稱，並清除多餘空白
                    stock_id = row[0].strip()
                    name = row[1].strip()
                    f_buy = int(row[4].replace(',', '')) if row[4] != '--' else 0
                    t_buy = int(row[8].replace(',', '')) if row[8] != '--' else 0
                    vol = int(row[7].replace(',', '')) if row[7] != '--' else 0
                    net = f_buy + t_buy
                    stocks.append({'id': stock_id, 'name': name, 'net': net, 'vol': vol})
                except: continue
        
        # 依照淨買賣超排序
        stocks.sort(key=lambda x: x['net'], reverse=True)
        
        # 產出報表
        msg = "🦞【戰情室 PRO 升級版｜20260529】\n"
        
        msg += "\n🔥 買超 Top 10:\n"
        for s in stocks[:10]:
            msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張\n"
            
        msg += "\n⚠️ 倒貨 Top 10:\n"
        for s in stocks[-10:][::-1]:
            msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張\n"
            
        msg += "\n🎯【主力狙擊鏡】:\n"
        # PRO 狙擊邏輯：排除 ETF (00開頭)，買超大於 1000 張，佔比 > 5%
        count = 0
        for s in stocks:
            if s['vol'] > 0 and s['net'] > 1000000 and not s['id'].startswith('00'):
                ratio = s['net'] / s['vol']
                if ratio > 0.05:
                    msg += f"⚡ {s['id']} {s['name']}: 佔比 {round(ratio*100, 1)}%\n"
                    count += 1
            if count >= 5: break
            
        if count == 0:
            msg += "今日無符合條件之主力鎖碼個股。\n"
            
        send_msg(msg)
    else:
        send_msg("❌ 證交所 API 回應異常")
except Exception as e:
    send_msg(f"⚠️ 程式錯誤: {str(e)}")
