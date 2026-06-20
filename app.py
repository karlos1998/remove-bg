import json
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from pydantic import BaseModel
from rembg import remove, new_session

app = FastAPI()

# Mount static files and setup templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize session with the birefnet-general model, which offers the highest detail precision
session = new_session("birefnet-general")


class BatchRemoveRequest(BaseModel):
    input_dir: str
    output_dir: str
    center_object: bool = True
    copy_labels: bool = True
    overwrite: bool = False


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def center_foreground(image_data: bytes, alpha_threshold: int = 8) -> bytes:
    image = Image.open(BytesIO(image_data)).convert("RGBA")
    alpha = image.getchannel("A")
    alpha_bbox = alpha.point(lambda value: 255 if value > alpha_threshold else 0).getbbox()

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


def remove_background(image_data: bytes, center_object: bool = False) -> bytes:
    # We forgo alpha_matting in favor of the more powerful birefnet model.
    # This model excels at cutting out the background inside loops and straps.
    out = remove(
        image_data,
        session=session,
        alpha_matting=False
    )
    if center_object:
        out = center_foreground(out)
    return out


def load_processable_image_bytes(path: Path) -> bytes:
    if path.suffix.lower() not in {".heic", ".heif"}:
        return path.read_bytes()

    with tempfile.TemporaryDirectory() as tmp_dir:
        converted_path = Path(tmp_dir) / f"{path.stem}.png"
        result = subprocess.run(
            [
                "sips",
                "-s",
                "format",
                "png",
                str(path),
                "--out",
                str(converted_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0 or not converted_path.exists():
            raise RuntimeError(result.stderr.strip() or f"Failed to convert {path.name}")
        return converted_path.read_bytes()


def process_manifest_directory(
    input_dir: Path,
    output_dir: Path,
    center_object: bool = True,
    copy_labels: bool = True,
    overwrite: bool = False,
    progress_callback=None,
) -> dict:
    manifest_path = input_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest.json in {input_dir}")
    if output_dir.exists() and not overwrite:
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    if output_dir.exists():
        shutil.rmtree(output_dir)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)

    processed_manifest = {
        **manifest,
        "source_manifest": str(manifest_path),
        "center_object": center_object,
        "background_removed": True,
        "groups": [],
    }
    processed_count = 0
    copied_label_count = 0
    total_photo_count = sum(
        1
        for group in manifest["groups"]
        for file_entry in group["files"]
        if file_entry.get("role", "photo") != "label"
    )

    for group in manifest["groups"]:
        group_dir = output_dir / group["folder"]
        group_dir.mkdir(parents=True, exist_ok=True)
        processed_group = {
            **group,
            "attachments": [],
            "files": [],
        }

        for file_entry in group["files"]:
            source_rel = Path(file_entry["file"])
            source_path = input_dir / source_rel
            role = file_entry.get("role", "photo")

            if role == "label":
                if not copy_labels:
                    continue
                output_rel = source_rel
                output_path = output_dir / output_rel
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, output_path)
                copied_label_count += 1
            else:
                output_name = f"{source_rel.stem}_no_bg_centered.png"
                output_rel = source_rel.parent / output_name
                output_path = output_dir / output_rel
                output_path.parent.mkdir(parents=True, exist_ok=True)
                image_data = load_processable_image_bytes(source_path)
                if progress_callback:
                    progress_callback(processed_count + 1, total_photo_count, source_path)
                output_path.write_bytes(remove_background(image_data, center_object=center_object))
                processed_count += 1

            processed_group["attachments"].append(str(output_rel))
            processed_group["files"].append({
                **file_entry,
                "source_file": file_entry["file"],
                "file": str(output_rel),
                "background_removed": role != "label",
            })

        processed_group["photo_count_excluding_label"] = sum(
            1 for file_entry in processed_group["files"]
            if file_entry.get("role") == "photo"
        )
        processed_manifest["groups"].append(processed_group)

    processed_manifest["processed_photo_count"] = processed_count
    processed_manifest["copied_label_count"] = copied_label_count
    processed_manifest["output_dir"] = str(output_dir)
    (output_dir / "manifest.json").write_text(
        json.dumps(processed_manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return processed_manifest


@app.post("/api/remove")
async def remove_bg(file: UploadFile = File(...), center_object: bool = Form(False)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Please upload an image file")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        out = remove_background(data, center_object=center_object)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove background: {e}")

    return Response(
        content=out,
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="no-bg.png"'},
    )


@app.post("/api/batch/remove-folder")
async def remove_bg_batch(request: BatchRemoveRequest):
    try:
        return process_manifest_directory(
            input_dir=Path(request.input_dir).expanduser(),
            output_dir=Path(request.output_dir).expanduser(),
            center_object=request.center_object,
            copy_labels=request.copy_labels,
            overwrite=request.overwrite,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process folder: {e}")
