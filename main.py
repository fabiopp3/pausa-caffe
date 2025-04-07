...

@app.get("/{group_name}", response_class=HTMLResponse)
async def group_page(request: Request, group_name: str, nickname: str = Cookie(default=None)):
    session = SessionLocal()
    group = session.query(Group).filter_by(name=group_name).first()
    if not group:
        session.close()
        return HTMLResponse("Gruppo non trovato", status_code=404)
    bars = session.query(Bar).filter_by(group_id=group.id).all()
    today = date.today()
    availabilities = (
        session.query(Availability)
        .options(joinedload(Availability.user), joinedload(Availability.bar))
        .filter(Availability.date == today, Availability.bar.has(group_id=group.id))
        .all()
    )
    session.close()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "group": group.name,
        "bars": bars,
        "availabilities": availabilities,
        "nickname": nickname,
        "date": today.isoformat()
    })
