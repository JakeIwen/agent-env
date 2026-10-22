"""Attribute edits using exact host turn IDs and successful, structured file-write records.

Git activity and command/output prose never establish ownership. Unknown transcript versions,
missing turn IDs, missing transcripts, and research-only turns fail quiet. Nothing is executed
from a transcript and no prompt, code, or output body is saved in hook state.
"""
import hashlib
import json
import os
from pathlib import Path

MAX_BYTES = 16 * 1024 * 1024
MAX_RECORD_BYTES = 4 * 1024 * 1024


def short_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def read_records(path):
    with open(path, 'rb') as fh:
        size = os.fstat(fh.fileno()).st_size
        if size > MAX_BYTES:
            fh.seek(size - MAX_BYTES)
            fh.readline()
        records = []
        while True:
            raw = fh.readline(MAX_RECORD_BYTES + 1)
            if not raw:
                break
            if len(raw) > MAX_RECORD_BYTES:
                return []  # incomplete tool-call pair: do not infer authorship
            try:
                record = json.loads(raw)
            except ValueError:
                continue
            if isinstance(record, dict):
                records.append(record)
        return records


def source_path(raw, cwd, root, cfg, detector):
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path(cwd) / path
    path = path.resolve()
    try:
        rel = path.relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return None
    if any(part in ('.git', '.agent', '.claude', '.codex', '.codeshape', '.local', '.cache')
           for part in Path(rel).parts):
        return None
    if path.suffix not in detector.SOURCE_EXT or detector.excluded(rel, cfg['exclude']):
        return None
    return rel


def claude_edits(records, prompt_id):
    calls = {}
    for r in records:
        msg = r.get('message', {})
        if not isinstance(msg, dict) or not isinstance(msg.get('content'), list):
            continue
        for block in msg['content']:
            if not isinstance(block, dict):
                continue
            if r.get('type') == 'assistant' and block.get('type') == 'tool_use':
                calls[block.get('id')] = block
                continue
            if (r.get('type') != 'user' or block.get('type') != 'tool_result'
                    or r.get('promptId') != prompt_id or block.get('is_error')):
                continue
            call = calls.get(block.get('tool_use_id'), {})
            name = str(call.get('name', '')).split('.')[-1].lower()
            args, result = call.get('input', {}), r.get('toolUseResult')
            if (name not in ('write', 'edit', 'multiedit') or not isinstance(args, dict)
                    or not isinstance(result, dict) or result.get('success') is False or result.get('error')):
                continue
            path = result.get('filePath')
            if not isinstance(path, str) or path != args.get('file_path'):
                continue
            if name == 'write':
                count = len(str(args.get('content', '')).splitlines())
            else:
                edits = args.get('edits', [args])
                count = sum(len(str(e.get(k, '')).splitlines()) for e in edits if isinstance(e, dict)
                            for k in ('old_string', 'new_string'))
            yield str(block.get('tool_use_id')), {path: count}


def codex_edits(records, turn_id):
    for r in records:
        if r.get('type') != 'event_msg':
            continue
        p = r.get('payload', {})
        if not isinstance(p, dict) or p.get('turn_id') != turn_id:
            continue
        kind = p.get('type')
        if kind == 'patch_apply_end':
            if p.get('success') is not True or p.get('status') != 'completed':
                continue
            key, changes = p.get('call_id'), p.get('changes')
        elif kind == 'item_completed':
            item = p.get('item', {})
            if not isinstance(item, dict) or item.get('type') != 'FileChange' or item.get('status') != 'completed':
                continue
            key, changes = item.get('id'), item.get('changes')
        else:
            continue
        if not key or not isinstance(changes, dict):
            continue
        result = {}
        for path, change in changes.items():
            if not isinstance(change, dict):
                continue
            diff = change.get('unified_diff')
            count = sum(1 for line in diff.splitlines() if line.startswith(('+', '-'))
                        and not line.startswith(('+++', '---'))) if isinstance(diff, str) else 0
            if not diff and isinstance(change.get('content'), str):
                count = len(change['content'].splitlines())
            result[path] = count
            if isinstance(change.get('move_path'), str):
                result[change['move_path']] = 0
        yield str(key), result


def turn_activity(event, root, cfg, detector):
    path = event.get('transcript_path')
    prompt_id, turn_id = event.get('prompt_id'), event.get('turn_id')
    if not isinstance(path, str) or not path or not (prompt_id or turn_id):
        return None
    try:
        path = str(Path(path).expanduser().resolve())
        records = read_records(path)
        edits = claude_edits(records, prompt_id) if prompt_id else codex_edits(records, turn_id)
        changes, seen = {}, set()
        for key, files in edits:
            if key in seen:
                continue
            seen.add(key)
            for raw, count in files.items():
                rel = source_path(raw, event.get('cwd', root), root, cfg, detector)
                if rel:
                    changes[rel] = changes.get(rel, 0) + count
        if not changes:
            return None
        session = event.get('session_id') or event.get('thread_id') or short_hash(path)
        return {'session': str(session), 'turn': short_hash(str(prompt_id or turn_id)),
                'changes': changes, 'paths': sorted(changes)}
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None
