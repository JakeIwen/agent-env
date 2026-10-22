#!/usr/bin/env python3
"""Agent-side checks, scoped to successful source edits in the stopping session's current turn.

A shared checkout is not authorship evidence. Research-only and unknown-attribution turns stay
silent, including when another agent commits improvements. Hooks never write repo files.
`--record` is retained for existing UserPromptSubmit registrations; it is now a silent no-op.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

import drift_check
from turn_activity import turn_activity

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, 'drift_check.py')
STATE_DIR = os.path.join(os.path.expanduser('~'), '.cache', 'codeshape')
REVIEW_SKILL = '~/.claude/skills/thermo-nuclear-code-quality-review/SKILL.md'
MAX_LINES = 12
IMPROVEMENTS_WORTH_A_NUDGE = 3
REBASELINE_HINT = '`/consolidate rebaseline` (Claude Code) or `$consolidate rebaseline` (Codex)'


def git(root, *args, timeout=5):
    try:
        return subprocess.run(['git', '-C', root, *args], capture_output=True,
                              text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return None


def git_out(root, *args):
    r = git(root, *args)
    return r.stdout.strip() if r and r.returncode == 0 else ''


def state_file(session, root, kind):
    key = hashlib.sha256(f'{session}|{os.path.realpath(root)}|{kind}'.encode()).hexdigest()
    return Path(STATE_DIR) / key


def claim(session, root, kind):
    """Atomic, persistent once-only claim; no PID identity or test-time cache wiping."""
    try:
        Path(STATE_DIR).mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(str(state_file(session, root, kind)), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        return True
    except OSError:
        return False


def hook_mode(root):
    mode = os.environ.get('CODESHAPE_HOOK_MODE', '').strip().lower()
    if mode:
        return mode
    try:
        return str(json.loads((Path(root) / '.codeshape/config.json').read_text()).get('hook_mode', 'advisory')).lower()
    except (OSError, ValueError, AttributeError):
        return 'advisory'


def tree_is_clean(root):
    r = git(root, 'status', '--porcelain', '--untracked-files=all')
    return r is not None and r.returncode == 0 and not r.stdout.strip()


def push_instruction(root):
    # Repository state alone cannot grant push permission; keep the session's existing authorization.
    return ('Keep the user-authorized commit/push intent of the task: if this task was authorized to commit '
            'and push, include the baseline commit in that same push; otherwise do not push. '
            'A clean or fully pushed branch is not new authorization.')


def owned_lines(out, prefix, paths):
    """Global marker totals have no file attribution; never block a worker on them automatically."""
    return [line for line in out.splitlines() if line.startswith(prefix)
            and any(line[len(prefix):].startswith(path + ':') for path in paths)]


def review_due(activity, root, cfg):
    """Count attributable edit/patch payload lines, never another session's Git diff."""
    threshold = cfg.get('review_lines', 400)
    if not isinstance(threshold, int) or threshold <= 0:
        return None
    path = state_file(activity['session'], root, 'owned-review-v1')
    try:
        state = json.loads(path.read_text())
    except (OSError, ValueError):
        state = {'lines': 0, 'paths': []}
    state['lines'] += sum(activity['changes'].values())
    state['paths'] = sorted(set(state['paths']) | set(activity['paths']))
    due = dict(state) if state['lines'] >= threshold else None
    if due:
        state = {'lines': 0, 'paths': []}
    tmp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    try:
        tmp.write_text(json.dumps(state))
        os.replace(str(tmp), str(path))
    except OSError:
        return None
    return due


def owned_improvements(root, paths):
    """Rebaseline eligibility requires actual improvement in files this turn demonstrably edited."""
    try:
        base = json.loads((Path(root) / '.codeshape/baseline.json').read_text())
        count = 0
        for path in paths:
            text = (Path(root) / path).read_text()
            before = base['files'].get(path, 0)
            limit = drift_check.file_limit(base, path)
            if limit is not None and before > limit and len(text.splitlines()) < before:
                count += 1
            if path.endswith('.py'):
                funcs, _ = drift_check.python_functions(text)
                old = drift_check.over_limit_functions(base, path)
                count += sum(1 for name, _, length in funcs if name in old and length < old[name])
        return count
    except (OSError, ValueError, SyntaxError, KeyError, TypeError):
        return 0


