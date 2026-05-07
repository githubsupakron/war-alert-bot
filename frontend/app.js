const API = '';
let allNews = [], curTab = 'all', curPage = 1;
const PAGE_SIZE = 4;
let _pollTimer = null;

function syncPolling(autoFetch) {
  if (autoFetch) {
    if (!_pollTimer) _pollTimer = setInterval(() => { loadStatus(); loadNews(); }, 30000);
  } else {
    clearInterval(_pollTimer);
    _pollTimer = null;
  }
}

function togglePanel(hdr) {
  const body = hdr.nextElementSibling;
  const isOpen = hdr.classList.toggle('open');
  body.style.display = isOpen ? '' : 'none';
}

// ── Utilities ──────────────────────────────────────────────
function esc(s) {
  return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

let toastTimer;
function toast(msg, type = 'ok') {
  const t = document.getElementById('toast');
  clearTimeout(toastTimer);
  t.className = `show ${type}`;
  t.innerHTML = (type === 'ok' ? '✅ ' : type === 'err' ? '❌ ' : 'ℹ️ ') + msg;
  toastTimer = setTimeout(() => t.className = '', 4000);
}

function unitShort(u) { return {seconds:'s',minutes:'m',hours:'h',days:'d'}[u] || 'm'; }
function unitTH(u)    { return {seconds:'วินาที',minutes:'นาที',hours:'ชั่วโมง',days:'วัน'}[u] || 'นาที'; }

function toMinutes(val, unit) {
  const m = {seconds: 1/60, minutes: 1, hours: 60, days: 1440};
  return Math.round(val * (m[unit] || 1));
}
function snapToFive(m) {
  return Math.max(5, Math.min(60, Math.round(m / 5) * 5));
}

function updateIvHint() {
  const v = document.getElementById('iv-minutes')?.value || 30;
  document.getElementById('iv-hint').innerHTML = `<i class="fa-solid fa-equals" style="margin-right:3px"></i> = ทุก ${v} นาที`;
}

// ── Quick date-range chips ──────────────────────────────────
let _activeRangeDays = null;
function setQuickRange(days, el) {
  if (_activeRangeDays === days) {
    _activeRangeDays = null;
    document.querySelectorAll('#range-chips .preset-chip').forEach(c => c.classList.remove('active'));
    return;
  }
  _activeRangeDays = days;
  document.querySelectorAll('#range-chips .preset-chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
}

// ── Channel Bar ─────────────────────────────────────────────
function updateChannelBar(lineOn, fbOn) {
  const lineBadge = document.getElementById('line-ch-badge');
  const fbBadge   = document.getElementById('fb-ch-badge');
  if (lineBadge) lineBadge.style.display = lineOn ? 'flex' : 'none';
  if (fbBadge)   fbBadge.style.display   = fbOn   ? 'flex' : 'none';

  const lineStatus = document.getElementById('ch-line-badge');
  const fbStatus   = document.getElementById('ch-fb-badge');
  if (lineStatus) {
    lineStatus.className = `ch-badge ${lineOn ? 'on-line' : 'off'}`;
    lineStatus.innerHTML = `<i class="fa-brands fa-line"></i> LINE ${lineOn ? 'เปิด' : 'ปิด'}`;
  }
  if (fbStatus) {
    fbStatus.className = `ch-badge ${fbOn ? 'on-fb' : 'off'}`;
    fbStatus.innerHTML = `<i class="fa-brands fa-facebook"></i> Facebook ${fbOn ? 'เปิด' : 'ปิด'}`;
  }
}

function updateClassifierModeUI() {
  const aiOn = document.getElementById('toggle-ai-classifier')?.checked;
  const desc = document.getElementById('classifier-mode-desc');
  const fields = document.querySelectorAll('.manual-classifier-field textarea');

  if (desc) {
    desc.textContent = aiOn
      ? 'AI mode: CodeSmart classifies danger / peace / neutral'
      : 'Manual mode: danger and peace keywords classify the feed';
  }
  fields.forEach(field => {
    field.disabled = aiOn;
  });
  document.querySelectorAll('.manual-classifier-field').forEach(row => {
    row.classList.toggle('is-disabled', !!aiOn);
  });
}

// ── LINE Preview toggle ─────────────────────────────────────
function togglePreview(id) {
  const box = document.getElementById(`prev-${id}`);
  const btn = document.getElementById(`pbtn-${id}`);
  if (!box) return;
  const hidden = box.style.display === 'none';
  box.style.display = hidden ? 'block' : 'none';
  btn.textContent = hidden ? '📋 ซ่อน LINE Preview ▲' : '📋 ดู LINE Preview ▼';
}

// ── Load Status ─────────────────────────────────────────────
async function loadStatus() {
  try {
    const d = await (await fetch(`${API}/api/status`)).json();

    document.getElementById('s-total').textContent  = d.total_news   ?? '—';
    document.getElementById('s-sent').textContent   = d.sent_news    ?? '—';
    document.getElementById('s-fbsent').textContent = d.fb_sent      ?? '—';
    document.getElementById('s-danger').textContent = d.danger_count ?? '—';
    document.getElementById('s-peace').textContent  = d.peace_count  ?? '—';

    // Only update controls when not actively editing
    if (document.activeElement.id !== 'toggle-auto') {
      document.getElementById('toggle-auto').checked = d.auto_fetch;
    }
    if (document.activeElement.id !== 'iv-minutes') {
      const mins = toMinutes(d.interval_value || 30, d.interval_unit || 'minutes');
      document.getElementById('iv-minutes').value = String(snapToFive(mins));
    }
    updateIvHint();

    // Auto badge
    const badge = document.getElementById('auto-badge');
    badge.style.display = d.auto_fetch ? 'flex' : 'none';
    document.getElementById('auto-badge-txt').textContent =
      `AUTO / ${d.interval_value}${unitShort(d.interval_unit)}`;

    if (d.last_fetch) {
      const dt = new Date(d.last_fetch + (d.last_fetch.endsWith('Z') ? '' : 'Z'));
      const timeStr = dt.toLocaleString('th-TH', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
      document.getElementById('hdr-last-time').textContent = timeStr;
      document.getElementById('last-badge').style.display = 'flex';
      document.getElementById('last-fetch-txt').textContent =
        'ล่าสุด: ' + dt.toLocaleString('th-TH');
    }
    if (document.activeElement.id !== 'toggle-line')
      document.getElementById('toggle-line').checked = d.line_enabled !== false;
    if (document.activeElement.id !== 'toggle-fb')
      document.getElementById('toggle-fb').checked = !!d.facebook_enabled;
    updateChannelBar(d.line_enabled !== false, !!d.facebook_enabled);
    if (document.activeElement.id !== 'toggle-ai-classifier' && d.classifier_mode) {
      document.getElementById('toggle-ai-classifier').checked = d.classifier_mode === 'ai';
      updateClassifierModeUI();
    }
    return d.auto_fetch;
  } catch(e) { console.error('loadStatus:', e); }
}

// ── Load Settings ───────────────────────────────────────────
async function loadSettings() {
  try {
    const d = await (await fetch(`${API}/api/settings`)).json();
    document.getElementById('kw-search').value = d.keywords || '';
    document.getElementById('kw-danger').value = d.danger_keywords || '';
    document.getElementById('kw-peace').value  = d.peace_keywords || '';
    document.getElementById('kw-hours').value  = d.max_news_age_hours || 6;
    document.getElementById('toggle-ai-classifier').checked = d.classifier_mode === 'ai';
    updateClassifierModeUI();
  } catch(e) {}
}

// ── Save Scheduler ──────────────────────────────────────────
async function saveScheduler() {
  const auto = document.getElementById('toggle-auto').checked;
  const val  = parseInt(document.getElementById('iv-minutes').value) || 30;

  const btn = event.currentTarget;
  btn.disabled = true;
  btn.innerHTML = '<div class="spin"></div> กำลังบันทึก...';

  try {
    const r = await fetch(`${API}/api/settings/scheduler`, {
      method: 'PUT',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({auto_fetch: auto, interval_value: val, interval_unit: 'minutes'}),
    });
    if (r.ok) {
      toast(auto ? `เปิด Auto ทุก ${val} นาที ✅` : 'ปิด Auto Fetch แล้ว ✅');
      if (auto) {
        const now = new Date();
        const from = new Date(now.getTime() - val * 60000);
        const toISO = d => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString();
        fetch(`${API}/api/news/fetch`, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ from_datetime: toISO(from), to_datetime: toISO(now) }),
        }).then(() => Promise.all([loadNews(), loadStatus()]));
      }
    } else {
      toast('บันทึกไม่สำเร็จ — ' + r.status, 'err');
    }
    const autoFetch = await loadStatus();
    syncPolling(autoFetch);
  } catch(e) { toast('เกิดข้อผิดพลาด', 'err'); }

  btn.disabled = false;
  btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> บันทึกการตั้งค่า Auto';
}

