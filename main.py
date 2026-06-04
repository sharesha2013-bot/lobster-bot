import os
import time
import requests
import traceback
import concurrent.futures
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

# ==========================================
# ⚙️ 系統設定區
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
}

def send_msg(text):
    if not BOT_TOKEN:
        print("⚠️ 未設定 BOT_TOKEN:\n", text)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print(f"Telegram 推播失敗: {e}")

# ==========================================
# 📊 教科書級：主力買超熱度分級模組
# ==========================================
def get_heat_level_tag(net_buy_shares):
    lots = net_buy_shares / 1000
    if lots >= 80000: return " 🌋[Lv.4 核爆]"
    elif lots >= 30000: return " 🔥[Lv.3 沸騰]"
    elif lots >= 10000: return " ♨️[Lv.2 加溫]"
    elif lots >= 5000: return " ☕[Lv.1 微溫]"
    return ""

# ==========================================
# 🦅 不死鳥濾網 2.0 (嚴格對齊日期)
# ==========================================
def check_undying_bird(stock_id, target_date_str):
    try:
        df = yf.Ticker(f"{stock_id}.TW").history(period="1mo")
        if df.empty or len(df) < 2:
            df = yf.Ticker(f"{stock_id}.TWO").history(period="1mo")
            
        df = df[df['Volume'] > 0]
        if len(df) < 2: return ""

        df.index = df.index.tz_localize(None)
        df['date_str'] = df.index.strftime('%Y%m%d')
        
        if target_date_str not in df['date_str'].values:
            return ""
            
        target_idx = df.index.get_loc(df[df['date_str'] == target_date_str].index[0])
        if target_idx < 1: return "" 
        
        target_close = df['Close'].iloc[target_idx]
        yesterday_close = df['Close'].iloc[target_idx - 1]
        
        pct_change = ((target_close - yesterday_close) / yesterday_close) * 100
        
        if pct_change >= -1.5:
            return f" 🦅[不死鳥 {pct_change:+.1f}%]"
            
        return ""
    except:
        return ""

# ==========================================
# 🌍 總體經濟與大盤風向
# ==========================================
def get_macro_score():
    score = 0
    try:
        vix = yf.Ticker("^VIX").history(period="2d")
        if len(vix) >= 2:
            vix_pct = ((vix['Close'].iloc[-1] - vix['Close'].iloc[-2]) / vix['Close'].iloc[-2]) * 100
            if vix['Close'].iloc[-1] > 20 or vix_pct > 5: score += 25
        
        usd = yf.Ticker("DX-Y.NYB").history(period="2d")
        if len(usd) >= 2:
            usd_pct = ((usd['Close'].iloc[-1] - usd['Close'].iloc[-2]) / usd['Close'].iloc[-2]) * 100
            if usd_pct > 0.3: score += 25
    except: pass 
    return score

def get_us_tech():
    try:
        sox = yf.Ticker("^SOX").history(period="2d")
        tsm = yf.Ticker("TSM").history(period="2d")
        if len(sox) >= 2 and len(tsm) >= 2:
            sox_pct = ((sox['Close'].iloc[-1] - sox['Close'].iloc[-2]) / sox['Close'].iloc[-2]) * 100
            tsm_pct = ((tsm['Close'].iloc[-1] - tsm['Close'].iloc[-2]) / tsm['Close'].iloc[-2]) * 100
            return f"🇺🇸【美股風向球】費城半導體: {sox_pct:+.2f}% ｜ 台積電 ADR: {tsm_pct:+.2f}%\n"
    except: return "🇺🇸【美股風向球】夜盤數據讀取中斷\n"
    return ""

# ==========================================
# 🎯 雙軌獵殺掃描系統
# ==========================================
def fetch_single_stock(args):
    stock, target_date_str = args
    stock_id = stock['id']
    try:
        df = yf.Ticker(f"{stock_id}.TW").history(period="1mo")
        if df.empty: df = yf.Ticker(f"{stock_id}.TWO").history(period="1mo")
        df = df[df['Volume'] > 0].dropna(subset=['Close', 'Volume'])
        
        df.index = df.index.tz_localize(None)
        df['date_str'] = df.index.strftime('%Y%m%d')
        
        if target_date_str in df['date_str'].values:
            target_idx = df.index.get_loc(df[df['date_str'] == target_date_str].index[0])
            df = df.iloc[:target_idx + 1]
            
        if len(df) < 20: return None
        return {'stock': stock, 'df': df}
    except: return None

