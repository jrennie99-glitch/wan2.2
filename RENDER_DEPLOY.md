# WAN 2.2 Dream Studio - Render Deployment Guide

## Overview
This is a DreamAI-style video generation web UI powered by WAN 2.2, ready for deployment on Render.

## Render Deployment

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | Auto-set | Render automatically sets this |
| `RUNPOD_API_KEY` | Optional | Your RunPod API key |
| `RUNPOD_ENDPOINT_ID` | Optional | Your RunPod endpoint ID (e.g., `abc123xyz`) |
| `RUNPOD_ENDPOINT_URL` | Optional | Full RunPod URL (alternative to ENDPOINT_ID) |
| `PUBLIC_BASE_URL` | Optional | Your app's public URL for webhooks |

### Modes

**Simulation Mode (Default)**
- When `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` are NOT set
- Jobs complete after 5-10 seconds with simulated progress
- Perfect for UI testing and development

**Production Mode**
- When `RUNPOD_API_KEY` AND (`RUNPOD_ENDPOINT_ID` or `RUNPOD_ENDPOINT_URL`) are set
- Real video generation via RunPod
- Polls RunPod for job status until completion

## Features

### DreamAI-Style Interface
- **Left Sidebar**: Navigation (New Generation, Gallery, History, Settings)
- **Main Area**: 
  - Large prompt textarea
  - "Generate Video" button
  - Real-time status with progress bar
  - Video player with download button

### Settings
- Negative Prompt
- Seed (-1 = random)
- Steps (default: 30)
- CFG Scale (default: 7.5)
- Duration (default: 4 seconds)
- FPS (default: 24)
- Width/Height (default: 512x512)
- Reference Image upload

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/HEAD | `/` | Main create page |
| GET/HEAD | `/health` | Health check for Render |
| GET | `/gallery` | View completed videos |
| GET | `/history` | All generation history |
| GET | `/settings` | RunPod configuration |
| GET | `/job/{id}` | Job details page |
| POST | `/api/jobs` | Create new job |
| GET | `/api/jobs` | List all jobs |
| GET | `/api/jobs/{id}` | Get job status |
| POST | `/api/upload` | Upload reference image |
| POST | `/api/test-connection` | Test RunPod connection |

### API Request Format

```json
POST /api/jobs
{
  "prompt": "A majestic eagle soaring through clouds",
  "negative_prompt": "blurry, low quality",
  "settings": {
    "duration": 4,
    "fps": 24,
    "steps": 30,
    "seed": 123,
    "guidance": 7.5,
    "aspect": "16:9"
  }
}
```

### API Response Format

```json
{
  "ok": true,
  "job_id": "abc12345",
  "status": "queued"
}
```

### Job Status Response

```json
GET /api/jobs/{job_id}
{
  "job_id": "abc12345",
  "status": "queued|running|completed|failed",
  "video_url": null | "/path/to/video.mp4",
  "error": null | "Error message",
  "progress": 0-100,
  "message": "Status message"
}
```

## File Structure

```
/app/
├── app.py              # Main FastAPI application
├── requirements.txt    # Python dependencies
├── templates/
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
└── uploads/            # Uploaded images
```

## Troubleshooting

### TemplateNotFound Error
The app uses absolute paths for templates. Ensure you're running from the `/app` directory.

### 405 on HEAD /
Fixed! The `/` route now accepts both GET and HEAD methods for Render health checks.

### No open ports detected
Ensure your start command uses `$PORT` (without quotes):
```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

### RunPod not working
1. Check Settings page shows "Configured"
2. Click "Test Connection" to verify
3. Ensure both `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` are set

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

No torch/torchvision needed - this is a gateway service only.
