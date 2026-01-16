/**
 * WAN 2.2 Dream Studio - Frontend JavaScript
 * Handles video generation, polling, and UI updates
 */

let currentJobId = null;
let pollInterval = null;
let uploadedImageUrl = null;

// DOM Elements
function getElements() {
    return {
        promptInput: document.getElementById('promptInput'),
        negativePrompt: document.getElementById('negativePrompt'),
        generateBtn: document.getElementById('generateBtn'),
        statusBar: document.getElementById('statusBar'),
        statusLabel: document.getElementById('statusLabel'),
        statusDetail: document.getElementById('statusDetail'),
        progressBar: document.getElementById('progressBar'),
        progressFill: document.getElementById('progressFill'),
        errorMessage: document.getElementById('errorMessage'),
        videoSection: document.getElementById('videoSection'),
        videoPlayer: document.getElementById('videoPlayer'),
        downloadBtn: document.getElementById('downloadBtn'),
        viewDetailBtn: document.getElementById('viewDetailBtn'),
        imageUpload: document.getElementById('imageUpload'),
        imagePreview: document.getElementById('imagePreview'),
        // Settings
        duration: document.getElementById('duration'),
        fps: document.getElementById('fps'),
        steps: document.getElementById('steps'),
        seed: document.getElementById('seed'),
        cfgScale: document.getElementById('cfgScale'),
        width: document.getElementById('width'),
        height: document.getElementById('height'),
        aspect: document.getElementById('aspect')
    };
}

// Initialize event listeners
function initializeApp() {
    const els = getElements();
    
    // Image upload handler
    if (els.imageUpload) {
        els.imageUpload.addEventListener('change', handleImageUpload);
    }
}

// Handle image upload
async function handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.ok) {
            uploadedImageUrl = data.url;
            const preview = document.getElementById('imagePreview');
            if (preview) {
                preview.innerHTML = `<img src="${data.url}" style="max-width: 200px; border-radius: 8px; margin-top: 8px;">`;
            }
        }
    } catch (err) {
        console.error('Upload failed:', err);
    }
}

// Submit prompt for video generation
async function submitPrompt() {
    const els = getElements();
    const prompt = els.promptInput?.value?.trim();
    
    if (!prompt) {
        showError('Please enter a prompt');
        return;
    }
    
    if (els.generateBtn) {
        els.generateBtn.disabled = true;
    }
    hideError();
    showStatus('Submitting...', 'Sending your prompt to the server');
    
    // Build payload with settings
    const payload = {
        prompt: prompt,
        negative_prompt: els.negativePrompt?.value || '',
        settings: {
            duration: parseFloat(els.duration?.value) || 4,
            fps: parseInt(els.fps?.value) || 24,
            steps: parseInt(els.steps?.value) || 30,
            seed: parseInt(els.seed?.value) || -1,
            guidance: parseFloat(els.cfgScale?.value) || 7.5,
            aspect: els.aspect?.value || '16:9'
        },
        // Legacy fields
        seed: parseInt(els.seed?.value) || -1,
        steps: parseInt(els.steps?.value) || 30,
        cfg_scale: parseFloat(els.cfgScale?.value) || 7.5,
        duration_seconds: parseFloat(els.duration?.value) || 4.0,
        fps: parseInt(els.fps?.value) || 24,
        width: parseInt(els.width?.value) || 512,
        height: parseInt(els.height?.value) || 512,
        image_url: uploadedImageUrl
    };
    
    try {
        const res = await fetch('/api/jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (!res.ok || data.error) {
            throw new Error(data.error || data.detail || 'Failed to create job');
        }
        
        currentJobId = data.job_id;
        showStatus('Queued', 'Job ID: ' + data.job_id);
        showProgress(5);
        startPolling(data.job_id);
        
    } catch (err) {
        showError(err.message);
        hideStatus();
        if (els.generateBtn) {
            els.generateBtn.disabled = false;
        }
    }
}

// Poll for job status updates
function startPolling(jobId) {
    pollInterval = setInterval(async () => {
        try {
            const res = await fetch('/api/jobs/' + jobId);
            const data = await res.json();
            
            showProgress(data.progress || 0);
            showStatus(
                data.status.charAt(0).toUpperCase() + data.status.slice(1),
                data.message || ''
            );
            
            if (data.status === 'completed') {
                clearInterval(pollInterval);
                showProgress(100);
                setTimeout(() => {
                    hideStatus();
                    if (data.video_url) {
                        showVideo(data.video_url, jobId);
                    } else {
                        showError('Generation complete but no video available. RunPod not connected yet.');
                    }
                    const btn = document.getElementById('generateBtn');
                    if (btn) btn.disabled = false;
                }, 500);
                
            } else if (data.status === 'failed') {
                clearInterval(pollInterval);
                showError(data.error || 'Generation failed');
                hideStatus();
                const btn = document.getElementById('generateBtn');
                if (btn) btn.disabled = false;
            }
            
        } catch (err) {
            console.error('Poll error:', err);
        }
    }, 2000);
}

// UI Helper functions
function showStatus(label, detail) {
    const statusBar = document.getElementById('statusBar');
    const progressBar = document.getElementById('progressBar');
    const statusLabel = document.getElementById('statusLabel');
    const statusDetail = document.getElementById('statusDetail');
    
    if (statusBar) statusBar.classList.remove('hidden');
    if (progressBar) progressBar.classList.remove('hidden');
    if (statusLabel) statusLabel.textContent = label;
    if (statusDetail) statusDetail.textContent = detail;
}

function hideStatus() {
    const statusBar = document.getElementById('statusBar');
    const progressBar = document.getElementById('progressBar');
    if (statusBar) statusBar.classList.add('hidden');
    if (progressBar) progressBar.classList.add('hidden');
}

function showProgress(percent) {
    const fill = document.getElementById('progressFill');
    if (fill) fill.style.width = percent + '%';
}

function showError(message) {
    const el = document.getElementById('errorMessage');
    if (el) {
        el.textContent = message;
        el.classList.remove('hidden');
    }
}

function hideError() {
    const el = document.getElementById('errorMessage');
    if (el) el.classList.add('hidden');
}

function showVideo(url, jobId) {
    const section = document.getElementById('videoSection');
    const player = document.getElementById('videoPlayer');
    const downloadBtn = document.getElementById('downloadBtn');
    const viewDetailBtn = document.getElementById('viewDetailBtn');
    
    if (downloadBtn) downloadBtn.href = url;
    if (viewDetailBtn) viewDetailBtn.href = '/job/' + jobId;
    if (player) {
        player.src = url;
        player.play().catch(() => {}); // Ignore autoplay errors
    }
    if (section) section.classList.remove('hidden');
}

function resetForm() {
    const promptInput = document.getElementById('promptInput');
    const videoSection = document.getElementById('videoSection');
    const videoPlayer = document.getElementById('videoPlayer');
    const imagePreview = document.getElementById('imagePreview');
    
    if (promptInput) promptInput.value = '';
    if (videoSection) videoSection.classList.add('hidden');
    if (videoPlayer) {
        videoPlayer.pause();
        videoPlayer.src = '';
    }
    if (imagePreview) imagePreview.innerHTML = '';
    uploadedImageUrl = null;
    hideError();
    hideStatus();
    currentJobId = null;
    if (pollInterval) clearInterval(pollInterval);
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}
