# Playwright demo helpers

Reference for `ui-demo`. Reusable helpers for the Rehearse and Record phases,
plus a script skeleton. These are illustrative building blocks — adapt names
and details to the app. The load-bearing techniques: **re-inject overlays
after every navigation**, **move before clicking**, **type visibly**, and
**never swallow a selector failure**.

## Discovery: dump the real interactive elements

Run this against each page in the flow *before* scripting anything.

```javascript
// Returns the visible, interactive elements actually present on the page.
async function dumpFields(page) {
  return page.evaluate(() => {
    const out = [];
    const sel = "input, select, textarea, button, [contenteditable]";
    for (const el of document.querySelectorAll(sel)) {
      if (el.offsetParent === null) continue; // skip hidden
      out.push({
        tag: el.tagName,
        type: el.type || "",
        name: el.name || "",
        placeholder: el.placeholder || "",
        text: (el.textContent || "").trim().slice(0, 40),
        editable: el.isContentEditable,
        role: el.getAttribute("role") || "",
      });
    }
    return out;
  });
}
// console.log(JSON.stringify(await dumpFields(page), null, 2));
```

For a `<select>`, also dump each option's value and text, and treat
`value === "0"` or text starting with "Select" as a placeholder to skip.

## Rehearsal: verify selectors, fail loudly

```javascript
// Returns true if the element is visible; on miss, dumps what IS visible.
async function ensureVisible(page, target, label) {
  const el = typeof target === "string" ? page.locator(target).first() : target;
  const ok = await el.isVisible().catch(() => false);
  if (ok) {
    console.log(`OK    ${label}`);
    return true;
  }
  const visible = await page.evaluate(() =>
    Array.from(document.querySelectorAll("button, input, select, textarea, a"))
      .filter((e) => e.offsetParent !== null)
      .map((e) => `${e.tagName}[${e.type || ""}] "${(e.textContent || "").trim().slice(0, 30)}"`)
      .join("\n  ")
  );
  console.error(`MISS  ${label}  (target: ${typeof target === "string" ? target : "<locator>"})`);
  console.error("  visible now:\n  " + visible);
  return false;
}

// Walk an ordered step list; exit non-zero if any selector is missing.
async function rehearse(page, steps) {
  let allOk = true;
  for (const s of steps) {
    if (!(await ensureVisible(page, s.selector, s.label))) allOk = false;
  }
  if (!allOk) {
    console.error("REHEARSAL FAILED — fix selectors before recording");
    process.exit(1);
  }
  console.log("REHEARSAL PASSED");
}
```

## Overlays: cursor + subtitles (re-inject after every navigation)

```javascript
// Visible arrow cursor that tracks the mouse. The overlay is wiped on
// navigation, so call this again after every page load.
async function injectCursor(page) {
  await page.evaluate(() => {
    if (document.getElementById("demo-cursor")) return;
    const c = document.createElement("div");
    c.id = "demo-cursor";
    c.innerHTML =
      '<svg width="24" height="24" viewBox="0 0 24 24" fill="none">' +
      '<path d="M5 3 L19 12 L12 13 L9 20 Z" fill="#fff" stroke="#000" ' +
      'stroke-width="1.5" stroke-linejoin="round"/></svg>';
    c.style.cssText =
      "position:fixed;z-index:999999;pointer-events:none;width:24px;height:24px;" +
      "transition:left .1s,top .1s;filter:drop-shadow(1px 1px 2px rgba(0,0,0,.3));";
    document.body.appendChild(c);
    addEventListener("mousemove", (e) => {
      c.style.left = e.clientX + "px";
      c.style.top = e.clientY + "px";
    });
  });
}

async function injectSubtitleBar(page) {
  await page.evaluate(() => {
    if (document.getElementById("demo-subtitle")) return;
    const b = document.createElement("div");
    b.id = "demo-subtitle";
    b.style.cssText =
      "position:fixed;left:0;right:0;bottom:0;z-index:999998;text-align:center;" +
      "padding:12px 24px;background:rgba(0,0,0,.75);color:#fff;font-size:16px;" +
      'font-weight:500;font-family:-apple-system,"Segoe UI",sans-serif;' +
      "transition:opacity .3s;opacity:0;pointer-events:none;";
    document.body.appendChild(b);
  });
}

// Set caption text, or pass "" to fade it out during a quiet moment.
async function showSubtitle(page, text) {
  await page.evaluate((t) => {
    const b = document.getElementById("demo-subtitle");
    if (!b) return;
    b.textContent = t || "";
    b.style.opacity = t ? "1" : "0";
  }, text);
  if (text) await page.waitForTimeout(800);
}
```

