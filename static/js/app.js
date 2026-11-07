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

    // Fase 2: Curación y Balanceo
    activePhase: 'phase1', // 'phase1' | 'phase2'
    phase2Category: 'R', // 'R' | 'S'
    phase2Filter: 'all', // 'all' | 'pending' | 'kept'
    phase2Items: [],
    phase2Index: 0,
    phase2Stats: null,

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
    // Phase Tabs
    tabPhase1: document.getElementById('tab-phase-1'),
    tabPhase2: document.getElementById('tab-phase-2'),
    phase2Bar: document.getElementById('phase2-bar'),
    batchBar: document.getElementById('batch-bar'),

    // Phase 2 Bar Controls
    btnPoolR: document.getElementById('btn-pool-r'),
    btnPoolS: document.getElementById('btn-pool-s'),
    btnPoolD: document.getElementById('btn-pool-d'),
    p2PoolRCount: document.getElementById('p2-pool-r-count'),
    p2PoolSCount: document.getElementById('p2-pool-s-count'),
    p2PoolDCount: document.getElementById('p2-pool-d-count'),
    bGoalVal: document.getElementById('b-goal-val'),
    bDiffVal: document.getElementById('b-diff-val'),
    bRatioVal: document.getElementById('b-ratio-val'),
    bStatusBadge: document.getElementById('b-status-badge'),
    barFillR: document.getElementById('bar-fill-r'),
    barFillS: document.getElementById('bar-fill-s'),
    btnP2ResetRound: document.getElementById('btn-p2-reset-round'),
    p2FilterBtns: document.querySelectorAll('.phase2-filter-group .filter-btn'),

    // Phase 2 Action Card
    phase1ActionCard: document.getElementById('phase1-action-card'),
    phase2ActionCard: document.getElementById('phase2-action-card'),
    phase2CardTitle: document.getElementById('phase2-card-title'),
    phase2ShortcutTip: document.getElementById('phase2-shortcut-tip'),
    phase2CurationGrid: document.getElementById('phase2-curation-grid'),
    phase2DudosaGrid: document.getElementById('phase2-dudosa-grid'),
    btnP2Keep: document.getElementById('btn-p2-keep'),
    btnP2Transfer: document.getElementById('btn-p2-transfer'),
    btnP2Discard: document.getElementById('btn-p2-discard'),
    btnP2ToR: document.getElementById('btn-p2-to-r'),
    btnP2ToS: document.getElementById('btn-p2-to-s'),
    btnP2DiscardD: document.getElementById('btn-p2-discard-d'),
    btnP2KeepD: document.getElementById('btn-p2-keep-d'),
    btnP2Undo: document.getElementById('btn-p2-undo'),
    inputPhase2Note: document.getElementById('input-phase2-note'),
    chkPhase2AutoAdvance: document.getElementById('chk-phase2-auto-advance'),
    balanceHintTitle: document.getElementById('balance-hint-title'),
    balanceHintDesc: document.getElementById('balance-hint-desc'),

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
    if (state.activePhase === 'phase2') {
      await switchPhase('phase2');
    } else {
      await loadBatch(state.currentBatchId);
    }
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

      if (data.session) {
        if (data.session.current_batch_id) {
          state.currentBatchId = data.session.current_batch_id;
          dom.batchSelect.value = state.currentBatchId;
        }
        if (data.session.active_phase) {
          state.activePhase = data.session.active_phase;
        } else if (data.total_reviewed >= data.total_images) {
          state.activePhase = 'phase2';
        }
        if (data.session.phase2_category) {
          state.phase2Category = data.session.phase2_category;
        }
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
      if (cat === 'X') label = decision.reason ? `X — DESCARTADA (${decision.reason})` : 'X — DESCARTADA';
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

  let activeImageLoader = null;

  function loadMainImage(url) {
    dom.imageLoadingOverlay.style.display = 'flex';
    if (activeImageLoader) {
      activeImageLoader.onload = null;
      activeImageLoader.onerror = null;
      activeImageLoader.src = '';
    }
    const img = new Image();
    activeImageLoader = img;
    img.onload = () => {
      if (activeImageLoader !== img) return;
      dom.mainInspectImage.src = url;
      dom.imageLoadingOverlay.style.display = 'none';
      resetTransform();
      activeImageLoader = null;
    };
    img.onerror = () => {
      if (activeImageLoader !== img) return;
      dom.imageLoadingOverlay.style.display = 'none';
      showToast('Error al cargar la imagen', 'error');
      activeImageLoader = null;
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
    if (state.activePhase === 'phase2') {
      renderPhase2QuickStrip();
      return;
    }
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

  // --- AVANCE AUTOMÁTICO Y STATS DE LOTE ---
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

  // =========================================================================
  // --- FASE 2: CURACIÓN Y BALANCEO R VS S ---
  // =========================================================================

  async function switchPhase(phase) {
    state.activePhase = phase;
    if (phase === 'phase2') {
      dom.tabPhase1.classList.remove('active');
      dom.tabPhase2.classList.add('active');
      dom.batchBar.style.display = 'none';
      dom.phase2Bar.style.display = 'flex';
      dom.phase1ActionCard.style.display = 'none';
      dom.phase2ActionCard.style.display = 'block';
      dom.btnModeGallery.style.display = 'none';
      switchViewMode('inspect');
      await loadPhase2Pool(state.phase2Category, state.phase2Filter);
    } else {
      dom.tabPhase1.classList.add('active');
      dom.tabPhase2.classList.remove('active');
      dom.batchBar.style.display = 'flex';
      dom.phase2Bar.style.display = 'none';
      dom.phase1ActionCard.style.display = 'block';
      dom.phase2ActionCard.style.display = 'none';
      dom.btnModeGallery.style.display = 'block';
      await loadBatch(state.currentBatchId);
    }
    saveSessionState();
  }

  function updatePoolButtonsUI(cat) {
    if (dom.btnPoolR) dom.btnPoolR.classList.toggle('active', cat === 'R');
    if (dom.btnPoolS) dom.btnPoolS.classList.toggle('active', cat === 'S');
    if (dom.btnPoolD) dom.btnPoolD.classList.toggle('active', cat === 'D');
  }

  async function loadPhase2Pool(category = 'R', filter = 'all', targetImageId = null) {
    try {
      dom.imageLoadingOverlay.style.display = 'flex';
      state.phase2Category = category;
      state.phase2Filter = filter;
      updatePoolButtonsUI(category);

      const res = await fetch(`/api/phase2/pool?category=${encodeURIComponent(category)}&filter=${encodeURIComponent(filter)}`);
      if (!res.ok) throw new Error(`Error al cargar pool ${category}`);
      const data = await res.json();

      state.phase2Items = data.items;
      state.phase2Stats = data.stats;

      updatePhase2Stats(data.stats);

      if (state.phase2Category === 'D') {
        if (dom.phase2CurationGrid) dom.phase2CurationGrid.style.display = 'none';
        if (dom.phase2DudosaGrid) dom.phase2DudosaGrid.style.display = 'flex';
        if (dom.phase2CardTitle) dom.phase2CardTitle.textContent = 'Resolución de Dudosas (D)';
        if (dom.phase2ShortcutTip) dom.phase2ShortcutTip.textContent = '[R] Con Defecto • [S] Sin Defecto • [X] Descartar • [M] Mantener';
      } else {
        if (dom.phase2CurationGrid) dom.phase2CurationGrid.style.display = 'flex';
        if (dom.phase2DudosaGrid) dom.phase2DudosaGrid.style.display = 'none';
        if (dom.phase2CardTitle) dom.phase2CardTitle.textContent = 'Curación de Fase 2';
        if (dom.phase2ShortcutTip) dom.phase2ShortcutTip.textContent = '[M] Mantener • [S/C] Mover • [X] Descartar';
        updatePhase2TransferButton();
      }

      // Seleccionar imagen inicial
      let initialIndex = 0;
      if (targetImageId) {
        const foundIdx = state.phase2Items.findIndex(it => it.image_id === targetImageId);
        if (foundIdx !== -1) initialIndex = foundIdx;
      } else {
        const firstPending = state.phase2Items.findIndex(it => !it.phase2_reviewed);
        if (firstPending !== -1) initialIndex = firstPending;
      }

      state.phase2Index = initialIndex;

      // Renderizar tira rápida de fase 2 centrada en la imagen activa
      renderPhase2QuickStrip();

      if (state.phase2Items.length > 0) {
        selectPhase2ImageByIndex(initialIndex);
      } else {
        dom.currentBadgeIndex.textContent = `0 / 0 [Pool ${category}]`;
        dom.currentImageName.textContent = 'No hay imágenes en este filtro';
        dom.currentCategoryBadge.textContent = 'VACÍO';
        dom.mainInspectImage.src = '';
      }

      saveSessionState();
    } catch (e) {
      console.error(e);
      showToast(`Error: ${e.message}`, 'error');
    } finally {
      dom.imageLoadingOverlay.style.display = 'none';
    }
  }

  function updatePhase2TransferButton() {
    if (!dom.btnP2Transfer) return;
    const isR = state.phase2Category === 'R';
    const targetCat = isR ? 'S' : 'R';
    const targetTitle = isR ? 'PASAR A SIN DEFECTO (S)' : 'PASAR A CON DEFECTO (R)';
    const targetDesc = isR ? 'Reclasificar como sana y transferir a Pool S' : 'Reclasificar con defecto y transferir a Pool R';
    const shortcutKey = isR ? 'S' : 'R';

    const titleEl = dom.btnP2Transfer.querySelector('.btn-title');
    const descEl = dom.btnP2Transfer.querySelector('.btn-desc');
    const shortcutEl = dom.btnP2Transfer.querySelector('.key-shortcut');

    if (titleEl) titleEl.textContent = targetTitle;
    if (descEl) descEl.textContent = targetDesc;
    if (shortcutEl) {
      shortcutEl.textContent = shortcutKey;
      shortcutEl.className = `key-shortcut shortcut-${targetCat.toLowerCase()}`;
    }
    dom.btnP2Transfer.title = `Presiona [${shortcutKey}] o [C] para mover a ${isR ? 'Sin Defecto' : 'Con Defecto'}`;
  }

  function updatePhase2Stats(stats) {
    if (!stats) return;

    dom.p2PoolRCount.textContent = `${stats.total_r.toLocaleString()} fotos`;
    dom.p2PoolSCount.textContent = `${stats.total_s.toLocaleString()} fotos`;
    if (dom.p2PoolDCount && stats.total_d !== undefined) {
      dom.p2PoolDCount.textContent = `${stats.total_d.toLocaleString()} fotos`;
    }

    const goal = stats.target_goal || 1500;
    if (dom.bGoalVal) {
      dom.bGoalVal.textContent = `${goal.toLocaleString()} R / ${goal.toLocaleString()} S`;
    }

    // Diferencia y Ratio
    if (stats.difference > 0) {
      dom.bDiffVal.textContent = `+${stats.difference.toLocaleString()} R`;
      dom.bDiffVal.className = 'b-val highlight-diff';
    } else if (stats.difference < 0) {
      dom.bDiffVal.textContent = `+${Math.abs(stats.difference).toLocaleString()} S`;
      dom.bDiffVal.className = 'b-val highlight-diff';
    } else {
      dom.bDiffVal.textContent = '0 (1:1 Exacto)';
      dom.bDiffVal.className = 'b-val';
    }

    const pctR = stats.pct_r !== undefined ? stats.pct_r : 50;
    const pctS = stats.pct_s !== undefined ? stats.pct_s : 50;
    dom.bRatioVal.textContent = `${pctR}% R / ${pctS}% S`;

    dom.barFillR.style.width = `${pctR}%`;
    dom.barFillS.style.width = `${pctS}%`;

    const surplusR = stats.surplus_r !== undefined ? stats.surplus_r : Math.max(0, stats.total_r - goal);
    const surplusS = stats.surplus_s !== undefined ? stats.surplus_s : Math.max(0, stats.total_s - goal);
    const isGoalReached = (stats.total_r === goal && stats.total_s === goal);

    // Status Badge & Hint hacia la meta de 1,500
    if (state.phase2Category === 'D') {
      const dTotal = stats.total_d !== undefined ? stats.total_d : (state.phase2Items ? state.phase2Items.length : 0);
      dom.bStatusBadge.textContent = `🟡 Revisando Dudosas: ${dTotal.toLocaleString()} fotos`;
      dom.bStatusBadge.classList.remove('is-perfect');
      dom.balanceHintTitle.textContent = `Resolución de Imágenes Dudosas (${dTotal.toLocaleString()} restantes)`;
      dom.balanceHintDesc.textContent = `Asigna cada duda a Con Defecto [R] o Sin Defecto [S] para balancear las clases (meta: 1,500 por grupo), o descártala [X] si no es aprovechable.`;
    } else if (isGoalReached) {
      dom.bStatusBadge.textContent = `🎉 ¡Meta de ${goal.toLocaleString()} por grupo alcanzada!`;
      dom.bStatusBadge.classList.add('is-perfect');
      dom.balanceHintTitle.textContent = `¡Dataset Equilibrado a ${goal.toLocaleString()} por Grupo!`;
      dom.balanceHintDesc.textContent = `Hay exactamente ${stats.total_r.toLocaleString()} fotos en R y ${stats.total_s.toLocaleString()} en S (Total: ${(goal * 2).toLocaleString()} fotos listas para YOLO).`;
    } else {
      dom.bStatusBadge.classList.remove('is-perfect');
      const isR = state.phase2Category === 'R';
      const curPoolCount = isR ? stats.total_r : stats.total_s;
      const curSurplus = isR ? surplusR : surplusS;
      const poolLetter = isR ? 'R' : 'S';

      if (curSurplus > 0) {
        dom.bStatusBadge.textContent = `🎯 Pool ${poolLetter}: Sobran ${curSurplus.toLocaleString()} fotos`;
        dom.balanceHintTitle.textContent = `Meta Pool ${poolLetter}: Llegar a ${goal.toLocaleString()} fotos`;
        dom.balanceHintDesc.textContent = `Tienes ${curPoolCount.toLocaleString()} fotos en ${poolLetter}. Sobran ${curSurplus.toLocaleString()} fotos para descartar o transferir hasta alcanzar ${goal.toLocaleString()}.`;
      } else if (curPoolCount < goal) {
        const needed = goal - curPoolCount;
        dom.bStatusBadge.textContent = `🎯 Pool ${poolLetter}: Faltan ${needed.toLocaleString()} fotos`;
        dom.balanceHintTitle.textContent = `Meta Pool ${poolLetter}: ${goal.toLocaleString()} fotos`;
        dom.balanceHintDesc.textContent = `Tienes ${curPoolCount.toLocaleString()} fotos en ${poolLetter} (faltan ${needed.toLocaleString()} para la meta). Transfiere fotos mal clasificadas desde el otro pool.`;
      } else {
        dom.bStatusBadge.textContent = `✓ Pool ${poolLetter}: ${goal.toLocaleString()} fotos exactas`;
        dom.balanceHintTitle.textContent = `¡Pool ${poolLetter} completado en ${goal.toLocaleString()}!`;
        dom.balanceHintDesc.textContent = `Este grupo ya tiene exactamente la cuota de ${goal.toLocaleString()} fotos. Revisa el otro grupo para completar el balance 1:1.`;
      }
    }
  }

  function selectPhase2ImageByIndex(index) {
    if (!state.phase2Items || state.phase2Items.length === 0) return;
    if (index < 0) index = 0;
    if (index >= state.phase2Items.length) index = state.phase2Items.length - 1;

    state.phase2Index = index;
    const item = state.phase2Items[index];
    state.currentImage = item;

    dom.currentBadgeIndex.textContent = `#${index + 1} / ${state.phase2Items.length} [Pool ${state.phase2Category}]`;
    dom.currentImageName.textContent = item.filename;

    updatePhase2Badge(item);

    // Metadatos
    dom.metaFruitId.textContent = item.fruit_id;
    dom.metaStorageGroup.textContent = item.storage_group;
    dom.metaDay.textContent = `Día ${item.day}`;
    dom.metaView.textContent = `Vista ${item.view.toUpperCase()}`;
    dom.metaRipening.textContent = `Estadío ${item.ripening_stage}`;
    dom.metaTimestamp.textContent = item.time_stamp || 'N/A';

    dom.inputPhase2Note.value = item.decision ? (item.decision.note || '') : '';

    loadMainImage(`/api/image/${encodeURIComponent(item.image_id)}`);
    highlightQuickStripActive(item.image_id);
    loadFruitComparison(item.fruit_id, item.image_id);
    saveSessionState();
  }

  function updatePhase2Badge(item) {
    dom.currentCategoryBadge.className = 'badge-status-current';
    const isKept = item && ((item.phase2_reviewed && item.phase2_action === 'kept') || (item.decision && item.decision.phase2_reviewed && item.decision.phase2_action === 'kept'));
    if (isKept) {
      dom.currentCategoryBadge.classList.add(`is-${state.phase2Category.toLowerCase()}`);
      dom.currentCategoryBadge.textContent = state.phase2Category === 'D' ? '✓ REVISADA (DUDOSA)' : `✓ MANTENIDA (${state.phase2Category})`;
    } else {
      dom.currentCategoryBadge.classList.add('is-pending');
      dom.currentCategoryBadge.textContent = state.phase2Category === 'D' ? 'DUDOSA POR RESOLVER (D)' : `POR REVISAR (${state.phase2Category})`;
    }
  }

  const PHASE2_STRIP_WINDOW = 40;

  function renderPhase2QuickStrip() {
    dom.batchQuickStrip.innerHTML = '';
    if (!state.phase2Items || state.phase2Items.length === 0) return;

    const total = state.phase2Items.length;
    const current = Math.min(Math.max(0, state.phase2Index || 0), total - 1);
    const half = Math.floor(PHASE2_STRIP_WINDOW / 2);

    let start = Math.max(0, current - half);
    let end = Math.min(total, start + PHASE2_STRIP_WINDOW);
    if (end - start < PHASE2_STRIP_WINDOW) {
      start = Math.max(0, end - PHASE2_STRIP_WINDOW);
    }

    const fragment = document.createDocumentFragment();

    for (let idx = start; idx < end; idx++) {
      const item = state.phase2Items[idx];
      const div = document.createElement('div');
      div.className = 'quick-thumb';
      div.id = `qthumb-${item.global_index}`;
      div.title = `${item.filename} (#${idx + 1} de ${total})`;

      if (idx === current) {
        div.classList.add('active');
      }

      const isKept = (item.phase2_reviewed && item.phase2_action === 'kept') ||
                     (item.decision && item.decision.phase2_reviewed && item.decision.phase2_action === 'kept');
      if (isKept) {
        div.classList.add('is-kept');
      } else {
        div.classList.add(`is-${state.phase2Category.toLowerCase()}`);
        div.classList.add('is-pending');
      }

      const img = document.createElement('img');
      img.loading = 'lazy';
      img.src = `/api/thumbnail/${encodeURIComponent(item.image_id)}`;
      img.alt = item.filename;

      div.appendChild(img);
      const targetIdx = idx;
      div.addEventListener('click', () => {
        selectPhase2ImageByIndex(targetIdx);
      });

      fragment.appendChild(div);
    }

    dom.batchQuickStrip.appendChild(fragment);

    const activeThumb = dom.batchQuickStrip.querySelector('.quick-thumb.active');
    if (activeThumb) {
      activeThumb.scrollIntoView({ behavior: 'auto', block: 'nearest', inline: 'center' });
    }
  }

  async function performPhase2Action(action, targetCategory = null) {
    if (!state.currentImage || state.isSaving) return;
    state.isSaving = true;

    const currentItem = state.currentImage;
    const imageId = currentItem.image_id;
    const note = dom.inputPhase2Note.value.trim();

    try {
      let resolvedTargetCat = targetCategory;
      if (action === 'transfer' && !resolvedTargetCat) {
        resolvedTargetCat = state.phase2Category === 'R' ? 'S' : 'R';
      }

      const res = await fetch('/api/phase2/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_id: imageId,
          action: action,
          target_category: resolvedTargetCat,
          category: state.phase2Category,
          note: note
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Error al ejecutar acción');

      if (action === 'keep') {
        const poolMsg = state.phase2Category === 'D' ? 'Dudosas (D)' : `Pool ${state.phase2Category}`;
        showToast(`✓ Mantenida: ${currentItem.filename} en ${poolMsg}`, `toast-${state.phase2Category.toLowerCase()}`);
        currentItem.phase2_reviewed = true;
        currentItem.phase2_action = 'kept';
        if (currentItem.decision) {
          currentItem.decision.phase2_reviewed = true;
          currentItem.decision.phase2_action = 'kept';
        }
      } else if (action === 'transfer') {
        const targetName = resolvedTargetCat === 'S' ? 'Sin Defecto (S)' : 'Con Defecto (R)';
        showToast(`🔄 Reclasificada: ${currentItem.filename} asignada a ${targetName}`, `toast-${resolvedTargetCat.toLowerCase()}`);
        state.phase2Items = state.phase2Items.filter(it => it.image_id !== imageId);
      } else if (action === 'discard') {
        showToast(`🗑️ Descartada: ${currentItem.filename} -> Grupo general de descartadas`, 'toast-x');
        state.phase2Items = state.phase2Items.filter(it => it.image_id !== imageId);
      }

      updatePhase2Stats(data.stats);

      // Avance a la siguiente foto
      const autoAdvance = !dom.chkPhase2AutoAdvance || dom.chkPhase2AutoAdvance.checked;
      if (autoAdvance) {
        if (action === 'discard' || action === 'transfer') {
          if (state.phase2Index >= state.phase2Items.length) {
            state.phase2Index = Math.max(0, state.phase2Items.length - 1);
          }
          if (state.phase2Items.length > 0) {
            selectPhase2ImageByIndex(state.phase2Index);
          } else {
            showToast(`¡No quedan más imágenes en el Pool ${state.phase2Category}!`, 'info');
          }
        } else {
          if (state.phase2Index < state.phase2Items.length - 1) {
            selectPhase2ImageByIndex(state.phase2Index + 1);
          } else {
            showToast(`¡Has llegado al final del Pool ${state.phase2Category}!`, 'info');
          }
        }
      } else {
        if (action === 'discard' || action === 'transfer') {
          if (state.phase2Index >= state.phase2Items.length) {
            state.phase2Index = Math.max(0, state.phase2Items.length - 1);
          }
          if (state.phase2Items.length > 0) {
            selectPhase2ImageByIndex(state.phase2Index);
          }
        } else {
          updatePhase2Badge(currentItem);
        }
      }

      // Actualizar estado global sin bloquear la interfaz
      loadGlobalStatus().catch(() => {});
    } catch (e) {
      console.error(e);
      showToast(`Error: ${e.message}`, 'error');
    } finally {
      state.isSaving = false;
    }
  }

  // --- DESHACER (UNDO) ---
  async function performUndo(steps = 1) {
    if (state.isUndoing || state.isSaving) return;
    state.isUndoing = true;
    try {
      const cleanSteps = (typeof steps === 'number' && !isNaN(steps) && steps >= 1) ? Math.floor(steps) : 1;
      const res = await fetch('/api/undo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps: cleanSteps })
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `Error ${res.status} del servidor`);
      }
      const data = await res.json();

      if (data.status === 'empty') {
        showToast('No hay más acciones para deshacer', 'info');
        return;
      }

      const countMsg = data.undone_count > 1 ? `${data.undone_count} acciones deshechas` : `Acción deshecha en ${data.image_id}`;
      const remainMsg = data.remaining_undo_count !== undefined ? ` (Disponibles: ${data.remaining_undo_count})` : '';
      showToast(`↺ ${countMsg}${remainMsg}`, 'info');

      // Recargar lote o pool de Fase 2 y estado global
      if (state.activePhase === 'phase2') {
        const targetPool = (data.restored_state && ['R', 'S', 'D'].includes(data.restored_state.category))
          ? data.restored_state.category
          : state.phase2Category;
        if (state.phase2Category !== targetPool) {
          state.phase2Category = targetPool;
          updatePoolButtonsUI(targetPool);
        }
        await loadPhase2Pool(state.phase2Category, state.phase2Filter, data.image_id);
      } else {
        await loadBatch(state.currentBatchId, data.image_id);
      }
      loadGlobalStatus().catch(() => {});
    } catch (e) {
      console.error(e);
      showToast(`Error al deshacer: ${e.message}`, 'error');
    } finally {
      state.isUndoing = false;
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
      const payload = {
        active_phase: state.activePhase,
        active_filter: state.filter
      };
      if (state.activePhase === 'phase2') {
        payload.phase2_category = state.phase2Category;
        payload.phase2_image_id = state.currentImage ? state.currentImage.image_id : null;
      } else {
        payload.batch_id = state.currentBatchId;
        payload.image_id = state.currentImage ? state.currentImage.image_id : null;
      }

      await fetch('/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
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
    // Pestañas de Navegación de Fase
    if (dom.tabPhase1) {
      dom.tabPhase1.addEventListener('click', () => switchPhase('phase1'));
    }
    if (dom.tabPhase2) {
      dom.tabPhase2.addEventListener('click', () => switchPhase('phase2'));
    }

    // Selectores de Pool de Fase 2
    if (dom.btnPoolR) {
      dom.btnPoolR.addEventListener('click', () => {
        state.phase2Category = 'R';
        updatePoolButtonsUI('R');
        loadPhase2Pool('R', state.phase2Filter);
      });
    }
    if (dom.btnPoolS) {
      dom.btnPoolS.addEventListener('click', () => {
        state.phase2Category = 'S';
        updatePoolButtonsUI('S');
        loadPhase2Pool('S', state.phase2Filter);
      });
    }
    if (dom.btnPoolD) {
      dom.btnPoolD.addEventListener('click', () => {
        state.phase2Category = 'D';
        updatePoolButtonsUI('D');
        loadPhase2Pool('D', state.phase2Filter);
      });
    }

    // Filtros de Pool en Fase 2
    dom.p2FilterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        dom.p2FilterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.phase2Filter = btn.dataset.p2filter || 'all';
        loadPhase2Pool(state.phase2Category, state.phase2Filter);
      });
    });

    // Botones de Decisión de Fase 2 (MANTENER / TRANSFERIR / DESCARTAR)
    if (dom.btnP2Keep) {
      dom.btnP2Keep.addEventListener('click', () => performPhase2Action('keep'));
    }
    if (dom.btnP2Transfer) {
      dom.btnP2Transfer.addEventListener('click', () => performPhase2Action('transfer'));
    }
    if (dom.btnP2Discard) {
      dom.btnP2Discard.addEventListener('click', () => performPhase2Action('discard'));
    }
    if (dom.btnP2ToR) {
      dom.btnP2ToR.addEventListener('click', () => performPhase2Action('transfer', 'R'));
    }
    if (dom.btnP2ToS) {
      dom.btnP2ToS.addEventListener('click', () => performPhase2Action('transfer', 'S'));
    }
    if (dom.btnP2DiscardD) {
      dom.btnP2DiscardD.addEventListener('click', () => performPhase2Action('discard'));
    }
    if (dom.btnP2KeepD) {
      dom.btnP2KeepD.addEventListener('click', () => performPhase2Action('keep'));
    }
    if (dom.btnP2Undo) {
      dom.btnP2Undo.addEventListener('click', () => performUndo(1));
    }
    if (dom.btnP2ResetRound) {
      dom.btnP2ResetRound.addEventListener('click', async () => {
        let catName = 'Con Defecto (R)';
        let curCount = dom.p2PoolRCount.textContent;
        if (state.phase2Category === 'S') {
          catName = 'Sin Defecto (S)';
          curCount = dom.p2PoolSCount.textContent;
        } else if (state.phase2Category === 'D') {
          catName = 'Dudosas (D)';
          curCount = dom.p2PoolDCount ? dom.p2PoolDCount.textContent : '293 fotos';
        }
        const ok = confirm(`¿Iniciar una nueva ronda de repaso para el grupo ${catName} (${curCount})?\n\nLas fotos que ya descartaste o transferiste se mantendrán de forma segura. Esta acción habilitará todas las fotos activas restantes para que puedas revisarlas desde la foto #1.`);
        if (!ok) return;

        try {
          const res = await fetch('/api/phase2/reset_round', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category: state.phase2Category })
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || 'Error al reiniciar ronda');

          showToast(`🔄 Nueva ronda iniciada: ${data.result.reset_count} fotos listas para repasar`, 'info');
          await loadPhase2Pool(state.phase2Category, 'all');
        } catch (e) {
          console.error(e);
          showToast(`Error al iniciar nueva ronda: ${e.message}`, 'error');
        }
      });
    }

    // Botones de Lote (Fase 1)
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
      if (state.activePhase === 'phase2') {
        if (state.phase2Index > 0) selectPhase2ImageByIndex(state.phase2Index - 1);
      } else {
        if (state.currentBatchIndex > 0) selectImageByIndex(state.currentBatchIndex - 1);
      }
    });

    dom.btnNavNext.addEventListener('click', () => {
      if (state.activePhase === 'phase2') {
        if (state.phase2Index < state.phase2Items.length - 1) {
          selectPhase2ImageByIndex(state.phase2Index + 1);
        }
      } else {
        if (state.currentBatchIndex < state.batchItems.length - 1) {
          selectImageByIndex(state.currentBatchIndex + 1);
        }
      }
    });

    // Botones de Acción de Clasificación
    dom.btnActionR.addEventListener('click', () => assignCategory('R'));
    dom.btnActionS.addEventListener('click', () => assignCategory('S'));
    dom.btnActionD.addEventListener('click', () => assignCategory('D'));
    dom.btnActionX.addEventListener('click', () => assignCategory('X'));

    // Acciones del Header
    dom.btnUndoHeader.addEventListener('click', () => performUndo(1));
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

      // Evitar auto-repetición continua al mantener presionadas teclas de acción
      // (evita descartar o clasificar 2 a 5 imágenes accidentalmente por repetición de teclado)
      if (e.repeat && ['r', 's', 'd', 'x', 'm', 'c', 'enter', ' ', 'delete', 'backspace', 'z'].includes(e.key.toLowerCase())) {
        e.preventDefault();
        return;
      }

      // Atajo Deshacer (Ctrl + Z)
      if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
        e.preventDefault();
        performUndo();
        return;
      }

      // ATAJOS ESPECÍFICOS SEGÚN FASE ACTIVA
      const key = e.key.toUpperCase();

      if (state.activePhase === 'phase2') {
        if (state.phase2Category === 'D') {
          // Atajos específicos para Pool D (Resolución de Dudosas)
          if (key === 'R') {
            e.preventDefault();
            performPhase2Action('transfer', 'R');
          } else if (key === 'S') {
            e.preventDefault();
            performPhase2Action('transfer', 'S');
          } else if (key === 'X' || key === 'DELETE') {
            e.preventDefault();
            performPhase2Action('discard');
          } else if (key === 'M' || key === 'D' || key === 'ENTER' || e.code === 'Space') {
            e.preventDefault();
            performPhase2Action('keep');
          } else if (e.key === 'ArrowLeft') {
            e.preventDefault();
            if (state.phase2Index > 0) selectPhase2ImageByIndex(state.phase2Index - 1);
          } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            if (state.phase2Index < state.phase2Items.length - 1) {
              selectPhase2ImageByIndex(state.phase2Index + 1);
            }
          }
          return;
        }

        // Atajos de Fase 2 para Pool R y S: Mantener, Mover de Grupo y Descartar
        if (key === 'M' || key === 'ENTER' || e.code === 'Space') {
          e.preventDefault();
          performPhase2Action('keep');
        } else if (key === 'X' || key === 'DELETE') {
          e.preventDefault();
          performPhase2Action('discard');
        } else if (key === 'C' || (state.phase2Category === 'R' && key === 'S') || (state.phase2Category === 'S' && key === 'R')) {
          e.preventDefault();
          performPhase2Action('transfer');
        } else if (e.key === 'ArrowLeft') {
          e.preventDefault();
          if (state.phase2Index > 0) selectPhase2ImageByIndex(state.phase2Index - 1);
        } else if (e.key === 'ArrowRight') {
          e.preventDefault();
          if (state.phase2Index < state.phase2Items.length - 1) {
            selectPhase2ImageByIndex(state.phase2Index + 1);
          }
        }
        return;
      }

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
        assignCategory('X');
      } else if (key === 'ArrowLeft') {
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
