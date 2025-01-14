import requests
import json
import os
from dotenv import load_dotenv  

# .envを読み込む
load_dotenv()

# 環境変数から設定を取得
BASE_URL = os.getenv("BASE_URL")  # サーバーのURL
VERIFY_SSL = False # SSL証明書 os.getenv("VERIFY_SSL") 自己署名の場合なのでFalse
SECRET_KEY = os.getenv("SECRET_KEY_id2") # .envから取得

# 更新するデータ
max_capacity = 44
current_count = 1
data = {
    "id": 4,
    "name": "学生協",
    "sub_name": "19号館1階",
    "max_capacity": max_capacity,
    "current_count": current_count
}

# データを送信する関数
def send_crowd_data():
    url = f"{BASE_URL}/api/sendCrowdLevel"
    
    # ヘッダー情報を設定
    headers = {
        "Content-Type": "application/json",  # JSONデータ送信を明示
        "Authorization": SECRET_KEY,  # サーバーが期待するトークン
    }

    try:
        # POSTリクエストを送信
        response = requests.post(url, json=data, headers=headers, verify=VERIFY_SSL)

        # レスポンスの確認
        if response.status_code == 200:
            print("Success:", response.json())
        else:
            print(f"Failed to send data. Status code: {response.status_code}")
            print("Response:", response.json())
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

# 実行
if __name__ == "__main__":
    if not BASE_URL:
        print("BASE_URLが設定されていません。")
    else:
        send_crowd_data()
