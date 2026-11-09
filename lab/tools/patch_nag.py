#!/usr/bin/env python3
"""Disable the "No valid subscription" login dialog in the Proxmox web UI (lab use only).

Usage: patch_nag.py [--quiet] [path-to-proxmoxlib.js]
Rewrites `Ext.Msg.show({ title: gettext('No valid sub...` to `void({ //Ext.Msg.show({ ...`, which
turns the dialog call into a harmless object literal. Idempotent. Exit 0 = patched or already patched,
1 = dialog code not recognised (file untouched, never guessed), 2 = file unreadable.
`apt-get install --reinstall proxmox-widget-toolkit` reverts it.
"""
import os
import re
import sys
import tempfile

DEFAULT_JS = "/usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js"
_DIALOG = re.compile(r"(Ext\.Msg\.show\(\{\s+title: gettext\('No valid sub)")
_PATCHED = "void({ //Ext.Msg.show({"


def patch_text(text):
    """Return (new_text, changed). new_text is None if the dialog code isn't recognised."""
    if _PATCHED in text:
        return text, False
    if not _DIALOG.search(text):
        return None, False
    return _DIALOG.sub(r"void({ //\1", text), True


def _write_atomically(path, text):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, os.stat(path).st_mode & 0o7777)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def main(argv):
    args = [a for a in argv[1:] if a != "--quiet"]
    quiet = "--quiet" in argv[1:]
    path = args[0] if args else DEFAULT_JS
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"cannot read {path}: {e.strerror}", file=sys.stderr)
        return 2
    new, changed = patch_text(text)
    if new is None:
        print(f"{path}: subscription dialog not recognised; not patching", file=sys.stderr)
        return 1
    if changed:
        _write_atomically(path, new)
    if not quiet:
        print(f"{path}: {'patched' if changed else 'already patched'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