// ── Save Keywords ───────────────────────────────────────────
async function saveKeywords() {
  const btn = event.currentTarget;
  btn.disabled = true;
  btn.innerHTML = '<div class="spin"></div> กำลังบันทึก...';

  try {
    const r = await fetch(`${API}/api/settings/keywords`, {
      method: 'PUT',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        keywords: document.getElementById('kw-search').value,
        danger_keywords: document.getElementById('kw-danger').value,
        peace_keywords:  document.getElementById('kw-peace').value,
        max_news_age_hours: parseInt(document.getElementById('kw-hours').value) || 6,
        classifier_mode: document.getElementById('toggle-ai-classifier').checked ? 'ai' : 'keyword',
      }),
    });
    if (r.ok) {
      const aiOn = document.getElementById('toggle-ai-classifier').checked;
      toast(aiOn ? 'บันทึกแล้ว: ใช้ AI classify' : 'บันทึกแล้ว: ใช้ Manual keywords');
      await loadStatus();
    } else {
      toast('บันทึกไม่สำเร็จ', 'err');
    }
  } catch(e) { toast('เกิดข้อผิดพลาด', 'err'); }

  btn.disabled = false;
  btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> บันทึก Keywords';
}

// ── Manual Fetch ────────────────────────────────────────────
async function manualFetch() {
  const btn  = document.getElementById('btn-fetch');
  const wrap = document.getElementById('fetch-wrap');

  btn.disabled = true;
  btn.innerHTML = '<div class="spin"></div> กำลังดึงข่าว + ประมวลผล...';
  wrap.classList.add('loading');

  // Poll the feed every 1.5 s while the fetch is running so completed
  // articles appear in the list as soon as they are committed to the DB.
  const livePoller = setInterval(loadNews, 1500);

  let body = {};
  if (_activeRangeDays) {
    const now = new Date();
    const from = new Date(now.getTime() - _activeRangeDays * 86400000);
    from.setHours(0, 0, 0, 0);
    const toISO = d => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString();
    body = { from_datetime: toISO(from), to_datetime: toISO(now) };
  }

  try {
    const r = await fetch(`${API}/api/news/fetch`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body),
    });
    const d = await r.json();
    if (r.ok) {
      toast(`ดึงข่าว ${d.fetched} รายการ · ใหม่ ${d.new} · ส่ง LINE ${d.sent} รายการ`);
    } else {
      toast(d.detail || 'เกิดข้อผิดพลาดในการดึงข่าว', 'err');
    }
  } catch(e) { toast('เกิดข้อผิดพลาด: ' + e.message, 'err'); }
  finally {
    clearInterval(livePoller);
    await Promise.all([loadNews(), loadStatus()]);
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> ค้นหาข่าวตอนนี้';
    wrap.classList.remove('loading');
  }
}

