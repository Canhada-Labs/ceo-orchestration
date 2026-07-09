---
name: frontend-slides
description: >
  Build zero-dependency, animation-rich HTML presentations — from a topic,
  from rough notes, or by converting an existing PowerPoint deck to the web.
  The distinguishing discipline is two hard gates most slide generators skip:
  (1) every slide must fit exactly one viewport with no internal scroll, and
  (2) non-designers are guided to a distinctive look through visual
  exploration (real preview slides they can react to) instead of abstract
  style questionnaires. Produces a single self-contained .html file with
  inline CSS/JS, keyboard/wheel/touch navigation, reveal-on-enter animation,
  and reduced-motion support. Use when someone wants to create a talk, pitch,
  workshop, or internal deck; convert a .ppt/.pptx to HTML; or fix the layout,
  motion, or typography of an HTML deck that already exists.
metadata:
  activation_triggers:
    - build a presentation / slide deck / pitch deck / talk deck / workshop deck
    - convert ppt / pptx / powerpoint into html slides
    - improve layout, motion, or typography of an existing HTML deck
    - explore presentation styles with someone unsure of their aesthetic
    - slide overflow, viewport-fit, scroll-snap, or reveal-animation problems
version: 1.0.0
risk_class: low
source: affaan-m/ecc@81af4076 skills/frontend-slides/
license: MIT
---

# Frontend Slides

Generate a browser-native presentation that runs from a single local `.html`
file with no build step and no runtime dependencies. The value of this skill
over a generic "make me slides" prompt is two enforced gates — **viewport fit**
and **style discovery by preview** — plus production-quality navigation and
accessibility baked in.

## When to Activate

- Someone wants a talk deck, pitch deck, workshop deck, or internal update deck.
- Someone hands you a `.ppt`/`.pptx` and wants it as a web presentation.
- An existing HTML deck needs better layout, motion, or type — or a slide is
  overflowing/scrolling and must be made viewport-safe.
- Someone wants to "make it look good" but cannot name a style — drive style
  discovery through previews, not a questionnaire.

## Non-negotiables

1. **Zero dependencies.** Default to one self-contained HTML file, CSS and JS
   inline. Fonts from a web font host are the only external fetch.
2. **Viewport fit is a hard gate.** Every slide occupies exactly one viewport
   and never scrolls internally. This is the section that fails most decks —
   treat it as a blocking check, not a nicety.
3. **Show, don't ask.** Discover the aesthetic with real preview slides the
   person can look at, not adjectives.
4. **Distinctive by default.** Avoid the generic look (a purple gradient,
   a neutral grotesk on white, template chrome). Commit to a direction.
5. **Production quality.** Commented, accessible, responsive, performant.

## Workflow

### 1. Detect the mode

- **New deck** — a topic, notes, or finished copy.
- **Conversion** — a `.ppt`/`.pptx` to bring to the web.
- **Enhancement** — HTML slides that already exist and need work.

### 2. Discover the content

Ask only the minimum: purpose (pitch / teaching / conference / internal),
rough length (short 5-10, medium 10-20, long 20+), and content state
(finished copy / rough notes / topic only). If they have copy, get it pasted
before you style anything.

### 3. Discover the style (default path: visual exploration)

If the person already knows the direction, use it and skip previews.
Otherwise:

1. Ask what the deck should make the audience *feel* — impressed, energized,
   focused, or moved. One word is enough to pick a direction.
2. Generate **three single-slide preview files** in a scratch directory
   (e.g. `slide-previews/`). Each is self-contained, shows type + color +
   motion clearly, and stays small (~100 lines of slide content).
3. Let them pick one, or mix elements across two.

Map feeling to a concrete direction (voice + palette + motion) using
`references/viewport-and-motion.md`. Teach yourself the *method* of committing
to a distinctive direction rather than reaching for a default — the reference
gives archetypes (editorial-serif, technical-mono, high-contrast keynote,
soft-geometric, atmospheric-dark) as starting points to adapt, not a fixed
brand list to copy.

### 4. Build

Output `presentation.html` (or `<name>.html`). Use an `assets/` folder only
when the deck carries extracted or user-supplied images.

Required structure:

- semantic slide sections (`<main>`, `<section>`, `<nav>`);
- the viewport-safe CSS base from `references/viewport-and-motion.md`;
- CSS custom properties for every theme value (one edit re-themes the deck);
- a small presentation-controller class for keyboard, wheel, and touch nav;
- an `IntersectionObserver` that adds a `visible` class to drive reveals;
- `prefers-reduced-motion` handling.

### 5. Enforce viewport fit (the hard gate)

