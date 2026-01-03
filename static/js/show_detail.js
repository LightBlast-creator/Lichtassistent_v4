const KEY_FOCUS = 'la_focus_cue';
const OFFSET_TOP = 110;
const safeInt = (v) => {
  const n = parseInt(String(v ?? ''), 10);
  return Number.isFinite(n) ? n : 0;
};
const scrollToEl = (el) => {
  const top = el.getBoundingClientRect().top + window.pageYOffset - OFFSET_TOP;
  window.scrollTo(0, Math.max(top, 0));
};
const cleanup = () => {
  try { sessionStorage.removeItem(KEY_SCROLL); } catch (e) {}
  try { sessionStorage.removeItem(KEY_URL); } catch (e) {}
  try { sessionStorage.removeItem(KEY_FOCUS); } catch (e) {}
};
const reveal = () => document.documentElement.classList.remove('preload');
// Vor jedem Submit: Scroll + URL speichern, offenes Cue merken, focus_cue merken
document.addEventListener('submit', function (ev) {
  try {
    sessionStorage.setItem(KEY_SCROLL, String(window.scrollY || 0));
    sessionStorage.setItem(KEY_URL, location.pathname);
    const open = document.querySelector('.song-collapse.show');
    if (open && open.id) sessionStorage.setItem(KEY_OPEN, open.id);
    const form = ev.target;
    const focusInput = form?.querySelector?.('input[name="focus_cue"]');
    if (focusInput?.value) sessionStorage.setItem(KEY_FOCUS, focusInput.value);
  } catch (e) {}
}, true);
// Beim Öffnen eines Cue: merken
document.addEventListener('shown.bs.collapse', function (e) {
  const el = e.target;
  if (el?.classList?.contains('song-collapse') && el.id) {
    try { sessionStorage.setItem(KEY_OPEN, el.id); } catch (e) {}
  }
});
document.addEventListener('DOMContentLoaded', function () {
  let scrollY = null, openId = null, focusId = null, sameUrl = false;
  try {
    scrollY = sessionStorage.getItem(KEY_SCROLL);
    openId = sessionStorage.getItem(KEY_OPEN);
    focusId = sessionStorage.getItem(KEY_FOCUS);
    sameUrl = sessionStorage.getItem(KEY_URL) === location.pathname;
  } catch (e) {}
  if (scrollY === null || !sameUrl) {
    cleanup();
    reveal();
    return;
  }
  cleanup();
  // 1) Priorität: Move ↑/↓ => genau zum betroffenen Cue
  if (focusId) {
    const card = document.getElementById('cue-' + focusId);
    const collapse = document.getElementById('songCollapse' + focusId);
    if (collapse && window.bootstrap) {
      const c = bootstrap.Collapse.getOrCreateInstance(collapse, { toggle: false });
      let done = false;
      const finish = () => { if (done) return; done = true; reveal(); };
      collapse.addEventListener('shown.bs.collapse', function () {
        scrollToEl(card || collapse);
        requestAnimationFrame(finish);
      }, { once: true });
      c.show();
      setTimeout(() => {
        if (!done) {
          if (card) scrollToEl(card); else window.scrollTo(0, safeInt(scrollY));
          finish();
        }
      }, 450);
      return;
    }
    if (card) scrollToEl(card); else window.scrollTo(0, safeInt(scrollY));
    reveal();
    return;
  }
  // 2) Sonst: zuletzt geöffnetes Cue wieder öffnen + dahin scrollen
  if (openId && window.bootstrap) {
    const el = document.getElementById(openId);
    if (el) {
      const c = bootstrap.Collapse.getOrCreateInstance(el, { toggle: false });
      let done = false;
      const finish = () => { if (done) return; done = true; reveal(); };
      el.addEventListener('shown.bs.collapse', function () {
        scrollToEl(el);
        requestAnimationFrame(finish);
      }, { once: true });
      c.show();
      setTimeout(() => {
        if (!done) {
          window.scrollTo(0, safeInt(scrollY));
          finish();
        }
      }, 350);
      return;
    }
  }
  // 3) Fallback: ScrollY
  window.scrollTo(0, safeInt(scrollY));
  requestAnimationFrame(reveal);
});

