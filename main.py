from fastapi import FastAPI, Request, Form, Response, Cookie
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
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String, unique=True)
    availabilities = relationship("Availability", back_populates="user")

class Bar(Base):
    __tablename__ = "bars"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
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

# Inizializza bar se non esistono
def init_bars():
    session = SessionLocal()
    existing = session.query(Bar).count()
    if existing == 0:
        bars = ["Fuori Orario", "Caffè degli artisti", "Amemì"]
        for name in bars:
            session.add(Bar(name=name))
        session.commit()
    session.close()

init_bars()

# Rotte
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, nickname: str = Cookie(default="")):
    session = SessionLocal()
    bars = session.query(Bar).all()
    selected_date = request.query_params.get("date")
    if selected_date:
        filter_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
    else:
        filter_date = date.today()
    availabilities = session.query(Availability)\
        .options(joinedload(Availability.user), joinedload(Availability.bar))\
        .filter_by(date=filter_date).all()
    session.close()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "bars": bars,
        "availabilities": availabilities,
        "nickname": nickname,
        "date": filter_date.strftime("%Y-%m-%d")
    })

@app.post("/submit")
async def submit(response: Response, nickname: str = Form(...), bar_id: int = Form(...), start: str = Form(...), end: str = Form(...)):
    session = SessionLocal()
    user = session.query(User).filter_by(nickname=nickname).first()
    if not user:
        user = User(nickname=nickname)
        session.add(user)
        session.commit()
    availability = Availability(
        user_id=user.id,
        bar_id=bar_id,
        start_time=datetime.strptime(start, "%H:%M").time(),
        end_time=datetime.strptime(end, "%H:%M").time(),
        date=date.today()
    )
    session.add(availability)
    session.commit()
    session.close()
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="nickname", value=nickname)
    return response

@app.post("/delete")
async def delete_availability(avail_id: int = Form(...)):
    session = SessionLocal()
    availability = session.query(Availability).filter_by(id=avail_id).first()
    if availability:
        session.delete(availability)
        session.commit()
    session.close()
    return RedirectResponse(url="/", status_code=303)

# Scrivi index.html minimale
template_html = """
<!DOCTYPE html>
<html lang=\"it\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Pausa Caffè</title>
    <link rel=\"stylesheet\" href=\"/static/styles.css\">
</head>
<body>
    <div class=\"container\">
        <h1>Pausa Caffè</h1>
        <form method=\"get\" action=\"/\">
            <label for=\"date\">Scegli una data:</label>
            <input type=\"date\" name=\"date\" value=\"{{ date }}\">
            <button type=\"submit\">Filtra</button>
        </form>
        <form method=\"post\" action=\"/submit\">
            <input type=\"text\" name=\"nickname\" placeholder=\"Il tuo nome\" required value=\"{{ nickname }}\">
            <select name=\"bar_id\">
                {% for bar in bars %}
                    <option value=\"{{ bar.id }}\">{{ bar.name }}</option>
                {% endfor %}
            </select>
            <input type=\"time\" name=\"start\" value=\"13:00\">
            <input type=\"time\" name=\"end\" value=\"14:00\">
            <button type=\"submit\">Salva disponibilità</button>
        </form>
        <h2>Disponibilità per {{ date }}</h2>
        <ul>
            {% for a in availabilities %}
                <li>
                    <strong>{{ a.user.nickname }}</strong> sarà a <strong>{{ a.bar.name }}</strong> dalle {{ a.start_time }} alle {{ a.end_time }}
                    {% if a.user.nickname == nickname %}
                        <form method=\"post\" action=\"/delete\" style=\"display:inline;\">
                            <input type=\"hidden\" name=\"avail_id\" value=\"{{ a.id }}\">
                            <button type=\"submit\">🗑</button>
                        </form>
                    {% endif %}
                </li>
            {% endfor %}
        </ul>
    </div>
</body>
</html>
"""
with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(template_html)

# Scrivi styles.css minimale
styles_css = """
body {
    font-family: sans-serif;
    background-color: #f6f6f6;
    margin: 0;
    padding: 0;
}

.container {
    max-width: 600px;
    margin: 40px auto;
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

form {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 20px;
}

input, select, button {
    padding: 8px;
    font-size: 1rem;
    border: 1px solid #ccc;
    border-radius: 4px;
}

button {
    background-color: #2e7d32;
    color: white;
    cursor: pointer;
}

button:hover {
    background-color: #1b5e20;
}
"""
with open("static/styles.css", "w", encoding="utf-8") as f:
    f.write(styles_css)
