// GeoReady v3 — shell di tutto il sito: barra, tema, mega menu, sheet mobile, newsletter, footer, reveal.
// La home lo importa da home-v3/app.js; le altre pagine lo caricano da Shell.astro.
import { initCtaTracking } from '../../lib/ctaTracking';

export var root = document.documentElement;
export var still = matchMedia('(prefers-reduced-motion: reduce)').matches;
export var fine = matchMedia('(hover: hover) and (pointer: fine)').matches;
export var EASE_IO = 'cubic-bezier(0.77, 0, 0.175, 1)';
export function store(k, v) { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) {} }

// indice per gli stagger CSS: ogni figlio di [data-stagger] riceve --i
document.querySelectorAll('[data-stagger], .sheet-nav, .mega-views').forEach(function (p) {
  Array.prototype.forEach.call(p.children, function (c, i) { c.style.setProperty('--i', i); });
});

// barra: vetro dopo i primi pixel di scroll
var top = document.querySelector('.top');
function stick() { top.classList.toggle('stuck', scrollY > 8); }
if (top) { addEventListener('scroll', stick, { passive: true }); stick(); }

// tema a 3 stati: system -> light -> dark -> system; bottone in barra e selettore nel footer
var themeBtn = document.querySelector('[data-theme-toggle]');
var segs = Array.prototype.slice.call(document.querySelectorAll('input[name="theme-seg"]'));
var order = ['system', 'light', 'dark'];
function setTheme(t) {
  if (t === 'system') { delete root.dataset.theme; store('theme'); }
  else { root.dataset.theme = t; store('theme', t); }
  if (themeBtn) {
    themeBtn.dataset.state = t;
    themeBtn.setAttribute('aria-label', 'Theme: ' + t + '. Switch to ' + order[(order.indexOf(t) + 1) % 3]);
  }
  segs.forEach(function (r) { r.checked = r.value === t; });
}
setTheme(root.dataset.theme || 'system');
function switchTheme(next, from) {
  if (still || !document.startViewTransition) { setTheme(next); return; }
  // il nuovo tema si apre a cerchio dal controllo usato
  var r = from.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
  var end = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
  document.startViewTransition(function () { setTheme(next); }).ready.then(function () {
    root.animate({ clipPath: ['circle(0px at ' + x + 'px ' + y + 'px)', 'circle(' + end + 'px at ' + x + 'px ' + y + 'px)'] },
      { duration: 560, easing: EASE_IO, pseudoElement: '::view-transition-new(root)' });
  });
}
if (themeBtn) themeBtn.addEventListener('click', function () { switchTheme(order[(order.indexOf(root.dataset.theme || 'system') + 1) % 3], themeBtn); });
segs.forEach(function (r) { r.addEventListener('change', function () { switchTheme(r.value, r.parentNode); }); });

// mega-menu Platform: click, hover con ritardo, Esc e click fuori chiudono
var megaBtn = document.querySelector('.nav-mega'), mega = document.getElementById('mega'), megaT = 0;
if (megaBtn && mega) {
  var megaSet = function (open) {
    clearTimeout(megaT);
    if (open === !mega.hidden) return;
    mega.hidden = !open; megaBtn.setAttribute('aria-expanded', open);
  };
  var hoverAt = 0;
  // un click subito dopo l'apertura via hover non deve richiudere
  megaBtn.addEventListener('click', function () { if (!mega.hidden && Date.now() - hoverAt < 600) return; megaSet(mega.hidden); });
  // tastiera: dal bottone si entra nel pannello, dall'ultimo link si torna alla nav; uscendo il pannello si chiude
  var megaLinks = mega.querySelectorAll('a'), afterMega = megaBtn.parentNode.querySelector('.nav-mega ~ a');
  megaBtn.addEventListener('keydown', function (e) { if (e.key === 'Tab' && !e.shiftKey && !mega.hidden) { e.preventDefault(); megaLinks[0].focus(); } });
  megaLinks[megaLinks.length - 1].addEventListener('keydown', function (e) { if (e.key === 'Tab' && !e.shiftKey && afterMega) { e.preventDefault(); megaSet(false); afterMega.focus(); } });
  megaLinks[0].addEventListener('keydown', function (e) { if (e.key === 'Tab' && e.shiftKey) { e.preventDefault(); megaBtn.focus(); } });
  mega.addEventListener('focusout', function (e) { if (!mega.contains(e.relatedTarget) && e.relatedTarget !== megaBtn) megaSet(false); });
  if (fine) {
    [megaBtn, mega].forEach(function (el) {
      el.addEventListener('pointerenter', function () { clearTimeout(megaT); megaT = setTimeout(function () { if (mega.hidden) hoverAt = Date.now(); megaSet(true); }, 90); });
      el.addEventListener('pointerleave', function () { clearTimeout(megaT); megaT = setTimeout(function () { megaSet(false); }, 180); });
    });
  }
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !mega.hidden) { var inMega = mega.contains(document.activeElement); megaSet(false); if (inMega) megaBtn.focus(); } });
  document.addEventListener('click', function (e) { if (!mega.hidden && !mega.contains(e.target) && !megaBtn.contains(e.target)) megaSet(false); });
}

