/* Site script. Three small jobs, nothing else. */
(function () {
  'use strict';

  // 1. Phone menu.
  var btn = document.querySelector('.menu-btn');
  var nav = document.getElementById('site-nav');
  if (btn && nav) {
    var setOpen = function (open) {
      btn.setAttribute('aria-expanded', String(open));
      btn.textContent = open ? 'Close' : 'Menu';
      nav.classList.toggle('is-open', open);
    };
    btn.addEventListener('click', function () {
      setOpen(btn.getAttribute('aria-expanded') !== 'true');
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.classList.contains('is-open')) {
        setOpen(false);
        btn.focus();
      }
    });
  }

  // 2. Videos: load YouTube's player only when someone taps play.
  document.querySelectorAll('[data-yt]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      var id = link.getAttribute('data-yt');
      if (!/^[A-Za-z0-9_-]{11}$/.test(id)) return; // odd link: just open YouTube
      e.preventDefault();
      var frame = document.createElement('iframe');
      frame.src = 'https://www.youtube-nocookie.com/embed/' + id + '?autoplay=1&rel=0';
      frame.title = link.getAttribute('data-title') || 'YouTube video';
      frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
      frame.allowFullscreen = true;
      var wrap = document.createElement('div');
      wrap.className = 'video__frame';
      wrap.appendChild(frame);
      link.replaceWith(wrap);
    });
  });

  // 3. CV page: a print button (only shown when JS runs).
  document.querySelectorAll('.js-print').forEach(function (b) {
    b.hidden = false;
    b.addEventListener('click', function () { window.print(); });
  });

  // 4. Long lists: show the first few items with a "Show all N" button.
  //    Mark a list (ul, ol, dl or tbody) with data-preview="5". Lists with
  //    only a few more than that stay fully open. Without JS, and when
  //    printing, everything shows (.is-folded only hides on screen).
  var folds = [];
  document.querySelectorAll('[data-preview]').forEach(function (list) {
    var keep = parseInt(list.getAttribute('data-preview'), 10) || 5;
    var items = Array.prototype.slice.call(list.children);
    if (items.length <= keep + 3) return;
    var extra = items.slice(keep);
    var more = document.createElement('button');
    more.type = 'button';
    more.className = 'more-btn';
    var setOpen = function (open) {
      extra.forEach(function (el) { el.classList.toggle('is-folded', !open); });
      more.setAttribute('aria-expanded', String(open));
      more.textContent = open ? 'Show fewer' : 'Show all ' + items.length;
    };
    more.addEventListener('click', function () {
      var open = more.getAttribute('aria-expanded') !== 'true';
      setOpen(open);
      if (!open) more.scrollIntoView({ block: 'nearest' });
      syncAll();
    });
    setOpen(false);
    (list.tagName === 'TBODY' ? list.closest('table') : list).insertAdjacentElement('afterend', more);
    folds.push({ btn: more, set: setOpen });
  });

  // 5. "Expand all" button (CV and Publications pages) for the lists above.
  var allBtns = document.querySelectorAll('.js-expand-all');
  function syncAll() {
    var allOpen = folds.length > 0 && folds.every(function (f) { return f.btn.getAttribute('aria-expanded') === 'true'; });
    allBtns.forEach(function (b) { b.textContent = allOpen ? 'Collapse all' : 'Expand all'; b.setAttribute('aria-pressed', String(allOpen)); });
  }
  allBtns.forEach(function (b) {
    if (!folds.length) return;
    b.hidden = false;
    b.addEventListener('click', function () {
      var open = b.getAttribute('aria-pressed') !== 'true';
      folds.forEach(function (f) { f.set(open); });
      syncAll();
    });
  });
  syncAll();
})();
