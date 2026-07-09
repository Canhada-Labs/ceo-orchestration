---
name: windows-desktop-e2e
description: >
  End-to-end UI testing for native Windows desktop applications — WPF,
  WinForms, Win32/MFC, and Qt (5.x and 6.x) — driven through pywinauto on top
  of the built-in Windows UI Automation (UIA) accessibility API. Covers
  testability setup (giving every control a stable AutomationId), a page-object
  test structure, a locator priority ladder (AutomationId > name > class+index),
  condition-based waits instead of sleeps, three tiers of test isolation, a
  screenshot/template-match fallback for controls UIA cannot see, Qt-specific
  quirks, and CI on a windows-latest runner. Use when writing or debugging E2E
  tests for a Windows desktop GUI, standing up a desktop test suite, or adding
  testability to an existing native app. Not for web apps (use a browser E2E
  skill), Electron/WebView (browser layer), or mobile.
metadata:
  activation_triggers:
    - write or run E2E / UI tests for a Windows native desktop app (WPF, WinForms, Win32, MFC, Qt)
    - stand up a desktop GUI test suite from scratch
    - diagnose a flaky or failing pywinauto / UI Automation test
    - add AutomationId / accessible names to a desktop app for testability
    - integrate desktop E2E into CI on a windows-latest runner
version: 1.0.0
risk_class: low
source: affaan-m/ecc@81af4076 skills/windows-desktop-e2e/
license: MIT
---

# Windows Desktop E2E Testing

Drive and assert on a running native Windows GUI through **pywinauto** with the
**UIA** backend. UIA is Windows' built-in accessibility API; every supported
framework exposes a tree of UIA elements with readable, actionable properties.
The whole discipline rests on one lever: **stable identifiers on controls**,
then condition-based waits, then assertions on state rather than pixels.

> **Risk note (why `risk_class: low`).** The optional per-step trace can log the
> text typed into fields, and screen recording captures whatever is on screen.
> Keep typed-text tracing **off** on any flow that enters credentials or PII
> (the trace defaults to redacting typed text — never flip that on for login or
> payment tests). Use seeded test accounts, not real ones.

## When to Activate

- Writing or running E2E tests for a Windows native desktop app.
- Standing up a desktop GUI test suite from scratch.
- Diagnosing a flaky or failing desktop automation test.
- Adding testability (AutomationId, accessible names) to an existing app.
- Wiring desktop E2E into CI (`windows-latest` — a real GUI, no Xvfb needed).

### When NOT to use

- **Web apps** -> a browser E2E skill (the DOM is the surface, not UIA).
- **Electron / CEF / WebView2** -> the HTML layer needs browser automation.
- **Mobile** -> platform tools (UIAutomator, XCUITest).
- Pure unit/integration tests that need no running GUI.

## How it fits together

```
Your test (Python)
  -> pywinauto (UIA backend)
     -> Windows UI Automation API   (built into Windows, framework-agnostic)
        -> the app's UIA provider   (each framework ships its own)
           -> the running .exe
```

UIA fidelity varies by framework — plan effort accordingly:

| Framework      | AutomationId | Reliability | Notes                                   |
|----------------|--------------|-------------|-----------------------------------------|
| WPF            | 5/5          | Excellent   | `x:Name` maps straight to AutomationId  |
| WinForms       | 4/5          | Good        | `AccessibleName` surfaces via UIA — verify id vs name per control |
| UWP / WinUI 3  | 5/5          | Excellent   | First-class support                     |
| Qt 6.x         | 5/5          | Excellent   | Accessibility on by default; `Qt6*` classes |
| Qt 5.15+       | 4/5          | Good        | Improved accessibility module           |
| Qt 5.7-5.14    | 3/5          | Fair        | Needs `QT_ACCESSIBILITY=1`; manual objectName |
| Win32 / MFC    | 3/5          | Fair        | Control IDs reachable; text matching common |