def review_instruction(name, due, root):
    paths = ', '.join(due['paths'][:20])
    return (f'code-shape ({name}): this session made about {due["lines"]} source-line edits '
            f'since its last review request. Run thermo-nuclear-code-quality-review ({REVIEW_SKILL}) '
            f'on your own edits in: {paths}. Use the tool-call history to identify your changes; '
            'a shared checkout diff can include another agent\'s work. Do not review or modify that work. '
            'Follow the current worker-model policy if delegating; do not silently switch models. '
            'Fix only findings inside the authorized task and report anything deferred. If ownership '
            'is ambiguous or this is research-only work, skip the request and finish without further action. '
            'Preserve the task\'s existing commit/push plan; this review grants no additional permission.')


def rebaseline_instruction(name, count, root):
    command = f'python3 {shlex.quote(CHECK)} rebaseline --repo {shlex.quote(root)}'
    return (f'code-shape ({name}): {count} improvements in source files this turn edited, and the tree is clean. '
            f'As part of this implementation task only, run `{command}` and handle .codeshape/baseline.json '
            'under the task\'s existing commit authorization. If committing is authorized, use a separate '
            '`code-shape: rebaseline` commit containing only that file. '
            + push_instruction(root) + ' Do not take over another agent\'s baseline or change its work. '
            'If this is outside your task, ownership is uncertain, the tree changes, or the command fails, '
            'skip and finish; this is a one-time request, not a reason to keep retrying.')


def emit(reason, notes):
    msg = {}
    if reason:
        msg.update(decision='block', reason=reason)
    if notes:
        msg['systemMessage'] = '\n\n'.join(notes)
    if msg:
        print(json.dumps(msg))


def on_stop(event, session, root):
    if event.get('stop_hook_active'):
        return
    cfg = drift_check.load_config(root)
    if 'config_error' in cfg:
        return
    activity = turn_activity(event, root, cfg, drift_check)
    if not activity:
        return  # no source writes by this turn: no scan, notices, review, or rebaseline
    session = activity['session']
    if not claim(session, root, 'handled-turn-v1:' + activity['turn']):
        return
    r = subprocess.run([sys.executable, CHECK, 'ratchet', '--repo', root], capture_output=True,
                       text=True, timeout=25, check=False)
    if r.returncode not in (0, 1):
        return
    out, name = r.stdout.strip(), os.path.basename(root)
    notes = []
    exceptions = owned_lines(out, 'EXCEPTION  ', activity['paths'])
    for line in exceptions[:MAX_LINES]:
        if claim(session, root, 'exception-v1:' + line):
            notes.append(line)
    worse = owned_lines(out, 'WORSE  ', activity['paths'])
    mode = hook_mode(root)
    if worse:
        text = (f'code-shape ({name}): warnings in files this turn edited:\n' + '\n'.join(worse[:MAX_LINES])
                + '\nOnly address your own changes within scope. Other agents may also have edited these files. '
                'If the warning predates your change or belongs to someone else, leave it alone and finish. '
                'Do not rebaseline to hide it or keep acknowledging this request.')
        if mode == 'block':
            emit(text, notes)
        else:
            emit(None, [text] + notes)
        return
    due = review_due(activity, root, cfg)
    if due:
        text = review_instruction(name, due, root)
        emit(text if mode == 'block' else None, notes if mode == 'block' else notes + [text])
        return
    if r.returncode == 0 and not exceptions and 'ratchet: ok;' in out and tree_is_clean(root):
        count = owned_improvements(root, activity['paths'])
        if count >= IMPROVEMENTS_WORTH_A_NUDGE and claim(session, root, 'rebaseline-request-v1'):
            text = rebaseline_instruction(name, count, root)
            emit(text if mode == 'block' else None, notes if mode == 'block' else notes + [text])
            return
    if out.startswith('ratchet: no baseline') and claim(session, root, 'no-baseline-v1'):
        notes.append(f'code-shape ({name}): no baseline; use {REBASELINE_HINT} when initializing policy for this repo.')
    emit(None, notes)


def main():
    if '--record' in sys.argv[1:]:
        return
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict) or event.get('stop_hook_active'):
            return
        root = git_out(event.get('cwd') or os.getcwd(), 'rev-parse', '--show-toplevel')
        if root:
            on_stop(event, event.get('session_id'), root)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError):
        return  # incomplete host payload or unavailable state never traps a session


if __name__ == '__main__':
    main()
