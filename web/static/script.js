// --- State & Utility ---
let state = {
  bills: [], vendors: [], categories: [],
  queue: [], currentQueueId: null, queueProcessing: false,
  checkedBillIds: new Set(),
};

async function api(url, options = {}) {
  try {
    const res = await fetch(url, options);
    return await res.json();
  } catch (err) {
    console.error("API Error:", err);
    return { success: false, error: err.message };
  }
}

function showToast(msg, isError = false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.backgroundColor = isError ? 'var(--danger)' : 'var(--primary)';
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// --- Routing & UI State ---
document.querySelectorAll('.nav-item').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelectorAll('.nav-item, .view').forEach(el => el.classList.remove('active'));
    e.target.classList.add('active');

    const target = e.target.getAttribute('data-target');
    document.getElementById(`view-${target}`).classList.add('active');

    const fetchMap = { receipts: fetchBills, categories: fetchCategories, vendors: fetchVendors, add: populateAddForm };
    if (fetchMap[target]) fetchMap[target]();
  });
});

function switchTab(tabId) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
  document.querySelector(`.tab[onclick*="${tabId}"]`).classList.add('active');
  document.getElementById(`tab-${tabId}`).style.display = 'block';
}

// --- Data Fetching & Rendering ---
// Bills: see fetchBills() further below, which owns the #bills-table
// rendering (row checkboxes + bulk delete + click-to-edit modal).

// Generic List & Dropdown Functions
function renderList(containerId, items, labelKey, delFnName) {
  document.getElementById(containerId).innerHTML = items.map(i => `
    <div class="list-item">
      <span>${i[labelKey]}</span>
      <button class="btn-danger-sm" onclick="${delFnName}(${i.id})">Delete</button>
    </div>
  `).join('');
}

function populateDropdown(selectId, items, labelKey, defaultText) {
  document.getElementById(selectId).innerHTML = `<option value="">${defaultText}</option>` + 
    items.map(i => `<option value="${i.id}">${i[labelKey]}</option>`).join('');
}

// Vendors & Categories Shared Logic
async function fetchData(type, stateKey, listId, selectId, labelKey, delFnName, defaultText) {
  const data = await api(`/api/${type}`);
  state[stateKey] = data;
  renderList(listId, data, labelKey, delFnName);
  populateDropdown(selectId, data, labelKey, defaultText);
}

const fetchVendors = () => fetchData('vendors', 'vendors', 'vendor-list', 'filter-vendor', 'name', 'deleteVendor', 'All Vendors');
const fetchCategories = () => fetchData('categories', 'categories', 'category-list', 'filter-category', 'category_name', 'deleteCategory', 'All Categories');

async function addEntity(type, inputId, label, fetchFn) {
  const input = document.getElementById(inputId);
  const name = input.value.trim();
  if (!name) return;
  await api(`/api/${type}`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ name }) });
  input.value = '';
  fetchFn();
  showToast(`${label} ${name} added`);
}

const addVendor = () => addEntity('vendors', 'new-vendor-name', 'Vendor', fetchVendors);
const addCategory = () => addEntity('categories', 'new-cat-name', 'Category', fetchCategories);

async function deleteEntity(type, id, fetchFn) {
  await api(`/api/${type}/${id}`, { method: 'DELETE' });
  fetchFn();
  fetchBills();
}

const deleteVendor = id => deleteEntity('vendors', id, fetchVendors);
const deleteCategory = id => deleteEntity('categories', id, fetchCategories);

// --- Forms & Receipts ---
async function populateAddForm() {
  captureCurrentEdits();
  await Promise.all([fetchVendors(), fetchCategories()]);
  const catsHTML = state.categories.map(c => `<label><input type="checkbox" value="${c.id}"> ${c.category_name}</label>`).join('');
  document.getElementById('add-categories').innerHTML = catsHTML;
  document.getElementById('ocr-categories').innerHTML = catsHTML;
  document.getElementById('add-date').valueAsDate = new Date();
  renderEditor();
}

async function getOrCreateVendorId(name) {
  const existing = state.vendors.find(v => v.name.toLowerCase() === name.toLowerCase());
  if (existing) return existing.id;
  const res = await api('/api/vendors', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ name }) });
  await fetchVendors(); // Refresh UI lists automatically
  return res.id;
}

