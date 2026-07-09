---
name: ui-demo
description: >
  Record a polished demo/walkthrough video of a web application with a browser
  automation driver (Playwright). Produces a WebM with a visible arrow cursor,
  natural human pacing, on-screen step subtitles, and a storytelling flow —
  not a jittery instant-fill capture. The defining discipline is a three-phase
  method: Discover the real page (dump the actual interactive elements before
  scripting), Rehearse (verify every selector resolves, failing loudly), then
  Record. Use when someone asks for a demo video, screen recording, product
  walkthrough, or tutorial video of a running web app for docs, onboarding, or
  a stakeholder showcase.
metadata:
  activation_triggers:
    - record a demo video / walkthrough / screen recording / tutorial of a web app
    - showcase a feature or workflow visually as a video
    - produce a WebM with a visible cursor and natural pacing
    - a demo recording keeps breaking on missing selectors or a too-fast capture
    - need a video for documentation, onboarding, or a stakeholder demo
version: 1.0.0
risk_class: low
source: affaan-m/ecc@81af4076 skills/ui-demo/
license: MIT
---

# UI Demo Video Recorder

Drive a headless browser through an app and record the session as a WebM, with
an injected cursor overlay, deliberate pacing, and step subtitles so the result
looks like a guided tour rather than a script running at machine speed.

> **Risk note (why `risk_class: low`).** This skill drives a real browser and
> types into real forms, including login screens, and can record whatever is
> on screen. Never hardcode real credentials or PII into a demo script, never
> point it at production data you would not want in a shared video, and prefer
> a seeded demo/staging account. Treat the recorded artifact as shareable — so
> nothing secret should ever appear in frame.

## When to Activate

- Someone asks for a "demo video", "screen recording", "walkthrough", or
  "tutorial" of a web app.
- Someone wants to show a feature or workflow visually for docs, onboarding, or
  a stakeholder update.
- A prior recording keeps breaking because selectors were assumed, or it looks
  bad because it runs too fast with a teleporting/dot cursor.

## The three phases — never skip to recording

Every demo goes **Discover -> Rehearse -> Record**. Skipping discovery is why
recordings break silently; skipping rehearsal is why they break on camera.

### Phase 1 — Discover

You cannot script what you have not seen. A field you assumed was a `<textarea>`
may be an `<input>`; a dropdown you assumed was a `<select>` may be a custom
component; a comment box may support `@mentions` or `#tags`. Wrong assumptions
fail silently mid-recording.

Navigate to **each page in the flow** and dump its visible interactive
elements before writing a single step. In the page context, collect the tag,
type, name, placeholder, trimmed text, `contenteditable`, and `role` for every
visible `input, select, textarea, button, [contenteditable]`, and log it as
JSON.

Then look specifically for:

- **Field kind** — real `<select>` vs. custom dropdown vs. combobox.
- **Select options** — dump both `value` and visible text. Placeholder options
  often carry `value="0"` or `value=""` and look real; skip options whose text
  starts with "Select" or whose value is `"0"`.
- **Rich text** — does the comment box support `@mentions`, `#tags`, markdown,
  or emoji? The placeholder usually tells you.
- **Required fields** — which fields block submit? Try submitting empty to
  surface validation.
- **Dynamic fields** — do some appear only after others are filled?
- **Exact button labels** — `Submit` vs. `Submit Request` vs. `Send`.
- **Table columns** — for table-driven modals, map each numeric input to its
  column header rather than assuming all numeric inputs mean the same thing.

Output a small **field map per page** — the source of truth for the selectors
you will script.

### Phase 2 — Rehearse

Run the whole flow **without recording** and verify every selector resolves.
Silent selector failures are the number-one cause of broken recordings, and
rehearsal catches them cheaply.

Wrap each lookup in a helper that logs loudly and, on failure, dumps the
currently-visible interactive elements so you can find the correct selector
immediately. Walk an ordered list of `{ label, selector }` steps; if any step
fails to resolve, print the visible-element dump and exit non-zero. Only
proceed to recording once every selector passes. When one fails: read the dump,
fix the selector, re-run rehearsal.

