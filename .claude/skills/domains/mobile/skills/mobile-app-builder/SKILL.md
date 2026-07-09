---
name: mobile-app-builder
description: Mobile application development discipline covering iOS native (Swift /
  SwiftUI), Android native (Kotlin / Jetpack Compose), React Native, and Flutter
  cross-platform approaches. Covers app architecture (MVVM, MVI, Clean, TCA),
  state management per platform, navigation and deep-link semantics, offline-first
  local-DB selection and sync conflict resolution, push and local notification
  compliance (APNs / FCM), accessibility (VoiceOver, TalkBack, WCAG 2.2 AA mobile),
  and App Store / Play Console store compliance including privacy manifests. Use when
  designing or reviewing any mobile feature, architecture decision, platform selection,
  or store-submission readiness. Pair with security-and-auth for token storage and
  biometric auth flows.
owner: Priya Menon (Mobile App Builder, domain persona)
tier: domain:mobile
scope_tags: [mobile, ios, android, react-native, flutter, mobile-architecture, offline-first]
# --- native path activation (PLAN-135 W3 K8; K1 mechanism) ---
paths: ["**/*.swift", "**/Package.swift"]
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-mobile-app-builder.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
  - source: affaan-m/ecc/skills/android-clean-architecture@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: mobile
priority: 8
risk_class: medium
stack: [swift, kotlin, react-native]
context_budget_tokens: 600
inactive_but_retained: true
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: false, priority: 10}
  generic: {active: false, priority: 10}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)foundation.?models|apple.?intelligence"}
source: affaan-m/ecc@81af4076 skills/android-clean-architecture/
license: MIT
---

# Mobile App Builder

## Cardinal Rule

**Platform behavior is a contract, not a suggestion.** Platform-specific memory
pressure, background execution limits, and review policy rules are not edge cases
— they are the invariants the entire runtime assumes. Every architecture decision
must be defensible against App Store Review and Play Console policies before any
line of implementation is written.

## Fail-Fast Rule

Stop and surface a structured error when:

- A proposed token or credential storage location is not the platform keychain or
  Keystore (see Cross-References: security-and-auth).
- A navigation change breaks the back-stack contract, universal-link routing, or
  accessibility traversal order.
- An offline-first sync operation has no conflict-resolution strategy defined.
- A notification payload exceeds the platform limit (APNs: 4 KB; FCM: 4 KB data,
  up to 4 KB notification) or lacks the required permission-request trigger.
- A store-submission target uses a deprecated API or missing privacy-manifest
  declaration.
- A Claude integration via Apple Foundation Models uses `.apiKey` auth in a
  release configuration (see Apple Foundation Models: three mandates).

Never silently default, guess, or smooth over these conditions.

## When to Apply

Load this skill when:

- Selecting or revisiting the native vs. cross-platform platform strategy.
- Designing or reviewing app architecture, module boundaries, or state-management
  approach.
- Implementing navigation, deep links, universal links, or app links.
- Adding or modifying offline persistence, sync, or conflict resolution.
- Integrating push notifications (APNs / FCM) or local notification scheduling.
- Reviewing accessibility compliance (VoiceOver, TalkBack, dynamic type, touch
  targets).
- Preparing a build for App Store or Play Console submission.
- Adding biometric authentication or platform keychain/Keystore integration
  (always pair with `core/security-and-auth`).
- Integrating Claude through Apple's Foundation Models framework
  (`ClaudeForFoundationModels`), or routing between the on-device model and
  Claude.

## Platform Strategy

### Selection matrix