// Unified Receipt Submission Logic
async function processReceiptSubmission(prefix, successCallback, imagePath = null) {
  const vendorInputId = prefix === 'add' ? 'add-vendor-name' : 'ocr-vendor';
  const vendorName = document.getElementById(vendorInputId).value.trim();
  const price = document.getElementById(`${prefix}-price`).value;
  const date = document.getElementById(`${prefix}-date`).value;
  const cats = Array.from(document.querySelectorAll(`#${prefix}-categories input:checked`)).map(cb => parseInt(cb.value));

  if (!vendorName || !price || !date) return showToast('Fill all required fields', true);

  const vId = await getOrCreateVendorId(vendorName);
  const res = await api('/api/bills', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      vendor_id: vId,
      price,
      date,
      category_ids: cats,
      image_path: imagePath   // <-- include image path if provided
    })
  });

  if (res.success === false) return showToast(res.error || 'Failed to save receipt', true);
  successCallback(vendorName, price, date, cats);
}

function saveManualReceipt() {
  processReceiptSubmission('add', () => {
    showToast('Receipt saved!');
    document.getElementById('add-vendor-name').value = '';
    document.getElementById('add-price').value = '';
    document.querySelectorAll('#add-categories input').forEach(cb => cb.checked = false);
  });
}

function saveOCRReceipt() {
  const item = state.queue.find(q => q.id === state.currentQueueId);
  const imagePath = (item && item.result && item.result.image_path) ? item.result.image_path : null;
  
  processReceiptSubmission('ocr', (vendorName, price, date, cats) => {
    if (item) {
      item.saved = true;
      item.edited = { vendor: vendorName, price, date, categoryIds: cats };
    }
    showToast(item ? `Saved "${item.name}"!` : 'Receipt saved!');
    renderQueue();

    // Auto-advance logic
    if (item) {
      const idx = state.queue.findIndex(q => q.id === item.id);
      const next = state.queue.slice(idx + 1).find(q => !q.saved);
      if (next) selectQueueItem(next.id); else renderEditor();
    } else {
      renderEditor();
    }
  }, imagePath);   // <-- pass image path
}

// --- OCR Batch Queue ---
let queueIdCounter = 0;

function handleFileSelect(event) {
  const files = Array.from(event.target.files || []);
  event.target.value = ''; // Allow re-selecting identical files later
  addFilesToQueue(files);
}

function addFilesToQueue(files) {
  if (!files.length) return;
  if (files.length > 25) showToast(`Queued ${files.length} images - this may take a while.`);

  files.forEach(file => {
    state.queue.push({
      id: ++queueIdCounter, file, name: file.name,
      previewUrl: URL.createObjectURL(file),
      status: 'pending', result: null, error: null, edited: null, saved: false,
    });
  });

  renderQueue();
  if (state.currentQueueId === null) selectQueueItem(state.queue[0].id);
  processQueue();
}

function initDropzone() {
  const zone = document.getElementById('ocr-dropzone');
  if (!zone) return;

  ['dragenter', 'dragover'].forEach(evt => zone.addEventListener(evt, e => {
    e.preventDefault();
    e.stopPropagation();
    zone.classList.add('drag-active');
  }));

  ['dragleave', 'drop'].forEach(evt => zone.addEventListener(evt, e => {
    e.preventDefault();
    e.stopPropagation();
    zone.classList.remove('drag-active');
  }));

  zone.addEventListener('drop', e => {
    const files = Array.from(e.dataTransfer?.files || []).filter(f => f.type.startsWith('image/'));
    addFilesToQueue(files);
  });
}

async function processQueue() {
  if (state.queueProcessing) return;
  state.queueProcessing = true;
  for (const item of state.queue) {
    if (item.status === 'pending') await scanQueueItem(item);
  }
  state.queueProcessing = false;
}

async function scanQueueItem(item) {
  item.status = 'scanning';
  item.error = null;
  updateQueueAndEditor(item.id);

  try {
    const formData = new FormData();
    formData.append('image', item.file);
    const res = await fetch('/api/scan', { method: 'POST', body: formData });
    const data = await res.json();
    
    if (data.error) {
      item.status = 'error';
      item.error = data.error;
    } else if (data.results && data.results.length > 0) {
      // 1. Map the primary extracted receipt to the original queue item
      const first = data.results[0];
      item.status = 'done';
      item.result = first;
      if (first.image_data_uri) {
        item.previewUrl = first.image_data_uri; // Replaces full image with the cropped preview
      }

      // 2. If multiple receipts were detected, inject them into the queue immediately
      if (data.results.length > 1) {
        const currentIdx = state.queue.findIndex(q => q.id === item.id);
        
        for (let i = 1; i < data.results.length; i++) {
          const subResult = data.results[i];
          queueIdCounter++;
          
          const newItem = {
            id: queueIdCounter, 
            file: null, 
            name: `${item.name} (Part ${i + 1})`,
            previewUrl: subResult.image_data_uri,
            status: 'done', 
            result: subResult, 
            error: null, 
            edited: null, 
            saved: false,
          };
          
          // Insert the new receipt exactly after the current one
          state.queue.splice(currentIdx + i, 0, newItem);
        }
      }
    } else {
      item.status = 'error';
      item.error = 'No valid data returned';
    }
  } catch (err) {
    item.status = 'error';
    item.error = 'Network error while scanning';
  }

  updateQueueAndEditor(item.id);
}

