import os
import subprocess
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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

# Linux (Render Docker) ke liye direct ffmpeg path
FFMPEG_EXE = "ffmpeg"

@app.get("/")
def read_root():
    return {"message": "Smooth.pk Video Optimizer API is running live!"}

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

    # Render ki kam RAM ke liye ultrafast preset aur optimize settings
    command = [
        FFMPEG_EXE,
        '-y',
        '-i', input_path,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2',
        '-r', '60',
        '-c:a', 'aac',
        '-b:a', '128k',
        output_path
    ]

    try:
        # Timeout 120 seconds rakha hai taake app hang na ho
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
        if result.returncode != 0:
            print("FFMPEG ERROR:", result.stderr)
            raise HTTPException(status_code=500, detail=f"FFmpeg Error: {result.stderr[-200:]}")
            
        return {
            "download_url": f"/api/download/{output_filename}",
            "status": "success"
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Video processing timed out! File bohot bari hai.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4", filename=filename)
    raise HTTPException(status_code=404, detail="File nahi mili!")
