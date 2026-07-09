# Page objects, fixtures, isolation, Qt, and CI

Reference for `windows-desktop-e2e`. Copy-ready building blocks. Everything here
is illustrative pywinauto/UIA usage — adapt ids, titles, and paths to the app
under test. These snippets exercise third-party libraries (pywinauto, pytest,
pyautogui, opencv) by design; they are documentation, not shippable framework
code.

## config.py — everything from the environment

```python
import os

APP_PATH   = os.environ.get("APP_PATH", "")     # set via env; no default path
APP_ARGS   = os.environ.get("APP_ARGS", "")
APP_TITLE  = os.environ.get("APP_TITLE", "")
LAUNCH_TO  = int(os.environ.get("LAUNCH_TIMEOUT", "15"))
ACTION_TO  = int(os.environ.get("ACTION_TIMEOUT", "10"))
ARTIFACTS  = os.path.join(os.path.dirname(__file__), "artifacts")
```

## pages/base_page.py — locators, waits, actions, artifacts

```python
from __future__ import annotations

import os
import time
from pywinauto import Desktop
from config import ACTION_TO, ARTIFACTS


class BasePage:
    def __init__(self, window):
        self.window = window

    # --- locators (priority order) ---
    def by_id(self, auto_id, **kw):
        """AutomationId — most stable; first choice."""
        return self.window.child_window(auto_id=auto_id, **kw)

    def by_name(self, name, **kw):
        """Visible text / accessible name."""
        return self.window.child_window(title=name, **kw)

    def by_class(self, cls, index=0, **kw):
        """Class + index — fragile; last resort."""
        return self.window.child_window(class_name=cls, found_index=index, **kw)

    # --- waits (never sleep) ---
    def wait_visible(self, spec, timeout=ACTION_TO):
        spec.wait("visible", timeout=timeout)
        return spec

    def wait_gone(self, spec, timeout=ACTION_TO):
        spec.wait_not("visible", timeout=timeout)
        return spec

    def wait_window(self, title, timeout=ACTION_TO):
        dlg = Desktop(backend="uia").window(title=title)
        dlg.wait("visible", timeout=timeout)
        return dlg

    def wait_until(self, predicate, timeout=ACTION_TO, interval=0.3):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if predicate():
                    return True
            except Exception:
                pass
            time.sleep(interval)
        raise TimeoutError("condition not met within %ss" % timeout)

    # --- actions ---
    def click(self, spec):
        self.wait_visible(spec)
        spec.click_input()

    def type_text(self, spec, text):
        self.wait_visible(spec)
        ctrl = spec.wrapper_object()
        try:
            ctrl.set_edit_text(text)
        except Exception as exc:
            # Qt 5.x etc.: UIA ValuePattern may be incomplete -> keyboard fallback
            import sys
            import pywinauto.keyboard as kb
            print("[windows-desktop-e2e] set_edit_text failed (%s); "
                  "using keyboard fallback" % exc, file=sys.stderr)
            ctrl.click_input()
            kb.send_keys("^a")
            kb.send_keys(text, with_spaces=True)

    def get_text(self, spec):
        ctrl = spec.wrapper_object()
        for attr in ("window_text", "get_value"):
            try:
                val = getattr(ctrl, attr)()
                if val:
                    return val
            except Exception:
                pass
        return ""

    # --- artifacts ---
    def screenshot(self, name):
        os.makedirs(ARTIFACTS, exist_ok=True)
        path = os.path.join(ARTIFACTS, "%s.png" % name)
        self.window.capture_as_image().save(path)
        return path
```

## pages/login_page.py — a concrete page object

```python
from __future__ import annotations

from pages.base_page import BasePage


class LoginPage(BasePage):
    @property
    def username(self):
        return self.by_id("usernameInput")

    @property
    def password(self):
        return self.by_id("passwordInput")

    @property
    def btn_login(self):
        return self.by_id("btnLogin")

    @property
    def error_label(self):
        return self.by_id("lblError")

    def login(self, user, pwd):
        self.type_text(self.username, user)
        self.type_text(self.password, pwd)
        self.click(self.btn_login)

    def login_ok(self, user, pwd, main_title="Main Window"):
        self.login(user, pwd)
        return self.wait_window(main_title)

    def login_fail(self, user, pwd):
        self.login(user, pwd)
        self.wait_visible(self.error_label)
        return self.get_text(self.error_label)
```

## pytest.ini

```ini
[pytest]
testpaths = tests
markers =
    smoke: fast smoke tests for critical paths
    flaky: known-unstable tests
addopts = -v --tb=short --html=artifacts/report.html --self-contained-html
timeout = 60
timeout_method = thread
```

## conftest.py — Tier 1 fixture (filesystem isolation, default)

Prefer this over a bare launch: it redirects per-user storage into pytest's
`tmp_path` at zero extra cost, launches via `subprocess.Popen` so a custom env
can be passed, and connects pywinauto by PID.

