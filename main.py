import os
import requests

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

try:
    url = "https://www.twse.com.tw/fund/T86?response=json&date=20260529&selectType=ALL"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
    
    if res.get('stat') == 'OK':
        data = res['data']
        stocks = []
        for row in data:
            # T86 完整欄位有 19 欄，確保資料完整
            if len(row) > 18:
                try:
                    stock_id = row[0].strip()
                    name = row[1].strip()
                    # 精準抓取：4 是外資淨買賣超，10 是投信淨買賣超
                    f_net = int(row[4].replace(',', '')) if row[4] != '--' else 0
                    t_net = int(row[10].replace(',', '')) if row[10] != '--' else 0
                    net = f_net + t_net
                    stocks.append({
                        'id': stock_id, 
                        'name': name, 
                        'f_net': f_net, 
                        't_net': t_net, 
                        'net': net
                    })
                except: continue
        
        # 依照總淨買賣超排序
        stocks.sort(key=lambda x: x['net'], reverse=True)
        
        msg = "🦞【戰情室 PRO 終極版｜20260529】\n"
        
        msg += "\n🔥 買超 Top 10:\n"
        for s in stocks[:10]:
            msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張\n"
            
        msg += "\n⚠️ 倒貨 Top 10:\n"
        for s in stocks[-10:][::-1]:
            msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張\n"
            
        # PRO 狙擊鏡：土洋合買 (外資與投信同步買超 > 0，且排除 ETF，總買超 > 1000張)
        msg += "\n🎯【主力狙擊鏡｜土洋合買】:\n"
        count = 0
        for s in stocks:
            if not s['id'].startswith('00'): # 排除 ETF
                if s['f_net'] > 0 and s['t_net'] > 0 and s['net'] > 1000000:
                    msg += f"⚡ {s['id']} {s['name']}: 共買 {int(s['net']/1000)} 張 (外資{int(s['f_net']/1000)}/投信{int(s['t_net']/1000)})\n"
                    count += 1
            if count >= 5: break
            
        if count == 0:
            msg += "今日無外資投信同步鎖碼個股。\n"
            
        send_msg(msg)
    else:
        send_msg("❌ 證交所 API 回應異常")
except Exception as e:
    send_msg(f"⚠️ 程式錯誤: {str(e)}")
