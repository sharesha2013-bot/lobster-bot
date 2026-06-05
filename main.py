import os
import time
import requests
import traceback
import concurrent.futures
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

# ==========================================
# ⚙️ 系統設定區 & 游擊隊族群字典
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

# 游擊隊專屬族群字典 (可自行擴充)
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

# ==========================================
# 📊 輔助模組 (宏觀天氣與美股)
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
    reasons = []
    try:
        # 1. 台幣匯率 (偵測外資提款)
        twd = yf.Ticker("TWD=X").history(period="5d")
        if len(twd) >= 2:
            twd_pct = ((twd['Close'].iloc[-1] - twd['Close'].iloc[-2]) / twd['Close'].iloc[-2]) * 100
            if twd_pct > 0.2:
                score += 35
                reasons.append("💸外資提款(台幣急貶)")
            elif twd['Close'].iloc[-1] > 32.5: 
                score += 15
                reasons.append("⚠️台幣弱勢")

        # 2. 櫃買指數 (偵測中小型股人踩人)
        otc = yf.Ticker("^TWO").history(period="1mo")
        if len(otc) >= 2:
            otc_pct = ((otc['Close'].iloc[-1] - otc['Close'].iloc[-2]) / otc['Close'].iloc[-2]) * 100
            otc_ma10 = otc['Close'].tail(10).mean()
            if otc_pct < -1.5:
                score += 45
                reasons.append("🩸中小型股血崩(櫃買大跌)")
            elif otc['Close'].iloc[-1] < otc_ma10:
                score += 20
                reasons.append("📉櫃買破10日線")

        # 3. 加權指數 (大盤趨勢防禦)
        twii = yf.Ticker("^TWII").history(period="1mo")
        if len(twii) >= 2:
            twii_ma20 = twii['Close'].tail(20).mean()
            if twii['Close'].iloc[-1] < twii_ma20:
                score += 20
                reasons.append("💀大盤跌破月線")
                
    except: pass 
    return score, reasons

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
        
        # 🧟‍♂️ 殭屍股濾網：單日總成交量小於 500 張 (50萬股) 直接無情剔除
        if current['Volume'] < 500000:
            return None
        
        ma5 = df['Close'].tail(5).mean()
        ma10 = df['Close'].tail(10).mean()
        ma20 = df['Close'].tail(20).mean()
        avg_vol_5d = df['Volume'].tail(5).mean()
        
        net_buy_shares = abs(stock['net'])
        capital_ratio = 0
        if shares_out and shares_out > 0:
            capital_ratio = net_buy_shares / shares_out

        sector_tag = f"[{SECTOR_MAP.get(stock_id, '個股')}]"
        
        res = {'stock': stock, 'washout': False, 'breakout': False, 'breakout_tier': '', 'fake_bd': False, 'dry_up': False, 'rod': False, 'current': current, 'tag': '', 'sector': sector_tag}
        
        # 共同特徵計算 (避雷針)
        body_len = abs(current['Close'] - current['Open'])
        upper_shadow = current['High'] - max(current['Close'], current['Open'])
        lower_shadow = min(current['Close'], current['Open']) - current['Low']
        has_rod = (upper_shadow > (body_len * 2)) and (upper_shadow > lower_shadow)
        vol_ratio_yest = current['Volume'] / yesterday['Volume'] if yesterday['Volume'] > 0 else 0

        if rank <= 40:
            # 🧼 洗碗區：鎖碼率 > 0.1%，且收盤價距離 5MA 成本線介於 -1% 到 +3% 之間
            price_diff_ma5 = (current['Close'] - ma5) / ma5
            if capital_ratio >= 0.001 and (-0.01 <= price_diff_ma5 <= 0.03):
                res['washout'] = True
                res['tag'] = f"鎖碼 {capital_ratio*100:.2f}% | 乖離 {price_diff_ma5*100:.1f}%"

            # 🚀 主升段：鎖碼率 > 0.5%，股價收紅，並依爆量與型態分級
            if capital_ratio >= 0.005 and current['Close'] > yesterday['Close']:
                if vol_ratio_yest >= 5.0 or has_rod:
                    res['breakout'] = True
                    res['breakout_tier'] = "💀[Lv.3 高危險]"
                    res['tag'] = f"量增 {vol_ratio_yest:.1f}倍 | 避雷針"
                elif 2.0 <= vol_ratio_yest < 5.0 and not has_rod:
                    res['breakout'] = True
                    res['breakout_tier'] = "🔥[Lv.2 大噴發]"
                    res['tag'] = f"量增 {vol_ratio_yest:.1f}倍 | 鎖碼 {capital_ratio*100:.2f}%"
                elif 1.2 <= vol_ratio_yest < 2.0 and not has_rod:
                    res['breakout'] = True
                    res['breakout_tier'] = "🟢[Lv.1 剛點火]"
                    res['tag'] = f"量增 {vol_ratio_yest:.1f}倍 | 鎖碼 {capital_ratio*100:.2f}%"

        # 🪤 極端吃屍區邏輯
        past_9d_low = df['Low'].iloc[-10:-1].min()
        if current['Low'] < past_9d_low and current['Close'] > yesterday['Close'] and current['Close'] > current['Open']:
            res['fake_bd'] = True
            
        amplitude = (current['High'] - current['Low']) / yesterday['Close']
        if current['Close'] > ma20 and current['Volume'] < (avg_vol_5d * 0.35) and amplitude < 0.015:
            res['dry_up'] = True

        if current['Volume'] > (avg_vol_5d * 1.5) and has_rod:
            res['rod'] = True

        return res
    except: return None

