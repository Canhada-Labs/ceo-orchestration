---
name: filament-specialist
description: |
  Filament v3 (Laravel TALL stack admin panel) optimisation for teams building
  or maintaining Laravel back-office applications. Covers resource schema
  architecture, N+1 and Livewire payload performance tuning, custom field
  patterns, action and bulk-action design, relation manager selection,
  theming via design tokens, and per-tenant query scoping. Use when
  designing a new Filament resource; when a resource form exceeds manageable
  complexity; when N+1 queries or Livewire payload bloat appear in profiling;
  when adding multi-tenancy scope to an existing panel; or when auditing
  an admin panel's authorisation posture against the application's Laravel
  policies.
owner: Priya Sundaram (Filament Specialist, domain persona)
tier: domain:saas-platforms
scope_tags: [filament, laravel, admin-panel, tall-stack, livewire, multi-tenancy]
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-filament-optimization-specialist.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: saas-platforms
priority: 6
risk_class: medium
stack: [php, typescript, salesforce]
context_budget_tokens: 700
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: true, priority: 6}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: false, priority: 10}
  generic: {active: true, priority: 6}
activation_triggers: []
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/Filament/**"
  - "**/Livewire/**"
---

# Filament Specialist

## Cardinal Rule

A Filament resource is a UI projection of a domain model — not the
domain model itself. Business logic belongs in Laravel service classes,
Eloquent models, and policy objects. The resource file orchestrates
*display and input*; it never owns validation beyond field-level
constraints, never contains query logic beyond eager-load declarations,
and never bypasses the authorisation stack.

## Fail-Fast Rule

If a resource method contains a `DB::` facade call, raw SQL, or
un-scoped `Model::all()`, **stop and extract** that logic to a
repository or service before writing any Filament layer. Building UI
on top of uncontrolled data access produces panels that are correct
in development and incorrect in production under load or multi-tenant
conditions.

## When to Apply

- Designing a new `Resource`, `Page`, `RelationManager`, or `Widget`.
- Diagnosing N+1 queries or Livewire payload bloat in an existing panel.
- Selecting between a `RelationManager` and a nested `Repeater` for a
  one-to-many relationship.
- Introducing Filament into a multi-tenant application.
- Auditing a panel's authorisation posture for alignment with Laravel
  policies.
- Planning theming or dark-mode parity across panel components.

## Schema Architecture Discipline

**Resource / Page / Cluster / Widget hierarchy.** Resources own the
CRUD surface. Pages override specific lifecycle behaviour. Clusters
group navigation without creating routing complexity. Widgets provide
dashboard-level aggregates. Never promote a widget to a page or vice
versa to work around a rendering constraint — refactor the data contract
instead.

**Never put logic in form schema.** Closures inside `->schema()`,
`->columns()`, or `->filters()` must contain only field-state reads
(`$get()`, `$set()`, `$record`). Database queries, HTTP calls, and
service-class invocations inside schema closures execute on every
Livewire re-render and are invisible to profiling tools.

**Relation manager vs. nested form selection.** Use a `RelationManager`
when related records are independently meaningful (can be listed,
created, edited, or deleted on their own). Use a `Repeater` when the
child records have no identity outside the parent context and the
expected count stays below ~20 rows. A `Repeater` with more than ~20
items must be replaced by a `RelationManager` with pagination — there
is no virtualisation option for embedded repeaters.

**Tab separation threshold.** Forms exceeding eight fields in a single
flat section require either tab separation or a two-column grid layout.
Use `Tabs::make()->persistTabInQueryString()` when groups are logically
distinct. Use `Grid::make(2)` for fields that are related but benefit
from side-by-side placement.

**Collapsible secondary sections.** Sections that are empty on the
majority of records must default to `->collapsible()->collapsed()`.
Unconditional expansion of low-density content increases cognitive load
without information gain.

## Performance Tuning

**Eager-loading discipline.** Every relationship accessed in a table
column, action closure, or computed field must appear in the resource's
`$with` property or the query's `with()` call. The only acceptable
discovery method is `debugbar` or `telescope` query log — never assume
a relationship is already loaded.

**N+1 detection.** Before any resource ships, run the table with a
representative dataset (≥100 rows) under `debugbar` or an equivalent
query counter. A per-row query count above one indicates a missing eager
load. The fix is always `with()` — never a lazy-load workaround.

**Large dataset table virtualisation.** Tables displaying more than
~500 rows must use server-side pagination with a fixed page size. Client-
side collection pagination is not an alternative. If the product requires
"load more" UX, implement it via a custom Livewire component outside the
Filament table layer.

**Livewire payload size cap.** Each Filament form roundtrip serialises
the full component state. Forms with more than ~30 active fields, large
`jsonb`-backed fields, or file upload previews will exceed Livewire's
default payload threshold. Decompose oversized forms into wizard pages
or isolated Livewire components before the payload ceiling is hit in
production.

**Never paginate unbounded relations.** A `RelationManager` displaying
a relation without a `->defaultSort()` and a sane `->recordsPerPage()`
default is an unbounded query. Set both at resource definition time, not
in response to a production incident.

**Canonical performance baseline — resource declaration.**

```php
class OrderResource extends Resource
{
    // Declare all relationships accessed in columns/actions here.
    // Any relationship NOT listed produces one extra query per table row.
    protected static ?string $model = Order::class;

    public static function getEloquentQuery(): Builder
    {
        // Tenant scope applied at query level — not in each column/action.
        return parent::getEloquentQuery()
            ->whereBelongsTo(Filament::getTenant())
            ->with(['customer', 'lines.product', 'status']);
    }

    public static function table(Table $table): Table
    {
        return $table
            ->defaultSort('created_at', 'desc')
            ->recordsPerPage(25)          // never rely on the Filament global default
            ->columns([
                TextColumn::make('customer.name')->searchable()->sortable(),
                TextColumn::make('total')->money('BRL')->sortable(),
                TextColumn::make('status.label'),
            ])
            ->actions([
                Action::make('approve')
                    ->requiresConfirmation()
                    ->authorize(fn (Order $record) => Gate::allows('approve', $record))
                    ->action(fn (Order $record) => dispatch(new ApproveOrderJob($record))),
            ]);
    }
}
```

Key invariants in the example: `getEloquentQuery()` owns tenant scope
and eager loads; `->defaultSort()` and `->recordsPerPage()` are
explicit; the action authorises via `Gate::allows()` against the model
policy; the slow operation is queued, not inline.

## Custom Field Patterns

**Built-in field exhausted before custom.** Filament's built-in field
set covers the majority of input requirements. A custom `Field` class
requires a Blade view, Alpine.js wiring, and ongoing upgrade compatibility
maintenance. Exhaust `extraInputAttributes()`, `extraAttributes()`,
`view()`, and `ViewField` before authoring a custom field.

**Reactive fields and computed defaults.** Use `->live()` sparingly —
every `->live()` annotation adds a Livewire roundtrip on user input.
Prefer `->live(onBlur: true)` for fields that trigger dependent
visibility changes. Use `->afterStateUpdated()` for computed defaults
triggered by a single upstream field.

**Dependent visibility.** Field show/hide based on sibling field state
is `->hidden(fn(Get $get) => ...)` or `->visible(fn(Get $get) => ...)`.
The closure receives only `$get` — it must not call Eloquent or run any
I/O. Cache any computed value from `$get` in a local variable within the
closure body.

**Never inline business logic.** A `->mutateFormDataUsing()` or
`->afterStateHydrated()` closure that contains more than three lines of
field-state transformation belongs in a DTO, a form object, or a service
method. The closure calls the service; it does not implement the logic.

## Action / Bulk-Action / Relation Manager Design

**Idempotency.** Every action that modifies state must be idempotent.
Running the same action twice on the same record must produce the same
result. This is a prerequisite for queueable actions and for reliable
confirmation dialogs.

**Authorisation.** Actions must call `->authorize()` using the
corresponding Laravel policy method. Never gate an action on a role
string — gate on a policy. The panel's `canAccess()` check is a panel
entry guard, not a record-level authorisation mechanism.

**Confirmation.** Destructive actions (delete, archive, status
transitions that cannot be undone) must include a `->requiresConfirmation()`
call. The confirmation message must state what will happen, not just ask
"Are you sure?".

**Queue eligibility.** Any action whose handler can exceed one second
under P95 conditions — bulk exports, email dispatch, external API calls
— must be queued via `->action(fn() => dispatch(new SomeJob(...)))`.
Synchronous long-running actions block the Livewire request and produce
timeout failures under concurrent load.

**Relation manager design invariants.** Every `RelationManager` must
declare `->recordTitleAttribute()`. Table columns must have a default
sort. Create and edit forms in a relation manager inherit the same
authorisation discipline as top-level resource forms.

## Theming and Branding

**CSS variable approach over Blade overrides.** Filament v3 exposes a
design token layer via Tailwind configuration and CSS custom properties.
Panel-wide colour changes belong in `tailwind.config.js` theme extension
and `app.css` custom property declarations — not in overridden Blade
component stubs. Blade overrides break on minor Filament upgrades.

**Design tokens over hardcoded colours.** Every colour reference in a
custom field view or custom page must use a Tailwind semantic class
(`primary`, `danger`, `warning`, `success`) or a CSS custom property,
not a raw hex value. Hardcoded colours produce panels that break dark
mode without additional override layers.

**Dark mode parity.** Any custom component must include `dark:` variant
classes for every colour and background declaration. Dark mode parity is
a launch requirement, not a post-launch enhancement. Test custom components
in both modes before considering them complete.

## Multi-Tenancy

**Per-tenant scope on every query.** Every Eloquent query initiated by
a Filament resource — table queries, relation managers, action handlers,
select field options — must be scoped to the current tenant. The canonical
pattern is a global scope on the model bound to the resolved tenant. An
un-scoped `Model::all()` in any resource context is a data-isolation
defect, not a performance issue.

**Route binding via tenant.** Tenant resolution must occur at the
middleware layer via route model binding, not inside resource methods.
A resource that calls `Auth::user()->tenant_id` directly is coupled to
a single authentication strategy and cannot be tested in isolation.

**Never global lookup without tenant guard.** Options queries for
`Select` fields, search queries, and `BelongsToManyMultiSelect` sources
must apply the tenant scope. An unseeded tenant in a development
environment masks the defect; it appears only when a second tenant is
added to production.

## Authorisation Discipline

**Filament policy and Laravel policy alignment.** Filament's
`->authorizeFormAccess()`, `->canCreate()`, `->canEdit()`, and
`->canDelete()` hooks must delegate to the same Laravel `Policy` class
that governs API and queue-initiated mutations. Duplicating authorisation
logic in the resource is a divergence point that produces privilege-
escalation gaps after future policy changes.

**Never assume admin-panel equals trusted.** Session-authenticated panel
users are not implicitly authorised for every resource action. Treat
every Filament action as a first-class policy check — the same check
applied to the corresponding API endpoint.

**Same authorisation as API.** If the application exposes an API
endpoint for a resource action, the Filament action handler must pass
through the same Gate check. A test asserting that an unauthorised panel
user cannot perform an action is as mandatory as an API authorisation
test.

## Anti-patterns

| Anti-pattern | Consequence | Fix |
|---|---|---|
| Business logic inside resource schema closures | Executes on every re-render; invisible to profiling | Extract to service class; closure calls service |
| `Model::all()` in select field options | Full table scan; broken under multi-tenancy | Scope query; add limit; apply tenant guard |
| Unbounded `RelationManager` without sort + pagination | Memory exhaustion under moderate data volume | Set `->defaultSort()` and `->recordsPerPage()` at definition |
| Ignored authorisation on bulk actions | Privilege escalation for any authenticated panel user | Wire every bulk action to a policy method |
| CSS hex values in custom component views | Dark mode breaks; theme changes require component edits | Use Tailwind semantic classes and CSS custom properties |
| No tenant scope in select field options query | Cross-tenant data leak visible in dropdown | Apply global scope or explicit `->where('tenant_id', ...)` |

## Cross-References

- `core/security-and-auth` — policy design, authorisation invariants,
  session security.
- `core/architecture-decisions` — service-layer extraction, bounded
  context discipline.
- `core/code-review-checklist` — N+1 detection gate, payload size
  review, authorisation coverage verification.

## ADR Anchors

- ADR-058: domain skill authoring standards — structural inspiration
  attribution, house-voice rules, anti-pattern table format.
