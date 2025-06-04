from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import subprocess
import re

app = FastAPI()

genai.configure(api_key="YOUR_API_KEY")

class PromptRequest(BaseModel):
    prompt: str

def clean_code(code: str) -> str:
    """
    Clean Gemini response code by removing markdown fences and 'python' label.
    """
    code = code.strip()
    if code.startswith("```"):
        code = code.strip("```")
        lines = code.splitlines()
        # Remove any line that is exactly 'python' (case-insensitive)
        lines = [line for line in lines if line.strip().lower() != "python"]
        code = "\n".join(lines)
    return code.strip()

@app.post("/generate")
async def generate_video(req: PromptRequest):
    prompt = req.prompt

    try:
        model = genai.GenerativeModel("gemini-2.0-flash-lite")

        for attempt in range(2):
            response = model.generate_content(
                f"Write a short, syntactically correct Manim Scene class Python code to: {prompt}. "
                "Use 'from manim import *' and only one Scene subclass. No extra explanation or comments."
            )
            code = clean_code(response.text)

            try:
                compile(code, "generated_scene.py", "exec")
                break  
            except SyntaxError:
                if attempt == 1:
                    return {
                        "status": "error",
                        "message": "Invalid Python code generated after retry",
                    }
          

        with open("generated_scene.py", "w") as f:
            f.write(code)

        match = re.search(r"class\s+(\w+)\(.*?Scene.*?\):", code)
        scene_class = match.group(1) if match else "Scene"

       
        subprocess.run(
            ["manim", "generated_scene.py", scene_class, "-o", "output.mp4", "-ql"],
            check=True,
            text=True,
            capture_output=True,
            timeout=120

        )

        return {
            "status": "success",
            "path": "./output.mp4",
            "scene": scene_class
        }

    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": "Manim rendering failed", "details": str(e)}
    except Exception as e:
        return {"status": "error", "message": "Unexpected error", "details": str(e)}
