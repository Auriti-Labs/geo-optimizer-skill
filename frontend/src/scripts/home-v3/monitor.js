// GeoReady v3 — grafico monitoring: dieci corse settimanali disegnate a scroll (scrub, reversibile).
// Senza JS o con reduced-motion resta lo stato finale statico del markup.
import { gsap as G } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

export function initMonitor() {
  var fig = document.getElementById('mon');
  if (!fig || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  // timeline costruita solo quando il grafico si avvicina: niente lavoro al caricamento
  ScrollTrigger.create({ trigger: fig, start: 'top bottom+=50%', once: true, onEnter: function () { build(fig); } });
}

function build(fig) {

  var q = function (s) { return fig.querySelector(s); };
  var line = q('.mc-line'), glow = q('.mc-glow'), clip = q('.mc-cliprect'), card = q('.mc-alert');
  var runs = Array.prototype.slice.call(fig.querySelectorAll('.mc-run'));
  var pts = runs.map(function (g) {
    var d = g.querySelector('.mc-dot');
    return { x: +d.getAttribute('cx'), y: +d.getAttribute('cy') };
  });
  // lunghezze cumulative: la linea è una spezzata, quindi la distanza euclidea è esatta
  var cum = [0];
  for (var i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y));
  var total = cum[cum.length - 1];
  var clipX = +clip.getAttribute('x'), clipW = +clip.getAttribute('width');

  var tl = G.timeline({
    defaults: { ease: 'none' },
    scrollTrigger: { trigger: fig, start: 'top 90%', end: 'bottom 78%', scrub: 0.6 }
  });

  // stato iniziale dentro la timeline: tornando su si riparte da vuoto
  tl.fromTo([line, glow], { strokeDasharray: total, strokeDashoffset: total }, { strokeDashoffset: total, duration: 0.01 }, 0);
  G.set(clip, { svgOrigin: clipX + ' 0' });
  G.set('#mon .mc-edge-hot', { svgOrigin: '414 100' });
  tl.fromTo(clip, { scaleX: 0 }, { scaleX: 0, duration: 0.01 }, 0);

  // posizione temporale di ogni settimana, usata anche dalle note via data-at
  var at = [];
  var t = 0.05;
  runs.forEach(function (g, i) {
    var p = pts[i];
    if (i > 0) {
      tl.to([line, glow], { strokeDashoffset: total - cum[i], duration: 1 }, t);
      tl.to(clip, { scaleX: (p.x - clipX) / clipW, duration: 1 }, t);
      t += 1;
    }
    at[i] = t;
    var drop = g.classList.contains('mc-drop');
    // la corsa schedulata parte: tacca, scan verticale, anello che si espande, punto
    G.set(g.querySelector('.mc-tick'), { svgOrigin: p.x + ' 300' });
    tl.fromTo(g.querySelector('.mc-tick'), { scaleY: 0 }, { scaleY: 1, duration: 0.2, ease: 'power2.out' }, t);
    tl.fromTo(g.querySelector('.mc-scan'), { opacity: 0 }, { opacity: 0.6, duration: 0.12 }, t)
      .to(g.querySelector('.mc-scan'), { opacity: 0, duration: 0.4 }, t + 0.12);
    // l'anello parte da opacità 0 così, prima del suo turno e tornando indietro, resta invisibile
    var ring = g.querySelector('.mc-ring');
    tl.fromTo(ring, { opacity: 0, scale: 1, transformOrigin: '50% 50%' }, { opacity: 0.8, duration: 0.02 }, t)
      .to(ring, { opacity: 0, scale: drop ? 4 : 3, duration: 0.6, ease: 'power2.out' }, t + 0.02);
    if (drop) {
      // il punto nasce accento e vira al rosso: due cerchi in dissolvenza incrociata
      var ok = g.querySelector('.mc-dot-ok'), bad = g.querySelector('.mc-dot-bad');
      tl.fromTo(ok, { opacity: 0, scale: 0, transformOrigin: '50% 50%' }, { opacity: 1, scale: 1, duration: 0.2, ease: 'back.out(2)' }, t)
        .to(ok, { opacity: 0, duration: 0.15 }, t + 0.25);
      tl.fromTo(bad, { opacity: 0, scale: 0.4, transformOrigin: '50% 50%' }, { opacity: 1, scale: 1, duration: 0.3, ease: 'back.out(3)' }, t + 0.25);
      tl.fromTo(card, { opacity: 0, scale: 0.55, x: 24 }, { opacity: 1, scale: 1, x: 0, duration: 0.6, ease: 'back.out(1.5)' }, t + 0.35);
      t += 0.9; // pausa di lettura sull'allarme
    } else {
      tl.fromTo(g.querySelector('.mc-dot'), { opacity: 0, scale: 0, transformOrigin: '50% 50%' }, { opacity: 1, scale: 1, duration: 0.25, ease: 'back.out(2)' }, t);
    }
    t += 0.35;
  });

  // note: data-at è l'indice della settimana (frazioni = dentro il segmento successivo)
  fig.querySelectorAll('[data-at]').forEach(function (el) {
    var a = +el.dataset.at, w = Math.floor(a), f = a - w;
    var start = f ? at[w] + 0.35 + f * 1 : at[w] + 0.1;
    tl.fromTo(el, { opacity: 0, y: 6 }, { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out' }, start);
    if (el.classList.contains('mc-cross')) {
      // la soglia 68 si accende da qui in poi
      tl.fromTo('#mon .mc-edge-hot', { opacity: 0, scaleX: 0 }, { opacity: 1, scaleX: 1, duration: 1.2, ease: 'power1.inOut' }, start);
    }
  });
  tl.to({}, { duration: 0.4 }); // coda: lo stato finale resta fermo prima della fine dello scroll
}
