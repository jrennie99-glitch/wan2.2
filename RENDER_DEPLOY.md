# Dream Studio - Render Deployment Guide
## Powered by WAN 2.2

## Overview
Dream Studio is a DreamAI-style video generation web UI powered by WAN 2.2, ready for deployment on Render.

---

## Quick Start - Render Deployment

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | Auto-set | Render automatically sets this |
| `RUNPOD_API_KEY` | Optional | Your RunPod API key |
| `RUNPOD_ENDPOINT_ID` | Optional | Your RunPod endpoint ID (e.g., `abc123xyz`) |
| `RUNPOD_ENDPOINT_URL` | Optional | Full RunPod URL (alternative to ENDPOINT_ID) |
| `PUBLIC_BASE_URL` | Optional | Your app's public URL for webhooks |

---

## Operating Modes

### Simulation Mode (Default)
- Active when `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` are NOT set
- Jobs complete after 5-10 seconds with simulated progress
- Perfect for UI testing and development
- No actual video generation occurs

### Production Mode
- Active when `RUNPOD_API_KEY` AND (`RUNPOD_ENDPOINT_ID` or `RUNPOD_ENDPOINT_URL`) are set
- Real video generation via RunPod
- Polls RunPod for job status until completion
- Returns actual video URLs from RunPod

---

## Features

### DreamAI-Style Interface
- **Left Sidebar**: Navigation (New Generation, Gallery, History, Settings)
- **Create Page**: 
  - Large prompt textarea
  - "Generate Video" button
  - Real-time status with progress bar
  - Video player with download button when complete
- **Gallery**: Browse completed videos
- **History**: View all generation jobs
- **Settings**: RunPod configuration status

### Generation Settings
| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| Duration | 4s | 1-30s | Video length |
| FPS | 24 | 8-60 | Frames per second |
| Steps | 30 | 1-100 | Diffusion steps |
| Seed | -1 | Any | Random if -1 |
| CFG Scale | 7.5 | 1-20 | Guidance strength |
| Width | 512 | 256-1024 | Video width |
| Height | 512 | 256-1024 | Video height |

---

## API Endpoints

### Health & Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/HEAD | `/` | Main create page (HTML) |
| GET/HEAD | `/health` | Health check `{"ok": true}` |
| GET | `/docs` | Swagger API documentation |

### Job Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/jobs` | Create new job |
| GET | `/api/jobs` | List all jobs |
| GET | `/api/jobs/{id}` | Get job status |
| POST | `/api/upload` | Upload reference image |

### Create Job Request
```json
POST /api/jobs
{
  "prompt": "A majestic eagle soaring through clouds",
  "negative_prompt": "blurry, low quality",
  "settings": {
    "duration": 4,
    "fps": 24,
    "steps": 30,
    "seed": -1,
    "guidance": 7.5,
    "aspect": "16:9"
  }
}
```

### Create Job Response
```json
{
  "ok": true,
  "job_id": "abc12345",
  "status": "queued"
}
```

### Get Job Status Response
```json
{
  "job_id": "abc12345",
  "status": "completed",
  "video_url": "/media/abc12345.mp4",
  "error": null,
  "progress": 100,
  "message": "Generation complete!"
}
```

---

## File Structure

```
/app/
├── app.py              # Main FastAPI application
├── requirements.txt    # Python dependencies (minimal)
├── templates/          # Jinja2 HTML templates
│   ├── base.html       # Base template with sidebar
│   ├── create.html     # Video creation page
│   ├── gallery.html    # Video gallery
│   ├── history.html    # Job history
│   ├── settings.html   # RunPod settings
│   └── job_detail.html # Job details page
├── static/
│   ├── styles.css      # CSS styles
│   └── app.js          # Frontend JavaScript
├── media/              # Generated videos
├── uploads/            # Uploaded reference images
└── jobs.json           # Job storage (auto-created)
```

---

## Troubleshooting

### TemplateNotFound Error
The app uses absolute paths for templates. Ensure you're running from the correct directory.

### 405 on HEAD /
Fixed! The `/` route accepts both GET and HEAD methods for Render health checks.

### No open ports detected
Ensure your start command uses `$PORT`:
```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

### RunPod not working
1. Check Settings page shows "Configured"
2. Verify both `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` are set
3. Ensure your RunPod endpoint is running

---

## Dependencies

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
jinja2>=3.1.2
python-multipart>=0.0.6
pydantic>=2.5.0
httpx>=0.26.0
requests>=2.31.0
```

**Note**: No torch/torchvision needed - this is a gateway service only. The heavy ML processing happens on RunPod.

---

## Security Notes

- API keys are never exposed in the frontend
- Jobs are stored in memory with optional file persistence
- No database required to run
- CORS is configured for same-origin requests

---

## License

This project uses WAN 2.2 for video generation. See LICENSE.txt for details.
