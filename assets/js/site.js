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
})();