| Criterion | Native iOS + Android | React Native | Flutter |
|---|---|---|---|
| Team skill fit | iOS (Swift) / Android (Kotlin) specialists | TypeScript / JavaScript teams | Dart-capable or greenfield |
| Platform fidelity | Highest — full API surface, no bridge | High with native modules; bridge overhead | High; own rendering engine, not system widgets |
| Performance ceiling | Best (Metal, Vulkan direct) | Good; JS bridge latency on high-frequency events | Good; Impeller/Skia rendering; no JS bridge |
| Time-to-market (both platforms) | Slowest (two codebases) | Faster; ~60-80% code share realistic | Fastest; ~70-90% code share realistic |
| Third-party SDK availability | All SDKs have native variants | Most SDKs; gaps require native modules | Growing; some SDKs absent or community-only |
| Maintenance burden | Two separate release trains | One JS layer + two native shells | One Dart layer + two shells; Dart FFI for native |
| Store compliance risk | Lowest; no interpretation layer | Low; React Native well-precedented | Low; Flutter well-precedented |

**Decision rule:** choose native when the feature set requires deep platform API
access (ARKit, Core NFC, on-device ML, Bluetooth LE central mode) or when the
existing team has platform specialization. Choose React Native when a JS/TS web
team is the primary mobile team and third-party SDK coverage is sufficient. Choose
Flutter when both platforms are greenfield, delivery velocity is the constraint, and
Dart adoption is feasible.

**Never choose a framework to avoid learning platform conventions.** Platform
conventions must be understood regardless of framework — they define the contract
that governs review and runtime behavior.

## Apple Foundation Models (Claude integration)

> Beta surface: targets the server-side language model API introduced in the
> OS 27 betas (iOS / iPadOS / macOS / visionOS / watchOS 27, Xcode 27). APIs
> may change before GA.

`ClaudeForFoundationModels` is Anthropic's Swift package
(`https://github.com/anthropics/ClaudeForFoundationModels.git`, SPM) that
conforms Claude to Apple's `LanguageModel` protocol. The same
`LanguageModelSession` API that drives Apple's on-device model drives Claude —
`respond(to:)`, streaming via `streamResponse(to:)`, guided generation, and
tool calling work unchanged; you switch providers by swapping the `model:`
argument. Requests go directly from the app to the Claude API (Apple is not in
the request path) and are billed to the adopter's Anthropic account at standard
API pricing.

```swift
// Package.swift
.package(url: "https://github.com/anthropics/ClaudeForFoundationModels.git", from: "0.1.0")
```

```swift
import FoundationModels
import ClaudeForFoundationModels

let claude = ClaudeLanguageModel(name: .sonnet4_6, auth: auth)
let session = LanguageModelSession(model: claude)
let response = try await session.respond(to: prompt)
```

### On-device <-> Claude routing doctrine

Same tiering logic as the CEO routing table: route every request to the
cheapest tier that is capable, escalate only on demonstrated capability demand.

| Tier | Route here when | Cost profile |
|---|---|---|
| Apple on-device model (`SystemLanguageModel`) | Lightweight tasks, privacy-sensitive content, offline paths | Free, private, offline-capable; sized for lightweight tasks |
| Claude (`ClaudeLanguageModel`) | Larger context, frontier reasoning, server-side tools (web search, code execution via `serverTools:`) | Billed per request to the adopter's account; network required |

- Routing is the `model:` argument — both tiers share `LanguageModelSession`,
  so there are no dual code paths to maintain.
- Escalation is a product decision the app makes per session; make it explicit
  in code (a named routing function), never implicit in scattered call sites.
- Degrade gracefully downward: catch `LanguageModelError.rateLimited` (or
  timeout) from Claude and fall back to `SystemLanguageModel` for that turn,
  queue the request, or surface a retry affordance.

### Structured output (`@Generable`)

Annotate a type with `@Generable` (with `@Guide` per field) and request it with
`generating:` — the package maps it onto Claude structured outputs. If the
chosen model's declared capabilities do not include structured output, the
package throws `LanguageModelError.unsupportedGenerationGuide` rather than
silently degrading — surface it, never swallow it.

### Three mandates (fail-fast — do not ship without all three)