// ── Test LINE ───────────────────────────────────────────────
async function testLine() {
  const btn = event.currentTarget;
  btn.disabled = true;
  btn.innerHTML = '<div class="spin"></div> กำลังส่ง...';

  try {
    const d = await (await fetch(`${API}/api/line/test`, {method:'POST'})).json();
    d.success ? toast('📱 ส่ง LINE สำเร็จ!') : toast('ส่ง LINE ไม่สำเร็จ — ตรวจสอบ Token', 'err');
  } catch(e) { toast('เกิดข้อผิดพลาด', 'err'); }

  btn.disabled = false;
  btn.innerHTML = '<i class="fa-brands fa-line"></i> ทดสอบส่ง LINE';
}

// ── News ────────────────────────────────────────────────────
async function loadNews() {
  try {
    const data = await (await fetch(`${API}/api/news?limit=200`)).json();
    allNews = data.sort((a, b) => new Date(b.published_at) - new Date(a.published_at));
    renderNews();
  } catch(e) {
    document.getElementById('news-list').innerHTML =
      '<div class="empty"><span class="ei">⚠️</span><p>เชื่อมต่อ API ไม่ได้</p></div>';
  }
}

function setTab(tab, el) {
  curTab = tab;
  curPage = 1;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  renderNews();
}

function getFilteredNews() {
  if      (curTab === 'danger')  return allNews.filter(n => n.category === 'danger');
  else if (curTab === 'peace')   return allNews.filter(n => n.category === 'peace');
  else if (curTab === 'neutral') return allNews.filter(n => n.category === 'neutral');
  else if (curTab === 'sent')    return allNews.filter(n => n.line_sent);
  else if (curTab === 'fb_sent') return allNews.filter(n => n.facebook_sent);
  return allNews;
}

function goPage(p) {
  const totalPages = Math.max(1, Math.ceil(getFilteredNews().length / PAGE_SIZE));
  curPage = Math.max(1, Math.min(p, totalPages));
  renderNews();
  document.getElementById('news-list').scrollTop = 0;
}

