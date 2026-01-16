import React, { useState, useEffect, useCallback } from 'react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

function App() {
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [settings, setSettings] = useState({
    duration: 4,
    fps: 24,
    steps: 30,
    seed: -1,
    cfgScale: 7.5,
    width: 512,
    height: 512
  });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [currentJob, setCurrentJob] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [currentPage, setCurrentPage] = useState('create');
  const [runpodConfigured, setRunpodConfigured] = useState(false);

  // Check health on load
  useEffect(() => {
    fetch(`${BACKEND_URL}/health`)
      .then(res => res.json())
      .then(data => setRunpodConfigured(data.runpod_configured))
      .catch(() => setRunpodConfigured(false));
  }, []);

  // Load jobs for history
  useEffect(() => {
    if (currentPage === 'history' || currentPage === 'gallery') {
      fetch(`${BACKEND_URL}/api/jobs`)
        .then(res => res.json())
        .then(data => setJobs(data.jobs || []))
        .catch(() => setJobs([]));
    }
  }, [currentPage]);

  // Poll for job status
  useEffect(() => {
    if (!currentJob || currentJob.status === 'completed' || currentJob.status === 'failed') {
      return;
    }
    const interval = setInterval(() => {
      fetch(`${BACKEND_URL}/api/jobs/${currentJob.job_id}`)
        .then(res => res.json())
        .then(data => {
          setCurrentJob(data);
          if (data.status === 'completed' || data.status === 'failed') {
            setIsGenerating(false);
          }
        })
        .catch(err => console.error('Poll error:', err));
    }, 2000);
    return () => clearInterval(interval);
  }, [currentJob]);

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError('Please enter a prompt');
      return;
    }
    setError(null);
    setIsGenerating(true);
    setCurrentJob(null);

    try {
      const response = await fetch(`${BACKEND_URL}/api/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          negative_prompt: negativePrompt,
          settings: {
            duration: settings.duration,
            fps: settings.fps,
            steps: settings.steps,
            seed: settings.seed,
            guidance: settings.cfgScale
          },
          seed: settings.seed,
          steps: settings.steps,
          cfg_scale: settings.cfgScale,
          duration_seconds: settings.duration,
          fps: settings.fps,
          width: settings.width,
          height: settings.height
        })
      });
      const data = await response.json();
      if (data.ok) {
        setCurrentJob({ job_id: data.job_id, status: 'queued', progress: 0, message: 'Job queued' });
      } else {
        setError(data.error || data.detail || 'Failed to create job');
        setIsGenerating(false);
      }
    } catch (err) {
      setError(err.message);
      setIsGenerating(false);
    }
  };

  const resetForm = () => {
    setPrompt('');
    setCurrentJob(null);
    setError(null);
    setIsGenerating(false);
  };

  const renderSidebar = () => (
    <nav className="sidebar">
      <div className="sidebar-logo">
        <h1>✨ Dream Studio</h1>
        <p>Powered by WAN 2.2</p>
      </div>
      <button 
        className={`nav-item ${currentPage === 'create' ? 'active' : ''}`}
        onClick={() => setCurrentPage('create')}
      >
        <span className="icon">🎬</span> New Generation
      </button>
      <button 
        className={`nav-item ${currentPage === 'gallery' ? 'active' : ''}`}
        onClick={() => setCurrentPage('gallery')}
      >
        <span className="icon">🖼️</span> Gallery
      </button>
      <button 
        className={`nav-item ${currentPage === 'history' ? 'active' : ''}`}
        onClick={() => setCurrentPage('history')}
      >
        <span className="icon">📜</span> History
      </button>
      <button 
        className={`nav-item ${currentPage === 'settings' ? 'active' : ''}`}
        onClick={() => setCurrentPage('settings')}
      >
        <span className="icon">⚙️</span> Settings
      </button>
    </nav>
  );

  const renderCreatePage = () => (
    <div className="main-content">
      <h2>🎬 Create New Video</h2>
      <p className="subtitle">Transform your ideas into stunning AI-generated videos</p>

      {!runpodConfigured && (
        <div className="warning-banner">
          ⚠️ Compute not connected yet. Go to <button onClick={() => setCurrentPage('settings')} className="link-btn">Settings</button> to configure RunPod.
        </div>
      )}

      <div className="card">
        <label className="label">Prompt</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe your dream video... e.g., 'A majestic eagle soaring through golden sunset clouds, cinematic 4K'"
          className="prompt-input"
          disabled={isGenerating}
        />

        <details open={showAdvanced} onToggle={(e) => setShowAdvanced(e.target.open)}>
          <summary className="advanced-toggle">Advanced Options</summary>
          <div className="settings-grid">
            <div className="setting-item">
              <label>Negative Prompt</label>
              <input
                type="text"
                value={negativePrompt}
                onChange={(e) => setNegativePrompt(e.target.value)}
                placeholder="Things to avoid..."
              />
            </div>
            <div className="setting-item">
              <label>Seed (-1 = random)</label>
              <input
                type="number"
                value={settings.seed}
                onChange={(e) => setSettings({...settings, seed: parseInt(e.target.value) || -1})}
              />
            </div>
            <div className="setting-item">
              <label>Steps</label>
              <input
                type="number"
                value={settings.steps}
                onChange={(e) => setSettings({...settings, steps: parseInt(e.target.value) || 30})}
                min="1" max="100"
              />
            </div>
            <div className="setting-item">
              <label>CFG Scale</label>
              <input
                type="number"
                value={settings.cfgScale}
                onChange={(e) => setSettings({...settings, cfgScale: parseFloat(e.target.value) || 7.5})}
                step="0.5" min="1" max="20"
              />
            </div>
            <div className="setting-item">
              <label>Duration (seconds)</label>
              <input
                type="number"
                value={settings.duration}
                onChange={(e) => setSettings({...settings, duration: parseFloat(e.target.value) || 4})}
                step="0.5" min="1" max="30"
              />
            </div>
            <div className="setting-item">
              <label>FPS</label>
              <input
                type="number"
                value={settings.fps}
                onChange={(e) => setSettings({...settings, fps: parseInt(e.target.value) || 24})}
                min="8" max="60"
              />
            </div>
            <div className="setting-item">
              <label>Width</label>
              <input
                type="number"
                value={settings.width}
                onChange={(e) => setSettings({...settings, width: parseInt(e.target.value) || 512})}
                step="64" min="256" max="1024"
              />
            </div>
            <div className="setting-item">
              <label>Height</label>
              <input
                type="number"
                value={settings.height}
                onChange={(e) => setSettings({...settings, height: parseInt(e.target.value) || 512})}
                step="64" min="256" max="1024"
              />
            </div>
          </div>
        </details>

        <div className="actions">
          <button 
            className="btn primary" 
            onClick={handleGenerate}
            disabled={isGenerating}
          >
            🚀 Generate Video
          </button>
        </div>

        {currentJob && (
          <div className="status-bar">
            <div className="spinner"></div>
            <div className="status-text">
              <div className="status-label">{currentJob.status?.charAt(0).toUpperCase() + currentJob.status?.slice(1)}</div>
              <div className="status-detail">{currentJob.message}</div>
            </div>
          </div>
        )}

        {currentJob && (
          <div className="progress-bar">
            <div className="progress-fill" style={{width: `${currentJob.progress || 0}%`}}></div>
          </div>
        )}

        {error && <div className="error-message">{error}</div>}
      </div>

      {currentJob?.status === 'completed' && (
        <div className="card video-section">
          {currentJob.video_url ? (
            <>
              <video controls className="video-player" src={currentJob.video_url}></video>
              <div className="video-actions">
                <a href={currentJob.video_url} download className="btn primary">⬇️ Download</a>
                <button className="btn secondary" onClick={resetForm}>🔄 New Generation</button>
              </div>
            </>
          ) : (
            <div className="warning-banner">
              ✅ Generation complete! {currentJob.message}
              <div style={{marginTop: '16px'}}>
                <button className="btn primary" onClick={resetForm}>🔄 New Generation</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderGalleryPage = () => (
    <div className="main-content">
      <h2>🖼️ Gallery</h2>
      <p className="subtitle">Browse your completed video generations</p>
      {jobs.filter(j => j.status === 'completed' && j.video_url).length > 0 ? (
        <div className="gallery-grid">
          {jobs.filter(j => j.status === 'completed' && j.video_url).map(job => (
            <div key={job.job_id} className="gallery-item card">
              <video src={job.video_url} className="gallery-video" muted loop 
                onMouseOver={e => e.target.play()} 
                onMouseOut={e => {e.target.pause(); e.target.currentTime = 0;}}
              />
              <div className="gallery-info">
                <p className="gallery-prompt">{job.prompt?.slice(0, 60)}...</p>
                <span className="gallery-date">{job.created_at?.slice(0, 10)}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card empty-state">
          <p>No completed videos yet.</p>
          <button className="btn primary" onClick={() => setCurrentPage('create')}>Create Your First Video</button>
        </div>
      )}
    </div>
  );

  const renderHistoryPage = () => (
    <div className="main-content">
      <h2>📜 Generation History</h2>
      <p className="subtitle">View all your video generation jobs</p>
      {jobs.length > 0 ? (
        <div className="card history-list">
          {jobs.map(job => (
            <div key={job.job_id} className="history-item">
              <div className="history-info">
                <div className="history-prompt">{job.prompt?.slice(0, 60)}...</div>
                <div className="history-time">{job.created_at?.replace('T', ' ').slice(0, 19)}</div>
              </div>
              <span className={`status-badge ${job.status}`}>{job.status}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="card empty-state">
          <p>No generation history yet.</p>
          <button className="btn primary" onClick={() => setCurrentPage('create')}>Create Your First Video</button>
        </div>
      )}
    </div>
  );

  const renderSettingsPage = () => (
    <div className="main-content">
      <h2>⚙️ Settings</h2>
      <p className="subtitle">Configure your RunPod connection</p>
      <div className="card">
        <h3>RunPod Configuration</h3>
        <p className="setting-desc">Set these environment variables on Render to connect to RunPod compute.</p>
        
        <div className="setting-display">
          <label>RUNPOD_ENDPOINT_URL</label>
          <div className="setting-value">
            {runpodConfigured ? (
              <span className="status-configured">✓ Configured</span>
            ) : (
              <span className="status-not-configured">✗ Not configured</span>
            )}
          </div>
        </div>
        
        <div className="setting-display">
          <label>RUNPOD_API_KEY</label>
          <div className="setting-value">
            {runpodConfigured ? (
              <span className="status-configured">✓ Configured</span>
            ) : (
              <span className="status-optional">○ Not set (optional for public endpoints)</span>
            )}
          </div>
        </div>
      </div>
      
      <div className="card" style={{marginTop: '24px'}}>
        <h3>Environment Variables</h3>
        <p className="setting-desc">Add these to your Render dashboard → Environment:</p>
        <pre className="code-block">
{`RUNPOD_ENDPOINT_URL=https://api.runpod.ai/v2/your-endpoint-id
RUNPOD_API_KEY=your-api-key-here
PUBLIC_BASE_URL=https://your-app.onrender.com`}
        </pre>
      </div>
    </div>
  );

  return (
    <div className="app-shell">
      {renderSidebar()}
      {currentPage === 'create' && renderCreatePage()}
      {currentPage === 'gallery' && renderGalleryPage()}
      {currentPage === 'history' && renderHistoryPage()}
      {currentPage === 'settings' && renderSettingsPage()}
    </div>
  );
}

export default App;