## Setup

```bash
# Python 3.8+, Windows only
pip install pywinauto pytest pytest-html Pillow pytest-timeout
# Optional screen recording needs ffmpeg on PATH.
```

Confirm UIA is reachable, then inspect the tree before writing any test:

```python
from pywinauto import Desktop
Desktop(backend="uia").windows()   # lists top-level windows
```

Install **Accessibility Insights for Windows** (free, from Microsoft) — it is
your "DevTools" for the UIA tree: find the `AutomationId` of a control before
you script it. At runtime you can also print the tree:

```python
win.print_control_identifiers()
win.child_window(auto_id="groupBox1").print_control_identifiers()  # narrowed
```

## The one thing that matters most: stable identifiers

Before writing tests, give every interactive control a stable AutomationId.

- **WPF (XAML):** `x:Name="usernameInput"` becomes the AutomationId
  automatically.
- **WinForms:** set `control.AccessibleName = "usernameInput"` (designer or
  code), then confirm in Accessibility Insights whether it surfaces as
  AutomationId or as the UIA Name for that control type (the bridge
  varies; it decides `by_id()` vs `by_name()`).
- **Win32/MFC:** resource control IDs are exposed as AutomationId strings;
  prefer `SetWindowText` for the Name and add `IAccessible` for richer support.
- **Qt:** set **both** `objectName` and `accessibleName` to the same id (the
  latter becomes the UIA Name). Centralize ids in one header to avoid typos.
  See `references/page-object-and-isolation.md` for the Qt helper.

## Locator priority

```
AutomationId  >  Name (visible text)  >  ClassName + index  >  XPath
  (stable)          (readable)              (fragile)          (last resort)
```

Reach for the leftmost that works. `ClassName + index` breaks the moment the
layout changes; use it only when there is genuinely no id or name.

## Wait on conditions, never sleep

Fixed `time.sleep()` is the primary source of desktop-test flakiness. Wait for
the actual state to become true instead:

```python
page.wait_visible(page.by_id("statusLabel"))     # control appears
page.wait_gone(page.by_id("spinnerOverlay"))      # spinner disappears
dlg = page.wait_window("Confirm Delete")          # a dialog pops up
page.wait_until(lambda: page.get_text(page.by_id("lblStatus")) == "Ready")
```

`wait_until` polls an arbitrary predicate — the escape hatch when UIA events are
unreliable. The `BasePage` implementations of these waits are in the reference.

## Test structure (page-object model)

```
tests/
  conftest.py      # app-launch fixture (+ failure screenshot)
  config.py        # APP_PATH / titles / timeouts from env — no hardcoded paths
  pytest.ini
  pages/           # base_page.py, login_page.py, ...  (with __init__.py)
  tests/           # test_login.py, ...                (with __init__.py)
  artifacts/       # screenshots, videos, reports
```

Keep locators and actions in page objects; keep assertions in tests. The full
`BasePage` (locators, waits, `type_text` with a keyboard fallback, `get_text`,
screenshot), an example `LoginPage`, `conftest.py`, `config.py`, and
`pytest.ini` are in `references/page-object-and-isolation.md`.

## Test isolation (three tiers — use the lightest that fits)

1. **Filesystem isolation (default, always).** Launch via `subprocess.Popen`
   with `APPDATA`/`LOCALAPPDATA`/`TEMP` redirected into pytest's `tmp_path`, and
   connect pywinauto by PID. Cleanup is automatic. This is zero-cost and every
   test should use it.
2. **Job Object (optional).** Attach the process to a Windows Job Object so it
   is killed when the fixture's handle is released, and cannot spawn escaping
   child processes. Note: a Job Object does **not** virtualize the filesystem or
   block network — use it only for process-lifetime and child-process
   containment.
3. **Windows Sandbox (CI clean-room).** Run the whole suite inside Windows
   Sandbox for a fresh OS image per run (no leftover registry/GPU state).
   Requires Windows Pro/Enterprise with virtualization; pywinauto and the app
   run inside the sandbox, artifacts map back to the host.