function updateQueueAndEditor(itemId) {
  renderQueue();
  if (state.currentQueueId === itemId) renderEditor();
}

const retryQueueItem = id => scanQueueItem(state.queue.find(q => q.id === id));

function removeQueueItem(id, evt) {
  if (evt) evt.stopPropagation();
  const idx = state.queue.findIndex(q => q.id === id);
  if (idx === -1) return;
  
  URL.revokeObjectURL(state.queue[idx].previewUrl);
  state.queue.splice(idx, 1);

  if (state.currentQueueId === id) {
    state.currentQueueId = null;
    const next = state.queue[idx] || state.queue[idx - 1] || null;
    if (next) selectQueueItem(next.id); else renderEditor();
  }
  renderQueue();
}

function clearQueue() {
  state.queue.forEach(q => URL.revokeObjectURL(q.previewUrl));
  state.queue = [];
  state.currentQueueId = null;
  renderQueue();
  renderEditor();
}

function renderQueue() {
  const list = document.getElementById('ocr-queue-list');
  const progressEl = document.getElementById('queue-progress');
  const clearBtn = document.getElementById('btn-clear-queue');

  if (!state.queue.length) {
    list.innerHTML = `<div class="queue-empty">Select one or more receipt images above - they'll be scanned automatically in the background. Come back and click any of them here to review and save.</div>`;
    progressEl.textContent = 'No images selected';
    clearBtn.disabled = true;
    return;
  }

  clearBtn.disabled = false;
  const total = state.queue.length;
  const done = state.queue.filter(q => ['done', 'error'].includes(q.status)).length;
  const saved = state.queue.filter(q => q.saved).length;
  const errors = state.queue.filter(q => q.status === 'error').length;
  progressEl.textContent = `${done}/${total} scanned • ${saved} saved` + (errors ? ` • ${errors} error${errors > 1 ? 's' : ''}` : '');

  const statusMeta = { 
    pending: { i: '⏳', l: 'Waiting…' }, scanning: { i: '🔄', l: 'Scanning…' }, 
    done: { i: '🟢', l: 'Ready to review' }, error: { i: '⚠️', l: 'Failed' } 
  };

  list.innerHTML = state.queue.map(item => {
    const meta = statusMeta[item.status];
    const icon = item.saved ? '✅' : meta.i;
    const label = item.saved ? 'Saved' : (item.status === 'error' ? (item.error || 'Failed') : meta.l);
    const activeClass = item.id === state.currentQueueId ? 'active' : '';
    
    return `
      <div class="queue-item ${activeClass} status-${item.status}" onclick="selectQueueItem(${item.id})">
        <img class="queue-thumb" src="${item.previewUrl}">
        <div class="queue-info">
          <div class="queue-name">${item.name}</div>
          <div class="queue-status">${icon} ${label}</div>
        </div>
        <button class="queue-remove" title="Remove" onclick="removeQueueItem(${item.id}, event)">×</button>
      </div>`;
  }).join('');
}

function captureCurrentEdits() {
  if (!state.currentQueueId) return;
  const item = state.queue.find(q => q.id === state.currentQueueId);
  if (item) {
    item.edited = {
      vendor: document.getElementById('ocr-vendor').value,
      price: document.getElementById('ocr-price').value,
      date: document.getElementById('ocr-date').value,
      categoryIds: Array.from(document.querySelectorAll('#ocr-categories input:checked')).map(cb => parseInt(cb.value)),
    };
  }
}

function selectQueueItem(id) {
  captureCurrentEdits();
  state.currentQueueId = id;
  renderQueue();
  renderEditor();
}