See `references/playwright-helpers.md` for `ensureVisible` and a rehearsal
harness.

### Phase 3 — Record

Only after discovery and rehearsal pass.

**Storytelling flow.** Plan the video as a story. Follow the requested order,
or default to: *Entry* (log in / land on the start page) -> *Context* (pan the
surroundings so viewers orient) -> *Action* (the main workflow) -> *Variation*
(a secondary feature — settings, theme, locale) -> *Result* (the outcome or
confirmation).

**Pacing.** Deliberate pauses are what make it watchable:

| Moment                    | Pause      |
|---------------------------|------------|
| After login               | ~4s        |
| After navigation          | ~3s        |
| After clicking a button   | ~2s        |
| Between major steps       | ~1.5-2s    |
| After the final action    | ~3s        |
| Typing                    | ~25-40ms/char |

**Visible cursor.** Inject an SVG arrow cursor (a real arrow, not a dot) that
follows `mousemove`. The overlay is destroyed on navigation, so **re-inject it
after every page load** — this is the single most common thing people forget.

**Never teleport the cursor.** Move the mouse to the target in steps, pause,
*then* click. Give every click a descriptive label for debugging.

**Type visibly.** Clear the field, then type character-by-character with a small
delay — never instant-fill.

**Scroll smoothly** (`behavior: 'smooth'`), and when showing a dashboard, pan
the cursor across a few key elements so the eye follows.

**Step subtitles.** Inject a bottom subtitle bar (also re-injected after every
navigation) and set short `Step N - Action` captions (< ~60 chars) at each
major transition; clear it during long pauses where the UI speaks for itself.

The reusable helpers — `injectCursor`, `injectSubtitleBar`/`showSubtitle`,
`moveAndClick`, `typeSlowly`, `panElements`, and a full script skeleton with a
`--rehearse` flag — are in `references/playwright-helpers.md`.

## Recording settings

- Headless browser, viewport and video size both `1280x720`.
- Record to a video directory; after the run, **copy the randomly-named video
  file to a stable output name** (e.g. `demo-<feature>.webm`) so the artifact
  path is predictable.
- Popups open as separate pages and produce separate video files — capture
  popup pages explicitly and merge later if the flow needs them.

## Pre-recording checklist

- [ ] Discovery complete; a field map exists per page.
- [ ] Rehearsal passes — every selector OK.
- [ ] Headless; resolution `1280x720`.
- [ ] Cursor + subtitle overlays re-injected after every navigation.
- [ ] `Step N - ...` subtitles at each major transition.
- [ ] All clicks go through the move-then-click helper with labels.
- [ ] All input goes through the visible-typing helper.
- [ ] No silent catches — helpers log warnings.
- [ ] Smooth scrolling for content reveals; key pauses are human-visible.
- [ ] Flow matches the requested story order and the *actual* discovered UI.
- [ ] No real credentials/PII anywhere in the script or in frame.

## Common pitfalls

1. Cursor vanishes after navigation — re-inject it.
2. Video too fast — add pauses.
3. Cursor is a dot — use the SVG arrow overlay.
4. Cursor teleports — move before clicking.
5. Modals feel abrupt — add a read pause before confirming.
6. Random video filename — copy to a stable output name.
7. Selector failures swallowed — never use silent catch blocks.
8. Field types assumed — discover them first.
9. Features assumed — inspect the real UI before scripting.
10. Placeholder select values look real — watch for `"0"` and `"Select..."`.

## Changelog

- **1.0.0** — Initial authored version. Teaches the Discover -> Rehearse ->
  Record method, natural pacing, visible-cursor and subtitle overlays,
  move-then-click and visible-typing discipline, and stable artifact output.
  Clean-room rewrite; helper implementations live in
  `references/playwright-helpers.md`.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=16c19c5fc562e2710e9ebb32483a80790a31cc531ccd4b0e82348baab5738c65
