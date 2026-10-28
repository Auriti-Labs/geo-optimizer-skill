// Scroll reveals for the marketing pages. Loaded lazily by Shell only when the page
// carries [data-reveal], so pages without motion never download GSAP.
// Content is always in the HTML: elements already in view at load are left alone
// (no flash), and reduced motion skips everything.
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

export const EASE = 'expo.out'; // closest GSAP curve to the dashboard --ease cubic-bezier(.16,1,.3,1)

export function initReveals() {
  gsap.registerPlugin(ScrollTrigger);
  const mm = gsap.matchMedia();
  mm.add('(prefers-reduced-motion: no-preference)', () => {
    const fold = window.innerHeight;
    document.querySelectorAll<HTMLElement>('[data-reveal]').forEach((el) => {
      if (el.getBoundingClientRect().top < fold) return;
      // [data-reveal="stagger"] animates its direct children one after another.
      const targets = el.dataset.reveal === 'stagger' ? Array.from(el.children) : el;
      gsap.from(targets, {
        opacity: 0,
        y: 14,
        duration: 0.7,
        ease: EASE,
        stagger: 0.06,
        scrollTrigger: { trigger: el, start: 'top 88%', once: true },
      });
    });
  });
}
