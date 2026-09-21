/* SCIA site scripts: mobile nav, photo carousel, publication filter. No dependencies. */
(function () {
  'use strict';

  /* ---------- mobile nav ---------- */
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && links.classList.contains('open')) {
        links.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.focus();
      }
    });
  }

  /* ---------- carousel ----------
     Follows the WAI-ARIA APG carousel pattern: auto-rotation is paused on
     hover/focus, has an explicit pause/play control (WCAG 2.2.2), does not
     start at all under prefers-reduced-motion, and the live region only
     announces slides the user has chosen (not automatic rotation). */
  var carousel = document.querySelector('.carousel');
  if (carousel) {
    var slides = Array.prototype.slice.call(carousel.querySelectorAll('.slide'));
    var dots = Array.prototype.slice.call(carousel.querySelectorAll('.carousel-dots button'));
    var prev = carousel.querySelector('.carousel-btn.prev');
    var next = carousel.querySelector('.carousel-btn.next');
    var playBtn = carousel.querySelector('.carousel-play');
    var status = carousel.querySelector('.carousel-status');
    var index = 0;
    var timer = null;
    var INTERVAL = 7000;
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var userPaused = reduceMotion || slides.length < 2;   // explicit pause state (button)
    var hovering = false;                                  // transient pause (hover / focus)

    function show(i, announce) {
      index = (i + slides.length) % slides.length;
      slides.forEach(function (s, k) {
        var active = k === index;
        s.classList.toggle('is-active', active);
        s.setAttribute('aria-hidden', active ? 'false' : 'true');
      });
      dots.forEach(function (d, k) {
        d.setAttribute('aria-current', k === index ? 'true' : 'false');
      });
      if (status) {
        status.setAttribute('aria-live', announce ? 'polite' : 'off');
        status.textContent = 'Photo ' + (index + 1) + ' of ' + slides.length;
      }
    }
    function stop() { if (timer) { window.clearInterval(timer); timer = null; } }
    function maybeStart() {
      stop();
      if (userPaused || hovering) return;
      timer = window.setInterval(function () { show(index + 1, false); }, INTERVAL);
    }
    function setPaused(p) {
      userPaused = p;
      if (playBtn) {
        playBtn.setAttribute('aria-pressed', p ? 'true' : 'false');
        playBtn.setAttribute('aria-label', p ? 'Play automatic slideshow' : 'Pause automatic slideshow');
      }
      maybeStart();
    }
    function userGo(i) { show(i, true); maybeStart(); }

    if (prev) prev.addEventListener('click', function () { userGo(index - 1); });
    if (next) next.addEventListener('click', function () { userGo(index + 1); });
    dots.forEach(function (d, k) { d.addEventListener('click', function () { userGo(k); }); });
    if (playBtn) playBtn.addEventListener('click', function () { setPaused(!userPaused); });

    carousel.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft') { userGo(index - 1); e.preventDefault(); }
      if (e.key === 'ArrowRight') { userGo(index + 1); e.preventDefault(); }
    });
    carousel.addEventListener('mouseenter', function () { hovering = true; stop(); });
    carousel.addEventListener('mouseleave', function () { hovering = false; maybeStart(); });
    carousel.addEventListener('focusin', function () { hovering = true; stop(); });
    carousel.addEventListener('focusout', function (e) {
      if (!carousel.contains(e.relatedTarget)) { hovering = false; maybeStart(); }
    });
    document.addEventListener('visibilitychange', function () { document.hidden ? stop() : maybeStart(); });

    // touch swipe
    var startX = null;
    carousel.addEventListener('touchstart', function (e) { startX = e.touches[0].clientX; }, { passive: true });
    carousel.addEventListener('touchend', function (e) {
      if (startX === null) return;
      var dx = e.changedTouches[0].clientX - startX;
      if (Math.abs(dx) > 40) userGo(dx < 0 ? index + 1 : index - 1);
      startX = null;
    }, { passive: true });

    show(0, false);
    setPaused(userPaused);
  }

  /* ---------- publication filter ---------- */
  var search = document.getElementById('pub-search');
  if (search) {
    var groups = Array.prototype.slice.call(document.querySelectorAll('.pub-group'));
    var pubs = Array.prototype.slice.call(document.querySelectorAll('.pub'));
    var noResults = document.getElementById('pub-no-results');
    var count = document.getElementById('pub-count');
    var total = pubs.length;
    if (count) count.textContent = total + ' entries';

    function normalize(s) {
      return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
    }
    pubs.forEach(function (p) { p.dataset.text = normalize(p.textContent); });

    function filter() {
      var q = normalize(search.value.trim());
      var terms = q ? q.split(/\s+/) : [];
      var shown = 0;
      pubs.forEach(function (p) {
        var ok = terms.every(function (t) { return p.dataset.text.indexOf(t) !== -1; });
        p.classList.toggle('is-hidden', !ok);
        if (ok) shown++;
      });
      groups.forEach(function (g) {
        var any = g.querySelector('.pub:not(.is-hidden)');
        g.classList.toggle('is-hidden', !any);
      });
      if (noResults) noResults.hidden = shown > 0;
      if (count) count.textContent = (terms.length ? shown + ' of ' + total : total) + ' entries';
    }
    search.addEventListener('input', filter);
    // support ?q= in the URL
    var m = /[?&]q=([^&]*)/.exec(window.location.search);
    if (m) { search.value = decodeURIComponent(m[1].replace(/\+/g, ' ')); filter(); }
  }

  /* ---------- visitor counter ----------
     Reads the site-wide total from GoatCounter's public counter endpoint
     (enabled in its settings) and fills the retro counter in the footer.
     The footer element stays hidden if the request fails. */
  var counter = document.getElementById('visit-counter');
  if (counter && window.fetch) {
    fetch('https://scia.goatcounter.com/counter/TOTAL.json', { credentials: 'omit' })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (d) {
        var n = parseInt(String(d.count).replace(/\D/g, ''), 10);   // "1 234" -> 1234
        if (isNaN(n)) return;
        var digits = String(n);
        while (digits.length < 6) digits = '0' + digits;
        var box = counter.querySelector('.counter-digits');
        box.textContent = '';
        digits.split('').forEach(function (ch) {
          var cell = document.createElement('span');
          cell.textContent = ch;
          box.appendChild(cell);
        });
        document.getElementById('visit-counter-text').textContent = n.toLocaleString('en-US') + ' visits';
        counter.hidden = false;
      })
      .catch(function () {});
  }
})();
