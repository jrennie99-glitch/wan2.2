import os
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# =============================================================================
# Configuration
# =============================================================================
RUNPOD_ENDPOINT_URL = os.environ.get("RUNPOD_ENDPOINT_URL", "")
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "")

# =============================================================================
# Job Storage (In-Memory + Optional Redis)
# =============================================================================
jobs_store: Dict[str, Dict[str, Any]] = {}
redis_client = None

def init_redis():
    global redis_client
    if REDIS_URL:
        try:
            import redis
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            redis_client.ping()
            print(f"Redis connected: {REDIS_URL[:30]}...")
        except Exception as e:
            print(f"Redis connection failed: {e}. Using in-memory storage.")
            redis_client = None


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    if redis_client:
        try:
            import json
            data = redis_client.get(f"job:{job_id}")
            return json.loads(data) if data else None
        except:
            pass
    return jobs_store.get(job_id)

def save_job(job_id: str, job_data: Dict[str, Any]):
    jobs_store[job_id] = job_data
    if redis_client:
        try:
            import json
            redis_client.setex(f"job:{job_id}", 86400, json.dumps(job_data))
        except:
            pass


def get_recent_jobs(limit: int = 10) -> list:
    jobs = list(jobs_store.values())
    jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jobs[:limit]

# =============================================================================
# Lifespan
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_redis()
    yield

# =============================================================================
# FastAPI App
# =============================================================================
app = FastAPI(
    title="WAN 2.2 Dream Generator",
    description="Render-ready FastAPI gateway for WAN 2.2 video generation",
    version="2.0.0",
    lifespan=lifespan
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# =============================================================================
# Pydantic Models
# =============================================================================
class PromptRequest(BaseModel):
    prompt: str

# =============================================================================
# RunPod Integration
# =============================================================================
async def call_runpod(job_id: str, prompt: str):
    job = get_job(job_id)
    if not job:
        return
    
    if not RUNPOD_ENDPOINT_URL:
        job["status"] = "failed"
        job["error"] = "RunPod not configured. Set RUNPOD_ENDPOINT_URL environment variable."
        save_job(job_id, job)
        return
    
    try:
        job["status"] = "running"
        job["message"] = "Sending request to RunPod..."
        save_job(job_id, job)
        
        headers = {"Content-Type": "application/json"}
        if RUNPOD_API_KEY:
            headers["Authorization"] = f"Bearer {RUNPOD_API_KEY}"
        
        payload = {
            "input": {
                "prompt": prompt,
                "job_id": job_id,
                "webhook_url": f"{PUBLIC_BASE_URL}/webhook/{job_id}" if PUBLIC_BASE_URL else None
            }
        }
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{RUNPOD_ENDPOINT_URL}/run",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            runpod_data = response.json()
            
            runpod_job_id = runpod_data.get("id")
            job["runpod_job_id"] = runpod_job_id
            job["message"] = f"RunPod job started: {runpod_job_id}"
            save_job(job_id, job)
            
            max_polls = 300
            poll_count = 0
            
            while poll_count < max_polls:
                await asyncio.sleep(2)
                poll_count += 1
                
                status_response = await client.get(
                    f"{RUNPOD_ENDPOINT_URL}/status/{runpod_job_id}",
                    headers=headers
                )
                status_data = status_response.json()
                runpod_status = status_data.get("status", "").lower()
                
                if runpod_status == "completed":
                    output = status_data.get("output", {})
                    video_url = output.get("video_url") or output.get("url")
                    job["status"] = "completed"
                    job["video_url"] = video_url
                    job["message"] = "Video generation complete!"
                    save_job(job_id, job)
                    return
                
                elif runpod_status == "failed":
                    error_msg = status_data.get("error", "RunPod job failed")
                    job["status"] = "failed"
                    job["error"] = error_msg
                    save_job(job_id, job)
                    return
                
                else:
                    job["message"] = f"RunPod status: {runpod_status}"
                    save_job(job_id, job)
            
            job["status"] = "failed"
            job["error"] = "Job timed out after 10 minutes"
            save_job(job_id, job)
            
    except httpx.HTTPStatusError as e:
        job["status"] = "failed"
        job["error"] = f"RunPod API error: {e.response.status_code}"
        save_job(job_id, job)
    except Exception as e:
        job["status"] = "failed"
        job["error"] = f"Error: {str(e)}"
        save_job(job_id, job)

# =============================================================================
# Routes
# =============================================================================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    runpod_configured = bool(RUNPOD_ENDPOINT_URL)
    recent_jobs = get_recent_jobs(10)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "runpod_configured": runpod_configured,
        "recent_jobs": recent_jobs
    })

@app.post("/jobs")
async def create_job(request: PromptRequest):
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    job_id = str(uuid.uuid4())[:8]
    job_data = {
        "job_id": job_id,
        "prompt": prompt,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "video_url": None,
        "error": None,
        "message": "Job queued for processing"
    }
    save_job(job_id, job_data)
    asyncio.create_task(call_runpod(job_id, prompt))
    
    return JSONResponse(content={
        "ok": True,
        "job_id": job_id,
        "status": "queued",
        "message": "Job created successfully"
    })

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(content=job)

@app.post("/webhook/{job_id}")
async def runpod_webhook(job_id: str, request: Request):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        data = await request.json()
        status = data.get("status", "").lower()
        
        if status == "completed":
            output = data.get("output", {})
            video_url = output.get("video_url") or output.get("url")
            job["status"] = "completed"
            job["video_url"] = video_url
            job["message"] = "Video generation complete!"
        elif status == "failed":
            job["status"] = "failed"
            job["error"] = data.get("error", "Job failed")
        else:
            job["message"] = f"Webhook update: {status}"
        
        save_job(job_id, job)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/health")
def health():
    return {
        "ok": True,
        "runpod_configured": bool(RUNPOD_ENDPOINT_URL),
        "redis_configured": bool(redis_client)
    }

@app.post("/prompt")
async def prompt_submit_legacy(prompt: str = Form(...)):
    req = PromptRequest(prompt=prompt)
    return await create_job(req)

@app.post("/prompt/json")
async def prompt_json_legacy(request: PromptRequest):
    return await create_job(request)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)