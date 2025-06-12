from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import subprocess
import re

app = FastAPI()

genai.configure(api_key="Your API Key Here")

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
        model = genai.GenerativeModel("gemini-2.0-flash")

        for attempt in range(2):
            response = model.generate_content(
              f"""Generate an elegant, high-quality Manim animation in Python based on the following concept: '{prompt}'
                Constraints:
                - Only output a Python file with one class that extends Scene
                - Class name must be 'GeneratedScene'
                - Include required import: 'from manim import *'
                - imp video should not overlap with other scenes use animation and remove previous scene that no needed.
                - The scene should not go outisde the screen or frame
                - Animation must include motion, transformations, color, labels, and timing
                - Make the animation visually appealing and smooth
                - Use creative use of shapes, graphs, text, or formulas (as needed)
                - Do not include comments or explanations — only valid Python code
                - No color constants like ORANGE_B – use 'red', 'blue', or hex
                - IMPORTANT: Use Text() instead of Tex() or MathTex() for all text
                - IMPORTANT: Use simple decimal numbers instead of PI or fractions in ranges
                - IMPORTANT: Avoid LaTeX symbols - use regular text only"""
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
            ["manim", "generated_scene.py", scene_class, "-o", "output.mp4", "-qm"],
            check=True,
            text=True,
            capture_output=True,
            timeout=150

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
