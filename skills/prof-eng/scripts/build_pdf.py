#!/usr/bin/env python3
"""Build the PDF versions of prof-eng Markdown files and check their layout.

Usage: build_pdf.py <file.md>... [--subject DIR]
       build_pdf.py --stale [<file.md>...] [--subject DIR]
       build_pdf.py --all [--subject DIR]

Files with a PDF version: see md_to_tex.py. For each file, md_to_tex.py writes
pdf/<same path>.tex, latexmk -pdf (or pdflatex, rerun until the references
settle) compiles it with its auxiliary files in .prof-eng-build/, and the PDF
is copied to pdf/<same path>.pdf. Then the layout is checked:
- the log: errors, Overfull \\vbox, Overfull \\hbox wider than 2pt, tcolorbox
  warnings, undefined or duplicate labels;
- the pages (needs pdftotext and pdfinfo from poppler): a heading as the last
  line of a page, and a page less than 60% full that is not followed by an
  intentional \\clearpage (usually a callout, table or figure that did not fit
  below).
--stale builds only files whose PDF is missing or older than the .md or the
document template (_templates/document.tex); with files given, only the stale
ones among them. --all builds every file with a PDF version.

Output: one line per file, `<file.md>: ok | layout-warnings | failed |
not-compiled`, then its problems and notes indented. Line numbers in compile
problems refer to pdf/<file>.tex: fix the .md, the .tex is regenerated.
Exit codes: 0 all ok; 1 a file failed or has layout warnings; 2 no latexmk or
pdflatex installed (the .tex files are still written) or a usage error.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from md_to_tex import find_template, in_scope, mirror_path  # noqa: E402

HBOX_LIMIT_PT = 2.0
FILL_MIN = 0.6  # a shorter page before a non-intentional break is reported
BP_PER_SP = 72 / 72.27 / 65536
BP_PER_PT = 72 / 72.27
SCOPE_DIRS = ("", "notes", "cheatsheets", "solutions")
NO_LATEX = ("LaTeX not found (latexmk or pdflatex): the .tex files are written but not compiled. "
            "Install TeX Live (Linux), MacTeX (macOS) or MiKTeX (Windows), or compile on Overleaf: "
            "upload the .tex together with the images it uses (notes/img/, .prof-eng-build/mermaid/), "
            "keeping the same folder layout (pdf/notes/..., notes/img/...).")

HBOX_RE = re.compile(r"^Overfull \\hbox \(([\d.]+)pt too wide\) (?:in paragraph|in alignment|detected) "
                     r"at lines? (\d+)(?:--(\d+))?")
VBOX_RE = re.compile(r"^Overfull \\vbox \(([\d.]+)pt too high\)")
WARNING_RES = (
    (re.compile(r"^Package tcolorbox Warning: (.*)"), "tcolorbox: {}"),
    (re.compile(r"^LaTeX Warning: Reference `([^']*)' on page \d+ undefined"), "undefined reference {}"),
    (re.compile(r"^LaTeX Warning: Label `([^']*)' multiply defined"), "label {} defined twice"),
    (re.compile(r"name\{([^}]*)\} has been referenced but does not exist"), "link to a missing destination {}"),
)
RERUN_RE = re.compile(r"Rerun to |may have changed\.\s+Rerun")
TEXTAREA_RE = re.compile(r"prof-eng: textarea top=([\d.]+)pt\s+height=([\d.]+)pt")
HEADING_MARK_RE = re.compile(r"prof-eng-heading: page=(\d+) y=(-?\d+)")
TEX_HEADING_RE = re.compile(r"^\\(?:sub){0,2}section\{", re.M)
PAGE_RE = re.compile(r'<page width="[\d.]+" height="([\d.]+)">(.*?)</page>', re.S)
LINE_RE = re.compile(r'<line xMin="[\d.]+" yMin="([\d.]+)" xMax="[\d.]+" yMax="([\d.]+)">(.*?)</line>', re.S)
WORD_RE = re.compile(r"<word [^>]*>(.*?)</word>")
DEST_RE = re.compile(r'^\s*(\d+)\s+\[[^\]]*\]\s+"(.*)"\s*$')


def say(text="", indent=0):
    print(" " * indent + text, flush=True)


def scope_files(subject):
    """Every Markdown file of the subject that has a PDF version (relative paths)."""
    found = []
    for folder in SCOPE_DIRS:
        path = os.path.join(subject, folder)
        if os.path.isdir(path):
            found += [os.path.join(folder, name).replace(os.sep, "/") for name in os.listdir(path)
                      if in_scope(os.path.join(folder, name))]
    return sorted(found)


def is_stale(subject, rel, template):
    pdf = mirror_path(subject, rel, ".pdf")
    if not os.path.isfile(pdf):
        return True
    newest = max(os.path.getmtime(os.path.join(subject, rel)), os.path.getmtime(template))
    return os.path.getmtime(pdf) < newest


def excerpt(tex_lines, first, last=None, width=110):
    text = " ".join(line.strip() for line in tex_lines[first - 1:(last or first)])
    return text if len(text) <= width else text[:width - 3] + "..."


# ---- compiling ----

def latex_tool():
    return shutil.which("latexmk") or shutil.which("pdflatex")


def compile_tex(tool, tex, build_dir):
    """Compile tex into build_dir; return (returncode, log text, tool output)."""
    os.makedirs(build_dir, exist_ok=True)
    folder, name = os.path.split(tex)
    log_path = os.path.join(build_dir, os.path.splitext(name)[0] + ".log")
    common = ["-interaction=nonstopmode", "-halt-on-error"]
    if os.path.basename(tool).startswith("latexmk"):
        runs = [[tool, "-pdf", "-g", *common, f"-outdir={build_dir}", name]]
    else:
        runs = [[tool, *common, f"-output-directory={build_dir}", name]] * 4
    output = ""
    log = ""
    for cmd in runs:
        try:
            result = subprocess.run(cmd, cwd=folder, capture_output=True, text=True, errors="replace",
                                    timeout=600)
            code, output = result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            code, output = 1, f"{os.path.basename(tool)} did not finish within 10 minutes"
        try:
            with open(log_path, encoding="latin-1") as fh:
                log = fh.read()
        except OSError:
            log = ""
        if code or not RERUN_RE.search(log):  # pdflatex: run again while labels or page totals change
            break
    return code, log, output


def compile_errors(log, tex_rel, output):
    """The first TeX error with its line, or the tail of the tool's output."""
    lines = log.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("! "):
            context = lines[i + 1:i + 8]
            at = next((n for n, c in enumerate(context) if re.match(r"l\.\d+", c)), None)
            if at is None:
                return [f"{tex_rel}: {line[2:]}"] + [c for c in context if c.strip()][:3]
            number = re.match(r"l\.(\d+)", context[at]).group(1)
            return [f"{tex_rel}:{number}: {line[2:]}"] + [c for c in context[:at + 2] if c.strip()]
    tail = [line for line in output.splitlines() if line.strip()][-6:]
    return [f"{tex_rel}: compile failed, no TeX error in the log"] + tail


