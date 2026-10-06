import os
import re
import uuid
import shutil
import subprocess
import threading
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SMOOTH.PK")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def find_program(name):
    found = shutil.which(name)
    if found:
        return found
    for p in (f"/usr/bin/{name}", f"/usr/local/bin/{name}", f"/bin/{name}", f"/app/{name}"):
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


FFMPEG_EXE = find_program("ffmpeg")
FFPROBE_EXE = find_program("ffprobe")
progress_store = {}


def set_progress(job_id, percent, status="processing", **extra):
    progress_store[job_id] = {"progress": max(0, min(100, int(percent))), "status": status, **extra}


def safe_filename(filename):
    name = Path(filename or "video.mp4").name
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name or "video.mp4"


def get_duration(path):
    if not FFPROBE_EXE:
        return None
    try:
        r = subprocess.run(
            [FFPROBE_EXE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30
        )
        value = r.stdout.strip()
        if value:
            d = float(value)
            return d if d > 0 else None
    except Exception as e:
        print("FFPROBE ERROR:", repr(e))
    return None


HTML_CONTENT = """
<!doctype html>
<html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SMOOTH.PK - TikTok Video Optimizer</title>
<style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;font-family:Arial,sans-serif;background:#0b0b0b;color:#fff;display:flex;justify-content:center;align-items:center;padding:20px}.box{width:100%;max-width:650px;background:#191919;border:1px solid #333;border-radius:22px;padding:30px}.logo{text-align:center;font-size:38px;font-weight:900}.logo span{color:#ff0050}.sub{text-align:center;color:#aaa;margin:8px 0 28px}.upload{display:block;border:2px dashed #444;border-radius:16px;padding:35px;text-align:center;cursor:pointer}.upload:hover{border-color:#ff0050}#file{display:none}.name{color:#aaa;margin-top:12px;word-break:break-word}button{width:100%;margin-top:18px;padding:15px;border:0;border-radius:12px;background:#ff0050;color:#fff;font-weight:bold;font-size:16px}button:disabled{opacity:.5}.progress{display:none;margin-top:25px}.row{display:flex;justify-content:space-between;color:#ccc;margin-bottom:8px}.bar{height:14px;background:#303030;border-radius:20px;overflow:hidden}.fill{height:100%;width:0;background:#ff0050;transition:width .25s}.status{text-align:center;color:#aaa;margin-top:12px;font-size:14px}.result{display:none;text-align:center;margin-top:25px;padding:20px;background:#111;border-radius:14px}.download{display:block;margin-top:14px;padding:13px;background:#20c997;color:white;text-decoration:none;border-radius:10px;font-weight:bold}.error{color:#ff6075}
</style></head><body><div class="box">
<div class="logo">SMOOTH<span>.PK</span></div><div class="sub">TikTok Video Optimizer</div>
<label class="upload" for="file"><div style="font-size:46px">🎬</div><div>Select your video</div><div class="name" id="name">MP4, MOV, AVI and other video files</div></label>
<input id="file" type="file" accept="video/*"><button id="btn" disabled>Optimize Video</button>
<div class="progress" id="progress"><div class="row"><span id="pct">0%</span><span id="st">Starting...</span></div><div class="bar"><div class="fill" id="fill"></div></div><div class="status" id="status">Preparing video...</div></div>
<div class="result" id="result"><b>✅ Video Ready</b><a id="download" class="download">Download Optimized Video</a></div>
</div>
<script>
let selected=null,job=null,timer=null;
const file=document.getElementById('file'),nameEl=document.getElementById('name'),btn=document.getElementById('btn'),prog=document.getElementById('progress'),fill=document.getElementById('fill'),pct=document.getElementById('pct'),st=document.getElementById('st'),status=document.getElementById('status'),result=document.getElementById('result'),download=document.getElementById('download');
file.onchange=()=>{selected=file.files[0]||null;nameEl.textContent=selected?selected.name:'MP4, MOV, AVI and other video files';btn.disabled=!selected};
btn.onclick=async()=>{if(!selected)return;btn.disabled=true;prog.style.display='block';result.style.display='none';ui(0,'Uploading...');let fd=new FormData();fd.append('file',selected);try{let r=await fetch('/api/optimize',{method:'POST',body:fd});let d=await r.json();if(!r.ok)throw Error(d.detail||'Processing failed.');job=d.job_id;if(timer)clearInterval(timer);timer=setInterval(check,500);check()}catch(e){showError(e.message);btn.disabled=false}};
function ui(p,t){p=Math.max(0,Math.min(100,Math.round(p)));fill.style.width=p+'%';pct.textContent=p+'%';st.textContent=t;status.textContent=t}
function showError(m){prog.style.display='block';fill.style.width='0%';pct.textContent='0%';st.textContent='Error';status.innerHTML='<span class="error">❌ '+String(m).replace(/</g,'&lt;')+'</span>'}
async function check(){if(!job)return;try{let r=await fetch('/api/progress/'+job);let d=await r.json();ui(d.progress||0,d.status_text||'Processing...');if(d.status==='completed'){clearInterval(timer);timer=null;ui(100,'Complete!');download.href=d.download_url;result.style.display='block';btn.disabled=false}if(d.status==='error'){clearInterval(timer);timer=null;showError(d.error||'FFmpeg video processing failed.');btn.disabled=false}}catch(e){console.log(e)}}
</script></body></html>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_CONTENT


@app.get("/health")
def health():
    return {"status": "ok", "ffmpeg": FFMPEG_EXE or "NOT FOUND", "ffprobe": FFPROBE_EXE or "NOT FOUND"}


@app.post("/api/optimize")
def optimize_video(file: UploadFile = File(...)):
    if not FFMPEG_EXE:
        raise HTTPException(500, "FFmpeg is not installed on the server.")
    if not file.filename:
        raise HTTPException(400, "No video file selected.")

    job_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{job_id}_{safe_filename(file.filename)}"
    output_path = OUTPUT_DIR / f"{job_id}_optimized.mp4"

    try:
        with open(input_path, "wb") as out:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except Exception as e:
        print("UPLOAD ERROR:", repr(e))
        raise HTTPException(500, "Could not save uploaded video.")

    set_progress(job_id, 1, "processing", status_text="Reading video...")
    threading.Thread(target=run_ffmpeg, args=(job_id, str(input_path), str(output_path)), daemon=True).start()
    return {"job_id": job_id}


def run_ffmpeg(job_id, input_path, output_path):
    try:
        duration = get_duration(input_path)
        set_progress(job_id, 1, "processing", status_text="Starting FFmpeg...")

        command = [
            FFMPEG_EXE, "-y", "-hide_banner", "-i", input_path,
            "-map", "0:v:0", "-map", "0:a:0?",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            "-progress", "pipe:1", "-nostats", output_path,
        ]

        print("FFMPEG COMMAND:", " ".join(command))
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        errors = []

        def read_errors():
            try:
                for line in process.stderr:
                    line = line.strip()
                    if line:
                        errors.append(line)
                        print("FFMPEG:", line)
            except Exception as e:
                print("STDERR ERROR:", repr(e))

        threading.Thread(target=read_errors, daemon=True).start()
        last = 1

        while True:
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                continue
            line = line.strip()
            if line.startswith("out_time_ms=") and duration:
                try:
                    seconds = int(line.split("=", 1)[1]) / 1000000
                    percent = max(1, min(99, int((seconds / duration) * 100)))
                    if percent > last:
                        last = percent
                        set_progress(job_id, percent, "processing", status_text="Optimizing video...")
                except Exception as e:
                    print("PROGRESS ERROR:", repr(e))

        code = process.wait()
        print("FFMPEG EXIT:", code)

        if code != 0:
            error_text = "\n".join(errors[-20:])
            set_progress(job_id, 0, "error", status_text="FFmpeg failed", error=error_text[-1500:] or "FFmpeg processing failed.")
            return

        if not os.path.exists(output_path) or os.path.getsize(output_path) <= 0:
            set_progress(job_id, 0, "error", status_text="Output missing", error="FFmpeg finished but no output video was created.")
            return

        set_progress(job_id, 100, "completed", status_text="Complete!", download_url="/outputs/" + os.path.basename(output_path))
        try:
            os.remove(input_path)
        except Exception:
            pass

    except Exception as e:
        print("WORKER ERROR:", repr(e))
        set_progress(job_id, 0, "error", status_text="Processing error", error=str(e))


@app.get("/api/progress/{job_id}")
def get_progress(job_id: str):
    data = progress_store.get(job_id)
    if not data:
        raise HTTPException(404, "Job not found.")
    return data


@app.get("/outputs/{filename}")
def download_output(filename: str):
    file_path = OUTPUT_DIR / Path(filename).name
    if not file_path.exists():
        raise HTTPException(404, "Output file not found.")
    return FileResponse(str(file_path), media_type="video/mp4", filename=file_path.name)


@app.on_event("startup")
def startup():
    print("SMOOTH.PK STARTED")
    print("FFmpeg:", FFMPEG_EXE or "NOT FOUND")
    print("FFprobe:", FFPROBE_EXE or "NOT FOUND")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
