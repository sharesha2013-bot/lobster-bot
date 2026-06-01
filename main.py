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

    def scan_dynamic_targets(candidate_stocks):
        washout_list = []
        scan_pool = candidate_stocks[:30] # 掃描籌碼最熱的前 30 檔
        
        for s in scan_pool:
            stock_id = s['id']
            name = s['name']
            
            ticker_id = f"{stock_id}.TW"
            try:
                df = yf.Ticker(ticker_id).history(period="15d")
                if len(df) < 10:
                    df = yf.Ticker(f"{stock_id}.TWO").history(period="15d")
                if len(df) < 10: continue
                
                # 🚀 跑車濾網：檢查「震幅」與「價格」
                current_price = df['Close'].iloc[-1]
                period_high = df['High'].max()
                period_low = df['Low'].min()
                amplitude = (period_high - period_low) / period_low
                
                # 踢掉股價太低 (<30) 或根本沒在動 (震幅 < 10%) 的殭屍股與存股
                if current_price < 30 or amplitude < 0.10:
                    continue

                # 🎯 計算近 10 日 VWAP 大戶建倉成本
                recent_10d = df.tail(10)
                vwap_10d = (recent_10d['Close'] * recent_10d['Volume']).sum() / recent_10d['Volume'].sum()
                
                vol_3ma = df['Volume'].tail(3).mean()
                current_vol = df['Volume'].iloc[-1]
                
                price_diff_pct = abs(current_price - vwap_10d) / vwap_10d
                
                if current_vol < vol_3ma and price_diff_pct <= 0.02:
                    position = "守穩建倉成本" if current_price >= vwap_10d else "成本線下緣"
                    washout_list.append(f"• {stock_id} {name}: 價 {current_price:.1f} (主力估計成本: {vwap_10d:.1f} | {position}, 量縮)")
            except:
                continue
                
        if washout_list:
            return "\n🎯【全市場起漲狙擊區 (強勢跑車版)】:\n" + "\n".join(washout_list) + "\n"
        else:
            return "\n🎯【全市場起漲狙擊區 (強勢跑車版)】:\n今日強勢股中，無符合量縮且具備高波動之標的。\n"

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

    # 3. 證交所資料抓取
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
                        
                        # 🛡️ 第一層防禦：直接把 ETF 與傳統防禦股踢出局！
                        if stock_id.startswith('00'): continue # 踢掉所有 ETF (如 00919, 00929)
                        if stock_id.startswith('28') or stock_id.startswith('58'): continue # 踢掉金融股
                        if stock_id.startswith('11') or stock_id.startswith('12') or stock_id.startswith('13') or stock_id.startswith('14'): continue # 踢掉水泥、食品、塑膠、紡織
                        
                        f_net = int(row[4].replace(',', '')) if row[4] != '--' else 0
                        t_net = int(row[10].replace(',', '')) if row[10] != '--' else 0
                        net = f_net + t_net
                        stocks.append({
                            'id': stock_id, 'name': name, 'f_net': f_net, 't_net': t_net, 'net': net
                        })
                    except: continue
            
            stocks.sort(key=lambda x: x['net'], reverse=True)
            
            washout_msg = scan_dynamic_targets(stocks)
            
            msg = f"🦞【戰情室 終極完全體｜{target_date.strftime('%Y-%m-%d')}】\n"
            msg += macro_msg
            msg += us_tech_msg
            
            msg += washout_msg 
            
            msg += "\n🔥 買超 Top 10:\n"
            for s in stocks[:10]:
                msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張\n"
                
            msg += "\n⚠️ 倒貨 Top 10:\n"
            for s in stocks[-10:][::-1]:
                msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張\n"
                
            msg += "\n🎯【主力狙擊鏡｜土洋合買】:\n"
            count = 0
            for s in stocks:
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