// Add Beam Row Logic
function addBeamRow() {
  const beamsRows = document.getElementById('beams-rows');
  if (!beamsRows) return;
  // Find the first .rig-item-row inside beamsRows as template
  const templateRow = beamsRows.querySelector('.rig-item-row');
  if (!templateRow) return;
  // Clone the row
  const newRow = templateRow.cloneNode(true);
  // Clear all input/select values in the new row
  newRow.querySelectorAll('input, select').forEach(el => {
    if (el.tagName === 'SELECT') el.selectedIndex = 0;
    else el.value = '';
  });
  beamsRows.appendChild(newRow);
}
// Attach event listener
const addBeamBtn = document.getElementById('add-beam-row');
if (addBeamBtn) {
  addBeamBtn.addEventListener('click', addBeamRow);
}

// Add Spot Row Logic
function addSpotRow() {
  const spotsRows = document.getElementById('spots-rows');
  if (!spotsRows) return;
  // Find the first .rig-item-row inside spotsRows as template
  const templateRow = spotsRows.querySelector('.rig-item-row');
  if (!templateRow) return;
  const newRow = templateRow.cloneNode(true);
  newRow.querySelectorAll('input, select').forEach(el => {
    if (el.tagName === 'SELECT') el.selectedIndex = 0;
    else el.value = '';
  });
  spotsRows.appendChild(newRow);
}
const addSpotBtn = document.getElementById('add-spot-row');
if (addSpotBtn) {
  addSpotBtn.addEventListener('click', addSpotRow);
}

// Add Wash Row Logic
function addWashRow() {
  const washesRows = document.getElementById('washes-rows');
  if (!washesRows) return;
  const templateRow = washesRows.querySelector('.rig-item-row');
  if (!templateRow) return;
  const newRow = templateRow.cloneNode(true);
  newRow.querySelectorAll('input, select').forEach(el => {
    if (el.tagName === 'SELECT') el.selectedIndex = 0;
    else el.value = '';
  });
  washesRows.appendChild(newRow);
}
const addWashBtn = document.getElementById('add-wash-row');
if (addWashBtn) {
  addWashBtn.addEventListener('click', addWashRow);
}

// Add Blinder Row Logic
function addBlinderRow() {
  const blindersRows = document.getElementById('blinders-rows');
  if (!blindersRows) return;
  const templateRow = blindersRows.querySelector('.rig-item-row');
  if (!templateRow) return;
  const newRow = templateRow.cloneNode(true);
  newRow.querySelectorAll('input, select').forEach(el => {
    if (el.tagName === 'SELECT') el.selectedIndex = 0;
    else el.value = '';
  });
  blindersRows.appendChild(newRow);
}
const addBlinderBtn = document.getElementById('add-blinder-row');
if (addBlinderBtn) {
  addBlinderBtn.addEventListener('click', addBlinderRow);
}

// Add Strobe Row Logic
function addStrobeRow() {
  const strobesRows = document.getElementById('strobes-rows');
  if (!strobesRows) return;
  const templateRow = strobesRows.querySelector('.rig-item-row');
  if (!templateRow) return;
  const newRow = templateRow.cloneNode(true);
  newRow.querySelectorAll('input, select').forEach(el => {
    if (el.tagName === 'SELECT') el.selectedIndex = 0;
    else el.value = '';
  });
  strobesRows.appendChild(newRow);
}
const addStrobeBtn = document.getElementById('add-strobe-row');
if (addStrobeBtn) {
  addStrobeBtn.addEventListener('click', addStrobeRow);
}

// Add Custom Device Row Logic
function addCustomDeviceRow() {
  const customRows = document.getElementById('custom-devices-rows');
  if (!customRows) return;
  const templateRow = customRows.querySelector('.rig-item-row');
  if (!templateRow) return;
  const newRow = templateRow.cloneNode(true);
  newRow.querySelectorAll('input, select').forEach(el => {
    if (el.tagName === 'SELECT') el.selectedIndex = 0;
    else el.value = '';
  });
  customRows.appendChild(newRow);
}
const addCustomBtn = document.getElementById('add-custom-device-row');
if (addCustomBtn) {
  addCustomBtn.addEventListener('click', addCustomDeviceRow);
}