Full fixtures for all three tiers are in the reference. Add `pytest-timeout`
(`timeout = 60`, `timeout_method = thread`) to cap any hung test, and reap
orphaned child processes at exit.

## Assert on state, not pixels

```python
# BAD — brittle geometry assertion
assert btn.rectangle().left == 120
# GOOD — assert observable state
assert page.get_text(page.by_id("lblStatus")) == "Logged in"
assert page.by_id("btnLogout").is_enabled()
```

Also: fresh process per test (function-scoped fixture), not a session-shared
app instance — shared state leaks between tests.

## Flaky-test triage

| Symptom / cause                       | Fix                                            |
|---------------------------------------|------------------------------------------------|
| Control not ready                     | replace `time.sleep` with `wait_visible`       |
| Window not focused                    | `win.set_focus()` before interacting           |
| Animation in progress                 | `wait_until(lambda: not spinner.exists())`     |
| Dialog timing                         | `wait_window(title, timeout=15)`               |
| `set_edit_text` raises NotImplemented | UIA ValuePattern missing (common on Qt 5.x) — the `type_text` keyboard fallback handles it |
| Visible times out                     | window minimized/off-screen — `win.restore()` + `set_focus()` first |

Quarantine a genuinely flaky test with `@pytest.mark.skip(reason="... #issue")`
rather than letting it redden the suite; track it to a fix.

## Qt specifics

- **Enable UIA on Qt 5.x:** set `QT_ACCESSIBILITY=1` **before** launch (module
  top of `conftest.py`, or a CI env). Qt 6.x is on by default.
- **QComboBox / QMessageBox / QDialog** open as **separate top-level windows** —
  wait for the popup as a new root window (`Desktop(backend="uia")`), then act
  on the item inside it, rather than searching within the main window.
- **QTableWidget/View:** address cells via the wrapper's `cell(row, column)`.
- **Self-drawn controls** (`paintEvent`-only, `QGraphicsView`, `QOpenGLWidget`)
  are invisible to UIA — use the screenshot fallback.

Copy-ready Qt snippets (id helper, combo popup, table cells) are in the
reference.

## Fallback: screenshot / template matching

When a control is genuinely unreachable via UIA (self-drawn, third-party, game
engine), match a template image on screen and click its center (`pyautogui` +
`opencv`). This is a last resort — **always try UIA first**. Screenshot
matching is brutally sensitive to display scaling:

1. Capture templates at the **same scaling** as the target machine; do not
   rescue a mismatch with `resize` — the matcher is fragile against resampling.
2. **Pin the CI display scaling** so screenshot dimensions are reproducible.
3. **Record the scale** (`GetDpiForWindow(hwnd) / 96`) alongside each artifact so
   postmortems are obvious.

For a Qt app, prefer "same-scale templates + CI pin" over flipping process-wide
DPI awareness in fixtures — it can conflict with Qt's own DPI handling. The
matcher and a diagnosis-only match-visualizer are in the reference.

## CI (windows-latest)

`windows-latest` is a real GUI environment — no virtual display needed. Check
out, set up Python, install deps, build the app, run pytest with
`APP_PATH`/`APP_TITLE`/`CI=true` in the env, and upload `artifacts/` with
`if: always()`. A ready workflow is in the reference.

## Changelog

- **1.0.0** — Initial authored version. Teaches pywinauto/UIA desktop E2E:
  testability-first identifiers, page-object structure, locator priority,
  condition waits, three isolation tiers, Qt quirks, and the screenshot
  fallback. Clean-room rewrite; heavier code (BasePage, fixtures, isolation
  tiers, Qt snippets, CI) lives in
  `references/page-object-and-isolation.md`.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=902032846c60aed25d78f508e45a0b022504928e7f10878873d8918f08085c71
