#!/usr/bin/env python3
"""Normalize images dropped into /uploads so phone photos Just Work.

For every image in uploads/:
  - HEIC/HEIF  -> converted to JPEG (original removed)
  - EXIF orientation applied, then ALL metadata stripped (including GPS)
  - resized down to max 1600px wide
  - JPEG re-encoded at quality 82

Idempotent: files that are already clean are left untouched.
GIFs, PDFs and non-images are skipped.

Requires Pillow; pillow-heif needed only for HEIC (guarded).
Runs in CI before every build; safe to run locally too.
"""
import os, sys

try:
    from PIL import Image, ImageOps
except ImportError:
    print("process_uploads: Pillow not installed, skipping upload normalization")
    sys.exit(0)

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF = True
except ImportError:
    HEIF = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS = os.path.join(ROOT, "uploads")
MAX_W = 1600
QUALITY = 82
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif")
HEIC_EXTS = (".heic", ".heif")

def main():
    changed = 0
    for fname in sorted(os.listdir(UPLOADS)):
        path = os.path.join(UPLOADS, fname)
        stem, ext = os.path.splitext(fname)
        ext = ext.lower()
        if not os.path.isfile(path) or ext not in IMAGE_EXTS:
            continue
        if ext in HEIC_EXTS and not HEIF:
            print(f"  warning: {fname} is HEIC but pillow-heif is missing; skipped")
            continue
        try:
            im = Image.open(path)
            im.load()
        except Exception as e:
            print(f"  warning: cannot read {fname}: {e}")
            continue

        has_meta = bool(im.getexif())
        needs = ext in HEIC_EXTS or im.width > MAX_W or has_meta
        if not needs:
            continue

        im = ImageOps.exif_transpose(im)
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)

        if ext == ".png":
            # PNGs stay PNG — they're logos/screenshots/pixel-art, often with
            # transparency. Re-saving without an exif kwarg strips metadata.
            im.save(path, "PNG", optimize=True)
            print(f"  normalized {fname} ({im.width}px PNG, metadata stripped)")
        else:
            # jpg/webp/heic -> jpg
            out = os.path.join(UPLOADS, stem + ".jpg")
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            im.save(out, "JPEG", quality=QUALITY, optimize=True)  # no exif kwarg = stripped
            if out != path:
                os.remove(path)
                print(f"  converted {fname} -> {stem}.jpg ({im.width}px, metadata stripped)")
            else:
                print(f"  normalized {fname} ({im.width}px, metadata stripped)")
        changed += 1
    print(f"process_uploads: {changed} file(s) processed")

if __name__ == "__main__":
    main()
