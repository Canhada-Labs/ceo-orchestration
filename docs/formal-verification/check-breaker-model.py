#!/usr/bin/env python3
"""Check the finite breaker model and prove that each property can fail.

Uses the SHA-verified TLC jar supplied by run-tlc.sh; no downloads here.
Mutants live only in a temporary directory. Runtime conformance is separate.
"""
from __future__ import annotations
import pathlib
import subprocess
import sys
import tempfile


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent
    jar = pathlib.Path(sys.argv[1]).resolve()
    source = (root / 'breaker.tla').read_text()
    config = (root / 'breaker.cfg').read_text()
    cases = [
        ('baseline', source, config, None),
        ('three-callers', source, config.replace('MAX_CALLERS       = 2', 'MAX_CALLERS       = 3'), None),
        ('short-window', source, config.replace('WINDOW_S          = 10', 'WINDOW_S          = 2'), None),
    ]
    mutations = [
        ('double-probe', 'THEN FALSE\n                         ELSE probe_available',
         'THEN TRUE\n                         ELSE probe_available', 'S2_HalfOpenSingleton'),
        ('threshold-missed', 'Len(AddFailure) >= FAILURE_THRESHOLD',
         'Len(AddFailure) > FAILURE_THRESHOLD', 'S1_OpenOnThreshold'),
        ('audit-missing', "audit_epoch' = ~audit_epoch", "audit_epoch' = audit_epoch", 'S3_OpenEmitsAudit'),
        ('timer-stuck', 'opened_age = HALF_OPEN_HOLD_S', 'opened_age > HALF_OPEN_HOLD_S', 'L1_EventuallyHeal'),
    ]
    for name, old, new, prop in mutations:
        if source.count(old) != 1:
            raise AssertionError('mutation anchor drift: ' + name)
        cases.append((name, source.replace(old, new), config, prop))
    for name, model, cfg, expected_failure in cases:
        with tempfile.TemporaryDirectory(prefix='breaker-tlc-') as tmp:
            work = pathlib.Path(tmp)
            (work / 'breaker.tla').write_text(model)
            (work / 'breaker.cfg').write_text(cfg)
            result = subprocess.run(
                ['java', '-Xmx2G', '-cp', str(jar), 'tlc2.TLC',
                 '-workers', '4', '-config', 'breaker.cfg', 'breaker.tla'],
                cwd=work, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=180)
            log = result.stdout
            if expected_failure is None:
                ok = result.returncode == 0 and 'No error has been found' in log
            else:
                # A syntax error or timeout must never count as killing a mutant.
                ok = result.returncode != 0 and (
                    ('Invariant ' + expected_failure + ' is violated') in log or
                    ('Action property ' + expected_failure + ' is violated') in log or
                    ('Temporal property ' + expected_failure + ' was violated') in log)
            if not ok:
                print(log)
                raise AssertionError('unexpected TLC result for ' + name)
            print(name + ': ' + ('PASS' if expected_failure is None
                                 else 'rejected by ' + expected_failure), flush=True)


if __name__ == '__main__':
    main()
