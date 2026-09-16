## Cure discipline — cure the class, not the example

> Added 2026-09-16 (PLAN-189 W0, ADR-140-AMEND-1). Applies to every cure of a
> review finding — pair-rail, debate, Owner, CI — from the first round of a
> ceremony onward. It reduces no detection: no round ceiling, no filter, no
> severity that waives review.

Every finding a reviewer raises belongs to a **class**: the property it
violates, or the input surface it enters through. The author of the cure
names the class in the round record — one `Class:` line per finding — and the
judgment is the author's, written down, never implicit. "Same class" is met by
either test: same property violated, or same input surface.

1. **First occurrence** — cure the finding and name its class in the record.
2. **Second occurrence of the same class in the same ceremony** — the next
   cure MUST NOT be another example. Either it removes the surface (an
   architecture change: the input no longer exists, or the property holds by
   construction), or the record states in writing why removal is not
   possible and carries a **named risk acceptance** for that class.
3. A round record showing a second occurrence of a class with neither a
   structural cure nor a declared acceptance is a **visible violation** of
   this section: it is a blocking finding against the record itself, and no
   further round opens on that class until the record carries one of the two.

Enumerating instances is not a cure; it is how a class stays open. Precedents:
PLAN-179 r22 — five rounds on one basename sanitizer (spaces, hyphens,
concatenation, limits), closed only when the surface was removed; PLAN-189
diagnosis — `_sanitize_memory_basename` byte-identical between the r6 and r15
candidates, so the "late" P1 had been there since r6.

Companion rules land in their own signatures: controls proportional to the
risk of the change (PLAN-189 W1), rail telemetry (W2), and the safeguard
against editing the record (W3).
