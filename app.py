from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from rembg import remove, new_session

app = FastAPI()

# Mount static files and setup templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize session with the birefnet-general model, which offers the highest detail precision
session = new_session("birefnet-general")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/remove")
async def remove_bg(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Please upload an image file")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        # We forgo alpha_matting in favor of the more powerful birefnet model
        # This model excels at cutting out the background inside loops and straps
        out = remove(
            data,
            session=session,
            alpha_matting=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove background: {e}")

    return Response(
        content=out,
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="no-bg.png"'},
    )
