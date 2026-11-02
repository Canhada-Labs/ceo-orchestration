"""Trust boundaries for the local Mac signing and release wrapper."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / '.claude' / 'hooks'))
from _lib.testing import TestEnvContext  # noqa: E402

spec = importlib.util.spec_from_file_location(
    'mac_sign_and_release', ROOT / '.claude' / 'scripts' / 'local' / 'mac_sign_and_release.py')
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)

SHA1 = 'a' * 40
SHA2 = 'b' * 40
TAG = 'v1.2.3-rc.1'


def result(stdout=''):
    return SimpleNamespace(stdout=stdout)


class TestMacRelease(TestEnvContext):
    def test_run_uses_repository_as_cwd(self):
        with patch.object(wrapper.subprocess, 'run', return_value=result('ok')) as call:
            wrapper.run(['git', 'status'], capture=True)
        call.assert_called_once_with(['git', 'status'], check=True, text=True,
                                     cwd=wrapper.REPO_ROOT, stdout=subprocess.PIPE)

    def test_dirty_tree_stops_before_signing_or_mutation(self):
        commands = []
        def fake(args, capture=False, **kwargs):
            commands.append(args)
            return result(' M tracked\n')
        with patch.object(wrapper, 'require_tools'), patch.object(wrapper, 'run', side_effect=fake):
            with self.assertRaisesRegex(RuntimeError, 'suja'):
                wrapper.sign_merge()
        self.assertEqual(commands, [['git', 'status', '--porcelain']])

    def test_signing_failure_kills_agent_and_reports_hint(self):
        commands = []
        def fake(args, capture=False, **kwargs):
            commands.append(args)
            if args[0] == 'gpg':
                raise subprocess.CalledProcessError(1, args)
            return result()
        with patch.object(wrapper, 'require_tools'), patch.object(wrapper, 'run', side_effect=fake), \
             patch('sys.stderr', new_callable=io.StringIO) as stderr:
            rc = wrapper.main(['sign-merge'])
        self.assertEqual(rc, 1)
        self.assertEqual(commands[-1], ['gpgconf', '--kill', 'gpg-agent'])
        self.assertIn('GPG_TTY', stderr.getvalue())
        self.assertFalse(any(cmd[:2] == ['git', 'push'] for cmd in commands))

    def test_verify_commit_failure_never_pushes(self):
        commands = []
        def fake(args, capture=False, **kwargs):
            commands.append(args)
            if args[:2] == ['git', 'verify-commit']:
                raise subprocess.CalledProcessError(1, args)
            return result(SHA1 if args[:2] == ['git', 'rev-parse'] else '')
        with patch.object(wrapper, 'require_tools'), patch.object(wrapper, 'signing_probe'), \
             patch.object(wrapper, 'run', side_effect=fake), patch('sys.stderr', new_callable=io.StringIO) as stderr:
            rc = wrapper.main(['sign-merge', '--watch'])
        self.assertEqual(rc, 1)
        self.assertIn('verify-commit', stderr.getvalue())
        self.assertTrue(any(c[:2] == ['git', 'verify-commit'] for c in commands))
        self.assertFalse(any(c[:2] == ['git', 'push'] or c[:2] == ['gh', 'run'] for c in commands))

    def test_ci_wrong_sha_and_failed_run_never_green(self):
        for run in (
            {'headSha': SHA2, 'event': 'push', 'status': 'completed', 'conclusion': 'success', 'workflowName': 'Validate'},
            {'headSha': SHA1, 'event': 'push', 'status': 'completed', 'conclusion': 'failure', 'workflowName': 'Validate'},
        ):
            with self.subTest(run=run), patch.object(wrapper, 'run', return_value=result(json.dumps([run]))) as call:
                with self.assertRaises(RuntimeError):
                    wrapper.watch_main(SHA1)
                args = call.call_args.args[0]
                self.assertIn(SHA1, args)
                self.assertIn('push', args)

    def test_ci_waits_for_initial_missing_run_then_times_out(self):
        commands = []
        sleeps = []
        clock = [0]
        def fake(args, capture=False, **kwargs):
            commands.append(args)
            return result('[]')
        def sleep(seconds):
            sleeps.append(seconds)
            clock[0] += seconds
        with patch.object(wrapper, 'CI_TIMEOUT_SECONDS', 10), \
             patch.object(wrapper, 'run', side_effect=fake), \
             patch.object(wrapper.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(wrapper.time, 'sleep', side_effect=sleep):
            with self.assertRaisesRegex(RuntimeError, 'Tempo esgotado'):
                wrapper.watch_main(SHA1)
        self.assertGreater(len(commands), 1)
        self.assertTrue(sleeps)
        self.assertLessEqual(sum(sleeps), 10)
        self.assertTrue(all(SHA1 in command and 'push' in command for command in commands))

    def test_all_in_one_ci_error_does_not_cut_release(self):
        with patch.object(wrapper, 'sign_merge', side_effect=RuntimeError('CI falhou')) as merge, \
             patch.object(wrapper, 'cut_release') as cut, patch('sys.stderr', new_callable=io.StringIO) as stderr:
            rc = wrapper.main(['all-in-one', '--push'])
        self.assertEqual(rc, 1)
        merge.assert_called_once_with(watch=True)
        cut.assert_not_called()
        self.assertIn('CI falhou', stderr.getvalue())

    def test_release_phase_failure_stops_later_actions(self):
        for phase in ('preflight', 'bump', 'tag'):
            commands = []
            def fake(args, capture=False, **kwargs):
                commands.append(args)
                if args[:3] == ['bash', wrapper.RELEASE, phase]:
                    raise subprocess.CalledProcessError(1, args)
                if args[:2] == ['git', 'rev-parse']:
                    return result(SHA1)
                if args[:3] == ['git', 'branch', '--show-current']:
                    return result('main')
                return result()
            with self.subTest(phase=phase), patch.object(wrapper, 'run', side_effect=fake), \
                 patch('sys.stderr', new_callable=io.StringIO) as stderr:
                rc = wrapper.main(['cut-rc', '--push'])
            self.assertEqual(rc, 1)
            self.assertIn(phase, stderr.getvalue())
            phases = [c[2] for c in commands if c[:2] == ['bash', wrapper.RELEASE]]
            self.assertEqual(phases, ['preflight', 'bump', 'tag'][:['preflight', 'bump', 'tag'].index(phase) + 1])
            self.assertFalse(any(c[:2] == ['git', 'push'] for c in commands))

    def test_no_push_creates_local_tag_without_publication(self):
        commands = []
        def fake(args, capture=False, **kwargs):
            commands.append(args)
            if args[:2] == ['git', 'rev-parse']:
                return result(SHA1)
            if args[:3] == ['git', 'branch', '--show-current']:
                return result('main')
            if args[:3] == ['bash', wrapper.RELEASE, 'tag']:
                return result(f'TAG {TAG} IS SIGNED LOCALLY AND NOT PUSHED.\n')
            return result()
        with patch.object(wrapper, 'run', side_effect=fake):
            self.assertEqual(wrapper.cut_release(), TAG)
        self.assertTrue(any(c[:3] == ['bash', wrapper.RELEASE, 'tag'] for c in commands))
        self.assertFalse(any(c[:2] == ['git', 'push'] for c in commands))

    def test_bad_tag_or_tag_head_mismatch_does_not_push(self):
        for malformed in (True, False):
            commands = []
            def fake(args, capture=False, **kwargs):
                commands.append(args)
                if args[:3] == ['git', 'rev-parse', '--verify']:
                    return result(SHA2)
                if args[:2] == ['git', 'rev-parse']:
                    return result(SHA1)
                if args[:3] == ['git', 'branch', '--show-current']:
                    return result('main')
                if args[:3] == ['bash', wrapper.RELEASE, 'tag']:
                    return result('TAG invalid IS SIGNED LOCALLY AND NOT PUSHED.\n' if malformed else
                                  f'TAG {TAG} IS SIGNED LOCALLY AND NOT PUSHED.\n')
                return result()
            with self.subTest(malformed=malformed), patch.object(wrapper, 'run', side_effect=fake), \
                 patch('sys.stderr', new_callable=io.StringIO) as stderr:
                rc = wrapper.main(['cut-rc', '--push'])
            self.assertEqual(rc, 1)
            self.assertIn('tag', stderr.getvalue().lower())
            self.assertFalse(any(c[:2] == ['git', 'push'] for c in commands))

    def test_bump_commit_requires_push_and_ci_before_tag(self):
        for push in (False, True):
            events = []
            heads = iter([SHA1, SHA2] + [SHA2] * 4)
            def fake(args, capture=False, **kwargs):
                events.append(args)
                if args[:3] == ['git', 'rev-parse', '--verify']:
                    return result(SHA2)
                if args[:2] == ['git', 'rev-parse']:
                    return result(next(heads))
                if args[:3] == ['git', 'branch', '--show-current']:
                    return result('main')
                if args[:3] == ['bash', wrapper.RELEASE, 'tag']:
                    return result(f'TAG {TAG} IS SIGNED LOCALLY AND NOT PUSHED.\n')
                return result()
            def watch(sha):
                events.append(['watch', sha])
            with self.subTest(push=push), patch.object(wrapper, 'run', side_effect=fake), \
                 patch.object(wrapper, 'watch_main', side_effect=watch), patch('sys.stderr', new_callable=io.StringIO) as stderr:
                rc = wrapper.main(['cut-rc'] + (['--push'] if push else []))
            if push:
                self.assertEqual(rc, 0)
                self.assertLess(events.index(['git', 'push', 'origin', 'main']), events.index(['watch', SHA2]))
                tag_index = next(i for i, c in enumerate(events) if c[:3] == ['bash', wrapper.RELEASE, 'tag'])
                self.assertLess(events.index(['watch', SHA2]), tag_index)
                self.assertIn(['git', 'push', 'origin', 'refs/tags/' + TAG], events)
            else:
                self.assertEqual(rc, 1)
                self.assertIn('bump', stderr.getvalue())
                self.assertFalse(any(c[:2] == ['git', 'push'] or c[:3] == ['bash', wrapper.RELEASE, 'tag'] for c in events))

    def test_signed_merge_is_verified_before_push_and_watches_same_sha(self):
        events = []
        heads = iter([SHA1, SHA2, SHA2])
        def fake(args, capture=False, **kwargs):
            events.append(args)
            if args[:2] == ['git', 'rev-parse']:
                return result(next(heads))
            if args[:3] == ['git', 'branch', '--show-current']:
                return result('main')
            return result()
        with patch.object(wrapper, 'require_tools'), patch.object(wrapper, 'signing_probe'), \
             patch.object(wrapper, 'run', side_effect=fake), \
             patch.object(wrapper, 'watch_main', side_effect=lambda sha: events.append(['watch', sha])):
            self.assertEqual(wrapper.sign_merge(watch=True), SHA2)
        merge = next(c for c in events if c[:2] == ['git', 'merge'])
        self.assertIn('-S', merge)
        self.assertIn('--no-ff', merge)
        self.assertIn('origin/' + wrapper.TRACK, merge)
        self.assertLess(events.index(merge), events.index(['git', 'verify-commit', 'HEAD']))
        self.assertLess(events.index(['git', 'verify-commit', 'HEAD']), events.index(['git', 'push', 'origin', 'main']))
        self.assertEqual(events[-1], ['watch', SHA2])

    def test_ci_waits_for_pending_run_and_rechecks_success(self):
        pending = {'headSha': SHA1, 'event': 'push', 'status': 'in_progress',
                   'conclusion': '', 'workflowName': 'Validate', 'databaseId': 42}
        done = dict(pending, status='completed', conclusion='success')
        snapshots = iter([[], [pending], [done]])
        commands = []
        def fake(args, capture=False, **kwargs):
            commands.append(args)
            if args[:3] == ['gh', 'run', 'list']:
                return result(json.dumps(next(snapshots)))
            return result()
        with patch.object(wrapper, 'run', side_effect=fake), patch.object(wrapper.time, 'sleep') as sleep:
            wrapper.watch_main(SHA1)
        sleep.assert_called_once()
        self.assertIn(['gh', 'run', 'watch', '42', '--exit-status'], commands)
        self.assertEqual(len([c for c in commands if c[:3] == ['gh', 'run', 'list']]), 3)

    def test_ga_uses_stable_flags_and_pushes_verified_ga_tag(self):
        commands = []
        tag = 'v1.2.3'
        def fake(args, capture=False, **kwargs):
            commands.append(args)
            if args[:2] == ['git', 'rev-parse']:
                return result(SHA1)
            if args[:3] == ['git', 'branch', '--show-current']:
                return result('main')
            if args[:3] == ['bash', wrapper.RELEASE, 'tag']:
                return result(f'TAG {tag} IS SIGNED LOCALLY AND NOT PUSHED.\n')
            return result()
        with patch.object(wrapper, 'run', side_effect=fake):
            self.assertEqual(wrapper.main(['cut-ga', '--push']), 0)
        for phase in ('preflight', 'bump', 'tag'):
            command = next(c for c in commands if c[:3] == ['bash', wrapper.RELEASE, phase])
            self.assertIn('--stable', command)
        self.assertIn(['git', 'push', 'origin', 'refs/tags/' + tag], commands)
