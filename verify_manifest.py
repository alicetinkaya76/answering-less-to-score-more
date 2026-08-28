#!/usr/bin/env python3
"""Generate or verify SHA256SUMS.txt for this deposit. Standard library only.

    python3 verify_manifest.py              # verify (exit 0 = intact)
    python3 verify_manifest.py --generate   # rewrite SHA256SUMS.txt

Two kinds of entry:

* Every file **outside** ``results/`` is listed individually as ``<sha256>  <path>``,
  where ``<sha256>`` is the SHA-256 of the file's bytes and ``<path>`` is its POSIX
  path relative to the deposit root.

* ``results/`` holds ~147k small files, so listing each one would add megabytes of
  manifest for little benefit. It is summarised by a single aggregate digest whose
  construction is defined exactly here rather than described in prose:

      h = sha256()
      for each regular file under results/, sorted by POSIX path relative to results/:
          rel  = that relative path, UTF-8 encoded
          data = the file's bytes
          h.update(len(rel).to_bytes(8, "big")  + rel)
          h.update(len(data).to_bytes(8, "big") + data)
      aggregate = h.hexdigest()

  The 8-byte big-endian length prefixes matter: without them a path/content boundary
  is ambiguous and two different trees could collide. An earlier version of this
  manifest described the aggregate in prose only, and a reviewer was unable to
  reproduce the digest from the description. This script is now the definition.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "SHA256SUMS.txt"
RESULTS = "results"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frame(blob: bytes) -> bytes:
    return len(blob).to_bytes(8, "big") + blob


def aggregate_results() -> tuple[int, str]:
    root = ROOT / RESULTS
    h = hashlib.sha256()
    files = sorted(p for p in root.rglob("*") if p.is_file())
    for path in files:
        h.update(frame(path.relative_to(root).as_posix().encode("utf-8")))
        h.update(frame(path.read_bytes()))
    return len(files), h.hexdigest()


def listed_files() -> list[Path]:
    out = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if rel.parts and rel.parts[0] == RESULTS:
            continue
        if rel.name == MANIFEST.name:
            continue
        out.append(p)
    return out


def generate() -> int:
    lines = [
        "# sha256 manifest for this deposit. Generated and verified by verify_manifest.py,",
        "# which is the authoritative definition of both entry kinds (see its docstring).",
        "#",
        "#   python3 verify_manifest.py              # verify",
        "#   python3 verify_manifest.py --generate   # regenerate this file",
        "#",
        "# Files outside results/ are listed individually as '<sha256>  <path>'.",
        "# results/ is summarised by an aggregate digest over every regular file beneath it,",
        "# sorted by POSIX path relative to results/, feeding sha256 with",
        "#     len(path_utf8).to_bytes(8,'big') + path_utf8",
        "#     len(content).to_bytes(8,'big')   + content",
        "# for each file in turn. The length prefixes are part of the definition.",
        "",
    ]
    total = 0
    for p in listed_files():
        total += p.stat().st_size
        lines.append(f"{sha256_file(p)}  {p.relative_to(ROOT).as_posix()}")
    n_res, agg = aggregate_results()
    res_bytes = sum(p.stat().st_size for p in (ROOT / RESULTS).rglob("*") if p.is_file())
    lines += [
        "",
        f"# results/  files={n_res}  aggregate_sha256={agg}",
        f"# deposit total: {len(listed_files()) + n_res} files, {total + res_bytes} bytes",
    ]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST.name}: {len(listed_files())} listed, {n_res} aggregated")
    return 0


def verify() -> int:
    if not MANIFEST.exists():
        print(f"FAIL: {MANIFEST.name} not found", file=sys.stderr)
        return 1
    want_listed: dict[str, str] = {}
    want_files = want_agg = None
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if line.startswith("# results/"):
            for tok in line.split():
                if tok.startswith("files="):
                    want_files = int(tok.split("=", 1)[1])
                elif tok.startswith("aggregate_sha256="):
                    want_agg = tok.split("=", 1)[1]
        if not line or line.startswith("#"):
            continue
        digest, path = line.split("  ", 1)
        want_listed[path] = digest

    bad = 0
    seen = set()
    for p in listed_files():
        rel = p.relative_to(ROOT).as_posix()
        seen.add(rel)
        if rel not in want_listed:
            print(f"  UNLISTED  {rel}")
            bad += 1
        elif sha256_file(p) != want_listed[rel]:
            print(f"  MISMATCH  {rel}")
            bad += 1
    for rel in want_listed.keys() - seen:
        print(f"  MISSING   {rel}")
        bad += 1
    print(f"listed files: {len(want_listed)} expected, {bad} problem(s)")

    n_res, agg = aggregate_results()
    ok_count = want_files is None or n_res == want_files
    ok_agg = want_agg is None or agg == want_agg
    print(f"results/: {n_res} files, aggregate {agg}")
    if not ok_count:
        print(f"  FAIL: expected {want_files} files")
    if not ok_agg:
        print(f"  FAIL: expected aggregate {want_agg}")

    if bad or not ok_count or not ok_agg:
        print("DEPOSIT DOES NOT MATCH ITS MANIFEST")
        return 1
    print("deposit matches its manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(generate() if "--generate" in sys.argv[1:] else verify())
