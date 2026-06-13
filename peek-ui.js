// Slide peek: a link marked `.peek` opens ONE slide from another deck in a
// modal overlay — no navigation, no deck controls. The student sees the single
// slide that jogs their memory and closes it (Esc / backdrop / ×) to return to
// where they were. This avoids sending students off into another deck where
// they can get lost and never come back.
//
// Authoring: [text](other.qmd#slide-id){.peek}, and give the target slide an
// explicit id:  ## 見出し {#slide-id}
//
// How it works: fetch the target deck's HTML, pull out the single <section>
// with that id, clone it into the modal. Only that one section comes along —
// no controls, no other slides — so there is structurally nowhere to wander.
// Best for static slides (figures, tables, code); interactive Plotly slides
// will not re-initialize from a clone, so do not peek those.
//
// Clone fix-ups (needed because we lift a slide out of its deck):
//   - revealjs lazy-loads images as `data-src`; resolve to `src` or they break.
//   - Quarto's lightbox wraps figures in `<a href="…png" class="lightbox">`;
//     unwrap them, otherwise a click navigates the whole tab to the raw image
//     (the modal vanishes and the student can't get back).
(function () {
  try {
    var STYLE = [
      // the inline link marker: dotted underline + magnifier, "preview" cursor
      'a.peek {',
      '  text-decoration: none; border-bottom: 2px dotted currentColor;',
      '  cursor: zoom-in;',
      '}',
      'a.peek::after { content: " \\1F50D"; font-size: 0.72em; opacity: 0.7; }',
      // modal
      '#peek-modal {',
      '  position: fixed; inset: 0; z-index: 10600; display: none;',
      '  align-items: flex-start; justify-content: center;',
      '  padding: 6vh 4vw; background: rgba(0,0,0,0.6); box-sizing: border-box;',
      '}',
      '#peek-modal.peek-open { display: flex; }',
      '#peek-panel {',
      '  position: relative; width: min(1000px, 92vw); max-height: 86vh;',
      '  overflow: auto; background: #fff; border-radius: 10px;',
      '  padding: 30px 36px 22px; box-sizing: border-box;',
      '  box-shadow: 0 18px 56px rgba(0,0,0,0.4);',
      '}',
      '#peek-source {',
      '  font-size: 0.95rem; color: #2980b9; font-weight: bold;',
      '  margin: 0 40px 12px 0;',
      '}',
      // prominent, obviously-clickable close button
      '#peek-close {',
      '  position: absolute; top: 10px; right: 12px; width: 38px; height: 38px;',
      '  border: none; border-radius: 50%; background: rgba(0,0,0,0.07);',
      '  font-size: 26px; line-height: 38px; text-align: center;',
      '  color: #555; cursor: pointer; padding: 0;',
      '  transition: background 0.15s ease, color 0.15s ease;',
      '}',
      '#peek-close:hover, #peek-close:focus { background: #e74c3c; color: #fff; }',
      '#peek-content { font-size: 23px; line-height: 1.55; color: #222; }',
      // a detached revealjs <section> is hidden/absolutely positioned by default;
      // force it back to normal flow inside the modal
      '#peek-content section {',
      '  display: block !important; position: static !important;',
      '  transform: none !important; height: auto !important;',
      '  top: auto !important; left: auto !important;',
      '  opacity: 1 !important; visibility: visible !important;',
      '}',
      '#peek-content h1, #peek-content h2, #peek-content h3 {',
      '  font-size: 1.5em; margin: 0 0 0.5em; color: #1a1a1a;',
      '}',
      '#peek-content img { max-width: 100%; height: auto; display: block; margin: 0.4em auto; cursor: default; }',
      '#peek-content ul, #peek-content ol { text-align: left; padding-left: 1.3em; }',
      '#peek-content table { border-collapse: collapse; margin: 0.5em auto; }',
      '#peek-content th, #peek-content td { border: 1px solid #ccc; padding: 4px 10px; }',
      // show fragments fully (this is a recall snapshot, not a walkthrough)
      '#peek-content .fragment { opacity: 1 !important; visibility: visible !important; }',
      '#peek-content aside, #peek-content .notes, #peek-content .footer { display: none !important; }',
      '#peek-hint { margin-top: 14px; font-size: 0.82rem; color: #aaa; text-align: right; }',
      '#peek-loading { color: #888; font-size: 1.1rem; padding: 24px; text-align: center; }'
    ].join('\n');

    var pageCache = {};     // url -> Promise<Document>
    var revealKbPrev = null;

    function injectStyle() {
      if (document.getElementById('peek-ui-style')) return;
      var st = document.createElement('style');
      st.id = 'peek-ui-style';
      st.textContent = STYLE;
      document.head.appendChild(st);
    }

    // Disable the underlying deck's keyboard nav while the peek is open, so
    // arrow keys don't move the deck behind the modal. Mirrors search-ui.js.
    function setRevealKeyboard(active) {
      try {
        if (!window.Reveal || !Reveal.configure) return;
        if (!active) {
          if (revealKbPrev === null && Reveal.getConfig) revealKbPrev = Reveal.getConfig().keyboard;
          Reveal.configure({ keyboard: false });
        } else {
          Reveal.configure({ keyboard: revealKbPrev === null ? true : revealKbPrev });
          revealKbPrev = null;
        }
      } catch (e) {}
    }

    function isOpen() {
      var modal = document.getElementById('peek-modal');
      return !!(modal && modal.classList.contains('peek-open'));
    }

    function closePeek() {
      var modal = document.getElementById('peek-modal');
      if (modal) modal.classList.remove('peek-open');
      setRevealKeyboard(true);
    }

    function ensureModal() {
      var modal = document.getElementById('peek-modal');
      if (modal) return modal;
      modal = document.createElement('div');
      modal.id = 'peek-modal';
      modal.setAttribute('role', 'dialog');
      modal.setAttribute('aria-modal', 'true');
      modal.innerHTML =
        '<div id="peek-panel">' +
        '<button id="peek-close" type="button" aria-label="閉じる" title="閉じる（Esc）">×</button>' +
        '<div id="peek-source"></div>' +
        '<div id="peek-content"></div>' +
        '<div id="peek-hint">Esc・背景クリック・× で閉じる</div>' +
        '</div>';
      document.body.appendChild(modal);
      // backdrop click closes
      modal.addEventListener('click', function (e) { if (e.target === modal) closePeek(); });
      var btn = document.getElementById('peek-close');
      if (btn) btn.addEventListener('click', closePeek);
      // a peek is a read-only snapshot: never let a link inside it navigate away
      var content = document.getElementById('peek-content');
      if (content) content.addEventListener('click', function (e) {
        var a = e.target && e.target.closest ? e.target.closest('a') : null;
        if (a) e.preventDefault();
      });
      return modal;
    }

    function fetchDoc(url) {
      if (pageCache[url]) return pageCache[url];
      pageCache[url] = fetch(url)
        .then(function (r) { if (!r.ok) throw new Error('peek fetch failed: ' + url); return r.text(); })
        .then(function (html) { return new DOMParser().parseFromString(html, 'text/html'); });
      return pageCache[url];
    }

    function typeset(el) {
      try {
        if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise([el]);
        else if (window.MathJax && MathJax.Hub && MathJax.Hub.Queue) MathJax.Hub.Queue(['Typeset', MathJax.Hub, el]);
      } catch (e) {}
    }

    function sourceLabel(doc) {
      var t = (doc && doc.title ? doc.title : '').split(/[–—|]/)[0].trim();
      return t ? ('出典：' + t) : '';
    }

    // Make a cloned slide safe and complete to display outside its own deck.
    function fixupClone(clone) {
      // 1) resolve revealjs lazy-loaded images (data-src -> src)
      var lazy = clone.querySelectorAll('img[data-src], img[data-srcset], source[data-src], source[data-srcset]');
      for (var i = 0; i < lazy.length; i++) {
        var im = lazy[i];
        if (im.getAttribute('data-src')) im.setAttribute('src', im.getAttribute('data-src'));
        if (im.getAttribute('data-srcset')) im.setAttribute('srcset', im.getAttribute('data-srcset'));
      }
      // 2) unwrap lightbox (and any) anchors that wrap an image, so a click
      //    can't navigate the tab to the raw image file
      var anchors = clone.querySelectorAll('a');
      for (var k = 0; k < anchors.length; k++) {
        var an = anchors[k];
        if (an.querySelector && an.querySelector('img')) {
          while (an.firstChild) an.parentNode.insertBefore(an.firstChild, an);
          an.parentNode.removeChild(an);
        }
      }
      // 3) drop ids so the clone never collides with the host page's elements
      clone.removeAttribute('id');
      var withId = clone.querySelectorAll('[id]');
      for (var j = 0; j < withId.length; j++) withId[j].removeAttribute('id');
      return clone;
    }

    function openPeek(page, frag) {
      var modal = ensureModal();
      var content = document.getElementById('peek-content');
      var source = document.getElementById('peek-source');
      if (source) source.textContent = '';
      if (content) content.innerHTML = '<div id="peek-loading">読み込み中…</div>';
      setRevealKeyboard(false);
      modal.classList.add('peek-open');
      var panel = document.getElementById('peek-panel');
      if (panel) panel.scrollTop = 0;

      // same-page peek (no page part) clones from the current document
      var docPromise = page ? fetchDoc(page) : Promise.resolve(document);
      docPromise.then(function (doc) {
        if (source) source.textContent = sourceLabel(doc);
        var node = frag ? doc.getElementById(frag) : null;
        if (!node) {
          content.innerHTML = '<div id="peek-loading">該当スライドが見つかりませんでした</div>';
          return;
        }
        content.innerHTML = '';
        content.appendChild(fixupClone(node.cloneNode(true)));
        typeset(content);
      }).catch(function () {
        content.innerHTML = '<div id="peek-loading">読み込みに失敗しました</div>';
      });
    }

    // Intercept clicks on a.peek in the capture phase so neither the browser's
    // default navigation nor revealjs ever acts on the link.
    document.addEventListener('click', function (e) {
      try {
        var a = e.target && e.target.closest ? e.target.closest('a.peek') : null;
        if (!a) return;
        e.preventDefault();
        e.stopPropagation();
        var href = a.getAttribute('href') || '';
        var hashIdx = href.indexOf('#');
        if (hashIdx < 0) return;
        var page = href.slice(0, hashIdx);
        var frag = href.slice(hashIdx + 1).replace(/^\//, '');  // tolerate #/id form
        openPeek(page, frag);
      } catch (e2) {}
    }, true);

    // Esc closes the peek (capture + stop so revealjs/search don't also react).
    document.addEventListener('keydown', function (e) {
      try {
        if (isOpen() && e.key === 'Escape') {
          e.preventDefault();
          e.stopImmediatePropagation();
          closePeek();
        }
      } catch (e2) {}
    }, true);

    function setup() { try { injectStyle(); } catch (e) {} }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
    else setup();
  } catch (e) {}
})();
