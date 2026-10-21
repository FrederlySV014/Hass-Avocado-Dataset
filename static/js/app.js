/**
 * CLASIFICADOR DE PALTA HASS — LÓGICA PRINCIPAL DEL VISOR (FRONTEND)
 * Maneja navegación por lotes de 250, zoom/pan interactivo, atajos de teclado,
 * avance automático, comparación multivista de la misma fruta, y sincronización REST.
 */

(function () {
  'use strict';

  // --- ESTADO GLOBAL ---
  const state = {
    currentBatchId: 1,
    totalBatches: 59,
    batchItems: [],
    currentBatchIndex: 0, // índice dentro de batchItems (0..249)
    currentImage: null,
    filter: 'all', // 'all', 'pending', 'R', 'S', 'D', 'X'
    autoAdvance: true,
    isSaving: false,
    viewMode: 'inspect', // 'inspect' | 'gallery'

    // Zoom y Pan
    zoom: 1.0,
    panX: 0,
    panY: 0,
    isDragging: false,
    dragStartX: 0,
    dragStartY: 0,

    // Comparativa de fruta
    currentFruitImages: []
  };

  // --- SELECTORES DOM ---
  const dom = {
    // Header Stats
    globalReviewedCount: document.getElementById('global-reviewed-count'),
    globalReviewedPct: document.getElementById('global-reviewed-pct'),
    globalProgressFill: document.getElementById('global-progress-fill'),
    globalFruitsCount: document.getElementById('global-fruits-count'),
    globalCountR: document.getElementById('global-count-r'),
    globalCountS: document.getElementById('global-count-s'),
    globalCountD: document.getElementById('global-count-d'),
    globalCountX: document.getElementById('global-count-x'),

    // Header Actions
    btnOpenProtocol: document.getElementById('btn-open-protocol'),
    btnUndoHeader: document.getElementById('btn-undo-header'),
    btnExportHeader: document.getElementById('btn-export-header'),

    // Batch Bar
    batchSelect: document.getElementById('batch-select'),
    btnPrevBatch: document.getElementById('btn-prev-batch'),
    btnNextBatch: document.getElementById('btn-next-batch'),
    batchStatTotal: document.getElementById('batch-stat-total'),
    batchStatPending: document.getElementById('batch-stat-pending'),
    batchStatR: document.getElementById('batch-stat-r'),
    batchStatS: document.getElementById('batch-stat-s'),
    batchStatD: document.getElementById('batch-stat-d'),
    batchStatX: document.getElementById('batch-stat-x'),

    // Filter Buttons
    filterGroup: document.getElementById('filter-group'),
    filterBtns: document.querySelectorAll('.filter-btn'),

    // View Mode
    btnModeInspect: document.getElementById('btn-mode-inspect'),
    btnModeGallery: document.getElementById('btn-mode-gallery'),
    inspectorView: document.getElementById('inspector-view'),
    galleryView: document.getElementById('gallery-view'),

    // Batch Completed Banner
    batchCompletedBanner: document.getElementById('batch-completed-banner'),
    btnBannerContinueBatch: document.getElementById('btn-banner-continue-batch'),

    // Stage & Image
    viewportCanvas: document.getElementById('viewport-canvas'),
    transformContainer: document.getElementById('transform-container'),
    mainInspectImage: document.getElementById('main-inspect-image'),
    imageLoadingOverlay: document.getElementById('image-loading-overlay'),
    currentBadgeIndex: document.getElementById('current-badge-index'),
    currentImageName: document.getElementById('current-image-name'),
    currentCategoryBadge: document.getElementById('current-category-badge'),

    // Stage Controls
    btnZoomIn: document.getElementById('btn-zoom-in'),
    btnZoomOut: document.getElementById('btn-zoom-out'),
    btnZoomFit: document.getElementById('btn-zoom-fit'),
    btnZoomReset: document.getElementById('btn-zoom-reset'),
    zoomLevelText: document.getElementById('zoom-level-text'),
    btnNavPrev: document.getElementById('btn-nav-prev'),
    btnNavNext: document.getElementById('btn-nav-next'),

    // Quick Strip
    batchQuickStrip: document.getElementById('batch-quick-strip'),

    // Sidebar Meta
    metaFruitId: document.getElementById('meta-fruit-id'),
    metaStorageGroup: document.getElementById('meta-storage-group'),
    metaDay: document.getElementById('meta-day'),
    metaView: document.getElementById('meta-view'),
    metaRipening: document.getElementById('meta-ripening'),
    metaTimestamp: document.getElementById('meta-timestamp'),

    // Sidebar Decision Buttons
    btnActionR: document.getElementById('btn-action-r'),
    btnActionS: document.getElementById('btn-action-s'),
    btnActionD: document.getElementById('btn-action-d'),
    btnActionX: document.getElementById('btn-action-x'),
    inputDecisionNote: document.getElementById('input-decision-note'),
    chkAutoAdvance: document.getElementById('chk-auto-advance'),

    // Comparison Gallery
    comparisonCountTag: document.getElementById('comparison-count-tag'),
    comparisonGallery: document.getElementById('comparison-gallery'),

    // Gallery View Elements
    galleryBatchNum: document.getElementById('gallery-batch-num'),
    galleryItemsCount: document.getElementById('gallery-items-count'),
    galleryCardsGrid: document.getElementById('gallery-cards-grid'),
    btnGalleryReturnInspect: document.getElementById('btn-gallery-return-inspect'),

    // Modals
    modalDiscard: document.getElementById('modal-discard'),
    inputDiscardDetail: document.getElementById('input-discard-detail'),
    btnCancelDiscard: document.getElementById('btn-cancel-discard'),
    btnConfirmDiscard: document.getElementById('btn-confirm-discard'),

    modalProtocol: document.getElementById('modal-protocol'),
    protocolContentBody: document.getElementById('protocol-content-body'),
    btnCloseProtocol: document.getElementById('btn-close-protocol'),
    btnOkProtocol: document.getElementById('btn-ok-protocol'),

    modalExport: document.getElementById('modal-export'),
    btnCloseExport: document.getElementById('btn-close-export'),
    btnCancelExportDialog: document.getElementById('btn-cancel-export-dialog'),
    btnRunExportAction: document.getElementById('btn-run-export-action'),
    exportSpinner: document.getElementById('export-spinner'),
    exportResultsArea: document.getElementById('export-results-area'),

    // Toast Container
    toastContainer: document.getElementById('toast-container')
  };

  // --- INICIALIZACIÓN ---
  async function init() {
    setupEventListeners();
    setupTransformHandlers();
    await loadGlobalStatus();
    await loadBatch(state.currentBatchId);
  }

  // --- CARGA DE ESTADO GLOBAL Y SESIÓN ---
  async function loadGlobalStatus() {
    try {
      const res = await fetch('/api/status');
      if (!res.ok) throw new Error('Error al obtener estado');
      const data = await res.json();

      updateGlobalMetrics(data);
      state.totalBatches = data.total_batches;

      // Poblar selector de lotes
      populateBatchSelect(data.total_batches, data.completed_batches);

      if (data.session && data.session.current_batch_id) {
        state.currentBatchId = data.session.current_batch_id;
        dom.batchSelect.value = state.currentBatchId;
      }
    } catch (e) {
      console.error(e);
      showToast('Error de conexión con el servidor', 'error');
    }
  }

  function updateGlobalMetrics(data) {
    dom.globalReviewedCount.textContent = data.total_reviewed.toLocaleString();
    const pct = data.total_images > 0 ? ((data.total_reviewed / data.total_images) * 100).toFixed(1) : '0.0';
    dom.globalReviewedPct.textContent = `${pct}%`;
    dom.globalProgressFill.style.width = `${pct}%`;

    dom.globalFruitsCount.textContent = data.reviewed_fruits_count || 0;
    dom.globalCountR.textContent = data.category_counts.R || 0;
    dom.globalCountS.textContent = data.category_counts.S || 0;
    dom.globalCountD.textContent = data.category_counts.D || 0;
    dom.globalCountX.textContent = data.category_counts.X || 0;
  }

  function populateBatchSelect(totalBatches, completedBatches = []) {
    dom.batchSelect.innerHTML = '';
    const completedSet = new Set(completedBatches);

    for (let i = 1; i <= totalBatches; i++) {
      const opt = document.createElement('option');
      opt.value = i;
      const isDone = completedSet.has(i);
      opt.textContent = `Lote ${i} / ${totalBatches} ${isDone ? '✓ (Completo)' : ''}`;
      dom.batchSelect.appendChild(opt);
    }
  }

  // --- CARGA DE LOTE ---
  async function loadBatch(batchId, targetImageId = null) {
    try {
      dom.imageLoadingOverlay.style.display = 'flex';
      const res = await fetch(`/api/batch/${batchId}`);
      if (!res.ok) throw new Error(`Lote ${batchId} no encontrado`);
      const data = await res.json();

      state.currentBatchId = batchId;
      state.batchItems = data.items;
      dom.batchSelect.value = batchId;

      // Actualizar píldoras de estado del lote
      updateBatchPills(data.stats);

      // Actualizar banner de completado
      if (data.is_completed) {
        dom.batchCompletedBanner.style.display = 'block';
      } else {
        dom.batchCompletedBanner.style.display = 'none';
      }

      // Habilitar/Deshabilitar botones de navegación de lote
      dom.btnPrevBatch.disabled = (batchId <= 1);
      dom.btnNextBatch.disabled = (batchId >= state.totalBatches);

      // Renderizar tira rápida y galería
      renderQuickStrip();
      renderGalleryGrid();

      // Seleccionar imagen inicial
      let initialIndex = 0;
      if (targetImageId) {
        const foundIdx = state.batchItems.findIndex(it => it.image_id === targetImageId);
        if (foundIdx !== -1) initialIndex = foundIdx;
      } else {
        // Encontrar la primera imagen pendiente
        const firstPending = state.batchItems.findIndex(it => !it.decision);
        if (firstPending !== -1) initialIndex = firstPending;
      }

      selectImageByIndex(initialIndex);

      // Guardar sesión
      saveSessionState();
    } catch (e) {
      console.error(e);
      showToast(`Error al cargar lote ${batchId}: ${e.message}`, 'error');
    } finally {
      dom.imageLoadingOverlay.style.display = 'none';
    }
  }

  function updateBatchPills(stats) {
    dom.batchStatTotal.textContent = `Total: ${stats.total}`;
    dom.batchStatPending.textContent = `Pendientes: ${stats.pending}`;
    dom.batchStatR.textContent = `R: ${stats.R}`;
    dom.batchStatS.textContent = `S: ${stats.S}`;
    dom.batchStatD.textContent = `D: ${stats.D}`;
    dom.batchStatX.textContent = `X: ${stats.X}`;

    // Actualizar etiquetas de filtros
    document.getElementById('filter-all').textContent = `Todos (${stats.total})`;
    document.getElementById('filter-pending').textContent = `Pendientes (${stats.pending})`;
    document.getElementById('filter-r').textContent = `R (${stats.R})`;
    document.getElementById('filter-s').textContent = `S (${stats.S})`;
    document.getElementById('filter-d').textContent = `D (${stats.D})`;
    document.getElementById('filter-x').textContent = `X (${stats.X})`;
  }

  // --- SELECCIÓN Y VISUALIZACIÓN DE IMAGEN ---
  function selectImageByIndex(index) {
    if (index < 0 || index >= state.batchItems.length) return;

    state.currentBatchIndex = index;
    const item = state.batchItems[index];
    state.currentImage = item;

    // Actualizar Encabezado del Visor
    dom.currentBadgeIndex.textContent = `#${item.batch_index} / ${state.batchItems.length}`;
    dom.currentImageName.textContent = item.filename;

    updateCategoryBadge(item.decision);

    // Actualizar Metadatos
    dom.metaFruitId.textContent = item.fruit_id;
    dom.metaStorageGroup.textContent = item.storage_group;
    dom.metaDay.textContent = `Día ${item.day}`;
    dom.metaView.textContent = `Vista ${item.view.toUpperCase()}`;
    dom.metaRipening.textContent = `Estadío ${item.ripening_stage}`;
    dom.metaTimestamp.textContent = item.time_stamp || 'N/A';

    // Cargar campo de notas si ya tenía
    dom.inputDecisionNote.value = item.decision ? (item.decision.note || '') : '';

    // Resaltar botones de acción según decisión actual
    highlightActiveDecisionButton(item.decision ? item.decision.category : null);

    // Cargar imagen en alta resolución
    loadMainImage(`/api/image/${encodeURIComponent(item.image_id)}`);

    // Actualizar tira rápida activa
    highlightQuickStripActive(item.image_id);

    // Cargar comparativa de la misma fruta
    loadFruitComparison(item.fruit_id, item.image_id);

    // Guardar sesión
    saveSessionState();
  }

  function updateCategoryBadge(decision) {
    dom.currentCategoryBadge.className = 'badge-status-current';
    if (!decision) {
      dom.currentCategoryBadge.classList.add('is-pending');
      dom.currentCategoryBadge.textContent = 'PENDIENTE';
    } else {
      const cat = decision.category.toUpperCase();
      dom.currentCategoryBadge.classList.add(`is-${cat.toLowerCase()}`);
      let label = cat;
      if (cat === 'R') label = 'R — CON DEFECTO';
      if (cat === 'S') label = 'S — SIN DEFECTO';
      if (cat === 'D') label = 'D — DUDOSA';
      if (cat === 'X') label = `X — DESCARTADA (${decision.reason || ''})`;
      dom.currentCategoryBadge.textContent = label;
    }
  }

  function highlightActiveDecisionButton(cat) {
    [dom.btnActionR, dom.btnActionS, dom.btnActionD, dom.btnActionX].forEach(b => b.classList.remove('is-current'));
    if (cat === 'R') dom.btnActionR.classList.add('is-current');
    if (cat === 'S') dom.btnActionS.classList.add('is-current');
    if (cat === 'D') dom.btnActionD.classList.add('is-current');
    if (cat === 'X') dom.btnActionX.classList.add('is-current');
  }

  function loadMainImage(url) {
    dom.imageLoadingOverlay.style.display = 'flex';
    const img = new Image();
    img.onload = () => {
      dom.mainInspectImage.src = url;
      dom.imageLoadingOverlay.style.display = 'none';
      resetTransform();
    };
    img.onerror = () => {
      dom.imageLoadingOverlay.style.display = 'none';
      showToast('Error al cargar la imagen', 'error');
    };
    img.src = url;
  }

  // --- COMPARATIVA DE LA MISMA FRUTA ---
  async function loadFruitComparison(fruitId, currentImageId) {
    try {
      const res = await fetch(`/api/fruit_comparison/${encodeURIComponent(fruitId)}`);
      if (!res.ok) return;
      const data = await res.json();

      dom.comparisonCountTag.textContent = `${data.total_images} fotos`;
      dom.comparisonGallery.innerHTML = '';

      data.images.forEach(item => {
        const card = document.createElement('div');
        card.className = 'compare-card';
        if (item.image_id === currentImageId) {
          card.classList.add('is-current-view');
        }

        const img = document.createElement('img');
        img.loading = 'lazy';
        img.src = `/api/thumbnail/${encodeURIComponent(item.image_id)}`;
        img.alt = item.filename;

        const pill = document.createElement('div');
        pill.className = 'compare-meta-pill';
        const catTag = item.decision ? item.decision.category : '•';
        pill.innerHTML = `<span>D${item.day} [${item.view.toUpperCase()}]</span><span style="color:var(--accent-cyan)">${catTag}</span>`;

        card.appendChild(img);
        card.appendChild(pill);

        card.addEventListener('click', () => {
          // Si la imagen pertenece al lote actual, saltar a ella
          const idx = state.batchItems.findIndex(it => it.image_id === item.image_id);
          if (idx !== -1) {
            selectImageByIndex(idx);
          } else {
            // Si está en otro lote, cambiar a ese lote
            loadBatch(item.batch_id, item.image_id);
          }
        });

        dom.comparisonGallery.appendChild(card);
      });
    } catch (e) {
      console.error('Error al cargar comparativa de fruta:', e);
    }
  }

  // --- TIRA RÁPIDA DE MINIATURAS ---
  function renderQuickStrip() {
    dom.batchQuickStrip.innerHTML = '';
    const filtered = getFilteredBatchItems();

    filtered.forEach(item => {
      const div = document.createElement('div');
      div.className = 'quick-thumb';
      div.id = `qthumb-${item.global_index}`;
      div.title = `${item.filename} (Día ${item.day}, Vista ${item.view.toUpperCase()})`;

      if (item.decision) {
        div.classList.add(`is-${item.decision.category.toLowerCase()}`);
      } else {
        div.classList.add('is-pending');
      }

      const img = document.createElement('img');
      img.loading = 'lazy';
      img.src = `/api/thumbnail/${encodeURIComponent(item.image_id)}`;
      img.alt = item.filename;

      div.appendChild(img);

      div.addEventListener('click', () => {
        const idx = state.batchItems.findIndex(it => it.image_id === item.image_id);
        if (idx !== -1) selectImageByIndex(idx);
      });

      dom.batchQuickStrip.appendChild(div);
    });
  }

  function highlightQuickStripActive(imageId) {
    document.querySelectorAll('.quick-thumb').forEach(el => el.classList.remove('active'));
    const item = state.currentImage;
    if (item) {
      const target = document.getElementById(`qthumb-${item.global_index}`);
      if (target) {
        target.classList.add('active');
        target.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      }
    }
  }

  // --- GALERÍA COMPLETA (250 TARJETAS) ---
  function renderGalleryGrid() {
    dom.galleryCardsGrid.innerHTML = '';
    dom.galleryBatchNum.textContent = state.currentBatchId;
    const filtered = getFilteredBatchItems();
    dom.galleryItemsCount.textContent = `Mostrando ${filtered.length} de ${state.batchItems.length} imágenes`;

    filtered.forEach(item => {
      const card = document.createElement('div');
      card.className = 'gallery-card';

      const thumbWrap = document.createElement('div');
      thumbWrap.className = 'gallery-thumb-wrap';

      const img = document.createElement('img');
      img.loading = 'lazy';
      img.src = `/api/thumbnail/${encodeURIComponent(item.image_id)}`;
      img.alt = item.filename;

      const badge = document.createElement('div');
      badge.className = 'gallery-card-badge';
      if (item.decision) {
        const cat = item.decision.category.toUpperCase();
        badge.classList.add(`badge-${cat.toLowerCase()}`);
        badge.textContent = cat;
      } else {
        badge.classList.add('badge-pending');
        badge.textContent = 'PEND';
      }

      thumbWrap.appendChild(img);
      thumbWrap.appendChild(badge);

      const body = document.createElement('div');
      body.className = 'gallery-card-body';

      const fname = document.createElement('span');
      fname.className = 'gallery-card-filename';
      fname.textContent = item.filename;

      const sub = document.createElement('div');
      sub.className = 'gallery-card-sub';
      sub.innerHTML = `<span>${item.fruit_id}</span><span>D${item.day} • ${item.view.toUpperCase()}</span>`;

      body.appendChild(fname);
      body.appendChild(sub);

      card.appendChild(thumbWrap);
      card.appendChild(body);

      card.addEventListener('click', () => {
        const idx = state.batchItems.findIndex(it => it.image_id === item.image_id);
        if (idx !== -1) {
          selectImageByIndex(idx);
          switchViewMode('inspect');
        }
      });

      dom.galleryCardsGrid.appendChild(card);
    });
  }

  function getFilteredBatchItems() {
    if (state.filter === 'all') return state.batchItems;
    if (state.filter === 'pending') return state.batchItems.filter(it => !it.decision);
    return state.batchItems.filter(it => it.decision && it.decision.category === state.filter);
  }

  // --- ACCIÓN DE CLASIFICACIÓN (GUARDAR DECISIÓN) ---
  async function assignCategory(category, note = '', reason = null) {
    if (!state.currentImage || state.isSaving) return;
    state.isSaving = true;

    const imageId = state.currentImage.image_id;
    const finalNote = note || dom.inputDecisionNote.value.trim();

    try {
      const payload = {
        image_id: imageId,
        category: category,
        note: finalNote,
        reason: reason
      };

      const res = await fetch('/api/decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Error al guardar');

      // Actualizar estado en memoria local
      state.currentImage.decision = data.decision;
      updateCategoryBadge(data.decision);
      highlightActiveDecisionButton(category);

      showToast(`Guardado: ${category} en ${state.currentImage.filename}`, `toast-${category.toLowerCase()}`);

      // Actualizar contadores del lote y globales
      await refreshBatchStats();
      await loadGlobalStatus();

      // Actualizar tira rápida y galería
      renderQuickStrip();
      highlightQuickStripActive(imageId);

      // Si el lote se completó
      if (data.batch_completed) {
        dom.batchCompletedBanner.style.display = 'block';
        showToast('¡Felicidades! Lote completado al 100%', 'info');
      }

      // Avance automático a la siguiente imagen pendiente
      if (dom.chkAutoAdvance.checked) {
        advanceToNextPending();
      }

    } catch (e) {
      console.error(e);
      showToast(`Error: ${e.message}`, 'error');
    } finally {
      state.isSaving = false;
    }
  }

  function advanceToNextPending() {
    // Buscar la siguiente pendiente hacia adelante
    let nextIdx = -1;
    for (let i = state.currentBatchIndex + 1; i < state.batchItems.length; i++) {
      if (!state.batchItems[i].decision) {
        nextIdx = i;
        break;
      }
    }

    // Si no encontró hacia adelante, buscar desde el inicio
    if (nextIdx === -1) {
      for (let i = 0; i < state.currentBatchIndex; i++) {
        if (!state.batchItems[i].decision) {
          nextIdx = i;
          break;
        }
      }
    }

    if (nextIdx !== -1) {
      selectImageByIndex(nextIdx);
    } else {
      // Si no quedan pendientes, avanzar a la siguiente normal
      if (state.currentBatchIndex < state.batchItems.length - 1) {
        selectImageByIndex(state.currentBatchIndex + 1);
      }
    }
  }

  async function refreshBatchStats() {
    const res = await fetch(`/api/batch/${state.currentBatchId}`);
    if (res.ok) {
      const data = await res.json();
      updateBatchPills(data.stats);
    }
  }

  // --- DESHACER (UNDO) ---
  async function performUndo() {
    try {
      const res = await fetch('/api/undo', { method: 'POST' });
      const data = await res.json();

      if (data.status === 'empty') {
        showToast('No hay más acciones para deshacer', 'info');
        return;
      }

      showToast(`Deshecha acción en ${data.image_id}`, 'info');

      // Recargar lote actual y estado global
      await loadBatch(state.currentBatchId, data.image_id);
      await loadGlobalStatus();
    } catch (e) {
      console.error(e);
      showToast('Error al deshacer', 'error');
    }
  }

  // --- MODAL DE DESCARTE (X) ---
  function openDiscardModal() {
    if (!state.currentImage) return;
    dom.inputDiscardDetail.value = '';
    dom.modalDiscard.style.display = 'flex';
  }

  function closeDiscardModal() {
    dom.modalDiscard.style.display = 'none';
  }

  function confirmDiscard() {
    const checkedRadio = document.querySelector('input[name="discard-reason"]:checked');
    if (!checkedRadio) {
      showToast('Selecciona un motivo de descarte', 'error');
      return;
    }

    let reason = checkedRadio.value;
    const detail = dom.inputDiscardDetail.value.trim();

    if (reason === 'otro') {
      if (!detail) {
        showToast('Para el motivo "Otro", el detalle es obligatorio', 'error');
        dom.inputDiscardDetail.focus();
        return;
      }
      reason = `Otro: ${detail}`;
    } else if (detail) {
      reason = `${reason} (${detail})`;
    }

    closeDiscardModal();
    assignCategory('X', '', reason);
  }

  // --- PROTOCOLO TÉCNICO MODAL ---
  async function openProtocolModal() {
    dom.modalProtocol.style.display = 'flex';
    try {
      const res = await fetch('/api/protocol');
      const data = await res.json();
      if (data.status === 'ok') {
        dom.protocolContentBody.innerHTML = formatMarkdown(data.content);
      } else {
        dom.protocolContentBody.innerHTML = '<p>Error al cargar el protocolo.</p>';
      }
    } catch (e) {
      dom.protocolContentBody.innerHTML = '<p>Error de conexión al cargar protocolo.</p>';
    }
  }

  function closeProtocolModal() {
    dom.modalProtocol.style.display = 'none';
  }

  function formatMarkdown(md) {
    // Conversor sencillo y limpio para el texto del protocolo
    return md
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
      .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*)\*/gim, '<em>$1</em>')
      .replace(/^- (.*$)/gim, '<li>$1</li>')
      .replace(/\n\n/gim, '<p></p>')
      .replace(/\n/gim, '<br>');
  }

  // --- EXPORTACIÓN ---
  function openExportModal() {
    dom.modalExport.style.display = 'flex';
    dom.exportSpinner.style.display = 'none';
    dom.exportResultsArea.style.display = 'block';
  }

  function closeExportModal() {
    dom.modalExport.style.display = 'none';
  }

  async function runExport() {
    dom.exportSpinner.style.display = 'flex';
    dom.exportResultsArea.style.display = 'none';
    dom.btnRunExportAction.disabled = true;

    try {
      const res = await fetch('/api/export', { method: 'POST' });
      const data = await res.json();

      if (data.status === 'ok') {
        const rep = data.report;
        dom.exportResultsArea.innerHTML = `
          <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid var(--cat-s); border-radius: 8px; padding: 14px; margin-bottom: 12px;">
            <h3 style="color: #6ee7b7; margin-bottom: 6px;">✓ Exportación Exitosa</h3>
            <p>Se copiaron <strong>${rep.total_exported}</strong> fotografías a disco.</p>
          </div>
          <ul class="export-list-preview">
            <li><strong>Con Defecto (R):</strong> ${rep.by_category.R_con_defecto} imágenes</li>
            <li><strong>Sin Defecto (S):</strong> ${rep.by_category.S_sin_defecto} imágenes</li>
            <li><strong>Dudosas (D):</strong> ${rep.by_category.D_dudosas} imágenes</li>
            <li><strong>Descartadas (X):</strong> ${rep.by_category.X_descartadas} imágenes</li>
          </ul>
          <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 8px;">
            Copias obsoletas reclasificadas eliminadas: ${rep.obsolete_cleaned_up}.
          </p>
        `;
        showToast('Exportación finalizada correctamente', 'info');
      } else {
        throw new Error(data.message || 'Error en exportación');
      }
    } catch (e) {
      dom.exportResultsArea.innerHTML = `<p style="color: #ef4444;">Error: ${e.message}</p>`;
      showToast('Falla en la exportación', 'error');
    } finally {
      dom.exportSpinner.style.display = 'none';
      dom.exportResultsArea.style.display = 'block';
      dom.btnRunExportAction.disabled = false;
    }
  }

  // --- ZOOM Y PAN INTERACTIVO ---
  function setupTransformHandlers() {
    const canvas = dom.viewportCanvas;

    // Zoom con rueda de ratón
    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = 1.15;
      if (e.deltaY < 0) {
        setZoom(state.zoom * zoomFactor);
      } else {
        setZoom(state.zoom / zoomFactor);
      }
    }, { passive: false });

    // Drag / Pan con ratón
    canvas.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return; // Solo clic izquierdo
      state.isDragging = true;
      state.dragStartX = e.clientX - state.panX;
      state.dragStartY = e.clientY - state.panY;
      canvas.style.cursor = 'grabbing';
    });

    window.addEventListener('mousemove', (e) => {
      if (!state.isDragging) return;
      state.panX = e.clientX - state.dragStartX;
      state.panY = e.clientY - state.dragStartY;
      applyTransform();
    });

    window.addEventListener('mouseup', () => {
      if (state.isDragging) {
        state.isDragging = false;
        canvas.style.cursor = 'grab';
      }
    });

    // Botones de zoom
    dom.btnZoomIn.addEventListener('click', () => setZoom(state.zoom * 1.2));
    dom.btnZoomOut.addEventListener('click', () => setZoom(state.zoom / 1.2));
    dom.btnZoomFit.addEventListener('click', () => resetTransform());
    dom.btnZoomReset.addEventListener('click', () => resetTransform());
  }

  function setZoom(newZoom) {
    // Límites de zoom: 0.5x a 8.0x
    state.zoom = Math.max(0.5, Math.min(8.0, newZoom));
    dom.zoomLevelText.textContent = `${Math.round(state.zoom * 100)}%`;
    applyTransform();
  }

  function resetTransform() {
    state.zoom = 1.0;
    state.panX = 0;
    state.panY = 0;
    dom.zoomLevelText.textContent = '100%';
    applyTransform();
  }

  function applyTransform() {
    dom.transformContainer.style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.zoom})`;
  }

  // --- NAVEGACIÓN Y CAMBIO DE VISTA ---
  function switchViewMode(mode) {
    state.viewMode = mode;
    if (mode === 'inspect') {
      dom.inspectorView.style.display = 'flex';
      dom.galleryView.style.display = 'none';
      dom.btnModeInspect.classList.add('active');
      dom.btnModeGallery.classList.remove('active');
    } else {
      dom.inspectorView.style.display = 'none';
      dom.galleryView.style.display = 'flex';
      dom.btnModeInspect.classList.remove('active');
      dom.btnModeGallery.classList.add('active');
      renderGalleryGrid();
    }
  }

  // --- SESIÓN PERSISTENTE ---
  async function saveSessionState() {
    try {
      await fetch('/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          batch_id: state.currentBatchId,
          image_id: state.currentImage ? state.currentImage.image_id : null,
          active_filter: state.filter
        })
      });
    } catch (e) {
      // Ignorar fallas silenciosas de sesión
    }
  }

  // --- NOTIFICACIONES TOAST ---
  function showToast(msg, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    let icon = 'ℹ️';
    if (type.includes('toast-r')) icon = '🔴';
    if (type.includes('toast-s')) icon = '🟢';
    if (type.includes('toast-d')) icon = '🟡';
    if (type.includes('toast-x')) icon = '🟣';
    if (type.includes('error')) icon = '❌';

    toast.innerHTML = `<span>${icon}</span><span>${msg}</span>`;
    dom.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 2400);
  }

  // --- EVENT LISTENERS GENERALES Y ATAJOS ---
  function setupEventListeners() {
    // Botones de Lote
    dom.batchSelect.addEventListener('change', (e) => {
      loadBatch(parseInt(e.target.value));
    });

    dom.btnPrevBatch.addEventListener('click', () => {
      if (state.currentBatchId > 1) loadBatch(state.currentBatchId - 1);
    });

    dom.btnNextBatch.addEventListener('click', () => {
      if (state.currentBatchId < state.totalBatches) loadBatch(state.currentBatchId + 1);
    });

    dom.btnBannerContinueBatch.addEventListener('click', () => {
      if (state.currentBatchId < state.totalBatches) {
        loadBatch(state.currentBatchId + 1);
      } else {
        showToast('¡Has completado el último lote del dataset!', 'info');
      }
    });

    // Filtros
    dom.filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        dom.filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.filter = btn.dataset.filter;
        renderQuickStrip();
        if (state.viewMode === 'gallery') renderGalleryGrid();
      });
    });

    // Cambio de Vista
    dom.btnModeInspect.addEventListener('click', () => switchViewMode('inspect'));
    dom.btnModeGallery.addEventListener('click', () => switchViewMode('gallery'));
    dom.btnGalleryReturnInspect.addEventListener('click', () => switchViewMode('inspect'));

    // Navegación Anterior / Siguiente en Inspector
    dom.btnNavPrev.addEventListener('click', () => {
      if (state.currentBatchIndex > 0) selectImageByIndex(state.currentBatchIndex - 1);
    });

    dom.btnNavNext.addEventListener('click', () => {
      if (state.currentBatchIndex < state.batchItems.length - 1) {
        selectImageByIndex(state.currentBatchIndex + 1);
      }
    });

    // Botones de Acción de Clasificación
    dom.btnActionR.addEventListener('click', () => assignCategory('R'));
    dom.btnActionS.addEventListener('click', () => assignCategory('S'));
    dom.btnActionD.addEventListener('click', () => assignCategory('D'));
    dom.btnActionX.addEventListener('click', () => openDiscardModal());

    // Acciones del Header
    dom.btnUndoHeader.addEventListener('click', performUndo);
    dom.btnOpenProtocol.addEventListener('click', openProtocolModal);
    dom.btnExportHeader.addEventListener('click', openExportModal);

    // Modales: Descarte
    dom.btnCancelDiscard.addEventListener('click', closeDiscardModal);
    dom.btnConfirmDiscard.addEventListener('click', confirmDiscard);

    // Modales: Protocolo
    dom.btnCloseProtocol.addEventListener('click', closeProtocolModal);
    dom.btnOkProtocol.addEventListener('click', closeProtocolModal);

    // Modales: Exportación
    dom.btnCloseExport.addEventListener('click', closeExportModal);
    dom.btnCancelExportDialog.addEventListener('click', closeExportModal);
    dom.btnRunExportAction.addEventListener('click', runExport);

    // ATAJOS DE TECLADO GLOBALES
    window.addEventListener('keydown', (e) => {
      // Si el foco está en un campo de texto, no capturar atajos
      const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
      if (activeTag === 'input' || activeTag === 'textarea') {
        // En modal de descarte, Enter confirma
        if (dom.modalDiscard.style.display === 'flex' && e.key === 'Enter') {
          e.preventDefault();
          confirmDiscard();
        }
        return;
      }

      // Cerrar modales con Escape
      if (e.key === 'Escape') {
        if (dom.modalDiscard.style.display === 'flex') closeDiscardModal();
        if (dom.modalProtocol.style.display === 'flex') closeProtocolModal();
        if (dom.modalExport.style.display === 'flex') closeExportModal();
        return;
      }

      // Enter en modal de descarte
      if (dom.modalDiscard.style.display === 'flex' && e.key === 'Enter') {
        e.preventDefault();
        confirmDiscard();
        return;
      }

      // Si algún modal está abierto, ignorar los otros atajos
      if (dom.modalDiscard.style.display === 'flex' ||
          dom.modalProtocol.style.display === 'flex' ||
          dom.modalExport.style.display === 'flex') {
        return;
      }

      // Atajo Deshacer (Ctrl + Z)
      if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
        e.preventDefault();
        performUndo();
        return;
      }

      // Atajos de Clasificación
      const key = e.key.toUpperCase();
      if (key === 'R') {
        e.preventDefault();
        assignCategory('R');
      } else if (key === 'S') {
        e.preventDefault();
        assignCategory('S');
      } else if (key === 'D') {
        e.preventDefault();
        assignCategory('D');
      } else if (key === 'X') {
        e.preventDefault();
        openDiscardModal();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        if (state.currentBatchIndex > 0) selectImageByIndex(state.currentBatchIndex - 1);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        if (state.currentBatchIndex < state.batchItems.length - 1) {
          selectImageByIndex(state.currentBatchIndex + 1);
        }
      }
    });
  }

  // Iniciar cuando el DOM esté listo
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
