
import os
import time
import requests
import traceback
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ==========================================
# ⚙️ 系統設定
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_telegram(text):
    """傳送 Telegram 訊息，自動分段避免超過 4000 字元限制"""
    if not BOT_TOKEN:
        print("⚠️ 尚未設定 BOT_TOKEN。以下為本地端輸出：\n")
        print(text)
        return
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Telegram 訊息長度限制為 4096，保守抓 4000
    chunk_size = 4000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    for chunk in chunks:
        try:
            requests.post(url, json={"chat_id": CHAT_ID, "text": chunk}, timeout=10)
            time.sleep(1) # 避免連續發送遭 Telegram 阻擋
        except Exception as e:
            print(f"⚠️ Telegram 推播失敗: {e}")

# ==========================================
# 📡 模組 1：尋找最近有效的交易日
# ==========================================
def get_valid_trading_days(days_needed=5, max_lookback=15):
    """從今天開始往前回溯，找出證交所有資料的 n 個交易日"""
    valid_dates = []
    current_date = datetime.now()
    lookback = 0
    
    print(f"📡 尋找最近 {days_needed} 個交易日資料...")
    
    while len(valid_dates) < days_needed and lookback < max_lookback:
        d_str = current_date.strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
        
        try:
            res = requests.get(url, timeout=10)
            data = res.json()
            if data.get('stat') == 'OK':
                valid_dates.append(d_str)
                print(f"✅ 取得交易日: {d_str}")
            time.sleep(1.5) # 友善延遲，保護 API
        except Exception as e:
            print(f"⚠️ {d_str} 抓取失敗，繼續往前回溯...")
            
        current_date -= timedelta(days=1)
        lookback += 1
        
    return valid_dates

