# PROBE — DirectoryAdded blockability (PLAN-163 T3.1, HARD GATE CF-9)

- **Substrate:** Claude Code `2.1.220` (`/Users/joaocanhada/.local/share/claude/versions/2.1.220`, Mach-O arm64)
- **Date:** 2026-07-28 (S283/S284)
- **Method:** static extraction from the CC binary (zod schemas + hook dispatch) + live-fire with an isolated `DirectoryAdded` hook that (a) logs raw stdin and (b) emits `{"decision":"block"}` exit 0.
- **Child sessions used:** 5 (Run A `/add-dir` prompt; Run B launch `--add-dir`; Run C/C2 stream-json control-req; Run D live hook capture). Cap 6.
- **S283 hypothesis under test:** DirectoryAdded is POST-FACTO and the CF-9 observer fallback covers only writes.

## VERDICT (one line)
`diradd=notification-only; post-facto-window=reads+writes`

The `decision:block` field is **structurally ignored** for DirectoryAdded. The event cannot gate the directory addition — by the time the hook runs, permission/sandbox state already includes the directory. CF-9 must therefore NOT rely on DirectoryAdded to *block*; it can only *observe after the fact*, and the S283 finding (observer covers only writes) is the real exposure: reads to the added directory are already live before any observer reacts.

---

## Q(i) — Did the hook RECEIVE the event? YES. Live input shape captured.

Live-fire Run D fired `register_repo_root` via SDK control request against a strict subdir of a launch `--add-dir` root; the wired hook logged this raw stdin (from `logs/diradd.log`):

```json
{"session_id":"adf8384d-7c1d-4ae4-9d99-32b6e694ca3b",
 "transcript_path":".../diradd-probe/work/adf8384d-....jsonl",
 "cwd":".../diradd-probe/work",
 "prompt_id":"99bd22dd-a2be-4fff-acf9-3400870b55b6",
 "hook_event_name":"DirectoryAdded",
 "directory":".../diradd-probe/victim",
 "source":"register_repo_root"}
```

Binary zod schema (authoritative shape, `uuT`):
```
hook_event_name:"DirectoryAdded",
directory: string  // "Absolute path of the directory that was added."
source: enum("slash_command","register_repo_root")
   // "slash_command" for /add-dir, "register_repo_root" for the SDK control_request
```
Plus the common base (`session_id`, `transcript_path`, `cwd`, `prompt_id`). Confirmed live: the `source` field distinguishes the two add paths; there is **no** `source` value for launch-time `--add-dir` (see Q-iii).

## Q(ii) — Does `decision:block` have EFFECT? NO — notification-only. Proven live + static.

**Live (Run D):** hook returned `{"decision":"block","reason":"probe-block-DirectoryAdded"}` exit 0. The CLI's `control_response` was nonetheless:
```json
{"subtype":"success","request_id":"req-diradd-2",
 "response":{"directory":".../diradd-probe/victim"}}
```
and the session completed the follow-up turn normally (`result:"DONE", is_error:false`). The block was discarded; the directory stayed registered.

**Static root cause** — the DirectoryAdded executor reads ONLY `systemMessage`, never `decision`:
```js
async function a$t(e,t,r=xm){
  let n={...Kf(void 0),hook_event_name:"DirectoryAdded",directory:e,source:t},
      o=await vL({hookInput:n,matchQuery:t,timeoutMs:r}),
      i=o.map((s)=>s.systemMessage).filter((s)=>!!s);   // <-- only systemMessage harvested
  return{results:o,systemMessages:i}                     // <-- no blockingError, no decision read
}
```
Contrast with the blocking-capable executors (e.g. Elicitation `nMt`) which explicitly extract `blockingError` via `H$o(...)`. DirectoryAdded has no such path.

**Corroborating static facts:**
- Blocking-capable event set `NFy = {PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest, PermissionDenied}` — **DirectoryAdded is NOT a member.** (It is only in the fire-registry `MFy`.)
- CC's own schema description string for the event:
  > "Fires after /add-dir or the register_repo_root SDK control request registers a new working directory, **after the sandbox configuration has been refreshed — so sandboxed tools and permission state already see the new directory** (hook commands themselves run ...)"
