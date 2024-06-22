from fastapi import FastAPI, HTTPException, status, Request, Body
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from module import *
import ssl
import datetime
import time
import math
from flask import Flask, render_template, request, redirect, url_for, flash
from jinja2 import Environment, FileSystemLoader, select_autoescape
from email.message import EmailMessage
from aiosmtplib import SMTP, SMTPException
import os
app = FastAPI()
uri = "mongodb+srv://qogywofhqht:a@cluster0.kupvcum.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

current_directory = os.path.dirname(os.path.abspath(__file__))
# Jinja2 환경 설정
templates = Environment(
    loader=FileSystemLoader(current_directory),
    autoescape=select_autoescape(['html', 'xml'])
)


client = MongoClient(uri, server_api=ServerApi('1'))
db = client['UserInformation'] 
collection = db['users']  
GPS_collection = db['gps'] 

class User(BaseModel):
    id: str = None
    password: str = None
    email: str = None

class GPSData(BaseModel):   
    latitude: float
    longitude: float

home = (38.251391382, 9.071245584)


@app.get("/", response_class=HTMLResponse)
async def join_page(request: Request):
    return HTMLResponse(content=open("login.html", encoding='UTF8').read(), status_code=200)

# @app.get("/join", response_class=HTMLResponse)    
# async def join_page(request: Request):
#     return HTMLResponse(content=open("Join.html", encoding='UTF8').read(), status_code=200)

# @app.get("/find_id", response_class=HTMLResponse)
# async def join_page(request: Request):
#     return HTMLResponse(content=open("FindID.html", encoding='UTF8').read(), status_code=200)

@app.post("/login")
async def login(user: User):
    user_doc = collection.find_one({"id": user.id})
    if user_doc:
        if user_doc["password"] == user.password:
            return {"message": "인증 성공", "id": user.id}
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="비밀번호가 틀렸습니다.")
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="아이디가 존재하지 않습니다.")

# @app.post("/findid")
# async def find_id(user: User):
#     user_doc = collection.find_one({"email": user.email})
#     if user_doc:
#         if user_doc["password"] == user.password:  # 비밀번호 비교
#             return {"message": "인증 성공", "id": user_doc["id"], "password": user.password}
#         else:
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="비밀번호가 틀렸습니다.")
#     else:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일없습니다")

class Timetracker:
    """
    Timetracker 클래스는 현재 시간을 추적하고, 특정 조건에 따라 상태를 변경하는 기능을 제공합니다.
    """
    def __init__(self):
        """
        Timetracker 객체를 초기화합니다.
        """
        self.current_time = datetime.datetime.now()
        self.condition = False
        self.message_sent = False  

    def update_time(self):
        """
        조건이 참일 경우 현재 시간을 업데이트합니다.
        """
        if self.condition:
            self.current_time = datetime.datetime.now()

    def change_condition(self, new_condition):
        """
        객체의 조건을 새로운 상태로 변경합니다.
        
        :param new_condition: 새로운 조건의 상태 (True 또는 False)
        """
        self.condition = new_condition

    def check_time_difference(self):
        """
        현재 시간과 이전에 기록된 시간의 차이가 1초 이상인지 확인합니다.
        
        :return: 시간 차이가 1초 이상이면 True, 그렇지 않으면 False
        """
        return (datetime.datetime.now() - self.current_time).total_seconds() >  1
    
tm = Timetracker()

@app.post("/get_gps_data")
async def check_location(gps_data: GPSData):
    #request 데이터 조회 후 디비에 삽입
    a = {"latitude":gps_data.latitude, "longitude":gps_data.longitude}
    print(a)
    gps_document = {"latitude": gps_data.latitude, "longitude": gps_data.longitude, "timestamp": time.strftime("%y-%m-%d/%H:%M:%S")}
    GPS_collection.insert_one(gps_document)
    # 디비에서 삽입한거 하나 꺼내옴
    
    distance = Location_home(home, gps_document)
    if distance > 1000:
        if not tm.condition:
            tm.change_condition(True)
            tm.update_time()
            print(f"시간 고정({datetime.datetime.now()})")

        elif tm.check_time_difference()and not tm.message_sent:  
            await mails(gps_document)
            tm.message_sent = True
            print("gmail 보냄")
        return {"message": "사용자 위치 확인됨"}
    
    elif not tm.condition:
        tm.change_condition(False)
        tm.update_time(False)
        tm.message_sent = False     
        print("정상")
        return {"message": "사용자 위치 정상"}
    else:
        print("비정상")
        return {"message": "사용자 위치 확인 중"}   

def Location_home(home, pos):
    #헤버사인 공식
    r = 6371000
    lat1 = pos['latitude']
    lon1 = pos['longitude']
    lat2 = home[0]
    lon2 = home[1]
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = int(r * c)
    print(distance)
    return(distance)
    
async def send_email(recipient: str, subject: str, body: str):
    message = EmailMessage()
    message["From"] = "injeungmeil@gmail.com"
    message["To"] = recipient
    message["Subject"] = subject
    
    GOOGLE_MAPS_API_KEY = 'AIzaSyAVnteL9JlOKZwa0cUk52PgpuqVYi7rZZQ'
    template = templates.get_template('email.html')
    html_content = template.render(latitude=37, longitude=127, api_key=GOOGLE_MAPS_API_KEY)
    message.set_content(html_content, subtype='html')

    context = ssl.create_default_context()
    print("before SMTP")
    try:
        smtp = SMTP(hostname="smtp.gmail.com", port=587)
        await smtp.connect()
        print("Connected to SMTP server")
        if not smtp.is_ehlo_or_helo_needed:
            await smtp.starttls(tls_context=context)
            print("Started TLS")
        print("Started TLS")
        await smtp.login("injeungmeil@gmail.com", "rdmu uziq wtpu vgjb")
        print("Logged in to SMTP server")
        await smtp.send_message(message)
        print("Email sent")
        await smtp.quit()
    except SMTPException as e:
        print(f"SMTPException: {e}")
    except Exception as e:
        print(f"Exception: {e}")


async def mails(user:User):
    subject = "제목"
    body = "NONE"
    # user_email= collection.find_one({"email": user.email})
    user_email = "qogywofhqht@gmail.com"
    await send_email(user_email, subject, body)
    print("성공")
    return "success"
