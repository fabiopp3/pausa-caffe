from fastapi import FastAPI, Request, Form, Response, Cookie, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Time, Date, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, joinedload
from passlib.context import CryptContext
from datetime import datetime, date, time
import os

app = FastAPI()

# Create folders if not exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)

# Database setup
DATABASE_URL = "sqlite:///./coffee.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Modelli DB
class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    premium = Column(Boolean, default=False)
    users = relationship("User", back_populates="group")
    bars = relationship("Bar", back_populates="group")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String)
    hashed_password = Column(String)
    group_id = Column(Integer, ForeignKey("groups.id"))
    group = relationship("Group", back_populates="users")
    availabilities = relationship("Availability", back_populates="user")

class Bar(Base):
    __tablename__ = "bars"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    group_id = Column(Integer, ForeignKey("groups.id"))
    group = relationship("Group", back_populates="bars")
    availabilities = relationship("Availability", back_populates="bar")

class Availability(Base):
    __tablename__ = "availabilities"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    bar_id = Column(Integer, ForeignKey("bars.id"))
    start_time = Column(Time)
    end_time = Column(Time)
    date = Column(Date)
    user = relationship("User", back_populates="availabilities")
    bar = relationship("Bar", back_populates="availabilities")

Base.metadata.create_all(bind=engine)

# Rotte di autenticazione
@app.get("/register", response_class=HTMLResponse)
async def show_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(response: Response, nickname: str = Form(...), password: str = Form(...), group_name: str = Form(...)):
    session = SessionLocal()
    group = session.query(Group).filter_by(name=group_name).first()
    if not group:
        session.close()
        return HTMLResponse("Gruppo non trovato.", status_code=404)
    existing = session.query(User).filter_by(nickname=nickname, group_id=group.id).first()
    if existing:
        session.close()
        return HTMLResponse("Nickname già registrato.", status_code=400)
    user = User(nickname=nickname, hashed_password=hash_password(password), group_id=group.id)
    session.add(user)
    session.commit()
    session.close()
    response = RedirectResponse(url=f"/{group.name}", status_code=303)
    response.set_cookie("nickname", nickname)
    return response

@app.get("/login", response_class=HTMLResponse)
async def show_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(response: Response, nickname: str = Form(...), password: str = Form(...), group_name: str = Form(...)):
    session = SessionLocal()
    group = session.query(Group).filter_by(name=group_name).first()
    if not group:
        session.close()
        return HTMLResponse("Gruppo non trovato.", status_code=404)
    user = session.query(User).filter_by(nickname=nickname, group_id=group.id).first()
    if not user or not verify_password(password, user.hashed_password):
        session.close()
        return HTMLResponse("Credenziali non valide.", status_code=401)
    session.close()
    response = RedirectResponse(url=f"/{group_name}", status_code=303)
    response.set_cookie("nickname", value=nickname)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("nickname")
    return response

# Homepage: elenco gruppi
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    session = SessionLocal()
    gruppi = session.query(Group).order_by(Group.name).all()
    session.close()
    return templates.TemplateResponse("homepage.html", {"request": request, "gruppi": gruppi})