1. **`.proxied(headers:)` is the ONLY production auth.** `.apiKey` is
   development-only: a key bundled into a shipping binary is extractable, and
   anyone who extracts it can make requests billed to the adopter's account.
   Production routes through the adopter's own backend via
   `auth: .proxied(headers:)` plus `baseURL:` — the relay attaches the Claude
   credential (`x-api-key`) server-side, the app ships no key, and the supplied
   headers let the proxy authorize the caller. A release build with `.apiKey`
   is a Fail-Fast condition (see Fail-Fast Rule).
2. **`fixedEffort:` for `.xhigh` / `.max`.** The framework's per-request
   reasoning hints stop at high. `fixedEffort:` pins a Claude effort level for
   every request, takes precedence over the framework's hints, and is the only
   way to request `.xhigh` or `.max`. The level must be one the model's
   declared capabilities accept; the API defaults to high when no effort is
   sent.
3. **Capability declaration for unknown model IDs.** Compiled-in `ClaudeModel`
   constants (e.g. `.opus4_8` = `claude-opus-4-8`) carry each model's
   capabilities — sampling parameters, effort levels, adaptive thinking,
   structured output, image input — and the package uses them to decide which
   request fields to send, because sending a field a model rejects is a hard
   error. For an ID that is not compiled in, declare what it accepts
   explicitly via `ClaudeModel(id:capabilities:)`; there is deliberately no
   shorthand that guesses. This is the framework-side mirror of ADR-149's
   model-id allowlist doctrine: never assume what an unverified model ID
   supports.

## App Architecture

### Architecture pattern selection

| Pattern | When it wins | When to avoid |
|---|---|---|
| MVVM (iOS: SwiftUI/Combine; Android: ViewModel/StateFlow) | Declarative UI, clear View/ViewModel boundary, reactive bindings | Deep side-effect chains where unidirectional flow is essential |
| MVI (Model-View-Intent) | Complex state with explicit intent dispatch; Android Compose is well-suited | Simple screens — ceremony overhead is not justified |
| Clean Architecture (Use Cases + Repositories) | Large codebases, testability priority, CI gate coverage requirements | Small apps; over-engineers the data layer unnecessarily |
| TCA (The Composable Architecture — iOS/Swift) | Pure unidirectional state machine; composable feature trees; SwiftUI teams already familiar | Non-Swift targets; Kotlin/RN/Flutter teams lack first-class TCA equivalents |

### Module boundaries

- **Feature modules** are independently compilable. Circular dependencies between
  feature modules are a build error, not a warning.
- **Core modules** (networking, persistence, analytics, auth) have no dependency on
  any feature module.
- **Platform modules** (camera, biometrics, push) expose a protocol/interface
  boundary to feature modules; no direct SDK import from feature code.
- No UI code in domain or data layers. Domain layer has zero UIKit / SwiftUI /
  Compose import.

### Testability

- ViewModels / Presenters are plain objects with no platform import.
- Repository layer takes protocol/interface arguments; real implementations are
  injected at the composition root, stubs at test time.
- Snapshot tests (iOS: swift-snapshot-testing; Android: Paparazzi) cover each
  distinct UI state, not every permutation.

## Clean Architecture on Android / Kotlin Multiplatform

The "Clean Architecture" row in the pattern table and the module-boundary
doctrine above become concrete on Android — and on Kotlin Multiplatform (KMP),
where the domain and data layers are shared Kotlin across Android and iOS — as a
fixed layer stack governed by a single one-directional dependency rule. Reach for
this realization when the codebase is large enough that testability and CI gate
coverage justify the data-layer ceremony; consult the pattern table's "when to
avoid" column before adopting it on a small app.

### Layer stack

| Module | Holds | Depends on |
|---|---|---|
| `app` | Entry point, DI wiring, `Application` / composition root | everything below |
| `presentation` | Screens, ViewModels, UI models, navigation | `domain`, `design-system`, `core` |
| `domain` | UseCases, domain models, repository **interfaces** — pure Kotlin | `core` only (ideally nothing) |
| `data` | Repository **implementations**, DataSources, DB, network | `domain`, `core` |
| `core` | Shared error types, base utilities | nothing |
| `design-system` | Reusable Compose components, theme, typography | `core` |
| `feature/*` | Optional per-feature slices for large apps | `domain`, `design-system`, `core` |

