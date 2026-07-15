"""
Strips a leading UTF-8 BOM (b'\xef\xbb\xbf') from every text file in the
repo that has one. Safe to run repeatedly -- files without a BOM are
left untouched.

Usage:
    python strip_bom.py            # actually strip them
    python strip_bom.py --check    # just list which files have one, don't touch anything
"""
import os
import sys

EXTENSIONS = (".py", ".json", ".js", ".md", ".toml", ".nk")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".nekova", "dist", "build"}

BOM = b"\xef\xbb\xbf"


def find_bom_files(root="."):
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if not fname.endswith(EXTENSIONS):
                continue
            path = os.path.join(dirpath, fname)
            try:
                with open(path, "rb") as f:
                    if f.read(3) == BOM:
                        hits.append(path)
            except OSError:
                pass
    return hits


def main():
    check_only = "--check" in sys.argv
    hits = find_bom_files()

    if not hits:
        print("No BOM-prefixed files found.")
        return

    for path in hits:
        if check_only:
            print(f"  has BOM: {path}")
            continue
        with open(path, "rb") as f:
            data = f.read()
        with open(path, "wb") as f:
            f.write(data[len(BOM):])
        print(f"  stripped: {path}")

    verb = "Would strip" if check_only else "Stripped"
    print(f"\n{verb} BOM from {len(hits)} file(s).")


if __name__ == "__main__":
    main()