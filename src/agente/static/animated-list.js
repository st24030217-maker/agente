// React Bits AnimatedList Engine (Vanilla JS + CSS)
// Powered by @react-bits/AnimatedList-JS-CSS
(function () {
  'use strict';

  function applyAnimatedList(container, options = {}) {
    if (!container) return;

    const {
      stagger = 0.035,
      showGradients = true,
      fadeSize = 40,
      enableGlide = true
    } = options;

    container.classList.add('animated-list-viewport');

    const items = Array.from(container.querySelectorAll('.lead-card, .animated-list__item, [data-animated-item]'));
    if (!items.length) return;

    // Apply staggered entrance animation
    items.forEach((item, index) => {
      item.classList.add('animated-list-item');
      item.dataset.index = index;
      const delay = (index * stagger).toFixed(3);
      item.style.animationDelay = `${delay}s`;
    });

    // Setup scroll gradient masks
    function updateFades() {
      if (!showGradients) return;
      const span = fadeSize;
      const { scrollTop, scrollHeight, clientHeight } = container;
      const top = Math.min(span, Math.max(0, scrollTop));
      const bottom = Math.min(span, Math.max(0, scrollHeight - clientHeight - scrollTop));
      container.style.setProperty('--al-fade-top', `${top.toFixed(1)}px`);
      container.style.setProperty('--al-fade-bottom', `${bottom.toFixed(1)}px`);
    }

    if (container._alScroll) {
      container.removeEventListener('scroll', container._alScroll);
    }
    container._alScroll = updateFades;
    container.addEventListener('scroll', updateFades, { passive: true });
    updateFades();

    // Gliding indicator ring
    if (enableGlide) {
      let indicator = container.querySelector(':scope > .al-indicator');
      if (!indicator) {
        indicator = document.createElement('div');
        indicator.className = 'al-indicator';
        container.appendChild(indicator);
      }

      let motion = { y: 0, h: 0, vy: 0, vh: 0, ty: 0, th: 0, ready: false };
      let raf = 0;
      let last = 0;

      function frame(now) {
        raf = 0;
        const dt = Math.min(0.05, (now - last) / 1000 || 0);
        last = now;
        const omega = 30;
        const zeta = 0.78;
        const steps = Math.max(1, Math.ceil(dt / (1 / 240)));
        const h = dt / steps;
        for (let i = 0; i < steps; i++) {
          motion.vy += (omega * omega * (motion.ty - motion.y) - 2 * zeta * omega * motion.vy) * h;
          motion.vh += (omega * omega * (motion.th - motion.h) - 2 * zeta * omega * motion.vh) * h;
          motion.y += motion.vy * h;
          motion.h += motion.vh * h;
        }
        indicator.style.transform = `translate3d(0, ${motion.y.toFixed(2)}px, 0)`;
        indicator.style.height = `${motion.h.toFixed(2)}px`;

        const moving =
          Math.abs(motion.ty - motion.y) > 0.05 ||
          Math.abs(motion.th - motion.h) > 0.05 ||
          Math.abs(motion.vy) + Math.abs(motion.vh) > 0.5;

        if (moving) {
          raf = requestAnimationFrame(frame);
        } else {
          motion.y = motion.ty;
          motion.h = motion.th;
          motion.vy = motion.vh = 0;
        }
      }

      function place(targetItem) {
        if (!targetItem) {
          indicator.style.opacity = '0';
          return;
        }
        indicator.style.opacity = '1';
        motion.ty = targetItem.offsetTop;
        motion.th = targetItem.offsetHeight;

        if (!motion.ready) {
          motion.y = motion.ty;
          motion.h = motion.th;
          motion.ready = true;
          indicator.style.transform = `translate3d(0, ${motion.y.toFixed(2)}px, 0)`;
          indicator.style.height = `${motion.h.toFixed(2)}px`;
          return;
        }

        if (!raf) {
          last = performance.now();
          raf = requestAnimationFrame(frame);
        }
      }

      items.forEach(item => {
        item.addEventListener('pointerenter', () => place(item));
      });

      container.addEventListener('pointerleave', () => {
        indicator.style.opacity = '0';
        motion.ready = false;
      });
    }
  }

  window.applyAnimatedList = applyAnimatedList;
})();
