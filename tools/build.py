#!/usr/bin/env python3
"""Rebuild content regions of index.html from content/site.md.

Editable regions in index.html are marked with data-edit="<key>" attributes.
This script parses content/site.md and replaces each region's inner HTML.
Run from anywhere: python3 tools/build.py
No dependencies beyond the Python standard library.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, "content", "site.md")
HTML = os.path.join(ROOT, "index.html")


# ---------- markdown (tiny dialect: links, bold, italic, line breaks) ----------

def _link(m):
    text, url = m.group(1), m.group(2)
    target = ' target="_blank"' if url.startswith("http") else ""
    return f'<a href="{url}"{target}>{text}</a>'

def md_inline(text):
    # order matters: emphasis runs before links so the underscores in
    # generated attributes (target="_blank") are never touched
    text = text.replace("&", "&amp;")
    text = re.sub(r"\*\*_(.+?)_\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w&])_(.+?)_(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link, text)
    return text

def block_html(text):
    """Blank line -> paragraph break, single newline -> line break."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return " <br/><br/>".join(md_inline(p).replace("\n", "<br/>") for p in paras)


# ---------- site.md parsing ----------

def parse_md(path):
    body = open(path, encoding="utf-8").read()
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)  # strip html comments
    sections, key, buf = {}, None, []
    for line in body.split("\n"):
        m = re.match(r"^##\s+(\w+)\s*$", line)
        if m:
            if key:
                sections[key] = "\n".join(buf).strip()
            key, buf = m.group(1), []
        elif key:
            buf.append(line)
    if key:
        sections[key] = "\n".join(buf).strip()
    return sections

def parse_writeups(text):
    """### LABEL | Name | optional-tag, followed by body lines."""
    entries, cur = [], None
    for line in text.split("\n"):
        m = re.match(r"^###\s+(.+)$", line)
        if m:
            if cur:
                entries.append(cur)
            parts = [p.strip() for p in m.group(1).split("|")]
            cur = {"label": parts[0],
                   "name": parts[1] if len(parts) > 1 else "",
                   "tag": parts[2] if len(parts) > 2 else "",
                   "body": []}
        elif cur is not None:
            cur["body"].append(line)
    if cur:
        entries.append(cur)
    for e in entries:
        e["body"] = "\n".join(e["body"]).strip()
    return entries


# ---------- region replacement (balanced-tag aware) ----------

def find_region(src, key):
    """Return (inner_start, inner_end) of the element with data-edit=key."""
    m = re.search(rf'<(\w+)[^>]*data-edit="{key}"[^>]*>', src)
    if not m:
        return None
    tag = m.group(1)
    start = m.end()
    depth = 1
    for t in re.finditer(rf"<{tag}\b[^>]*>|</{tag}>", src[start:]):
        depth += 1 if not t.group(0).startswith("</") else -1
        if depth == 0:
            return start, start + t.start()
    raise ValueError(f"unbalanced region: {key}")

def replace_region(src, key, inner):
    pos = find_region(src, key)
    if pos is None:
        print(f"  warning: no data-edit=\"{key}\" region in index.html, skipped")
        return src
    return src[:pos[0]] + inner + src[pos[1]:]


# ---------- build ----------

def main():
    sections = parse_md(MD)
    src = open(HTML, encoding="utf-8").read()

    simple = {
        "hero": lambda t: md_inline(t.strip()),
        "about": block_html,
        "overview": block_html,
        "away": block_html,
    }
    for key, render in simple.items():
        if key in sections:
            src = replace_region(src, key, render(sections[key]))
            print(f"  {key}: ok")

    if "skills" in sections:
        items = [l[2:].strip() for l in sections["skills"].split("\n") if l.startswith("- ")]
        inner = "".join(f'<li class="list-item">{md_inline(i)}</li>' for i in items)
        src = replace_region(src, "skills", inner)
        print(f"  skills: {len(items)} items")

    if "writeups" in sections:
        rows = []
        for e in parse_writeups(sections["writeups"]):
            tag = f'<div class="new-tag">{md_inline(e["tag"])}</div>' if e["tag"] else ""
            rows.append(
                f'<div class="row w-row"><div class="w-col w-col-3">'
                f'<h3>{md_inline(e["label"])}</h3><h4>{md_inline(e["name"])}</h4>{tag}</div>'
                f'<div class="w-col w-col-9"><div>{block_html(e["body"])}</div></div></div>')
        src = replace_region(src, "writeups", "".join(rows))
        print(f"  writeups: {len(rows)} entries")

    open(HTML, "w", encoding="utf-8").write(src)
    print("build complete")

if __name__ == "__main__":
    main()