- Slash-command call site `ORB` (`/add-dir` handler) ordering: `setToolPermissionContext(addDirectories)` → print "Added …" → `a$t(a,"slash_command").then(...)`. The permission-context mutation is **synchronous and complete before** the hook is dispatched, and the dispatch is a **fire-and-forget `.then()`** whose only follow-up is logging failed hooks and surfacing `systemMessage`s.

## Q(iii) — POST-FACTO window: what could the model do in victim despite block? reads+writes (full).

**Run B (launch `--add-dir victim`, authed, model haiku):** the model performed BOTH:
- READ `victim/sentinel.txt` → returned exact bytes `SENTINEL-CONTENT-XYZ-7439` (SUCCESS)
- WROTE `victim/probe-write.txt` = `WROTE-OK-9931` (SUCCESS, file present on disk after)
→ a directory added as a working root is fully read+write. There is no "read-only added directory" state.

**Ordering guarantees the window is unclosable:** because the permission/sandbox state is refreshed BEFORE the hook fires (schema description) and the addition is never reverted by the hook (Q-ii), every tool call issued after the add — reads AND writes — is already authorized. A DirectoryAdded hook can at best emit a `systemMessage` into the transcript AFTER the directory is live; it cannot retroactively deny the reads/writes that a same-turn agent could already have issued.

**Structural note on register_repo_root (Run C2):** `register_repo_root` is itself refused unless the target is a strict subdir of cwd or of a launch-time `--add-dir` root:
```
control_response error: "register_repo_root: <victim> is not a subdirectory of cwd
or of a launch-time --add-dir root"
```
So the SDK path cannot introduce a *new* outside tree — the only way an outside tree enters is launch `--add-dir` (Run B, **fires NO DirectoryAdded hook at all** — `logs/diradd.log` empty) or the interactive `/add-dir` slash command (fires the hook, but post-facto per above). Net: **no DirectoryAdded configuration can prevent access to an added directory.**

## Q(iv) — Is Notification wireable in the schema? YES (wireable) but also non-blocking.

- Present in registry set `MFy` (…,"Notification",…). Input schema:
  `{hook_event_name:"Notification", message:string, title?:string, notification_type:string}` (+ base fields).
- Executor is fire-and-forget: `await vL({hookInput:i,timeoutMs:t,matchQuery:o})` with the result discarded — no `decision`/`blockingError` consumed.
- Output schema for Notification permits only `{hookEventName:"Notification", additionalContext?:string}` — **no** block/deny variant (unlike `PermissionRequest` whose output carries `decision:{behavior:allow|deny}`).
- Live trigger not attempted (a real Notification condition — permission-needed / idle — is not cheap to force in `-p`; budget conserved). Static evidence is conclusive that Notification is wireable-but-notification-only.

---

## Raw evidence index (this probe)
- `logs/diradd.log` live capture reproduced under Q(i).
- Run B stdout: two SUCCESS results + on-disk `victim/probe-write.txt`.
- Run C2 control_response: register_repo_root subdir-constraint rejection.
- Run D control_response: `subtype:"success"` despite hook `decision:block`.
- Binary strings: `a$t` executor body; `NFy`/`MFy` sets; DirectoryAdded description string; `uuT`/Notification zod schemas.

## Implication for CF-9 (feeds T3.1 authoring)
1. Do NOT design CF-9 as a DirectoryAdded *blocker* — the field is inert. Any "block" wiring is a false sense of security.
2. The genuine control points that CAN deny directory-scoped access are the blocking events in `NFy` — specifically `PreToolUse` / `PermissionRequest` on the Read/Write/Bash tools, evaluated against the (already-updated) working-root set. CF-9 enforcement belongs there, not on DirectoryAdded.
3. DirectoryAdded remains useful as an *audit/observer* signal (source-attributed: slash_command vs register_repo_root). But per S283, an observer that reacts only to writes leaves the read window fully open — reads land before the observer can run. If CF-9 needs to gate reads of a newly-added tree, it must do so at PreToolUse on Read, keyed off the working-root membership, not at DirectoryAdded.
4. Launch-time `--add-dir` fires NO DirectoryAdded event, so an observer keyed on DirectoryAdded is blind to the most common outside-tree entry path entirely.
