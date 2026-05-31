import os
import requests
from datetime import datetime, timedelta
import yfinance as yf

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

try:
    def get_macro_score():
        score = 0
        try:
            # 1. 恐慌指數 VIX
            vix = yf.Ticker("^VIX").history(period="2d")
            if len(vix) >= 2:
                vix_val = vix['Close'].iloc[-1]
                vix_pct = ((vix['Close'].iloc[-1] - vix['Close'].iloc[-2]) / vix['Close'].iloc[-2]) * 100
                if vix_val > 20 or vix_pct > 5: score += 25
            
            # 2. 美元指數
            usd = yf.Ticker("DX-Y.NYB").history(period="2d")
            if len(usd) >= 2:
                usd_pct = ((usd['Close'].iloc[-1] - usd['Close'].iloc[-2]) / usd['Close'].iloc[-2]) * 100
                if usd_pct > 0.3: score += 25
            
            # 3. 國際黃金期貨
            gold = yf.Ticker("GC=F").history(period="2d")
            if len(gold) >= 2:
                gold_pct = ((gold['Close'].iloc[-1] - gold['Close'].iloc[-2]) / gold['Close'].iloc[-2]) * 100
                if gold_pct > 1.0: score += 25
            
            # 4. 紐約原油期貨
            oil = yf.Ticker("CL=F").history(period="2d")
            if len(oil) >= 2:
                oil_pct = ((oil['Close'].iloc[-1] - oil['Close'].iloc[-2]) / oil['Close'].iloc[-2]) * 100
                if oil_pct > 2.0: score += 25
        except:
            pass 
        return score

    def get_us_tech():
        try:
            sox = yf.Ticker("^SOX").history(period="2d")
            tsm = yf.Ticker("TSM").history(period="2d")
            
            if len(sox) >= 2 and len(tsm) >= 2:
                sox_pct = ((sox['Close'].iloc[-1] - sox['Close'].iloc[-2]) / sox['Close'].iloc[-2]) * 100
                tsm_pct = ((tsm['Close'].iloc[-1] - tsm['Close'].iloc[-2]) / tsm['Close'].iloc[-2]) * 100
                return f"🇺🇸【美股風向球】費城半導體: {sox_pct:+.2f}% ｜ 台積電 ADR: {tsm_pct:+.2f}%\n"
        except:
            return "🇺🇸【美股風向球】夜盤數據讀取中斷\n"
        return ""

    def get_washout_leaders():
        # 大俠專屬：科技龍頭觀察池 (可隨時增減)
        tech_leaders = {
            '2330.TW': '台積電', '2454.TW': '聯發科', '2317.TW': '鴻海',
            '2382.TW': '廣達', '3231.TW': '緯創', '2308.TW': '台達電',
            '3017.TW': '奇鋐', '3324.TW': '雙鴻', '3661.TW': '世芯-KY',
            '2344.TW': '華邦電', '2408.TW': '南亞科', '8299.TWO': '群聯'
        }
        washout_list = []
        try:
            for ticker, name in tech_leaders.items():
                df = yf.Ticker(ticker).history(period="25d")
                if len(df) < 20: continue
                
                # 計算 20日均線 (月線) 與 5日均量
                ma20 = df['Close'].tail(20).mean()
                current_price = df['Close'].iloc[-1]
                vol_5ma = df['Volume'].tail(5).mean()
                current_vol = df['Volume'].iloc[-1]
                
                # 🎯 洗盤過濾邏輯：
                # 1. 量縮：今日成交量小於近 5 日均量
                # 2. 貼近支撐：股價距離 20MA 上下不超過 3%
                price_diff_pct = abs(current_price - ma20) / ma20
                
                if current_vol < vol_5ma and price_diff_pct <= 0.03:
                    # 判斷是在月線之上還是之下
                    position = "守穩月線" if current_price >= ma20 else "月線下緣"
                    washout_list.append(f"• {name}: 價 {current_price:.1f} ({position}, 量縮)")
        except Exception as e:
            return f"\n⚠️ 龍頭洗盤雷達掃描異常: {e}\n"
        
        if washout_list:
            return "\n🎯【科技龍頭洗盤狙擊區】:\n" + "\n".join(washout_list) + "\n"
        else:
            return "\n🎯【科技龍頭洗盤狙擊區】:\n今日無符合量縮貼近月線之龍頭股。\n"


    # 1. 執行全球風險判定
    score = get_macro_score()
    if score >= 75:
        macro_msg = f"🚨【全球防禦警報：{score} 分】市場風暴來襲，請啟動絕對防禦！\n"
    elif score >= 50:
        macro_msg = f"⚠️【全球風險評估：{score} 分】市場出現烏雲，建議觀望保守。\n"
    else:
        macro_msg = f"🟢【全球風險評估：{score} 分】全球市場安全，焦點看個股籌碼。\n"

    # 2. 執行美股夜盤風向
    us_tech_msg = get_us_tech()

    # 3. 執行大俠的科技龍頭洗盤雷達
    washout_msg = get_washout_leaders()

    # 4. 證交所資料抓取
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
                            'id': stock_id, 'name': name, 'f_net': f_net, 't_net': t_net, 'net': net
                        })
                    except: continue
            
            stocks.sort(key=lambda x: x['net'], reverse=True)
            
            # 組合終極戰報
            msg = f"🦞【戰情室 終極完全體｜{target_date.strftime('%Y-%m-%d')}】\n"
            msg += macro_msg
            msg += us_tech_msg
            
            msg += washout_msg # ★ 科技龍頭洗盤雷達插入這裡 ★
            
            msg += "\n🔥 買超 Top 10:\n"
            for s in stocks[:10]:
                msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張\n"
                
            msg += "\n⚠️ 倒貨 Top 10:\n"
            for s in stocks[-10:][::-1]:
                msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張\n"
                
            msg += "\n🤝【主力狙擊鏡｜土洋合買】:\n"
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
    send_msg("⚠️ 系統警報：找不到 yfinance 套件！請檢查 requirements.txt")
except Exception as e:
    send_msg(f"⚠️ 終極完全體運行錯誤: {str(e)}")
