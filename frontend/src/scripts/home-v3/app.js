// GeoReady v3 — home: rubric viva, carousel, FAQ, prezzi, hero. La shell sta in site-v3/shell.js.
import { gsap as G } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ScrambleTextPlugin } from 'gsap/ScrambleTextPlugin';
import { root, still, fine, store, reveal, pauseOffScreen } from '../site-v3/shell.js';
import { toAuditableUrl } from '../../lib/urlInput';
import { trackAuditStarted } from '../../lib/geo_track';
import { initMonitor } from './monitor.js';

G.registerPlugin(ScrollTrigger, ScrambleTextPlugin);

(function () {
  var EASE = 'cubic-bezier(0.22, 1, 0.36, 1)';

  // rubric: gli switch spostano categoria, punteggio e banda
  var scoreEl = document.getElementById('score');
  var ring = document.getElementById('ring'), scoreBox = document.querySelector('.rb-score');
  var bandEl = document.getElementById('band');
  var rows = {};
  document.querySelectorAll('#cats li').forEach(function (li) {
    var b = li.querySelector('b');
    var max = parseInt(li.querySelector('i').textContent.slice(1), 10);
    rows[li.dataset.cat] = { li: li, b: b, base: parseInt(b.textContent, 10), max: max };
  });
  var fixes = Array.prototype.slice.call(document.querySelectorAll('.rb-fixes input'));
  var shown = parseInt(scoreEl.textContent, 10);
  var raf = 0, scoreSr = document.getElementById('score-sr'), srT = 0;
  function announce(v) { clearTimeout(srT); srT = setTimeout(function () { scoreSr.textContent = 'Score ' + v + ' of 100, ' + band(v); }, 650); }

  function band(s) { return s >= 86 ? 'Excellent' : s >= 68 ? 'Good' : s >= 36 ? 'Foundation' : 'Critical'; }
  function tween(to) {
    cancelAnimationFrame(raf);
    if (still) { shown = to; scoreEl.textContent = to; return; }
    var from = shown, t0 = performance.now();
    (function step(now) {
      var k = Math.min(1, (now - t0) / 600), e = 1 - Math.pow(1 - k, 3);
      shown = Math.round(from + (to - from) * e);
      scoreEl.textContent = shown;
      if (k < 1) raf = requestAnimationFrame(step);
    })(t0);
  }
  // chip "+N" che sale dall'anello quando un fix si accende
  function pop(n) {
    if (still) return;
    var el = document.createElement('span');
    el.className = 'pop'; el.setAttribute('aria-hidden', 'true'); el.textContent = '+' + n;
    scoreBox.appendChild(el);
    el.animate([{ opacity: 0, transform: 'translateY(6px) scale(0.95)' }, { opacity: 1, transform: 'translateY(-14px)', offset: 0.3 }, { opacity: 0, transform: 'translateY(-34px)' }],
      { duration: 1100, easing: EASE }).onfinish = function () { el.remove(); };
  }
  var lastBand = '';
  function render() {
    var add = {};
    fixes.forEach(function (f) { if (f.checked) add[f.dataset.cat] = (add[f.dataset.cat] || 0) + +f.dataset.pts; });
    var total = 0;
    Object.keys(rows).forEach(function (k) {
      var r = rows[k], v = Math.min(r.max, r.base + (add[k] || 0));
      r.b.textContent = v;
      r.li.style.setProperty('--r', v / r.max);
      r.li.classList.toggle('bump', !!add[k]);
      total += v;
    });
    tween(total);
    if (lastBand) announce(total);
    // la scena WebGL dell'hero ascolta questo evento (hero-scene.js)
    var robots = fixes.find(function (f) { return f.dataset.cat === 'robots'; });
    document.dispatchEvent(new CustomEvent('geo:score', { detail: { score: total, robots: !!(robots && robots.checked), fixes: fixes.filter(function (f) { return f.checked; }).length } }));
    ring.style.strokeDashoffset = 100 - total;
    var b = band(total);
    if (b !== lastBand) {
      bandEl.textContent = b;
      bandEl.classList.toggle('good', total >= 68);
      if (lastBand && !still) bandEl.animate({ transform: ['scale(0.94)', 'none'] }, { duration: 320, easing: EASE });
      lastBand = b;
    }
  }
  function flip(f) { render(); if (f.checked) pop(f.dataset.pts); }
  fixes.forEach(function (f) { f.addEventListener('change', function () { touched = true; flip(f); }); });
  // prima passata: barre e anello partono da zero, in sequenza
  Object.keys(rows).forEach(function (k, i) { rows[k].li.style.setProperty('--d', (still ? 0 : 500 + i * 45) + 'ms'); });
  bandEl.textContent = lastBand = band(shown);
  setTimeout(function () {
    render();
    setTimeout(function () { Object.keys(rows).forEach(function (k) { rows[k].li.style.removeProperty('--d'); }); }, 1400);
  }, still ? 0 : 60);

  // demo una sola volta quando la rubric entra in vista; si ferma al primo tocco
  var touched = false;
  var rubric = document.querySelector('.rubric');
  rubric.addEventListener('pointerdown', function () { touched = true; }, { once: true });
  rubric.addEventListener('focusin', function () { touched = true; }, { once: true });
  if (!still && 'IntersectionObserver' in window) {
    new IntersectionObserver(function (es, io) {
      if (!es[0].isIntersecting) return;
      io.disconnect();
      // solo il primo fix: mostra che la rubrica si muove, il resto lo prova il visitatore
      setTimeout(function () { if (!touched && !root.classList.contains('motion-off')) { fixes[0].checked = true; flip(fixes[0]); } }, 2600);
    }, { threshold: 0.6 }).observe(rubric);
  }

  // tilt leggero e luce che segue il puntatore, solo con mouse
  if (fine && !still) {
    var tf = 0, rr = null;
    rubric.addEventListener('pointerenter', function () { rr = rubric.getBoundingClientRect(); });
    rubric.addEventListener('pointermove', function (e) {
      cancelAnimationFrame(tf);
      tf = requestAnimationFrame(function () {
        var r = rr || (rr = rubric.getBoundingClientRect()), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        rubric.style.transform = 'perspective(1400px) rotateX(' + ((0.5 - y) * 4).toFixed(2) + 'deg) rotateY(' + ((x - 0.5) * 5).toFixed(2) + 'deg)';
        rubric.style.setProperty('--mx', (x * 100).toFixed(1) + '%');
        rubric.style.setProperty('--my', (y * 100).toFixed(1) + '%');
      });
    });
    rubric.addEventListener('pointerleave', function () { cancelAnimationFrame(tf); rr = null; rubric.style.transform = ''; });
  }

  // platform: fila nativa su touch e schermi piccoli; su desktop un anello 3D guidato dallo scroll
  var section = document.getElementById('platform');
  var row = document.getElementById('pf-row');
  var items = Array.prototype.slice.call(row.querySelectorAll('.pf-item'));
  var nameEl = document.getElementById('pf-name'), descEl = document.getElementById('pf-desc'), planEl = document.getElementById('pf-plan');
  var lit = -1, live = document.getElementById('pf-live'), count = document.getElementById('pf-count');
  var arrows = document.querySelectorAll('[data-pf]'), caption = document.querySelector('.pf-caption');
  var rail = Array.prototype.slice.call(document.querySelectorAll('[data-rail]'));
  var pfST = null;
  function setLit(best) {
    if (best === lit) return;
    if (lit >= 0) items[lit].classList.remove('is-lit');
    lit = best;
    items[lit].classList.add('is-lit');
    nameEl.textContent = items[lit].dataset.name;
    planEl.textContent = items[lit].dataset.plan;
    descEl.textContent = items[lit].dataset.desc;
    if (!still) Array.prototype.forEach.call(caption.children, function (c, i) {
      c.animate([{ opacity: 0, transform: 'translateY(12px)' }, {}], { duration: 320, delay: i * 50, easing: EASE, fill: 'backwards' });
    });
    // nell'anello 3D i pannelli laterali sono decorativi: fuori dal tab e dagli screen reader
    if (pfST) items.forEach(function (it, i) { it.inert = i !== lit; });
    count.textContent = (lit + 1) + ' / ' + items.length;
    arrows[0].setAttribute('aria-disabled', lit === 0); arrows[1].setAttribute('aria-disabled', lit === items.length - 1);
    rail.forEach(function (r, i) { r.classList.toggle('on', i === lit); r.setAttribute('aria-current', i === lit ? 'true' : 'false'); });
    if (!pfST) rail.forEach(function (r, i) { r.style.setProperty('--p', i <= lit ? 1 : 0); });
  }
  function center() {
    var mid = row.getBoundingClientRect().left + row.clientWidth / 2, best = 0, bd = Infinity;
    items.forEach(function (it, i) {
      var r = it.getBoundingClientRect(), d = Math.abs(r.left + r.width / 2 - mid);
      if (d < bd) { bd = d; best = i; }
    });
    setLit(best);
  }
  function go(i) {
    i = Math.max(0, Math.min(items.length - 1, i));
    live.textContent = items[i].dataset.name + ' (' + items[i].dataset.plan + '). ' + items[i].dataset.desc;
    if (pfST) { scrollTo({ top: pfST.start + (pfST.end - pfST.start) * i / (items.length - 1) + 1, behavior: still ? 'auto' : 'smooth' }); return i; }
    var it = items[i];
    row.scrollTo({ left: it.offsetLeft - (row.clientWidth - it.offsetWidth) / 2, behavior: still ? 'auto' : 'smooth' });
    return i;
  }
  var tick = 0;
  row.addEventListener('scroll', function () { if (pfST) return; cancelAnimationFrame(tick); tick = requestAnimationFrame(center); }, { passive: true });
  arrows.forEach(function (b) {
    b.addEventListener('click', function () {
      if (b.getAttribute('aria-disabled') === 'true') return;
      go(lit + +b.dataset.pf);
    });
  });
  rail.forEach(function (r) { r.addEventListener('click', function () { go(+r.dataset.rail); }); });
  document.querySelectorAll('[data-go]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault(); megaSet(false);
      var i = +a.dataset.go;
      rail[i].focus({ preventScroll: true });
      if (pfST) go(i); else { section.scrollIntoView({ behavior: still ? 'auto' : 'smooth' }); setTimeout(function () { go(i); }, still ? 0 : 500); }
    });
  });
  row.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); go(lit + (e.key === 'ArrowRight' ? 1 : -1)); }
  });
  center();

  {
    var mm = G.matchMedia();
    mm.add('(min-width: 1081px) and (min-height: 700px) and (prefers-reduced-motion: no-preference)', function () {
      section.classList.add('pf-3d');
      var n = items.length, state = { a: 0 };
      var h = 0; items.forEach(function (it) { h = Math.max(h, it.offsetHeight); });
      row.style.setProperty('--pf-h', (h + 60) + 'px');
      function layout() {
        var w = items[0].offsetWidth;
        items.forEach(function (it, i) {
          var d = i - state.a, ad = Math.abs(d), ry = Math.max(-60, Math.min(60, -d * 34));
          // pannelli opachi: la profondità la danno distanza, rotazione e un velo scuro, non la trasparenza
          var x = Math.sign(d) * (Math.min(ad, 1) * 0.74 + Math.max(0, ad - 1) * 0.3) * w;
          it.style.transform = 'translate(-50%,-50%) translate3d(' + x.toFixed(1) + 'px,0,' + (-ad * 300).toFixed(1) + 'px) rotateY(' + ry.toFixed(2) + 'deg)';
          it.style.opacity = Math.max(0, Math.min(1, 2.6 - ad)).toFixed(3);
          it.style.setProperty('--dim', Math.min(0.82, ad * 0.6).toFixed(3));
          it.style.zIndex = 10 - Math.round(ad);
        });
        rail.forEach(function (r, i) { r.style.setProperty('--p', i === 0 ? 1 : Math.max(0, Math.min(1, state.a - i + 1)).toFixed(3)); });
        setLit(Math.round(state.a));
      }
      var tw = G.to(state, { a: n - 1, ease: 'none', onUpdate: layout,
        scrollTrigger: { trigger: section, start: 'top top', end: '+=' + Math.round((n - 1) * innerHeight * 0.42), pin: true, scrub: 0.7, invalidateOnRefresh: true,
          snap: { snapTo: 1 / (n - 1), inertia: false, duration: { min: 0.2, max: 0.5 }, delay: 0.08, ease: 'power2.inOut' } } });
      pfST = tw.scrollTrigger; layout();
      items.forEach(function (it, i) { it.inert = i !== lit; });
      return function () {
        pfST = null; section.classList.remove('pf-3d'); row.style.removeProperty('--pf-h');
        items.forEach(function (it) { it.inert = false; it.style.transform = it.style.opacity = it.style.zIndex = ''; it.style.removeProperty('--dim'); });
        center();
      };
    });
  }

  // fisarmonica FAQ: altezza misurata e animata con WAAPI, una sola aperta
  var faqs = Array.prototype.slice.call(document.querySelectorAll('.faq details'));
  var setters = faqs.map(function (d) {
    d.removeAttribute('name'); // l'esclusività la gestiamo qui, così la chiusura resta animata
    d.classList.toggle('is-open', d.open);
    var s = d.querySelector('summary'), body = d.querySelector('p'), anim = null;
    return function (open) {
      d.classList.toggle('is-open', open);
      if (still) { d.open = open; return; }
      var from = d.offsetHeight;
      if (anim) anim.cancel();
      if (open) d.open = true;
      var to = open ? s.offsetHeight + body.offsetHeight : s.offsetHeight;
      anim = d.animate({ height: [from + 'px', to + 'px'] }, { duration: 300, easing: EASE });
      if (open) body.animate({ opacity: [0, 1], transform: ['translateY(-6px)', 'none'] }, { duration: 260, delay: 60, easing: EASE, fill: 'backwards' });
      anim.onfinish = function () { anim = null; if (!open) d.open = false; };
    };
  });
  faqs.forEach(function (d, i) {
    d.querySelector('summary').addEventListener('click', function (e) {
      e.preventDefault();
      var open = !d.classList.contains('is-open');
      if (open) faqs.forEach(function (o, j) { if (j !== i && o.classList.contains('is-open')) setters[j](false); });
      setters[i](open);
    });
  });

  // cta: l'indirizzo scritto compare nell'anteprima, che scorre le nove categorie in loop
  var ctaUrl = document.getElementById('cta-url'), cpDomain = document.getElementById('cp-domain');
  ctaUrl.addEventListener('input', function () {
    var v = ctaUrl.value.trim().replace(/^https?:\/\//i, '').split(/[\/?#\s]/)[0].slice(0, 48).toLowerCase();
    cpDomain.textContent = v || 'your-site.com';
  });
  var prev = document.querySelector('.cta-prev'), cpLis = Array.prototype.slice.call(document.querySelectorAll('#cp-cats li'));
  var cpStep = document.getElementById('cp-step');
  var steps = ['Checking Google AI signals', 'Reading robots.txt · 27 bots', 'Parsing JSON-LD', 'Reading the rendered page', 'Matching brand entities', 'Checking meta tags', 'Fetching /llms.txt', 'Checking freshness signals', 'Looking for ai.txt'];
  function say(t) {
    if (!still) G.to(cpStep, { duration: 0.5, scrambleText: { text: t, chars: 'lowerCase', speed: 0.6 } });
    else cpStep.textContent = t;
  }
  if (still) cpStep.textContent = 'Nine categories · 100 points';
  else if ('IntersectionObserver' in window) {
    var cpT = 0, cpI = 0, cpOn = false;
    function cpRun() {
      if (!cpOn || root.classList.contains('motion-off')) return;
      if (cpI === 0) { cpLis.forEach(function (li) { li.classList.remove('scan', 'done'); }); prev.classList.add('run'); }
      if (cpI < cpLis.length) {
        if (cpI > 0) { cpLis[cpI - 1].classList.remove('scan'); cpLis[cpI - 1].classList.add('done'); }
        cpLis[cpI].classList.add('scan'); say(steps[cpI]); cpI++;
        cpT = setTimeout(cpRun, 820);
      } else {
        cpLis[cpI - 1].classList.remove('scan'); cpLis[cpI - 1].classList.add('done');
        prev.classList.remove('run'); say('Report ready · fixes ranked by points');
        cpI = 0; cpT = setTimeout(cpRun, 3200);
      }
    }
    new IntersectionObserver(function (es) {
      cpOn = es[0].isIntersecting; clearTimeout(cpT);
      if (cpOn) cpRun();
    }, { threshold: 0.35 }).observe(prev);
    document.addEventListener('geo:motion', function () { clearTimeout(cpT); if (cpOn) cpRun(); });
  }

  // form di audit (hero e CTA): stessa normalizzazione e stesso evento di AuditForm
  document.querySelectorAll('form[data-audit-form]').forEach(function (f) {
    var input = f.querySelector('input[name="url"]'), note = f.parentNode.querySelector('[data-audit-note]'), noteHtml = note.innerHTML;
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var raw = input.value.trim(), url = raw ? toAuditableUrl(raw) : null;
      if (!url) {
        note.textContent = raw ? 'Enter a valid website address, for example example.com.' : 'Enter a URL to audit.';
        input.setAttribute('aria-invalid', 'true'); input.focus(); return;
      }
      input.removeAttribute('aria-invalid'); note.innerHTML = noteHtml;
      trackAuditStarted();
      location.href = '/report/audit/?url=' + encodeURIComponent(url);
    });
  });

  // hero: il titolo entra parola per parola (dividere per lettera perde il kerning); il gradiente resta continuo sulla riga
  var grad = document.querySelector('#hero-title .grad');
  function gradFit() {
    var gl = grad.getBoundingClientRect().left, gw = grad.offsetWidth;
    grad.querySelectorAll('.ch').forEach(function (c) {
      c.style.backgroundSize = gw + 'px 100%';
      c.style.backgroundPosition = -(c.getBoundingClientRect().left - gl) + 'px 0';
    });
  }
  if (grad) { document.fonts.ready.then(gradFit); addEventListener('resize', gradFit, { passive: true }); }
  if (!still) {
    // all'uscita il titolo sale piano e la rubric resta indietro
    G.to('.hero-copy', { yPercent: -12, opacity: 0.35, ease: 'none', scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true } });
  }
  if (!still) {
    var site = document.querySelector('.rb-site'), siteT = site.textContent;
    G.to(site, { duration: 1.1, delay: 0.35, scrambleText: { text: siteT, chars: 'abcdefghijklmnopqrstuvwxyz.', speed: 0.5 } });
  }

  // prova: i numeri contano fino al valore reale quando entrano in vista
  if (!still) document.querySelectorAll('[data-count]').forEach(function (b) {
    var o = { v: 0 }, end = +b.dataset.count;
    G.to(o, { v: end, duration: 1.6, ease: 'expo.out', scrollTrigger: { trigger: b, start: 'top 90%', once: true },
      onUpdate: function () { b.textContent = Math.round(o.v).toLocaleString('en-US'); } });
  });

  // pricing: le tacche delle run si accendono in sequenza quando i piani entrano in vista
  document.querySelectorAll('.pr-runs').forEach(function (r) { r.querySelectorAll('i.on').forEach(function (t, k) { t.style.setProperty('--k', k); }); });
  var prc = document.querySelector('.pr-cols');
  if (prc) { prc.classList.add('reveal'); reveal(prc); }

  // pausa delle animazioni continue (WCAG 2.2.2): WebGL della hero, anteprima CTA, pulsazioni; la scelta resta salvata
  var motionBtn = document.querySelector('.motion-btn');
  function motionSet(off) {
    root.classList.toggle('motion-off', off);
    motionBtn.setAttribute('aria-pressed', off);
    store('motion', off ? 'off' : null);
    document.dispatchEvent(new CustomEvent('geo:motion'));
  }
  if (motionBtn) {
    var saved = null; try { saved = localStorage.getItem('motion'); } catch (e) {}
    if (saved === 'off') motionSet(true);
    motionBtn.addEventListener('click', function () { motionSet(!root.classList.contains('motion-off')); });
  }

  // loop infiniti in pausa fuori schermo (il footer lo osserva la shell)
  document.querySelectorAll('.hero, .ev-fetch, .cta-prev, #mon').forEach(pauseOffScreen);

  initMonitor();

  // three.js solo dopo load + idle, da tablet in su e senza risparmio dati
  var conn = navigator.connection;
  if (innerWidth >= 768 && !(conn && conn.saveData)) {
    var boot = function () { import('./hero-scene.js'); };
    var idle = function () { (window.requestIdleCallback || setTimeout)(boot, { timeout: 2000 }); };
    if (document.readyState === 'complete') idle(); else addEventListener('load', idle, { once: true });
  }
})();
