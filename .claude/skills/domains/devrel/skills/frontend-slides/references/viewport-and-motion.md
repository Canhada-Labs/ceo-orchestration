# Viewport-safe base + motion reference

Reference for `frontend-slides`. Two things live here: the mandatory CSS that
keeps every slide inside one viewport, and the motion/style vocabulary for
picking a distinctive, intentional look. Copy the CSS base into every deck and
theme on top of it.

## The golden rule

```text
One slide == one viewport height.
Content does not fit  ->  split into more slides.
Never scroll inside a slide.  Never shrink body text below readable size.
```

## Mandatory viewport CSS base

Paste this once, near the top of your `<style>` block, then layer theme
colors and fonts on top. Every value that a person might tune is a custom
property, so re-theming is a handful of edits.

```css
/* --- 1. Lock the page to the viewport ------------------------------- */
html, body { height: 100%; overflow-x: hidden; }
html { scroll-snap-type: y mandatory; scroll-behavior: smooth; }
* { margin: 0; padding: 0; box-sizing: border-box; }

/* --- 2. One slide == one viewport, never overflowing ---------------- */
.slide {
  width: 100vw;
  height: 100vh;
  height: 100dvh;          /* dynamic vh: correct on mobile URL-bar resize */
  overflow: hidden;        /* the hard stop against any internal scroll   */
  scroll-snap-align: start;
  display: flex;
  flex-direction: column;
  position: relative;
}
.slide-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  max-height: 100%;
  overflow: hidden;        /* second layer of overflow protection        */
  padding: var(--pad-slide);
}

/* --- 3. Fluid type + spacing scale (tune the clamps, not fixed px) --- */
:root {
  --type-title:  clamp(1.5rem, 5vw, 4rem);
  --type-h2:     clamp(1.25rem, 3.5vw, 2.5rem);
  --type-h3:     clamp(1rem, 2.5vw, 1.75rem);
  --type-body:   clamp(0.75rem, 1.5vw, 1.125rem);
  --type-small:  clamp(0.65rem, 1vw, 0.875rem);

  --pad-slide:   clamp(1rem, 4vw, 4rem);
  --gap-block:   clamp(0.5rem, 2vw, 2rem);
  --gap-item:    clamp(0.25rem, 1vw, 1rem);

  --ease-out:    cubic-bezier(0.16, 1, 0.3, 1);
  --dur:         0.6s;
}

/* --- 4. Containers, lists, grids, media all viewport-relative ------- */
.card, .panel { max-width: min(90vw, 1000px); max-height: min(80vh, 700px); }
.bullets { display: flex; flex-direction: column; gap: clamp(0.4rem, 1vh, 1rem); }
.bullets li { font-size: var(--type-body); line-height: 1.4; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 250px), 1fr));
  gap: clamp(0.5rem, 1.5vw, 1rem);
}
img { max-width: 100%; max-height: min(50vh, 400px); object-fit: contain; }

/* --- 5. Short-height + narrow breakpoints (this is what saves you) -- */
@media (max-height: 700px) {
  :root { --pad-slide: clamp(0.75rem, 3vw, 2rem);
          --type-title: clamp(1.25rem, 4.5vw, 2.5rem); }
}
@media (max-height: 600px) {
  :root { --pad-slide: clamp(0.5rem, 2.5vw, 1.5rem);
          --type-title: clamp(1.1rem, 4vw, 2rem);
          --type-body: clamp(0.7rem, 1.2vw, 0.95rem); }
  .nav-dots, .decorative { display: none; }   /* drop chrome first */
}
@media (max-height: 500px) {
  :root { --pad-slide: clamp(0.4rem, 2vw, 1rem);
          --type-title: clamp(1rem, 3.5vw, 1.5rem);
          --type-body: clamp(0.65rem, 1vw, 0.85rem); }
}
@media (max-width: 600px) {
  :root { --type-title: clamp(1.25rem, 7vw, 2.5rem); }
  .grid { grid-template-columns: 1fr; }
}

/* --- 6. Respect reduced motion -------------------------------------- */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.2s !important;
  }
  html { scroll-behavior: auto; }
}
```

### Viewport checklist

