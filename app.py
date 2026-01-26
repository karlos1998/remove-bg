from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, Response
from rembg import remove

app = FastAPI()

INDEX_HTML = """
<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>BG Remover (local)</title>
  <style>
    body{font-family:system-ui,Segoe UI,Roboto,Arial;max-width:900px;margin:40px auto;padding:0 16px}
    .card{border:1px solid #e5e7eb;border-radius:16px;padding:18px}
    .row{display:flex;gap:16px;flex-wrap:wrap}
    .col{flex:1;min-width:260px}
    input,button{font:inherit}
    button{padding:10px 14px;border-radius:12px;border:1px solid #111;background:#111;color:#fff;cursor:pointer}
    button[disabled]{opacity:.5;cursor:not-allowed}
    .muted{color:#6b7280;font-size:14px}
    img{max-width:100%;border-radius:12px;border:1px solid #e5e7eb;background:#f9fafb}
    .preview{display:grid;gap:10px}
    a{color:#111}
    .bar{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
    .spinner{width:18px;height:18px;border-radius:50%;border:2px solid #ddd;border-top-color:#111;animation:spin 1s linear infinite;display:none}
    @keyframes spin{to{transform:rotate(360deg)}}
  </style>
</head>
<body>
  <h1>Local remove.bg</h1>
  <p class="muted">Wysyłasz zdjęcie → po chwili pobierasz PNG bez tła (offline, lokalnie).</p>

  <div class="card">
    <div class="bar">
      <input id="file" type="file" accept="image/*" />
      <button id="btn" disabled>Usuń tło</button>
      <div id="spin" class="spinner"></div>
      <span id="status" class="muted"></span>
    </div>

    <div style="height:14px"></div>

    <div class="row">
      <div class="col preview">
        <strong>Podgląd wejścia</strong>
        <img id="inImg" alt="Wejście" />
      </div>
      <div class="col preview">
        <strong>Wynik (PNG alpha)</strong>
        <img id="outImg" alt="Wynik" />
        <a id="download" href="#" download="no-bg.png" style="display:none">Pobierz PNG</a>
      </div>
    </div>
  </div>

<script>
  const fileEl = document.getElementById('file')
  const btn = document.getElementById('btn')
  const inImg = document.getElementById('inImg')
  const outImg = document.getElementById('outImg')
  const dl = document.getElementById('download')
  const status = document.getElementById('status')
  const spin = document.getElementById('spin')

  let currentFile = null

  const setBusy = (busy) => {
    btn.disabled = busy || !currentFile
    spin.style.display = busy ? 'inline-block' : 'none'
  }

  fileEl.addEventListener('change', () => {
    const f = fileEl.files?.[0]
    currentFile = f ?? null
    dl.style.display = 'none'
    outImg.removeAttribute('src')
    status.textContent = ''
    if (!currentFile) {
      inImg.removeAttribute('src')
      btn.disabled = true
      return
    }
    inImg.src = URL.createObjectURL(currentFile)
    btn.disabled = false
  })

  btn.addEventListener('click', async () => {
    if (!currentFile) return
    setBusy(true)
    status.textContent = 'Przetwarzanie...'

    try {
      const fd = new FormData()
      fd.append('file', currentFile)

      const res = await fetch('/api/remove', { method: 'POST', body: fd })
      if (!res.ok) {
        const msg = await res.text()
        throw new Error(msg || 'Błąd przetwarzania')
      }

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      outImg.src = url
      dl.href = url
      dl.style.display = 'inline-block'
      status.textContent = 'Gotowe'
    } catch (e) {
      status.textContent = 'Błąd: ' + (e?.message ?? e)
    } finally {
      setBusy(false)
    }
  })
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML

@app.post("/api/remove")
async def remove_bg(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Wyślij plik graficzny")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Pusty plik")

    try:
        out = remove(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Nie udało się usunąć tła: {e}")

    return Response(
        content=out,
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="no-bg.png"'},
    )
