import os
import requests
import traceback
import concurrent.futures
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

# ==========================================
# ⚙️ 系統設定區 & 族群字典
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

SECTOR_MAP = {
    '3324': '散熱', '3017': '散熱', '2421': '散熱',
    '1504': '重電', '1513': '重電', '1519': '重電',
    '2368': 'AI伺服器', '3231': 'AI伺服器', '2382': 'AI伺服器',
    '2330': '晶圓代工', '6770': '晶圓代工', '2303': '晶圓代工',
    '2342': '封測', '3049': '面板', '3481': '面板',
    '2371': '綠能', '6901': '創投'
}

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

def get_heat_level_tag(net_buy_shares):
    lots = net_buy_shares / 1000
    if lots >= 80000: return " 🌋[Lv.4]"
    elif lots >= 30000: return " 🔥[Lv.3]"
    elif lots >= 10000: return " ♨️[Lv.2]"
    elif lots >= 5000: return " ☕[Lv.1]"
    return ""

def get_macro_score():
    score, reasons = 0, []
    try:
        twd = yf.Ticker("TWD=X").history(period="5d")
        if len(twd) >= 2:
            twd_pct = ((twd['Close'].iloc[-1] - twd['Close'].iloc[-2]) / twd['Close'].iloc[-2]) * 100
            if twd_pct > 0.2:
                score += 35
                reasons.append(f"💸台幣急貶(+{twd_pct:.2f}%)")
    except: reasons.append("⚠️匯率斷線")
    try:
        otc = yf.Ticker("^TWO").history(period="1mo")
        if len(otc) >= 2:
            otc_pct = ((otc['Close'].iloc[-1] - otc['Close'].iloc[-2]) / otc['Close'].iloc[-2]) * 100
            if otc_pct < -1.0: 
                score += 45
                reasons.append(f"🩸櫃買下殺({otc_pct:.2f}%)")
    except: score += 20
    try:
        twii = yf.Ticker("^TWII").history(period="1mo")
        if len(twii) >= 2:
            twii_pct = ((twii['Close'].iloc[-1] - twii['Close'].iloc[-2]) / twii['Close'].iloc[-2]) * 100
            if twii_pct < -1.0:
                score += 30
                reasons.append(f"💀大盤下殺({twii_pct:.2f}%)")
    except: score += 20
    return score, reasons

def analyze_stock(args):
    stock, target_date_str, rank, macro_score = args
    try:
        ticker = yf.Ticker(f"{stock['id']}.TW")
        df = ticker.history(period="1mo")
        if df.empty: 
            ticker = yf.Ticker(f"{stock['id']}.TWO")
            df = ticker.history(period="1mo")
        df = df[df['Volume'] > 0].dropna(subset=['Close', 'Volume'])
        if len(df) < 20: return None
        
        shares_out = ticker.fast_info.shares
        df.index = df.index.tz_localize(None)
        df['date_str'] = df.index.strftime('%Y%m%d')
        
        if target_date_str in df['date_str'].values:
            target_idx = df.index.get_loc(df[df['date_str'] == target_date_str].index[0])
            df = df.iloc[:target_idx + 1]
        
        current, yesterday = df.iloc[-1], df.iloc[-2]
        if current['Volume'] < 500000: return None
        
        ma5, ma10, ma20 = df['Close'].tail(5).mean(), df['Close'].tail(10).mean(), df['Close'].tail(20).mean()
        capital_ratio = stock['net'] / shares_out if shares_out and stock['net'] > 0 else 0
        
        res = {'stock': stock, 'washout': False, 'breakout': False, 'tier': '', 'current': current, 'tag': '', 'sector': f"[{SECTOR_MAP.get(stock['id'], '個股')}]"}
        
        body_len = abs(current['Close'] - current['Open'])
        upper_shadow = current['High'] - max(current['Close'], current['Open'])
        has_rod = (upper_shadow > (body_len * 2))
        vol_ratio = current['Volume'] / yesterday['Volume'] if yesterday['Volume'] > 0 else 0
        
        if rank <= 40:
            if stock['net'] > 0 and capital_ratio >= 0.001 and (-0.01 <= (current['Close']-ma5)/ma5 <= 0.03):
                res['washout'] = True
                res['tag'] = f"鎖碼{capital_ratio*100:.2f}%"
            
            req_ratio = 0.008 if macro_score >= 50 else 0.005
            if stock['net'] > 0 and current['Close'] > yesterday['Close'] and current['Close'] > ma20 and capital_ratio >= req_ratio:
                if has_rod:
                    res['breakout'], res['tier'] = True, "💀[假突破]"
                elif vol_ratio >= 1.2:
                    res['breakout'], res['tier'] = True, "🔥[主升段]"
        return res
    except: return None

if __name__ == "__main__":
    try:
        twii = yf.Ticker("^TWII").history(period="10d")
        score, _ = get_macro_score()
        for offset in range(1, 5):
            latest_date = twii.index[-offset]
            d_str, display_date = latest_date.strftime('%Y%m%d'), latest_date.strftime('%Y-%m-%d')
            stocks = []
            
            # 抓取資料
            try:
                res = requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL", headers=HEADERS, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    for row in data:
                        sid = row.get('Code', '').strip()
                        if sid and not sid.startswith('00'):
                            stocks.append({'id': sid, 'name': row.get('Name', '').strip(), 'net': int(str(row.get('Difference', '0')).replace(',', ''))})
            except: pass
            
            if stocks:
                stocks.sort(key=lambda x: x['net'], reverse=True)
                scan_args = [(s, d_str, i + 1, score) for i, s in enumerate(stocks[:150])]
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    results = list(executor.map(analyze_stock, scan_args))
                
                msg = f"🦞【戰情室 Pro｜{display_date}】\n"
                msg += "\n🔴 主升段:\n" + "\n".join([f"• {r['tier']} {r['sector']} {r['stock']['id']}" for r in results if r and r['breakout']])
                send_msg(msg)
                break
    except Exception as e:
        send_msg(f"⚠️ 系統錯誤: {str(e)}")
