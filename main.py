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
# 📊 輔助模組
# ==========================================
def get_heat_level_tag(net_buy_shares):
    lots = net_buy_shares / 1000
    if lots >= 80000: return " 🌋[Lv.4 核爆]"
    elif lots >= 30000: return " 🔥[Lv.3 沸騰]"
    elif lots >= 10000: return " ♨️[Lv.2 加溫]"
    elif lots >= 5000: return " ☕[Lv.1 微溫]"
    return ""

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

def check_undying_bird(stock_id, target_date_str):
    try:
        df = yf.Ticker(f"{stock_id}.TW").history(period="1mo")
        if df.empty or len(df) < 2:
            df = yf.Ticker(f"{stock_id}.TWO").history(period="1mo")
            
        df = df[df['Volume'] > 0]
        if len(df) < 2: return ""

        df.index = df.index.tz_localize(None)
        df['date_str'] = df.index.strftime('%Y%m%d')
        
        if target_date_str not in df['date_str'].values: return ""
            
        target_idx = df.index.get_loc(df[df['date_str'] == target_date_str].index[0])
        if target_idx < 1: return "" 
        
        target_close = df['Close'].iloc[target_idx]
        yesterday_close = df['Close'].iloc[target_idx - 1]
        pct_change = ((target_close - yesterday_close) / yesterday_close) * 100
        
        if pct_change >= -1.5:
            return f" 🦅[不死鳥 {pct_change:+.1f}%]"
        return ""
    except: return ""

# ==========================================
# 🎯 核心大腦：股本透視與攻防分離引擎
# ==========================================
def analyze_stock(args):
    stock, target_date_str, rank = args
    stock_id = stock['id']
    try:
        ticker = yf.Ticker(f"{stock_id}.TW")
        df = ticker.history(period="1mo")
        if df.empty: 
            ticker = yf.Ticker(f"{stock_id}.TWO")
            df = ticker.history(period="1mo")
            
        df = df[df['Volume'] > 0].dropna(subset=['Close', 'Volume'])
        
        shares_out = None
        try:
            shares_out = ticker.fast_info.shares
        except:
            try:
                shares_out = ticker.info.get('sharesOutstanding')
            except:
                pass
        
        df.index = df.index.tz_localize(None)
        df['date_str'] = df.index.strftime('%Y%m%d')
        
        if target_date_str in df['date_str'].values:
            target_idx = df.index.get_loc(df[df['date_str'] == target_date_str].index[0])
            df = df.iloc[:target_idx + 1]
            
        if len(df) < 20: return None
        
        current = df.iloc[-1]
        yesterday = df.iloc[-2]
        ma10 = df['Close'].tail(10).mean()
        ma20 = df['Close'].tail(20).mean()
        avg_vol_5d = df['Volume'].tail(5).mean()
        
        recent_10d = df.tail(10)
        vol_sum = recent_10d['Volume'].sum()
        if vol_sum == 0: return None
        
        vwap_10d = (recent_10d['Close'] * recent_10d['Volume']).sum() / vol_sum
        high_10d = recent_10d['High'].max()
        past_9d_low = df['Low'].iloc[-10:-1].min()
        
        net_buy_shares = abs(stock['net'])
        is_heavy_dinosaur = False
        cap_tag = ""
        
        if shares_out and shares_out > 0:
            capital_ratio = net_buy_shares / shares_out
            day_turnover = current['Volume'] / shares_out
            cap_tag = f" | 鎖碼 {capital_ratio*100:.2f}%"
            if capital_ratio < 0.001 and day_turnover < 0.02:
                is_heavy_dinosaur = True
        else:
            vol_ratio = (net_buy_shares / current['Volume']) if current['Volume'] > 0 else 0
            cap_tag = f" | 佔量 {vol_ratio*100:.1f}%"
            if avg_vol_5d > 20000 and vol_ratio < 0.05:
                is_heavy_dinosaur = True
                
        if rank <= 40 and is_heavy_dinosaur:
            rank = 999 
        
        res = {'stock': stock, 'washout': False, 'breakout': False, 'fake_bd': False, 'dry_up': False, 'rod': False, 'current': current, 'tag': cap_tag}
        
        if rank <= 40:
            if current['Close'] > ma20 and ma10 >= ma20:
                price_diff_pct = (current['Close'] - vwap_10d) / vwap_10d
                if current['Close'] >= (vwap_10d * 0.98) and current['Volume'] < (avg_vol_5d * 0.75) and abs(price_diff_pct) <= 0.03:
                    res['washout'] = True
                if current['Close'] >= vwap_10d and current['Volume'] > (avg_vol_5d * 1.5) and current['Close'] > yesterday['Close']:
                    if current['Close'] >= (high_10d * 0.98):
                        res['breakout'] = True

        if current['Low'] < past_9d_low and current['Close'] > yesterday['Close'] and current['Close'] > current['Open']:
            res['fake_bd'] = True
            
        amplitude = (current['High'] - current['Low']) / yesterday['Close']
        if current['Close'] > ma20 and current['Volume'] < (avg_vol_5d * 0.35) and amplitude < 0.015:
            res['dry_up'] = True

        if current['Volume'] > (avg_vol_5d * 1.5):
            body_len = abs(current['Close'] - current['Open'])
            upper_shadow = current['High'] - max(current['Close'], current['Open'])
            lower_shadow = min(current['Close'], current['Open']) - current['Low']
            if upper_shadow > (body_len * 2) and upper_shadow > lower_shadow:
                res['rod'] = True

        return res
    except: return None

# ==========================================
# 🚀 主程式啟動區
# ==========================================
if __name__ == "__main__":
    try:
        tw_now = datetime.utcnow() + timedelta(hours=8)
        
        score = get_macro_score()
        macro_msg = f"🚨【風險：{score}分】風暴來襲！\n" if score >= 75 else (f"⚠️【風險：{score}分】建議觀望。\n" if score >= 50 else f"🟢【風險：{score}分】市場安全。\n")
        us_tech_msg = get_us_tech()
        
        twii = yf.Ticker("^TWII").history(period="5d")
        latest_date = twii.index[-1]
        d_str = latest_date.strftime('%Y%m%d')
        display_date = latest_date.strftime('%Y-%m-%d')
        
        stocks = []
        
        api_url = "https
