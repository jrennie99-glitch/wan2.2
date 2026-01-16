import os
import uuid
import json
import asyncio
import random
import shutil
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, HTTPException, Form, UploadFile, File, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# =============================================================================
# Configuration
# =============================================================================
# Get the base directory where app.py is located
BASE_DIR = Path(__file__).resolve().parent

RUNPOD_ENDPOINT_URL = os.environ.get("RUNPOD_ENDPOINT_URL", "")
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "")
JOBS_FILE = BASE_DIR / "jobs.json"
MEDIA_DIR = BASE_DIR / "media"
UPLOADS_DIR = BASE_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Build RunPod URL from endpoint ID if not directly provided
if not RUNPOD_ENDPOINT_URL and RUNPOD_ENDPOINT_ID:
    RUNPOD_ENDPOINT_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"

# Check if RunPod is configured
RUNPOD_CONFIGURED = bool(RUNPOD_ENDPOINT_URL and RUNPOD_API_KEY)

# Ensure directories exist
MEDIA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# =============================================================================
# Job Storage (In-memory with optional file persistence)
# =============================================================================
jobs_store: Dict[str, Dict[str, Any]] = {}

def load_jobs() -> Dict[str, Dict[str, Any]]:
    global jobs_store
    if not jobs_store and JOBS_FILE.exists():
        try:
            with open(JOBS_FILE, "r") as f:
                jobs_store = json.load(f)
        except:
            jobs_store = {}
    return jobs_store

def save_jobs(jobs: Dict[str, Dict[str, Any]]):
    global jobs_store
    jobs_store = jobs
    try:
        with open(JOBS_FILE, "w") as f:
            json.dump(jobs, f, indent=2)
    except:
        pass  # File persistence is optional

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    jobs = load_jobs()
    return jobs.get(job_id)

def save_job(job_id: str, job_data: Dict[str, Any]):
    jobs = load_jobs()
    jobs[job_id] = job_data
    save_jobs(jobs)

def get_all_jobs() -> List[Dict[str, Any]]:
    jobs = load_jobs()
    job_list = list(jobs.values())
    job_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return job_list

def get_recent_jobs(limit: int = 50) -> List[Dict[str, Any]]:
    return get_all_jobs()[:limit]

# =============================================================================
# Lifespan
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_jobs()
    yield

# =============================================================================
# FastAPI App
# =============================================================================
app = FastAPI(
    title="WAN 2.2 Dream Studio",
    description="AI Video Generation Platform powered by WAN 2.2",
    version="3.0.0",
    lifespan=lifespan
)

# Mount static files, media, and templates using absolute paths
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# =============================================================================
# Pydantic Models
# =============================================================================
class JobCreateRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = ""
    settings: Optional[Dict[str, Any]] = None
    # Legacy fields for backward compatibility
    seed: Optional[int] = -1
    steps: Optional[int] = 30
    cfg_scale: Optional[float] = 7.5
    duration_seconds: Optional[float] = 4.0
    fps: Optional[int] = 24
    width: Optional[int] = 512
    height: Optional[int] = 512
    image_url: Optional[str] = None

class SettingsUpdateRequest(BaseModel):
    runpod_endpoint_url: Optional[str] = None
    runpod_api_key: Optional[str] = None

# =============================================================================
# Simulated Generation (when RunPod is not configured)
# =============================================================================
async def simulate_generation(job_id: str):
    """Simulate video generation with a delay (demo mode)"""
    job = get_job(job_id)
    if not job:
        return
    
    try:
        job["status"] = "running"
        job["message"] = "Initializing generation (simulated mode)..."
        job["progress"] = 10
        save_job(job_id, job)
        
        # Simulate 5-10 second processing time
        total_wait = random.uniform(5, 10)
        steps = 10
        for i in range(steps):
            await asyncio.sleep(total_wait / steps)
            progress = 10 + int((i + 1) / steps * 85)
            job["progress"] = progress
            job["message"] = f"Generating video... ({progress}%)"
            save_job(job_id, job)
        
        # Check if sample video exists
        sample_video = STATIC_DIR / "sample.mp4"
        if sample_video.exists():
            job["status"] = "completed"
            job["video_url"] = "/static/sample.mp4"
            job["message"] = "Generation complete (demo mode)"
            job["progress"] = 100
        else:
            job["status"] = "completed"
            job["video_url"] = None
            job["message"] = "Generation complete - RunPod not connected yet. Configure RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID for real video generation."
            job["progress"] = 100
        
        job["completed_at"] = datetime.utcnow().isoformat() + "Z"
        save_job(job_id, job)
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = f"Simulation error: {str(e)}"
        job["completed_at"] = datetime.utcnow().isoformat() + "Z"
        save_job(job_id, job)

