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


# ---------- work example cards ----------

CARD_SIZES = "(max-width: 479px) 92vw, (max-width: 767px) 44vw, (max-width: 991px) 45vw, 28vw"
# shared Webflow interaction ids — identical across all cards, drive hover animations
IX_LIGHTBOX = "c1bd08d3-66e5-bb61-06da-da09a92a1c1c"
IX_TEXT = "c1bd08d3-66e5-bb61-06da-da09a92a1c1e"
IX_IMG = "c1bd08d3-66e5-bb61-06da-da09a92a1c21"
IX_MORE = "bbcf335e-1723-b142-da42-929b3baf3f85"
EMBEDLY_KEY = "96f1f04c5f4143bcb0f2e68c87d65feb"

def imgsize(path):
    """Width/height of a PNG or JPEG without external deps. None if unknown."""
    import struct
    try:
        with open(path, "rb") as f:
            head = f.read(2)
            if head == b"\x89P":  # PNG
                f.seek(16)
                w, h = struct.unpack(">II", f.read(8))
                return w, h
            if head == b"\xff\xd8":  # JPEG
                while True:
                    marker = f.read(2)
                    if len(marker) < 2 or marker[0] != 0xFF:
                        return None
                    if 0xC0 <= marker[1] <= 0xCF and marker[1] not in (0xC4, 0xC8, 0xCC):
                        f.read(3)
                        h, w = struct.unpack(">HH", f.read(4))
                        return w, h
                    size = struct.unpack(">H", f.read(2))[0]
                    f.seek(size - 2, 1)
    except Exception:
        pass
    return None

def srcset_for(image):
    """Build a srcset from Webflow-style responsive variants if they exist."""
    full = os.path.join(ROOT, image.lstrip("/"))
    d, fname = os.path.dirname(full), os.path.basename(full)
    stem = re.sub(r"\.[a-z]+$", "", fname, flags=re.I)
    entries = []
    if os.path.isdir(d):
        for f in os.listdir(d):
            m = re.match(re.escape(stem) + r"-p-(\d+)\.[a-z]+$", f, re.I)
            if m:
                entries.append((int(m.group(1)), f"/assets/img/{f}"))
    if not entries:
        return ""
    size = imgsize(full)
    if size:
        entries.append((size[0], image))
    entries.sort()
    ss = ", ".join(f"{u} {w}w" for w, u in entries)
    return f' sizes="{CARD_SIZES}" srcset="{ss}"'

def youtube_id(url):
    m = re.search(r"(?:youtu\.be/|[?&]v=|/embed/)([\w-]{6,})", url)
    return m.group(1) if m else None

def video_json(url):
    import json as _json
    vid = youtube_id(url)
    if not vid:
        raise SystemExit(f"unsupported video url (YouTube only for now): {url}")
    watch = f"https://www.youtube.com/watch?v={vid}"
    thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    import urllib.parse as up
    embed_src = ("//cdn.embedly.com/widgets/media.html?src=" +
                 up.quote(f"https://www.youtube.com/embed/{vid}?feature=oembed", safe="") +
                 "&url=" + up.quote(watch, safe="") +
                 "&image=" + up.quote(thumb, safe="") +
                 f"&key={EMBEDLY_KEY}&type=text%2Fhtml&schema=youtube")
    html_embed = (f'<iframe class="embedly-embed" src="{embed_src}" width="940" height="528" '
                  f'scrolling="no" frameborder="0" allow="autoplay; fullscreen" allowfullscreen="true"></iframe>')
    item = {"url": watch, "originalUrl": watch, "width": 940, "height": 528,
            "thumbnailUrl": thumb, "html": html_embed, "type": "video"}
    return _json.dumps({"items": [item], "group": "works"}), thumb

def render_examples(text):
    import json as _json
    cards = []
    for e in parse_writeups(text):  # same ### parser: label=caption line
        caption = e["label"]
        fields = dict(re.findall(r"^(\w+):\s*(.+)$", e["body"], re.M))
        image, video, page = fields.get("image"), fields.get("video"), fields.get("page")
        if video:
            jsn, thumb = video_json(video)
            src, extra = thumb, ""
        elif image:
            if not image.startswith("/"):
                image = "/" + image
            if not os.path.exists(os.path.join(ROOT, image.lstrip("/"))):
                print(f"  warning: examples image not found: {image}")
            jsn = _json.dumps({"items": [{"url": image, "type": "image"}], "group": "works"})
            src, extra = image, srcset_for(image)
        else:
            print(f"  warning: example '{caption[:40]}' has no image/video, skipped")
            continue
        more = (f'<a data-w-id="{IX_MORE}" href="{page}" class="collection-link">'
                f'More about this project ➔</a>') if page else ""
        textblock = ("" if caption.strip() == "-" else
                     f'<div data-w-id="{IX_TEXT}" class="textblock"><p class="paragraph">{md_inline(caption)}</p></div>')
        cards.append(
            f'<div role="listitem" class="collection-item w-dyn-item"><div class="collection-wrapper">'
            f'<a href="#" data-w-id="{IX_LIGHTBOX}" class="lightbox-link w-inline-block w-lightbox">'
            f'{textblock}'
            f'<img data-w-id="{IX_IMG}" alt="" src="{src}"{extra} class="lightbox-thumbnail"/>'
            f'<script type="application/json" class="w-json">{jsn}</script></a>{more}</div></div>')
    return "".join(cards)


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

    if "examples" in sections:
        inner = render_examples(sections["examples"])
        src = replace_region(src, "examples", inner)
        print(f"  examples: {inner.count('collection-item')} cards")

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
