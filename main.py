import os
import requests
import time

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
        # 把原始資料直接轉成清單
        raw_data = res['data']
        processed_list = []
        
        for row in raw_data:
            # 欄位：0代號, 1名稱, 4外資, 8投信, 7成交股數
            try:
                name = row[1]
                # 強制轉換數字，失敗設為 0
                f_buy = int(row[4].replace(',', '')) if row[4] != '--' else 0
                t_buy = int(row[8].replace(',', '')) if row[8] != '--' else 0
                vol = int(row[7].replace(',', '')) if row[7] != '--' else 0
                net = f_buy + t_buy
                
                processed_list.append({'name': name, 'net': net, 'vol': vol})
            except: continue
        
        # 排序
        processed_list.sort(key=lambda x: x['net'], reverse=True)
        
        # 1. 買超 Top 10
        msg = f"🦞【戰情報告｜{d_str}】\n🔥 買超 Top 10:\n"
        for item in processed_list[:10]:
            msg += f"• {item['name']}: {int(item['net']/1000)} 張\n"
        
        # 2. 倒貨 Top 10
        msg += "\n⚠️ 倒貨 Top 10:\n"
        for item in processed_list[-10:][::-1]:
            msg += f"• {item['name']}: {int(item['net']/1000)} 張\n"
        
        # 3. 狙擊鏡 (篩選邏輯：買超 > 500張，佔比 > 5%)
        msg += "\n🎯【主力狙擊鏡】:\n"
        count = 0
        for item in processed_list:
            if item['vol'] > 0 and item['net'] > 500000:
                ratio = item['net'] / item['vol']
                if ratio > 0.05:
                    msg += f"⚡ {item['name']}: 佔比 {round(ratio*100, 1)}%\n"
                    count += 1
                    if count >= 5: break
        
        send_msg(msg)
    else:
        send_msg("❌ 證交所 API 無回應")
except Exception as e:
    send_msg(f"⚠️ 最終修復錯誤: {str(e)}")
