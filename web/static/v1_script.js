// --- Routing & UI State ---
document.querySelectorAll('.nav-item').forEach(link => {
    link.addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    
    e.target.classList.add('active');
    const target = e.target.getAttribute('data-target');
    document.getElementById(`view-${target}`).classList.add('active');

    if(target === 'receipts') fetchBills();
    if(target === 'categories') fetchCategories();
    if(target === 'vendors') fetchVendors();
    if(target === 'add') populateAddForm();
    });
});

function switchTab(tabId) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
    event.target.classList.add('active');
    document.getElementById(`tab-${tabId}`).style.display = 'block';
}

function showToast(msg, isError=false) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.style.backgroundColor = isError ? 'var(--danger)' : 'var(--primary)';
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

// --- Data Fetching ---
let state = {
    bills: [], vendors: [], categories: [], selectedBillId: null,
    queue: [], currentQueueId: null, queueProcessing: false,
};

async function api(url, options = {}) {
    const res = await fetch(url, options);
    return await res.json();
}

// Bills
async function fetchBills() {
    const search = document.getElementById('search-bills').value.toLowerCase();
    const vid = document.getElementById('filter-vendor').value;
    const cid = document.getElementById('filter-category').value;
    
    let url = '/api/bills?';
    if(vid) url += `vendor_id=${vid}&`;
    if(cid) url += `category_id=${cid}`;

    const bills = await api(url);
    const tbody = document.querySelector('#bills-table tbody');
    tbody.innerHTML = '';
    
    const filtered = bills.filter(b => {
    const text = `${b.vendor} ${b.date} ${b.categories.map(c=>c.category_name).join(' ')}`.toLowerCase();
    return text.includes(search);
    });

    filtered.forEach(b => {
    const tr = document.createElement('tr');
    tr.onclick = () => selectBill(b.id, b.vendor, tr);
    tr.innerHTML = `
        <td>${b.date}</td>
        <td>${b.vendor || '(no vendor)'}</td>
        <td>$${b.price.toFixed(2)}</td>
        <td>${b.categories.map(c=>c.category_name).join(', ')}</td>
        <td>${b.id}</td>
    `;
    tbody.appendChild(tr);
    });
    state.selectedBillId = null;
    document.getElementById('selected-receipt-label').textContent = 'No receipt selected';
    document.getElementById('btn-delete-receipt').disabled = true;
}

function selectBill(id, vendor, row) {
    document.querySelectorAll('#bills-table tr').forEach(r => r.classList.remove('selected'));
    row.classList.add('selected');
    state.selectedBillId = id;
    document.getElementById('selected-receipt-label').textContent = `Selected: #${id} ${vendor}`;
    document.getElementById('btn-delete-receipt').disabled = false;
}

async function deleteSelectedReceipt() {
    if(!state.selectedBillId) return;
    await api(`/api/bills/${state.selectedBillId}`, { method: 'DELETE' });
    showToast(`Receipt #${state.selectedBillId} deleted`);
    fetchBills();
}

// Vendors & Categories
async function fetchVendors() {
    const v = await api('/api/vendors');
    state.vendors = v;
    renderList('vendor-list', v, 'name', id => deleteVendor(id));
    const sel = document.getElementById('filter-vendor');
    sel.innerHTML = '<option value="">All Vendors</option>' + v.map(vi => `<option value="${vi.id}">${vi.name}</option>`).join('');
}

async function fetchCategories() {
    const c = await api('/api/categories');
    state.categories = c;
    renderList('category-list', c, 'category_name', id => deleteCategory(id));
    const sel = document.getElementById('filter-category');
    sel.innerHTML = '<option value="">All Categories</option>' + c.map(ci => `<option value="${ci.id}">${ci.category_name}</option>`).join('');
}

function renderList(containerId, items, labelKey, delFn) {
    const c = document.getElementById(containerId);
    c.innerHTML = items.map(i => `
    <div class="list-item">
        <span>${i[labelKey]}</span>
        <button class="btn-danger-sm" onclick="(${delFn})(${i.id})">Delete</button>
    </div>
    `).join('');
}

