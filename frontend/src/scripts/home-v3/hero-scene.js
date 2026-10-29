// GeoReady v3 — prototipo home: campo delle citazioni (anello di particelle + 27 crawler) dietro la rubric.
import * as THREE from 'three';

const canvas = document.getElementById('hero-gl');
const hero = document.querySelector('.hero');
const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
const fine = matchMedia('(hover: hover) and (pointer: fine)').matches;
let warned = false;
function warn(e) { if (!warned) { warned = true; console.warn('hero-gl:', e); } }

// maschera morbida sul blocco testo: le particelle lì dietro restano quasi spente
const MASK = `
uniform vec4 uCopy, uCopy2, uCopy3, uCopy4; uniform vec2 uRes; uniform float uFloor, uFloorH;
float inRect(vec2 p, vec4 r) {
  return smoothstep(r.x - 40.0, r.x + 8.0, p.x) * smoothstep(r.z + 16.0, r.z - 6.0, p.x)
       * smoothstep(r.y - 16.0, r.y + 6.0, p.y) * smoothstep(r.w + 16.0, r.w - 6.0, p.y);
}
// fH: soglia dietro al titolo (glifi grandi, regge di più), uFloor: dietro paragrafo, form ed etichette
float copyMask(vec2 sp, float fH) {
  return min(mix(1.0, fH, max(inRect(sp, uCopy), inRect(sp, uCopy4))), mix(1.0, uFloor, max(inRect(sp, uCopy2), inRect(sp, uCopy3))));
}
vec2 toScreen(vec4 cl) { vec2 s = (cl.xy / cl.w * 0.5 + 0.5) * uRes; return vec2(s.x, uRes.y - s.y); }
`;

const RING_VS = `
uniform float uTime, uIntro, uLit, uPulse, uR, uDpr, uCam, uAlpha, uDark, uMouseOn, uRingK;
uniform vec2 uMouse; uniform vec3 uA, uB, uInk;
attribute vec3 aStart; attribute vec4 aData; // angolo, offset radiale, offset z, seme
varying vec3 vCol; varying float vAlpha;
const float TAU = 6.2831853;
${MASK}
void main() {
  float seed = aData.w;
  // le particelle scorrono lungo l'anello; l'arco acceso resta fermo in alto
  float th = aData.x - uTime * (0.016 + 0.014 * fract(seed * 7.31));
  float frac = mod(1.5707963 - th, TAU) / TAU;
  float ad = abs(frac - uLit); ad = min(ad, 1.0 - ad);
  float wave = 0.0;
  if (uPulse < 3.5) { float w = (ad - uPulse * 0.3) / 0.04; wave = exp(-w * w) * exp(-uPulse * 1.3); }
  float r = uR * (1.0 + aData.y + wave * 0.045 * (0.5 + fract(seed * 5.7)));
  vec3 ring = vec3(cos(th) * r, sin(th) * r, aData.z * uR);
  float delay = fract(seed * 13.7) * 0.55 + frac * 0.3;
  float k = clamp((uIntro - delay) / 1.3, 0.0, 1.0);
  float e = k >= 1.0 ? 1.0 : 1.0 - pow(2.0, -10.0 * k);
  vec3 p = mix(aStart * uR, ring, e);
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  vec2 sp = toScreen(projectionMatrix * mv);
  if (uMouseOn > 0.001) {
    vec2 dm = sp - uMouse; float l = length(dm) + 0.001;
    vec2 off = dm / l * uMouseOn * smoothstep(150.0, 0.0, l) * 30.0;
    mv.xy += vec2(off.x, -off.y) * (-mv.z / uCam);
    sp += off;
  }
  gl_Position = projectionMatrix * mv;

  float lit = (1.0 - smoothstep(uLit - 0.003, uLit + 0.003, frac)) * step(0.002, uLit);
  float head = exp(-pow(ad / 0.014, 2.0)) * step(0.01, uLit);
  vec3 litCol = mix(uA, uB, clamp(frac / max(uLit, 0.01), 0.0, 1.0));
  vCol = mix(uInk, litCol, max(lit, head * 0.8));
  float tw = 0.62 + 0.38 * sin(uTime * (1.1 + 2.2 * fract(seed * 3.1)) + seed * 57.0);
  float core = exp(-pow(aData.y / 0.02, 2.0)); // le particelle sul filo centrale disegnano l'anello
  float dimA = mix(0.26, 0.42, uDark) * (0.3 + 0.7 * core);
  float litA = mix(0.45, 1.0, core);
  vAlpha = (mix(dimA, litA, lit) * tw + head * 0.8 + wave * 0.35) * (0.35 + 0.65 * e) * smoothstep(0.0, 0.35, uIntro) * uAlpha * uRingK * copyMask(sp, uFloor);
  float size = mix(1.3, 3.0, fract(seed * 91.7)) * (1.0 + lit * 0.25 + head * 1.2 + wave * 0.8);
  gl_PointSize = size * uDpr * uCam / -mv.z;
}`;

