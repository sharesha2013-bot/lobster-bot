import os
import io
import json
import requests
import traceback
import pandas as pd
from datetime import datetime

# ==========================================
# ⚙️ 系統設定區
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"
DB_FILE = "tdcc_history.json"      
SNIPER_FILE = "sniper_list.json"   

# 🛡️ 啟動 PRO 級偽裝裝甲
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/csv,application/csv,text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
}

def send_msg(text):
    if not BOT_TOKEN:
        print("⚠️ 尚未設定 BOT_TOKEN。\n" + text)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print(f"Telegram 推播失敗: {e}")

# ==========================================
# 📊 核心模組：偽裝並獲取官方集保資料
# ==========================================
def fetch_tdcc_data():
    url = "https://smart.tdcc.com.tw/opendata/getOD.ashx?id=1-5"
    print("📡 啟動隱形雷達：正在突破官方防線下載數據...")
    
    try:
        # 🛡️ 1. 用真人偽裝去發送請求
        res = requests.get(url, headers=HEADERS, timeout=30)
        
        if res.status_code != 200:
            print(f"⚠️ 連線遭拒，狀態碼: {res.status_code}")
            return None
            
        # 🛡️ 2. 確認抓回來的是不是真的 CSV (防網頁阻擋)
        if "<html>" in res.text.lower() or "error" in res.text.lower()[:50]:
            print("⚠️ 遭遇官方網頁防火牆阻擋！")
            return None
            
        # 🛡️ 3. 將文字轉換成資料表
        df = pd.read_csv(io.StringIO(res.text))
        
        if df.empty or len(df.columns) < 6:
            print("⚠️ 檔案格式異常或為空。")
            return None
            
        df.columns = ['Date', 'Stock_ID', 'Level', 'People', 'Shares', 'Percent']
        
        df['Stock_ID'] = df['Stock_ID'].astype(str)
        df = df[df['Stock_ID'].str.match(r'^\d{4}$')]
        
        df['Type'] = 'Other'
        df.loc[df['Level'] <= 8, 'Type'] = 'Retail'
        df.loc[df['Level'] >= 13, 'Type'] = 'Large'
        
        pivot_df = df[df['Type'] != 'Other'].groupby(['Date', 'Stock_ID', 'Type'])['Percent'].sum().unstack(fill_value=0)
        
        result_df = pivot_df.reset_index()
        if result_df.empty:
            return None
            
        return result_df
        
    except Exception as e:
        print(f"⚠️ 數據解析失敗: {e}")
        return None

# ==========================================
# 💾 記憶模組：更新本地端集保歷史庫
# ==========================================
def update_history(current_data):
    history = {}
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
            
    latest_date = str(current_data['Date'].iloc[0])
    
    for _, row in current_data.iterrows():
        stock_id = row['Stock_ID']
        retail_pct = row.get('Retail', 0)
        large_pct = row.get('Large', 0)
        
        if stock_id not in history:
            history[stock_id] = {}
            
        history[stock_id][latest_date] = {
            'retail': round(retail_pct, 2),
            'large': round(large_pct, 2)
        }
    
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
        
    return history, latest_date

# ==========================================
# 🎯 獵殺模組：連續 3 週散戶退、大戶進
# ==========================================
def scan_sniper_targets(history):
    targets = []
    
    for stock_id, date_records in history.items():
        sorted_dates = sorted(date_records.keys())
        
        if len(sorted_dates) < 4:
            continue
            
        recent_4 = sorted_dates[-4:]
        match = True
        total_retail_drop = 0
        
        for i in range(3):
            prev_week = date_records[recent_4[i]]
            curr_week = date_records[recent_4[i+1]]
            
            retail_diff = curr_week['retail'] - prev_week['retail']
            large_diff = curr_week['large'] - prev_week['large']
            
            if not (-2.0 <= retail_diff <= -1.0):
                match = False
                break
                
            if large_diff <= 0:
                match = False
                break
                
            total_retail_drop += retail_diff
            
        if match:
            targets.append({
                'id': stock_id,
                'drop': round(abs(total_retail_drop), 2)
            })
            
    return targets

# ==========================================
# 🚀 主程式啟動區
# ==========================================
if __name__ == "__main__":
    try:
        current_data = fetch_tdcc_data()
        
        if current_data is not None and not current_data.empty:
            history, latest_date = update_history(current_data)
            
            sample_stock = list(history.keys())[0]
            weeks_collected = len(history[sample_stock])
            
            if weeks_collected < 4:
                msg = f"🦞【週末集保雷達｜系統初始化中】\n"
                msg += f"✅ 已成功突破防線抓取本週 ({latest_date}) 數據。\n"
                msg += f"⚠️ 目前資料庫僅累積 {weeks_collected} 週數據。\n"
                msg += "需累積滿 4 週才能啟動「連續 3 週大洗盤」濾網，請於下週末再次執行累積。"
                
                with open(SNIPER_FILE, 'w', encoding='utf-8') as f:
                    json.dump([], f)
            else:
                targets = scan_sniper_targets(history)
                
                msg = f"🦞【週末大雷達｜地獄洗盤狙擊名單】\n"
                msg += f"結算日期: {latest_date}\n"
                msg += "="*35 + "\n"
                
                if targets:
                    sniper_ids = []
                    for t in targets:
                        msg += f"🎯 {t['id']} (3週散戶累計流失 {t['drop']}% | 大戶連續增)\n"
                        sniper_ids.append(t['id'])
                        
                    with open(SNIPER_FILE, 'w', encoding='utf-8') as f:
                        json.dump(sniper_ids, f)
                    msg += "\n✅ 已自動寫入狙擊名單，平日系統將自動鎖定。"
                else:
                    msg += "本週全台股無符合「連續 3 週散戶減 1~2% 且大戶增」之極端標的。"
                    with open(SNIPER_FILE, 'w', encoding='utf-8') as f:
                        json.dump([], f)
            
            send_msg(msg)
        else:
            send_msg("⚠️【雷達警報】官方阻擋或格式異常，請檢查伺服器連線狀態。")
            
    except Exception as e:
        error_detail = traceback.format_exc()
        error_msg = f"⚠️ 雷達系統發生崩潰！\n{str(e)}\n{error_detail[:500]}"
        print(error_msg)
        send_msg(error_msg)