```python
from __future__ import annotations

import os
import shlex
import subprocess
import pytest
from pywinauto import Application
from config import APP_PATH, APP_ARGS, APP_TITLE, LAUNCH_TO, ARTIFACTS


@pytest.fixture(scope="function")
def app(request, tmp_path):
    """Fresh process + isolated user-data dirs per test."""
    if not APP_PATH:
        pytest.exit("APP_PATH not set", returncode=1)
    if not APP_TITLE:
        pytest.exit("APP_TITLE not set", returncode=1)

    env = os.environ.copy()
    env["QT_ACCESSIBILITY"] = "1"                      # harmless on non-Qt apps
    env["APPDATA"]      = str(tmp_path / "AppData" / "Roaming")
    env["LOCALAPPDATA"] = str(tmp_path / "AppData" / "Local")
    env["TEMP"] = env["TMP"] = str(tmp_path / "Temp")
    for p in (env["APPDATA"], env["LOCALAPPDATA"], env["TEMP"]):
        os.makedirs(p, exist_ok=True)

    # shlex.split handles quoted args with spaces; str.split() would not.
    proc = subprocess.Popen([APP_PATH] + shlex.split(APP_ARGS), env=env)
    pw = Application(backend="uia").connect(process=proc.pid, timeout=LAUNCH_TO)
    win = pw.window(title=APP_TITLE)
    win.wait("visible", timeout=LAUNCH_TO)
    yield win

    if getattr(getattr(request.node, "rep_call", None), "failed", False):
        os.makedirs(ARTIFACTS, exist_ok=True)
        try:
            win.capture_as_image().save(
                os.path.join(ARTIFACTS, "FAIL_%s.png" % request.node.name))
        except Exception:
            pass
    try:
        win.close()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    # tmp_path is cleaned up by pytest automatically.


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    setattr(item, "rep_%s" % outcome.get_result().when, outcome.get_result())
```

## Tier 2 — Job Object (process-lifetime containment)

Kills the app when the returned handle is released and blocks escaping child
processes. Not a filesystem/network sandbox. Stdlib `ctypes` only.

```python
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt


def restrict_process(pid):
    """Attach `pid` to a Job Object that is killed when the handle GCs."""
    JOB_LIMIT_KILL_ON_CLOSE = 0x00002000
    PROC_SET_QUOTA_AND_TERMINATE = 0x0101  # SET_QUOTA(0x0100) | TERMINATE(0x0001)
    k32 = ctypes.windll.kernel32

    job = k32.CreateJobObjectW(None, None)
    hproc = k32.OpenProcess(PROC_SET_QUOTA_AND_TERMINATE, False, pid)

    class BasicLimit(ctypes.Structure):
        # LimitFlags sits at offset +16 — get the field order right or it no-ops.
        _fields_ = [
            ("PerProcessUserTimeLimit", wt.LARGE_INTEGER),
            ("PerJobUserTimeLimit",     wt.LARGE_INTEGER),
            ("LimitFlags",              wt.DWORD),
            ("MinimumWorkingSetSize",   ctypes.c_size_t),
            ("MaximumWorkingSetSize",   ctypes.c_size_t),
            ("ActiveProcessLimit",      wt.DWORD),
            ("Affinity",                ctypes.c_size_t),
            ("PriorityClass",           wt.DWORD),
            ("SchedulingClass",         wt.DWORD),
        ]

    info = BasicLimit()
    info.LimitFlags = JOB_LIMIT_KILL_ON_CLOSE
    if not k32.SetInformationJobObject(job, 2, ctypes.byref(info), ctypes.sizeof(info)):
        raise ctypes.WinError()
    k32.AssignProcessToJobObject(job, hproc)
    k32.CloseHandle(hproc)
    return job  # raw kernel HANDLE (int): Python's GC does NOT close it,
    # so KILL_ON_JOB_CLOSE fires when this test process exits — or sooner
    # if teardown calls k32.CloseHandle(job) explicitly (recommended).


# after proc = subprocess.Popen(...):  job = restrict_process(proc.pid)
# teardown: k32.CloseHandle(job)   # closing the job kills the whole tree
```

## Tier 3 — Windows Sandbox (clean OS image per run)

`e2e-sandbox.wsb` maps the app read-only and the test suite read-write, then a
logon command installs Python and runs pytest inside the sandbox. Artifacts
map back to the host.

```xml
<Configuration>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>C:\path\to\build\Release</HostFolder>
      <SandboxFolder>C:\app</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
    <MappedFolder>
      <HostFolder>C:\path\to\e2e_test</HostFolder>
      <SandboxFolder>C:\e2e_test</SandboxFolder>
      <ReadOnly>false</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>powershell -Command "
      winget install --id Python.Python.3.11 --silent --accept-package-agreements;
      $env:PATH += ';' + $env:LOCALAPPDATA + '\Programs\Python\Python311\Scripts';
      cd C:\e2e_test;
      pip install -r requirements.txt;
      pytest tests\ -v
    "</Command>
  </LogonCommand>
</Configuration>
```