The one-directional rule (dependencies point inward, never out):

```
app          -> presentation, domain, data, core
presentation -> domain, design-system, core
data         -> domain, core
domain       -> core   (or nothing)
core         -> (nothing)
```

**The load-bearing invariant: `domain` is pure Kotlin.** Zero Android framework
import, zero `data` or `presentation` import. This is the concrete form of the
"no UI code in domain or data layers" rule above. A framework import in `domain`
is a Fail-Fast condition, not a style preference — it silently couples business
rules to a platform and breaks KMP sharing.

### Domain layer

- **UseCase = one business operation**, exposed through a single
  `operator fun invoke` so call sites read as `getItemsByCategory(category)`.
  Use `suspend` for one-shot work and return `Flow<T>` for reactive streams —
  do not fold both concerns into one UseCase.
- **Domain models are plain data classes** with no persistence or serialization
  annotations. An `@Entity`, `@Serializable`, or DTO type in the domain layer is
  a leak of an outer concern inward.
- **Repository interfaces live in `domain`; implementations live in `data`.**
  This is dependency inversion: the business layer declares what it needs, the
  data layer supplies it, and `domain` never names a concrete database or client.

```kotlin
// domain/
class GetItemsByCategory(private val repo: ItemRepository) {
    suspend operator fun invoke(category: String): Result<List<Item>> =
        repo.getItemsByCategory(category)
}

interface ItemRepository {                     // declared here...
    suspend fun getItemsByCategory(category: String): Result<List<Item>>
    fun observeItems(): Flow<List<Item>>
}
```

### Data layer

- **Repository implementations coordinate DataSources** — a local source and a
  remote source, each with one job — rather than talking to the framework
  directly. A repository that accretes query logic, caching policy, and mapping
  all at once is the "fat repository" anti-pattern; split it into focused
  DataSources.
- **Map at the boundary.** DTOs (network) and entities (DB) convert to and from
  domain models via small mapper functions — idiomatically Kotlin extension
  functions kept beside the data models. A DTO or DB entity must never cross into
  `domain` or the UI; the mapper is the seam that keeps the invariant true.
- **Storage/network realization for the offline-first strategy:** Room on
  Android, SQLDelight for KMP, Ktor for the network client. Clean layering is
  what lets you swap those without touching `domain`.

### Composition root and error boundary

- **Dependency injection is wired only in `app`** — the one module that sees
  every layer. Koin is the KMP-friendly choice; Hilt is Android-only. This is the
  same "inject real implementations at the composition root, stub at test time"
  discipline the Testability section states, made concrete: because `domain`
  depends on interfaces, tests substitute fakes with no framework present.
- **Errors cross the repository boundary as values, not exceptions.** Return
  `Result<T>` or a sealed `AppError` / `Try` type from the repository; the
  ViewModel maps that value to UI state. An exception thrown from `data` and
  caught (or missed) in a Composable is an uncontrolled boundary — model the
  failure explicitly so every call site is forced to handle it.

### Layering anti-patterns (build-time and review-time)

- Android framework class imported in `domain` — breaks purity and KMP sharing.
- DB entity or DTO exposed to the UI — always map to a domain model first.
- Business logic living in a ViewModel — extract it to a UseCase so it is
  testable without the UI.
- `GlobalScope` or unstructured coroutines — use `viewModelScope` and structured
  concurrency (see State Management).
- Circular module dependency — if `A` depends on `B`, `B` must not depend on
  `A`; this is a build error, matching the feature-module rule in Module
  boundaries above.

## State Management

State management is platform-specific. Cross-platform frameworks add their own layer.

