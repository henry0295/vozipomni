/*!
 * VozipOmni — widget de chat web
 * Uso: <script src="https://TU-DOMINIO/webchat/widget.js" data-key="CLAVE" data-api="https://TU-DOMINIO/api/messaging/webchat/public" async></script>
 *
 * - Sin dependencias; los estilos van aislados en un Shadow DOM.
 * - Peticiones "simples" (GET o POST text/plain) para no requerir preflight CORS.
 * - La sesión del visitante (token firmado por el servidor) se guarda en localStorage.
 */
(function () {
  'use strict';
  if (window.__vozipWebchatLoaded) return;
  window.__vozipWebchatLoaded = true;

  var script = document.currentScript || (function () {
    var s = document.querySelectorAll('script[data-key][src*="webchat/widget.js"]');
    return s[s.length - 1];
  })();
  if (!script) return;
  var KEY = script.getAttribute('data-key');
  var API = (script.getAttribute('data-api') || script.src.replace(/\/webchat\/widget\.js.*$/, '/api/messaging/webchat/public')).replace(/\/$/, '');
  if (!KEY) { console.warn('[VozipOmni] Falta data-key en el script del chat'); return; }

  var STORE = 'vozip_webchat_' + KEY;
  var state = { cfg: null, token: null, name: '', open: false, lastId: 0, unread: 0, timer: null, sending: false, ids: {} };
  try {
    var saved = JSON.parse(localStorage.getItem(STORE) || 'null');
    if (saved && saved.token) { state.token = saved.token; state.name = saved.name || ''; }
  } catch (e) { /* storage bloqueado */ }

  function url(path, q) {
    var u = API + '/' + encodeURIComponent(KEY) + path;
    if (q) {
      var parts = [];
      for (var k in q) if (q[k] !== undefined && q[k] !== null) parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(q[k]));
      if (parts.length) u += '?' + parts.join('&');
    }
    return u;
  }
  function get(path, q) {
    return fetch(url(path, q), { method: 'GET', credentials: 'omit' }).then(parse);
  }
  function post(path, body) {
    return fetch(url(path), {
      method: 'POST', credentials: 'omit',
      headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
      body: JSON.stringify(body || {})
    }).then(parse);
  }
  function parse(r) {
    return r.json().catch(function () { return {}; }).then(function (d) {
      if (!r.ok) { var err = new Error(firstError(d) || ('Error ' + r.status)); err.status = r.status; throw err; }
      return d;
    });
  }
  function firstError(d) {
    if (!d) return '';
    if (d.error) return d.error;
    if (d.detail) return d.detail;
    for (var k in d) if (Array.isArray(d[k])) return d[k][0];
    return '';
  }

  // ── DOM ───────────────────────────────────────────────────────────────────
  var host = document.createElement('div');
  host.id = 'vozip-webchat';
  var root = host.attachShadow ? host.attachShadow({ mode: 'open' }) : host;

  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === 'text') n.textContent = attrs[k];
      else if (k.indexOf('on') === 0) n.addEventListener(k.slice(2), attrs[k]);
      else n.setAttribute(k, attrs[k]);
    }
    (children || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }

  function css(color, side) {
    return '' +
      ':host{all:initial}*{box-sizing:border-box;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}' +
      '.btn{position:fixed;bottom:20px;' + side + ':20px;width:58px;height:58px;border-radius:50%;border:0;cursor:pointer;background:' + color + ';color:#fff;box-shadow:0 6px 20px rgba(0,0,0,.25);display:flex;align-items:center;justify-content:center;z-index:2147483000}' +
      '.btn:focus-visible,.panel button:focus-visible,.panel input:focus-visible,.panel textarea:focus-visible{outline:3px solid #2563eb;outline-offset:2px}' +
      '.badge{position:absolute;top:-2px;right:-2px;background:#dc2626;color:#fff;border-radius:10px;font-size:11px;min-width:20px;height:20px;padding:0 5px;display:flex;align-items:center;justify-content:center}' +
      '.panel{position:fixed;bottom:90px;' + side + ':20px;width:360px;max-width:calc(100vw - 32px);height:520px;max-height:calc(100vh - 120px);background:#fff;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.25);display:none;flex-direction:column;overflow:hidden;z-index:2147483000;color:#111827;font-size:14px}' +
      '.panel.open{display:flex}' +
      '.head{background:' + color + ';color:#fff;padding:14px 16px;display:flex;align-items:flex-start;gap:8px}' +
      '.head h2{margin:0;font-size:16px;font-weight:600}.head p{margin:2px 0 0;font-size:12px;opacity:.9}' +
      '.close{margin-left:auto;background:transparent;border:0;color:#fff;font-size:22px;line-height:1;cursor:pointer;padding:0 4px}' +
      '.body{flex:1;overflow-y:auto;padding:12px;background:#f3f4f6;display:flex;flex-direction:column;gap:6px}' +
      '.msg{max-width:80%;padding:8px 10px;border-radius:10px;white-space:pre-wrap;word-wrap:break-word;line-height:1.35}' +
      '.in{align-self:flex-end;background:' + color + ';color:#fff;border-bottom-right-radius:3px}' +
      '.out{align-self:flex-start;background:#fff;border:1px solid #e5e7eb;border-bottom-left-radius:3px}' +
      '.meta{font-size:10px;opacity:.7;margin-top:3px}.who{font-size:11px;font-weight:600;margin-bottom:2px;color:' + color + '}' +
      '.out a{color:' + color + '}.notice{font-size:12px;color:#6b7280;text-align:center;padding:4px}' +
      '.form{padding:16px;display:flex;flex-direction:column;gap:10px;overflow-y:auto}' +
      '.form label{font-size:12px;color:#374151;display:flex;flex-direction:column;gap:4px}' +
      'input,textarea{border:1px solid #d1d5db;border-radius:8px;padding:9px 10px;font-size:14px;width:100%;color:#111827;background:#fff}' +
      '.primary{background:' + color + ';color:#fff;border:0;border-radius:8px;padding:10px;font-size:14px;font-weight:600;cursor:pointer}' +
      '.primary[disabled]{opacity:.6;cursor:default}' +
      '.composer{display:flex;gap:6px;padding:10px;border-top:1px solid #e5e7eb;background:#fff}' +
      '.composer textarea{resize:none;height:42px;max-height:120px}' +
      '.send{background:' + color + ';color:#fff;border:0;border-radius:8px;width:44px;cursor:pointer;flex-shrink:0}' +
      '.err{color:#b91c1c;font-size:12px}.offline{background:#fef3c7;color:#92400e;font-size:12px;padding:8px 12px}' +
      '.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}';
  }

  var ICON_CHAT = '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
  var ICON_SEND = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4 20-7z"/></svg>';

  var ui = {};

  function build(cfg) {
    var side = cfg.position === 'left' ? 'left' : 'right';
    root.appendChild(el('style', { text: css(cfg.color || '#16a34a', side) }));

    ui.badge = el('span', { class: 'badge', 'aria-hidden': 'true' });
    ui.badge.style.display = 'none';
    ui.btn = el('button', { class: 'btn', type: 'button', 'aria-label': 'Abrir chat', 'aria-expanded': 'false', onclick: toggle });
    ui.btn.innerHTML = ICON_CHAT;
    ui.btn.appendChild(ui.badge);

    ui.panel = el('div', { class: 'panel', role: 'dialog', 'aria-modal': 'false', 'aria-label': cfg.title || 'Chat' });
    var head = el('div', { class: 'head' }, [
      el('div', null, [el('h2', { text: cfg.title || 'Chat' }), cfg.subtitle ? el('p', { text: cfg.subtitle }) : null]),
      el('button', { class: 'close', type: 'button', 'aria-label': 'Cerrar chat', text: '×', onclick: toggle })
    ]);
    ui.panel.appendChild(head);
    if (!cfg.online && cfg.offline_text) ui.panel.appendChild(el('div', { class: 'offline', role: 'status', text: cfg.offline_text }));
    ui.content = el('div', { style: 'flex:1;display:flex;flex-direction:column;min-height:0' });
    ui.panel.appendChild(ui.content);
    ui.live = el('div', { class: 'sr', 'aria-live': 'polite' });
    ui.panel.appendChild(ui.live);

    root.appendChild(ui.btn);
    root.appendChild(ui.panel);
    document.body.appendChild(host);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && state.open) toggle(); });

    if (state.token) showChat(); else showForm();
  }

  function showForm() {
    var cfg = state.cfg;
    ui.content.innerHTML = '';
    var err = el('p', { class: 'err', role: 'alert' });
    var name = el('input', { type: 'text', autocomplete: 'name', maxlength: '100' });
    var email = el('input', { type: 'email', autocomplete: 'email', maxlength: '200' });
    var msg = el('textarea', { rows: '3', maxlength: '2000' });
    var submit = el('button', { class: 'primary', type: 'submit', text: 'Iniciar chat' });
    var form = el('form', { class: 'form', novalidate: 'novalidate' }, [
      cfg.intro_text ? el('p', { text: cfg.intro_text, style: 'margin:0;color:#4b5563;font-size:13px' }) : null,
      el('label', null, [document.createTextNode('Nombre' + (cfg.require_name ? ' *' : '')), name]),
      el('label', null, [document.createTextNode('Email' + (cfg.require_email ? ' *' : '')), email]),
      el('label', null, [document.createTextNode('¿En qué te ayudamos? *'), msg]),
      err, submit
    ]);
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      err.textContent = '';
      if (!msg.value.trim()) { err.textContent = 'Escribe tu mensaje.'; msg.focus(); return; }
      submit.disabled = true;
      post('/session/', { name: name.value.trim(), email: email.value.trim(), page_url: location.href })
        .then(function (s) {
          state.token = s.token; state.name = s.name || '';
          try { localStorage.setItem(STORE, JSON.stringify({ token: s.token, name: state.name })); } catch (x) { /* ignore */ }
          return post('/messages/', { token: state.token, body: msg.value.trim() });
        })
        .then(function () { showChat(); })
        .catch(function (x) { err.textContent = x.message || 'No se pudo iniciar el chat.'; submit.disabled = false; });
    });
    ui.content.appendChild(form);
    setTimeout(function () { if (state.open) name.focus(); }, 50);
  }

  function showChat() {
    ui.content.innerHTML = '';
    state.lastId = 0; state.ids = {};
    ui.body = el('div', { class: 'body', role: 'log', 'aria-label': 'Mensajes' });
    ui.input = el('textarea', { placeholder: 'Escribe un mensaje…', 'aria-label': 'Mensaje', maxlength: '2000' });
    ui.input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });
    var sendBtn = el('button', { class: 'send', type: 'button', 'aria-label': 'Enviar', onclick: send });
    sendBtn.innerHTML = ICON_SEND;
    ui.content.appendChild(ui.body);
    ui.content.appendChild(el('div', { class: 'composer' }, [ui.input, sendBtn]));
    poll();
    schedule();
  }

  function fmtTime(iso) {
    try { return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); } catch (e) { return ''; }
  }

  function render(m) {
    if (state.ids[m.id]) return;
    state.ids[m.id] = true;
    var mine = m.direction === 'inbound'; // inbound = escrito por el visitante
    var bubble = el('div', { class: 'msg ' + (mine ? 'in' : 'out') });
    if (!mine && m.agent) bubble.appendChild(el('div', { class: 'who', text: m.agent }));
    if (m.has_media) {
      var link = el('a', { href: url('/media/' + m.id + '/', { token: state.token }), target: '_blank', rel: 'noopener noreferrer', text: '📎 ' + (m.filename || 'Archivo adjunto') });
      bubble.appendChild(el('div', null, [link]));
    }
    if (m.body) bubble.appendChild(el('div', { text: m.body }));
    bubble.appendChild(el('div', { class: 'meta', text: fmtTime(m.sent_at) }));
    ui.body.appendChild(bubble);
    if (!mine) {
      ui.live.textContent = (m.agent ? m.agent + ': ' : 'Nuevo mensaje: ') + (m.body || m.filename || '');
      if (!state.open) { state.unread++; updateBadge(); }
    }
  }

  function updateBadge() {
    ui.badge.textContent = state.unread > 9 ? '9+' : String(state.unread);
    ui.badge.style.display = state.unread ? 'flex' : 'none';
    ui.btn.setAttribute('aria-label', state.unread ? 'Abrir chat (' + state.unread + ' mensajes nuevos)' : 'Abrir chat');
  }

  function poll() {
    if (!state.token) return Promise.resolve();
    return get('/messages/', { token: state.token, after: state.lastId })
      .then(function (d) {
        var atBottom = ui.body.scrollHeight - ui.body.scrollTop - ui.body.clientHeight < 60;
        (d.messages || []).forEach(function (m) { render(m); if (m.id > state.lastId) state.lastId = m.id; });
        if (d.status === 'closed' && !ui.closedNotice) {
          ui.closedNotice = el('div', { class: 'notice', text: 'La conversación fue cerrada. Si escribes de nuevo, un asesor te atenderá.' });
          ui.body.appendChild(ui.closedNotice);
        } else if (d.status && d.status !== 'closed' && ui.closedNotice) {
          ui.closedNotice.remove(); ui.closedNotice = null;
        }
        if (atBottom || (d.messages || []).length) ui.body.scrollTop = ui.body.scrollHeight;
      })
      .catch(function (e) {
        if (e.status === 401) { // sesión expirada
          state.token = null;
          try { localStorage.removeItem(STORE); } catch (x) { /* ignore */ }
          showForm();
        }
      });
  }

  function schedule() {
    clearTimeout(state.timer);
    if (!state.token) return;
    var delay = state.open && document.visibilityState === 'visible' ? 3000 : 15000;
    state.timer = setTimeout(function () { poll().then(schedule, schedule); }, delay);
  }

  function send() {
    var text = (ui.input.value || '').trim();
    if (!text || state.sending) return;
    state.sending = true;
    ui.input.value = '';
    post('/messages/', { token: state.token, body: text })
      .then(function (d) {
        if (d.message) { render(d.message); if (d.message.id > state.lastId) state.lastId = d.message.id; }
        if (ui.closedNotice) { ui.closedNotice.remove(); ui.closedNotice = null; }
        ui.body.scrollTop = ui.body.scrollHeight;
      })
      .catch(function (e) {
        ui.input.value = text;
        ui.body.appendChild(el('div', { class: 'notice err', role: 'alert', text: e.message || 'No se pudo enviar' }));
      })
      .then(function () { state.sending = false; ui.input.focus(); });
  }

  function toggle() {
    state.open = !state.open;
    ui.panel.classList.toggle('open', state.open);
    ui.btn.setAttribute('aria-expanded', String(state.open));
    if (state.open) {
      state.unread = 0; updateBadge();
      var focusable = ui.panel.querySelector('textarea, input');
      if (focusable) setTimeout(function () { focusable.focus(); }, 50);
      if (ui.body) { poll(); ui.body.scrollTop = ui.body.scrollHeight; }
    } else {
      ui.btn.focus();
    }
    schedule();
  }

  document.addEventListener('visibilitychange', schedule);

  function init() {
    get('/config/').then(function (cfg) { state.cfg = cfg; build(cfg); })
      .catch(function (e) { console.warn('[VozipOmni] Chat no disponible:', e.message); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