const COMET_VS = `
uniform float uDpr, uCam, uAlpha, uGain;
attribute vec4 aInfo; // alfa, dimensione, rosso (bloccato), teal (ammesso)
varying float vAlpha, vBad, vOk;
${MASK}
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vec4 cl = projectionMatrix * mv;
  gl_Position = cl;
  vAlpha = min(1.0, aInfo.x * uGain) * uAlpha * copyMask(toScreen(cl), uFloorH);
  vBad = aInfo.z; vOk = aInfo.w;
#ifndef TRAIL
  if (aInfo.y < 0.5) vAlpha = 0.0;
#endif
  gl_PointSize = aInfo.y * uDpr * uCam / -mv.z;
}`;

// scie: linee sottili da 1px, stessa geometria delle teste
const TRAIL_FS = `
uniform vec3 uHead, uBad, uOk;
varying float vAlpha, vBad, vOk;
void main() { gl_FragColor = vec4(mix(mix(uHead, uOk, vOk), uBad, vBad) * vAlpha, vAlpha); }`;

const RING_FS = `
varying vec3 vCol; varying float vAlpha;
void main() {
  float d = length(gl_PointCoord - 0.5) * 2.0;
  float a = smoothstep(1.0, 0.15, d) * vAlpha;
  if (a < 0.003) discard;
  gl_FragColor = vec4(vCol * a, a);
}`;

const COMET_FS = `
uniform vec3 uHead, uBad, uOk;
varying float vAlpha, vBad, vOk;
void main() {
  float d = length(gl_PointCoord - 0.5) * 2.0;
  float a = (exp(-d * d * 4.0) * 0.55 + smoothstep(0.3, 0.0, d) * 0.45) * vAlpha;
  if (a < 0.003) discard;
  gl_FragColor = vec4(mix(mix(uHead, uOk, vOk), uBad, vBad) * a, a);
}`;

// bagliore d'impatto sul bordo della card: alone tondo + lama verticale rossa quando il muro respinge
const GLOW_VS = `
uniform float uDpr, uSize;
void main() { gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); gl_PointSize = uSize * uDpr; }`;
const GLOW_FS = `
uniform vec3 uOk, uBad; uniform float uEOk, uEBad, uAlpha, uHalo;
void main() {
  vec2 q = gl_PointCoord - 0.5;
  float disc = exp(-dot(q, q) * 26.0);
  float blade = exp(-q.x * q.x * 1400.0) * exp(-q.y * q.y * 7.0);
  float eo = uEOk * disc, eb = uEBad * (disc * 1.2 * uHalo + blade * 2.0);
  float a = clamp(eo + eb, 0.0, 1.0) * uAlpha;
  if (a < 0.003) discard;
  gl_FragColor = vec4((uOk * eo + uBad * eb) / max(eo + eb, 1e-4) * a, a);
}`;

function gauss() { return (Math.random() + Math.random() + Math.random() - 1.5) / 1.5; }