async function addVendor() {
    const name = document.getElementById('new-vendor-name').value;
    await api('/api/vendors', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
    document.getElementById('new-vendor-name').value = '';
    fetchVendors(); showToast(`Vendor ${name} added`);
}
async function deleteVendor(id) { await api(`/api/vendors/${id}`, {method:'DELETE'}); fetchVendors(); fetchBills(); }

async function addCategory() {
    const name = document.getElementById('new-cat-name').value;
    await api('/api/categories', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
    document.getElementById('new-cat-name').value = '';
    fetchCategories(); fetchBills(); showToast(`Category ${name} added`);
}
async function deleteCategory(id) { await api(`/api/categories/${id}`, {method:'DELETE'}); fetchCategories(); fetchBills(); }

// Forms
async function populateAddForm() {
    captureCurrentEdits(); // don't lose in-progress OCR edits when categories reload
    await Promise.all([fetchVendors(), fetchCategories()]);
    const catsHTML = state.categories.map(c => `<label><input type="checkbox" value="${c.id}"> ${c.category_name}</label>`).join('');
    document.getElementById('add-categories').innerHTML = catsHTML;
    document.getElementById('ocr-categories').innerHTML = catsHTML;
    document.getElementById('add-date').valueAsDate = new Date();
    renderEditor(); // restore the currently-selected queue item's fields/checkboxes
}

async function getOrCreateVendorId(name) {
    const existing = state.vendors.find(v => v.name.toLowerCase() === name.toLowerCase());
    if(existing) return existing.id;
    const res = await api('/api/vendors', {method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
    return res.id;
}

async function saveManualReceipt() {
    const vendorName = document.getElementById('add-vendor-name').value;
    const price = document.getElementById('add-price').value;
    const date = document.getElementById('add-date').value;
    const cats = Array.from(document.querySelectorAll('#add-categories input:checked')).map(cb => parseInt(cb.value));

    if(!vendorName || !price || !date) return showToast('Fill all required fields', true);

    const vId = await getOrCreateVendorId(vendorName);
    await api('/api/bills', {
    method: 'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({vendor_id: vId, price, date, category_ids: cats})
    });
    showToast('Receipt saved!');
    document.getElementById('add-vendor-name').value = '';
    document.getElementById('add-price').value = '';
    document.querySelectorAll('#add-categories input').forEach(cb => cb.checked = false);
}

// --- OCR Batch Queue ---
// Selecting multiple images queues them all and scans them one-by-one
// in the background (sequentially, so the single shared OCR model never
// gets hit concurrently). You don't have to wait for a scan to finish
// before picking the next receipt to review - click any item in the
// queue at any time to see its current status / result.
let queueIdCounter = 0;

function handleFileSelect(event) {
    const files = Array.from(event.target.files || []);
    event.target.value = ''; // allow re-selecting the same file(s) later

    if(files.length === 0) return;
    if(files.length > 25) showToast(`Queued ${files.length} images - this may take a while.`);

    files.forEach(file => {
    queueIdCounter += 1;
    state.queue.push({
        id: queueIdCounter,
        file,
        name: file.name,
        previewUrl: URL.createObjectURL(file),
        status: 'pending',   // pending | scanning | done | error
        result: null,
        error: null,
        edited: null,
        saved: false,
    });
    });

    renderQueue();
    if(state.currentQueueId === null) selectQueueItem(state.queue[0].id);
    processQueue();
}

async function processQueue() {
    if(state.queueProcessing) return; // a loop is already draining the queue
    state.queueProcessing = true;

    for(const item of state.queue) {
    if(item.status !== 'pending') continue;
    await scanQueueItem(item);
    }

    state.queueProcessing = false;
}

async function scanQueueItem(item) {
    item.status = 'scanning';
    item.error = null;
    renderQueue();
    if(state.currentQueueId === item.id) renderEditor();

    try {
    const formData = new FormData();
    formData.append('image', item.file);
    const res = await fetch('/api/scan', { method: 'POST', body: formData });
    const data = await res.json();

    if(data.error) {
        item.status = 'error';
        item.error = data.error;
    } else {
        item.status = 'done';
        item.result = data;
    }
    } catch(err) {
    item.status = 'error';
    item.error = 'Network error while scanning';
    }

    renderQueue();
    if(state.currentQueueId === item.id) renderEditor();
}

async function retryQueueItem(id) {
    const item = state.queue.find(q => q.id === id);
    if(!item) return;
    await scanQueueItem(item);
}

function removeQueueItem(id, evt) {
    if(evt) evt.stopPropagation();
    const idx = state.queue.findIndex(q => q.id === id);
    if(idx === -1) return;
    URL.revokeObjectURL(state.queue[idx].previewUrl);
    state.queue.splice(idx, 1);

    if(state.currentQueueId === id) {
    state.currentQueueId = null;
    const next = state.queue[idx] || state.queue[idx - 1] || null;
    if(next) selectQueueItem(next.id); else renderEditor();
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

    if(state.queue.length === 0) {
    list.innerHTML = `<div class="queue-empty">Select one or more receipt images above - they'll be scanned automatically in the background. Come back and click any of them here to review and save.</div>`;
    progressEl.textContent = 'No images selected';
    clearBtn.disabled = true;
    return;
    }

    clearBtn.disabled = false;
    const total = state.queue.length;
    const done = state.queue.filter(q => q.status === 'done' || q.status === 'error').length;
    const saved = state.queue.filter(q => q.saved).length;
    const errors = state.queue.filter(q => q.status === 'error').length;
    progressEl.textContent = `${done}/${total} scanned • ${saved} saved` + (errors ? ` • ${errors} error${errors > 1 ? 's' : ''}` : '');

    const statusIcon  = { pending: '⏳', scanning: '🔄', done: '🟢', error: '⚠️' };
    const statusLabel = { pending: 'Waiting…', scanning: 'Scanning…', done: 'Ready to review', error: 'Failed' };

    list.innerHTML = state.queue.map(item => {
    const icon = item.saved ? '✅' : statusIcon[item.status];
    const label = item.saved ? 'Saved' : (item.status === 'error' ? (item.error || 'Failed') : statusLabel[item.status]);
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
    if(state.currentQueueId === null) return;
    const item = state.queue.find(q => q.id === state.currentQueueId);
    if(!item) return;
    item.edited = {
    vendor: document.getElementById('ocr-vendor').value,
    price: document.getElementById('ocr-price').value,
    date: document.getElementById('ocr-date').value,
    categoryIds: Array.from(document.querySelectorAll('#ocr-categories input:checked')).map(cb => parseInt(cb.value)),
    };
}

function selectQueueItem(id) {
    captureCurrentEdits();
    state.currentQueueId = id;
    renderQueue();
    renderEditor();
}

function navigateQueue(delta) {
    if(state.queue.length === 0) return;
    const idx = state.queue.findIndex(q => q.id === state.currentQueueId);
    const newIdx = Math.min(Math.max(idx + delta, 0), state.queue.length - 1);
    const target = state.queue[newIdx];
    if(target) selectQueueItem(target.id);
}

function renderEditor() {
    const preview = document.getElementById('ocr-preview');
    const banner = document.getElementById('ocr-status-banner');
    const saveBtn = document.getElementById('btn-save-ocr');
    const label = document.getElementById('editor-item-label');
    const prevBtn = document.getElementById('btn-prev-item');
    const nextBtn = document.getElementById('btn-next-item');

    const item = state.queue.find(q => q.id === state.currentQueueId);

    if(!item) {
    preview.innerHTML = 'Image will appear here';
    banner.style.display = 'none';
    saveBtn.disabled = true;
    label.textContent = '—';
    prevBtn.disabled = true; nextBtn.disabled = true;
    document.getElementById('ocr-vendor').value = '';
    document.getElementById('ocr-price').value = '';
    document.getElementById('ocr-date').value = '';
    document.querySelectorAll('#ocr-categories input').forEach(cb => cb.checked = false);
    return;
    }

    const idx = state.queue.findIndex(q => q.id === item.id);
    label.textContent = `${idx + 1} of ${state.queue.length} — ${item.name}`;
    prevBtn.disabled = idx === 0;
    nextBtn.disabled = idx === state.queue.length - 1;

    preview.innerHTML = `<img src="${item.previewUrl}" style="max-width:100%; height:400px; border-radius:8px;">`;

    const fields = item.edited || item.result || {};
    document.getElementById('ocr-vendor').value = fields.vendor || '';
    document.getElementById('ocr-price').value = fields.price || '';

    let dateVal = '';
    if(item.edited && item.edited.date) {
    dateVal = item.edited.date;
    } else if(item.result && item.result.date_str) {
    const parts = item.result.date_str.split('/');
    if(parts.length === 3) dateVal = `${parts[2]}-${parts[0].padStart(2,'0')}-${parts[1].padStart(2,'0')}`;
    }
    document.getElementById('ocr-date').value = dateVal;

    const checkedIds = new Set((item.edited && item.edited.categoryIds) || []);
    document.querySelectorAll('#ocr-categories input').forEach(cb => {
    cb.checked = checkedIds.has(parseInt(cb.value));
    });

    if(item.status === 'scanning') {
    banner.style.display = 'block';
    banner.className = 'status-banner scanning';
    banner.textContent = '🔄 Scanning this receipt…';
    saveBtn.disabled = true;
    } else if(item.status === 'pending') {
    banner.style.display = 'block';
    banner.className = 'status-banner pending';
    banner.textContent = '⏳ Waiting to be scanned…';
    saveBtn.disabled = true;
    } else if(item.status === 'error') {
    banner.style.display = 'block';
    banner.className = 'status-banner error';
    banner.innerHTML = `⚠️ Scan failed: ${item.error || 'Unknown error'} — <a href="#" onclick="retryQueueItem(${item.id}); return false;">Retry</a> (or fill the fields in manually below)`;
    saveBtn.disabled = false;
    } else if(item.saved) {
    banner.style.display = 'block';
    banner.className = 'status-banner saved';
    banner.textContent = '✅ Saved to your receipts.';
    saveBtn.disabled = false;
    } else {
    banner.style.display = 'none';
    saveBtn.disabled = false;
    }
}

async function saveOCRReceipt() {
    const item = state.queue.find(q => q.id === state.currentQueueId);
    const vendorName = document.getElementById('ocr-vendor').value;
    const price = document.getElementById('ocr-price').value;
    const date = document.getElementById('ocr-date').value;
    const cats = Array.from(document.querySelectorAll('#ocr-categories input:checked')).map(cb => parseInt(cb.value));

    if(!vendorName || !price || !date) return showToast('Fill all required fields', true);

    const vId = await getOrCreateVendorId(vendorName);
    const res = await api('/api/bills', {
    method: 'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({vendor_id: vId, price, date, category_ids: cats})
    });

    if(!res.success) return showToast(res.error || 'Failed to save receipt', true);

    if(item) {
    item.saved = true;
    item.edited = { vendor: vendorName, price, date, categoryIds: cats };
    }

    showToast(item ? `Saved "${item.name}"!` : 'Receipt saved!');
    renderQueue();

    // Auto-advance to the next not-yet-saved item, if any
    if(item) {
    const idx = state.queue.findIndex(q => q.id === item.id);
    const next = state.queue.slice(idx + 1).find(q => !q.saved);
    if(next) selectQueueItem(next.id); else renderEditor();
    } else {
    renderEditor();
    }
}

async function updateApp() {
    await api('/api/update', {method: 'POST'});
    showToast('Update initiated. App will restart.');
}

// Init
fetchVendors(); fetchCategories();