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


# =========================================================
# APP
# =========================================================

app = FastAPI(title="SMOOTH.PK")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DIRECTORIES
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# FFMPEG DETECTION
# =========================================================

def find_program(name: str):
    """
    Works on Railway/Linux, Windows and Docker.
    """

    found = shutil.which(name)

    if found:
        return found

    possible_paths = [
        "/usr/bin/" + name,
        "/usr/local/bin/" + name,
        "/bin/" + name,
        "/opt/render/project/.render/bin/" + name,
        "/app/" + name,
    ]

    for path in possible_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    return None


FFMPEG_EXE = find_program("ffmpeg")
FFPROBE_EXE = find_program("ffprobe")


# =========================================================
# PROGRESS STORAGE
# =========================================================

progress_store = {}


def set_progress(job_id, percent, status="processing", **extra):
    progress_store[job_id] = {
        "progress": max(0, min(100, int(percent))),
        "status": status,
        **extra
    }


# =========================================================
# HELPERS
# =========================================================

def safe_filename(filename: str):
    """
    Removes unsafe characters from uploaded filenames.
    """

    filename = filename or "video.mp4"

    filename = Path(filename).name

    filename = re.sub(
        r"[^a-zA-Z0-9._-]",
        "_",
        filename
    )

    if not filename:
        filename = "video.mp4"

    return filename


def get_duration(file_path: str):
    """
    Get video duration using ffprobe.
    """

    if not FFPROBE_EXE:
        return None

    try:
        result = subprocess.run(
            [
                FFPROBE_EXE,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )

        value = result.stdout.strip()

        if value:
            duration = float(value)

            if duration > 0:
                return duration

    except Exception as e:
        print("FFPROBE ERROR:", repr(e))

    return None


# =========================================================
# HOME PAGE
# =========================================================

HTML_CONTENT = r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>SMOOTH.PK - TikTok Video Optimizer</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100vh;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background:
        linear-gradient(
            135deg,
            #090909,
            #151515,
            #080808
        );

    color: white;

    display: flex;
    justify-content: center;
    align-items: center;

    padding: 20px;
}

.container {
    width: 100%;
    max-width: 650px;

    background: rgba(25,25,25,0.96);

    border: 1px solid #292929;

    border-radius: 24px;

    padding: 30px;

    box-shadow:
        0 20px 60px rgba(0,0,0,0.45);
}

.logo {
    text-align: center;

    font-size: 38px;

    font-weight: 900;

    margin-bottom: 5px;
}

.logo span {
    color: #ff0050;
}

.subtitle {
    text-align: center;

    color: #aaa;

    margin-bottom: 30px;
}

.upload-box {
    border: 2px dashed #444;

    border-radius: 18px;

    padding: 35px 20px;

    text-align: center;

    cursor: pointer;

    transition: 0.2s;
}

.upload-box:hover {
    border-color: #ff0050;
    background: rgba(255,0,80,0.04);
}

.upload-icon {
    font-size: 48px;
    margin-bottom: 10px;
}

input[type=file] {
    display: none;
}

.file-name {
    margin-top: 15px;

    color: #bbb;

    word-break: break-word;
}

button {
    width: 100%;

    margin-top: 20px;

    border: none;

    border-radius: 13px;

    padding: 15px;

    background: #ff0050;

    color: white;

    font-size: 17px;

    font-weight: bold;

    cursor: pointer;
}

button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.progress-container {
    display: none;

    margin-top: 25px;
}

.progress-top {
    display: flex;

    justify-content: space-between;

    margin-bottom: 9px;

    color: #ccc;
}

.progress-bar {
    width: 100%;

    height: 14px;

    background: #2b2b2b;

    border-radius: 20px;

    overflow: hidden;
}

.progress-fill {
    height: 100%;

    width: 0%;

    background:
        linear-gradient(
            90deg,
            #ff0050,
            #ff336f
        );

    border-radius: 20px;

    transition: width 0.25s linear;
}

.status {
    text-align: center;

    margin-top: 15px;

    color: #aaa;

    font-size: 14px;
}

.result {
    display: none;

    margin-top: 25px;

    text-align: center;

    padding: 20px;

    background: #151515;

    border-radius: 15px;
}

