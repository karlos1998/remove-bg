from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from rembg import remove, new_session

app = FastAPI()

# Mount static files and setup templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Inicjalizacja sesji z modelem birefnet-general, który oferuje najwyższą precyzję detali
session = new_session("birefnet-general")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/remove")
async def remove_bg(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Wyślij plik graficzny")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Pusty plik")

    try:
        # Rezygnujemy z alpha_matting na rzecz potężniejszego modelu birefnet
        # Model ten świetnie radzi sobie z wycinaniem tła wewnątrz pętli i pasków
        out = remove(
            data,
            session=session,
            alpha_matting=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Nie udało się usunąć tła: {e}")

    return Response(
        content=out,
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="no-bg.png"'},
    )
