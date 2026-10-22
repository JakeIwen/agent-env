---
name: codex-artifact
description: Summarize the current conversation as a codex Artifact, a self-contained HTML page saved in ~/.agent/artifacts with a browsable index. Use when the owner writes `+art` (alone, appended to a task, or followed by a focus such as `+art just the wiring findings`), asks for a codex Artifact, or asks to summarize the conversation as a page or artifact. Also use when a reply would run longer than one terminal screen (the long-reply rule in the global instructions; see Long replies).
---

# codex Artifact

`+art [focus]` turns this conversation into one HTML page in the local store.
Anything after `+art` is the focus: cover only that topic. The page is for
the owner coming back days later with no memory of the chat, and for reading on
a phone-width window.

The script that saves pages is `scripts/agent_art.py` next to this file
(`~/.codex/skills/codex-artifact/scripts/agent_art.py`). It wraps the body
you write in the shared template (title header, date/project/agent line,
light and dark styles), saves it, rebuilds `~/.agent/artifacts/index.html`,
and deletes pages untouched for 90 days. Pages in `pinned/` are kept.

## Steps

1. If `+art` came appended to a task, finish the task first, then summarize.
2. Pick a title: a plain name of two to four words (`Codex artifact design`,
   `Service restart verification`), never "Summary of..." or a sentence.
3. Write the body fragment (see Content and Markup) and save it through
   stdin with a quoted heredoc so nothing in the page is expanded:

   ```sh
   python3 ~/.codex/skills/codex-artifact/scripts/agent_art.py save \
     --title "Service restart verification" <<'ART_HTML'
   <h2>Summary</h2>
   ...
   ART_HTML
   ```

   Options: `--slug` overrides the filename slug, `--project` overrides the
   label (default: git toplevel name, else the cwd name), `--agent claude`
   when a Claude agent runs this. To revise a page already saved in this
   conversation, pass `--out <its path>` so it is updated in place instead
   of creating a second page.
4. Don't open a browser. End your final message with the `file://` URL from
   the script's `url:` line as plain text, not a Markdown link, so it stays
   clickable in the terminal. When the script also printed a `mac:` line
   (pages saved on the Pi), give that path too: it opens the page from the
   Mac over the `<shared-volume>` share.

If the save fails with a permission error, the store isn't writable in this
sandbox: report that and the exact error. Don't save the page anywhere else.

Other commands: `list [-n N]` shows recent pages and their paths (use it to
find a page the owner refers to), `pin <path>` moves a page into `pinned/`,
`index` prunes and rebuilds the index.

## Long replies

The global instructions send any reply longer than one terminal screen to
a page instead of the terminal. For those, the page is the reply itself,
not a summary of the conversation:

- Title it after the reply's subject (`Mac sessions on Pi page`).
- Write the reply as you would have in the terminal, under `<h2>`
  sections, with tables, `<pre><code>` blocks, and a `<p class="callout">`
  for each choice or command waiting on the owner. Skip the Content section's
  scaffold; its rules on secrets and unverified claims still apply.
- When a later reply revises the same page (a follow-up that changes the
  plan), pass `--out` to update it; a reply on a new subject gets its own
  page.
- The terminal message still carries what the owner must act on in full, a
  summary of up to five lines, and the link (step 4).

## Content

Use only what happened in the conversation. Mark anything unverified as
unverified. Order the sections as below and leave out any that would be
empty:

- **Summary**: two to four sentences: what was asked and where it ended up.
- **Outcome**: the answer or findings themselves, with the key numbers,
  names, paths, and versions.
- **Decisions**: each choice with its reason; rejected options in one line.
- **Changes**: files created or edited (paths), config, services, commits.
  Use a table when there are more than a few.
- **Verification**: what was checked and the result; what wasn't checked.
- **Open items**: next steps, questions still open, and commands the owner has
  to run himself, each in its own `<pre><code>` block.
- **References**: paths, URLs, and docs the conversation relied on.

Leave out tool chatter, retries that changed nothing, and diffs unless
the owner asked for them. Never include secrets: tokens, passwords, keys,
private URLs with credentials. Redact them as `[redacted]`.

## Markup

- Write a fragment only: no `<html>`, `<head>`, `<body>`, or `<h1>`. The
  template supplies those, and the script rejects a full document.
- Sections are `<h2>`, subsections `<h3>`.
- `<table>` with `<th>` headers for comparisons and inventories,
  `<pre><code>` for commands and config, `<code>` for paths and names,
  `<details><summary>` for long logs.
- Template classes: `<p class="callout">` for the one thing the owner must act
  on; `<span class="ok">`, `<span class="warn">`, `<span class="bad">` for
  status labels.
- No external scripts, fonts, stylesheets, or images by URL. Inline SVG is
  fine for a diagram that explains the mechanism. Add JavaScript only when
  the page needs interaction.
- The Web pages rule in the global instructions applies: no hero, slogan,
  tagline, kicker label, or copy describing the page itself.
- Escape `<`, `>`, and `&` in code and log text (`&lt;`, `&gt;`, `&amp;`).