- Every `.slide` uses `height: 100vh; height: 100dvh; overflow: hidden;`.
- All type and spacing scale with `clamp()` — never fixed px for body copy.
- When content will not fit, **split into more slides** — never shrink text
  below readable size and never allow a scrollbar inside a slide.
- Apply the short-height breakpoints (700 / 600 / 500 px) from the reference so
  landscape phones and short laptops still fit.

### 6. Validate

Check the finished deck at 1920x1080, 1280x720, 768x1024, 375x667, and
667x375. If browser automation is available, drive it to confirm no slide
overflows and that keyboard navigation advances slides. (A companion
demo/E2E skill can record or exercise the result.)

### 7. Deliver

- Remove temporary preview files unless asked to keep them.
- Open the deck with the OS-appropriate opener when useful: macOS `open`,
  Linux `xdg-open`, Windows `start ""`.
- Summarize: file path, the style direction chosen, slide count, and the
  handful of CSS custom properties to tweak for re-theming.

## PowerPoint conversion

Keep conversion **cross-platform** — reach for Python, not OS-only tooling.

1. Extract text, speaker notes, and images while preserving slide order. The
   `python-pptx` package (third-party, optional) reads a `.pptx` cleanly:
   iterate slides, pull shape text and the title placeholder, save picture
   blobs to `assets/`, and read `notes_slide` for speaker notes. If it is not
   installed, ask whether to install it or fall back to a manual/export path
   rather than assuming.
2. Preserve slide order, notes, and extracted assets in a small intermediate
   structure (one record per slide: title, body blocks, image paths, notes).
3. Then run the same style-discovery + build workflow as a new deck.

> This skill ships no bundled extractor script — a `.pptx` reader needs a
> third-party parser, which conflicts with the zero-dependency posture. Treat
> the reader as an optional tool the user opts into, and keep the extraction
> logic small and inline.

## Implementation notes

- **HTML/CSS:** inline unless the user explicitly wants a multi-file project.
  Prefer atmospheric backgrounds, a strong type hierarchy, and abstract
  geometry (gradients, grids, noise, shapes) over stock illustration.
- **JavaScript:** keyboard nav (arrows / space / page-up-down), touch/swipe,
  mouse-wheel, a progress indicator or slide index, and reveal-on-enter
  triggers via `IntersectionObserver`.
- **Optional inline editing** (only if the user opts in): gate the visibility
  of any edit UI behind JS classes — do **not** use a CSS `~` sibling
  hover-reveal, because `pointer-events: none` on the button breaks the hover
  chain. When exporting the edited file, strip edit state (`contenteditable`
  attributes, edit-active body class, toggle/banner classes) *before* reading
  `outerHTML`, then restore it — otherwise the saved file opens stuck in edit
  mode. When you capture `outerHTML`, clear generated nav-dots first or they
  duplicate on re-open.
- **Images:** reference by file path (not base64) for local viewing; constrain
  every image with `max-height`; resize anything over ~1 MB; never overwrite an
  original (write a `_processed` copy).

## Accessibility

- Semantic structure (`main`, `section`, `nav`).
- Readable contrast; keyboard-only navigation must work end to end.
- Honor `prefers-reduced-motion` (collapse animation, disable smooth scroll).

## Content density limits

Use these maxima unless the user explicitly asks for denser slides *and*
readability still holds:

| Slide type   | Limit                                          |
|--------------|------------------------------------------------|
| Title        | 1 heading + 1 subtitle + optional tagline      |
| Content      | 1 heading + 4-6 bullets or 2 short paragraphs  |
| Feature grid | 6 cards max                                    |
| Code         | 8-10 lines max                                 |
| Quote        | 1 quote + attribution                          |
| Image        | 1 image, constrained by the viewport           |

## Anti-patterns

- Generic startup gradient with no visual identity.
- System-font decks unless intentionally editorial/utilitarian.
- Bullet walls; tiny type; code blocks that need scrolling.
- Fixed-height content boxes that break on short screens.
- Negated CSS math functions like `right: -clamp(...)` — browsers silently
  ignore them. Use `calc(-1 * clamp(...))`.

## Deliverable checklist

- Runs from a local file in a browser, no build step.
- Every slide fits the viewport with no internal scroll.
- The style is distinctive and intentional, not a default.
- Motion is meaningful, not noisy; reduced motion is respected.
- File path and the re-theming custom properties are explained at handoff.

## Changelog

- **1.0.0** — Initial authored version. Teaches viewport-locked HTML slide
  generation, preview-driven style discovery, cross-platform PPTX conversion,
  and accessible navigation. Clean-room rewrite; the viewport CSS base and the
  motion/style archetypes live in `references/viewport-and-motion.md`.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=de4437a4086c12429c3dff77077d6cbdaac922fd7d5137f31540cc97dfe7efab
