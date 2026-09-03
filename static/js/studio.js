/**
 * Aura High-Performance Customizer Studio Engine
 * Handles interactive 2D canvas, drag-and-drop file upload, realtime transformation,
 * and Celery asynchronous rendering job polling.
 */

(function () {
  'use strict';

  // State Management
  const state = {
    baseImage: null,
    baseImageLoaded: false,
    designImage: null,
    designImageLoaded: false,
    currentDesignId: null,
    currentAngleId: window.AURA_CONFIG?.angleId || null,
    customArea: window.AURA_CONFIG?.customArea || null,
    
    // User Transformations
    scale: 1.0,
    rotation: 0.0,
    offsetX: 0.0, // In percentage of print zone (-100 to 100)
    offsetY: 0.0,
    blendMode: 'MULTIPLY',
    displacementIntensity: 18.0,
    showPrintZone: true,

    // Interaction State
    isDragging: false,
    dragStartX: 0,
    dragStartY: 0,
    startOffsetX: 0,
    startOffsetY: 0,
    
    // Active Render Job
    currentJobId: null,
    pollInterval: null,
    jobStartTime: null,
    isComparing: false,
    flatPreviewDataUrl: null,
  };

  const canvas = document.getElementById('customizerCanvas');
  const ctx = canvas ? canvas.getContext('2d') : null;

  // DOM Elements
  const scaleSlider = document.getElementById('scaleSlider');
  const scaleDisplay = document.getElementById('scaleValueDisplay');
  const rotSlider = document.getElementById('rotationSlider');
  const rotDisplay = document.getElementById('rotationValueDisplay');
  const dispSlider = document.getElementById('displacementSlider');
  const dispDisplay = document.getElementById('dispValueDisplay');
  const blendSelect = document.getElementById('blendModeSelector');
  const dropZone = document.getElementById('dropZone');
  const loadingOverlay = document.getElementById('canvasLoadingOverlay');

  // Initialization
  function initStudio() {
    if (!canvas || !ctx) return;

    // High DPI Canvas setup (internal resolution 1200x1200)
    canvas.width = 1200;
    canvas.height = 1200;

    // Setup canvas event listeners for mouse and touch
    setupCanvasInteractions();
    setupDropZone();

    // Load Base Product Image
    loadBaseImage(window.AURA_CONFIG.baseImageUrl);

    // If preset sample exists, pick first as default artwork
    const firstPreset = document.querySelector('.preset-btn');
    if (firstPreset) {
      firstPreset.click();
    }
  }

  function loadBaseImage(url) {
    if (loadingOverlay) loadingOverlay.classList.remove('hidden');
    state.baseImageLoaded = false;
    
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      state.baseImage = img;
      state.baseImageLoaded = true;
      if (loadingOverlay) loadingOverlay.classList.add('hidden');
      renderCanvas();
    };
    img.onerror = () => {
      if (loadingOverlay) loadingOverlay.classList.add('hidden');
      console.error('Failed to load base image from', url);
    };
    img.src = url;
  }

  function loadDesignImage(url, designId, title, dimsText) {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      state.designImage = img;
      state.designImageLoaded = true;
      state.currentDesignId = designId;

      // Update badge
      const badge = document.getElementById('activeDesignBadge');
      const thumb = document.getElementById('activeDesignThumb');
      const titleElem = document.getElementById('activeDesignTitle');
      const dimsElem = document.getElementById('activeDesignDims');

      if (badge && thumb && titleElem) {
        badge.classList.remove('hidden');
        badge.classList.add('flex');
        thumb.src = url;
        titleElem.innerText = title || 'Artwork Loaded';
        if (dimsElem && dimsText) dimsElem.innerText = dimsText;
      }

      renderCanvas();
    };
    img.src = url;
  }

  // Render Pipeline on HTML5 Canvas
  function renderCanvas() {
    if (!ctx || !canvas) return;

    // 1. Clear background
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 2. Draw Base Product Image
    if (state.baseImageLoaded && state.baseImage) {
      ctx.drawImage(state.baseImage, 0, 0, canvas.width, canvas.height);
    } else {
      ctx.fillStyle = '#161922';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }

    const area = state.customArea;
    if (!area) return;

    // Calculate target print zone in pixel coordinates
    const pLeft = (area.boundingLeft / 100.0) * canvas.width;
    const pTop = (area.boundingTop / 100.0) * canvas.height;
    const pWidth = (area.boundingWidth / 100.0) * canvas.width;
    const pHeight = (area.boundingHeight / 100.0) * canvas.height;
    const pCenterX = pLeft + pWidth * 0.5;
    const pCenterY = pTop + pHeight * 0.5;

    // 3. Draw Design Graphic (if loaded)
    if (state.designImageLoaded && state.designImage) {
      ctx.save();

      // Clip strictly to perspective quad or bounding box to avoid spill
      ctx.beginPath();
      if (area.quadPoints && area.quadPoints.length === 4) {
        const qp = area.quadPoints.map(p => ({
          x: (p[0] / 100.0) * canvas.width,
          y: (p[1] / 100.0) * canvas.height
        }));
        ctx.moveTo(qp[0].x, qp[0].y);
        ctx.lineTo(qp[1].x, qp[1].y);
        ctx.lineTo(qp[2].x, qp[2].y);
        ctx.lineTo(qp[3].x, qp[3].y);
        ctx.closePath();
      } else {
        ctx.rect(pLeft, pTop, pWidth, pHeight);
      }
      ctx.clip();

      // Apply User Offsets (normalized to print area size)
      const userX = pCenterX + (state.offsetX / 100.0) * pWidth;
      const userY = pCenterY + (state.offsetY / 100.0) * pHeight;

      // Translate to graphic center
      ctx.translate(userX, userY);

      // Rotate
      ctx.rotate((state.rotation * Math.PI) / 180);

      // Blend Mode Simulation on Canvas
      if (state.blendMode === 'MULTIPLY') {
        ctx.globalCompositeOperation = 'multiply';
      } else if (state.blendMode === 'OVERLAY') {
        ctx.globalCompositeOperation = 'overlay';
      } else if (state.blendMode === 'SOFT_LIGHT') {
        ctx.globalCompositeOperation = 'soft-light';
      } else {
        ctx.globalCompositeOperation = 'source-over';
      }

      // Calculate Graphic Dimensions maintaining aspect ratio
      const dw = state.designImage.width;
      const dh = state.designImage.height;
      const aspect = dw / dh;

      let drawW = pWidth * state.scale;
      let drawH = drawW / aspect;

      // Draw centered
      ctx.drawImage(
        state.designImage,
        -drawW * 0.5,
        -drawH * 0.5,
        drawW,
        drawH
      );

      ctx.restore();
    }

    // 4. Draw Print Zone Boundary Overlay
    if (state.showPrintZone) {
      ctx.save();
      ctx.strokeStyle = 'rgba(163, 230, 53, 0.7)';
      ctx.lineWidth = 2.5;
      ctx.setLineDash([8, 6]);

      if (area.quadPoints && area.quadPoints.length === 4) {
        const qp = area.quadPoints.map(p => ({
          x: (p[0] / 100.0) * canvas.width,
          y: (p[1] / 100.0) * canvas.height
        }));
        ctx.beginPath();
        ctx.moveTo(qp[0].x, qp[0].y);
        ctx.lineTo(qp[1].x, qp[1].y);
        ctx.lineTo(qp[2].x, qp[2].y);
        ctx.lineTo(qp[3].x, qp[3].y);
        ctx.closePath();
        ctx.stroke();

        // Draw corner alignment crosshairs
        ctx.setLineDash([]);
        ctx.fillStyle = '#A3E635';
        qp.forEach(pt => {
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 4.5, 0, Math.PI * 2);
          ctx.fill();
        });
      } else {
        ctx.strokeRect(pLeft, pTop, pWidth, pHeight);
      }
      ctx.restore();
    }
  }

  // Interactive Drag & Zoom Controls
  function setupCanvasInteractions() {
    function getCanvasCoords(e) {
      const rect = canvas.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      return {
        x: ((clientX - rect.left) / rect.width) * canvas.width,
        y: ((clientY - rect.top) / rect.height) * canvas.height
      };
    }

    function onPointerDown(e) {
      if (!state.designImageLoaded) return;
      state.isDragging = true;
      const coords = getCanvasCoords(e);
      state.dragStartX = coords.x;
      state.dragStartY = coords.y;
      state.startOffsetX = state.offsetX;
      state.startOffsetY = state.offsetY;
    }

    function onPointerMove(e) {
      if (!state.isDragging) return;
      e.preventDefault();
      const coords = getCanvasCoords(e);
      const deltaX = coords.x - state.dragStartX;
      const deltaY = coords.y - state.dragStartY;

      const pWidth = (state.customArea.boundingWidth / 100.0) * canvas.width;
      const pHeight = (state.customArea.boundingHeight / 100.0) * canvas.height;

      // Convert delta pixel movement to percentage offsets
      state.offsetX = state.startOffsetX + (deltaX / pWidth) * 100.0;
      state.offsetY = state.startOffsetY + (deltaY / pHeight) * 100.0;

      renderCanvas();
    }

    function onPointerUp() {
      state.isDragging = false;
    }

    // Wheel zooming
    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 0.05 : -0.05;
      state.scale = Math.min(Math.max(state.scale + zoomFactor, 0.2), 2.2);
      if (scaleSlider) scaleSlider.value = Math.round(state.scale * 100);
      if (scaleDisplay) scaleDisplay.innerText = `${Math.round(state.scale * 100)}%`;
      renderCanvas();
    }, { passive: false });

    canvas.addEventListener('mousedown', onPointerDown);
    window.addEventListener('mousemove', onPointerMove);
    window.addEventListener('mouseup', onPointerUp);

    canvas.addEventListener('touchstart', onPointerDown, { passive: false });
    window.addEventListener('touchmove', onPointerMove, { passive: false });
    window.addEventListener('touchend', onPointerUp);
  }

  // Drag and Drop File Upload
  function setupDropZone() {
    if (!dropZone) return;

    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-active');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-active');
      }, false);
    });

    dropZone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files.length > 0) {
        handleFileInput(files[0]);
      }
    });
  }

  // Global methods exposed to DOM buttons
  window.handleFileInput = function (file) {
    if (!file) return;

    const formData = new FormData();
    formData.append('design_file', file);
    formData.append('title', file.name.split('.')[0]);

    if (dropZone) dropZone.classList.add('opacity-50', 'pointer-events-none');

    fetch('/api/upload-design/', {
      method: 'POST',
      body: formData
    })
    .then(res => res.json())
    .then(data => {
      if (dropZone) dropZone.classList.remove('opacity-50', 'pointer-events-none');
      if (data.success) {
        loadDesignImage(data.url, data.design_id, data.title, `${data.width} x ${data.height} px`);
      } else {
        alert('Upload failed: ' + (data.error || 'Unknown error'));
      }
    })
    .catch(err => {
      if (dropZone) dropZone.classList.remove('opacity-50', 'pointer-events-none');
      console.error('Upload error', err);
      alert('Network upload error: ' + err.message);
    });
  };

  window.selectPresetArtwork = function (presetId, url, title) {
    // Highlight button
    document.querySelectorAll('.preset-btn').forEach(b => {
      b.classList.remove('border-[#A3E635]', 'bg-[#1E2536]');
    });
    const clickedBtn = document.querySelector(`.preset-btn[data-preset-id="${presetId}"]`);
    if (clickedBtn) {
      clickedBtn.classList.add('border-[#A3E635]', 'bg-[#1E2536]');
    }

    fetch('/api/select-preset/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preset_id: presetId })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        loadDesignImage(data.url, data.design_id, data.title, `${data.width} x ${data.height} px`);
      }
    })
    .catch(err => {
      // Direct fallback to image url
      loadDesignImage(url, presetId, title, '1000 x 1000 px');
    });
  };

  window.updateScale = function (val) {
    state.scale = val / 100.0;
    if (scaleDisplay) scaleDisplay.innerText = `${val}%`;
    renderCanvas();
  };

  window.updateRotation = function (val) {
    state.rotation = parseFloat(val);
    if (rotDisplay) rotDisplay.innerText = `${val}°`;
    renderCanvas();
  };

  window.updateDisplacement = function (val) {
    state.displacementIntensity = parseFloat(val);
    if (dispDisplay) dispDisplay.innerText = `${val} px`;
  };

  window.updateBlendMode = function (val) {
    state.blendMode = val;
    renderCanvas();
  };

  window.centerArtwork = function () {
    state.offsetX = 0.0;
    state.offsetY = 0.0;
    renderCanvas();
  };

  window.fitArtworkToZone = function () {
    state.scale = 1.0;
    state.offsetX = 0.0;
    state.offsetY = 0.0;
    if (scaleSlider) scaleSlider.value = 100;
    if (scaleDisplay) scaleDisplay.innerText = '100%';
    renderCanvas();
  };

  window.resetTransformations = function () {
    state.scale = 1.0;
    state.rotation = 0.0;
    state.offsetX = 0.0;
    state.offsetY = 0.0;
    state.blendMode = 'MULTIPLY';
    if (scaleSlider) scaleSlider.value = 100;
    if (scaleDisplay) scaleDisplay.innerText = '100%';
    if (rotSlider) rotSlider.value = 0;
    if (rotDisplay) rotDisplay.innerText = '0°';
    if (blendSelect) blendSelect.value = 'MULTIPLY';
    renderCanvas();
  };

  window.togglePrintZoneOverlay = function () {
    state.showPrintZone = !state.showPrintZone;
    const btn = document.getElementById('btnToggleZone');
    if (btn) {
      btn.innerText = state.showPrintZone ? 'Hide Print Box' : 'Show Print Box';
    }
    renderCanvas();
  };

  window.switchProduct = function (slug) {
    window.location.href = `/?product=${slug}`;
  };

  window.switchAngle = function (angleId) {
    const url = new URL(window.location.href);
    url.searchParams.set('angle', angleId);
    window.location.href = url.toString();
  };

  // Trigger Asynchronous High-Resolution Render Job
  window.triggerHighResRender = function () {
    if (!state.currentDesignId) {
      alert('Please upload or select an artwork first.');
      return;
    }

    const btn = document.getElementById('btnExecuteRender');
    const spinner = document.getElementById('btnRenderSpinner');
    const btnText = document.getElementById('btnRenderText');
    const progressCard = document.getElementById('renderProgressCard');
    const resultCard = document.getElementById('renderResultCard');

    if (btn) btn.disabled = true;
    if (spinner) spinner.classList.remove('hidden');
    if (btnText) btnText.innerText = 'Executing Render Pipeline...';
    if (progressCard) progressCard.classList.remove('hidden');
    if (resultCard) resultCard.classList.add('hidden');

    state.jobStartTime = performance.now();
    updateJobProgress(10, 'Submitting payload to Celery queue...');

    const payload = {
      angle_id: state.currentAngleId,
      design_id: state.currentDesignId,
      scale: state.scale,
      rotation: state.rotation,
      offset_x: state.offsetX,
      offset_y: state.offsetY,
      blend_mode: state.blendMode,
      displacement_intensity: state.displacementIntensity
    };

    fetch('/api/render-mockup/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
      if (!data.success) {
        throw new Error(data.error || 'Server rejected render job');
      }

      state.currentJobId = data.job_id;

      // If already finished synchronously
      if (data.status === 'COMPLETED' && data.result_url) {
        finishJob(data.result_url, data.execution_time || 0.25);
      } else {
        // Start polling Celery status
        startJobPolling(data.job_id);
      }
    })
    .catch(err => {
      resetRenderButton();
      updateJobProgress(100, 'Render failed: ' + err.message);
      alert('Rendering Error: ' + err.message);
    });
  };

  function startJobPolling(jobId) {
    if (state.pollInterval) clearInterval(state.pollInterval);

    state.pollInterval = setInterval(() => {
      const elapsed = ((performance.now() - state.jobStartTime) / 1000).toFixed(1);
      const timerElem = document.getElementById('jobTimer');
      if (timerElem) timerElem.innerText = `${elapsed}s`;

      fetch(`/api/jobs/${jobId}/status/`)
        .then(res => res.json())
        .then(data => {
          updateJobProgress(data.progress, data.status_message);

          if (data.status === 'COMPLETED') {
            clearInterval(state.pollInterval);
            finishJob(data.result_url, data.execution_time);
          } else if (data.status === 'FAILED') {
            clearInterval(state.pollInterval);
            resetRenderButton();
            alert('Render failed: ' + (data.error || 'Unknown worker error'));
          }
        })
        .catch(e => {
          console.warn('Status poll attempt failed', e);
        });
    }, 600);
  }

  function updateJobProgress(pct, msg) {
    const bar = document.getElementById('jobProgressBar');
    const textPct = document.getElementById('jobProgressPct');
    const textMsg = document.getElementById('jobStatusMsg');

    if (bar) bar.style.width = `${pct}%`;
    if (textPct) textPct.innerText = `${pct}%`;
    if (textMsg && msg) textMsg.innerText = msg;
  }

  function finishJob(resultUrl, execTime) {
    resetRenderButton();
    updateJobProgress(100, 'Render completed successfully');

    const resultCard = document.getElementById('renderResultCard');
    const resultImg = document.getElementById('renderedMockupImg');
    const downloadBtn = document.getElementById('btnDownloadMockup');
    const statsElem = document.getElementById('renderedStats');

    if (resultCard && resultImg && downloadBtn) {
      resultCard.classList.remove('hidden');
      resultImg.src = resultUrl;
      downloadBtn.href = resultUrl;
      if (statsElem) {
        statsElem.innerText = `Execution: ${execTime || 0.28}s | Output: 2400 x 2400 px | Quality: 95%`;
      }

      // Smooth scroll into view on mobile
      resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function resetRenderButton() {
    const btn = document.getElementById('btnExecuteRender');
    const spinner = document.getElementById('btnRenderSpinner');
    const btnText = document.getElementById('btnRenderText');

    if (btn) btn.disabled = false;
    if (spinner) spinner.classList.add('hidden');
    if (btnText) btnText.innerText = '⚡ Render Photorealistic 2400px Mockup';
  }

  // Comparison mode (Conformed vs Flat)
  window.toggleCompareMode = function () {
    const img = document.getElementById('renderedMockupImg');
    const btn = document.getElementById('btnCompare');
    if (!img) return;

    state.isComparing = !state.isComparing;
    if (state.isComparing) {
      // Show flat preview from client canvas
      if (!state.flatPreviewDataUrl) {
        state.flatPreviewDataUrl = canvas.toDataURL('image/jpeg', 0.9);
      }
      img.dataset.conformedSrc = img.src;
      img.src = state.flatPreviewDataUrl;
      if (btn) btn.innerText = 'Showing Flat • Click for Folds';
    } else {
      if (img.dataset.conformedSrc) {
        img.src = img.dataset.conformedSrc;
      }
      if (btn) btn.innerText = 'Compare Flat vs Folds';
    }
  };

  // Fullscreen Zoom Modal Handlers
  window.openZoomModal = function (src) {
    const modal = document.getElementById('zoomModal');
    const img = document.getElementById('zoomModalImg');
    if (modal && img) {
      img.src = src;
      modal.classList.remove('hidden');
      modal.classList.add('flex');
    }
  };

  window.closeZoomModal = function () {
    const modal = document.getElementById('zoomModal');
    if (modal) {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    }
  };

  // Boot on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initStudio);
  } else {
    initStudio();
  }

})();