def scan_pro_targets(candidate_stocks, target_date_str):
    washout_mode_list, breakout_mode_list = [], []
    scan_pool = [(stock, target_date_str) for stock in candidate_stocks[:40]]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_single_stock, scan_pool))
    
    for res in results:
        if not res: continue
        stock_id, name, df = res['stock']['id'], res['stock']['name'], res['df']
        
        current_price = df['Close'].iloc[-1]
        yesterday_price = df['Close'].iloc[-2]
        current_vol = df['Volume'].iloc[-1]
        ma10 = df['Close'].tail(10).mean()
        ma20 = df['Close'].tail(20).mean()
        
        if not (current_price > ma20 and ma10 >= ma20): continue 
        
        recent_10d = df.tail(10)
        vol_sum = recent_10d['Volume'].sum()
        if vol_sum == 0: continue 
        
        vwap_10d = (recent_10d['Close'] * recent_10d['Volume']).sum() / vol_sum
        avg_vol_5d = df['Volume'].tail(5).mean()
        high_10d = recent_10d['High'].max() 
        price_diff_pct = (current_price - vwap_10d) / vwap_10d

        if current_price >= (vwap_10d * 0.98) and current_vol < (avg_vol_5d * 0.75) and abs(price_diff_pct) <= 0.03:
            washout_mode_list.append(f"• {stock_id} {name}: 價 {current_price:.1f} (守底 {vwap_10d:.1f} | 量縮)")
        elif current_price >= vwap_10d and current_vol > (avg_vol_5d * 1.5) and current_price > yesterday_price:
            if current_price >= (high_10d * 0.98): 
                breakout_mode_list.append(f"• {stock_id} {name}: 價 {current_price:.1f} (爆量! 前高 {high_10d:.1f})")
            
    report = "\n🎯【龍蝦戰情室 Pro - 雙軌獵殺名單】\n===================================\n"
    report += "🟢 洗碗秀 (量縮守底，適合潛伏)\n"
    report += "\n".join(washout_mode_list) if washout_mode_list else "無"
    report += "\n\n🔴 主升段 (爆量點火)\n"
    report += "\n".join(breakout_mode_list) if breakout_mode_list else "無"
    report += "\n===================================\n"
    return report

# ==========================================
# 🚀 主程式啟動區 (全新 API 引擎)
# ==========================================
if __name__ == "__main__":
    try:
        # 1. 取得大盤與美股狀態
        score = get_macro_score()
        macro_msg = f"🚨【風險：{score}分】風暴來襲！\n" if score >= 75 else (f"⚠️【風險：{score}分】建議觀望。\n" if score >= 50 else f"🟢【風險：{score}分】市場安全。\n")
        us_tech_msg = get_us_tech()
        
        # 2. 自動抓取「真實的最新交易日」，避免遇到假日當機
        twii = yf.Ticker("^TWII").history(period="5d")
        latest_date = twii.index[-1]
        d_str = latest_date.strftime('%Y%m%d')
        display_date = latest_date.strftime('%Y-%m-%d')
        
        # 3. 呼叫證交所官方 Open API 專線 (瞬間抓取最新三大法人買賣超)
        api_url = "https://openapi.twse.com.tw/v1/fund/T86_ALL"
        res = requests.get(api_url, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            stocks = []
            
            for row in data:
                try:
                    stock_id = row.get('Code', '').strip()
                    name = row.get('Name', '').strip()
                    
                    if not stock_id or stock_id.startswith('00'): 
                        continue 
                        
                    # 直接從 JSON 抓取數據，不用再算陣列位置
                    f_net = int(str(row.get('ForeignInvestorNetBuy', '0')).replace(',', ''))
                    t_net = int(str(row.get('InvestmentTrustNetBuy', '0')).replace(',', ''))
                    net = int(str(row.get('Difference', '0')).replace(',', ''))
                    
                    stocks.append({'id': stock_id, 'name': name, 'f_net': f_net, 't_net': t_net, 'net': net})
                except:
                    continue
            
            # 排序：依照總買賣超張數排序
            stocks.sort(key=lambda x: x['net'], reverse=True)
            
            # 4. 啟動獵殺雷達
            pro_msg = scan_pro_targets(stocks, d_str)
            
            # 5. 組合戰情報告
            msg = f"🦞【戰情室 Pro 完全版｜{display_date}】\n"
            msg += macro_msg + us_tech_msg + pro_msg 
            
            msg += "\n🔥 買超 Top 10:\n"
            for s in stocks[:10]:
                heat_tag = get_heat_level_tag(s['net'])
                msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張{heat_tag}\n"
                
            msg += "\n⚠️ 倒貨警報 (不死鳥):\n"
            found_bird = False
            for s in stocks[-10:][::-1]:
                bird_tag = check_undying_bird(s['id'], d_str)
                if bird_tag:
                    msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張{bird_tag}\n"
                    found_bird = True
            if not found_bird:
                msg += "今日無符合條件的不死鳥標的。\n"
                
            msg += "\n🎯【主力狙擊鏡｜土洋合買】:\n"
            count = 0
            for s in stocks:
                if s['f_net'] > 0 and s['t_net'] > 0 and s['net'] > 1000000: 
                    msg += f"⚡ {s['id']} {s['name']}: 共買 {int(s['net']/1000)} 張 (外{int(s['f_net']/1000)}/投{int(s['t_net']/1000)})\n"
                    count += 1
                if count >= 5: break
            if count == 0: msg += "無土洋合買標的。\n"
                
            send_msg(msg)
        else:
            send_msg(f"❌ API 連線異常，狀態碼: {res.status_code}")

    except Exception as e:
        error_detail = traceback.format_exc()
        send_msg(f"⚠️ 龍蝦系統 Pro 發生崩潰！\n{str(e)}\n{error_detail[:300]}")
