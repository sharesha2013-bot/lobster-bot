import os
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
DB_FILE = "tdcc_history.json"      # 用來記憶每週集保數據的資料庫
SNIPER_FILE = "sniper_list.json"   # 產出的狙擊名單，供平日程式讀取

def send_msg(text):
    """傳送 Telegram 訊息"""
    if not BOT_TOKEN:
        print("⚠️ 尚未設定 BOT_TOKEN 環境變數。以下為系統輸出：\n")
        print(text)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print(f"Telegram 推播失敗: {e}")

# ==========================================
# 📊 核心模組：獲取並解析官方集保資料
# ==========================================
def fetch_tdcc_data():
    """從集保結算所開放資料下載最新一週的股權分散表"""
    url = "https://smart.tdcc.com.tw/opendata/getOD.ashx?id=1-5"
    print("📡 啟動雷達：正在下載官方集保數據，檔案較大請稍候...")
    
    try:
        # 直接用 pandas 讀取 CSV
        df = pd.read_csv(url)
        
        # 🛡️ 防空包彈裝甲：檢查資料是否為空或格式錯誤
        if df.empty or len(df.columns) < 6:
            print("⚠️ 官方傳回空資料或格式異常。")
            return None
            
        df.columns = ['Date', 'Stock_ID', 'Level', 'People', 'Shares', 'Percent']
        
        # 只保留普通股 (4碼數字)
        df['Stock_ID'] = df['Stock_ID'].astype(str)
        df = df[df['Stock_ID'].str.match(r'^\d{4}$')]
        
        # 定義籌碼級距
        # Level 1~8: 1股 ~ 50,000股 (散戶 50張以下)
        # Level 13~15, 17: 400,001股以上 (大戶 400張以上)
        df['Type'] = 'Other'
        df.loc[df['Level'] <= 8, 'Type'] = 'Retail'
        df.loc[df['Level'] >= 13, 'Type'] = 'Large'
        
        # 計算每檔股票的散戶與大戶佔比總和
        pivot_df = df[df['Type'] != 'Other'].groupby(['Date', 'Stock_ID', 'Type'])['Percent'].sum().unstack(fill_value=0)
        
        # 🛡️ 再次確認重組後的資料是否為空
        result_df = pivot_df.reset_index()
        if result_df.empty:
            return None
            
        return result_df
        
    except Exception as e:
        print(f"⚠️ 下載或解析集保資料失敗: {e}")
        return None

# ==========================================
# 💾 記憶模組：更新本地端集保歷史庫
# ==========================================
def update_history(current_data):
    """將本週數據存入本地 JSON 檔案，以利計算連續三週變化"""
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
    
    # 存檔
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
            
            # 條件一：散戶每週減少 1% ~ 2% (-2.0 <= diff <= -1.0)
            if not (-2.0 <= retail_diff <= -1.0):
                match = False
                break
                
            # 條件二：大戶增加 (diff > 0)
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
        # 1. 抓取最新官方資料
        current_data = fetch_tdcc_data()
        
        # 🛡️ 攔截空資料
        if current_data is not None and not current_data.empty:
            
            # 2. 更新本地歷史資料庫
            history, latest_date = update_history(current_data)
            
            sample_stock = list(history.keys())[0]
            weeks_collected = len(history[sample_stock])
            
            if weeks_collected < 4:
                msg = f"🦞【週末集保雷達｜系統初始化中】\n"
                msg += f"✅ 已成功抓取本週 ({latest_date}) 數據。\n"
                msg += f"⚠️ 目前資料庫僅累積 {weeks_collected} 週數據。\n"
                msg += "需累積滿 4 週才能啟動「連續 3 週大洗盤」濾網，請於下週末再次執行累積。"
                
                with open(SNIPER_FILE, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                    
            else:
                # 3. 執行獵殺掃描
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
            send_msg("⚠️【雷達警報】官方集保資料目前為空或尚在更新中，請稍後或明日再試。")
            
    except Exception as e:
        error_detail = traceback.format_exc()
        error_msg = f"⚠️ 雷達系統發生崩潰！\n{str(e)}\n{error_detail[:500]}"
        print(error_msg)
        send_msg(error_msg)