# =============================================================================
# RunPod Integration
# =============================================================================
async def process_job_runpod(job_id: str):
    job = get_job(job_id)
    if not job:
        return
    
    if not RUNPOD_CONFIGURED:
        # Use simulated mode
        await simulate_generation(job_id)
        return
    
    try:
        job["status"] = "running"
        job["message"] = "Connecting to RunPod..."
        job["progress"] = 5
        save_job(job_id, job)
        
        headers = {"Content-Type": "application/json"}
        if RUNPOD_API_KEY:
            headers["Authorization"] = f"Bearer {RUNPOD_API_KEY}"
        
        payload = {
            "input": {
                "prompt": job.get("prompt", ""),
                "negative_prompt": job.get("negative_prompt", ""),
                "seed": job.get("seed", -1),
                "steps": job.get("steps", 30),
                "cfg_scale": job.get("cfg_scale", 7.5),
                "duration_seconds": job.get("duration_seconds", 4.0),
                "fps": job.get("fps", 24),
                "width": job.get("width", 512),
                "height": job.get("height", 512),
                "image_url": job.get("image_url"),
                "job_id": job_id,
                "webhook_url": f"{PUBLIC_BASE_URL}/api/webhook/{job_id}" if PUBLIC_BASE_URL else None
            }
        }
        
        async with httpx.AsyncClient(timeout=600.0) as client:
            job["message"] = "Starting generation on RunPod..."
            job["progress"] = 10
            save_job(job_id, job)
            
            response = await client.post(
                f"{RUNPOD_ENDPOINT_URL}/run",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            runpod_data = response.json()
            
            runpod_job_id = runpod_data.get("id")
            job["runpod_job_id"] = runpod_job_id
            job["message"] = f"RunPod job: {runpod_job_id}"
            job["progress"] = 15
            save_job(job_id, job)
            
            max_polls = 600
            poll_count = 0
            
            while poll_count < max_polls:
                await asyncio.sleep(2)
                poll_count += 1
                
                status_response = await client.get(
                    f"{RUNPOD_ENDPOINT_URL}/status/{runpod_job_id}",
                    headers=headers
                )
                status_data = status_response.json()
                runpod_status = status_data.get("status", "").upper()
                
                if runpod_status == "COMPLETED":
                    output = status_data.get("output", {})
                    video_url = output.get("video_url") or output.get("url") or output.get("result")
                    
                    job["status"] = "completed"
                    job["video_url"] = video_url
                    job["output"] = output
                    job["message"] = "Generation complete!"
                    job["progress"] = 100
                    job["completed_at"] = datetime.utcnow().isoformat() + "Z"
                    save_job(job_id, job)
                    return
                    
                elif runpod_status == "FAILED":
                    error_msg = status_data.get("error", "RunPod job failed")
                    job["status"] = "failed"
                    job["error"] = error_msg
                    job["completed_at"] = datetime.utcnow().isoformat() + "Z"
                    save_job(job_id, job)
                    return
                    
                elif runpod_status == "IN_PROGRESS":
                    progress = min(15 + poll_count // 3, 95)
                    job["message"] = f"Generating video... ({runpod_status})"
                    job["progress"] = progress
                    save_job(job_id, job)
                    
                else:
                    job["message"] = f"Status: {runpod_status}"
                    save_job(job_id, job)
            
            job["status"] = "failed"
            job["error"] = "Job timed out after 20 minutes"
            job["completed_at"] = datetime.utcnow().isoformat() + "Z"
            save_job(job_id, job)
            
    except httpx.HTTPStatusError as e:
        job["status"] = "failed"
        job["error"] = f"RunPod API error: {e.response.status_code}"
        job["completed_at"] = datetime.utcnow().isoformat() + "Z"
        save_job(job_id, job)
    except Exception as e:
        job["status"] = "failed"
        job["error"] = f"Error: {str(e)}"
        job["completed_at"] = datetime.utcnow().isoformat() + "Z"
        save_job(job_id, job)

# =============================================================================
# Page Routes - Support both GET and HEAD for Render health checks
# =============================================================================
@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def page_create(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)
    return templates.TemplateResponse("create.html", {
        "request": request,
        "page": "create",
        "runpod_configured": RUNPOD_CONFIGURED
    })

@app.get("/gallery", response_class=HTMLResponse)
async def page_gallery(request: Request):
    jobs = [j for j in get_recent_jobs(100) if j.get("status") == "completed" and j.get("video_url")]
    return templates.TemplateResponse("gallery.html", {
        "request": request,
        "page": "gallery",
        "jobs": jobs
    })

@app.get("/history", response_class=HTMLResponse)
async def page_history(request: Request):
    jobs = get_recent_jobs(100)
    return templates.TemplateResponse("history.html", {
        "request": request,
        "page": "history",
        "jobs": jobs
    })

@app.get("/settings", response_class=HTMLResponse)
async def page_settings(request: Request):
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "page": "settings",
        "runpod_configured": RUNPOD_CONFIGURED,
        "runpod_endpoint": RUNPOD_ENDPOINT_URL[:50] + "..." if len(RUNPOD_ENDPOINT_URL) > 50 else RUNPOD_ENDPOINT_URL,
        "has_api_key": bool(RUNPOD_API_KEY)
    })

