// Site-wide full-text search over Quarto's generated search.json.
// Provides: (1) a search button next to the Home button that opens a modal
// on every slide deck, (2) wiring for the inline search box on index.qmd
// (a #search-input / #search-results pair, if present on the page).
(function () {
  try {
    var STYLE = [
      '#search-btn {',
      '  position: fixed; top: 12px; left: 94px; z-index: 100;',
      '  display: inline-flex; align-items: center; gap: 6px;',
      '  background: #5dade2; color: white; border: none; cursor: pointer;',
      '  padding: 4px 12px; border-radius: 4px; font-size: 1rem;',
      '}',
      '#search-btn svg { width: 0.9em; height: 0.9em; display: block; }',
      '#search-modal {',
      '  position: fixed; inset: 0; z-index: 10500; display: none;',
      '  align-items: flex-start; justify-content: center;',
      '  padding: 8vh 4vw; background: rgba(0,0,0,0.55); box-sizing: border-box;',
      '}',
      '#search-modal.search-open { display: flex; }',
      '#search-modal-panel {',
      '  width: min(860px, 92vw); max-height: 80vh; background: #fff;',
      '  border-radius: 8px; padding: 16px; box-sizing: border-box;',
      '  box-shadow: 0 16px 48px rgba(0,0,0,0.35);',
      '  display: flex; flex-direction: column;',
      '}',
      '#lecture-search { margin: 0.5em 0 0.9em; }',
      '#search-input, #search-modal-input {',
      '  width: 100%; font-size: 1.4rem; padding: 8px 14px;',
      '  border: 2px solid #5dade2; border-radius: 6px;',
      '  box-sizing: border-box; background: #fff;',
      '}',
      '#search-results { margin-top: 6px; max-height: 45vh; overflow-y: auto; }',
      '#search-modal-results { margin-top: 8px; overflow-y: auto; }',
      '.search-ui-results a.search-hit {',
      '  display: block; padding: 6px 12px; margin: 5px 0;',
      '  font-size: 1.15rem; line-height: 1.5;',
      '  border: 1px solid #ddd; border-radius: 5px;',
      '  text-decoration: none; color: #333; background: #fafafa;',
      '}',
      '.search-ui-results a.search-hit:hover { background: #eaf4fb; border-color: #5dade2; }',
      '.search-ui-results .hit-loc { font-weight: bold; color: #2980b9; }',
      '.search-ui-results mark { background: #fff3a0; padding: 0 2px; }',
      '.search-ui-results .search-note { font-size: 1.1rem; color: #888; padding: 4px 10px; }',
      '.search-ui-results a[href]::after { content: none !important; display: none !important; }'
    ].join('\n');

    var indexData = null;

    function esc(s) {
      return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
                      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function loadIndex() {
      if (indexData !== null) return Promise.resolve(indexData);
      return fetch('search.json')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          indexData = d.filter(function (e) { return e.href.indexOf('index.html') !== 0; });
          return indexData;
        });
    }

    function snippet(text, q) {
      var i = text.toLowerCase().indexOf(q);
      if (i < 0) return '';
      var start = Math.max(0, i - 35);
      var end = Math.min(text.length, i + q.length + 50);
      return ((start > 0 ? '…' : '') + esc(text.slice(start, i)) +
              '<mark>' + esc(text.slice(i, i + q.length)) + '</mark>' +
              esc(text.slice(i + q.length, end)) +
              (end < text.length ? '…' : '')).replace(/\n+/g, ' ');
    }

    function renderInto(resultsEl, qRaw) {
      var q = qRaw.trim().toLowerCase();
      if (q.length < 2) {
        resultsEl.innerHTML = q.length === 1
          ? '<div class="search-note">2文字以上で検索</div>' : '';
        return;
      }
      loadIndex().then(function (idx) {
        var hits = [];
        for (var i = 0; i < idx.length && hits.length < 30; i++) {
          var e = idx[i];
          var hay = (e.title + '\n' + (e.section || '') + '\n' + (e.text || '')).toLowerCase();
          if (hay.indexOf(q) >= 0) hits.push(e);
        }
        if (hits.length === 0) {
          resultsEl.innerHTML = '<div class="search-note">ヒットなし</div>';
          return;
        }
        resultsEl.innerHTML = hits.map(function (e) {
          var href = e.href.replace('#', '#/');
          var loc = esc(e.title) + (e.section ? ' › ' + esc(e.section) : '');
          return '<a class="search-hit" href="' + href + '">' +
                 '<span class="hit-loc">' + loc + '</span><br>' +
                 snippet(e.text || '', q) + '</a>';
        }).join('');
      }).catch(function () {
        resultsEl.innerHTML =
          '<div class="search-note">検索インデックスを読み込めませんでした</div>';
      });
    }

    function attach(input, resultsEl) {
      var timer = null;
      input.addEventListener('input', function () {
        clearTimeout(timer);
        timer = setTimeout(function () { renderInto(resultsEl, input.value); }, 120);
      });
    }

    // --- modal ---
    var keyboardPrev = null;

    function setRevealKeyboard(active) {
      try {
        if (!window.Reveal || !Reveal.configure) return;
        if (!active) {
          if (keyboardPrev === null && Reveal.getConfig) {
            keyboardPrev = Reveal.getConfig().keyboard;
          }
          Reveal.configure({ keyboard: false });
        } else {
          Reveal.configure({ keyboard: keyboardPrev === null ? true : keyboardPrev });
          keyboardPrev = null;
        }
      } catch (e) {}
    }

    function ensureModal() {
      var modal = document.getElementById('search-modal');
      if (modal) return modal;
      modal = document.createElement('div');
      modal.id = 'search-modal';
      modal.setAttribute('role', 'dialog');
      modal.setAttribute('aria-modal', 'true');
      modal.innerHTML =
        '<div id="search-modal-panel">' +
        '<input id="search-modal-input" type="search" ' +
        'placeholder="全文検索 — どの回に出てきたか探せる（Esc で閉じる）" autocomplete="off">' +
        '<div id="search-modal-results" class="search-ui-results"></div>' +
        '</div>';
      document.body.appendChild(modal);
      modal.addEventListener('click', function (e) {
        if (e.target === modal) closeModal();
      });
      var input = document.getElementById('search-modal-input');
      var results = document.getElementById('search-modal-results');
      if (input && results) {
        attach(input, results);
        // close after choosing a result (same-page hash jumps don't reload)
        results.addEventListener('click', function (e) {
          if (e.target.closest && e.target.closest('a.search-hit')) closeModal();
        });
      }
      return modal;
    }

    function openModal() {
      var modal = ensureModal();
      setRevealKeyboard(false);
      modal.classList.add('search-open');
      var input = document.getElementById('search-modal-input');
      if (input) {
        input.focus();
        input.select();
      }
    }

    function closeModal() {
      var modal = document.getElementById('search-modal');
      if (modal) modal.classList.remove('search-open');
      setRevealKeyboard(true);
    }

    document.addEventListener('keydown', function (e) {
      try {
        var modal = document.getElementById('search-modal');
        if (!modal || !modal.classList.contains('search-open')) return;
        if (e.key === 'Escape') {
          e.preventDefault();
          e.stopImmediatePropagation();
          closeModal();
        }
      } catch (e2) {}
    }, true);

    function createButton() {
      if (document.getElementById('search-btn') || !document.body) return;
      var btn = document.createElement('button');
      btn.id = 'search-btn';
      btn.type = 'button';
      btn.title = '全文検索';
      btn.setAttribute('aria-label', '全文検索');
      btn.innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" ' +
        'stroke-linecap="round" aria-hidden="true">' +
        '<circle cx="10.5" cy="10.5" r="6.5"></circle>' +
        '<line x1="15.5" y1="15.5" x2="21" y2="21"></line></svg>' +
        '<span>検索</span>';
      btn.addEventListener('click', openModal);
      document.body.appendChild(btn);
    }

    function injectStyle() {
      if (document.getElementById('search-ui-style')) return;
      var st = document.createElement('style');
      st.id = 'search-ui-style';
      st.textContent = STYLE;
      document.head.appendChild(st);
    }

    function setup() {
      try {
        injectStyle();
        createButton();
        var inlineInput = document.getElementById('search-input');
        var inlineResults = document.getElementById('search-results');
        if (inlineInput && inlineResults && inlineInput.dataset.searchWired !== 'true') {
          inlineInput.dataset.searchWired = 'true';
          attach(inlineInput, inlineResults);
        }
      } catch (e) {}
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', setup);
    } else {
      setup();
    }
  } catch (e) {}
})();