async function init() {
  if (!canvas || !hero || !window.WebGLRenderingContext) return;
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false, premultipliedAlpha: true, powerPreference: 'low-power' });
  } catch (e) { return; }
  renderer.setClearColor(0x000000, 0);
  // alcuni driver limitano gl_PointSize: il glow non deve superare il massimo
  const maxPoint = renderer.getContext().getParameter(renderer.getContext().ALIASED_POINT_SIZE_RANGE)[1] || 64;

  const narrowStart = innerWidth < 768;
  const N = narrowStart ? 2200 : 6000;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, 1, 10000);
  const group = new THREE.Group();
  scene.add(group);

  // anello: angolo, offset radiale (filo centrale + alone + polvere), punto di partenza nella nube
  const pos = new Float32Array(N * 3), start = new Float32Array(N * 3), data = new Float32Array(N * 4);
  for (let i = 0; i < N; i++) {
    const t = Math.random() * Math.PI * 2, kind = Math.random();
    const rad = kind < 0.55 ? gauss() * 0.009 : kind < 0.92 ? gauss() * 0.06 : gauss() * 0.2;
    data.set([t, rad, gauss() * (kind < 0.55 ? 0.01 : 0.05), Math.random()], i * 4);
    const u = Math.random() * Math.PI * 2, v = Math.acos(2 * Math.random() - 1), s = 0.35 + Math.pow(Math.random(), 0.7) * 1.3;
    start.set([Math.sin(v) * Math.cos(u) * s, Math.sin(v) * Math.sin(u) * s * 0.75, Math.cos(v) * s * 0.6], i * 3);
  }
  const ringGeo = new THREE.BufferGeometry();
  ringGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  ringGeo.setAttribute('aStart', new THREE.BufferAttribute(start, 3));
  ringGeo.setAttribute('aData', new THREE.BufferAttribute(data, 4));

  const shared = { uRes: { value: new THREE.Vector2() }, uCopy: { value: new THREE.Vector4(-1e4, -1e4, -1e4, -1e4) }, uCopy2: { value: new THREE.Vector4(-1e4, -1e4, -1e4, -1e4) }, uCopy3: { value: new THREE.Vector4(-1e4, -1e4, -1e4, -1e4) }, uCopy4: { value: new THREE.Vector4(-1e4, -1e4, -1e4, -1e4) }, uDpr: { value: 1 }, uCam: { value: 1 }, uAlpha: { value: 1 }, uFloor: { value: 0.1 }, uFloorH: { value: 0.45 } };
  const U = Object.assign({
    uTime: { value: 0 }, uRingK: { value: 1 }, uIntro: { value: still ? 10 : 0 }, uLit: { value: 0 }, uPulse: { value: 10 }, uR: { value: 1 },
    uDark: { value: 0 }, uMouseOn: { value: 0 }, uMouse: { value: new THREE.Vector2(-1e4, -1e4) },
    uA: { value: new THREE.Color() }, uB: { value: new THREE.Color() }, uInk: { value: new THREE.Color() },
  }, shared);
  const ringMat = new THREE.ShaderMaterial({ uniforms: U, vertexShader: RING_VS, fragmentShader: RING_FS, transparent: true, depthTest: false, depthWrite: false, premultipliedAlpha: true });
  const ring = new THREE.Points(ringGeo, ringMat);
  ring.frustumCulled = false;
  group.add(ring);

  // 27 crawler in coordinate schermo (1 unità = 1px a z=0): teste + scie verso la riga Robots.txt della rubric
  // i primi 3 sono i bot di ricerca del fix (OAI-SearchBot, PerplexityBot, Claude-SearchBot)
  const C = 27, S = 3, TRAIL = 64, H = 0.006, HOLD = 0.2, BOUNCE = 0.8, WALL = 7;
  const cPos = new Float32Array(C * TRAIL * 3), cInfo = new Float32Array(C * TRAIL * 4);
  const cGeo = new THREE.BufferGeometry();
  cGeo.setAttribute('position', new THREE.BufferAttribute(cPos, 3).setUsage(THREE.DynamicDrawUsage));
  cGeo.setAttribute('aInfo', new THREE.BufferAttribute(cInfo, 4).setUsage(THREE.DynamicDrawUsage));
  const CU = Object.assign({ uHead: { value: new THREE.Color() }, uBad: { value: new THREE.Color() }, uOk: { value: new THREE.Color() }, uGain: { value: 1 } }, shared);
  const cMat = new THREE.ShaderMaterial({ uniforms: CU, vertexShader: COMET_VS, fragmentShader: COMET_FS, transparent: true, depthTest: false, depthWrite: false, premultipliedAlpha: true });
  const comets = new THREE.Points(cGeo, cMat);
  const idx = [];
  for (let i = 0; i < C; i++) for (let j = 0; j < TRAIL - 1; j++) idx.push(i * TRAIL + j, i * TRAIL + j + 1);
  const lGeo = new THREE.BufferGeometry();
  lGeo.setAttribute('position', cGeo.attributes.position); lGeo.setAttribute('aInfo', cGeo.attributes.aInfo); lGeo.setIndex(idx);
  const lMat = new THREE.ShaderMaterial({ defines: { TRAIL: 1 }, uniforms: CU, vertexShader: COMET_VS, fragmentShader: TRAIL_FS, transparent: true, depthTest: false, depthWrite: false, premultipliedAlpha: true });
  const trails = new THREE.LineSegments(lGeo, lMat);
  const gGeo = new THREE.BufferGeometry();
  gGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(3), 3));
  const GU = { uOk: CU.uOk, uBad: CU.uBad, uDpr: shared.uDpr, uAlpha: shared.uAlpha, uSize: { value: 120 }, uEOk: { value: 0 }, uEBad: { value: 0 }, uHalo: { value: 1 } };
  const gMat = new THREE.ShaderMaterial({ uniforms: GU, vertexShader: GLOW_VS, fragmentShader: GLOW_FS, transparent: true, depthTest: false, depthWrite: false, premultipliedAlpha: true });
  const glow = new THREE.Points(gGeo, gMat);
  comets.frustumCulled = trails.frustumCulled = glow.frustumCulled = false;
  scene.add(trails, comets, glow);

  // etichette DOM dei 3 bot di ricerca: aggiornate solo ai cambi di stato
  const NAMES = ['OAI-SearchBot', 'PerplexityBot', 'Claude-SearchBot'];
  const tags = document.createElement('div');
  tags.className = 'gl-tags'; tags.setAttribute('aria-hidden', 'true');
  tags.innerHTML = NAMES.map((n) => `<span class="gl-tag"><b>${n}</b><span class="gl-st"><i class="gl-no">blocked</i><i class="gl-ok">allowed</i></span></span>`).join('');
  hero.appendChild(tags);
  const tagEls = tags.children;
  const card = hero.querySelector('.rubric'), rowEl = hero.querySelector('.rb-cats li[data-cat="robots"]');

  let robots = false, clock = 0, pulseArmed = false, eOk = 0, eBad = 0;
  let lane = 0;
  const E = { x: 0, y: 0, h: 30 }, band = { y0: 96, y1: 160 }, low = { x: 0, y0: 0, y1: 0 };
  let W = 1, Hh = 1, heroH = 1, narrow = false, baseAlpha = 1;
  const bots = [];
  for (let i = 0; i < C; i++) bots.push({ i, search: i < S, p0: [0, 0], p1: [0, 0], p2: [0, 0], p3: [0, 0], v: [0, 0] });
  const R = Math.random;

  // percorso: bezier da origine nel campo (sopra il titolo, sopra la card o dal bordo sinistro) fino alla riga
  // l'ultimo tratto è orizzontale verso il bordo della card (verticale verso il bordo alto su schermi stretti)
  function plan(c, at) {
    c.launch = at; c.hit = false; c.block = c.search && !robots;
    c.tin = c.search ? 1.0 + R() * 0.2 : 1.6 + R() * 1.2;
    const { p0, p1, p2, p3 } = c;
    if (narrow) {
      p3[0] = E.x + (c.search ? (c.i - 1) * 10 : (R() - 0.5) * 60); p3[1] = E.y;
      p0[0] = W * (0.35 + R() * 0.75); p0[1] = -40 + R() * 80;
      p1[0] = p0[0] + (R() - 0.5) * 80; p1[1] = p0[1] + (E.y - p0[1]) * 0.4;
      p2[0] = p3[0]; p2[1] = p3[1] - 70 - R() * 80;
    } else {
      // i bot di ricerca: tre lance quasi orizzontali dal bordo sinistro, dietro al titolo, dritte nella riga
      // gli altri: dalla fascia sopra il titolo, da sopra la card o risalendo il campo vuoto sotto il testo
      const k = c.search ? -1 : R();
      p3[0] = E.x; p3[1] = E.y + (c.search ? (c.i - 1) * 5 : (R() - 0.5) * E.h * 0.7);
      if (k < 0) {
        p0[0] = -80; p0[1] = lane + (c.i - 1) * 3;
        p1[0] = E.x * 0.5; p1[1] = p0[1];
        p2[0] = E.x - 150 - R() * 40; p2[1] = p3[1];
      } else if (k < 0.45) {
        p0[0] = -60 + R() * E.x * 0.8; p0[1] = band.y0 + R() * (band.y1 - band.y0);
        p1[0] = E.x + 10 + R() * 30; p1[1] = p0[1] + (E.y - p0[1]) * 0.05;
        p2[0] = E.x - 40 - R() * 50; p2[1] = p3[1] - 30 - R() * 30;
      } else if (k < 0.6) {
        p0[0] = E.x + 80 + R() * Math.max(80, W - E.x); p0[1] = band.y0 + R() * (band.y1 - band.y0) * 0.6;
        p1[0] = E.x - 60 - R() * 40; p1[1] = p0[1] + 20;
        p2[0] = E.x - 40 - R() * 50; p2[1] = p3[1] - 30 - R() * 20;
      } else {
        p0[0] = -60 + R() * E.x * 0.55; p0[1] = low.y0 + R() * (low.y1 - low.y0);
        p1[0] = low.x + R() * 50; p1[1] = p0[1] - (p0[1] - E.y) * (0.2 + R() * 0.2);
        p2[0] = E.x - 90 - R() * 60; p2[1] = p3[1] + 20 + R() * 20;
      }
    }
    // velocità d'uscita: il passaggio prosegue dritto dietro la card (opaca, quindi invisibile)
    c.v[0] = 3 * (p3[0] - p2[0]) / c.tin; c.v[1] = 3 * (p3[1] - p2[1]) / c.tin;
  }
  function bez(c, u, o) {
    const m = 1 - u, a = m * m * m, b = 3 * m * m * u, d = 3 * m * u * u, e = u * u * u;
    o[0] = a * c.p0[0] + b * c.p1[0] + d * c.p2[0] + e * c.p3[0];
    o[1] = a * c.p0[1] + b * c.p1[1] + d * c.p2[1] + e * c.p3[1];
  }
  // posizione al tempo t dal lancio; i bloccati si fermano al muro e rimbalzano indietro lungo la curva
  function at(c, t, o) {
    if (t < 0) return false;
    const r = t - c.tin;
    if (r < 0) bez(c, t / c.tin, o);
    else if (!c.block) { o[0] = c.p3[0] + c.v[0] * r; o[1] = c.p3[1] + c.v[1] * r; return true; }
    else if (r < HOLD) { o[0] = c.p3[0]; o[1] = c.p3[1]; }
    else { const m = 1 - Math.min(1, (r - HOLD) / BOUNCE); bez(c, 1 - 0.24 * (1 - m * m * m), o); }
    // il muro sta qualche px prima del bordo della card: la testa rossa resta visibile
    if (c.block) { const w = WALL * Math.min(1, Math.max(0, t / c.tin - 0.9) * 10); if (narrow) o[1] -= w; else o[0] -= w; }
    return true;
  }
  function relaunch(c, now) {
    const d = c.search ? (robots ? 0.1 + R() * 0.45 : 0.25 + R() * 0.4) : 0.2 + R() * 2.2;
    plan(c, now + d);
  }
  function impact(c) {
    // i crawler generici passano sempre: bagliore teal leggero, quasi nullo finché il muro è su
    if (!c.search) { eOk = Math.max(eOk, robots ? 0.3 : 0.1); return; }
    if (!c.tagged) { c.tagged = true; tagEls[c.i].classList.add('on'); }
    if (c.block) { eBad = 1; return; }
    eOk = 1;
    if (pulseArmed && rowEl && rowEl.animate) {
      pulseArmed = false;
      try { rowEl.animate({ opacity: [0, 1, 0] }, { duration: 1400, easing: 'cubic-bezier(0.16, 1, 0.3, 1)', pseudoElement: '::before' }); } catch (e) { /* pseudo-elementi non animabili qui */ }
    }
  }
  // posa fissa per reduced motion: crawler a metà strada, bot di ricerca appena arrivati alla riga
  function stillT(c) { return c.search ? (c.block ? c.tin + HOLD * 0.5 : c.tin - 0.03) : c.tin * (0.3 + 0.65 * ((c.i * 0.618) % 1)); }
  const tmp = [0, 0];
  function updateComets(now, dt) {
    const hx = W / 2, hy = Hh / 2, gk = narrow ? 0.4 : 1;
    for (let i = 0; i < C; i++) {
      const c = bots[i];
      let t = still ? stillT(c) : now - c.launch;
      if (!still) {
        if (!c.hit && t >= c.tin) { c.hit = true; impact(c); }
        const end = c.block ? c.tin + HOLD + BOUNCE : c.tin + TRAIL * H + 0.05;
        if (t > end) { relaunch(c, now); t = now - c.launch; }
      }
      const r = t - c.tin, hitBad = c.block && r >= 0;
      // il bloccato lampeggia rosso all'impatto e svanisce mentre rimbalza
      const fade = hitBad && r > HOLD ? 1 - Math.pow(Math.min(1, (r - HOLD) / BOUNCE), 1.5) : 1;
      const bad = hitBad ? 1 : 0, ok = c.search && !c.block ? 1 : 0;
      const flash = hitBad && r < HOLD + 0.2 ? 1 - Math.max(0, r - HOLD) / 0.2 : 0;
      for (let j = 0; j < TRAIL; j++) {
        const n = (i * TRAIL + j) * 3, m = (i * TRAIL + j) * 4, ts = t - j * H;
        const on = at(c, ts, tmp);
        cPos[n] = tmp[0] - hx; cPos[n + 1] = hy - tmp[1]; cPos[n + 2] = 0;
        const q = 1 - j / TRAIL, fin = on ? Math.min(1, ts / 0.3) : 0;
        const head = j === 0;
        cInfo[m] = fin * fade * (c.search ? (head ? 1 : 0.85 * Math.pow(q, 0.8)) : (head ? 0.8 : 0.5 * Math.pow(q, 1.3)) * gk);
        cInfo[m + 1] = c.search ? (head ? 24 + flash * 26 : 3 + 9 * q * q) : (head ? 12 : 1.5 + 4 * q * q);
        cInfo[m + 2] = bad; cInfo[m + 3] = ok;
      }
    }
    cGeo.attributes.position.needsUpdate = true;
    cGeo.attributes.aInfo.needsUpdate = true;
    if (still) { eOk = robots ? 0.85 : 0.2; eBad = robots ? 0 : 0.9; }
    else { const k = Math.exp(-dt * 2.6); eOk *= k; eBad *= k; }
    GU.uEOk.value = eOk; GU.uEBad.value = eBad;
  }

  // tema: colori dalle custom properties, blending additivo solo su fondo scuro
  function theme() {
    const cs = getComputedStyle(document.documentElement);
    const col = (n, c) => c.setStyle(cs.getPropertyValue(n).trim() || '#888', THREE.LinearSRGBColorSpace);
    const bg = col('--bg', new THREE.Color());
    const dark = bg.r * 0.3 + bg.g * 0.59 + bg.b * 0.11 < 0.5;
    col('--grad-a', U.uA.value); col('--grad-b', U.uB.value); col('--ink', U.uInk.value); col('--bad', CU.uBad.value); col('--accent', CU.uOk.value);
    // crawler generici neutri: bianco freddo sul fondo scuro, inchiostro su quello chiaro
    if (dark) CU.uHead.value.copy(U.uInk.value).lerp(U.uB.value, 0.25);
    else col('--muted', CU.uHead.value);
    U.uDark.value = dark ? 1 : 0; CU.uGain.value = dark ? 1 : 1.5; GU.uHalo.value = dark ? 1 : 0.2; // alone rosso più contenuto su fondo chiaro
    shared.uFloorH.value = narrow ? 0.3 : dark ? 0.5 : 0.35;
    ringMat.blending = cMat.blending = lMat.blending = gMat.blending = dark ? THREE.AdditiveBlending : THREE.NormalBlending;
    kick();
  }

  // offset di layout (senza transform) rispetto all'hero
  function off(el) { let x = 0, y = 0; while (el && el !== hero) { x += el.offsetLeft; y += el.offsetTop; el = el.offsetParent; } return [x, y]; }
  // layout: anello dietro la rubric, punto d'impatto sul bordo sinistro della card all'altezza della riga Robots.txt
  function layout() {
    const px = E.x, py = E.y;
    W = canvas.clientWidth; Hh = canvas.clientHeight; heroH = hero.offsetHeight || Hh;
    narrow = W < 1080;
    const dpr = Math.min(devicePixelRatio || 1, 1.25);
    renderer.setPixelRatio(dpr); renderer.setSize(W, Hh, false);
    const dist = Hh / 2 / Math.tan(THREE.MathUtils.degToRad(17.5));
    camera.aspect = W / Hh; camera.position.set(0, 0, dist); camera.far = dist * 4; camera.updateProjectionMatrix();
    shared.uCam.value = dist; shared.uDpr.value = dpr; shared.uRes.value.set(W, Hh);
    const ox = canvas.offsetLeft, oy = canvas.offsetTop;
    let cx = W * 0.7, cy = 88 + heroH * 0.45, Rr = Math.min(heroH * 0.46, W * 0.3);
    const [kx, ky] = card ? off(card) : [W * 0.6, 200];
    if (!narrow && card) {
      // centro poco a sinistra della card: l'arco visibile cade nel varco tra testo e rubric
      cx = kx - ox + card.offsetWidth * 0.3; cy = ky - oy + card.offsetHeight * 0.45;
      Rr = Math.min(card.offsetWidth * 0.73, heroH * 0.46, W * 0.3);
    }
    if (narrow) { cx = W * 0.86; cy = Math.min(Hh * 0.16, 200); Rr = Math.max(W * 0.62, 220); }
    U.uR.value = Rr; U.uRingK.value = narrow ? 1 : 0.55; baseAlpha = narrow ? 0.6 : 1; shared.uFloor.value = narrow ? 0.3 : 0.1; shared.uFloorH.value = narrow ? 0.3 : U.uDark.value ? 0.5 : 0.35;
    group.position.set(cx - W / 2, Hh / 2 - cy, 0);
    // bersaglio dei crawler: bordo sinistro della card sulla riga Robots.txt (in alto sulla card se impilata)
    if (rowEl && !narrow) { const [, ry] = off(rowEl); E.x = kx - ox; E.y = ry - oy + rowEl.offsetHeight / 2; E.h = rowEl.offsetHeight; }
    else { E.x = kx - ox + (card ? card.offsetWidth * 0.72 : 0); E.y = ky - oy; E.h = 30; }
    glow.position.set(E.x - W / 2, Hh / 2 - E.y, 0);
    GU.uSize.value = Math.min(narrow ? 110 : 180, maxPoint / dpr);
    // rettangoli del testo, in coordinate canvas
    const heroCopy = hero.querySelector('.hero-copy');
    const hb = heroCopy.getBoundingClientRect(), [hx, hy] = off(heroCopy);
    const cr = { left: hb.left - hx + ox, top: hb.top - hy + oy };
    const rect = (els, v) => {
      let x0 = 1e5, y0 = 1e5, x1 = -1e5, y1 = -1e5;
      els.forEach((el) => {
        if (!el) return;
        // per i paragrafi conta il testo vero, non la larghezza del box
        let r = el.getBoundingClientRect();
        if (el.tagName === 'P') { const g = document.createRange(); g.selectNodeContents(el); r = g.getBoundingClientRect(); } x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); });
      if (x1 > x0) v.set(x0 - cr.left, y0 - cr.top, x1 - cr.left, y1 - cr.top);
    };
    const q = (s) => hero.querySelector(s);
    const lines = [...hero.querySelectorAll('h1 .line > span')];
    rect(lines.slice(0, 1), shared.uCopy.value); rect(lines.slice(1), shared.uCopy4.value);
    rect([q('.hero-lead'), q('.audit'), q('.note')], shared.uCopy2.value);
    // fascia libera tra la nav e il titolo, dove passano le scie
    band.y0 = Math.max(-oy + 10, 10); band.y1 = Math.max(band.y0 + 20, shared.uCopy.value.y - 26);
    // corsia libera tra titolo e paragrafo: i 3 bot di ricerca la percorrono come lance
    const l0 = shared.uCopy4.value.w + 7, l1 = shared.uCopy2.value.y - 12;
    lane = l1 > l0 ? (l0 + l1) / 2 : l0;
    // campo basso: sotto la riga delle prove, risalendo a destra del paragrafo
    const pf = q('.hero-proof'), pb = pf ? off(pf)[1] - oy + pf.offsetHeight : Hh * 0.8;
    low.x = shared.uCopy2.value.z + 30; low.y0 = Math.min(pb + 30, Hh - 20); low.y1 = Math.max(low.y0, Math.min(Hh + 40, pb + 220));
    // etichette sotto la riga, allineate a destra contro il muro; nascoste se toccano il testo
    const tx = E.x + ox - 16, ty = E.y + oy + E.h / 2 + 12;
    tags.style.right = (hero.clientWidth - tx) + 'px'; tags.style.top = ty + 'px';
    const tw = tags.offsetWidth, th = tags.offsetHeight, c2 = shared.uCopy2.value;
    const fits = !narrow && tx - tw - ox > c2.z + 20 && ty - oy > Math.max(shared.uCopy.value.w, shared.uCopy4.value.w) - 4;
    tags.classList.toggle('gl-off', !fits);
    if (fits) shared.uCopy3.value.set(tx - tw - ox, ty - oy, tx - ox, ty - oy + th); else shared.uCopy3.value.set(-1e4, -1e4, -1e4, -1e4);
    if (still) bots.forEach((c) => plan(c, 0));
    // solo se il bersaglio si è mosso davvero: plan() ripesca i percorsi a caso
    else if (Math.abs(E.x - px) + Math.abs(E.y - py) > 2) bots.forEach((c) => { if (clock - c.launch < c.tin) plan(c, c.launch); });
    kick();
  }

  // stato punteggio: arco che scorre in ~900ms (expo-out) + onda
  let litFrom = 0, litTo = 0, litT0 = -10, pulseT0 = -10;
  function setScore(score, rob) {
    const to = Math.max(0, Math.min(100, score || 0)) / 100;
    if (rob !== robots) {
      robots = rob;
      tags.classList.toggle('is-ok', robots);
      pulseArmed = robots && !still;
      // stessa curva per entrambi gli esiti: chi è ancora in volo cambia destino senza scatti
      bots.forEach((c) => { if (c.search && (still || clock - c.launch < c.tin)) c.block = !robots; });
    }
    if (still) { U.uLit.value = litTo = to; kick(); return; }
    // in pausa il tempo è fermo: arco subito al valore e niente bagliore di blocco residuo
    if (paused()) { U.uLit.value = litFrom = litTo = to; bots.forEach((c) => { if (c.search) c.block = !robots; }); if (robots) eBad = 0; else { eOk = 0; eBad = 1; } kick(); return; }
    if (Math.abs(to - litTo) < 1e-4) return;
    litFrom = U.uLit.value; litTo = to; litT0 = Math.max(clock, 0.5);
    if (clock > 0.6) pulseT0 = clock;
  }

  // puntatore e scroll, sempre interpolati
  const tilt = { x: 0, y: 0, tx: 0, ty: 0 }, scroll = { v: 0 }, mouse = { x: -1e4, y: -1e4, on: 0, ton: 0 };
  if (fine && !still) {
    addEventListener('pointermove', (e) => {
      tilt.tx = (e.clientX / innerWidth) * 2 - 1; tilt.ty = (e.clientY / innerHeight) * 2 - 1;
      const r = canvas.getBoundingClientRect();
      mouse.x = e.clientX - r.left; mouse.y = e.clientY - r.top; mouse.ton = 1;
    }, { passive: true });
    document.addEventListener('pointerleave', () => { mouse.ton = 0; tilt.tx = tilt.ty = 0; });
  }

  let visible = true, running = false, last = 0, shown = false, raf = 0, dead = false;
  const paused = () => document.documentElement.classList.contains('motion-off');
  const schedule = () => { if (!raf) raf = requestAnimationFrame(frame); };
  function frame(now) {
    raf = 0;
    // massimo 60 fps anche sugli schermi a 120 Hz
    if (running && last && now - last < 15.5) { schedule(); return; }
    try { draw(now); } catch (e) { running = false; dead = true; warn(e); return; }
    if (running && !(visible && !document.hidden && !paused())) running = false;
    if (running) schedule();
  }
  function draw(now) {
    const dt = running ? Math.min(0.1, Math.max(0, (now - last) / 1000)) : 0; last = now;
    if (!still) clock += dt;
    U.uTime.value = still ? 40 : clock;
    if (!still) {
      U.uIntro.value = clock;
      const k = Math.min(1, (clock - litT0) / 0.9);
      U.uLit.value = k < 0 ? litFrom : litFrom + (litTo - litFrom) * (k >= 1 ? 1 : 1 - Math.pow(2, -10 * k));
      U.uPulse.value = clock - pulseT0;
      const l = 1 - Math.pow(0.001, dt);
      tilt.x += (tilt.tx - tilt.x) * l * 0.5; tilt.y += (tilt.ty - tilt.y) * l * 0.5;
      scroll.v = running ? scroll.v + (Math.min(1, scrollY / heroH) - scroll.v) * l : Math.min(1, scrollY / heroH);
      mouse.on += (mouse.ton - mouse.on) * l * 0.4;
      U.uMouseOn.value = mouse.on; U.uMouse.value.set(mouse.x, mouse.y);
    }
    const s = scroll.v;
    group.rotation.set(-0.5 + tilt.y * 0.06 + s * 0.25, -0.2 + tilt.x * 0.08, s * 0.7 + (still ? 0 : Math.sin(clock * 0.07) * 0.03));
    group.scale.setScalar(1 - 0.22 * s);
    shared.uAlpha.value = baseAlpha * (1 - 0.85 * s);
    updateComets(clock, dt);
    renderer.render(scene, camera);
    if (!shown) { shown = true; requestAnimationFrame(() => canvas.classList.add('on')); }
  }
  // avvia il loop, oppure in reduced motion disegna un solo frame
  function kick() {
    if (dead) return;
    if (still) { schedule(); return; }
    if (paused()) {
      // pausa: un frame statico solo se la hero si vede; se la pausa arriva al caricamento, posa con anello formato e primi impatti
      if (clock < 1.45) clock = 1.45;
      if (visible && !document.hidden) schedule();
      return;
    }
    if (!running && visible && !document.hidden) { running = true; last = performance.now(); schedule(); }
  }

  // shader compilati in parallelo prima del primo frame: niente scatto all'avvio
  if (renderer.compileAsync) await renderer.compileAsync(scene, camera);
  document.addEventListener('geo:score', (e) => { const d = e.detail || {}; setScore(+d.score, !!d.robots); });
  const ro = new ResizeObserver(layout);
  ro.observe(canvas); if (card) ro.observe(card);
  new IntersectionObserver((en) => { visible = en[0].isIntersecting; kick(); }).observe(hero);
  document.addEventListener('visibilitychange', kick);
  document.addEventListener('geo:motion', kick);
  if (!still) addEventListener('scroll', kick, { passive: true });
  new MutationObserver(theme).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', theme);

  // stato iniziale dal DOM: il primo evento può essere già passato
  const rb = document.querySelector('.rb-fixes input[data-cat="robots"]');
  theme(); layout();
  setTimeout(layout, 1600); // dopo le animazioni d'ingresso del testo
  // punteggio dalle righe della rubric, non dal numero che sta contando
  let base = 0; hero.querySelectorAll('.rb-cats li b').forEach((b) => { base += parseInt(b.textContent, 10) || 0; });
  setScore(base, !!(rb && rb.checked));
  tags.classList.toggle('is-ok', robots);
  // i bot di ricerca partono subito (primo impatto entro ~1 s); gli altri sono già in volo
  bots.forEach((c) => plan(c, c.search ? c.i * 0.09 : -R() * 2.2));
  if (still) for (const el of tagEls) el.classList.add('on');
  kick();
}

// il caricamento pigro lo decide app.js: qui si parte subito
init().catch(warn);
