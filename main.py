import os
import requests

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

try:
    d_str = "20260529"
    url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
    
    if res.get('stat') == 'OK':
        data = res['data']
        stocks = []
        for row in data:
            if len(row) > 8:
                try:
                    name = row[1]
                    f_buy = int(row[4].replace(',', '')) if row[4] != '--' else 0
                    t_buy = int(row[8].replace(',', '')) if row[8] != '--' else 0
                    vol = int(row[7].replace(',', '')) if row[7] != '--' else 0
                    net = f_buy + t_buy
                    stocks.append({'name': name, 'net': net, 'vol': vol})
                except: continue
        
        # 買賣超排行
        stocks.sort(key=lambda x: x['net'], reverse=True)
        
        # 1. 買超 Top 10
        msg = f"🦞【戰情報告｜{d_str}】\n🔥 買超 Top 10:\n"
        for s in stocks[:10]:
            msg += f"• {s['name']}: {int(s['net']/1000)} 張\n"
            
        # 2. 賣超 Top 10
        msg += "\n⚠️ 倒貨 Top 10:\n"
        for s in stocks[-10:][::-1]:
            msg += f"• {s['name']}: {int(s['net']/1000)} 張\n"
            
        # 3. 主力狙擊鏡 (精準篩選)
        msg += "\n🎯【主力狙擊鏡】:\n"
        count = 0
        for s in stocks:
            if s['vol'] > 1000000 and s['net'] > 100000:
                ratio = s['net'] / s['vol']
                if ratio > 0.03:
                    msg += f"⚡ {s['name']}: 佔比 {round(ratio*100, 1)}%\n"
                    count += 1
            if count >= 5: break
            
        if count == 0:
            msg += "今日無法人悄悄吃貨之標的。"
            
        send_msg(msg)
    else:
        send_msg("❌ 證交所 API 回傳異常")
except Exception as e:
    send_msg(f"⚠️ 程式修復錯誤: {str(e)}")
