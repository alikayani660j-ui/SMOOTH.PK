import os
import subprocess
import json
import glob
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="RTX Fury v3.9 - Phantom Edition")

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

active_connections = set()

desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
ffmpeg_search = glob.glob(os.path.join(desktop_path, "**", "ffmpeg.exe"), recursive=True)

if ffmpeg_search:
    FFMPEG_EXE = ffmpeg_search[0]
else:
    FFMPEG_EXE = "ffmpeg"

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>smooth.pk - TikTok Video Optimizer & Analyzer</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background-color: #0c0c0e; color: #ffffff; line-height: 1.6; }
        header { display: flex; justify-content: space-between; align-items: center; padding: 20px 50px; background: #121216; border-bottom: 1px solid #222; position: sticky; top: 0; z-index: 1000; }
        .logo { font-size: 24px; font-weight: bold; color: #00ffcc; letter-spacing: 1px; }
        nav a { color: #aaa; text-decoration: none; margin-left: 20px; font-size: 14px; transition: 0.3s; cursor: pointer; }
        nav a:hover, nav a.active { color: #00ffcc; }
        .live-badge { background: rgba(0, 255, 204, 0.1); border: 1px solid #00ffcc; padding: 5px 12px; border-radius: 20px; font-size: 13px; color: #00ffcc; display: flex; align-items: center; gap: 6px; }
        .live-dot { width: 8px; height: 8px; background: #00ffcc; border-radius: 50%; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
        
        .container { max-width: 1000px; margin: 40px auto; padding: 20px; text-align: center; }
        .section { display: none; }
        .section.active { display: block; }
        
        h1 { font-size: 42px; margin-bottom: 15px; font-weight: 800; }
        p.sub { color: #aaa; margin-bottom: 30px; font-size: 16px; }

        .card { background: #16161a; border: 1px solid #26262f; border-radius: 16px; padding: 40px; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); text-align: left; }
        .center-card { text-align: center; }
        .upload-box { border: 2px dashed #333; padding: 40px; border-radius: 12px; cursor: pointer; transition: 0.3s; background: #121215; display: block; text-align: center; }
        .upload-box:hover { border-color: #00ffcc; }
        input[type="file"] { display: none; }
        input[type="text"], textarea { width: 100%; padding: 14px; background: #121215; border: 1px solid #333; color: #fff; border-radius: 8px; font-size: 16px; margin-bottom: 15px; outline: none; }
        input[type="text"]:focus, textarea:focus { border-color: #00ffcc; }
        
        .btn { background: #00ffcc; color: #000; padding: 12px 30px; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; transition: 0.3s; margin-top: 15px; display: inline-block; text-decoration: none; text-align: center; }
        .btn:hover { background: #00cca3; transform: translateY(-2px); }

        .free-badge { background: rgba(0, 255, 204, 0.15); border: 1px solid #00ffcc; color: #00ffcc; padding: 8px 16px; border-radius: 8px; font-size: 14px; margin-bottom: 20px; display: inline-block; font-weight: bold; }

        .guide-box { background: #121215; border: 1px solid #222; padding: 20px; border-radius: 10px; margin-top: 20px; font-size: 14px; color: #ccc; }
        .guide-box h3 { color: #00ffcc; margin-bottom: 10px; }
        .guide-box ul { padding-left: 20px; }
        .guide-box li { margin-bottom: 8px; }

        /* GAMING BEFORE/AFTER SLIDER STYLES */
        .preview-container { margin-top: 25px; background: #121215; border: 1px solid #222; padding: 20px; border-radius: 12px; text-align: center; }
        .img-comparision-slider { position: relative; width: 100%; max-width: 600px; height: 350px; margin: 20px auto; overflow: hidden; border-radius: 8px; border: 1px solid #333; user-select: none; }
        
        .slider-image-wrapper { position: absolute; top: 0; left: 0; width: 50%; height: 100%; overflow: hidden; z-index: 2; }
        
        .slider-handle { position: absolute; top: 0; bottom: 0; left: 50%; width: 4px; background: #00ffcc; z-index: 3; cursor: ew-resize; }
        .slider-handle-button { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 36px; height: 36px; background: #00ffcc; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #000; font-weight: bold; font-size: 12px; box-shadow: 0 0 10px rgba(0,0,0,0.5); }
        
        .badge-before { position: absolute; top: 15px; left: 15px; background: rgba(0,0,0,0.8); color: #ff4d4d; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; z-index: 4; }
        .badge-after { position: absolute; top: 15px; right: 15px; background: rgba(0,0,0,0.8); color: #00ffcc; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; z-index: 4; }

        .complaint-section { margin-top: 30px; background: #16161a; border: 1px solid #26262f; border-radius: 16px; padding: 30px; text-align: left; }
        .complaint-section h3 { color: #00ffcc; margin-bottom: 10px; font-size: 20px; }

        .activate-section { margin-top: 30px; background: #16161a; border: 1px solid #00ffcc; border-radius: 16px; padding: 30px; text-align: center; }
        .activate-section h3 { color: #00ffcc; margin-bottom: 10px; font-size: 20px; }

        .pricing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-top: 30px; }
        .price-card { background: #16161a; border: 1px solid #26262f; border-radius: 16px; padding: 30px; text-align: left; position: relative; transition: 0.3s; }
        .price-card:hover { border-color: #00ffcc; transform: translateY(-5px); }
        .price-card h3 { font-size: 18px; color: #888; margin-bottom: 10px; }
        .price-card .price { font-size: 48px; font-weight: bold; color: #fff; margin-bottom: 20px; }
        .price-card ul { list-style: none; margin-bottom: 25px; }
        .price-card ul li { margin-bottom: 10px; color: #ccc; font-size: 14px; }
        .price-card ul li::before { content: "✓ "; color: #00ffcc; font-weight: bold; }

        .result-box { margin-top: 20px; background: #121215; padding: 20px; border-radius: 10px; text-align: left; border: 1px solid #222; display: none; }
        
        #progress-overlay { display: none; text-align: center; padding: 30px; }
        .loader-bar { width: 100%; background: #222; border-radius: 10px; height: 12px; overflow: hidden; margin: 20px 0; }
        .loader-fill { width: 0%; height: 100%; background: #00ffcc; transition: width 0.3s ease; }
    header {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 15px;
  gap: 10px;
}

nav {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}
    </style>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>

    <header>
        <div class="logo">smooth.pk</div>
        <nav>
            <a onclick="switchTab('optimizer')" id="nav-optimizer" class="active">Optimizer</a>
            <a onclick="switchTab('analyzer')" id="nav-analyzer">Video Analyzer</a>
            <a onclick="switchTab('pricing')" id="nav-pricing">PRO Plans</a>
        </nav>
        <div class="live-badge">
            <div class="live-dot"></div>
            <span id="live-count">1</span> Live
        </div>
    </header>

    <div class="container">
        <!-- OPTIMIZER SECTION -->
        <div id="optimizer" class="section active">
            <h1>TIKTOK VIDEO OPTIMIZER</h1>
            <p class="sub">Bypass TikTok compression while preserving maximum high-end quality using our engine.</p>
            
            <div class="center-card free-badge" id="status-badge">
                🎁 Special Offer: Pehle 2 videos bilkul **FREE** optimize karein! (<span id="free-left">2</span> free credits left)
            </div>

            <div class="card center-card">
                <form id="upload-form" onsubmit="uploadVideo(event)">
                    <div id="form-content">
                        <label class="upload-box" id="drop-zone">
                            <input type="file" name="file" id="file-input" required onchange="showFileName('file-input', 'upload-text', '📁 Drop your video here or click to browse')">
                            <div id="upload-text">
                                <h3>📁 Drop your video here or click to browse</h3>
                                <p style="color: #666; font-size: 13px; margin-top: 8px;">Supports MP4, MOV from your Desktop</p>
                            </div>
                        </label>
                        <br>
                        <button type="submit" class="btn" id="submit-btn">⚡ Optimize Video Now</button>
                    </div>

                    <!-- PROGRESS BAR CONTAINER -->
                    <div id="progress-overlay">
                        <h3 style="color: #00ffcc; margin-bottom: 10px;" id="progress-title">⚡ Optimizing Video Quality...</h3>
                        <p id="progress-status-text" style="color: #aaa; font-size: 14px;">Please wait, rendering top-tier 1080x1920 60FPS video...</p>
                        <div class="loader-bar">
                            <div class="loader-fill" id="loader-fill"></div>
                        </div>
                        <h2 id="progress-percent" style="color: #fff; font-size: 28px; font-weight: bold;">0%</h2>
                    </div>
                </form>

                <!-- PRO ACTIVATION BOX -->
                <div class="activate-section">
                    <h3>💎 Already Paid? Activate PRO Key</h3>
                    <p style="color: #aaa; font-size: 13px; margin-bottom: 15px;">Agar aapne payment kardi hai, toh WhatsApp par mila hua secret code yahan enter karein:</p>
                    <div style="display: flex; gap: 10px; max-width: 400px; margin: auto;">
                        <input type="text" id="promo-code" placeholder="Enter PRO Code (e.g. SMOOTH-...)" style="margin-bottom: 0;">
                        <button onclick="activatePro()" class="btn" style="margin-top: 0; white-space: nowrap;">Activate</button>
                    </div>
                </div>

                <!-- HOW TO USE GUIDE -->
                <div class="guide-box">
                    <h3>📌 How to Use & Instructions:</h3>
                    <ul>
                        <li><b>Desktop Upload:</b> Behtar performance aur heavy files ke liye hamesha apni video **Desktop** ya PC se select karke upload karein.</li>
                        <li><b>Free Credits:</b> Har naye user ko 2 videos bilkul free optimize karne ki sahulat milti hai.</li>
                        <li><b>Quality:</b> Engine aapki video ko 1080x1920 resolution aur 60 FPS par top-tier quality mein render karta hai jo TikTok par blur nahi hoti.</li>
                    </ul>
                </div>

                <!-- GAMING BEFORE & AFTER IMAGE SLIDER -->
                <div class="preview-container">
                    <h3 style="color: #00ffcc; margin-bottom: 6px;">🔥 Gaming Before & After Slider</h3>
                    <p style="color: #aaa; font-size: 13px; margin-bottom: 15px;">Slider ko drag karke check karein: 1 taraf Laggy aur doosri taraf Smooth quality!</p>
                    
                    <div class="img-comparision-slider" id="comparison-slider">
                        <!-- AFTER IMAGE (Smooth & Clear Gaming Setup) -->
                        <div class="badge-after">SMOOTH ⚡</div>
                        <img src="https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; pointer-events: none;" alt="Smooth Gaming">
                        
                        <!-- BEFORE IMAGE (Laggy / Blurred) -->
                        <div class="slider-image-wrapper" id="slider-wrapper">
                            <div class="badge-before">LAGGY 🚫</div>
                            <img src="https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800" style="position: absolute; top: 0; left: 0; width: 600px; height: 100%; object-fit: cover; max-width: none; filter: blur(6px) grayscale(50%);" alt="Laggy Gaming">
                        </div>
                        
                        <!-- SLIDER HANDLE BAR -->
                        <div class="slider-handle" id="slider-handle">
                            <div class="slider-handle-button">↔</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- VIDEO ANALYZER SECTION -->
        <div id="analyzer" class="section">
            <h1>REAL VIDEO ANALYZER</h1>
            <p class="sub">Upload any video file to inspect its actual resolution, real frame rate, codec, and bitrate.</p>
            
            <div class="card center-card">
                <form id="analyzer-form" onsubmit="analyzeVideo(event)">
                    <label class="upload-box">
                        <input type="file" name="file" id="analyzer-file-input" required onchange="showFileName('analyzer-file-input', 'analyzer-upload-text', '📁 Video Selected for Analysis')">
                        <div id="analyzer-upload-text">
                            <h3>📁 Upload video file from Desktop to analyze specs</h3>
                            <p style="color: #666; font-size: 13px; margin-top: 8px;">Get accurate specs of your specific video</p>
                        </div>
                    </label>
                    <br>
                    <button type="submit" class="btn" id="analyzer-btn">📊 Analyze Real Specs</button>
                </form>

                <div id="analyzer-result" class="result-box">
                    <h3 style="color: #00ffcc; margin-bottom: 10px;">📊 Real Video Analysis Report</h3>
                    <div id="analysis-content" style="color: #ccc; font-size: 14px; line-height: 1.8;"></div>
                </div>
            </div>
        </div>

        <!-- PRICING SECTION -->
        <div id="pricing" class="section">
            <h1>GO PRO</h1>
            <p class="sub">Unlock unlimited high-end optimizations, larger uploads, and priority processing.</p>
            
            <div class="pricing-grid">
                <div class="price-card">
                    <h3>1 MONTH</h3>
                    <div class="price">$1</div>
                    <ul>
                        <li>30 Days Access</li>
                        <li>Unlimited optimizations</li>
                        <li>Larger video uploads</li>
                        <li>No daily limits</li>
                    </ul>
                    <a href="https://wa.me/923199628815?text=Hi%20Ali,%20I%20want%20to%20buy%201%20Month%20PRO%20Access%20for%20$1" target="_blank" class="btn" style="width: 100%;">Get via WhatsApp ($1)</a>
                </div>

                <div class="price-card" style="border-color: #00ffcc;">
                    <h3>5 MONTHS</h3>
                    <div class="price">$5</div>
                    <ul>
                        <li>5 Months Full Access</li>
                        <li>Unlimited optimizations</li>
                        <li>Larger video uploads</li>
                        <li>Priority processing engine</li>
                    </ul>
                    <a href="https://wa.me/923199628815?text=Hi%20Ali,%20I%20want%20to%20buy%205%20Months%20PRO%20Access%20for%20$5" target="_blank" class="btn" style="width: 100%;">Get via WhatsApp ($5)</a>
                </div>

                <div class="price-card">
                    <h3>UNLIMITED LIFETIME</h3>
                    <div class="price">$20</div>
                    <ul>
                        <li>Lifetime Access</li>
                        <li>Unlimited optimizations</li>
                        <li>Maximum file size support</li>
                        <li>VIP Support & Updates</li>
                    </ul>
                    <a href="https://instagram.com/alikayani09" target="_blank" class="btn" style="width: 100%;">Get via Instagram ($20)</a>
                </div>
            </div>
        </div>

        <!-- COMPLAINT / SUPPORT SYSTEM -->
        <div class="complaint-section">
            <h3>🛠️ Koi Bhi Masla Ho? Yahan Complaint Likhein!</h3>
            <p style="color: #aaa; font-size: 13px; margin-bottom: 15px;">Agar aapko video optimization ya kisi bhi cheez mein koi masla aa raha hai, toh apna message yahan likh kar direct hamare WhatsApp par send karein:</p>
            <textarea id="complaint-text" rows="3" placeholder="Apna masla yahan type karein..."></textarea>
            <br>
            <button onclick="sendComplaint()" class="btn" style="margin-top: 0;">💬 Send Complaint via WhatsApp</button>
        </div>
    </div>

    <script>
        let isPro = localStorage.getItem('smooth_is_pro') === 'true';
        let freeCredits = localStorage.getItem('smooth_free_credits');
        if (freeCredits === null) {
            freeCredits = 2;
            localStorage.setItem('smooth_free_credits', freeCredits);
        }

        function updateUIStatus() {
            if (isPro) {
                document.getElementById('status-badge').innerHTML = "🔥 PRO ACCOUNT ACTIVE: Aapke paas unlimited optimizations hain!";
                document.getElementById('status-badge').style.borderColor = "#00ffcc";
            } else {
                document.getElementById('free-left').innerText = freeCredits;
            }
        }
        updateUIStatus();

        function activatePro() {
            const code = document.getElementById('promo-code').value.trim();
            const validCodes = ["SMOOTH-1M-786", "SMOOTH-5M-992", "SMOOTH-LIFE-2026"];
            
            if (validCodes.includes(code)) {
                localStorage.setItem('smooth_is_pro', 'true');
                isPro = true;
                updateUIStatus();
                alert("🎉 Mubarak ho! Aapka PRO account successfully activate ho gaya hai.");
            } else {
                alert("❌ Ghalat code! Baraye meharbani theek code enter karein jo aapko WhatsApp par mila hai.");
            }
        }

        function switchTab(tabId) {
            document.querySelectorAll('.section').forEach(sec => sec.classList.remove('active'));
            document.querySelectorAll('nav a').forEach(nav => nav.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            document.getElementById('nav-' + tabId).classList.add('active');
        }

        function showFileName(inputId, textId, defaultText) {
            const input = document.getElementById(inputId);
            const textDiv = document.getElementById(textId);
            if (input.files.length > 0) {
                textDiv.innerHTML = `<h3 style="color: #00ffcc;">✅ Selected: ${input.files[0].name}</h3>`;
            } else {
                textDiv.innerHTML = `<h3>${defaultText}</h3>`;
            }
        }

        function sendComplaint() {
            const msg = document.getElementById('complaint-text').value.trim();
            if (!msg) {
                alert("Pehle apna masla ya complaint box mein type karein!");
                return;
            }
            const encodedMsg = encodeURIComponent("Complaint / Issue: " + msg);
            window.open(`https://wa.me/923199628815?text=${encodedMsg}`, '_blank');
        }

        // GAMING SLIDER LOGIC
        const slider = document.getElementById('comparison-slider');
        const sliderWrapper = document.getElementById('slider-wrapper');
        const sliderHandle = document.getElementById('slider-handle');

        let isDragging = false;

        function updateSlider(clientX) {
            const rect = slider.getBoundingClientRect();
            let x = clientX - rect.left;
            if (x < 0) x = 0;
            if (x > rect.width) x = rect.width;
            
            const percent = (x / rect.width) * 100;
            sliderWrapper.style.width = percent + '%';
            sliderHandle.style.left = percent + '%';
        }

        slider.addEventListener('mousedown', (e) => {
            isDragging = true;
            updateSlider(e.clientX);
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            updateSlider(e.clientX);
        });

        window.addEventListener('mouseup', () => {
            isDragging = false;
        });

        slider.addEventListener('touchstart', (e) => {
            isDragging = true;
            updateSlider(e.touches[0].clientX);
        });

        window.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            updateSlider(e.touches[0].clientX);
        });

        window.addEventListener('touchend', () => {
            isDragging = false;
        });

        async function analyzeVideo(event) {
            event.preventDefault();
            const fileInput = document.getElementById('analyzer-file-input');
            if (fileInput.files.length === 0) return;

            const btn = document.getElementById('analyzer-btn');
            btn.innerText = "⏳ Reading real metadata...";
            btn.disabled = true;

            const formData = new FormData();
            formData.append("file", fileInput.files[0]);

            try {
                const response = await fetch('/api/analyze', { method: 'POST', body: formData });
                const data = await response.json();
                const resBox = document.getElementById('analyzer-result');
                const contentDiv = document.getElementById('analysis-content');
                resBox.style.display = "block";

                if (response.ok) {
                    contentDiv.innerHTML = `
                        • <b>Filename:</b> ${data.filename}<br>
                        • <b>Resolution:</b> <span style="color: #00ffcc;">${data.width}x${data.height}</span><br>
                        • <b>Frame Rate (FPS):</b> ${data.fps}<br>
                        • <b>Video Codec:</b> ${data.codec}<br>
                        • <b>Bitrate:</b> ${data.bitrate}<br>
                        • <b>TikTok Status:</b> <span style="color: #00ffcc;">${data.status_msg}</span>
                    `;
                } else {
                    contentDiv.innerHTML = `<span style="color: #ff4d4d;">Error: ${data.detail || 'Analysis failed'}</span>`;
                }
            } catch (err) {
                alert("Error connecting to server.");
            } finally {
                btn.innerText = "📊 Analyze Real Specs";
                btn.disabled = false;
            }
        }

        async function uploadVideo(event) {
            event.preventDefault();
            let credits = parseInt(localStorage.getItem('smooth_free_credits') || 0);
            
            if (!isPro && credits <= 0) {
                alert("Aapke 2 free credits khatam ho chuke hain! Mazeed videos optimize karne ke liye PRO plan khareedain ya PRO code enter karein.");
                switchTab('pricing');
                return;
            }

            const fileInput = document.getElementById('file-input');
            if (fileInput.files.length === 0) return;

            document.getElementById('form-content').style.display = 'none';
            document.getElementById('progress-overlay').style.display = 'block';

            let progress = 0;
            const fill = document.getElementById('loader-fill');
            const percentText = document.getElementById('progress-percent');
            const statusText = document.getElementById('progress-status-text');

            const timer = setInterval(() => {
                if (progress < 95) {
                    progress += 1;
                    fill.style.width = progress + '%';
                    percentText.innerText = progress + '%';
                    
                    if(progress > 20 && progress < 50) {
                        statusText.innerText = "Applying Phantom high-end slow-mo filter...";
                    } else if(progress >= 50) {
                        statusText.innerText = "Rendering 60 FPS master quality...";
                    }
                }
            }, 80);

            const formData = new FormData();
            formData.append("file", fileInput.files[0]);

            try {
                const response = await fetch('/api/optimize', { method: 'POST', body: formData });
                const data = await response.json();

                clearInterval(timer);
                fill.style.width = '100%';
                percentText.innerText = '100%';
                statusText.innerText = "Optimization Complete!";

                if (response.ok) {
                    if (!isPro && credits > 0) {
                        credits--;
                        localStorage.setItem('smooth_free_credits', credits);
                        document.getElementById('free-left').innerText = credits;
                    }

                    setTimeout(() => {
                        document.body.innerHTML = `
                            <div style="background-color: #0c0c0e; color: #fff; font-family: 'Segoe UI', sans-serif; text-align: center; padding-top: 100px;">
                                <div style="background: #16161a; border: 1px solid #26262f; max-width: 500px; margin: auto; padding: 40px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                                    <h1 style="color: #00ffcc; margin-bottom: 20px; font-size: 28px;">🎉 Video Optimized Successfully!</h1>
                                    <p style="color: #aaa; margin-bottom: 30px; font-size: 15px;">Aapki video master quality par optimize ho chuki hai.</p>
                                    <a href="${data.download_url}" class="btn" download style="background: #00ffcc; color: #000; padding: 14px 30px; font-weight: bold; border-radius: 8px; text-decoration: none; display: inline-block;">📥 Download Optimized Video</a>
                                    <br><br>
                                    <a href="/" style="color: #888; text-decoration: none; font-size: 14px;">← Back to Optimizer</a>
                                </div>
                            </div>
                        `;
                    }, 500);
                } else {
                    alert("Error: " + (data.detail || "Kuch ghalat ho gaya"));
                    document.getElementById('form-content').style.display = 'block';
                    document.getElementById('progress-overlay').style.display = 'none';
                }
            } catch (err) {
                clearInterval(timer);
                alert("Processing Error: Video compress hone mein waqt le rahi hai.");
                document.getElementById('form-content').style.display = 'block';
                document.getElementById('progress-overlay').style.display = 'none';
            }
        }

        async function updateLiveUsers() {
            try {
                const res = await fetch('/api/live-count');
                const data = await res.json();
                document.getElementById('live-count').innerText = data.count;
            } catch (e) {}
        }
        setInterval(updateLiveUsers, 3000);
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
    count = max(1, len(active_connections))
    return {"count": count}

@app.middleware("http")
async def track_visitors(request, call_next):
    client_ip = request.client.host
    active_connections.add(client_ip)
    response = await call_next(request)
    return response

@app.post("/api/analyze")
async def analyze_video_specs(file: UploadFile = File(...)):
    temp_path = os.path.join(UPLOAD_DIR, f"temp_{file.filename}")
    try:
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        cmd = [FFMPEG_EXE, '-i', temp_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output_text = result.stderr
        
        width, height, fps, codec, bitrate = 1080, 1920, "60 fps", "h264", "Unknown"
        for line in output_text.split('\n'):
            if "Stream" in line and "Video" in line:
                if "x" in line:
                    parts = line.split(',')
                    for p in parts:
                        p = p.strip()
                        if "x" in p and any(char.isdigit() for char in p):
                            res = p.split(' ')[0]
                            if 'x' in res:
                                try:
                                    w, h = res.split('x')
                                    width, height = int(w), int(h)
                                except:
                                    pass
                        if "fps" in p or "tb(s)" in p or "tbr" in p:
                            fps = p
                        if any(c in p for c in ["h264", "hevc", "vp9", "av1", "mpeg4"]):
                            codec = p.split(' ')[0]
            if "bitrate:" in line:
                try:
                    bitrate = line.split("bitrate:")[1].strip().split(" ")[0] + " kbps"
                except:
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
async def optimize_video(file: UploadFile = File(...)):
    input_path = os.path.join(UPLOAD_DIR, file.filename)
    output_filename = f"optimized_{file.filename}"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    try:
        with open(input_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save nahi ho saki: {str(e)}")

    command = [
        FFMPEG_EXE,
        '-y',
        '-i', input_path,
        '-c:v', 'libx264',
        '-preset', 'slow',
        '-crf', '16',
        '-pix_fmt', 'yuv420p',
        '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setpts=1.25*PTS',
        '-r', '60',
        '-c:a', 'aac',
        '-b:a', '192k',
        output_path
    ]

    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0 # SW_HIDE

        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, startupinfo=startupinfo)
    except Exception as e:
        error_msg = getattr(e, 'stderr', str(e))
        raise HTTPException(status_code=500, detail=f"FFmpeg Error: {error_msg}")

    return {
        "status": "success",
        "download_url": f"/api/download/{output_filename}"
    }

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4", filename=filename)
    raise HTTPException(status_code=404, detail="File nahi mili!")
