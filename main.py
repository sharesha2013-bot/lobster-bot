import os
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
# 📊 宏觀天氣預測
# ==========================================
def get_macro_score():
    score = 0
    reasons = []
    
    try:
        twd = yf.Ticker("TWD=X").history(period="5d")
        if len(twd) >= 2:
            twd_pct = ((twd['Close'].iloc[-1] - twd['Close'].iloc[-2]) / twd['Close'].iloc[-2]) * 100
            if twd_pct > 0.2:
                score += 35
                reasons.append(f"💸台幣急貶(+{twd_pct:.2f}%)")
            elif twd['Close'].iloc[-1] > 32.5: 
                score += 15
                reasons.append("⚠️台幣弱勢")
    except: reasons.append("⚠️匯率雷達斷線")

    try:
        otc = yf.Ticker("^TWO").history(period="1mo")
        if len(otc) >= 2:
            otc_pct = ((otc['Close'].iloc[-1] - otc['Close'].iloc[-2]) / otc['Close'].iloc[-2]) * 100
            otc_ma10 = otc['Close'].tail(10).mean()
            if otc_pct < -1.0: 
                score += 45
                reasons.append(f"🩸櫃買下殺({otc_pct:.2f}%)")
            elif otc['Close'].iloc[-1] < otc_ma10:
                score += 20
                reasons.append("📉櫃買破10日線")
    except:
        score += 20
        reasons.append("⚠️櫃買雷達斷線")

    try:
        twii = yf.Ticker("^TWII").history(period="1mo")
        if len(twii) >= 2:
            twii_pct = ((twii['Close'].iloc[-1] - twii['Close'].iloc[-2]) / twii['Close'].iloc[-2]) * 100
            twii_ma20 = twii['Close'].tail(20).mean()
            if twii_pct < -1.0:
                score += 30
                reasons.append(f"💀大盤下殺({twii_pct:.2f}%)")
            elif twii['Close'].iloc[-1] < twii_ma20:
                score += 20
                reasons.append("📉大盤破月線")
    except:
        score += 20
        reasons.append("⚠️加權雷達斷線")
        
    return score, reasons

# ==========================================
# 🎯 核心大腦：股本透視與攻防分離引擎
# ==========================================
def analyze_stock(args):
    stock, target_date_str, rank, macro_score = args
    stock_id = stock['id']
    try:
        ticker = yf.Ticker(f"{stock_id}.TW")
        df = ticker.history(period="1mo")
        if df.empty: 
            ticker = yf.Ticker(f"{stock_id}.TWO")
            df = ticker.history(period="1mo")
            
        df = df[df['Volume'] > 0].dropna(subset=['Close', 'Volume'])
        if len(df) < 20: return None
        
        shares_out = None
        try:
            shares_out = ticker.fast_info.shares
        except:
            try:
                shares_out = ticker.info.get('sharesOutstanding')
            except: pass
        
        df.index = df.index.tz_localize(None)
        df['date_str'] = df.index.strftime('%Y%m%d')
        
        if target_date_str in df['date_str'].values:
            target_idx = df.index.get_loc(df[df['date_str'] == target_date_str].index[0])
            df = df.iloc[:target_idx + 1]
            
        if len(df) < 20: return None
        
        current = df.iloc[-1]
        yesterday = df.iloc[-2]
        
        # 🧟‍♂️ 殭屍股濾網
        if current['Volume'] < 500000:
            return None
        
        ma5 = df['Close'].tail(5).mean()
        ma10 = df['Close'].tail(10).mean()
        ma20 = df['Close'].tail(20).mean()
        
        # 必須是真實淨買超
        net_buy_shares = stock['net']
        capital_ratio = 0
        if shares_out and shares_out > 0 and net_buy_shares > 0:
            capital_ratio = net_buy_shares / shares_out

        sector_tag = f"[{SECTOR_MAP.get(stock_id, '個股')}]"
        res = {'stock': stock, 'washout': False, 'breakout': False, 'breakout_tier': '', 'current': current, 'tag': '', 'sector': sector_tag}
        
        body_len = abs(current['Close'] - current['Open'])
        upper_shadow = current['High'] - max(current['Close'], current['Open'])
        lower_shadow = min(current['Close'], current['Open']) - current['Low']
        has_rod = (upper_shadow > (body_len * 2)) and (upper_shadow > lower_shadow)
        vol_ratio_yest = current['Volume'] / yesterday['Volume'] if yesterday['Volume'] > 0 else 0
        
        is_uptrend = current['Close'] > ma10 and current['Close'] > ma20

        if rank <= 40:
            # 🧼 洗碗區
            price_diff_ma5 = (current['Close'] - ma5) / ma5
            if net_buy_shares > 0 and capital_ratio >= 0.001 and (-0.01 <= price_diff_ma5 <= 0.03):
                res['washout'] = True
                res['tag'] = f"鎖碼 {capital_ratio*100:.2f}% | 乖離 {price_diff_ma5*100:.1f}%"

            # 🚀 主升段動態過濾
            if net_buy_shares > 0 and current['Close'] > yesterday['Close'] and is_uptrend:
                required_ratio = 0.008 if macro_score >= 50 else 0.005
                real_inst_backing = (stock['f_net'] > 0 or stock['t_net'] > 0) if macro_score >= 50 else True

                if capital_ratio >= required_ratio and real_inst_backing:
                    if has_rod:
                        res['breakout'] = True
                        res['breakout_tier'] = "💀[假突破/避雷針]"
                        res['tag'] = f"量增 {vol_ratio_yest:.1f}倍 | 留心隔日沖"
                    elif vol_ratio_yest >= 2.0:
                        res['breakout'] = True
                        res['breakout_tier'] = "🔥[Lv.2 大噴發]"
                        res['tag'] = f"量增 {vol_ratio_yest:.1f}倍 | 鎖碼 {capital_ratio*100:.2f}%"
                    elif 1.2 <= vol_ratio_yest < 2.0:
                        res['breakout'] = True
                        res['breakout_tier'] = "🟢[Lv.1 溫和點火]"
                        res['tag'] = f"量增 {vol_ratio_yest:.1f}倍 | 鎖碼 {capital_ratio*100:.2f}%"

        return res
    except: return None