@app.get("/job/{job_id}", response_class=HTMLResponse)
async def page_job_detail(request: Request, job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return templates.TemplateResponse("job_detail.html", {
        "request": request,
        "page": "gallery",
        "job": job
    })

# =============================================================================
# API Routes
# =============================================================================
@app.post("/api/jobs")
async def api_create_job(request: JobCreateRequest, background_tasks: BackgroundTasks):
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    # Parse settings from new format or legacy fields
    settings = request.settings or {}
    
    job_id = str(uuid.uuid4())[:8]
    job_data = {
        "job_id": job_id,
        "prompt": prompt,
        "negative_prompt": request.negative_prompt or settings.get("negative_prompt", ""),
        "seed": settings.get("seed", request.seed) if settings.get("seed") else request.seed if request.seed and request.seed > 0 else -1,
        "steps": settings.get("steps", request.steps) or 30,
        "cfg_scale": settings.get("guidance", request.cfg_scale) or 7.5,
        "duration_seconds": settings.get("duration", request.duration_seconds) or 4.0,
        "fps": settings.get("fps", request.fps) or 24,
        "width": request.width or 512,
        "height": request.height or 512,
        "aspect": settings.get("aspect", "16:9"),
        "image_url": request.image_url,
        "status": "queued",
        "progress": 0,
        "message": "Job queued",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "completed_at": None,
        "video_url": None,
        "error": None,
        "output": None
    }
    save_job(job_id, job_data)
    
    background_tasks.add_task(process_job_runpod, job_id)
    
    return JSONResponse(content={"ok": True, "job_id": job_id, "status": "queued"})

@app.get("/api/jobs")
async def api_list_jobs(limit: int = 50, status: Optional[str] = None):
    jobs = get_recent_jobs(limit)
    if status:
        jobs = [j for j in jobs if j.get("status") == status]
    return JSONResponse(content={"ok": True, "jobs": jobs, "count": len(jobs)})

@app.get("/api/jobs/{job_id}")
async def api_get_job(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(content={
        "job_id": job.get("job_id"),
        "status": job.get("status", "unknown"),
        "video_url": job.get("video_url"),
        "error": job.get("error"),
        "progress": job.get("progress", 0),
        "message": job.get("message", "")
    })

@app.post("/api/upload")
async def api_upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    file_id = str(uuid.uuid4())[:8]
    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    filename = f"{file_id}.{ext}"
    filepath = UPLOADS_DIR / filename
    
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    return JSONResponse(content={
        "ok": True,
        "filename": filename,
        "url": f"/uploads/{filename}"
    })

@app.post("/api/webhook/{job_id}")
async def api_webhook(job_id: str, request: Request):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        data = await request.json()
        status = data.get("status", "").upper()
        
        if status == "COMPLETED":
            output = data.get("output", {})
            video_url = output.get("video_url") or output.get("url")
            job["status"] = "completed"
            job["video_url"] = video_url
            job["output"] = output
            job["progress"] = 100
            job["message"] = "Complete!"
            job["completed_at"] = datetime.utcnow().isoformat() + "Z"
        elif status == "FAILED":
            job["status"] = "failed"
            job["error"] = data.get("error", "Job failed")
            job["completed_at"] = datetime.utcnow().isoformat() + "Z"
        else:
            job["message"] = f"Webhook: {status}"
        
        save_job(job_id, job)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/api/test-connection")
async def api_test_connection():
    if not RUNPOD_ENDPOINT_URL:
        return JSONResponse(content={"ok": False, "error": "RUNPOD_ENDPOINT_URL not configured"})
    
    try:
        headers = {}
        if RUNPOD_API_KEY:
            headers["Authorization"] = f"Bearer {RUNPOD_API_KEY}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{RUNPOD_ENDPOINT_URL}/health", headers=headers)
            if response.status_code == 200:
                return JSONResponse(content={"ok": True, "message": "Connection successful!"})
            else:
                return JSONResponse(content={"ok": False, "error": f"Status {response.status_code}"})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)})

# =============================================================================
# Health Check Routes
# =============================================================================
@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {
        "ok": True,
        "runpod_configured": RUNPOD_CONFIGURED,
        "mode": "production" if RUNPOD_CONFIGURED else "simulation"
    }

# =============================================================================
# Legacy endpoints for backward compatibility
# =============================================================================
@app.post("/jobs")
async def legacy_create_job(request: JobCreateRequest, background_tasks: BackgroundTasks):
    return await api_create_job(request, background_tasks)

@app.get("/jobs/{job_id}")
async def legacy_get_job(job_id: str):
    return await api_get_job(job_id)

# =============================================================================
# Main entry point
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