function buildPager(curPage, totalPages) {
  const pages = new Set();
  for (let i = 1; i <= Math.min(2, totalPages); i++) pages.add(i);
  for (let i = Math.max(1, totalPages - 1); i <= totalPages; i++) pages.add(i);
  for (let i = Math.max(1, curPage - 1); i <= Math.min(totalPages, curPage + 1); i++) pages.add(i);

  const sorted = [...pages].sort((a, b) => a - b);
  let btns = '';
  let prev = 0;
  for (const p of sorted) {
    if (p - prev > 1) btns += `<span class="pager-ellipsis">…</span>`;
    btns += `<button class="pager-page-btn${p === curPage ? ' active' : ''}" onclick="goPage(${p})">${p}</button>`;
    prev = p;
  }

  return `<div class="pager">
    <button class="btn btn-ghost btn-sm pager-nav" onclick="goPage(${curPage - 1})" ${curPage === 1 ? 'disabled' : ''}><i class="fa-solid fa-chevron-left"></i></button>
    ${btns}
    <button class="btn btn-ghost btn-sm pager-nav" onclick="goPage(${curPage + 1})" ${curPage === totalPages ? 'disabled' : ''}><i class="fa-solid fa-chevron-right"></i></button>
  </div>`;
}

function renderNews() {
  const list = getFilteredNews();
  const total = list.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (curPage > totalPages) curPage = totalPages;

  const badge = document.getElementById('news-count-badge');
  badge.textContent = total;
  badge.className = `badge ${total ? 'b-blue' : 'b-neutral'}`;

  const container = document.getElementById('news-list');
  const pager = document.getElementById('news-pagination');

  if (!total) {
    container.innerHTML = '<div class="empty"><span class="ei">📭</span><p>ไม่มีข่าวในหมวดนี้</p></div>';
    pager.innerHTML = '';
    return;
  }

  const start = (curPage - 1) * PAGE_SIZE;
  const pageItems = list.slice(start, start + PAGE_SIZE);
  const pStart = start + 1;
  const pEnd = Math.min(curPage * PAGE_SIZE, total);

  pager.innerHTML = buildPager(curPage, totalPages);

  container.innerHTML = pageItems.map(n => {
    const cat       = n.category || 'neutral';
    const badgeCls  = cat === 'danger' ? 'b-danger' : cat === 'peace' ? 'b-peace' : 'b-neutral';
    const catIcon   = cat === 'danger'
      ? '<i class="fa-solid fa-triangle-exclamation"></i>'
      : cat === 'peace'
      ? '<i class="fa-solid fa-dove"></i>'
      : '⚪';
    const catLabel  = cat.toUpperCase();

    // Bilingual title
    const hasTH     = n.title_th && n.title_th !== n.title && n.title_th.trim() !== '';
    const titleMain = esc(hasTH ? n.title_th : n.title);
    const titleSub  = hasTH
      ? `<div class="ntitle-en"><i class="fa-solid fa-language" style="margin-right:4px;color:var(--purple)"></i>${esc(n.title)}</div>`
      : '';

    const descText  = n.description ? esc(n.description.slice(0, 160)) + (n.description.length > 160 ? '…' : '') : '';
    const pub       = n.published_at ? new Date(n.published_at).toLocaleString('th-TH') : '';

    const sentBadge  = n.line_sent     ? '<span class="badge b-sent"><i class="fa-brands fa-line"></i> ส่งแล้ว</span>'  : '';
    const fbBadge    = n.facebook_sent ? '<span class="badge b-fb"><i class="fa-brands fa-facebook"></i> FB</span>'        : '';
    const transBadge = hasTH           ? '<span class="badge b-trans">🇹🇭 แปลแล้ว</span>'                                  : '';

    const previewBlock = n.alert_message ? `
      <button class="preview-toggle" id="pbtn-${n.id}" onclick="togglePreview(${n.id})">📋 ซ่อน LINE Preview ▲</button>
      <div class="apreview" id="prev-${n.id}">${esc(n.alert_message)}</div>
    ` : '';

    const sendBtn   = (!n.line_sent && n.alert_message)
      ? `<button class="btn btn-primary btn-sm" onclick="sendLine(${n.id})"><i class="fa-brands fa-line"></i> ส่ง LINE</button>` : '';
    const postFBBtn = (!n.facebook_sent && n.alert_message)
      ? `<button class="btn btn-fb btn-sm" onclick="postFacebook(${n.id})"><i class="fa-brands fa-facebook"></i> FB</button>` : '';

    return `
<div class="ncard ${cat}" id="nc-${n.id}">
  <div class="nmeta">
    <span class="badge ${badgeCls}">${catIcon} ${catLabel}</span>
    ${sentBadge}${fbBadge}${transBadge}
    <span class="nsrc" style="margin-left:auto">${esc(n.source || '')}</span>
  </div>
  <div class="ntitle">${titleMain}</div>
  ${titleSub}
  ${descText ? `<div class="ndesc">${descText}</div>` : ''}
  ${previewBlock}
  <div class="nfoot">
    <span class="nsrc">${pub}</span>
    <div class="nact">
      <a href="${esc(n.url)}" target="_blank" rel="noopener" class="btn btn-ghost btn-sm">
        <i class="fa-solid fa-arrow-up-right-from-square"></i> ลิงก์
      </a>
      ${sendBtn}
      ${postFBBtn}
      <button class="btn btn-danger btn-sm" onclick="delNews(${n.id})">
        <i class="fa-solid fa-trash"></i>
      </button>
    </div>
  </div>
</div>`;
  }).join('');
}

