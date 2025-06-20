from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import subprocess
import re


app = FastAPI()



# Use API key from environment variable
genai.configure(api_key="AIzaSyAnZmCZkZ6Kuq9aRHhKkcLlu4jG7nd4unA")


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
                f"""Generate a clean, high-quality Manim animation in Python based on the following concept: '{prompt}'
                Constraints:
                - Output only a single Python file with one class that extends Scene
                - Use good colors for visibility and aesthetics
                - Class name must be 'GeneratedScene'
                - Use: 'from manim import *' as the only import
                - Import 'math' and 'random' explicitly if needed
                - Do not use any other libraries
                - Use only documented Manim methods and attributes — no internal APIs or renderer properties
                - Do not use any attribute that is not explicitly assigned — no .index(), .creation_order, or similar
                - When assigning indices to Mobjects, use enumerate() or attach a custom .my_index = i property manually
                - Never use VGroup.submobjects.index() or any index() call on Mobjects
                - Only use 3D vectors like [x, y, 0] for all positioning, moving, or transformations
                - Do not use LaTeX — use Text(), not Tex() or MathTex()
                - Use only valid color strings like 'red', 'blue', 'green', or hex codes like '#FF5733' — avoid constants like ORANGE_B
                - Never pass None to self.play() — every animation must be a valid Animation object
                - Avoid referencing self.renderer, self.camera, or any internal engine state
                - Never use zero-length or empty lists in transformations (e.g., shift([]) or move_to([])) — use full 3D vectors
                - If using randomness, import and use random properly with fallback defaults to ensure stability
                - If any helper method like get_ring_animation() is used, define it fully within the same class above its usage
                - If animating a group, use AnimationGroup with valid lag_ratio and only on valid, pre-created Mobjects
                - Never assume a Mobject can be accessed inside an animation update function unless it was explicitly created and indexed properly
                - Avoid overly long animations — total duration must be under 15 seconds
                - Total frame count must not exceed 450 (assume 30fps)
                - Use run_time wisely to distribute timing across scenes
                - Use wait() only when needed, never longer than 0.5s unless inside total frame budget
                - Keep visuals on screen — nothing should move off-frame
                - Output must be valid, executable Python code — no comments or explanations
                - Prioritize stability over complexity — final output must run without errors, even if visually simple
"""

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
    
@app.get("/health")
def health_check():    
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        res = model.generate_content("hi gemini , what is the current time?")
        return {"status": "ok", "message": "Service is healthy", "time": res.text}
    except Exception as e:
        return {"status": "error", "message": "Service is unhealthy", "details": str(e)}