**iOS — SwiftUI + Combine:**
- `@StateObject` owns lifecycle; `@ObservedObject` observes. Mixing them causes
  phantom resets.
- `@Published` properties trigger re-render; expensive computations belong in
  `receive(on:)` pipelines, not body closures.
- Global shared state lives in `@EnvironmentObject`; over-use creates invisible
  coupling — prefer scoped `@StateObject` trees.

**Android — Jetpack Compose + Kotlin Flow:**
- `ViewModel` survives configuration changes; `rememberSaveable` survives process
  death for lightweight UI state only.
- `collectAsStateWithLifecycle` (not `collectAsState`) prevents background
  collection and battery drain.
- `StateFlow` for UI state; `SharedFlow` for events (navigation, one-shot errors).
  Never emit UI state through `SharedFlow` — it has no replay guarantee on
  recomposition.

**React Native — Redux / MobX / Zustand:**
- Zustand preferred for small-to-medium apps; Redux + Redux Toolkit for
  complex async flows.
- All async side effects belong in middleware (Redux Thunk / Saga) or Zustand
  actions; never inside component effects.
- Component re-render surface must be minimized via selector memoization
  (`useSelector`, `useMemo`).

**Flutter — Riverpod / Bloc:**
- Riverpod `AsyncNotifier` for async data; `Notifier` for synchronous state.
- Bloc pattern for complex event-state machines; avoid it for simple CRUD screens.
- `StateProvider` in Riverpod is a code smell for complex state — migrate to
  `Notifier` before the first code review.

## Navigation Discipline

- **Route as URL.** Every screen has a deterministic path segment. Deep links,
  universal links (iOS), and app links (Android) must resolve to the same code
  path as in-app navigation — no dual routing tables.
- **Back-stack semantics are explicit.** `popBackStack`, `replaceTop`, and
  `clearAndReplace` have distinct semantics; the wrong choice corrupts the user's
  navigation history.
- **Universal links (iOS):** `apple-app-site-association` file must be hosted at
  `https://<domain>/.well-known/apple-app-site-association` with correct
  `applinks` entries. AASA changes propagate with up to 24-hour CDN delay.
- **App links (Android):** Digital Asset Links JSON at
  `https://<domain>/.well-known/assetlinks.json`. Verification must pass before
  release; test via `adb shell pm get-app-links`.
- **Gesture handling:** swipe-back (iOS edge-pan) and predictive-back (Android 13+)
  must not trigger unsaved-data loss without a confirmation dialog. Modal sheets
  must handle the dismiss gesture identically to the dismiss button.

## Offline-First Patterns

### Local DB selection

| Database | iOS fit | Android fit | RN fit | Flutter fit | When to choose |
|---|---|---|---|---|---|
| SQLite (raw) | Core Data wrapper | Room wrapper | `expo-sqlite` / `react-native-quick-sqlite` | `sqflite` | Full SQL control; complex queries |
| Core Data | Native | — | — | — | iOS-only; tight SwiftUI integration; migration tooling |
| Room | — | Native | — | — | Android-only; Kotlin-first; Flow integration |
| Realm | Native SDK | Native SDK | `realm-js` | `realm-dart` | Reactive queries; sync with MongoDB Atlas |
| WatermelonDB | — | — | React Native | — | RN-specific; lazy loading; Observable architecture |
| Drift (formerly Moor) | — | — | — | Native | Flutter-native; type-safe SQL with code generation |

### Sync conflict resolution

Conflict resolution strategy must be documented in the architecture before
implementation. Accepted strategies:

- **Last-write-wins (LWW):** simplest; requires server-authoritative timestamps;
  correct only when concurrent writes to the same field are rare and low-stakes.
- **Server-wins:** client changes are local optimistic UI only; server state
  replaces on sync. Correct for externally driven data (e.g. order status).
- **CRDT (Conflict-free Replicated Data Types):** mathematically merge-safe;
  appropriate for collaborative or append-only structures (notes, checklists).
