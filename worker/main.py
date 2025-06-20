from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import subprocess
import os
import shutil
import uuid
import ast
import re
import boto3
from botocore.exceptions import ClientError
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import io

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
TEMP_DIR = "temp"

@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    yield
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
app.lifespan = lifespan

class PromptRequest(BaseModel):
    prompt: str

def clean_code(code: str) -> str:
    code = code.strip()
    if code.startswith("```"):
        code = code.strip("```")
        lines = code.splitlines()
        lines = [line for line in lines if line.strip().lower() != "python"]
        code = "\n".join(lines)
    return code.strip()

def extract_scene_name(code: str) -> str | None:
    match = re.search(r"class\s+(\w+)\s*\(\s*Scene\s*\):", code)
    return match.group(1) if match else None

@app.post("/generate")
async def generate_video(req: PromptRequest):
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        for attempt in range(2):
            response = model.generate_content(
                f"""Generate a clean, high-quality Manim animation in Python based on the following concept: '{req.prompt}'... [Constraints trimmed for brevity]"""
            )
            code = clean_code(response.text)
            try:
                ast.parse(code)
                break
            except SyntaxError:
                if attempt == 1:
                    return {"status": "error", "message": "Invalid code after retry"}

        os.makedirs(TEMP_DIR, exist_ok=True)
        file_path = os.path.join(TEMP_DIR, "main.py")
        with open(file_path, "w") as f:
            f.write(code)

        scene_name = extract_scene_name(code) or "GeneratedScene"

        result = subprocess.run(
            ["manim", "-ql", file_path, scene_name],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            return JSONResponse({
                "error": f"Manim failed:\n{result.stderr}\n{result.stdout}"
            }, status_code=400)

        video_file = f"{scene_name}.mp4"
        video_path = os.path.join("media", "videos", "main", "480p15", video_file)

        if not os.path.exists(video_path):
            return JSONResponse({"error": f"Video not found at {video_path}"}, status_code=500)

        # ✅ Upload to S3 using in-memory file
        with open(video_path, "rb") as f:
            file_data = io.BytesIO(f.read())

        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION")
        )
        s3_key = f"videos/{uuid.uuid4().hex}_{video_file}"
        bucket_name = os.getenv("AWS_S3_BUCKET_NAME")

        s3_client.upload_fileobj(
            file_data,
            bucket_name,
            s3_key,
            ExtraArgs={"ContentType": "video/mp4"}
        )

        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"

        # ✅ Cleanup temp files
        os.remove(video_path)
        os.remove(file_path)

        return {"status": "success", "videoUrl": s3_url}

    except subprocess.TimeoutExpired:
        return JSONResponse({"error": "Manim timed out"}, status_code=408)
    except FileNotFoundError:
        return JSONResponse({
            "error": "Manim not installed or not in PATH",
            "solution": "Install with `pip install manim` and ensure ffmpeg is available"
        }, status_code=500)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"Unexpected error: {str(e)}"}, status_code=500)

@app.get("/health")
def health_check():
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        res = model.generate_content("ping")
        return {"status": "ok", "message": res.text}
    except Exception as e:
        return {"status": "error", "message": "Unhealthy", "details": str(e)}