Launch: `WindowsSandbox.exe e2e-sandbox.wsb`. Requires Windows Pro/Enterprise
with virtualization enabled; pywinauto and the app both run inside the sandbox.

### Tier comparison

| Tier | Isolation   | Cost   | On CI | Use when                          |
|------|-------------|--------|-------|-----------------------------------|
| 1    | Filesystem  | Zero   | Always| default for every test            |
| 2    | Process tree| Low    | Always| prevent child-process escape      |
| 3    | Full OS     | Medium | Pro/Ent image | nightly clean-room runs   |

Also reap orphans in `conftest.py` (the `thread` timeout method cannot kill Qt
subprocesses on Windows):

```python
import atexit, psutil
atexit.register(lambda: [p.kill() for p in psutil.Process().children(recursive=True)])
```

## Opt-in per-step trace (flake repro only)

Off by default. Screenshots + a JSONL step log, ~50-200 ms per action and one
PNG per step — do **not** enable on the default matrix.

```bash
E2E_TRACE=1 pytest tests/test_login.py -v
# Include typed text ONLY on non-sensitive flows — never on credential/PII tests:
E2E_TRACE=1 E2E_TRACE_INCLUDE_TEXT=1 pytest ...
```

Typed text is `<redacted>` unless `E2E_TRACE_INCLUDE_TEXT=1`. Clear the artifact
dir before reruns and use per-worker dirs under xdist; raw pywinauto calls made
outside `BasePage` are not traced.

## Qt snippets

```cpp
// Give a Qt widget a stable id: objectName + accessibleName (UIA Name).
void setTestId(QWidget* w, const char* id) {
    w->setObjectName(id);
    w->setAccessibleName(id);
}
// setTestId(ui->usernameEdit, "usernameInput"); etc. Centralize ids in a header.
```

```python
from pywinauto import Desktop

def select_combo_item(page, combo_spec, item_text):
    """A Qt combo dropdown is a separate top-level window."""
    page.click(combo_spec)
    # class name varies by Qt version — confirm with Accessibility Insights.
    popup = Desktop(backend="uia").window(class_name_re=r"Qt\d+QWindowIcon")
    popup.wait("visible", timeout=5)
    popup.child_window(title=item_text).click_input()

# QMessageBox / QDialog are also separate top-level windows:
#   dlg = page.wait_window("Confirm"); dlg.child_window(title="OK").click_input()
# QTableWidget cell access:
#   table = page.by_id("tblUsers").wrapper_object(); table.cell(row=0, column=1)
```

## Screenshot fallback (UIA-unreachable controls)

```python
from __future__ import annotations

import numpy as np
import pyautogui
import cv2
from PIL import Image


def find_on_screen(template_path, confidence=0.85):
    """Return the center (x, y) of the best template match, or None."""
    screen = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)
    template = cv2.cvtColor(np.array(Image.open(template_path)), cv2.COLOR_RGB2BGR)
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(result)
    if score >= confidence:
        h, w = template.shape[:2]
        return loc[0] + w // 2, loc[1] + h // 2
    return None


def click_on_screen(template_path, confidence=0.85):
    pos = find_on_screen(template_path, confidence)
    if pos is None:
        raise RuntimeError("image not found on screen: %s" % template_path)
    pyautogui.click(*pos)
```

Diagnosis-only visualizer (calibrating `confidence`; never call from tests):

```python
def debug_match(template_path, out="artifacts/match_debug.png", confidence=0.85):
    import os
    import numpy as np, cv2, pyautogui
    screen = np.array(pyautogui.screenshot())[:, :, ::-1].copy()
    tpl = cv2.imread(template_path)
    if tpl is None:
        raise RuntimeError("template unreadable: %s" % template_path)
    res = cv2.matchTemplate(screen, tpl, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(res)
    h, w = tpl.shape[:2]
    color = (0, 255, 0) if score >= confidence else (0, 0, 255)
    cv2.rectangle(screen, loc, (loc[0] + w, loc[1] + h), color, 2)
    cv2.putText(screen, "score=%.3f thr=%s" % (score, confidence),
                (loc[0], max(20, loc[1] - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    cv2.imwrite(out, screen)
    return score
```

Screenshot matching breaks on DPI/theme changes and occlusion — keep it a
last resort, and honor the same-scale + CI-pin + record-the-scale rules.

## CI workflow (windows-latest)

```yaml
name: Desktop E2E
on: [push, pull_request]

jobs:
  e2e:
    runs-on: windows-latest   # real GUI; no virtual display needed
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install deps
        run: pip install pywinauto pytest pytest-html Pillow pytest-timeout
      - name: Build app
        run: cmake --build build --config Release   # adjust to your build system
      - name: Run E2E
        env:
          APP_PATH: ${{ github.workspace }}\build\Release\MyApp.exe
          APP_TITLE: "My Application"
          QT_ACCESSIBILITY: "1"
          CI: "true"
        run: pytest tests/ --html=artifacts/report.html --self-contained-html --junitxml=artifacts/results.xml -v
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: e2e-artifacts
          path: artifacts/
          retention-days: 14
```
