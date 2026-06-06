import os
import requests

def main():
    # 這是最後的確認：直接對 Telegram API 發送一則強制訊息
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = "8543567603"
    
    if not bot_token:
        print("錯誤：找不到 BOT_TOKEN 環境變數")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "✅ 龍蝦雷達：系統運作中，通訊連線正常。"
    }
    
    response = requests.post(url, json=payload)
    print(f"發送狀態碼: {response.status_code}")
    print(f"回傳內容: {response.text}")

if __name__ == "__main__":
    main()
