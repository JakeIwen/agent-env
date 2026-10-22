# Keeping four instruction files aligned

The daily setup has a Claude global and a Codex global on each of two hosts:
a Mac and a Raspberry Pi. The shared sections are working conventions,
`+` commands, terminal handoffs, web-page conventions, local services, code
shape and cross-agent handoffs.

A configuration-maintenance session backs up the globals before changing them.
The Mac copy of the maintenance notes is authoritative, but the session first
compares the remote notes and merges still-valid remote changes. It then edits
the matching sections in all four globals and compares those sections directly.
Shell and tool names are translated by capability: the intent stays the same,
while a headless Linux host gets different commands from a Mac terminal.
An unreachable host is reported as unsynchronized.

Most shared skills have one real directory per host; the other agent's local
skill entry points refer to it. Consolidate has a copied instruction file that
points at the canonical implementation. Skill updates are copied to the other
host and verified by byte comparison or hashes, including supporting files.

This repository is a separate, manually reviewed copy. It contains no links to
live configuration and does not participate in that synchronization. The
private maintenance notes, host inventory and access configuration are omitted.