# ==========================================
# 🚀 主程式啟動區
# ==========================================
if __name__ == "__main__":
    try:
        tw_now = datetime.utcnow() + timedelta(hours=8)
        
        # 🚨 台股專屬風暴預警
        score, macro_reasons = get_macro_score()
        reason_str = f" [{', '.join(macro_reasons)}]" if macro_reasons else " [市場籌碼安定]"
        
        if score >= 75:
            macro_msg = f"🚨【風險：{score}分】風暴來襲！請空手！{reason_str}\n"
        elif score >= 50:
            macro_msg = f"⚠️【風險：{score}分】警報亮起，縮小部位。{reason_str}\n"
        else:
            macro_msg = f"🟢【風險：{score}分】環境安全，適合游擊。{reason_str}\n"
            
        us_tech_msg = get_us_tech()
        
        twii = yf.Ticker("^TWII").history(period="5d")
        latest_date = twii.index[-1]
        d_str = latest_date.strftime('%Y%m%d')
        display_date = latest_date.strftime('%Y-%m-%d')
        
        stocks = []
        
        api_url = "https://openapi.twse.com.tw/v1/fund/T86_ALL"
        try:
            res = requests.get(api_url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for row in data:
                    stock_id = row.get('Code', '').strip()
                    name = row.get('Name', '').strip()
                    if not stock_id or stock_id.startswith('00'): continue 
                    f_net = int(str(row.get('ForeignInvestorNetBuy', '0')).replace(',', ''))
                    t_net = int(str(row.get('InvestmentTrustNetBuy', '0')).replace(',', ''))
                    net = int(str(row.get('Difference', '0')).replace(',', ''))
                    stocks.append({'id': stock_id, 'name': name, 'f_net': f_net, 't_net': t_net, 'net': net})
        except Exception as e:
            print(f"Open API 遇到干擾: {e}")
            
        if not stocks:
            url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
            try:
                res = requests.get(url, headers=HEADERS, timeout=10)
                if res.status_code == 200:
                    res_json = res.json()
                    if res_json.get('stat') == 'OK':
                        for row in res_json['data']:
                            if len(row) > 18:
                                stock_id = row[0].strip()
                                name = row[1].strip()
                                if stock_id.startswith('00'): continue 
                                f_net = int(row[4].replace(',', '')) if row[4] != '--' else 0
                                t_net = int(row[10].replace(',', '')) if row[10] != '--' else 0
                                stocks.append({'id': stock_id, 'name': name, 'f_net': f_net, 't_net': t_net, 'net': f_net + t_net})
            except Exception as backup_e:
                print(f"備用引擎也失敗: {backup_e}")

        if not stocks:
            send_msg(f"❌ 兩套資料引擎皆抓取失敗，證交所可能維護中。")
        else:
            stocks.sort(key=lambda x: x['net'], reverse=True)
            
            scan_args = []
            for i, s in enumerate(stocks[:150]):
                scan_args.append((s, d_str, i + 1))
            for s in stocks[-50:]:
                scan_args.append((s, d_str, 999))
            
            washout_list, breakout_list = [], []
            fake_bd_list, dry_up_list = [], []
            rod_list = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                results = list(executor.map(analyze_stock, scan_args))
                
            for res in results:
                if not res: continue
                s = res['stock']
                price = res['current']['Close']
                tag = res['tag']
                sector = res['sector']
                
                if res['washout']: washout_list.append(f"• {sector} {s['id']} {s['name']}: 價 {price:.1f} ({tag})")
                if res['breakout']: breakout_list.append(f"• {res['breakout_tier']} {sector} {s['id']} {s['name']}: 價 {price:.1f} ({tag})")
                if res['fake_bd']: fake_bd_list.append(f"• {sector} {s['id']} {s['name']}: 價 {price:.1f} (殺盤洗停損)")
                if res['dry_up']: dry_up_list.append(f"• {sector} {s['id']} {s['name']}: 價 {price:.1f} (極度鎖死)")
                if res['rod']: rod_list.append(f"• {sector} {s['id']} {s['name']}: 價 {price:.1f} (爆量被出貨)")

            it_dump_list = sorted([s for s in stocks if s['t_net'] < -1500], key=lambda x: x['t_net'])[:5]
            
            # ================= 組合報告 =================
            msg = f"🦞【戰情室 Pro 終極版｜{display_date}】\n"
            msg += macro_msg + us_tech_msg
            
            msg += "\n🎯【主力獵殺區｜小股本菁英】\n========================\n"
            
            washout_str = "\n".join(washout_list) if washout_list else "無"
            msg += f"🟢 洗碗秀 (大戶護盤伏擊)\n{washout_str}\n"
            
            breakout_str = "\n".join(breakout_list) if breakout_list else "無"
            msg += f"🔴 主升段 (爆量衝鋒點火)\n{breakout_str}\n"
            
            msg += "\n🥷【闇黑兵法｜極端吃屍區】\n========================\n"
            
            fake_bd_str = "\n".join(fake_bd_list) if fake_bd_list else "無符合 (市場無恐慌錯殺)"
            msg += f"🪤 破底翻 (假跌破真誘空)\n{fake_bd_str}\n"
            
            dry_up_str = "\n".join(dry_up_list) if dry_up_list else "無符合 (市場籌碼尚在浮動)"
            msg += f"🩸 終極窒息量 (主力偷偷鎖碼)\n{dry_up_str}\n"
            
            msg += "\n💀【高危雷區｜請勿接刀】\n========================\n"
            msg += "🔪 投信無情結帳:\n"
            if it_dump_list:
                for s in it_dump_list:
                    msg += f"• {s['id']} {s['name']}: 賣 {abs(int(s['t_net']/1000))} 張\n"
            else:
                msg += "無\n"
                
            rod_str = "\n".join(rod_list) if rod_list else "無"
            msg += f"⚡ 散戶絞肉機 (避雷針):\n{rod_str}\n"
            
            msg += "\n🔥 買超 Top 5 (大戶動向):\n"
            for s in stocks[:5]:
                msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張{get_heat_level_tag(s['net'])}\n"
                
            msg += "\n⚠️ 倒貨警報 (不死鳥):\n"
            found_bird = False
            for s in stocks[-10:][::-1]:
                bird_tag = check_undying_bird(s['id'], d_str)
                if bird_tag:
                    msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張{bird_tag}\n"
                    found_bird = True
            if not found_bird:
                msg += "無\n"
            
            msg += "\n🎯【主力狙擊鏡｜土洋合買】:\n"
            count = 0
            for s in stocks:
                if s['f_net'] > 0 and s['t_net'] > 0 and s['net'] > 1000000: 
                    msg += f"⚡ {s['id']} {s['name']}: 共買 {int(s['net']/1000)} 張 (外{int(s['f_net']/1000)}/投{int(s['t_net']/1000)})\n"
                    count += 1
                if count >= 5: break
            if count == 0:
                msg += "無土洋合買標的。\n"
                
            send_msg(msg)

    except Exception as e:
        error_detail = traceback.format_exc()
        send_msg(f"⚠️ 龍蝦系統核心崩潰！\n{str(e)}\n{error_detail[:300]}")
