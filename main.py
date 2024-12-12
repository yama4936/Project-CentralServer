from fastapi import FastAPI, Request, HTTPException, Header
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_403_FORBIDDEN
import json
import os

# 定数
JSON_FILE_PATH = "data.json"
TEMPLATE_DIR = "templates"
STATIC_DIR = "static"

# POSTで受け取るデータモデル
class FacilityInfo(BaseModel):
    id: int = Field(..., description="施設のID")
    name: str = Field(..., min_length=1, max_length=50, description="施設名")
    max_capacity: int = Field(..., ge=0, description="最大収容人数")
    current_count: int = Field(..., ge=0, description="現在の人数")

# テンプレートのパスを指定
templates = Jinja2Templates(directory=TEMPLATE_DIR)

app = FastAPI()

# 静的ファイルの設定
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 後のためのCORS回避
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
@app.get("/")
async def get_html(request: Request):
    #JSONファイルの読み込み
    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as file:
        data = json.load(file)

    return templates.TemplateResponse("index.html", {"request": request, "facilities":data['facilities']})

# POSTエンドポイント
@app.post("/api/sendCrowdLevel")
async def update(info:FacilityInfo, authorization:str=Header(None)):

    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)

    new_data = {
        "max_capacity": info.max_capacity,
        "current_count": info.current_count
    }

    # id一致で情報更新
    if update_json(data["facilities"], info.id, new_data):
        save_to_json(JSON_FILE_PATH, data)
        print("update_json is correct!")
        return {"Result" : "update_json is correct!"}
    else:
        print("update_json error")
        return {"Result" : "update_json is faild!"}

