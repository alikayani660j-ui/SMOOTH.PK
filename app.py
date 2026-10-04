import os
import re
import uuid
import subprocess
import glob
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="smooth.pk - TikTok Video Optimizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Real FFmpeg progress is stored here:
# job_id -> 0..100, or -1 on error
progress_store = {}

active_connections = set()

desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
ffmpeg_search = glob.glob(
    os.path.join(desktop_path, "**", "ffmpeg.exe"),
    recursive=True
)
FFMPEG_EXE = ffmpeg_search[0] if ffmpeg_search else "ffmpeg"


HTML_CONTENT = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>smooth.pk - TikTok Video Optimizer</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:'Segoe UI',Tahoma,sans-serif}
body{background:#0c0c0e;color:#fff;line-height:1.6}
header{display:flex;justify-content:space-between;align-items:center;padding:20px 50px;background:#121216;border-bottom:1px solid #222;position:sticky;top:0;z-index:1000}
.logo{font-size:24px;font-weight:bold;color:#00ffcc;letter-spacing:1px}
nav a{color:#aaa;text-decoration:none;margin-left:20px;font-size:14px;cursor:pointer}
nav a:hover,nav a.active{color:#00ffcc}
.live-badge{background:rgba(0,255,204,.1);border:1px solid #00ffcc;padding:5px 12px;border-radius:20px;font-size:13px;color:#00ffcc;display:flex;align-items:center;gap:6px}
.live-dot{width:8px;height:8px;background:#00ffcc;border-radius:50%;animation:pulse 1.5s infinite}
@keyframes pulse{0%{opacity:1}50%{opacity:.3}100%{opacity:1}}
.container{max-width:1000px;margin:40px auto;padding:20px;text-align:center}
.section{display:none}.section.active{display:block}
h1{font-size:42px;margin-bottom:15px;font-weight:800}
p.sub{color:#aaa;margin-bottom:30px;font-size:16px}
.card{background:#16161a;border:1px solid #26262f;border-radius:16px;padding:40px;margin-bottom:30px;box-shadow:0 10px 30px rgba(0,0,0,.5);text-align:left}
.center-card{text-align:center}
.upload-box{border:2px dashed #333;padding:40px;border-radius:12px;cursor:pointer;transition:.3s;background:#121215;display:block;text-align:center}
.upload-box:hover{border-color:#00ffcc}
input[type=file]{display:none}
input[type=text],textarea{width:100%;padding:14px;background:#121215;border:1px solid #333;color:#fff;border-radius:8px;font-size:16px;margin-bottom:15px;outline:none}
.btn{background:#00ffcc;color:#000;padding:12px 30px;font-weight:bold;border:none;border-radius:8px;cursor:pointer;font-size:16px;margin-top:15px;display:inline-block;text-decoration:none;text-align:center}
.btn:hover{background:#00cca3}
.btn:disabled{opacity:.6;cursor:not-allowed}
.free-badge{background:rgba(0,255,204,.15);border:1px solid #00ffcc;color:#00ffcc;padding:8px 16px;border-radius:8px;font-size:14px;margin-bottom:20px;display:inline-block;font-weight:bold}
.guide-box{background:#121215;border:1px solid #222;padding:20px;border-radius:10px;margin-top:20px;font-size:14px;color:#ccc}
.guide-box h3{color:#00ffcc;margin-bottom:10px}.guide-box ul{padding-left:20px}.guide-box li{margin-bottom:8px}
.preview-container{margin-top:25px;background:#121215;border:1px solid #222;padding:20px;border-radius:12px;text-align:center}
.img-comparision-slider{position:relative;width:100%;max-width:600px;height:350px;margin:20px auto;overflow:hidden;border-radius:8px;border:1px solid #333;user-select:none}
.slider-image-wrapper{position:absolute;top:0;left:0;width:50%;height:100%;overflow:hidden;z-index:2}
.slider-handle{position:absolute;top:0;bottom:0;left:50%;width:4px;background:#00ffcc;z-index:3;cursor:ew-resize}
.slider-handle-button{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:36px;height:36px;background:#00ffcc;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#000;font-weight:bold}
.badge-before,.badge-after{position:absolute;top:15px;background:rgba(0,0,0,.8);padding:4px 10px;border-radius:4px;font-size:12px;font-weight:bold;z-index:4}
.badge-before{left:15px;color:#ff4d4d}.badge-after{right:15px;color:#00ffcc}
.complaint-section,.activate-section{margin-top:30px;background:#16161a;border:1px solid #26262f;border-radius:16px;padding:30px;text-align:left}
.activate-section{border-color:#00ffcc;text-align:center}.activate-section h3,.complaint-section h3{color:#00ffcc;margin-bottom:10px;font-size:20px}
.pricing-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;margin-top:30px}
.price-card{background:#16161a;border:1px solid #26262f;border-radius:16px;padding:30px;text-align:left}
.price-card h3{font-size:18px;color:#888;margin-bottom:10px}.price-card .price{font-size:48px;font-weight:bold;margin-bottom:20px}
.price-card ul{list-style:none;margin-bottom:25px}.price-card ul li{margin-bottom:10px;color:#ccc;font-size:14px}
.price-card ul li::before{content:"✓ ";color:#00ffcc;font-weight:bold}
.result-box{margin-top:20px;background:#121215;padding:20px;border-radius:10px;text-align:left;border:1px solid #222;display:none}
#progress-overlay{display:none;text-align:center;padding:30px}
.loader-bar{width:100%;background:#222;border-radius:10px;height:12px;overflow:hidden;margin:20px 0}
.loader-fill{width:0%;height:100%;background:#00ffcc;transition:width .25s ease}
</style>
</head>

<body>
<header>
<div class="logo">smooth.pk</div>
<nav>
<a onclick="switchTab('optimizer')" id="nav-optimizer" class="active">Optimizer</a>
<a onclick="switchTab('analyzer')" id="nav-analyzer">Video Analyzer</a>
<a onclick="switchTab('pricing')" id="nav-pricing">PRO Plans</a>
</nav>
<div class="live-badge"><div class="live-dot"></div><span id="live-count">1</span> Live</div>
</header>

<div class="container">

<div id="optimizer" class="section active">
<h1>TIKTOK VIDEO OPTIMIZER</h1>
<p class="sub">Optimize your video while preserving high-end quality.</p>

<div class="center-card free-badge" id="status-badge">
🎁 Special Offer: Pehle 2 videos bilkul FREE! (<span id="free-left">2</span> free credits left)
</div>

<div class="card center-card">
<form id="upload-form" onsubmit="uploadVideo(event)">
<div id="form-content">
<label class="upload-box" id="drop-zone">
<input type="file" name="file" id="file-input" required onchange="showFileName('file-input','upload-text')">
<div id="upload-text">
<h3>📁 Drop your video here or click to browse</h3>
<p style="color:#666;font-size:13px;margin-top:8px">Supports MP4, MOV</p>
</div>
</label>
<br>
<button type="submit" class="btn" id="submit-btn">⚡ Optimize Video Now</button>
</div>

<div id="progress-overlay">
<h3 style="color:#00ffcc;margin-bottom:10px">⚡ Optimizing Video Quality...</h3>
<p id="progress-status-text" style="color:#aaa;font-size:14px">Preparing video...</p>
<div class="loader-bar"><div class="loader-fill" id="loader-fill"></div></div>
<h2 id="progress-percent" style="color:#fff;font-size:28px">0%</h2>
<p style="color:#777;font-size:12px;margin-top:8px">
Real FFmpeg rendering progress — 95% par fake lock nahi hai.
</p>
</div>
</form>

<div class="activate-section">
<h3>💎 Already Paid? Activate PRO Key</h3>
<p style="color:#aaa;font-size:13px;margin-bottom:15px">WhatsApp par mila PRO code enter karein:</p>
<div style="display:flex;gap:10px;max-width:400px;margin:auto">
<input type="text" id="promo-code" placeholder="Enter PRO Code" style="margin-bottom:0">
<button onclick="activatePro()" class="btn" style="margin-top:0">Activate</button>
</div>
</div>

<div class="guide-box">
<h3>📌 How to Use</h3>
<ul>
<li>Video select karein aur Optimize Video Now dabayein.</li>
<li>Progress bar FFmpeg ki REAL rendering progress show karegi.</li>
<li>100% sirf video successfully render hone ke baad aayega.</li>
</ul>
</div>

<div class="preview-container">
<h3 style="color:#00ffcc">🔥 Gaming Before & After Slider</h3>
<div class="img-comparision-slider" id="comparison-slider">
<div class="badge-after">SMOOTH ⚡</div>
<img src="https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800" style="position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover">
<div class="slider-image-wrapper" id="slider-wrapper">
<div class="badge-before">LAGGY 🚫</div>
<img src="https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800" style="position:absolute;top:0;left:0;width:600px;height:100%;object-fit:cover;max-width:none;filter:blur(6px) grayscale(50%)">
</div>
<div class="slider-handle" id="slider-handle"><div class="slider-handle-button">↔</div></div>
</div>
</div>
</div>
</div>

<div id="analyzer" class="section">
<h1>REAL VIDEO ANALYZER</h1>
<p class="sub">Check resolution, FPS, codec and bitrate.</p>
<div class="card center-card">
<form id="analyzer-form" onsubmit="analyzeVideo(event)">
<label class="upload-box">
<input type="file" id="analyzer-file-input" required onchange="showFileName('analyzer-file-input','analyzer-upload-text')">
<div id="analyzer-upload-text"><h3>📁 Upload video to analyze</h3></div>
</label>
<br>
<button type="submit" class="btn" id="analyzer-btn">📊 Analyze Real Specs</button>
</form>
<div id="analyzer-result" class="result-box">
<h3 style="color:#00ffcc;margin-bottom:10px">📊 Real Video Analysis</h3>
<div id="analysis-content" style="color:#ccc;line-height:1.8"></div>
</div>
</div>
</div>

<div id="pricing" class="section">
<h1>GO PRO</h1>
<p class="sub">Unlock unlimited optimizations.</p>
<div class="pricing-grid">
<div class="price-card"><h3>1 MONTH</h3><div class="price">$1</div>
<ul><li>30 Days Access</li><li>Unlimited optimizations</li><li>Larger uploads</li></ul>
<a href="https://wa.me/923199628815?text=Hi%20Ali,%20I%20want%20to%20buy%201%20Month%20PRO%20Access%20for%20$1" target="_blank" class="btn" style="width:100%">Get via WhatsApp ($1)</a></div>
<div class="price-card" style="border-color:#00ffcc"><h3>5 MONTHS</h3><div class="price">$5</div>
<ul><li>5 Months Access</li><li>Unlimited optimizations</li><li>Priority processing</li></ul>
<a href="https://wa.me/923199628815?text=Hi%20Ali,%20I%20want%20to%20buy%205%20Months%20PRO%20Access%20for%20$5" target="_blank" class="btn" style="width:100%">Get via WhatsApp ($5)</a></div>
<div class="price-card"><h3>UNLIMITED LIFETIME</h3><div class="price">$20</div>
<ul><li>Lifetime Access</li><li>Unlimited optimizations</li><li>VIP Support</li></ul>
<a href="https://instagram.com/alikayani09" target="_blank" class="btn" style="width:100%">Get via Instagram ($20)</a></div>
</div>
</div>

<div class="complaint-section">
<h3>🛠️ Koi Bhi Masla Ho?</h3>
<p style="color:#aaa;font-size:13px;margin-bottom:15px">Apna masla likhein aur WhatsApp par send karein:</p>
<textarea id="complaint-text" rows="3" placeholder="Apna masla yahan type karein..."></textarea>
<button onclick="sendComplaint()" class="btn">💬 Send Complaint via WhatsApp</button>
</div>

</div>

<script>
let isPro = localStorage.getItem('smooth_is_pro') === 'true';
let freeCredits = parseInt(localStorage.getItem('smooth_free_credits') || '2');

function updateUIStatus(){
if(isPro){
document.getElementById('status-badge').innerHTML='🔥 PRO ACCOUNT ACTIVE: Unlimited optimizations!';
}else{
document.getElementById('free-left').innerText=freeCredits;
}
}
updateUIStatus();

function activatePro(){
const code=document.getElementById('promo-code').value.trim();
const validCodes=["SMOOTH-1M-786","SMOOTH-5M-992","SMOOTH-LIFE-2026"];
if(validCodes.includes(code)){
localStorage.setItem('smooth_is_pro','true');
isPro=true; updateUIStatus();
alert('🎉 Mubarak ho! PRO successfully activated.');
}else alert('❌ Ghalat code!');
}

function switchTab(tabId){
document.querySelectorAll('.section').forEach(x=>x.classList.remove('active'));
document.querySelectorAll('nav a').forEach(x=>x.classList.remove('active'));
document.getElementById(tabId).classList.add('active');
document.getElementById('nav-'+tabId).classList.add('active');
}

function showFileName(inputId,textId){
const input=document.getElementById(inputId);
const text=document.getElementById(textId);
if(input.files.length>0)
text.innerHTML='<h3 style="color:#00ffcc">✅ Selected: '+input.files[0].name+'</h3>';
}

function sendComplaint(){
const msg=document.getElementById('complaint-text').value.trim();
if(!msg){alert('Pehle complaint likhein!');return;}
window.open('https://wa.me/923199628815?text='+encodeURIComponent('Complaint / Issue: '+msg),'_blank');
}

// Slider
const slider=document.getElementById('comparison-slider');
const wrapper=document.getElementById('slider-wrapper');
const handle=document.getElementById('slider-handle');
let dragging=false;

function updateSlider(clientX){
const rect=slider.getBoundingClientRect();
let x=Math.max(0,Math.min(rect.width,clientX-rect.left));
let p=(x/rect.width)*100;
wrapper.style.width=p+'%';
handle.style.left=p+'%';
}
slider.addEventListener('mousedown',e=>{dragging=true;updateSlider(e.clientX)});
window.addEventListener('mousemove',e=>{if(dragging)updateSlider(e.clientX)});
window.addEventListener('mouseup',()=>dragging=false);
slider.addEventListener('touchstart',e=>{dragging=true;updateSlider(e.touches[0].clientX)});
window.addEventListener('touchmove',e=>{if(dragging)updateSlider(e.touches[0].clientX)});
window.addEventListener('touchend',()=>dragging=false);

// Analyzer
async function analyzeVideo(event){
event.preventDefault();
const input=document.getElementById('analyzer-file-input');
if(!input.files.length)return;
const btn=document.getElementById('analyzer-btn');
btn.disabled=true;btn.innerText='⏳ Reading metadata...';
const fd=new FormData();fd.append('file',input.files[0]);
try{
const response=await fetch('/api/analyze',{method:'POST',body:fd});
const data=await response.json();
const box=document.getElementById('analyzer-result');
const content=document.getElementById('analysis-content');
box.style.display='block';
if(response.ok){
content.innerHTML='• <b>Filename:</b> '+data.filename+
'<br>• <b>Resolution:</b> <span style="color:#00ffcc">'+data.width+'x'+data.height+
'</span><br>• <b>Frame Rate:</b> '+data.fps+
'<br>• <b>Codec:</b> '+data.codec+
'<br>• <b>Bitrate:</b> '+data.bitrate+
'<br>• <b>Status:</b> <span style="color:#00ffcc">'+data.status_msg+'</span>';
}else content.innerHTML='<span style="color:#ff4d4d">Error: '+(data.detail||'Analysis failed')+'</span>';
}catch(e){alert('Error connecting to server.')}
finally{btn.disabled=false;btn.innerText='📊 Analyze Real Specs'}
}

// IMPORTANT: REAL FFmpeg progress
async function uploadVideo(event){
event.preventDefault();

let credits=parseInt(localStorage.getItem('smooth_free_credits')||'0');
if(!isPro && credits<=0){
alert('Aapke free credits khatam ho chuke hain!');
switchTab('pricing');return;
}

const input=document.getElementById('file-input');
if(!input.files.length)return;

document.getElementById('form-content').style.display='none';
document.getElementById('progress-overlay').style.display='block';

const fill=document.getElementById('loader-fill');
const percentText=document.getElementById('progress-percent');
const statusText=document.getElementById('progress-status-text');

const jobId=Date.now()+'-'+Math.random().toString(36).slice(2);
const fd=new FormData();
fd.append('file',input.files[0]);
fd.append('job_id',jobId);

let finished=false;

const progressTimer=setInterval(async()=>{
if(finished)return;
try{
const r=await fetch('/api/progress/'+encodeURIComponent(jobId));
const d=await r.json();
const p=Number(d.progress||0);

if(p>=0){
fill.style.width=p+'%';
percentText.innerText=p+'%';

if(p<10)statusText.innerText='Preparing video...';
else if(p<30)statusText.innerText='Processing video...';
else if(p<60)statusText.innerText='Rendering high quality...';
else if(p<90)statusText.innerText='Rendering 1080x1920 60FPS...';
else if(p<100)statusText.innerText='Finishing video...';
}
}catch(e){}
},500);

try{
const response=await fetch('/api/optimize',{method:'POST',body:fd});
const data=await response.json();

finished=true;
clearInterval(progressTimer);

if(!response.ok)throw new Error(data.detail||'Optimization failed');

fill.style.width='100%';
percentText.innerText='100%';
statusText.innerText='Optimization Complete!';

if(!isPro && credits>0){
credits--;
localStorage.setItem('smooth_free_credits',credits);
document.getElementById('free-left').innerText=credits;
}

setTimeout(()=>{
document.body.innerHTML='<div style="background:#0c0c0e;color:#fff;font-family:Segoe UI,sans-serif;text-align:center;padding-top:100px"><div style="background:#16161a;border:1px solid #26262f;max-width:500px;margin:auto;padding:40px;border-radius:16px"><h1 style="color:#00ffcc;margin-bottom:20px">🎉 Video Optimized Successfully!</h1><p style="color:#aaa;margin-bottom:30px">Aapki video optimize ho chuki hai.</p><a href="'+data.download_url+'" download class="btn">📥 Download Optimized Video</a><br><br><a href="/" style="color:#888;text-decoration:none">← Back to Optimizer</a></div></div>';
},500);

}catch(err){
finished=true;
clearInterval(progressTimer);
alert('❌ Processing Error: '+err.message);
document.getElementById('form-content').style.display='block';
document.getElementById('progress-overlay').style.display='none';
}
}

async function updateLiveUsers(){
try{
const r=await fetch('/api/live-count');
const d=await r.json();
document.getElementById('live-count').innerText=d.count;
}catch(e){}
}
setInterval(updateLiveUsers,3000);
updateLiveUsers();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    return HTML_CONTENT


@app.get("/api/live-count")
async def get_live_count():
    return {"count": max(1, len(active_connections))}


@app.middleware("http")
async def track_visitors(request, call_next):
    client_ip = request.client.host
    active_connections.add(client_ip)
    return await call_next(request)


@app.post("/api/analyze")
async def analyze_video_specs(file: UploadFile = File(...)):
    safe_name = os.path.basename(file.filename)
    temp_path = os.path.join(UPLOAD_DIR, f"temp_{uuid.uuid4().hex}_{safe_name}")

    try:
        with open(temp_path, "wb") as buffer:
            buffer.write(await file.read())

        cmd = [FFMPEG_EXE, "-i", temp_path]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output_text = result.stderr

        width, height = 1080, 1920
        fps = "Unknown"
        codec = "Unknown"
        bitrate = "Unknown"

        for line in output_text.splitlines():
            if "Stream" in line and "Video" in line:
                parts = line.split(",")

                for p in parts:
                    p = p.strip()

                    m = re.search(r"(\d{2,5})x(\d{2,5})", p)
                    if m:
                        width = int(m.group(1))
                        height = int(m.group(2))

                    if "fps" in p or "tbr" in p:
                        fps = p

                    for c in ["h264", "hevc", "vp9", "av1", "mpeg4"]:
                        if c in p.lower():
                            codec = c
                            break

            if "bitrate:" in line.lower():
                try:
                    bitrate = line.lower().split("bitrate:")[1].strip().split()[0] + " kbps"
                except Exception:
                    pass

        return {
            "filename": file.filename,
            "width": width,
            "height": height,
            "fps": fps,
            "codec": codec,
            "bitrate": bitrate,
            "status_msg": "Real specs extracted successfully!"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis Error: {str(e)}")

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/api/optimize")
def optimize_video(
    file: UploadFile = File(...),
    job_id: str = Form(...)
):
    # Unique/safe filenames prevent clashes when two users upload
    # files with the same name.
    original_name = os.path.basename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{original_name}"

    input_path = os.path.join(UPLOAD_DIR, unique_name)
    output_filename = f"optimized_{unique_name}"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    progress_store[job_id] = 0

    try:
        with open(input_path, "wb") as buffer:
            buffer.write(file.file.read())

        # Get exact duration first.
        probe = subprocess.run(
            [FFMPEG_EXE, "-i", input_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True
        )

        duration = 0.0
        match = re.search(
            r"Duration:\s*(\d+):(\d+):([\d.]+)",
            probe.stderr
        )

        if match:
            duration = (
                int(match.group(1)) * 3600
                + int(match.group(2)) * 60
                + float(match.group(3))
            )

        if duration <= 0:
            raise HTTPException(
                status_code=400,
                detail="Video duration read nahi ho saki."
            )

        command = [
            FFMPEG_EXE,
            "-y",
            "-i", input_path,

            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",

            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2",

            "-r", "60",

            "-c:a", "aac",
            "-b:a", "192k",

            "-movflags", "+faststart",

            # REAL FFmpeg progress:
            "-progress", "pipe:1",
            "-nostats",

            output_path
        ]

        startupinfo = None

        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            startupinfo=startupinfo,
            bufsize=1
        )

        # FFmpeg writes out_time_ms while rendering.
        # Convert that actual timestamp into an actual percentage.
        for line in process.stdout:
            line = line.strip()

            if line.startswith("out_time_ms="):
                try:
                    current_time = int(
                        line.split("=", 1)[1]
                    ) / 1_000_000

                    percent = int(
                        (current_time / duration) * 100
                    )

                    # Never show 100 until the process really exits.
                    percent = max(0, min(99, percent))
                    progress_store[job_id] = percent

                except (ValueError, ZeroDivisionError):
                    pass

        process.wait()

        if process.returncode != 0:
            progress_store[job_id] = -1
            raise HTTPException(
                status_code=500,
                detail="FFmpeg video processing failed."
            )

        if not os.path.exists(output_path):
            progress_store[job_id] = -1
            raise HTTPException(
                status_code=500,
                detail="Output video generate nahi hui."
            )

        # 100 means FFmpeg actually finished successfully.
        progress_store[job_id] = 100

        return {
            "status": "success",
            "download_url": f"/outputs/{output_filename}"
        }

    except HTTPException:
        raise

    except Exception as e:
        progress_store[job_id] = -1
        raise HTTPException(
            status_code=500,
            detail=f"FFmpeg Error: {str(e)}"
        )

    finally:
        if os.path.exists(input_path):
            os.remove(input_path)


@app.get("/api/progress/{job_id}")
async def get_progress(job_id: str):
    return {
        "progress": progress_store.get(job_id, 0)
    }


@app.get("/outputs/{filename}")
async def get_output_file(filename: str):
    safe_name = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_name)

    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="video/mp4",
            filename=safe_name
        )

    raise HTTPException(
        status_code=404,
        detail="File nahi mili"
    )