# ==========================================
# 📊 模組 2：抓取官方籌碼與融資數據
# ==========================================
def fetch_twse_data(valid_dates):
    """獲取指定日期的三大法人買賣超與融資數據"""
    # stocks_data 結構: {sid: {'name': name, 'foreign': [], 'it': [], 'margin': []}}
    stocks_data = {}
    
    for d_str in valid_dates:
        # 1. 抓取三大法人 (T86)
        inst_url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
        try:
            res = requests.get(inst_url, timeout=10)
            data = res.json()
            if data.get('stat') == 'OK':
                for row in data['data']:
                    sid = row[0].strip()
                    name = row[1].strip()
                    
                    if sid.startswith('00'): continue # 排除 ETF
                    
                    if sid not in stocks_data:
                        stocks_data[sid] = {'name': name, 'foreign': [], 'it': [], 'margin': []}
                        
                    try:
                        f_buy = int(row[4].replace(',', ''))  # 外資及陸資買賣超股數
                        it_buy = int(row[10].replace(',', '')) # 投信買賣超股數
                        # 單位換算為張
                        stocks_data[sid]['foreign'].append(f_buy // 1000)
                        stocks_data[sid]['it'].append(it_buy // 1000)
                    except:
                        stocks_data[sid]['foreign'].append(0)
                        stocks_data[sid]['it'].append(0)
            time.sleep(1.5)
        except Exception as e:
            print(f"⚠️ 法人資料 {d_str} 抓取失敗: {e}")

        # 2. 抓取信用交易/融資 (MI_MARGN)
        margin_url = f"https://www.twse.com.tw/exchangeReport/MI_MARGN?response=json&date={d_str}&selectType=ALL"
        try:
            res = requests.get(margin_url, timeout=10)
            data = res.json()
            if data.get('stat') == 'OK':
                # MI_MARGN 的表格有多個，通常 ['data'] 包含個股明細
                # 欄位：0代號, 1名稱, 2買進, 3賣出, 4現金償還, 5前日餘額, 6今日餘額
                for row in data.get('data', []):
                    sid = row[0].strip()
                    if sid in stocks_data:
                        try:
                            margin_balance = int(row[6].replace(',', ''))
                            stocks_data[sid]['margin'].append(margin_balance)
                        except:
                            stocks_data[sid]['margin'].append(0)
            time.sleep(1.5)
        except Exception as e:
            print(f"⚠️ 融資資料 {d_str} 抓取失敗: {e}")

    return stocks_data

# ==========================================
# 🎯 模組 3：分析候選名單與連買邏輯
# ==========================================
def analyze_candidates(stocks_data):
    """計算連買天數與融資變化，篩選出須進行技術面驗證的候選名單"""
    candidates = []
    minefield_candidates = []
    
    for sid, data in stocks_data.items():
        # 反轉陣列，讓 index 0 是最新的一天 (T日, T-1, T-2...)
        f_list = data['foreign'][::-1]
        it_list = data['it'][::-1]
        m_list = data['margin'][::-1]
        
        # 計算連買天數
        f_consec = 0
        for vol in f_list:
            if vol > 0: f_consec += 1
            else: break
            
        it_consec = 0
        for vol in it_list:
            if vol > 0: it_consec += 1
            else: break
            
        # 計算 5 日累積買超張數
        total_buy = sum(f_list) + sum(it_list)
        
        # 融資減少百分比
        margin_decrease_pct = 0.0
        if len(m_list) >= 2 and m_list[-1] > 0:
            latest_margin = m_list[0]
            oldest_margin = m_list[-1]
            margin_decrease_pct = ((latest_margin - oldest_margin) / oldest_margin) * 100

        # --- 判斷邏輯 ---
        is_accumulation = False
        is_minefield = False
        
        # 法人布局區條件：外資或投信連買 >= 3天
        if f_consec >= 3 or it_consec >= 3:
            is_accumulation = True
            
        # 避雷區條件一：今日投信賣超 > 1000張
        if len(it_list) > 0 and it_list[0] <= -1000:
            is_minefield = True
            
        if is_accumulation or is_minefield:
            candidates.append({
                'sid': sid,
                'name': data['name'],
                'f_consec': f_consec,
                'it_consec': it_consec,
                'total_buy': total_buy,
                'margin_pct': margin_decrease_pct,
                'is_accum': is_accumulation,
                'is_mine': is_minefield,
                'it_latest': it_list[0] if len(it_list) > 0 else 0
            })
            
    return candidates

# ==========================================
# 📈 模組 4：Yahoo Finance 技術面確認
# ==========================================
def check_technicals(candidates):
    """透過 yfinance 驗證 MA20、成交量、K線型態"""
    print(f"📡 進入技術面驗證，共 {len(candidates)} 檔標的...")
    
    uptrend_list = []
    accum_list = []
    minefield_list = []
    
    for cand in candidates:
        sid = cand['sid']
        
        try:
            # 優先嘗試 .TW，無資料改 .TWO (皆使用 yfinance 防當機機制)
            tick = yf.Ticker(f"{sid}.TW")
            hist = tick.history(period="2mo")
            if hist.empty or len(hist) < 20:
                tick = yf.Ticker(f"{sid}.TWO")
                hist = tick.history(period="2mo")
                
            if hist.empty or len(hist) < 20:
                continue # 資料不足，放棄該檔，保證不崩潰
                
            close = hist['Close'].iloc[-1]
            open_p = hist['Open'].iloc[-1]
            high_p = hist['High'].iloc[-1]
            volume = hist['Volume'].iloc[-1] # yf volume 為股數
            
            ma20 = hist['Close'].tail(20).mean()
            ma20_prev = hist['Close'].shift(1).tail(20).mean()
            
            turnover = close * volume # 成交值 (元)
            vol_5d_avg = hist['Volume'].tail(5).mean()
            
            # --- 指標計算 ---
            is_above_ma20 = close > ma20
            is_ma20_up = ma20 > ma20_prev
            is_high_turnover = turnover > 100000000 # 成交值 > 1億
            is_vol_spike = volume > (1.5 * vol_5d_avg)
            
            # 爆量長上影判斷：上影線長度 > 實體 K 線的 2 倍
            real_body = abs(close - open_p)
            upper_shadow = high_p - max(close, open_p)
            is_long_upper = upper_shadow > (real_body * 2) and real_body > 0
            
            # ==========================
            # 🎯 條件分流
            # ==========================
            added_to_mine = False
            
            # 【第五關：避雷區】
            mine_reasons = []
            if cand['it_latest'] <= -1000:
                mine_reasons.append(f"投信大賣 {abs(cand['it_latest'])}張")
            if not is_above_ma20:
                mine_reasons.append("跌破 MA20")
            if is_vol_spike and is_long_upper:
                mine_reasons.append("爆量長上影")
                
            if mine_reasons and (cand['is_mine'] or cand['is_accum']):
                minefield_list.append({
                    'sid': sid, 'name': cand['name'],
                    'price': close, 'reason': "、".join(mine_reasons)
                })
                added_to_mine = True
                
            # 如果已經進避雷區，就不排入好名單
            if added_to_mine:
                continue

            # 【第四關：主升段雷達】 & 【第一關：法人布局區】
            if cand['is_accum']:
                base_str = f"• {sid} {cand['name']} | 價: {close:.1f} | MA20: {ma20:.1f}\n  外買:{cand['f_consec']}天 投買:{cand['it_consec']}天 | 累積:{cand['total_buy']}張"
                
                # 融資洗盤加分 (第二關)
                margin_str = f" | 融資洗盤: {cand['margin_pct']:.1f}%" if cand['margin_pct'] <= -5.0 else ""
                full_str = base_str + margin_str
                
                # 第三關 & 第四關技術確認
                if is_above_ma20 and is_ma20_up and is_high_turnover and is_vol_spike:
                    uptrend_list.append(full_str)
                elif is_above_ma20 and is_ma20_up and is_high_turnover:
                    accum_list.append(full_str)

        except Exception as e:
            # 遇到單一股票報錯，忽略並繼續下一檔
            continue

    return uptrend_list, accum_list, minefield_list

# ==========================================
# 🚀 系統主程式
# ==========================================
def main():
    try:
        print("啟動龍蝦雷達 V3...")
        # 1. 取得最新 5 個交易日
        valid_dates = get_valid_trading_days(days_needed=5)
        if not valid_dates:
            send_telegram("⚠️ 龍蝦雷達 V3：無法從證交所獲取任何交易日資料，系統安全中止。")
            return
            
        report_date = valid_dates[0] # 最新交易日
        
        # 2. 獲取證交所籌碼
        stocks_data = fetch_twse_data(valid_dates)
        
        # 3. 分析候選名單
        candidates = analyze_candidates(stocks_data)
        
        # 4. 技術面確認與分流
        uptrend, accum, minefield = check_technicals(candidates)
        
        # 5. 組裝報表
        msg = f"🦞【龍蝦雷達 V3】\n📅 結算日: {report_date}\n\n"
        
        msg += "🔥【主升段雷達】(法人連買+站上MA20且上彎+出量)\n"
        msg += "="*35 + "\n"
        msg += "\n\n".join(uptrend) if uptrend else "今日無符合標的"
        msg += "\n\n"
        
        msg += "🛡️【法人布局區】(外資/投信連買3天+站上MA20)\n"
        msg += "="*35 + "\n"
        msg += "\n\n".join(accum) if accum else "今日無符合標的"
        msg += "\n\n"
        
        msg += "⚠️【避雷區】(籌碼鬆動/跌破線型)\n"
        msg += "="*35 + "\n"
        if minefield:
            for m in minefield:
                msg += f"• {m['sid']} {m['name']} | 價: {m['price']:.1f}\n  原因: {m['reason']}\n"
        else:
            msg += "今日無避雷標的"
            
        # 6. 安全推播
        send_telegram(msg)
        print("✅ 龍蝦雷達 V3 執行完畢！")

    except Exception as e:
        error_msg = f"⚠️ 龍蝦雷達 V3 發生未預期錯誤:\n{str(e)}\n{traceback.format_exc()[:500]}"
        send_telegram(error_msg)
        print(error_msg)

if __name__ == "__main__":
    main()