.download-btn {
    display: block;

    text-decoration: none;

    margin-top: 15px;

    background: #20c997;

    color: white;

    padding: 13px;

    border-radius: 12px;

    font-weight: bold;
}

.error {
    color: #ff5c75;
}

.success {
    color: #20c997;
}

</style>

</head>

<body>

<div class="container">

    <div class="logo">
        SMOOTH<span>.PK</span>
    </div>

    <div class="subtitle">
        TikTok Video Optimizer
    </div>


    <label
        class="upload-box"
        for="videoInput"
    >

        <div class="upload-icon">
            🎬
        </div>

        <div>
            Select your video
        </div>

        <div class="file-name" id="fileName">
            MP4, MOV, AVI and other video files
        </div>

    </label>


    <input
        id="videoInput"
        type="file"
        accept="video/*"
    >


    <button
        id="processBtn"
        onclick="startProcessing()"
        disabled
    >
        Optimize Video
    </button>


    <div
        class="progress-container"
        id="progressContainer"
    >

        <div class="progress-top">

            <span id="progressText">
                0%
            </span>

            <span id="statusText">
                Starting...
            </span>

        </div>


        <div class="progress-bar">

            <div
                class="progress-fill"
                id="progressFill"
            ></div>

        </div>


        <div
            class="status"
            id="status"
        >
            Preparing video...
        </div>

    </div>


    <div
        class="result"
        id="result"
    >

        <div
            class="success"
            style="font-size:20px;font-weight:bold;"
        >
            ✅ Video Ready
        </div>

        <a
            id="downloadBtn"
            class="download-btn"
            href="#"
        >
            Download Optimized Video
        </a>

    </div>

</div>


<script>

let selectedFile = null;

let currentJobId = null;

let progressTimer = null;


const videoInput =
    document.getElementById("videoInput");

const fileName =
    document.getElementById("fileName");

const processBtn =
    document.getElementById("processBtn");

const progressContainer =
    document.getElementById("progressContainer");

const progressFill =
    document.getElementById("progressFill");

const progressText =
    document.getElementById("progressText");

const statusText =
    document.getElementById("statusText");

const status =
    document.getElementById("status");

const result =
    document.getElementById("result");

const downloadBtn =
    document.getElementById("downloadBtn");


videoInput.addEventListener(
    "change",
    function() {

        if (!this.files.length) {
            selectedFile = null;

            fileName.textContent =
                "MP4, MOV, AVI and other video files";

            processBtn.disabled = true;

            return;
        }


        selectedFile = this.files[0];

        fileName.textContent =
            selectedFile.name;

        processBtn.disabled = false;

        result.style.display = "none";

    }
);


async function startProcessing() {

    if (!selectedFile) {
        return;
    }


    processBtn.disabled = true;

    progressContainer.style.display = "block";

    result.style.display = "none";


    setProgressUI(
        0,
        "Uploading..."
    );


    const formData =
        new FormData();

    formData.append(
        "file",
        selectedFile
    );


    try {

        const response =
            await fetch(
                "/api/optimize",
                {
                    method: "POST",
                    body: formData
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Video processing failed."
            );

        }


        currentJobId =
            data.job_id;


        startProgressPolling();

    }

    catch (error) {

        showError(
            error.message
        );

        processBtn.disabled = false;

    }

}


function startProgressPolling() {

    if (progressTimer) {
        clearInterval(progressTimer);
    }


    progressTimer =
        setInterval(
            checkProgress,
            500
        );


    checkProgress();

}


async function checkProgress() {

    if (!currentJobId) {
        return;
    }


    try {

        const response =
            await fetch(
                "/api/progress/" +
                currentJobId
            );


        const data =
            await response.json();


        const percent =
            Number(data.progress || 0);


        setProgressUI(
            percent,
            data.status_text ||
            "Processing..."
        );


        if (
            data.status === "completed"
        ) {

            clearInterval(
                progressTimer
            );

            progressTimer = null;


            setProgressUI(
                100,
                "Complete!"
            );


            downloadBtn.href =
                data.download_url;


            result.style.display =
                "block";


            processBtn.disabled =
                false;

        }


        if (
            data.status === "error"
        ) {

            clearInterval(
                progressTimer
            );

            progressTimer = null;


            showError(
                data.error ||
                "FFmpeg video processing failed."
            );


            processBtn.disabled =
                false;

        }

    }

    catch (error) {

        console.log(
            "Progress error:",
            error
        );

    }

}