# ==========================================
# 🚀 主程式啟動區
# ==========================================
if __name__ == "__main__":
    try:
        # 🚨 計算宏觀風險分數
        score, macro_reasons = get_macro_score()
        reason_str = f" [{', '.join(macro_reasons)}]" if macro_reasons else " [市場籌碼安定]"
        
        if score >= 75: macro_msg = f"🚨【風險：{score}分】風暴來襲！請空手！{reason_str}\n"
        elif score >= 50: macro_msg = f"⚠️【風險：{score}分】警報亮起，縮小部位。{reason_str}\n"
        else: macro_msg = f"🟢【風險：{score}分】環境安全，適合游擊。{reason_str}\n"
            
        twii = yf.Ticker("^TWII").history(period="10d")
        stocks = []
        d_str = ""
        display_date = ""
        
        # 🕵️‍♂️ 智能回溯機制：從最新交易日找起，撲空就往前推 (最多 5 天)
        for offset in range(1, 6):
            latest_date = twii.index[-offset]
            d_str = latest_date.strftime('%Y%m%d')
            display_date = latest_date.strftime('%Y-%m-%d')
            stocks = []
            
            # --- 1. 抓取上市 ---
            api_url = "https://openapi.twse.com.tw/v1/fund/T86_ALL"
            try:
                res = requests.get(api_url, headers=HEADERS, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if data and data[0].get('Date', '').replace('-', '') == d_str:
                        for row in data:
                            stock_id = row.get('Code', '').strip()
                            name = row.get('Name', '').strip()
                            if not stock_id or stock_id.startswith('00'): continue 
                            f_net = int(str(row.get('ForeignInvestorNetBuy', '0')).replace(',', ''))
                            t_net = int(str(row.get('InvestmentTrustNetBuy', '0')).replace(',', ''))
                            net = int(str(row.get('Difference', '0')).replace(',', ''))
                            stocks.append({'id': stock_id, 'name': name, 'f_net': f_net, 't_net': t_net, 'net': net})
            except: pass
                
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
                except: pass

            # --- 2. 抓取上櫃 (🚨 終極防錯版) ---
            try:
                tw_year = latest_date.year - 1911
                otc_date = f"{tw_year}/{latest_date.strftime('%m/%d')}"
                otc_url = f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&o=json&se=EW&t=D&d={otc_date}"
                res_otc = requests.get(otc_url, headers=HEADERS, timeout=10)
                if res_otc.status_code == 200:
                    data_otc = res_otc.json()
                    if 'aaData' in data_otc:
                        for row in data_otc['aaData']:
                            if len(row) > 12: # 🛑 絕對防呆：確保資料列長度夠長
                                try:
                                    stock_id = row[0].strip()
                                    name = row[1].strip()
                                    if not stock_id.isdigit() or len(stock_id) != 4: continue 
                                    f_net_otc = int(row[8].replace(',', ''))
                                    t_net_otc = int(row[11].replace(',', ''))
                                    stocks.append({'id': stock_id, 'name': name, 'f_net': f_net_otc, 't_net': t_net_otc, 'net': f_net_otc + t_net_otc})
                                except: continue # 若轉換失敗直接跳過，不中斷
            except: pass

            # 🛑 只要有資料就跳出回溯迴圈
            if stocks:
                break

        # --- 3. 合併排序與執行 ---
        if not stocks:
            send_msg(f"❌ 龍蝦雷達警告：已回溯 5 個交易日仍無資料，交易所可能維護中。")
        else:
            stocks.sort(key=lambda x: x['net'], reverse=True)
            
            scan_args = []
            for i, s in enumerate(stocks[:150]):
                scan_args.append((s, d_str, i + 1, score))
            
            washout_list, breakout_list = [], []
            
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

            # ================= 組合報告 =================
            msg = f"🦞【戰情室 Pro 終極版｜{display_date}】\n"
            msg += macro_msg
            
            msg += "\n🎯【主力獵殺區｜小股本菁英】\n========================\n"
            
            washout_str = "\n".join(washout_list) if washout_list else "無符合標準"
            msg += f"🟢 洗碗秀 (大戶護盤伏擊)\n{washout_str}\n"
            
            breakout_str = "\n".join(breakout_list) if breakout_list else "無符合標準"
            msg += f"🔴 主升段 (爆量衝鋒點火)\n{breakout_str}\n"
            
            send_msg(msg)

    except Exception as e:
        error_detail = traceback.format_exc()
        send_msg(f"⚠️ 龍蝦系統核心崩潰！\n{str(e)}\n{error_detail[:300]}")
