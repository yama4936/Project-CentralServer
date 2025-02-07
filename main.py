from fastapi import FastAPI, Request, Header
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_403_FORBIDDEN
import json
import os
#.envから読み込む設定
import jwt
import requests
from dotenv import load_dotenv 
import sqlite3
import datetime

# .envを読み込む
load_dotenv()  

# 定数
JSON_FILE_PATH = "data.json"
TEMPLATE_DIR = "templates"
STATIC_DIR = "build"
SECRET_KEYS = {os.getenv("SECRET_KEY_id1"), os.getenv("SECRET_KEY_id2"), os.getenv("SECRET_KEY_id3"),os.getenv("SECRET_KEY_id4") } # .envから取得

# POSTで受け取るデータモデル
class FacilityInfo(BaseModel):
    id: int = Field(..., description="施設のID")
    name: str = Field(..., min_length=1, max_length=50, description="施設名")
    sub_name: str = Field(..., min_length=1, max_length=50, description="施設の場所")
    max_capacity: int = Field(..., ge=0, description="最大収容人数")
    current_count: int = Field(..., ge=0, description="現在の人数")

app = FastAPI()

# 静的ファイルの設定
app.mount("/static", StaticFiles(directory=os.path.join(STATIC_DIR, "static")), name="static")
app.mount("/images", StaticFiles(directory=os.path.join(STATIC_DIR, "images")), name="images")


# 後のためのCORS回避
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_current_weekday():
    return datetime.datetime.now().weekday()  # 0: 月曜日, 6: 日曜日

def update_json(facilities, facility_id, new_data):
    for facility in facilities:
        if facility["id"] == facility_id:
            facility.update(new_data)
            return True
    return False

def save_to_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# 混雑状況確認ページを表示
@app.get("/", response_class=HTMLResponse)
async def serve_react_app(request: Request):
    react_index_path = os.path.join("build", "index.html")
    if os.path.exists(react_index_path):
        with open(react_index_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return HTMLResponse(content=content)
    return JSONResponse(content={"error": "index.html not found"}, status_code=404)

# JSONファイルの提供
@app.get("/api/getJsonData")
async def get_json_data():
    try:
        # JSONファイルを読み込む
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # JSONレスポンスとして返す
            return JSONResponse(content=data)
    except FileNotFoundError:
        return JSONResponse(content={"error": "File not found"}, status_code=404)
    except json.JSONDecodeError:
        return JSONResponse(content={"error": "Invalid JSON format"}, status_code=400)

# POSTエンドポイント
@app.post("/api/sendCrowdLevel")
async def update(info: FacilityInfo, authorization: str = Header(None)):
    # ヘッダーの検証
    if not authorization or authorization not in SECRET_KEYS: # トークンの検証 適当な文字列を入れる
        return JSONResponse(
            content={"error": "Unauthorized access"},
            status_code=HTTP_403_FORBIDDEN
        )

    # JSONファイルを読み込む
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        return JSONResponse(content={"error": "File not found"}, status_code=404)
    except json.JSONDecodeError:
        return JSONResponse(content={"error": "Invalid JSON format"}, status_code=400)

    # 更新データの作成
    new_data = {
        "max_capacity": info.max_capacity,
        "current_count": info.current_count
    }

    # id一致で情報更新
    if update_json(data["facilities"], info.id, new_data):
        save_to_json(JSON_FILE_PATH, data)

        try:
            # データベース接続を管理
            with sqlite3.connect("data.db") as conn:
                # カーソルは明示的に管理
                cursor = conn.cursor()
                try:
                    cursor.execute('''
                        INSERT INTO data (id, max_value, current_value)
                        VALUES (?, ?, ?)
                    ''', (info.id, info.max_capacity, info.current_count))
                finally:
                    # カーソルを閉じる
                    cursor.close()

            print("update_data is correct!")
            return {
                "message": "Data updated successfully",
            }

        except sqlite3.Error as e:
            # SQLiteエラー時の処理
            raise RuntimeError(f"Database error occurred: {e}")
        
    else:
        print("update_json error")
        return {"Result" : "update_json is faild!"}

@app.get("/api/weekly_average")
async def get_weekly_average():
    current_weekday = get_current_weekday()

    # 日付の範囲を設定
    today = datetime.datetime.now()
    one_week_ago = today - datetime.timedelta(days=7)
    one_week_ago_start = one_week_ago.replace(hour=0, minute=0, second=0, microsecond=0)
    one_week_ago_end = one_week_ago.replace(hour=23, minute=59, second=59, microsecond=999999)

    try:
        with sqlite3.connect("data.db") as conn:
            cursor = conn.cursor()

            # 先週の同じ曜日に該当するデータを30分ごとに集計
            query = f"""
            SELECT 
                id,
                strftime('%Y-%m-%d %H:%M', created_at, 'localtime') AS time_block,
                AVG(current_value) AS avg_current
            FROM data
            WHERE strftime('%w', created_at) = '{current_weekday}' AND created_at BETWEEN '{one_week_ago_start}' AND '{one_week_ago_end}'
            GROUP BY id, time_block
            ORDER BY id, time_block;
            """
            cursor.execute(query)
            results = cursor.fetchall()

            # idごとに施設のデータを整理
            facility_data = {}
            for row in results:
                facility_id = row[0]
                if facility_id not in facility_data:
                    facility_data[facility_id] = {
                        "id": facility_id,
                        "time_blocks": []
                    }
                facility_data[facility_id]["time_blocks"].append({
                    "time_block": row[1],
                    "average_current_value": row[2]
                })

            # JSON形式のリストを整形
            response_data = list(facility_data.values())

            return JSONResponse(content=response_data)

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}