def log_problems(log, tex_lines, tex_rel):
    problems = []
    for line in log.splitlines():
        match = HBOX_RE.match(line)
        if match:
            if float(match.group(1)) > HBOX_LIMIT_PT:
                first = int(match.group(2))
                problems.append(f"{tex_rel}:{first}: line {float(match.group(1)):.1f}pt too wide: "
                                f"{excerpt(tex_lines, first, int(match.group(3) or first))}")
            continue
        match = VBOX_RE.match(line)
        if match:
            problems.append(f"{tex_rel}: a block is {float(match.group(1)):.1f}pt taller than the page "
                            "(a callout, table or figure longer than one page: split it)")
            continue
        for pattern, message in WARNING_RES:
            match = pattern.search(line)
            if match:
                problems.append(f"{tex_rel}: {message.format(match.group(1).strip())}")
                break
    return list(dict.fromkeys(problems))


# ---- page checks ----

def text_lines(pdf, top, height):
    """Per page: (page height, [(yMin, yMax, text)] of the lines inside the text area)."""
    out = subprocess.run(["pdftotext", "-bbox-layout", pdf, "-"], capture_output=True, text=True,
                         errors="replace", check=True, timeout=300).stdout
    pages = []
    for page in PAGE_RE.finditer(out):
        lines = []
        for line in LINE_RE.finditer(page.group(2)):
            y_min, y_max = float(line.group(1)), float(line.group(2))
            # the last line's descenders reach below the text area: compare its top
            if y_max < top or y_min > top + height:
                continue
            words = [w.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
                     for w in WORD_RE.findall(line.group(3))]
            lines.append((y_min, y_max, " ".join(words)))
        pages.append((float(page.group(1)), sorted(lines)))
    return pages