- **Three-way merge (ancestor + local + remote):** requires ancestor record storage;
  appropriate for complex entities where partial merges are valid.

**No silent discard.** If a conflict is resolved in a way that discards user
input, the resolution must be surfaced to the user.

### Optimistic UI

Minimum structure for an optimistic mutation (pseudocode — applies to all platforms):

```
function submitOptimistic(item):
    previousState = store.snapshot()
    store.applyOptimistic(item)           // local immediate update
    try:
        result = await api.post(item)
        store.commit(result)              // replace optimistic with confirmed
    catch SyncError as e:
        store.rollback(previousState)     // restore prior state
        retryQueue.enqueue(item, e)       // dead-letter; never silent drop
        ui.showConflictBanner(e)
```

Optimistic mutations must be paired with:

1. A rollback path on sync failure (restore previous local state).
2. A visual diff signal so the user can distinguish committed from optimistic state.
3. A retry queue with exponential backoff and dead-letter storage (not silent drop).

## Push + Local Notifications

### APNs (iOS)

- Register via `UNUserNotificationCenter.requestAuthorization` at a justified
  moment — not on first app launch. Prompt timing must be validated against
  provisioning profile entitlements.
- Payload limit: 4 KB total. Exceed it and the notification is silently dropped.
- Use `mutable-content: 1` for notification service extension processing only when
  needed (media attachments, decryption). The extension has 30 seconds.
- Silent push (`content-available: 1`, no alert/sound/badge) is rate-limited by
  iOS at discretion. Never rely on silent push for time-sensitive delivery.

### FCM (Android / cross-platform)

- Notification messages (display by FCM SDK) vs. data messages (handled by app):
  choose data messages for all custom handling; notification messages bypass
  `onMessageReceived` when the app is in background.
- `HIGH` vs. `NORMAL` priority: `HIGH` wakes the device from Doze; use only for
  user-facing alerts. Background data sync must use `NORMAL`.
- Android 13+ requires `POST_NOTIFICATIONS` permission; request at the appropriate
  user-action moment, not at app start.

### Delivery diagnostics

- Log device token registration, token refresh, and delivery receipt (FCM
  delivery receipt API / APNs feedback service) at the analytics plane.
- Silent-push budget exhaustion (iOS) and Doze-mode delivery latency (Android)
  must be documented in the system's SLA.

## Accessibility Compliance

- **VoiceOver (iOS) / TalkBack (Android):** every interactive element has a
  descriptive `accessibilityLabel` (iOS) / `contentDescription` (Android). Never
  expose implementation strings ("ic_btn_close_24") as accessibility labels.
- **Dynamic type (iOS) / font scale (Android):** layouts must not overflow or
  truncate at the system's largest accessibility font size. Test at 200% scale.
- **Touch target floor:** minimum 44 × 44 pt (iOS HIG) / 48 × 48 dp (Material
  Design). Elements below the floor must have a tap-area inset applied without
  changing visual size.
- **WCAG 2.2 AA mobile profile:**
  - Contrast ratio ≥ 4.5:1 for body text; ≥ 3:1 for large text (18pt regular /
    14pt bold) and UI components.
  - Focus indicators visible at ≥ 3:1 contrast against adjacent colors.
  - No information conveyed by color alone; use shape or label redundancy.
  - Motion: respect `prefers-reduced-motion` (iOS) / `ANIMATOR_DURATION_SCALE = 0`
    (Android) — provide non-animated state transitions.

## Store Compliance

### App Store (iOS)

- **Privacy manifest (PrivacyInfo.xcprivacy):** required for all third-party SDKs
  in the required reasons API list since 2024. Missing or incomplete manifests
  cause automated rejection.
- **Tracking permission (ATT):** `NSUserTrackingUsageDescription` required; present
  the `requestTrackingAuthorization` prompt only after a pre-permission dialog
  explaining value. Cross-app tracking without permission is a Review guideline 5.1.2
  violation.
