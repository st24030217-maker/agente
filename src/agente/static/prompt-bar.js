// =============================================================================
// SEBAX AI - PROMPTBAR COMPONENT (React Bits @react-bits/PromptBar-JS-CSS)
// Interactive Chat Composer with / Commands, Model Picker, Equalizer Dictation & Sparks
// =============================================================================
(function () {
  function initPromptBar() {
    const root = document.querySelector(".prompt-bar");
    const input = document.getElementById("user-input");
    const sendBtn = document.getElementById("btn-send");
    const micBtn = document.getElementById("btn-mic");
    const menu = document.getElementById("prompt-menu");
    const sparkCanvas = document.getElementById("prompt-sparks");
    const modelBtn = document.getElementById("prompt-model-btn");
    const plusBtn = document.getElementById("prompt-plus-btn");

    if (!input || !sendBtn) return;

    // 1. Auto-resize textarea
    function autoResize() {
      input.style.height = "auto";
      const newHeight = Math.min(input.scrollHeight, 120);
      input.style.height = (newHeight > 24 ? newHeight : 24) + "px";
      
      const hasText = input.value.trim().length > 0;
      if (hasText) {
        sendBtn.setAttribute("data-armed", "");
      } else {
        sendBtn.removeAttribute("data-armed");
      }
    }
    input.addEventListener("input", autoResize);

    // 2. Slash Commands Definition
    const commands = [
      { key: "/prospectar", name: "/prospectar", desc: "Ronda inmediata de prospección comercial en La Laguna" },
      { key: "/demo", name: "/demo", desc: "Generar prototipo web interactivo para cliente" },
      { key: "/agenda", name: "/agenda", desc: "Consultar reuniones y citas agendadas" },
      { key: "/whatsapp", name: "/whatsapp", desc: "Verificar puente Baileys y Meta Cloud API" },
      { key: "/reiniciar", name: "/reiniciar", desc: "Limpiar historial de conversación y memoria" }
    ];

    function showMenu(items, kind = "command") {
      if (!menu) return;
      menu.innerHTML = "";
      menu.setAttribute("data-kind", kind);

      items.forEach((item) => {
        const row = document.createElement("button");
        row.type = "button";
        row.className = "prompt-bar__row";
        row.innerHTML = `
          <span class="prompt-bar__row-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
            </svg>
          </span>
          <span class="prompt-bar__row-name">${item.name}</span>
          <span class="prompt-bar__row-desc">${item.desc || ""}</span>
        `;
        row.addEventListener("mousedown", (e) => {
          e.preventDefault();
          selectCommand(item.key);
        });
        menu.appendChild(row);
      });

      menu.style.display = "block";
    }

    function hideMenu() {
      if (menu) menu.style.display = "none";
    }

    function selectCommand(cmd) {
      hideMenu();
      if (cmd === "/prospectar") {
        input.value = "Inicia una ronda de prospección en Torreón para nuevos clientes comerciales.";
      } else if (cmd === "/demo") {
        if (typeof openDemosTab === "function") openDemosTab();
        input.value = "Genera un prototipo web de alta conversión.";
      } else if (cmd === "/agenda") {
        if (typeof openAgendaModal === "function") openAgendaModal();
        return;
      } else if (cmd === "/whatsapp") {
        if (typeof checkWhatsAppStatus === "function") checkWhatsAppStatus();
        return;
      } else if (cmd === "/reiniciar") {
        if (typeof resetChatContext === "function") resetChatContext();
        return;
      } else {
        input.value = cmd + " ";
      }
      autoResize();
      input.focus();
    }

    // 3. Command Popup on typing '/'
    input.addEventListener("keyup", (e) => {
      const val = input.value;
      if (val.startsWith("/")) {
        const query = val.toLowerCase();
        const matches = commands.filter((c) => c.key.toLowerCase().startsWith(query));
        if (matches.length > 0) {
          showMenu(matches, "command");
        } else {
          hideMenu();
        }
      } else {
        hideMenu();
      }
    });

    // 4. Plus Button Menu
    if (plusBtn) {
      plusBtn.addEventListener("click", (e) => {
        e.preventDefault();
        if (menu && menu.style.display === "block") {
          hideMenu();
        } else {
          showMenu(commands, "command");
        }
      });
    }

    // 5. Model Switcher
    if (modelBtn) {
      const models = [
        { key: "gemini", name: "Gemini 3.5 Flash", desc: "Motor cognitivo ultra-rápido" },
        { key: "autopilot", name: "Autopilot 24/7", desc: "Agente autónomo de prospección continua" }
      ];
      modelBtn.addEventListener("click", (e) => {
        e.preventDefault();
        showMenu(models, "model");
      });
    }

    // Close menu when clicking outside
    document.addEventListener("pointerdown", (e) => {
      if (root && !root.contains(e.target)) {
        hideMenu();
      }
    });

    // 6. Enter to send
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        hideMenu();
        if (typeof window.sendUserOrder === "function") {
          window.sendUserOrder();
        } else {
          sendBtn.click();
        }
      }
    });

    // 7. Sparks Particle Effect
    if (sparkCanvas) {
      const ctx = sparkCanvas.getContext("2d");
      let sparks = [];
      let width = (sparkCanvas.width = sparkCanvas.offsetWidth || 300);
      let height = (sparkCanvas.height = sparkCanvas.offsetHeight || 50);

      window.addEventListener("resize", () => {
        width = sparkCanvas.width = sparkCanvas.offsetWidth || 300;
        height = sparkCanvas.height = sparkCanvas.offsetHeight || 50;
      });

      function addSparks() {
        for (let i = 0; i < 4; i++) {
          sparks.push({
            x: Math.random() * width,
            y: height - 2,
            vx: (Math.random() - 0.5) * 1.5,
            vy: -Math.random() * 2 - 0.5,
            life: 1.0,
            decay: 0.03 + Math.random() * 0.04,
            size: Math.random() * 2 + 1,
            color: Math.random() > 0.5 ? "#a855f7" : "#32d466"
          });
        }
      }

      input.addEventListener("input", addSparks);

      function renderSparks() {
        requestAnimationFrame(renderSparks);
        ctx.clearRect(0, 0, width, height);
        for (let i = sparks.length - 1; i >= 0; i--) {
          const p = sparks[i];
          p.x += p.vx;
          p.y += p.vy;
          p.life -= p.decay;
          if (p.life <= 0) {
            sparks.splice(i, 1);
            continue;
          }
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
          ctx.fillStyle = p.color;
          ctx.globalAlpha = p.life * 0.7;
          ctx.fill();
        }
        ctx.globalAlpha = 1.0;
      }
      renderSparks();
    }
  }

  window.addEventListener("DOMContentLoaded", initPromptBar);
})();
