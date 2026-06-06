import os
import json
import requests
import pandas as pd
import io

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"
DB_FILE = "tdcc_history.json"
SNIPER_FILE = "sniper_list.json"

def send_msg(text):
    if BOT_TOKEN:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    print(text)

def fetch_data():
    url = "https://smart.tdcc.com.tw/opendata/getOD.ashx?id=1-5"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers, timeout=60)
    df = pd.read_csv(io.StringIO(res.text))
    df.columns = ['Date', 'Stock_ID', 'Level', 'People', 'Shares', 'Percent']
    # 只抓散戶 (Level 1-8 是 50張以下)
    df = df[df['Level'] <= 8]
    df['Stock_ID'] = df['Stock_ID'].astype(str)
    return df.groupby(['Date', 'Stock_ID'])['Percent'].sum().reset_index()

def main():
    try:
        new_data = fetch_data()
        latest_date = str(new_data['Date'].iloc[0])
        
        # 讀取歷史並更新
        history = {}
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r') as f: history = json.load(f)
            
        for _, row in new_data.iterrows():
            sid = row['Stock_ID']
            if sid not in history: history[sid] = {}
            history[sid][latest_date] = row['Percent']
            
        with open(DB_FILE, 'w') as f: json.dump(history, f)
        
        # 篩選條件
        targets = []
        for sid, records in history.items():
            dates = sorted(records.keys())
            if len(dates) < 4: continue
            
            # 檢查最近 3 次週變化
            match = True
            for i in range(-3, 0):
                diff = records[dates[i]] - records[dates[i-1]]
                if diff > -2.0: # 必須減少 2% 以上
                    match = False
                    break
            
            if match: targets.append(sid)
            
        with open(SNIPER_FILE, 'w') as f: json.dump(targets, f)
        send_msg(f"🦞【狙擊名單更新】日期: {latest_date}\n目標: {', '.join(targets)}")
        
    except Exception as e:
        send_msg(f"⚠️ 程式崩潰: {str(e)}")

if __name__ == "__main__":
    main()
