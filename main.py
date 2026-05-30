import os
import requests

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

try:
    # 直接固定抓 2026/05/29 的完整數據進行測試
    url = "https://www.twse.com.tw/fund/T86?response=json&date=20260529&selectType=ALL"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
    
    if res.get('stat') == 'OK':
        stocks = []
        for row in res['data']:
            # 確保行數正確，避開標頭與尾巴的合計行
            if len(row) > 8:
                try:
                    name = row[1]
                    f_buy = int(row[4].replace(',', '')) if row[4] != '--' else 0
                    t_buy = int(row[8].replace(',', '')) if row[8] != '--' else 0
                    vol = int(row[7].replace(',', '')) if row[7] != '--' else 0
                    net = f_buy + t_buy
                    stocks.append({'name': name, 'net': net, 'vol': vol})
                except: continue
        
        # 按買超排序
        stocks.sort(key=lambda x: x['net'], reverse=True)
        
        # 產出訊息 (精簡且穩定)
        msg = f"🦞【完全體戰情報告｜20260529】\n\n🔥 買超 Top 10:\n"
        for s in stocks[:10]:
            msg += f"• {s['name']}: {int(s['net']/1000)} 張\n"
            
        msg += "\n⚠️ 倒貨 Top 10:\n"
        for s in stocks[-10:][::-1]:
            msg += f"• {s['name']}: {int(s['net']/1000)} 張\n"
            
        msg += "\n🎯【主力狙擊鏡】:\n"
        # 狙擊邏輯：只要法人有進場，且佔比大於 2%，就列出，不設上限
        found = False
        for s in stocks:
            if s['vol'] > 0 and s['net'] > 500000:
                ratio = s['net'] / s['vol']
                if ratio > 0.02:
                    msg += f"⚡ {s['name']}: 佔比 {round(ratio*100, 1)}%\n"
                    found = True
        
        if not found: msg += "無特別主力鎖碼標的。"
        send_msg(msg)
    else:
        send_msg("❌ 證交所 API 回應異常，請稍後再試。")

except Exception as e:
    send_msg(f"⚠️ 程式修復錯誤: {str(e)}")
