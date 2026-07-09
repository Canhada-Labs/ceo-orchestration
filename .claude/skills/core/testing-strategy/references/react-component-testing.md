<!-- PLAN-153 Wave G clean-room ADAPT merge (rides SP-026 via /skill-review). NEW reference — NOT a verbatim extraction. Knowledge ported in our own voice; no upstream prose copied verbatim, no vendor names in body, upstream SKILL.md treated as untrusted data. Soak: parallel-shadow (OQ3=c). Edit only via a new SP-026 that bumps the parent testing-strategy SKILL.md version. -->
<!-- Provenance: .claude/skills/core/testing-strategy/references/react-component-testing.md — recorded in the parent SKILL.md `inspired_by:` frontmatter. -->

# React Component & Hook Testing

Behavior-focused testing for React components, custom hooks, and pages. This is
the frontend echo of the parent skill's core rule — *test observable behavior,
not implementation* — expressed in the vocabulary of React Testing Library
(RTL), a JSDOM runner (Vitest or Jest), and network-seam mocking (MSW).

> Stack note: the tool names here are JS/TS-specific. The *principles* —
> query by what a user can perceive, mock at the network seam, assert visible
> output and observable side effects — carry to any component framework.

## The one rule everything else follows

Test what the user sees and does; never reach for what the component holds.

A good component test:

- renders the component with the **same providers** it has in production;
- drives it through **accessible queries** (role, label) and a real interaction
  library, not synthetic clicks;
- asserts on **visible output** and **observable side effects** (a callback
  fired, a request left the app).

A bad component test inspects internal state, the props handed to a child, which
hooks ran, or the exact render count. All of those break on a refactor that a
user would never notice — the definition of a brittle test.

## Choosing a runner

| Runner | Reach for it when | Note |
|---|---|---|
| **Vitest** | Vite / modern ESM setups | Fast, native ESM, Jest-compatible API |
| **Jest** | Established repos, Next.js/CRA lineage | Still the default in many React codebases |
| **Playwright Component Testing** | You need a real browser engine | Use when JSDOM cannot render the feature |
| **Cypress Component Testing** | Real browser + Cypress already present | Alternative to Playwright CT |

Pick one lane. Running RTL-in-JSDOM and a real-browser component runner in the
same repo without a clear separation of what lives where produces two flaky
suites instead of one good one.

## Query priority — a ladder, top-down

RTL exposes queries in tiers. Start at the top and only descend when the tier
above genuinely cannot express the target:

1. **Accessible to everyone** — `getByRole`, `getByLabelText`,
   `getByPlaceholderText`, `getByText`, `getByDisplayValue`
2. **Semantic** — `getByAltText`, `getByTitle`
3. **Test-id escape hatch** — `getByTestId`

```tsx
// Preferred: the button as a user would find it
screen.getByRole("button", { name: /save/i });

// Acceptable for form fields
screen.getByLabelText("Email");

// Last resort — reaching for a test id usually means the markup lacks a
// role or an accessible name, which is itself a finding worth fixing.
screen.getByTestId("save-btn");
```

Query variants, and what each is *for*:

- `getBy*` — throws when there is no match. Use to assert presence.
- `queryBy*` — returns `null` on no match. Use to assert **absence**.
- `findBy*` — returns a Promise. Use for elements that appear after async work.

## Interactions — simulate a real user

Prefer a user-event library over dispatching single synthetic events: it fires
the full browser sequence (focus, keydown, input, keyup) a real user would
trigger, so the test exercises the same code paths as production.

```tsx
import userEvent from "@testing-library/user-event";

test("fires onSubmit with the typed email", async () => {
  const user = userEvent.setup();          // once per test; reuse `user`
  const onSubmit = vi.fn();
  render(<UserForm onSubmit={onSubmit} />);

  await user.type(screen.getByLabelText("Email"), "a@example.com");
  await user.click(screen.getByRole("button", { name: /save/i }));

  expect(onSubmit).toHaveBeenCalledWith({ email: "a@example.com" });
});
```

- Always `await` user-event calls — they are async.
- Call `setup()` once and reuse the returned handle.
- Reach for a raw synthetic-event dispatch only for the rare case a real
  interaction cannot reproduce.

## Async — matchers, never sleeps

```tsx
// Appears after async work
expect(await screen.findByText("Loaded")).toBeInTheDocument();

// A side effect completed
await waitFor(() => expect(saveSpy).toHaveBeenCalled());

// Something disappears
await waitForElementToBeRemoved(() => screen.queryByText("Loading"));
```

A hand-rolled `setTimeout` + assertion is a flake generator — it races the
component's real timing. Use the async matchers, which poll until the condition
holds or the timeout trips.

## Mock at the network seam (MSW)

Mock Service Worker intercepts at the HTTP layer, so the component, its hooks,
and its fetch library all run exactly as they do in production — only the wire
is faked. That is a far stronger test than stubbing a data-fetching module.

