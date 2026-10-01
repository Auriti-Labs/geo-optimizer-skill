#!/usr/bin/env node
/**
 * generate-og-images.mjs — genera og:image dinamiche (1200x630) per ogni pagina
 * dopo `astro build`, tramite satori (@resvg/resvg-js). Post-build:
 *   1. scansiona la directory dist (title, description, canonical, tipo pagina)
 *   2. renderizza un template brandizzato con satori -> SVG -> PNG
 *   3. scrive dist/og/<slug>.png e inietta <meta og:image>/<twitter:image>
 *
 * Logo GeoReady (rettangolo teal + archi bianchi) incluso in alto a sinistra.
 * Testo chiaro su fondo ink (#0D110E) con accento teal — leggibile a 200px.
 */
import { readdirSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import React from 'react';
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';
import { config } from 'dotenv';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const DIST = join(ROOT, 'dist');
const OUT_DIR = join(DIST, 'og');
const W = 1200, H = 630;
const h = React.createElement;

const COLORS = { ink:'#0D110E', paper:'#F4F5F2', pass:'#0B8076', passDeep:'#0F766E', mute:'#9FAB9F' };
// satori accetta solo TTF/OTF, non WOFF2. I TTF sono generati da fontTools a
// build (vedi scripts/convert-fonts.mjs) in public/fonts/ttf/.
const FONT_BOLD = readFileSync(join(ROOT,'public','fonts','ttf','archivo-bold.ttf'));
const FONT_REG = readFileSync(join(ROOT,'public','fonts','ttf','publicsans-regular.ttf'));
const FONTS = [
  { name:'Archivo', data:FONT_BOLD, weight:800, style:'normal' },
  { name:'PublicSans', data:FONT_REG, weight:400, style:'normal' },
];

const GeoLogo = ({ size=40 }) => h('svg', { width:size, height:size, viewBox:'0 0 48 48', fill:'none' },
  h('rect', { width:48, height:48, rx:4, fill:COLORS.pass }),
  h('path', { d:'M11.74 13.71 A16 16 0 1 1 11.74 34.29', stroke:'white', 'stroke-width':2.8, 'stroke-linecap':'round' }),
  h('path', { d:'M8 24 C12 14 18 34 24 24 C30 14 36 34 40 24', stroke:'white', 'stroke-width':2.1, 'stroke-linecap':'round', 'stroke-opacity':0.72 })
);

function pageType(path) {
  const p = (path||'').replace(/^\/+|\/+$/g,'');
  if (!p || p==='index') return 'home';
  if (p.startsWith('guides/')) return 'guide';
  if (p.startsWith('resources/')) return 'guide';
  if (p.endsWith('-alternative')) return 'comparison';
  if (p.startsWith('tools/')) return 'tool';
  if (p==='book') return 'book';
  if (p.startsWith('state-of-geo')) return 'report';
  if (/ai-seo-audit|visibility|citation|perplexity|chatgpt/.test(p)) return 'tool';
  return 'default';
}
const truncate = (s,n) => (s||'').length<=n ? s : s.slice(0,n-1).trim()+'…';
const EYEBROW = { home:'AI SEARCH VISIBILITY', guide:'GUIDE', comparison:'COMPARISON', tool:'TOOL', book:'BOOK', report:'STATE OF GEO', default:'AI SEARCH VISIBILITY' };

function OgTemplate({ eyebrow, title, subtitle, type, slug }) {
  const isComp = type==='comparison';
  const bg = isComp ? '#0F2E29' : COLORS.ink;
  const eyebrowText = isComp
    ? (slug||'COMPARISON').replace(/-alternative$/,'').replace(/-/g,' ').toUpperCase() + ' VS GEOREADY'
    : (EYEBROW[type]||EYEBROW.default);
  return h('div', { style:{ width:W, height:H, background:bg, color:COLORS.paper, display:'flex', flexDirection:'column', padding:'56px 64px', position:'relative', overflow:'hidden', fontFamily:'Archivo' } },
    h('div', { style:{ position:'absolute', top:-90, right:-90, width:340, height:340, borderRadius:'50%', background:isComp?COLORS.pass:'#123B35', opacity:0.8 } }),
    h('div', { style:{ position:'absolute', bottom:-40, right:120, width:180, height:180, borderRadius:'50%', background:isComp?COLORS.passDeep:'#0F766E', opacity:0.5 } }),
    // logo + wordmark
    h('div', { style:{ display:'flex', alignItems:'center', gap:12, position:'relative', zIndex:1 } },
      GeoLogo({ size:46 }),
      h('span', { style:{ fontFamily:'Archivo', fontWeight:800, fontSize:36, letterSpacing:'-0.02em' } },
        h('span', { style:{ color:COLORS.pass } }, 'geo'), 'ready'
      )
    ),
    // eyebrow
    h('div', { style:{ marginTop:48, fontFamily:'PublicSans', fontWeight:400, fontSize:20, letterSpacing:'0.14em', textTransform:'uppercase', color:'#4FD1C5' } }, eyebrowText),
    // titolo 2 righe
    h('div', { style:{ marginTop:16, fontFamily:'Archivo', fontWeight:800, fontSize:50, lineHeight:1.08, letterSpacing:'-0.02em', maxWidth:980 } }, truncate(title,120) || 'GeoReady'),
    // sottotitolo
    subtitle && h('div', { style:{ marginTop:18, fontFamily:'PublicSans', fontWeight:400, fontSize:22, lineHeight:1.35, maxWidth:960, color:COLORS.mute } }, truncate(subtitle,130)),
    // spacer
    h('div', { style:{ flex:1 } }),
    // footer url
    h('div', { style:{ display:'flex', alignItems:'center', gap:12, flexWrap:'wrap', position:'relative', zIndex:1 } },
      h('span', { style:{ fontFamily:'PublicSans', fontSize:20, letterSpacing:'0.06em', color:'#C8D0CB' } }, 'geoready.dev'),
      h('span', { style:{ fontFamily:'PublicSans', fontSize:17, color:'#5C665F' } }, '· Free GEO audit · ChatGPT · Perplexity')
    )
  );
}

function readMeta(htmlPath) {
  const html = readFileSync(htmlPath,'utf-8');
  const title = (html.match(/<title>(.*?)<\/title>/s)||[])[1]?.replace(/<[^>]+>/g,'').trim() || 'GeoReady';
  const desc = (html.match(/<meta name="description" content="([^"]*)"/)||[])[1] || '';
  const canon = (html.match(/rel="canonical" href="([^"]+)"/)||[])[1] || '';
  const slug = (canon.replace('https://geoready.dev/','').replace(/\/$/,'')) || '';
  return { title, desc, canon, slug };
}
function walkPages(dir, out=[]) {
  for (const e of readdirSync(dir,{withFileTypes:true})) {
    const full = join(dir,e.name);
    if (e.isDirectory()) walkPages(full,out);
    else if (e.name==='index.html') out.push(dirname(full));
  }
  return out;
}

async function main() {
  try { config(); } catch {}
  const pages = walkPages(DIST);
  console.log(`[og] generate per ${pages.length} pagine...`);
  mkdirSync(OUT_DIR,{recursive:true});
  let n=0;
  for (const pageDir of pages) {
    const rel = pageDir.replace(DIST+'/','').replace(/\\/g,'/');
    const { title, desc, canon, slug } = readMeta(join(pageDir,'index.html'));
    const type = pageType(rel || slug);
    const el = OgTemplate({ eyebrow:null, title, subtitle:desc, type, slug });
    const svg = await satori(el, { width:W, height:H, fonts:FONTS });
    const png = new Resvg(svg,{ fitWidth:W }).render().asPng();
    const pageName = pageDir === DIST ? 'home'
      : (slug || '').split('/').filter(Boolean).pop()
        || rel.split('/').filter(Boolean).pop() || 'index';
    const outName = pageName + '.png';
    writeFileSync(join(OUT_DIR,outName), png);
    const assetUrl = 'https://geoready.dev/og/'+outName;
    let html = readFileSync(join(pageDir,'index.html'),'utf-8');
    if (/<meta property="og:image"/.test(html)) {
      html = html.replace(/<meta property="og:image"[^>]*>/, `<meta property="og:image" content="${assetUrl}">`);
      html = html.replace(/<meta property="og:image:secure_url"[^>]*>/, `<meta property="og:image:secure_url" content="${assetUrl}">`);
    } else {
      html = html.replace('</title>', `</title>\n    <meta property="og:image" content="${assetUrl}">`);
    }
    if (/<meta name="twitter:image"/.test(html)) html = html.replace(/<meta name="twitter:image"[^>]*>/, `<meta name="twitter:image" content="${assetUrl}">`);
    writeFileSync(join(pageDir,'index.html'), html);
    n++;
  }
  console.log(`[og] OK — ${n} og:image in dist/og/`);
}
main().catch(e=>{ console.error('[og] ERRORE', e); process.exit(1); });
