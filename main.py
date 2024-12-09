from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import random
import json

from fastapi import FastAPI, Request, HTTPException
from starlette.status import HTTP_403_FORBIDDEN

app = FastAPI()

# POSTで受け取るデータモデル
class Information(BaseModel):
    id: int = Field(...,)
    name: str = Field(..., min_length=1, max_length=50)
    max_capacity: int = Field(..., ge=0)
    current_count: int = Field(..., ge=0)

JSON_FILE_PATH = 'data.json'

# テンプレートのパスを指定
templates = Jinja2Templates(directory="templates")

# 静的ファイルの設定
app.mount("/static", StaticFiles(directory="static"), name="static")

# 後のためのCORS回避
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 混雑状況確認ページを表示
@app.get("/")
async def get_html(request: Request):
    #JSONファイルの読み込み
    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as file:
        data = json.load(file)

    return templates.TemplateResponse("index.html", {"request": request, "facilities":data['facilities']})

# POSTエンドポイント
@app.post("/info/")
async def update(info:Information):

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
        return {"Result" : "Correct!"}
    else:
        print("update_json error")
        return {"Result" : "Failed"}

def update_json(facilities, facility_id, new_data):
    for facility in facilities:
        if facility["id"] == facility_id:
            facility.update(new_data)
            return True
    return False

def save_to_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)