def intentional_breaks(pdf, tex_text):
    """Pages (1-based) that start with a \\clearpage of the converter or a \\docpart."""
    labels = set(re.findall(r"\\clearpage\s*\n\s*\\(?:sub){0,2}section\{.*\}\\label\{([^{}]*)\}\s*$",
                            tex_text, re.M))
    labels |= set(re.findall(r"^\\docpart\{.*\}\{([^{}]*)\}\s*$", tex_text, re.M))
    if not labels:
        return set()
    out = subprocess.run(["pdfinfo", "-dests", pdf], capture_output=True, text=True, errors="replace",
                         timeout=120).stdout
    pages = set()
    for line in out.splitlines():
        match = DEST_RE.match(line)
        if match and match.group(2) in labels:
            pages.add(int(match.group(1)))
    return pages


def page_problems(pdf, log, tex_text):
    """(problems, notes) from the page positions of text and headings."""
    if not (shutil.which("pdftotext") and shutil.which("pdfinfo")):
        return [], ["pdftotext or pdfinfo (poppler) not installed: page checks skipped"]
    area = TEXTAREA_RE.search(log)
    if not area:
        return [], ["the template does not log its text area: page checks skipped "
                    "(copy the prof-eng lines from the skill's templates/document.tex)"]
    top, height = float(area.group(1)) * BP_PER_PT, float(area.group(2)) * BP_PER_PT
    marks = [(int(p), int(y)) for p, y in HEADING_MARK_RE.findall(log)]
    notes = []
    if not marks and TEX_HEADING_RE.search(tex_text):
        notes.append("the template has no \\docheadingmark: check for headings at the bottom of a page skipped")
    pages = text_lines(pdf, top, height)
    return check_pages(pages, top, height, marks, intentional_breaks(pdf, tex_text)), notes


def check_pages(pages, top, height, marks, forced):
    """Layout problems. pages: (height, [(yMin, yMax, text)]) per page, in bp from the top;
    top, height: the text area; marks: (page, last baseline in sp from the bottom) per
    heading; forced: pages that start after an intentional \\clearpage."""
    problems = []
    for page, y_sp in marks:
        if page >= len(pages):
            continue  # the last page may end with anything
        page_height, lines = pages[page - 1]
        baseline = page_height - y_sp * BP_PER_SP
        if not any(y_min > baseline for y_min, _, _ in lines):
            heading = next((text for y_min, y_max, text in lines if y_min <= baseline <= y_max + 1), "")
            problems.append(f'page {page} ends with the heading "{heading}"')
    for index in range(len(pages) - 1):
        if index + 2 in forced:
            continue
        lines = pages[index][1]
        fill = (max(y_max for _, y_max, _ in lines) - top) / height if lines else 0.0
        if fill < FILL_MIN:
            following = pages[index + 1][1]
            first = following[0][2] if following else ""
            problems.append(f'page {index + 1} is only {fill:.0%} full: what starts page {index + 2} '
                            f'("{first[:60]}") did not fit below; shorten or split that block')
    return problems


# ---- one file ----

