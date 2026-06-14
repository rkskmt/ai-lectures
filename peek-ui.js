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
      '#peek-content { color: #222; }',
      // The clone is rendered inside a real `.reveal` wrapper (.peek-deck) so
      // every `.reveal`-scoped deck style applies — without it the slide shows
      // unstyled (no heading boxes, default bullets, wrong sizes). reveal
      // normally absolutely-positions `.slides`/`section` and JS-scales them;
      // none of that runs here, so force static flow and scale the whole deck
      // with `zoom` (computed in fitPeekDeck so it fills the panel width).
      '#peek-content .peek-deck {',
      '  position: static; height: auto; overflow: visible;',
      '  transform-origin: top left;',
      '}',
      '#peek-content .peek-deck .slides {',
      '  position: static !important; left: auto !important; top: auto !important;',
      '  width: 100% !important; height: auto !important;',
      '  transform: none !important; zoom: 1 !important; text-align: left;',
      '}',
      '#peek-content .peek-deck .slides > section {',
      '  display: block !important; position: static !important;',
      '  top: auto !important; left: auto !important; transform: none !important;',
      '  width: 100% !important; height: auto !important; min-height: 0 !important;',
      '  opacity: 1 !important; visibility: visible !important;',
      '}',
      // a peek is a snapshot, not a walkthrough: reveal every fragment
      '#peek-content .peek-deck .fragment {',
      '  opacity: 1 !important; visibility: visible !important; transform: none !important;',
      '}',
      // deck chrome that makes no sense lifted out of its deck; also hide
      // Quarto's copy button (its clipboard.js is not bound to the clone) —
      // we add our own working one below.
      '#peek-content .peek-deck .footer, #peek-content .peek-deck aside.notes,',
      '#peek-content .peek-deck .notes, #peek-content .peek-deck .code-expand-button,',
      '#peek-content .peek-deck .code-copy-button { display: none !important; }',
      // wrap long code lines so there is no zoom-mangled horizontal scrollbar;
      // copying still yields the original (unwrapped) source text
      '#peek-content .peek-deck pre, #peek-content .peek-deck pre code {',
      '  white-space: pre-wrap !important; overflow-x: hidden !important; word-break: normal; overflow-wrap: anywhere;',
      '}',
      // our own copy button, one per code block
      '#peek-content .peek-copy-button {',
      '  position: absolute; top: 6px; right: 8px; width: 30px; height: 30px;',
      '  display: flex; align-items: center; justify-content: center;',
      '  border: 1px solid rgba(0,0,0,0.14); border-radius: 4px;',
      '  background: rgba(255,255,255,0.85); padding: 0; cursor: pointer; z-index: 4;',
      '}',
      '#peek-content .peek-copy-button:hover { background: #fff; border-color: rgba(0,0,0,0.3); }',
      '#peek-content .peek-copy-button::before {',
      '  content: ""; display: inline-block; width: 16px; height: 16px;',
      '  background-color: rgb(90,99,104);',
      '  -webkit-mask: url(\'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/><path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/></svg>\') no-repeat center / 16px 16px;',
      '  mask: url(\'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/><path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/></svg>\') no-repeat center / 16px 16px;',
      '}',
      '#peek-content .peek-copy-button.copied::before {',
      '  background-color: rgb(18,128,60);',
      '  -webkit-mask: url(\'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>\') no-repeat center / 16px 16px;',
      '  mask: url(\'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>\') no-repeat center / 16px 16px;',
      '}',
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

    // The deck's design width (slides are authored at this px width, then the
    // real deck JS-scales to fit the window). We lay the clone out at this
    // width and zoom to fit the modal, reproducing the on-screen proportions.
    function deckWidth() {
      try {
        if (window.Reveal && Reveal.getConfig) {
          var w = Reveal.getConfig().width;
          if (typeof w === 'number' && w > 0) return w;
        }
      } catch (e) {}
      return 1280;
    }

    function fitPeekDeck(deck, avail) {
      try {
        if (!deck) return;
        var dw = deckWidth();
        deck.style.width = dw + 'px';
        deck.style.zoom = (avail > 0) ? String(avail / dw) : '1';
      } catch (e) {}
    }

    function copyText(text, btn) {
      function done() {
        try {
          if (!btn) return;
          btn.classList.add('copied');
          setTimeout(function () { btn.classList.remove('copied'); }, 1000);
        } catch (e) {}
      }
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done).catch(function () { fallbackCopy(text, done); });
        } else {
          fallbackCopy(text, done);
        }
      } catch (e) {}
    }

    function fallbackCopy(text, done) {
      try {
        var ta = document.createElement('textarea');
        ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta); ta.select();
        document.execCommand('copy'); document.body.removeChild(ta);
        done();
      } catch (e) {}
    }

    // Quarto's copy button is dead in the clone (clipboard.js isn't bound),
    // so add a working one to every code block in the peek.
    function addPeekCopyButtons(content) {
      try {
        var pres = content.querySelectorAll('pre');
        for (var i = 0; i < pres.length; i++) {
          var pre = pres[i];
          var code = pre.querySelector('code');
          if (!code) continue;
          var host = pre.closest('div.sourceCode') || pre;
          if (host.querySelector('.peek-copy-button')) continue;
          if (getComputedStyle(host).position === 'static') host.style.position = 'relative';
          var btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'peek-copy-button';
          btn.title = 'コピー';
          btn.setAttribute('aria-label', 'コードをコピー');
          btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            var c = this.parentNode.querySelector('code');
            if (c) copyText(c.innerText, this);
          });
          host.appendChild(btn);
        }
      } catch (e) {}
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
        // measure the panel's inner width before inserting the (wider) deck
        var avail = content.clientWidth;
        // wrap the clone in a real .reveal > .slides so deck CSS applies
        var deck = document.createElement('div');
        deck.className = 'reveal peek-deck';
        var slides = document.createElement('div');
        slides.className = 'slides';
        slides.appendChild(fixupClone(node.cloneNode(true)));
        deck.appendChild(slides);
        content.appendChild(deck);
        fitPeekDeck(deck, avail);
        addPeekCopyButtons(content);
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
