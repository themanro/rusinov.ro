#!/usr/bin/env python3
"""Build index.html from content/site.md + tools/template.html.

site.md sections:
  ## hero   - bio paragraph(s)
  ## now    - the one-line "now" (without the leading "now —")
  ## pile   - entries: "### caption" followed by optional fields:
                image: /uploads/foo.jpg     -> image entry
                video: https://youtu.be/ID  -> inline YouTube embed
                pinned: yes                 -> floats to top (max 3)
                circa: 2008                 -> "(circa 2008)" tag once 10+ yrs old
              an entry with no image/video renders as a text line.
Markdown: [text](url), **bold**, _italic_. Blank line = paragraph break.

Content mistakes never kill the build: bad fields degrade to warnings and
the entry renders as text, so a typo can't take the site down.
Stdlib only. Run: python3 tools/build.py
"""
import html as html_mod
import os, re, struct, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, "content", "site.md")
TEMPLATE = os.path.join(ROOT, "tools", "template.html")
HTML = os.path.join(ROOT, "index.html")

warnings = []
def warn(msg):
    warnings.append(msg)
    print(f"  warning: {msg}")


# ---------- tiny markdown ----------

def _link(m):
    text, url = m.group(1), m.group(2)
    target = ' target="_blank"' if url.startswith("http") else ""
    return f'<a href="{url}"{target}>{text}</a>'

def md_inline(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*_(.+?)_\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w&])_(.+?)_(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link, text)
    return text

def md_plain(text):
    """Caption as plain text (for alt attributes)."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\*\*|__|(?<![\w])_|_(?![\w])", "", text)
    return html_mod.escape(text.strip(), quote=True)

def paragraphs(text):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return "\n\n".join(f"<p>{md_inline(p).replace(chr(10), '<br>')}</p>" for p in paras)


# ---------- site.md parsing ----------

def parse_md(path):
    body = open(path, encoding="utf-8").read()
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
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

FIELDS = ("image", "video", "pinned", "circa")

def parse_entries(text):
    entries, cur = [], None
    for line in text.split("\n"):
        m = re.match(r"^###\s+(.*)$", line)
        if m:
            if cur:
                entries.append(cur)
            cur = {"caption": m.group(1).strip(), "fields": {}}
            continue
        if cur is None or not line.strip():
            continue
        f = re.match(r"^(\w+):\s*(.+?)\s*$", line)
        if f and f.group(1) in FIELDS:
            cur["fields"][f.group(1)] = f.group(2)
        else:
            warn(f'unrecognized line under "{cur["caption"][:40]}": {line.strip()[:60]!r} (ignored)')
    if cur:
        entries.append(cur)
    return entries


# ---------- images ----------

def imgsize(path):
    """(width, height) of a PNG/JPEG/GIF without deps; None if unknown."""
    try:
        with open(path, "rb") as f:
            head = f.read(6)
            if head.startswith(b"\x89PN"):
                f.seek(16)
                return struct.unpack(">II", f.read(8))
            if head.startswith(b"GIF8"):
                f.seek(6)
                return struct.unpack("<HH", f.read(4))
            if head.startswith(b"\xff\xd8"):
                f.seek(2)
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

def resolve_image(ref):
    """Return (web_path, fs_path) or (None, None). Maps .heic refs to the
    converted .jpg, tolerates missing leading slash."""
    ref = ref if ref.startswith("/") else "/" + ref
    fs = os.path.join(ROOT, ref.lstrip("/"))
    if os.path.exists(fs):
        return ref, fs
    # self-heal: a ref whose extension changed during upload processing
    # (heic/png -> jpg) still resolves to the produced file.
    stem, ext = os.path.splitext(ref)
    if ext.lower() in (".heic", ".heif", ".png", ".webp", ""):
        alt = stem + ".jpg"
        alt_fs = os.path.join(ROOT, alt.lstrip("/"))
        if os.path.exists(alt_fs):
            return alt, alt_fs
    return None, None


# ---------- pile rendering ----------

def youtube_id(url):
    m = re.search(r"(?:youtu\.be/|[?&]v=|/embed/)([\w-]{6,})", url)
    return m.group(1) if m else None

MAX_PINNED = 3

def render_pile(text):
    import datetime
    this_year = datetime.date.today().year
    entries = parse_entries(text)
    pinned = [e for e in entries if e["fields"].get("pinned", "").lower() in ("yes", "true", "1")]
    if len(pinned) > MAX_PINNED:
        warn(f"{len(pinned)} pinned entries, only the first {MAX_PINNED} stay pinned")
        pinned = pinned[:MAX_PINNED]
    rest = [e for e in entries if e not in pinned]
    blocks = []
    for e in pinned + rest:
        cap = md_inline(e["caption"])
        alt = md_plain(e["caption"])
        circa = e["fields"].get("circa")
        if circa and circa.isdigit() and this_year - int(circa) >= 10:
            cap += f' <span class="circa">(circa {circa})</span>'
        pin_cls = " pinned" if e in pinned else ""
        image, video = e["fields"].get("image"), e["fields"].get("video")

        if video:
            vid = youtube_id(video)
            if not vid:
                warn(f"unrecognized video url (YouTube only): {video} — rendered as text")
                blocks.append(f'  <p class="say{pin_cls}">{cap}</p>')
                continue
            blocks.append(
                f'  <div class="entry{pin_cls}">\n    <div class="vid"><iframe src="https://www.youtube.com/embed/{vid}" '
                f'loading="lazy" allowfullscreen title="{alt}"></iframe></div>\n'
                f'    <p class="cap">{cap}</p>\n  </div>')
        elif image:
            web, fs = resolve_image(image)
            if not web:
                warn(f"image not found: {image} — entry rendered as text")
                blocks.append(f'  <p class="say{pin_cls}">{cap}</p>')
                continue
            src = urllib.parse.quote(web, safe="/")
            size = imgsize(fs)
            dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
            blocks.append(
                f'  <div class="entry{pin_cls}">\n    <img src="{src}"{dims} alt="{alt}" loading="lazy" decoding="async">\n'
                f'    <p class="cap">{cap}</p>\n  </div>')
        else:
            blocks.append(f'  <p class="say{pin_cls}">{cap}</p>')
    return "\n\n".join(blocks), len(blocks)


# ---------- build ----------

def main():
    sections = parse_md(MD)
    for required in ("hero", "now", "pile"):
        if required not in sections:
            raise SystemExit(f"content/site.md is missing the ## {required} section")
    page = open(TEMPLATE, encoding="utf-8").read()
    page = page.replace("{{hero}}", paragraphs(sections["hero"]))
    page = page.replace("{{now}}", md_inline(sections["now"]))
    pile_html, n = render_pile(sections["pile"])
    page = page.replace("{{pile}}", pile_html)
    open(HTML, "w", encoding="utf-8").write(page)
    status = f", {len(warnings)} warning(s)" if warnings else ""
    print(f"built index.html: hero ok, now ok, pile {n} entries{status}")

if __name__ == "__main__":
    main()
