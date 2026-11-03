#!/usr/bin/env python3
"""Turn every saved Claude Code chat of this project into one readable Markdown file each, plus an index.
Keeps: the user's messages, the assistant's replies, messages between sessions, earlier-conversation summaries.
Drops: tool calls and their output, hidden reasoning, system reminders, task notifications, subagent threads.
usage: python3 tools/chats_to_md.py <transcripts dir> <output dir>
The transcripts dir is Claude Code's folder for this project, ~/.claude/projects/<the project path with / as ->/
(on the owner's Mac: ~/.claude/projects/-Users-kiwimango-Downloads-Dungeon-Master-master). Its .jsonl files are the raw
chats, archived ones included. Example:
  python3 tools/chats_to_md.py ~/.claude/projects/-Users-kiwimango-Downloads-Dungeon-Master-master handoff-chats"""
import json, os, re, sys
from datetime import datetime

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

STRIP = [
    re.compile(r"<system-reminder[^>]*>.*?</system-reminder[^>]*>", re.S),
    re.compile(r"<task-notification>.*?</task-notification>", re.S),
    re.compile(r"<local-command-(?:caveat|stdout|stderr)>.*?</local-command-(?:caveat|stdout|stderr)>", re.S),
    re.compile(r"<command-(?:message|args)>.*?</command-(?:message|args)>", re.S),
    re.compile(r"<artifact-content-authored-by-others/>"),
]
CMD = re.compile(r"<command-name>(.*?)</command-name>", re.S)
XSESS = re.compile(r'<cross-session-message[^>]*from-name="([^"]*)"[^>]*>(.*?)</cross-session-message>', re.S)
PASTE = re.compile(r"</?pasted_content[^>]*>")

def clean_user(text):
    for r in STRIP:
        text = r.sub("", text)
    text = CMD.sub(lambda m: f"(ran {m.group(1).strip()})", text)
    text = PASTE.sub("", text)
    return text.strip()

def text_blocks(content, kinds=("text",)):
    if isinstance(content, str):
        return [content]
    out = []
    for b in content or []:
        if isinstance(b, dict) and b.get("type") in kinds and b.get("text"):
            out.append(b["text"])
    return out

def when(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts or ""

chats = []
for name in sorted(os.listdir(SRC)):
    if not name.endswith(".jsonl"):
        continue
    path = os.path.join(SRC, name)
    title = None
    first_user = None
    entries = []   # (role, time, text)
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            head = line[:400]
            if '"custom-title"' in head or '"agent-name"' in head:
                try:
                    d = json.loads(line)
                    title = d.get("customTitle") or d.get("agentName") or title
                except Exception:
                    pass
                continue
            if '"type":"user"' not in line and '"type":"assistant"' not in line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("type") not in ("user", "assistant") or d.get("isSidechain") or d.get("isMeta"):
                continue
            msg = d.get("message") or {}
            ts = d.get("timestamp", "")
            if d["type"] == "user":
                for raw in text_blocks(msg.get("content")):
                    if raw.startswith("This session is being continued from a previous conversation"):
                        entries.append(("summary", ts, raw.strip()))
                        continue
                    xs = XSESS.findall(raw)
                    if xs:
                        for who, body in xs:
                            entries.append(("session:" + who, ts, body.strip()))
                        raw = XSESS.sub("", raw)
                    t = clean_user(raw)
                    if t:
                        entries.append(("user", ts, t))
                        if first_user is None:
                            first_user = t
            else:
                t = "\n\n".join(x.strip() for x in text_blocks(msg.get("content")) if x.strip())
                if t:
                    if entries and entries[-1][0] == "assistant":
                        r, ts0, t0 = entries[-1]
                        entries[-1] = (r, ts0, t0 + "\n\n" + t)
                    else:
                        entries.append(("assistant", ts, t))
    if not entries:
        continue
    if not title:
        title = (first_user or name).splitlines()[0][:70]
    chats.append((entries[0][1], entries[-1][1], title, name, entries))

chats.sort(key=lambda c: c[0])
index = []
for i, (t0, t1, title, name, entries) in enumerate(chats, 1):
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower()[:60] or "chat"
    fname = f"{i:02d}-{slug}.md"
    n_user = sum(1 for e in entries if e[0] == "user")
    lines = [f"# {title}", "", f"- Dates: {when(t0)} to {when(t1)}", f"- Messages from the user: {n_user}",
             f"- Transcript file: `{name}` (Claude Code session)", "",
             "Tool calls, their output, hidden reasoning and system notes are left out; messages between sessions are kept.", ""]
    for role, ts, text in entries:
        if role == "user":
            lines += [f"## User ({when(ts)})", "", text, ""]
        elif role == "assistant":
            lines += [f"### Claude ({when(ts)})", "", text, ""]
        elif role == "summary":
            lines += [f"### Summary of the earlier part of this chat ({when(ts)})", "", text, ""]
        else:
            lines += [f"### Message from the session \"{role[8:]}\" ({when(ts)})", "", text, ""]
    body = "\n".join(lines)
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
        f.write(body)
    index.append((fname, title, when(t0), when(t1), n_user, len(body.encode("utf-8"))))

with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as f:
    f.write("# All project chats (Claude Code), 2026-10-17 to 2026-10-26\n\n")
    f.write("Every Claude Code chat run in this project's folder, one Markdown file each, oldest first. Each keeps the\n"
            "user's messages, Claude's replies and messages between sessions; tool calls and their output, hidden reasoning\n"
            "and system notes are left out. Start with ../HANDOFF_2026-10-26.md for where things stand.\n\n")
    f.write("| # | Chat | From | To | User messages | Size |\n|---|---|---|---|---|---|\n")
    for fname, title, a, b, n, size in index:
        f.write(f"| [{fname[:2]}]({fname}) | {title.replace('|', '/')} | {a} | {b} | {n} | {size // 1024} KB |\n")
print(len(index), "chats;", sum(x[5] for x in index) // 1024, "KB in all")
