from fastapi import FastAPI, Request, Form, Response, Cookie, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Time, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, joinedload
from datetime import datetime, date, time
import os

app = FastAPI()

# Create folders if not exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
    users = relationship("User", back_populates="group")
    bars = relationship("Bar", back_populates="group")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String)
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

# Homepage: elenco gruppi
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    session = SessionLocal()
    gruppi = session.query(Group).order_by(Group.name).all()
    session.close()
    return templates.TemplateResponse("homepage.html", {"request": request, "gruppi": gruppi})

# Rotta per creare gruppo
@app.get("/crea-gruppo", response_class=HTMLResponse)
async def crea_gruppo_form(request: Request):
    session = SessionLocal()
    gruppi = session.query(Group).all()
    session.close()
    return templates.TemplateResponse("create_group.html", {"request": request, "gruppi": gruppi})

@app.post("/crea-gruppo", response_class=HTMLResponse)
async def crea_gruppo(request: Request, nome_gruppo: str = Form(...), bar1: str = Form(...), bar2: str = Form(...), bar3: str = Form(...)):
    session = SessionLocal()
    existing = session.query(Group).filter_by(name=nome_gruppo).first()
    if existing:
        session.close()
        return HTMLResponse("Questo gruppo esiste già.", status_code=400)
    group = Group(name=nome_gruppo)
    session.add(group)
    session.commit()
    session.add_all([
        Bar(name=bar1, group_id=group.id),
        Bar(name=bar2, group_id=group.id),
        Bar(name=bar3, group_id=group.id),
    ])
    session.commit()
    session.close()
    return HTMLResponse(f"Gruppo '{nome_gruppo}' creato con successo! Vai a <a href='/{nome_gruppo}'>/{nome_gruppo}</a>")

# Inizializza gruppo e bar se non esistono
def init_group_and_bars():
    session = SessionLocal()
    group = session.query(Group).filter_by(name="default").first()
    if not group:
        group = Group(name="default")
        session.add(group)
        session.commit()
        bars = ["Fuori Orario", "Caffè degli artisti", "Amemì"]
        for name in bars:
            session.add(Bar(name=name, group_id=group.id))
        session.commit()
    session.close()

init_group_and_bars()

# Rotte principali
@app.get("/{group_name}", response_class=HTMLResponse)
async def index(request: Request, group_name: str = Path(...), nickname: str = Cookie(default="")):
    session = SessionLocal()
    group = session.query(Group).filter_by(name=group_name).first()
    if not group:
        session.close()
        return HTMLResponse(f"Gruppo '{group_name}' non trovato", status_code=404)
    bars = session.query(Bar).filter_by(group_id=group.id).all()
    availabilities = session.query(Availability)\
        .join(User).filter(User.group_id == group.id)\
        .options(joinedload(Availability.user), joinedload(Availability.bar))\
        .order_by(Availability.date, Availability.start_time).all()
    session.close()
    today = date.today()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "bars": bars,
        "availabilities": availabilities,
        "nickname": nickname,
        "date": today.strftime("%Y-%m-%d"),
        "group": group_name
    })

@app.post("/{group_name}/submit")
async def submit(group_name: str, response: Response, nickname: str = Form(...), bar_id: int = Form(...), start: str = Form(...), end: str = Form(...), date_input: str = Form(...)):
    session = SessionLocal()
    group = session.query(Group).filter_by(name=group_name).first()
    if not group:
        session.close()
        return HTMLResponse(f"Gruppo '{group_name}' non trovato", status_code=404)
    user = session.query(User).filter_by(nickname=nickname, group_id=group.id).first()
    if not user:
        user = User(nickname=nickname, group_id=group.id)
        session.add(user)
        session.commit()
    availability = Availability(
        user_id=user.id,
        bar_id=bar_id,
        start_time=datetime.strptime(start, "%H:%M").time(),
        end_time=datetime.strptime(end, "%H:%M").time(),
        date=datetime.strptime(date_input, "%Y-%m-%d").date()
    )
    session.add(availability)
    session.commit()
    session.close()
    response = RedirectResponse(url=f"/{group_name}", status_code=303)
    response.set_cookie(key="nickname", value=nickname)
    return response

@app.post("/{group_name}/delete")
async def delete_availability(group_name: str, request: Request, avail_id: int = Form(...)):
    session = SessionLocal()
    availability = session.query(Availability).filter_by(id=avail_id).first()
    if availability:
        session.delete(availability)
        session.commit()
    session.close()
    referrer = request.headers.get("referer") or f"/{group_name}"
    return RedirectResponse(url=referrer, status_code=303)