function setProgressUI(
    percent,
    text
) {

    percent =
        Math.max(
            0,
            Math.min(
                100,
                Math.round(percent)
            )
        );


    progressFill.style.width =
        percent + "%";


    progressText.textContent =
        percent + "%";


    statusText.textContent =
        text;


    status.textContent =
        text;

}


function showError(message) {

    progressContainer.style.display =
        "block";


    status.innerHTML =
        '<span class="error">❌ ' +
        escapeHtml(message) +
        '</span>';


    statusText.textContent =
        "Error";


    progressText.textContent =
        "0%";


    progressFill.style.width =
        "0%";

}


function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent =
        text;

    return div.innerHTML;

}

</script>

</body>

</html>
"""


# =========================================================
# HOME ROUTE
# =========================================================

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_CONTENT


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "ffmpeg": FFMPEG_EXE or "NOT FOUND",
        "ffprobe": FFPROBE_EXE or "NOT FOUND"
    }


# =========================================================
# OPTIMIZATION
# =========================================================

@app.post("/api/optimize")
def optimize_video(file: UploadFile = File(...)):

    if not FFMPEG_EXE:
        raise HTTPException(
            status_code=500,
            detail="FFmpeg is not installed on the server."
        )


    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No video file selected."
        )


    job_id =
        str(uuid.uuid4())


    original_name =
        safe_filename(file.filename)


    input_path =
        UPLOAD_DIR / (
            job_id + "_" + original_name
        )


    output_path =
        OUTPUT_DIR / (
            job_id + "_optimized.mp4"
        )


    try:

        with open(
            input_path,
            "wb"
        ) as buffer:

            while True:

                chunk =
                    file.file.read(
                        1024 * 1024
                    )

                if not chunk:
                    break

                buffer.write(chunk)


    except Exception as e:

        print(
            "UPLOAD ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Could not save uploaded video."
        )


    progress_store[job_id] = {
        "progress": 1,
        "status": "processing",
        "status_text": "Reading video..."
    }


    thread =
        threading.Thread(
            target=run_ffmpeg,
            args=(
                job_id,
                str(input_path),
                str(output_path),
            ),
            daemon=True
        )


    thread.start()


    return {
        "job_id": job_id
    }


# =========================================================
# FFMPEG WORKER
# =========================================================

def run_ffmpeg(
    job_id,
    input_path,
    output_path
):

    try:

        duration =
            get_duration(
                input_path
            )


        if not duration:

            print(
                "WARNING: Could not detect duration."
            )


        set_progress(
            job_id,
            1,
            "processing",
            status_text="Starting FFmpeg..."
        )


        # -------------------------------------------------
        # RAILWAY-FRIENDLY ENCODING
        # -------------------------------------------------
        #
        # veryfast = much less CPU than slow
        #
        # CRF 20 = good quality
        #
        # Do NOT force 60fps.
        # This prevents unnecessary CPU usage.
        #
        # Scale to max 1080x1920 while keeping aspect ratio.
        #

        command = [

            FFMPEG_EXE,

            "-y",

            "-hide_banner",

            "-i",
            input_path,

            "-map",
            "0:v:0",

            "-map",
            "0:a:0?",

            "-vf",
            (
                "scale="
                "1080:1920:"
                "force_original_aspect_ratio=decrease,"
                "pad=1080:1920:"
                "(ow-iw)/2:"
                "(oh-ih)/2"
            ),

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "20",

            "-pix_fmt",
            "yuv420p",

            "-c:a",
            "aac",

            "-b:a",
            "128k",

            "-movflags",
            "+faststart",

            "-progress",
            "pipe:1",

            "-nostats",

            output_path
        ]


        print("")
        print("========================================")
        print("FFMPEG START")
        print("JOB:", job_id)
        print("FFMPEG:", FFMPEG_EXE)
        print("FFPROBE:", FFPROBE_EXE)
        print("DURATION:", duration)
        print("COMMAND:")
        print(" ".join(command))
        print("========================================")
        print("")


        process =
            subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )


        stderr_lines = []


        def read_stderr():

            try:

                for line in process.stderr:

                    line =
                        line.strip()

                    if line:

                        stderr_lines.append(
                            line
                        )

                        print(
                            "FFMPEG:",
                            line
                        )

            except Exception as e:

                print(
                    "STDERR READ ERROR:",
                    repr(e)
                )


        stderr_thread =
            threading.Thread(
                target=read_stderr,
                daemon=True
            )

        stderr_thread.start()


        last_percent = 1


        while True:

            line =
                process.stdout.readline()


            if not line:

                if process.poll() is not None:
                    break

                continue


            line =
                line.strip()


            if line.startswith(
                "out_time_ms="
            ):

                try:

                    out_time_ms =
                        int(
                            line.split(
                                "=",
                                1
                            )[1]
                        )


                    if duration:

                        current_seconds =
                            out_time_ms / 1_000_000


                        percent =
                            int(
                                (
                                    current_seconds /
                                    duration
                                ) * 100
                            )


                        percent =
                            max(
                                1,
                                min(
                                    99,
                                    percent
                                )
                            )


                        if percent > last_percent:

                            last_percent =
                                percent


                            set_progress(
                                job_id,
                                percent,
                                "processing",
                                status_text=(
                                    "Optimizing video..."
                                )
                            )


                except Exception as e:

                    print(
                        "PROGRESS PARSE ERROR:",
                        repr(e)
                    )


        return_code =
            process.wait()


        stderr_thread.join(
            timeout=2
        )


        print(
            "FFMPEG EXIT CODE:",
            return_code
        )


        if return_code != 0:

            error_text =
                "\n".join(
                    stderr_lines[-20:]
                )


            print("")
            print(
                "FFMPEG FAILED:"
            )
            print(
                error_text
            )
            print("")


            set_progress(
                job_id,
                0,
                "error",
                status_text="FFmpeg failed",
                error=(
                    "FFmpeg processing failed. "
                    + (
                        error_text[-1500:]
                        if error_text
                        else
                        "No FFmpeg error was returned."
                    )
                )
            )

            return


        if not os.path.exists(
            output_path
        ):

            set_progress(
                job_id,
                0,
                "error",
                status_text="Output file missing",
                error=(
                    "FFmpeg finished but "
                    "the output file was not created."
                )
            )

            return


        output_size =
            os.path.getsize(
                output_path
            )


        if output_size <= 0:

            set_progress(
                job_id,
                0,
                "error",
                status_text="Empty output",
                error="FFmpeg created an empty file."
            )

            return


        # -------------------------------------------------
        # ONLY NOW = 100%
        # -------------------------------------------------

        set_progress(
            job_id,
            100,
            "completed",
            status_text="Complete!",
            download_url=(
                "/outputs/" +
                os.path.basename(
                    output_path
                )
            )
        )


        print(
            "SUCCESS:",
            output_path
        )


        # Delete original upload after success

        try:

            os.remove(
                input_path
            )

        except Exception:
            pass


    except Exception as e:

        print("")
        print(
            "WORKER ERROR:",
            repr(e)
        )
        print("")


        set_progress(
            job_id,
            0,
            "error",
            status_text="Processing error",
            error=str(e)
        )


# =========================================================
# PROGRESS API
# =========================================================

@app.get("/api/progress/{job_id}")
def get_progress(job_id: str):

    data =
        progress_store.get(
            job_id
        )


    if not data:

        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )


    return data


# =========================================================
# OUTPUT DOWNLOAD
# =========================================================

@app.get("/outputs/{filename}")
def download_output(
    filename: str
):

    safe_name =
        Path(filename).name


    file_path =
        OUTPUT_DIR / safe_name


    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Output file not found."
        )


    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=safe_name
    )


# =========================================================
# STARTUP INFO
# =========================================================

@app.on_event("startup")
def startup_event():

    print("")
    print("========================================")
    print("SMOOTH.PK STARTED")
    print("========================================")
    print(
        "FFmpeg:",
        FFMPEG_EXE or "NOT FOUND"
    )
    print(
        "FFprobe:",
        FFPROBE_EXE or "NOT FOUND"
    )
    print("========================================")
    print("")


# =========================================================
# LOCAL RUN
# =========================================================

if __name__ == "__main__":

    import uvicorn

    port =
        int(
            os.environ.get(
                "PORT",
                "8000"
            )
        )


    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
