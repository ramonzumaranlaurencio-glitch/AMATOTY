/**
 * AMIA – Asistente Inteligente AMATOTY
 * Widget flotante de chat con Gemini 2.5
 * Se auto-inicializa en cualquier página donde se incluya este script.
 */
(function () {
  "use strict";

  // ── Detectar base URL del backend ──────────────────────────────────────────
  function backendBase() {
    const h = window.location.hostname;
    if (h === "localhost" || h === "127.0.0.1") {
      return window.location.origin; // mismo servidor local
    }
    // En producción el frontend y backend van en el mismo dominio de Render
    return window.location.origin;
  }

  const API_URL = backendBase() + "/api/chat";

  // ── Historial de conversación ──────────────────────────────────────────────
  let history = [];

  // ── Estilos ────────────────────────────────────────────────────────────────
  const CSS = `
    #amia-fab {
      position:fixed; bottom:24px; right:24px; z-index:9999;
      width:58px; height:58px; border-radius:50%;
      background:linear-gradient(135deg,#ff9900,#d81b60);
      box-shadow:0 4px 18px rgba(0,0,0,.28);
      border:none; cursor:pointer; display:flex;
      align-items:center; justify-content:center;
      font-size:26px; color:#fff; transition:transform .2s;
    }
    #amia-fab:hover { transform:scale(1.1); }
    #amia-panel {
      position:fixed; bottom:92px; right:24px; z-index:9998;
      width:340px; max-width:calc(100vw - 32px);
      background:#fff; border-radius:18px;
      box-shadow:0 8px 40px rgba(0,0,0,.22);
      display:flex; flex-direction:column;
      overflow:hidden; font-family:Arial,sans-serif;
      transition:opacity .25s, transform .25s;
      opacity:0; transform:translateY(16px) scale(.97);
      pointer-events:none;
    }
    #amia-panel.open {
      opacity:1; transform:translateY(0) scale(1); pointer-events:all;
    }
    #amia-header {
      background:linear-gradient(90deg,#ff9900,#d81b60);
      color:#fff; padding:14px 16px 10px 16px;
      display:flex; align-items:center; gap:10px;
    }
    #amia-avatar {
      width:36px; height:36px; border-radius:50%;
      background:rgba(255,255,255,.25);
      display:flex; align-items:center; justify-content:center;
      font-size:20px; flex-shrink:0;
    }
    #amia-header-text { flex:1; }
    #amia-header-text strong { display:block; font-size:1em; }
    #amia-header-text span { font-size:.78em; opacity:.88; }
    #amia-close {
      background:none; border:none; color:#fff;
      font-size:20px; cursor:pointer; line-height:1; padding:2px 4px;
    }
    #amia-messages {
      flex:1; overflow-y:auto; padding:14px 12px 8px 12px;
      min-height:220px; max-height:380px;
      display:flex; flex-direction:column; gap:8px;
      background:#fafafa;
    }
    .amia-bubble {
      max-width:88%; padding:9px 13px; border-radius:14px;
      line-height:1.45; font-size:.92em; word-break:break-word;
    }
    .amia-bubble.bot {
      background:#fff; color:#1f2937;
      border:1px solid #e5e7eb;
      align-self:flex-start; border-bottom-left-radius:4px;
    }
    .amia-bubble.user {
      background:linear-gradient(135deg,#ff9900,#f59e0b);
      color:#fff; align-self:flex-end;
      border-bottom-right-radius:4px;
    }
    .amia-bubble.typing { color:#9ca3af; font-style:italic; }
    #amia-input-row {
      display:flex; gap:8px; padding:10px 12px 12px 12px;
      border-top:1px solid #e5e7eb; background:#fff;
    }
    #amia-input {
      flex:1; border:1px solid #d1d5db; border-radius:10px;
      padding:8px 12px; font-size:.92em; outline:none;
      resize:none; font-family:inherit;
      transition:border-color .2s;
    }
    #amia-input:focus { border-color:#ff9900; }
    #amia-send {
      background:linear-gradient(135deg,#ff9900,#d81b60);
      border:none; border-radius:10px; color:#fff;
      padding:8px 14px; cursor:pointer; font-size:18px;
      transition:opacity .2s;
    }
    #amia-send:disabled { opacity:.4; cursor:default; }
    #amia-badge {
      position:absolute; top:2px; right:2px;
      background:#d81b60; color:#fff; border-radius:50%;
      width:18px; height:18px; font-size:11px;
      display:none; align-items:center; justify-content:center;
      font-weight:bold; pointer-events:none;
    }
  `;

  function injectStyles() {
    if (document.getElementById("amia-styles")) return;
    const s = document.createElement("style");
    s.id = "amia-styles";
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function buildWidget() {
    // FAB button
    const fab = document.createElement("button");
    fab.id = "amia-fab";
    fab.setAttribute("aria-label", "Abrir asistente AMIA");
    fab.innerHTML = "💬";
    const badge = document.createElement("span");
    badge.id = "amia-badge";
    badge.textContent = "1";
    fab.appendChild(badge);

    // Panel
    const panel = document.createElement("div");
    panel.id = "amia-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Chat con AMIA");
    panel.innerHTML = `
      <div id="amia-header">
        <div id="amia-avatar">🤖</div>
        <div id="amia-header-text">
          <strong>AMIA</strong>
          <span>Asistente AMATOTY · Gemini 2.5</span>
        </div>
        <button id="amia-close" aria-label="Cerrar chat">✕</button>
      </div>
      <div id="amia-messages" role="log" aria-live="polite"></div>
      <div id="amia-input-row">
        <textarea id="amia-input" rows="1" placeholder="Escribe tu pregunta..." aria-label="Mensaje"></textarea>
        <button id="amia-send" aria-label="Enviar">➤</button>
      </div>
    `;

    document.body.appendChild(fab);
    document.body.appendChild(panel);

    // ── Lógica ──────────────────────────────────────────────────────────────
    const messages = panel.querySelector("#amia-messages");
    const input = panel.querySelector("#amia-input");
    const sendBtn = panel.querySelector("#amia-send");
    const closeBtn = panel.querySelector("#amia-close");
    let isOpen = false;
    let hasShownBadge = false;

    function openPanel() {
      isOpen = true;
      panel.classList.add("open");
      fab.innerHTML = "✕";
      badge.style.display = "none";
      setTimeout(() => input.focus(), 150);
    }

    function closePanel() {
      isOpen = false;
      panel.classList.remove("open");
      fab.innerHTML = "💬";
    }

    fab.addEventListener("click", () => (isOpen ? closePanel() : openPanel()));
    closeBtn.addEventListener("click", closePanel);

    // Mostrar badge con retraso para invitar al usuario
    setTimeout(() => {
      if (!isOpen && !hasShownBadge) {
        badge.style.display = "flex";
        hasShownBadge = true;
      }
    }, 4000);

    function addBubble(text, role) {
      const div = document.createElement("div");
      div.className = "amia-bubble " + role;
      div.textContent = text;
      messages.appendChild(div);
      messages.scrollTop = messages.scrollHeight;
      return div;
    }

    // Mensaje de bienvenida
    addBubble("¡Hola! 👋 Soy AMIA, tu asistente de AMATOTY. ¿En qué te puedo ayudar hoy?", "bot");

    async function sendMessage() {
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      input.style.height = "auto";
      sendBtn.disabled = true;

      addBubble(text, "user");
      history.push({ role: "user", text });

      const typingBubble = addBubble("Escribiendo...", "bot typing");

      try {
        const res = await fetch(API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, history: history.slice(-10) }),
        });
        const data = await res.json();
        const reply = data.reply || data.error || "Sin respuesta.";
        typingBubble.textContent = reply;
        typingBubble.classList.remove("typing");
        history.push({ role: "model", text: reply });
      } catch (err) {
        typingBubble.textContent = "Error de conexión. ¿El servidor está activo?";
        typingBubble.classList.remove("typing");
      } finally {
        sendBtn.disabled = false;
        input.focus();
      }
    }

    sendBtn.addEventListener("click", sendMessage);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto-resize textarea
    input.addEventListener("input", () => {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, 90) + "px";
    });
  }

  // ── Inicialización ─────────────────────────────────────────────────────────
  function init() {
    injectStyles();
    buildWidget();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