```ts
// test/setup.ts
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

export const server = setupServer(
  http.get("/api/users/:id", ({ params }) =>
    HttpResponse.json({ id: params.id, name: "Alice" }),
  ),
);

// Fail loudly on any request the test did not explicitly mock — a silent
// pass-through is worse than a red test.
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

Override one endpoint for the error-path test without disturbing the rest:

```tsx
test("renders the error state on 500", async () => {
  server.use(
    http.get("/api/users/:id", () => new HttpResponse(null, { status: 500 })),
  );
  render(<UserPage id="1" />);
  expect(await screen.findByText(/something went wrong/i)).toBeInTheDocument();
});
```

## Provider wrapping — define it once

Wrap the production providers in a single render helper so every test renders
the component in a realistic tree:

```tsx
// test-utils.tsx
export function renderWithProviders(ui: React.ReactElement, options?: RenderOptions) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }, // deterministic: no retry storms
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={lightTheme}>
        <MemoryRouter>{ui}</MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
    options,
  );
}
export * from "@testing-library/react";
```

Then import `renderWithProviders` (and `screen`) from `test-utils` everywhere.

## Custom hooks

```tsx
import { renderHook, act } from "@testing-library/react";

test("useCounter increments", () => {
  const { result } = renderHook(() => useCounter(0));
  act(() => result.current.increment());
  expect(result.current.count).toBe(1);
});
```

- Wrap state-changing calls in `act`.
- Test only through the hook's public return value — never its internals.
- For a hook that reads context, pass a `wrapper`. **Instantiate any client
  (e.g. a query client) once, outside the wrapper closure** — creating it inside
  the closure resets its cache on every render and produces intermittent
  failures.

## Accessibility assertions

Run an automated a11y check inside component tests for every interactive
component:

```tsx
import { axe, toHaveNoViolations } from "jest-axe"; // or vitest-axe
expect.extend(toHaveNoViolations);

test("UserCard has no a11y violations", async () => {
  const { container } = render(<UserCard user={mockUser} />);
  expect(await axe(container)).toHaveNoViolations();
});
```

This catches missing input labels, invalid ARIA, missing `alt` text, and
heading-order breaks. It does **not** catch visual contrast reliably — JSDOM has
no CSS engine, so contrast belongs in a real-browser run. For the full a11y
playbook see the sibling skills at
[`frontend/frontend-accessibility/SKILL.md`](../../../frontend/frontend-accessibility/SKILL.md)
and [`frontend/accessibility-and-wcag/SKILL.md`](../../../frontend/accessibility-and-wcag/SKILL.md).

## Snapshots — narrow by default

Rendered-output snapshots break on every styling change, get rubber-stamped in
review, and pin DOM structure (implementation) rather than behavior. Avoid them
for component output.

Acceptable snapshot uses are the *pure serialization* cases: a formatting
function whose output is a stable string, or a generated config file. For visual
regression on components, use real-browser screenshot diffs, not DOM strings.

## When to escalate past JSDOM

A JSDOM runner cannot render real layout (flexbox/grid, viewport queries), run
CSS transitions, exercise scroll/drag-drop/clipboard, or handle iframes,
popups, downloads, and cross-origin flows. When the behavior under test needs
any of those, move it to a real-browser runner. Decision boundary:

- a hook, a presentational component, a form with logic → **RTL in JSDOM**;
- a component whose layout matters or that touches a browser API JSDOM lacks →
  **Playwright / Cypress Component Testing**;
- a full flow across pages → **end-to-end** (see the parent skill's
  `references/e2e-multiprocess.md` for the multi-process analogue).

## Coverage targets

| Layer | Target |
|---|---|
| Pure utilities | ≥ 90% |
| Custom hooks | ≥ 85% |
| Presentational components | ≥ 80% — behavior, not lines |
| Container components | ≥ 70% — golden paths + error states |
| Pages | smoke test minimum; full flows covered end-to-end |

Wire the thresholds into the runner config (`vitest.config.ts` /
`jest.config.js`) so a coverage regression fails CI rather than living in a
dashboard nobody reads.

## RTL anti-patterns

| Anti-pattern | Why it is wrong |
|---|---|
| `container.querySelector(...)` | Bypasses accessible queries; passes where a real user would fail |
| Asserting on render count | Implementation detail, not behavior |
| `jest.mock("react", ...)` | Never mock React or framework hooks — refactor the component instead |
| Mocking child components by default | You then test isolation, not integration; mock only heavy-side-effect children |
| Ignoring `act(...)` warnings | They flag real bugs — state update after unmount, missing async wrapping |
| Shared mutable state across tests | Flakes the moment test order changes |
| A test that still passes after its `it.skip` twin is deleted | The assertion does not prove what you think |

## Related

- Parent skill: [`../SKILL.md`](../SKILL.md) — overall testing strategy and the
  behavior-over-implementation principle this reference specializes.
- Sibling: [`tdd-red-green-cycle.md`](./tdd-red-green-cycle.md) — the test-first
  loop these component tests slot into.
- Sibling: [`test-quality-and-mutation.md`](./test-quality-and-mutation.md) —
  verifying the tests themselves catch faults.