function navigateQueue(delta) {
  if (!state.queue.length) return;
  const idx = state.queue.findIndex(q => q.id === state.currentQueueId);
  const newIdx = Math.max(0, Math.min(idx + delta, state.queue.length - 1));
  if (state.queue[newIdx]) selectQueueItem(state.queue[newIdx].id);
}

function renderEditor() {
  const els = {
    preview: document.getElementById('ocr-preview'), banner: document.getElementById('ocr-status-banner'),
    saveBtn: document.getElementById('btn-save-ocr'), label: document.getElementById('editor-item-label'),
    prevBtn: document.getElementById('btn-prev-item'), nextBtn: document.getElementById('btn-next-item'),
    vendor: document.getElementById('ocr-vendor'), price: document.getElementById('ocr-price'),
    date: document.getElementById('ocr-date'), cats: document.querySelectorAll('#ocr-categories input')
  };

  const item = state.queue.find(q => q.id === state.currentQueueId);

  if (!item) {
    els.preview.innerHTML = 'Image will appear here';
    els.banner.style.display = 'none';
    els.saveBtn.disabled = true; els.label.textContent = '—';
    els.prevBtn.disabled = true; els.nextBtn.disabled = true;
    els.vendor.value = ''; els.price.value = ''; els.date.value = '';
    els.cats.forEach(cb => cb.checked = false);
    return;
  }

  const idx = state.queue.findIndex(q => q.id === item.id);
  els.label.textContent = `${idx + 1} of ${state.queue.length} — ${item.name}`;
  els.prevBtn.disabled = idx === 0; els.nextBtn.disabled = idx === state.queue.length - 1;
  els.preview.innerHTML = `<img src="${item.previewUrl}" style="max-width:100%; height:400px; border-radius:8px;">`;

  const fields = item.edited || item.result || {};
  els.vendor.value = fields.vendor || '';
  els.price.value = fields.price || '';

  // Parse generic date_str cleanly
  let dateVal = fields.date || '';
  if (!item.edited?.date && item.result?.date_str) {
    const [m, d, y] = item.result.date_str.split('/');
    if (y) dateVal = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
  }
  els.date.value = dateVal;

  const checkedIds = new Set(item.edited?.categoryIds || []);
  els.cats.forEach(cb => cb.checked = checkedIds.has(parseInt(cb.value)));

  const bannerStates = {
    scanning: { class: 'scanning', text: '🔄 Scanning this receipt…', btnState: true },
    pending: { class: 'pending', text: '⏳ Waiting to be scanned…', btnState: true },
    error: { class: 'error', html: `⚠️ Scan failed: ${item.error || 'Unknown error'} — <a href="#" onclick="retryQueueItem(${item.id}); return false;">Retry</a> (or fill the fields in manually below)`, btnState: false },
    saved: { class: 'saved', text: '✅ Saved to your receipts.', btnState: false }
  };

  if (bannerStates[item.status] || item.saved) {
    const stateKey = item.saved ? 'saved' : item.status;
    const bState = bannerStates[stateKey];
    
    els.banner.style.display = 'block';
    els.banner.className = `status-banner ${bState.class}`;
    if (bState.html) els.banner.innerHTML = bState.html; else els.banner.textContent = bState.text;
    els.saveBtn.disabled = bState.btnState;
  } else {
    els.banner.style.display = 'none';
    els.saveBtn.disabled = false;
  }
}

async function updateApp() {
  await api('/api/update', { method: 'POST' });
  showToast('Update initiated. App will restart.');
}

async function fetchBills() {
  const search = document.getElementById('search-bills').value.toLowerCase();
  const vid = document.getElementById('filter-vendor').value;
  const cid = document.getElementById('filter-category').value;
  
  const query = new URLSearchParams();
  if (vid) query.append('vendor_id', vid);
  if (cid) query.append('category_id', cid);

  const bills = await api(`/api/bills?${query.toString()}`);
  state.bills = bills; // Cache globally
  const tbody = document.querySelector('#bills-table tbody');
  
  const filtered = bills.filter(b => 
    `${b.vendor} ${b.date} ${b.categories.map(c=>c.category_name).join(' ')}`.toLowerCase().includes(search)
  );

  // Clear tracking sets if records disappear from visible array filter configurations
  document.getElementById('select-all-checkbox').checked = false;

  tbody.innerHTML = filtered.map(b => {
    const isChecked = state.checkedBillIds.has(b.id) ? 'checked' : '';
    return `
      <tr onclick="openEditModal(${b.id})">
        <td onclick="event.stopPropagation();">
          <input type="checkbox" class="row-checkbox" data-id="${b.id}" ${isChecked} onchange="handleRowCheckChange(this, ${b.id})">
        </td>
        <td>${b.date}</td>
        <td>${b.vendor || '(no vendor)'}</td>
        <td>$${b.price.toFixed(2)}</td>
        <td>${b.categories.map(c=>c.category_name).join(', ')}</td>
        <td>${b.id}</td>
      </tr>
    `;
  }).join('');

  updateBulkActionUI();
}

