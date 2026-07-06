/* ============================================================
   NEKOVA Docs — Animations
   Scroll reveal, 3D tilt, and a lightweight canvas "signal field"
   behind the hero — restrained on purpose. One orchestrated
   moment (the hero) rather than effects scattered everywhere.
   ============================================================ */

(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Scroll reveal ---------- */
  function initReveal() {
    var els = document.querySelectorAll('.reveal');
    if (!els.length) return;

    if (reduceMotion || !('IntersectionObserver' in window)) {
      els.forEach(function (el) { el.classList.add('is-visible'); });
      return;
    }

    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: '0px 0px -8% 0px' }
    );
    els.forEach(function (el) { io.observe(el); });
  }

  /* ---------- 3D tilt on pillar cards ---------- */
  function initTilt() {
    if (reduceMotion) return;
    var cards = document.querySelectorAll('[data-tilt]');
    cards.forEach(function (card) {
      var maxTilt = 8; // degrees — restrained, not a gimmick

      card.addEventListener('mousemove', function (e) {
        var rect = card.getBoundingClientRect();
        var x = (e.clientX - rect.left) / rect.width;  // 0..1
        var y = (e.clientY - rect.top) / rect.height;  // 0..1
        var rotateY = (x - 0.5) * maxTilt * 2;
        var rotateX = (0.5 - y) * maxTilt * 2;
        card.style.transform =
          'rotateX(' + rotateX.toFixed(2) + 'deg) rotateY(' + rotateY.toFixed(2) + 'deg)';
      });

      card.addEventListener('mouseleave', function () {
        card.style.transform = 'rotateX(0deg) rotateY(0deg)';
      });
    });
  }

  /* ---------- Hero canvas: a quiet field of drifting nodes,
     occasionally linking — a "signal" being thought through.
     Deliberately calm, not a particle-explosion effect. ---------- */
  function initHeroCanvas() {
    var canvas = document.querySelector('.hero-canvas');
    if (!canvas || reduceMotion) return;
    var ctx = canvas.getContext('2d');
    var w, h, dpr = Math.min(window.devicePixelRatio || 1, 2);
    var nodes = [];
    var NODE_COUNT = 46;
    var LINK_DIST = 130;

    function resize() {
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function makeNodes() {
      nodes = [];
      for (var i = 0; i < NODE_COUNT; i++) {
        nodes.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * 0.18,
          vy: (Math.random() - 0.5) * 0.18,
          r: Math.random() * 1.6 + 0.6
        });
      }
    }

    function step() {
      ctx.clearRect(0, 0, w, h);
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        n.x += n.vx; n.y += n.vy;
        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;
      }
      for (var i = 0; i < nodes.length; i++) {
        for (var j = i + 1; j < nodes.length; j++) {
          var a = nodes[i], b = nodes[j];
          var dx = a.x - b.x, dy = a.y - b.y;
          var dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < LINK_DIST) {
            ctx.globalAlpha = (1 - dist / LINK_DIST) * 0.35;
            ctx.strokeStyle = '#2ECC71';
            ctx.lineWidth = 0.6;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }
      ctx.globalAlpha = 0.8;
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        ctx.beginPath();
        ctx.fillStyle = '#3DDC84';
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      requestAnimationFrame(step);
    }

    resize();
    makeNodes();
    window.addEventListener('resize', function () {
      resize();
      makeNodes();
    });
    requestAnimationFrame(step);
  }

  /* ---------- Copy buttons on code blocks ---------- */
  function initCopyButtons() {
    document.querySelectorAll('pre').forEach(function (pre) {
      if (pre.querySelector('.code-copy-btn')) return;
      var btn = document.createElement('button');
      btn.className = 'code-copy-btn';
      btn.type = 'button';
      btn.textContent = 'Copy';
      btn.addEventListener('click', function () {
        var code = pre.querySelector('code');
        var text = code ? code.textContent : pre.textContent;
        navigator.clipboard.writeText(text).then(function () {
          btn.textContent = 'Copied';
          btn.classList.add('copied');
          setTimeout(function () {
            btn.textContent = 'Copy';
            btn.classList.remove('copied');
          }, 1600);
        });
      });
      pre.appendChild(btn);
    });
  }

  /* ---------- Active sidebar / TOC link tracking ---------- */
  function initActiveTracking() {
    var sidebarLinks = document.querySelectorAll('.docs-sidebar a[href]');
    var currentPath = window.location.pathname.replace(/index\.html$/, '');
    sidebarLinks.forEach(function (a) {
      var href = a.getAttribute('href').replace(/index\.html$/, '');
      if (href === currentPath || (href !== '/' && currentPath.endsWith(href))) {
        a.classList.add('active');
      }
    });

    var tocLinks = document.querySelectorAll('.docs-toc a[href^="#"]');
    if (!tocLinks.length || reduceMotion === undefined) return;
    var headings = [];
    tocLinks.forEach(function (a) {
      var id = a.getAttribute('href').slice(1);
      var el = document.getElementById(id);
      if (el) headings.push({ link: a, el: el });
    });
    if (!headings.length || !('IntersectionObserver' in window)) return;

    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          var match = headings.find(function (h) { return h.el === entry.target; });
          if (!match) return;
          if (entry.isIntersecting) {
            tocLinks.forEach(function (l) { l.classList.remove('active'); });
            match.link.classList.add('active');
          }
        });
      },
      { rootMargin: '-15% 0px -70% 0px' }
    );
    headings.forEach(function (h) { io.observe(h.el); });
  }

  /* ---------- Mobile sidebar toggle ---------- */
  function initMobileToggle() {
    var btn = document.querySelector('.docs-mobile-toggle');
    var sidebar = document.querySelector('.docs-sidebar');
    if (!btn || !sidebar) return;
    btn.addEventListener('click', function () {
      sidebar.classList.toggle('is-open');
      btn.textContent = sidebar.classList.contains('is-open') ? 'Hide navigation' : 'Show navigation';
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initReveal();
    initTilt();
    initHeroCanvas();
    initCopyButtons();
    initActiveTracking();
    initMobileToggle();
  });
})();