## Interaction: move-then-click, visible typing, panning

```javascript
// Move the mouse to the element in steps, pause, then click. Never teleport.
async function moveAndClick(page, target, label, opts = {}) {
  const { after = 800, ...clickOpts } = opts;
  const el = typeof target === "string" ? page.locator(target).first() : target;
  if (!(await el.isVisible().catch(() => false))) {
    console.error(`skip moveAndClick — "${label}" not visible`);
    return false;
  }
  try {
    await el.scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    const box = await el.boundingBox();
    if (box) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 10 });
      await page.waitForTimeout(400);
    }
    await el.click(clickOpts);
  } catch (e) {
    console.error(`moveAndClick failed on "${label}": ${e.message}`);
    return false;
  }
  await page.waitForTimeout(after);
  return true;
}

// Type character-by-character so the input is visible on camera.
async function typeSlowly(page, target, text, label, delay = 35) {
  const el = typeof target === "string" ? page.locator(target).first() : target;
  if (!(await el.isVisible().catch(() => false))) {
    console.error(`skip typeSlowly — "${label}" not visible`);
    return false;
  }
  await moveAndClick(page, el, label);
  await el.fill("");
  await el.pressSequentially(text, { delay });
  await page.waitForTimeout(500);
  return true;
}

// Pan the cursor across the top few elements of a dashboard for orientation.
async function panElements(page, selector, max = 6) {
  const els = await page.locator(selector).all();
  for (let i = 0; i < Math.min(els.length, max); i++) {
    try {
      const box = await els[i].boundingBox();
      if (box && box.y < 700) {
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 8 });
        await page.waitForTimeout(600);
      }
    } catch (e) {
      console.warn(`panElements skipped #${i}: ${e.message}`);
    }
  }
}

// Smooth scroll instead of a jump.
async function smoothScrollTo(page, y) {
  await page.evaluate((top) => scrollTo({ top, behavior: "smooth" }), y);
  await page.waitForTimeout(1500);
}
```

## Script skeleton (rehearse + record in one file)

```javascript
"use strict";
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BASE_URL = process.env.QA_BASE_URL || "http://localhost:3000";
const VIDEO_DIR = path.join(__dirname, "recordings");
const OUTPUT = "demo-feature.webm";
const REHEARSAL = process.argv.includes("--rehearse");
// Paste the helpers above here.

(async () => {
  const browser = await chromium.launch({ headless: true });

  if (REHEARSAL) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
    const page = await ctx.newPage();
    // Navigate the flow and call rehearse(page, steps) for each page.
    await browser.close();
    return;
  }

  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir: VIDEO_DIR, size: { width: 1280, height: 720 } },
  });
  const page = await ctx.newPage();
  try {
    await injectCursor(page);
    await injectSubtitleBar(page);
    await showSubtitle(page, "Step 1 - Logging in");
    // ...login...

    await page.goto(`${BASE_URL}/dashboard`);
    await injectCursor(page);          // re-inject after navigation
    await injectSubtitleBar(page);     // re-inject after navigation
    await showSubtitle(page, "Step 2 - Dashboard overview");
    // ...panElements...

    await showSubtitle(page, "Step 3 - Main workflow");
    // ...action sequence...

    await showSubtitle(page, "Step 4 - Result");
    await showSubtitle(page, "");
  } catch (err) {
    console.error("DEMO ERROR:", err.message);
  } finally {
    await ctx.close(); // finalizes the video file
    const video = page.video();
    if (video) {
      const src = await video.path();
      const dest = path.join(VIDEO_DIR, OUTPUT);
      try {
        fs.copyFileSync(src, dest);
        console.log("Video saved:", dest);
      } catch (e) {
        console.error("copy failed:", e.message, "\n  src:", src, "\n  dest:", dest);
      }
    }
    await browser.close();
  }
})();
```

```bash
node demo-script.cjs --rehearse   # phase 2
node demo-script.cjs              # phase 3
```