- Every `.slide` has `100vh` + `100dvh` + `overflow: hidden`.
- All type and spacing use `clamp()` or viewport units — no fixed px body text.
- Images carry a `max-height`; grids use `auto-fit` + `minmax()`.
- Short-height breakpoints exist at 700 / 600 / 500 px.
- If any slide feels cramped, the fix is *split it*, not shrink it.

## Reveal-on-enter motion

Slides animate when they scroll into view. Add a `visible` class with an
`IntersectionObserver`; CSS does the rest.

```css
.reveal { opacity: 0; transform: translateY(30px);
          transition: opacity var(--dur) var(--ease-out),
                      transform var(--dur) var(--ease-out); }
.slide.visible .reveal { opacity: 1; transform: translateY(0); }

/* stagger children for a sequential feel */
.slide.visible .reveal:nth-child(1) { transition-delay: 0.1s; }
.slide.visible .reveal:nth-child(2) { transition-delay: 0.2s; }
.slide.visible .reveal:nth-child(3) { transition-delay: 0.3s; }

/* variants: scale-in, slide-from-left, blur-in — same visible toggle */
.reveal-scale { opacity: 0; transform: scale(0.92); }
.slide.visible .reveal-scale { opacity: 1; transform: scale(1); }
.reveal-blur  { opacity: 0; filter: blur(10px); }
.slide.visible .reveal-blur  { opacity: 1; filter: blur(0); }
```

```javascript
// Toggle `visible` as each slide enters the viewport.
const io = new IntersectionObserver((entries) => {
  for (const e of entries) e.target.classList.toggle("visible", e.isIntersecting);
}, { threshold: 0.4 });
document.querySelectorAll(".slide").forEach((s) => io.observe(s));
```

## Feeling -> motion direction

| Feeling                   | Motion direction                                        |
|---------------------------|---------------------------------------------------------|
| Dramatic / cinematic      | slow fades (1-1.5s), large scale-ins, parallax          |
| Techy / futuristic        | glow, grid reveals, scramble text, restrained particles |
| Playful / friendly        | springy easing, floating/bob, rounded shapes            |
| Professional / corporate  | fast subtle 200-300ms transitions, clean cuts           |
| Calm / minimal            | very slow gentle fades, whitespace-first                |
| Editorial / magazine      | staggered text + image interplay, strong hierarchy      |

Match motion to the message. Movement should carry meaning (draw the eye to the
next idea); noisy animation on every element reads as a template, not a voice.

## Style archetypes (adapt, do not copy)

Pick a direction and commit — a distinctive deck reads as intentional. These are
starting archetypes to adapt to the topic and brand, not a fixed catalog:

- **editorial-serif** — a display serif paired with a clean sans body, generous
  rules and pull quotes; good for narrative talks and essays.
- **technical-mono** — a monospace voice, terminal/scanline framing, precise
  rhythm; good for CLI tools, APIs, engineering demos.
- **high-contrast keynote** — one bold display face, oversized section numbers,
  a single saturated accent on a dark field; good for launches and statements.
- **soft-geometric** — rounded cards, pastel accents, soft shadows; good for
  onboarding and lighter product overviews.
- **atmospheric-dark** — near-black field, blurred abstract shapes, fine rules,
  restrained motion; good for premium/product narratives.

Choose fonts from a web font host, prefer abstract geometry over stock
illustration, and let one accent color do the work rather than a rainbow.

## Background texture snippets

```css
/* layered radial gradients for depth */
.bg-mesh {
  background:
    radial-gradient(ellipse at 20% 80%, rgba(120,90,255,0.28) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, rgba(0,220,180,0.20) 0%, transparent 50%),
    var(--bg);
}
/* subtle structural grid */
.bg-grid {
  background-image:
    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 50px 50px;
}
/* grain via an inline SVG data URI (keep the payload short/placeholder) */
.bg-noise { background-image: url("data:image/svg+xml,<svg .../>"); }
```

## CSS gotcha: negated math functions

Browsers silently ignore a leading minus on a CSS function:

```css
/* IGNORED — does nothing */    right: -clamp(28px, 3.5vw, 44px);
/* CORRECT */                   right: calc(-1 * clamp(28px, 3.5vw, 44px));
```

## Validation sizes

Desktop 1920x1080 / 1440x900 / 1280x720; tablet 1024x768 / 768x1024;
phone 375x667 / 414x896; landscape phone 667x375 / 896x414.