// ── Save Channels ───────────────────────────────────────────
async function saveChannels() {
  const lineOn = document.getElementById('toggle-line').checked;
  const fbOn   = document.getElementById('toggle-fb').checked;
  const btn = event.currentTarget;
  btn.disabled = true;
  btn.innerHTML = '<div class="spin"></div> กำลังบันทึก...';
  try {
    const r = await fetch(`${API}/api/settings/channels`, {
      method: 'PUT',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({line_enabled: lineOn, facebook_enabled: fbOn}),
    });
    if (r.ok) {
      toast(`บันทึกแล้ว — LINE ${lineOn?'เปิด':'ปิด'} · Facebook ${fbOn?'เปิด':'ปิด'} ✅`);
      updateChannelBar(lineOn, fbOn);
    } else {
      toast('บันทึกไม่สำเร็จ', 'err');
    }
  } catch(e) { toast('เกิดข้อผิดพลาด', 'err'); }
  btn.disabled = false;
  btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> บันทึก Channel Settings';
}

// ── Test Facebook ───────────────────────────────────────────
async function testFacebook() {
  const btn = event.currentTarget;
  btn.disabled = true;
  btn.innerHTML = '<div class="spin"></div>';
  try {
    const d = await (await fetch(`${API}/api/facebook/test`, {method:'POST'})).json();
    d.success ? toast('📘 โพสต์ Facebook สำเร็จ!') : toast('Facebook ไม่สำเร็จ — ตรวจสอบ Page Token', 'err');
  } catch(e) { toast('เกิดข้อผิดพลาด', 'err'); }
  btn.disabled = false;
  btn.innerHTML = '<i class="fa-brands fa-facebook"></i> Test Facebook';
}

// ── Post Facebook ───────────────────────────────────────────
async function postFacebook(id) {
  try {
    const d = await (await fetch(`${API}/api/facebook/send/${id}`, {method:'POST'})).json();
    d.success ? toast('📘 โพสต์ Facebook สำเร็จ!') : toast('โพสต์ Facebook ไม่สำเร็จ', 'err');
    await Promise.all([loadNews(), loadStatus()]);
  } catch(e) { toast('เกิดข้อผิดพลาด', 'err'); }
}

async function sendLine(id) {
  try {
    const d = await (await fetch(`${API}/api/line/send/${id}`, {method:'POST'})).json();
    d.success ? toast('📱 ส่ง LINE สำเร็จ!') : toast('ส่งไม่สำเร็จ — ตรวจสอบ Token', 'err');
    await Promise.all([loadNews(), loadStatus()]);
  } catch(e) { toast('เกิดข้อผิดพลาด', 'err'); }
}

async function delNews(id) {
  if (!confirm('ลบข่าวนี้?')) return;
  try {
    await fetch(`${API}/api/news/${id}`, {method:'DELETE'});
    toast('ลบข่าวแล้ว');
    allNews = allNews.filter(n => n.id !== id);
    renderNews();
    loadStatus();
  } catch(e) {}
}

async function deleteAll() {
  if (!confirm('⚠️ ลบข่าวทั้งหมดในฐานข้อมูล?')) return;
  try {
    await fetch(`${API}/api/news`, {method:'DELETE'});
    toast('ลบทั้งหมดแล้ว');
    allNews = [];
    renderNews();
    loadStatus();
  } catch(e) {}
}

// ── Init ────────────────────────────────────────────────────
document.getElementById('iv-minutes').addEventListener('change', updateIvHint);

// Default to 1-day range
_activeRangeDays = 1;
document.querySelector('#range-chips .preset-chip').classList.add('active');

Promise.all([loadStatus().then(syncPolling), loadSettings(), loadNews()]);