def build(subject, rel, tool):
    """(status, detail lines) for one Markdown file."""
    md = os.path.join(subject, rel)
    convert = subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "md_to_tex.py"), md, "--subject", subject],
                             capture_output=True, text=True, errors="replace", timeout=600)
    details = [line for line in convert.stderr.splitlines() if line.strip()]
    if convert.returncode:
        return "failed", details
    tex = mirror_path(subject, rel, ".tex")
    tex_rel = os.path.relpath(tex, subject).replace(os.sep, "/")
    if not tool:
        return "not-compiled", details + [f"wrote {tex_rel}"]
    build_dir = os.path.join(subject, ".prof-eng-build", os.path.dirname(rel))
    code, log, output = compile_tex(tool, tex, build_dir)
    built = os.path.join(build_dir, os.path.splitext(os.path.basename(rel))[0] + ".pdf")
    if code or not os.path.isfile(built):
        return "failed", details + compile_errors(log, tex_rel, output)
    pdf = mirror_path(subject, rel, ".pdf")
    shutil.copyfile(built, pdf + ".part")
    os.replace(pdf + ".part", pdf)
    with open(tex, encoding="utf-8") as fh:
        tex_text = fh.read()
    problems = log_problems(log, tex_text.splitlines(), tex_rel)
    try:
        more, notes = page_problems(pdf, log, tex_text)
    except (subprocess.SubprocessError, OSError) as exc:
        more, notes = [], [f"page checks failed: {exc}"]
    problems += more
    details += [f"note: {note}" for note in notes]
    pdf_rel = os.path.relpath(pdf, subject).replace(os.sep, "/")
    return ("layout-warnings" if problems else "ok"), problems + details + [f"wrote {pdf_rel}"]


def main():
    parser = argparse.ArgumentParser(description="Build and check the PDF versions of prof-eng Markdown files.")
    parser.add_argument("files", nargs="*", help="Markdown files (paths relative to the current directory)")
    parser.add_argument("--subject", default=".", help="subject folder (default: current directory)")
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--stale", action="store_true", help="only files whose PDF is missing or out of date")
    which.add_argument("--all", action="store_true", help="every file with a PDF version")
    args = parser.parse_args()
    if args.all and args.files:
        parser.error("--all takes no files")
    if not (args.files or args.stale or args.all):
        parser.error("give Markdown files, --stale or --all")
    subject = os.path.abspath(args.subject)
    if args.files:
        rels = [os.path.relpath(os.path.abspath(f), subject).replace(os.sep, "/") for f in args.files]
    else:
        rels = scope_files(subject)
    template, fallback = find_template(subject)

    results = []
    for rel in rels:
        if not os.path.isfile(os.path.join(subject, rel)):
            results.append((rel, "failed", [f"no such file: {rel}"]))
        elif rel.startswith("../") or not in_scope(rel):
            results.append((rel, "failed", [f"{rel} has no PDF version (only notes, cheatsheets, exam and "
                                            "homework solutions, EXAM-SHEET.md and EXAM-SHEET-print.md)"]))
        elif args.stale and not is_stale(subject, rel, template):
            continue
        else:
            results.append((rel, None, None))
    if not results:
        say("nothing to build: every PDF is newer than its .md and the document template")
        return 0

    tool = latex_tool()
    counts = {}
    for rel, status, details in results:
        if status is None:
            status, details = build(subject, rel, tool)
        if fallback:
            details = [d for d in details if not d.startswith("note: _templates/document.tex is missing")]
        counts[status] = counts.get(status, 0) + 1
        say(f"{rel}: {status}")
        for line in details:
            say(line, indent=2)
    if fallback:
        say(f"note: _templates/document.tex is missing, used {template}")
    if "not-compiled" in counts:
        say(NO_LATEX)
    say(f"{len(results)} file{'s' if len(results) != 1 else ''}: "
        + ", ".join(f"{n} {status}" for status, n in sorted(counts.items())))
    if counts.get("failed") or counts.get("layout-warnings"):
        return 1
    return 2 if counts.get("not-compiled") else 0


if __name__ == "__main__":
    sys.exit(main())
