import os
import requests
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

try:
    # 嘗試載入總經套件
    import yfinance as yf
    
    def get_macro_score():
        score = 0
        try:
            # 1. 恐慌指數 VIX
            vix = yf.Ticker("^VIX").history(period="2d")
            if len(vix) >= 2:
                vix_val = vix['Close'].iloc[-1]
                vix_pct = ((vix['Close'].iloc[-1] - vix['Close'].iloc[-2]) / vix['Close'].iloc[-2]) * 100
                if vix_val > 20 or vix_pct > 5:
                    score += 25
            
            # 2. 美元指數
            usd = yf.Ticker("DX-Y.NYB").history(period="2d")
            if len(usd) >= 2:
                usd_pct = ((usd['Close'].iloc[-1] - usd['Close'].iloc[-2]) / usd['Close'].iloc[-2]) * 100
                if usd_pct > 0.3:
                    score += 25
            
            # 3. 國際黃金期貨
            gold = yf.Ticker("GC=F").history(period="2d")
            if len(gold) >= 2:
                gold_pct = ((gold['Close'].iloc[-1] - gold['Close'].iloc[-2]) / gold['Close'].iloc[-2]) * 100
                if gold_pct > 1.0:
                    score += 25
            
            # 4. 紐約原油期貨
            oil = yf.Ticker("CL=F").history(period="2d")
            if len(oil) >= 2:
                oil_pct = ((oil['Close'].iloc[-1] - oil['Close'].iloc[-2]) / oil['Close'].iloc[-2]) * 100
                if oil_pct > 2.0:
                    score += 25
        except:
            pass 
        return score

    # 執行全球風險判定
    score = get_macro_score()
    if score >= 75:
        macro_msg = f"🚨【全球防禦警報：{score} 分】市場風暴來襲，請啟動絕對防禦！\n"
    elif score == 50:
        macro_msg = f"⚠️【全球風險評估：{score} 分】市場出現烏雲，建議觀望保守。\n"
    else:
        macro_msg = f"🟢【全球風險評估：{score} 分】全球市場安全，焦點看個股籌碼。\n"

    # 證交所資料抓取 (自動向前尋找有效交易日)
    target_date = datetime.now()
    data_found = False
    
    for _ in range(7):
        d_str = target_date.strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        
        if res.get('stat') == 'OK':
            data = res['data']
            stocks = []
            for row in data:
                if len(row) > 18:
                    try:
                        stock_id = row[0].strip()
                        name = row[1].strip()
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
            
            stocks.sort(key=lambda x: x['net'], reverse=True)
            
            msg = f"🦞【戰情室 終極完全體｜{target_date.strftime('%Y-%m-%d')}】\n"
            msg += macro_msg
            
            msg += "\n🔥 買超 Top 10:\n"
            for s in stocks[:10]:
                msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張\n"
                
            msg += "\n⚠️ 倒貨 Top 10:\n"
            for s in stocks[-10:][::-1]:
                msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張\n"
                
            msg += "\n🎯【主力狙擊鏡｜土洋合買】:\n"
            count = 0
            for s in stocks:
                if not s['id'].startswith('00'): 
                    if s['f_net'] > 0 and s['t_net'] > 0 and s['net'] > 1000000: 
                        msg += f"⚡ {s['id']} {s['name']}: 共買 {int(s['net']/1000)} 張 (外資{int(s['f_net']/1000)}/投信{int(s['t_net']/1000)})\n"
                        count += 1
                if count >= 5: break
                
            if count == 0:
                msg += "今日無外資投信同步鎖碼個股。\n"
                
            send_msg(msg)
            data_found = True
            break
            
        target_date -= timedelta(days=1)
        
    if not data_found:
        send_msg("❌ 查詢天數內皆無證交所資料。")

except ImportError:
    send_msg("⚠️ 系統警報：找不到 yfinance 套件！\n大俠，請去 GitHub 檢查 `requirements.txt` 檔案，裡面必須包含 `yfinance` 這行字。")
except Exception as e:
    send_msg(f"⚠️ 終極完全體運行錯誤: {str(e)}")
