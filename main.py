import os
import requests

def main():
    # 這裡放你要查詢的 URL
    url = "https://goodinfo.tw/tw/StockList.asp?RPT_CAT=PER_BUY_SELL&MARKET_CAT=TWSE"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        # 只試著抓一次，沒資料就斷開，絕不循環，絕不嘗試回溯
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            print("成功抓取網頁資料")
            # 這裡我們才開始加過濾條件
        else:
            print("無法連線，直接退出")
    except:
        print("連線錯誤，直接退出")

if __name__ == "__main__":
    main()