- **Age rating:** accurately declare content; incorrect rating triggers removal.
- **Export compliance:** encryption usage requires annual self-classification or
  the `ITSAppUsesNonExemptEncryption = NO` plist key when only standard
  platform APIs (HTTPS, Keychain) are used.
- **Review guideline 4.2 (Minimum Functionality):** content-only apps without
  native functionality will be rejected.

### Play Console (Android)

- **Data safety section:** every data type collected or shared must be declared;
  inconsistency with actual behavior triggers enforcement action.
- **Target API level:** must target the current year's required API level within
  the grace period. Apps targeting older levels are hidden from new installations.
- **Background location:** requires `ACCESS_BACKGROUND_LOCATION` permission with a
  policy URL and a specific use-case justification in the declaration.
- **Exact alarms (Android 12+):** `USE_EXACT_ALARM` or `SCHEDULE_EXACT_ALARM`
  requires justification; calendar and reminder apps qualify; background sync
  does not.

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Blocking the main thread (UI thread) with I/O or CPU work | Causes ANR (Android) / watchdog kills (iOS); 5-second main-thread block is observable by App Store Review automated tools |
| Ignoring memory pressure signals (`applicationDidReceiveMemoryWarning` / `onTrimMemory`) | Image caches grow unbounded; app is killed by the OS in background; users blame "battery drain" |
| Storing credentials, tokens, or PII in `UserDefaults`, `SharedPreferences`, or unprotected files | Accessible to any other app on jailbroken / rooted devices; violates App Store guideline 5.1.1 |
| Shipping `.apiKey` Claude auth in a release binary (`ClaudeForFoundationModels`) | The key is extractable from the shipped binary; anyone who extracts it makes requests billed to the adopter's Anthropic account. `.proxied(headers:)` through the adopter's backend is the only production auth |
| No offline handling — assuming network is always available | Crashes or blank screens on airplane mode; fails Review on unreliable test networks; breaks accessibility (assistive tech users rely on cached content) |
| Requesting sensitive permissions (location, camera, notifications) at app launch with no context | Permission denial rate is highest at launch; iOS 14+ enforces notification permission timing heuristics |
| Using deprecated API without fallback | App is rejected or removed from store on next review cycle; no graceful runtime degradation |

## Cross-References

- `.claude/skills/core/security-and-auth/SKILL.md` — Keychain / Keystore token
  storage, biometric auth, OAuth / PKCE flows, certificate pinning.
- `.claude/skills/core/code-review-checklist/SKILL.md` — apply mobile-specific
  checklist items during PR review: thread safety, memory leaks, permission
  handling, test coverage floor.
- `.claude/skills/frontend/accessibility-and-wcag/SKILL.md` — WCAG 2.2 detailed
  compliance criteria and testing methodology applicable to web views embedded in
  mobile apps.
- `.claude/skills/core/llm-routing-and-finops/SKILL.md` — the CEO tiering table
  that the on-device <-> Claude routing doctrine mirrors (cheapest capable tier
  first, escalate on capability demand).

## ADR Anchors

- **ADR-058** (Brainstorm gate + two-pass adversarial review): mobile architecture
  and platform-strategy decisions are L3+ and require the brainstorm gate before
  plan execution. Two-pass adversarial review applies to any change touching the
  offline-sync contract, store compliance declarations, or notification permission
  surfaces.
- **ADR-149** (model-id allowlist): `ClaudeModel(id:capabilities:)` explicit
  capability declaration for model IDs not compiled into
  `ClaudeForFoundationModels` is the in-app mirror of the framework's allowlist
  doctrine — never guess what an unverified model ID accepts.

## Changelog

- **PLAN-153 Wave G (SP-037, 2026-07-09):** Android clean-architecture layering doctrine folded in (clean-room ADAPT; provenance in frontmatter/NOTICE).
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=00ff5c83ae52e269b5121ff86de4b1e1003f3d157998053e669bf06d773e128d
