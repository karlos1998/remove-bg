from io import BytesIO

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
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


def center_foreground(image_data: bytes) -> bytes:
    image = Image.open(BytesIO(image_data)).convert("RGBA")
    alpha_bbox = image.getchannel("A").getbbox()

    if not alpha_bbox:
        return image_data

    width, height = image.size
    left, top, right, bottom = alpha_bbox
    foreground = image.crop(alpha_bbox)
    foreground_width = right - left
    foreground_height = bottom - top
    target_left = (width - foreground_width) // 2
    target_top = (height - foreground_height) // 2

    centered = Image.new("RGBA", image.size, (255, 255, 255, 0))
    centered.alpha_composite(foreground, (target_left, target_top))

    buffer = BytesIO()
    centered.save(buffer, format="PNG")
    return buffer.getvalue()


@app.post("/api/remove")
async def remove_bg(file: UploadFile = File(...), center_object: bool = Form(False)):
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
        if center_object:
            out = center_foreground(out)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove background: {e}")

    return Response(
        content=out,
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="no-bg.png"'},
    )