function handleRowCheckChange(checkbox, id) {
  if (checkbox.checked) {
    state.checkedBillIds.add(id);
  } else {
    state.checkedBillIds.delete(id);
  }
  updateBulkActionUI();
}

function toggleAllCheckboxes(masterCheckbox) {
  const checkboxes = document.querySelectorAll('.row-checkbox');
  checkboxes.forEach(cb => {
    const id = parseInt(cb.getAttribute('data-id'));
    cb.checked = masterCheckbox.checked;
    if (masterCheckbox.checked) {
      state.checkedBillIds.add(id);
    } else {
      state.checkedBillIds.delete(id);
    }
  });
  updateBulkActionUI();
}

function updateBulkActionUI() {
  const count = state.checkedBillIds.size;
  document.getElementById('selected-receipt-label').textContent = `${count} receipt${count !== 1 ? 's' : ''} selected`;
  document.getElementById('btn-delete-receipt').disabled = count === 0;
}

async function deleteSelectedReceipts() {
  const idsToDelete = Array.from(state.checkedBillIds);
  if (!idsToDelete.length) return;

  if (confirm(`Are you absolutely sure you want to permanently delete these ${idsToDelete.length} selected receipt records?`)) {
    const response = await api('/api/bills/bulk-delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: idsToDelete })
    });
    
    if (response.success) {
      showToast(`Successfully deleted ${response.deleted} receipts.`);
      state.checkedBillIds.clear();
      fetchBills();
    } else {
      showToast('Error executing requested sequence removal.', true);
    }
  }
}

// --- Popup Modal Architecture Control Methods ---
function openEditModal(billId) {
  const bill = state.bills.find(b => b.id === billId);
  if (!bill) return;

  document.getElementById('edit-bill-id').value = bill.id;
  document.getElementById('edit-vendor-name').value = bill.vendor || '';
  document.getElementById('edit-price').value = bill.price || '';
  document.getElementById('edit-date').value = bill.date || '';
  document.getElementById('modal-img-view').src = bill.image_path || '';

  // Render categories with matching tags checked
  const currentCategoryIds = new Set(bill.categories.map(c => c.id));
  document.getElementById('edit-categories-list').innerHTML = state.categories.map(c => `
    <label><input type="checkbox" class="modal-cat-box" value="${c.id}" ${currentCategoryIds.has(c.id) ? 'checked' : ''}> ${c.category_name}</label>
  `).join('');

  document.getElementById('edit-receipt-modal').classList.add('active');
}

function closeEditModal() {
  document.getElementById('edit-receipt-modal').classList.remove('active');
}

async function saveModalEdits() {
  const id = document.getElementById('edit-bill-id').value;
  const vendorName = document.getElementById('edit-vendor-name').value.trim();
  const price = document.getElementById('edit-price').value;
  const date = document.getElementById('edit-date').value;
  
  const categoryIds = Array.from(document.querySelectorAll('.modal-cat-box:checked'))
    .map(cb => parseInt(cb.value));

  if (!price || !date) {
    return showToast('Price and Date are required values.', true);
  }

  const response = await api(`/api/bills/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vendor_name: vendorName, price, date, category_ids: categoryIds })
  });

  if (response.success) {
    showToast('Receipt changes updated smoothly.');
    closeEditModal();
    fetchBills();
  } else {
    showToast(response.error || 'Failed saving changes.', true);
  }
}

async function deleteBillFromModal() {
  const id = parseInt(document.getElementById('edit-bill-id').value);
  if (confirm('Are you sure you want to completely remove this receipt record?')) {
    const response = await api(`/api/bills/${id}`, { method: 'DELETE' });
    if (response.success) {
      showToast('Receipt deleted successfully.');
      state.checkedBillIds.delete(id);
      closeEditModal();
      fetchBills();
    }
  }
}

function clearFilters() {
  document.getElementById('search-bills').value = '';
  document.getElementById('filter-vendor').value = '';
  document.getElementById('filter-category').value = '';
  fetchBills();
}

// Init Application
fetchVendors();
fetchCategories();
initDropzone();