// menu mobile: popover nativo; il burger segue lo stato, i link lo chiudono
var sheet = document.getElementById('sheet'), burger = document.querySelector('.bar .burger');
if (sheet && burger) {
  sheet.addEventListener('toggle', function (e) { burger.setAttribute('aria-expanded', e.newState === 'open'); });
  // lo sheet copre la pagina: il Tab non deve finire sul contenuto dietro (sync, prima del ritorno del focus)
  var behind = document.querySelectorAll('a[href="#main-content"], .top, main, .foot');
  sheet.addEventListener('beforetoggle', function (e) { behind.forEach(function (el) { el.inert = e.newState === 'open'; }); });
  sheet.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', function () { sheet.hidePopover(); }); });
}

// newsletter: doppio opt-in, stesso endpoint e stessi testi di NewsletterSignup
var news = document.getElementById('news'), newsMsg = document.getElementById('news-msg'), newsBusy = false;
if (news) news.addEventListener('submit', function (e) {
  e.preventDefault();
  if (newsBusy) return;
  var em = news.email.value.trim();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)) { newsMsg.textContent = 'Enter a valid email address.'; news.email.setAttribute('aria-invalid', 'true'); news.email.focus(); return; }
  news.email.removeAttribute('aria-invalid');
  newsBusy = true; newsMsg.textContent = 'Sending…';
  fetch('https://app.geoready.dev/api/email/capture', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: em, source: news.dataset.source, source_url: location.href }),
  }).then(function (r) {
    if (!r.ok) throw new Error(String(r.status));
    newsMsg.textContent = 'Check your inbox and confirm. Nothing is sent until you click the link.';
    news.reset();
  }).catch(function () {
    newsMsg.textContent = 'Something went wrong — check the email and try again.';
  }).finally(function () { newsBusy = false; });
});

// footer: la parola grande prende luce sotto il puntatore
var word = document.querySelector('.foot-word'), foot = document.querySelector('.foot');
if (word && foot && fine && !still) {
  var wf = 0;
  foot.addEventListener('pointermove', function (e) {
    cancelAnimationFrame(wf);
    wf = requestAnimationFrame(function () {
      var r = word.getBoundingClientRect();
      word.style.setProperty('--fx', ((e.clientX - r.left) / r.width * 100).toFixed(1) + '%');
      word.style.setProperty('--fy', ((e.clientY - r.top) / r.height * 100).toFixed(1) + '%');
    });
  });
}

// entrate di sezione: reveal(el) per gli elementi marcati dopo il caricamento
var io = 'IntersectionObserver' in window && new IntersectionObserver(function (es) {
  es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
}, { rootMargin: '0px 0px -12% 0px' });
export function reveal(el) { if (io) io.observe(el); else el.classList.add('in'); }
document.querySelectorAll('.reveal').forEach(reveal);

// loop infiniti in pausa fuori schermo: un solo observer per tutti
var offIO = new IntersectionObserver(function (es) {
  es.forEach(function (e) { e.target.classList.toggle('off-screen', !e.isIntersecting); });
});
export function pauseOffScreen(el) { offIO.observe(el); }
if (foot) pauseOffScreen(foot);

initCtaTracking();
