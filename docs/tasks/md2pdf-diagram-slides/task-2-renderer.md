# Task 2: Diagram renderer with loud failure

Status: [ ]
Spec: `tooling/specs/md2pdf-diagram-slides.md`
File under change: `tools/md2pdf/md2pdf.py`, tests in `tools/md2pdf/test_md2pdf.py`
Depends on: none (parallel with Task 1)

## Objective

Add `render_diagram(lang, source, out_dir, slide_title) -> Path` that writes the diagram source to a temp file in `out_dir`, invokes the correct CLI, and returns the generated image path. Fail loudly on missing CLI, non-zero exit, or timeout.

## Implementation guidance

- **Filename convention (critique E6):** `out_dir / f"diagram_{lang}_{hashlib.sha256(source.encode('utf-8')).hexdigest()[:16]}.{ext}"` — `.pdf` for d2, `.png` for mermaid. If the file already exists, return it immediately (idempotent).
- **Commands (critique E2, E5; white background):**
  - d2: `["d2", "--theme", "0", "--browser", "0", str(src_file), str(out_file)]`
  - mermaid: `["mmdr", "-i", str(src_file), "-o", str(out_file), "-e", "png", "-w", "2400", "-t", "default", "-b", "white"]` (no `-H` — preserve aspect ratio).
- **Subprocess (critique E3, E4):** `subprocess.run(cmd, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)`. Catch `subprocess.TimeoutExpired` → `SystemExit` naming slide title, language, timeout. On `returncode != 0`, decode stderr with `encoding="utf-8", errors="replace"` → `SystemExit` naming the tool, slide title, and diagnostic. Argument lists only; never shell string interpolation.
- **Binary resolution (critique E9):** `shutil.which` first, then fall back to `Path.home()/".cargo"/"bin"/"mmdr.exe"` (mermaid) and `Path.home()/"go"/"bin"/"d2.exe"` (d2). If unresolved → `SystemExit` with install hint (`cargo install mmdr`, `go install oss.terrastruct.com/d2@latest`) and slide title.

## Test requirements

Unit (no CLI needed; mock `subprocess.run` and the resolver):
- Correct command formation per language (flags, filenames, hash-based name).
- `TimeoutExpired` → `SystemExit` naming the timeout.
- Non-zero return with stderr bytes → `SystemExit` carrying decoded diagnostic, tool, slide title.
- Missing binary → `SystemExit` with install hint.

Integration (`skipif` the respective CLI absent):
- Trivial valid d2 → non-empty `.pdf`; trivial valid mermaid → non-empty `.png`.
- Invalid d2/mermaid syntax → `SystemExit` containing slide title, tool, captured stderr.

## Demo

`uv run pytest tools/md2pdf/test_md2pdf.py -k render_diagram -v` — unit cases pass; integration cases pass where `d2`/`mmdr` are installed.
