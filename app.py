import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="WAN 2.2 Gateway",
    description="Render-ready FastAPI gateway for WAN 2.2 video generation",
    version="1.0.0"
)


class PromptRequest(BaseModel):
    """JSON request body for prompt submission."""
    prompt: str


@app.get("/", response_class=HTMLResponse)
def home():
    """Serve a simple web UI with a prompt textbox and submit button."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WAN 2.2 Gateway</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 700px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }
        h2 { color: #2c3e50; margin-bottom: 10px; }
        p { color: #666; margin-bottom: 20px; }
        textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            resize: vertical;
            min-height: 100px;
        }
        textarea:focus { outline: none; border-color: #3498db; }
        button {
            background: #3498db;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
        button:hover { background: #2980b9; }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>WAN 2.2 Gateway (Render)</h2>
        <p>This is the front-end/API gateway. Compute will run on RunPod later.</p>
        <form method="post" action="/prompt">
            <textarea name="prompt" rows="4" placeholder="Type your prompt for video generation..."></textarea>
            <br/>
            <button type="submit">Submit Prompt</button>
        </form>
    </div>
</body>
</html>
"""


@app.post("/prompt")
async def prompt_submit(prompt: str = Form(...)):
    """
    Receive prompt from HTML form (application/x-www-form-urlencoded).
    For now, echoes the prompt. Will connect to RunPod for inference later.
    """
    return JSONResponse(content={
        "ok": True,
        "prompt": prompt,
        "next": "connect to RunPod"
    })


@app.post("/prompt/json")
async def prompt_json(request: PromptRequest):
    """
    Receive prompt as JSON body: {"prompt": "..."}
    For now, echoes the prompt. Will connect to RunPod for inference later.
    """
    return JSONResponse(content={
        "ok": True,
        "prompt": request.prompt,
        "next": "connect to RunPod"
    })


@app.get("/health")
def health():
    """Health check endpoint for Render."""
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)