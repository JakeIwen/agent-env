"""Regression fixtures for shared-checkout Stop hooks. No network, git commits, or real cache writes."""
import contextlib
import io
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess
import tempfile
import unittest
from unittest import mock

import drift_check
import stop_hook as hook
from turn_activity import turn_activity


class HookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('CODESHAPE_TEST_TMP'))
        self.root = Path(self.temp.name) / 'checkout'
        self.root.mkdir()
        self.cache = Path(self.temp.name) / 'cache'
        self.cfg = dict(drift_check.DEFAULTS, exclude=[])
        self.ratchet = 'ratchet: ok; 7 improvement(s). Run rebaseline to lock them in.\n'
        self.exit_code = 0
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.addCleanup(self.temp.cleanup)
        self.stack.enter_context(mock.patch.object(hook, 'STATE_DIR', str(self.cache)))
        self.stack.enter_context(mock.patch.object(hook.drift_check, 'load_config', return_value=self.cfg))
        self.stack.enter_context(mock.patch.object(hook, 'hook_mode', return_value='block'))
        self.stack.enter_context(mock.patch.object(hook, 'tree_is_clean', return_value=True))
        self.run = self.stack.enter_context(mock.patch.object(hook.subprocess, 'run', side_effect=self.result))
        self.improvements = self.stack.enter_context(mock.patch.object(hook, 'owned_improvements', return_value=4))

    def result(self, *args, **kwargs):
        return subprocess.CompletedProcess([], self.exit_code, self.ratchet, '')

    def transcript(self, name, records, session=True):
        path = Path(self.temp.name) / (name + '.jsonl')
        current = None
        for record in records:
            if record.get('type') == 'user' and record.get('uuid'):
                current = record['uuid']
            elif record.get('type') == 'user' and current:
                record.setdefault('promptId', current)
        path.write_text(''.join(json.dumps(r) + '\n' for r in records))
        event = {'cwd': str(self.root), 'transcript_path': str(path), 'prompt_id': current}
        if session:
            event['session_id'] = name
        return event

    def prompt(self, key='p1'):
        return {'type': 'user', 'uuid': key, 'message': {'role': 'user', 'content': 'fixture'}}

    def edit(self, key='c1', path='a.py', lines=2, failed=False, name='Edit'):
        file_path = str(self.root / path)
        args = {'file_path': file_path, 'old_string': 'old\n', 'new_string': 'new\n' * lines}
        if name == 'Write':
            args = {'file_path': file_path, 'content': 'line\n' * lines}
        return [
            {'type': 'assistant', 'message': {'role': 'assistant', 'content': [
                {'type': 'tool_use', 'id': key, 'name': name, 'input': args}]}},
            {'type': 'user', 'toolUseResult': {'filePath': file_path},
             'message': {'role': 'user', 'content': [
                {'type': 'tool_result', 'tool_use_id': key, 'is_error': failed, 'content': 'fixture'}]}}
        ]

    def run_stop(self, event):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            hook.on_stop(event, event.get('session_id'), str(self.root))
        text = output.getvalue()
        return json.loads(text) if text else None

    def test_researcher_silent_on_peer_committed_improvements(self):
        event = self.transcript('researcher', [self.prompt()])
        self.assertIsNone(self.run_stop(event))
        self.run.assert_not_called()
        self.improvements.assert_not_called()

    def test_two_sessions_one_checkout_writer_only_gets_rebaseline(self):
        reader = self.transcript('researcher', [self.prompt()])
        writer = self.transcript('writer', [self.prompt()] + self.edit())
        result = self.run_stop(writer)
        self.assertEqual(result['decision'], 'block')
        self.assertIn('rebaseline', result['reason'])
        for _ in range(5):
            self.assertIsNone(self.run_stop(reader))
            self.assertIsNone(self.run_stop(writer))
        self.assertEqual(self.run.call_count, 1)

    def test_reader_silent_on_peer_regressions_and_review_threshold(self):
        self.exit_code = 1
        self.ratchet = 'WORSE  a.py: grew\nratchet: 1 regression\n'
        self.assertIsNone(self.run_stop(self.transcript('r', [self.prompt()])))
        self.run.assert_not_called()

    def test_read_tools_and_shell_output_dont_imply_authorship(self):
        records = [self.prompt()] + self.edit(name='Read')
        records += [
            {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'exec_command',
             'call_id': 'shell', 'arguments': json.dumps({'cmd': 'git log --stat'})}},
            {'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'shell',
             'output': 'Process exited with code 0\nOutput: changed 1000 source lines'}}]
        self.assertIsNone(self.run_stop(self.transcript('r', records)))

    def test_previous_writer_now_researching_is_silent(self):
        rows = [self.prompt('old')] + self.edit() + [self.prompt('research')]
        self.assertIsNone(self.run_stop(self.transcript('r', rows)))
        self.run.assert_not_called()

    def test_failed_write_does_not_count(self):
        rows = [self.prompt()] + self.edit(failed=True)
        self.assertIsNone(self.run_stop(self.transcript('r', rows)))

    def test_non_source_and_policy_files_do_not_count(self):
        for path in ['notes.md', '.agent/report.py', '.codeshape/baseline.json', '.claude/foo.py']:
            with self.subTest(path=path):
                self.assertIsNone(self.run_stop(self.transcript('r', [self.prompt()] + self.edit(path=path))))

    def test_writes_outside_root_do_not_count(self):
        self.assertIsNone(self.run_stop(self.transcript('r', [self.prompt()] + self.edit(path='../other.py'))))

    def test_retry_without_stop_hook_active_is_deduplicated(self):
        self.exit_code = 1
        self.ratchet = 'WORSE  a.py: grew\nratchet: 1 regression\n'
        event = self.transcript('r', [self.prompt()] + self.edit())
        self.assertEqual(self.run_stop(event)['decision'], 'block')
        self.assertIsNone(self.run_stop(event))

    def test_stop_hook_active_is_quiet_even_after_more_writes(self):
        event = self.transcript('r', [self.prompt()] + self.edit())
        event['stop_hook_active'] = True
        self.assertIsNone(self.run_stop(event))
        self.run.assert_not_called()

    def test_missing_session_id_uses_stable_transcript_identity(self):
        event = self.transcript('r', [self.prompt()] + self.edit(), session=False)
        self.assertIsNotNone(self.run_stop(event))
        self.assertIsNone(self.run_stop(event))

    def test_missing_or_bad_transcript_is_quiet(self):
        for event in [{'cwd': str(self.root)}, {'transcript_path': '/no/such/path'}]:
            self.assertIsNone(self.run_stop(event))
        event = self.transcript('bad', [{'unrecognized': 'record'}])
        self.assertIsNone(self.run_stop(event))
        self.run.assert_not_called()

    def test_current_turn_filters_peer_file_warnings(self):
        self.exit_code = 1
        self.ratchet = 'WORSE  peer.py: grew\nWORSE  marker ts_any: 1 -> 20\nratchet: 2 regressions\n'
        event = self.transcript('writer', [self.prompt()] + self.edit())
        self.assertIsNone(self.run_stop(event))

    def test_own_warnings_still_block(self):
        self.exit_code = 1
        self.ratchet = 'WORSE  a.py: grew\nWORSE  peer.py: grew\nratchet: 2 regressions\n'
        result = self.run_stop(self.transcript('w', [self.prompt()] + self.edit()))
        self.assertEqual(result['decision'], 'block')
        self.assertIn('a.py', result['reason'])
        self.assertNotIn('peer.py', result['reason'])

    def test_400_review_counts_own_payload_not_peer_diff(self):
        self.ratchet = ''
        event = self.transcript('w', [self.prompt('one')] + self.edit(lines=199))
        self.assertIsNone(self.run_stop(event))  # 200 old + new lines
        event = self.transcript('w', [self.prompt('two')] + self.edit(key='c2', lines=199))
        result = self.run_stop(event)
        self.assertIn('400 source-line edits', result['reason'])
        self.assertIn('thermo-nuclear', result['reason'])
        self.assertIsNone(self.run_stop(event))

    def test_rebaseline_once_per_session_even_after_new_turn(self):
        event = self.transcript('w', [self.prompt()] + self.edit())
        self.assertIn('rebaseline', self.run_stop(event)['reason'])
        event = self.transcript('w', [self.prompt('next')] + self.edit(key='c2'))
        self.assertIsNone(self.run_stop(event))

    def test_no_auto_baseline_without_own_improvements(self):
        self.improvements.return_value = 0
        self.assertIsNone(self.run_stop(self.transcript('w', [self.prompt()] + self.edit())))

    def test_dirty_tree_does_not_rebaseline(self):
        with mock.patch.object(hook, 'tree_is_clean', return_value=False):
            self.assertIsNone(self.run_stop(self.transcript('w', [self.prompt()] + self.edit())))

    def test_rebaseline_does_not_grant_commit_or_push_permission(self):
        text = hook.rebaseline_instruction('fixture', 4, str(self.root))
        self.assertIn('existing commit authorization', text)
        self.assertIn('not new authorization', text)

    def test_atomic_turn_claim(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: hook.claim('s', str(self.root), 'same'), range(20)))
        self.assertEqual(sum(results), 1)

    def codex_record(self, turn='t1', success=True, modern=False):
        change = {str(self.root / 'a.py'): {'type': 'update', 'unified_diff': '-old\n+new\n'}}
        payload = {'type': 'patch_apply_end', 'turn_id': turn, 'call_id': 'patch',
                   'success': success, 'status': 'completed' if success else 'failed', 'changes': change}
        if modern:
            payload = {'type': 'item_completed', 'turn_id': turn, 'thread_id': 'codex',
                       'item': {'type': 'FileChange', 'id': 'patch', 'status': payload['status'], 'changes': change}}
        return {'type': 'event_msg', 'payload': payload}

    def test_codex_structured_patch_success(self):
        event = self.transcript('codex', [self.codex_record()])
        event['turn_id'] = 't1'
        evidence = turn_activity(event, str(self.root), self.cfg, drift_check)
        self.assertEqual(evidence['changes'], {'a.py': 2})
        self.assertIsNotNone(self.run_stop(event))
        event['turn_id'] = 'research'
        self.assertIsNone(self.run_stop(event))

    def test_codex_modern_filechange(self):
        event = self.transcript('codex', [self.codex_record(modern=True)])
        event['turn_id'] = 't1'
        self.assertEqual(turn_activity(event, str(self.root), self.cfg, drift_check)['paths'], ['a.py'])

    def test_codex_failed_patch(self):
        event = self.transcript('codex', [self.codex_record(success=False)])
        event['turn_id'] = 't1'
        self.assertIsNone(self.run_stop(event))

    def test_shell_and_unstructured_patch_output_are_not_evidence(self):
        rows = [self.prompt(),
                {'type': 'response_item', 'payload': {'type': 'custom_tool_call_output',
                 'call_id': 'patch', 'output': 'Success. Updated the following files:\nM a.py'}}]
        self.assertIsNone(self.run_stop(self.transcript('w', rows)))

    def test_exact_turn_id_required(self):
        event = self.transcript('w', [self.prompt()] + self.edit())
        del event['prompt_id']
        self.assertIsNone(self.run_stop(event))
        self.run.assert_not_called()

    def test_result_without_prompt_id_is_ignored(self):
        event = self.transcript('w', [self.prompt()] + self.edit())
        p = Path(event['transcript_path'])
        rows = [json.loads(line) for line in p.read_text().splitlines()]
        for row in rows:
            row.pop('promptId', None)
        p.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        self.assertIsNone(self.run_stop(event))

    def test_null_codex_transcript_is_ignored(self):
        self.assertIsNone(self.run_stop({'turn_id': 't1', 'session_id': 'codex', 'transcript_path': None}))


if __name__ == '__main__':
    unittest.main()
