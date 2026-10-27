"""Tests for scripts/build_pdf.py, which builds and checks the PDF output.

Unit tests feed the log and page checks with synthetic input and run the
command line without LaTeX on PATH (file selection, converter errors, the
not-compiled case). The compile tests (skipped without LaTeX and poppler)
build the sample files of make_fixtures.py and Markdown made to trigger each
layout problem.

Run from the repo root: python3 -m unittest discover tests
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "skills", "prof-eng", "scripts")
TEMPLATE = os.path.join(os.path.dirname(HERE), "skills", "prof-eng", "templates", "document.tex")
sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)

from make_fixtures import SAMPLES, make_subject, write_samples  # noqa: E402
from test_md_to_tex import write  # noqa: E402
import build_pdf  # noqa: E402
import md_to_tex  # noqa: E402


def run(*args, cwd, path=None):
    env = dict(os.environ)
    if path is not None:
        env["PATH"] = path
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, "build_pdf.py"), *args],
                          capture_output=True, text=True, timeout=600, cwd=cwd, env=env)


def statuses(stdout):
    """{file: status} from the unindented `file: status` lines."""
    return dict(re.findall(r"^(\S+\.md): (\S+)$", stdout, re.M))


class TempSubjectTest(unittest.TestCase):
    def setUp(self):
        self.subject = tempfile.mkdtemp(prefix="prof-eng-build-")
        self.empty_path = os.path.join(self.subject, ".no-tools")  # PATH without LaTeX or poppler
        os.mkdir(self.empty_path)

    def tearDown(self):
        shutil.rmtree(self.subject)

    def add(self, rel, text):
        write(os.path.join(self.subject, rel), text, dedent=False)


class LogTest(unittest.TestCase):
    TEX = ["line one", "a very long word here", "third", "fourth"]

    def test_overfull_hbox_above_limit_with_tex_text(self):
        log = ("Overfull \\hbox (1.5pt too wide) in paragraph at lines 1--1\n"
               "Overfull \\hbox (12.34567pt too wide) in paragraph at lines 2--3\n"
               "Overfull \\hbox (8.0pt too wide) in alignment at lines 4--4\n")
        self.assertEqual(build_pdf.log_problems(log, self.TEX, "pdf/x.tex"), [
            "pdf/x.tex:2: line 12.3pt too wide: a very long word here third",
            "pdf/x.tex:4: line 8.0pt too wide: fourth"])

    def test_vbox_tcolorbox_and_references(self):
        log = ("Overfull \\vbox (157.3pt too high) has occurred while \\output is active []\n"
               "Package tcolorbox Warning: Using nobreak failed. Try to enlarge `lines before\n"
               "LaTeX Warning: Reference `ans:2' on page 3 undefined on input line 40.\n"
               "LaTeX Warning: Label `intro' multiply defined.\n"
               "pdfTeX warning (dest): name{q:7} has been referenced but does not exist, replaced by a fixed one\n")
        problems = build_pdf.log_problems(log, self.TEX, "pdf/x.tex")
        self.assertEqual(len(problems), 5, problems)
        self.assertIn("157.3pt taller than the page", problems[0])
        self.assertIn("Using nobreak failed", problems[1])
        self.assertIn("ans:2", problems[2])
        self.assertIn("intro", problems[3])
        self.assertIn("q:7", problems[4])

    def test_compile_error_with_line(self):
        log = ("(./x.tex\n! Undefined control sequence.\n<recently read> \\foo \n"
               "l.314 Text $\\foo\n              x$.\nHere is how much of TeX's memory you used:\n")
        self.assertEqual(build_pdf.compile_errors(log, "pdf/x.tex", ""), [
            "pdf/x.tex:314: Undefined control sequence.", "<recently read> \\foo ",
            "l.314 Text $\\foo", "              x$."])

    def test_compile_failure_without_tex_error(self):
        problems = build_pdf.compile_errors("", "pdf/x.tex", "first\nsecond\nlast words\n")
        self.assertEqual(problems[0], "pdf/x.tex: compile failed, no TeX error in the log")
        self.assertEqual(problems[-1], "last words")


class CheckPagesTest(unittest.TestCase):
    """Synthetic pages: text area from 70 to 770 bp, page height 842 bp."""
    TOP, HEIGHT, PAGE = 70.0, 700.0, 842.0

    def page(self, *rows):
        return (self.PAGE, [(y, y + 12, text) for y, text in rows])

    def mark(self, page, baseline_from_top):
        return (page, round((self.PAGE - baseline_from_top) / build_pdf.BP_PER_SP))

    def check(self, pages, marks=(), forced=()):
        return build_pdf.check_pages(pages, self.TOP, self.HEIGHT, list(marks), set(forced))

    def test_full_pages_pass(self):
        pages = [self.page((70, "Title"), (700, "text")), self.page((70, "more"))]
        self.assertEqual(self.check(pages, [self.mark(1, 80)]), [])

    def test_heading_at_bottom(self):
        pages = [self.page((70, "text"), (700, "Heading")), self.page((70, "body"))]
        self.assertEqual(self.check(pages, [self.mark(1, 710)]), ['page 1 ends with the heading "Heading"'])

    def test_heading_on_last_page_is_fine(self):
        pages = [self.page((700, "text")), self.page((70, "text"), (100, "Heading"))]
        self.assertEqual(self.check(pages, [self.mark(2, 110)]), [])

    def test_underfilled_page(self):
        pages = [self.page((70, "text"), (300, "short")), self.page((70, "Big box title"))]
        self.assertEqual(self.check(pages), ['page 1 is only 35% full: what starts page 2 ("Big box title") '
                                             "did not fit below; shorten or split that block"])

    def test_underfilled_before_intentional_break_and_last_page(self):
        pages = [self.page((70, "statements")), self.page((70, "Solutions")), self.page((70, "end"))]
        self.assertEqual(len(self.check(pages)), 2)
        self.assertEqual(self.check(pages, forced=[2, 3]), [])


class CommandLineTest(TempSubjectTest):
    def test_not_compiled_without_latex(self):
        self.add("notes/L01-x.md", "# L01 – x\n\nText.\n")
        result = run("notes/L01-x.md", cwd=self.subject, path=self.empty_path)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(statuses(result.stdout), {"notes/L01-x.md": "not-compiled"})
        self.assertIn("wrote pdf/notes/L01-x.tex", result.stdout)
        self.assertIn("LaTeX not found", result.stdout)
        self.assertIn("Overleaf", result.stdout)
        self.assertTrue(os.path.isfile(os.path.join(self.subject, "pdf", "notes", "L01-x.tex")))
        self.assertFalse(os.path.exists(os.path.join(self.subject, "pdf", "notes", "L01-x.pdf")))

    def test_converter_error_fails_with_md_line(self):
        self.add("notes/L01-x.md", "# L01\n\nText ==marked==.\n")
        self.add("notes/L02-y.md", "# L02\n\nFine.\n")
        result = run("notes/L01-x.md", "notes/L02-y.md", cwd=self.subject, path=self.empty_path)
        self.assertEqual(result.returncode, 1)  # failed outranks not-compiled
        self.assertEqual(statuses(result.stdout), {"notes/L01-x.md": "failed", "notes/L02-y.md": "not-compiled"})
        self.assertIn("  notes/L01-x.md:3: unsupported Markdown: highlight", result.stdout)
        self.assertIn("2 files: 1 failed, 1 not-compiled", result.stdout)

    def test_missing_and_out_of_scope_files(self):
        self.add("00-index.md", "# Index\n")
        result = run("00-index.md", "notes/none.md", cwd=self.subject, path=self.empty_path)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(statuses(result.stdout), {"00-index.md": "failed", "notes/none.md": "failed"})
        self.assertIn("has no PDF version", result.stdout)
        self.assertIn("no such file: notes/none.md", result.stdout)

    def test_subject_option_and_template_note_once(self):
        self.add("notes/L01-x.md", "# L01\n")
        self.add("cheatsheets/L01-cheatsheet.md", "# L01 cheatsheet\n")
        result = run("--all", "--subject", self.subject, cwd=HERE, path=self.empty_path)
        self.assertEqual(statuses(result.stdout), {"cheatsheets/L01-cheatsheet.md": "not-compiled",
                                                   "notes/L01-x.md": "not-compiled"})
        self.assertEqual(result.stdout.count("_templates/document.tex is missing"), 1)

    def test_usage_errors(self):
        self.assertEqual(run(cwd=self.subject).returncode, 2)
        self.assertEqual(run("--all", "notes/x.md", cwd=self.subject).returncode, 2)
        self.assertEqual(run("--all", "--stale", cwd=self.subject).returncode, 2)


class SelectionTest(TempSubjectTest):
    def setUp(self):
        super().setUp()
        for rel in ("notes/L01-a.md", "cheatsheets/L01-cheatsheet.md", "solutions/exam-2024-jan.md",
                    "solutions/hw-L01.md", "EXAM-SHEET.md", "EXAM-SHEET-print.md",
                    "00-index.md", "progress.md", "solutions/notes.md", "_templates/lecture-note.md",
                    "notes/img/x.md"):
            self.add(rel, "# T\n")

    def test_scope_files(self):
        self.assertEqual(build_pdf.scope_files(self.subject), [
            "EXAM-SHEET-print.md", "EXAM-SHEET.md", "cheatsheets/L01-cheatsheet.md", "notes/L01-a.md",
            "solutions/exam-2024-jan.md", "solutions/hw-L01.md"])

    def test_stale_rule(self):
        template = os.path.join(self.subject, "_templates", "document.tex")
        self.add("_templates/document.tex", "%%BODY%%\n")
        pdf = os.path.join(self.subject, "pdf", "notes", "L01-a.pdf")
        md = os.path.join(self.subject, "notes", "L01-a.md")
        self.assertTrue(build_pdf.is_stale(self.subject, "notes/L01-a.md", template))  # no PDF yet
        self.add("pdf/notes/L01-a.pdf", "")
        tex = f"% Generated by md_to_tex.py (converter {md_to_tex.converter_version()}) from notes/L01-a.md.\n"
        self.add("pdf/notes/L01-a.tex", tex)
        now = time.time()
        os.utime(md, (now - 100, now - 100))
        os.utime(template, (now - 100, now - 100))
        os.utime(pdf, (now - 50, now - 50))
        self.assertFalse(build_pdf.is_stale(self.subject, "notes/L01-a.md", template))
        os.utime(md, (now, now))
        self.assertTrue(build_pdf.is_stale(self.subject, "notes/L01-a.md", template))
        os.utime(md, (now - 100, now - 100))
        os.utime(template, (now, now))
        self.assertTrue(build_pdf.is_stale(self.subject, "notes/L01-a.md", template))
        os.utime(template, (now - 100, now - 100))
        self.add("pdf/notes/L01-a.tex", tex.replace(md_to_tex.converter_version(), "0123456789ab"))
        os.utime(pdf, (now - 50, now - 50))
        self.assertTrue(build_pdf.is_stale(self.subject, "notes/L01-a.md", template))  # skill updated

    def test_stale_command_line(self):
        shutil.copy(TEMPLATE, os.path.join(self.subject, "_templates", "document.tex"))
        old = time.time() - 100
        for rel in build_pdf.scope_files(self.subject):
            self.add(os.path.join("pdf", os.path.splitext(rel)[0] + ".pdf"), "")
            self.add(os.path.join("pdf", os.path.splitext(rel)[0] + ".tex"),
                     f"% Generated by md_to_tex.py (converter {md_to_tex.converter_version()}) from {rel}.\n")
            os.utime(os.path.join(self.subject, rel), (old, old))
        os.utime(os.path.join(self.subject, "_templates", "document.tex"), (old, old))
        result = run("--stale", cwd=self.subject, path=self.empty_path)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("nothing to build", result.stdout)
        os.utime(os.path.join(self.subject, "notes", "L01-a.md"))
        result = run("--stale", cwd=self.subject, path=self.empty_path)
        self.assertEqual(statuses(result.stdout), {"notes/L01-a.md": "not-compiled"})
        result = run("--stale", "EXAM-SHEET.md", "notes/L01-a.md", cwd=self.subject, path=self.empty_path)
        self.assertEqual(statuses(result.stdout), {"notes/L01-a.md": "not-compiled"})


NEEDS_TOOLS = (build_pdf.latex_tool() and shutil.which("pdftotext") and shutil.which("pdfinfo"),
               "needs LaTeX (latexmk or pdflatex) and poppler (pdftotext, pdfinfo)")
TALL_CALLOUT = ("# L03 – gap\n\n" + "".join(f"Paragraph {n} with some words in it.\n" for n in range(15))
                + "\n> [!important] Big box\n" + "".join(f"> Line {n} of a tall callout.\n" for n in range(25)))


@unittest.skipUnless(*NEEDS_TOOLS)
class CompileTest(TempSubjectTest):
    def test_samples_build_clean(self):
        write_samples(make_subject(self.subject, name="."))
        result = run("--all", cwd=self.subject)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(set(statuses(result.stdout).values()), {"ok"}, result.stdout)
        self.assertEqual(len(statuses(result.stdout)), len(SAMPLES))
        made = sorted(os.path.relpath(os.path.join(d, f), self.subject)
                      for d, _, files in os.walk(os.path.join(self.subject, "pdf")) for f in files)
        self.assertEqual(made, sorted(os.path.join("pdf", os.path.splitext(rel)[0] + ext)
                                      for rel in SAMPLES for ext in (".pdf", ".tex")))
        info = subprocess.run(["pdfinfo", os.path.join(self.subject, "pdf", "notes", "L02-rc-circuits.pdf")],
                              capture_output=True, text=True).stdout
        self.assertIn("595.276 x 841.89", info)
        log_path = os.path.join(self.subject, ".prof-eng-build", "notes", "L02-rc-circuits.log")
        with open(log_path, encoding="latin-1") as fh:
            log = fh.read()
        with open(os.path.join(self.subject, "pdf", "notes", "L02-rc-circuits.tex"), encoding="utf-8") as fh:
            headings = len(build_pdf.TEX_HEADING_RE.findall(fh.read()))
        self.assertEqual(len(build_pdf.HEADING_MARK_RE.findall(log)), headings)  # one mark per heading
        # the solutions start on a fresh page after a short page of statements: intentional
        self.assertNotIn("full", result.stdout)

    def test_heading_at_bottom(self):
        # a template whose headings always end their page
        with open(TEMPLATE, encoding="utf-8") as fh:
            template = re.sub(r"(\{0pt\}\{\\docheadingmark\})$", r"\1[\\newpage]", fh.read(), flags=re.M)
        self.add("_templates/document.tex", template)
        self.add("notes/L01-x.md", "# L01\n\nIntro.\n\n## First part\n\nText.\n\n### Second $x^2$\n\nMore.\n")
        result = run("notes/L01-x.md", cwd=self.subject)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('page 1 ends with the heading "First part"', result.stdout)
        self.assertIn('page 2 ends with the heading "Second x 2"', result.stdout)

    def test_underfilled_page_and_overfull_line(self):
        self.add("notes/L03-gap.md", TALL_CALLOUT + "\n" + "x" * 90 + "\n")
        result = run("notes/L03-gap.md", cwd=self.subject)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(statuses(result.stdout), {"notes/L03-gap.md": "layout-warnings"})
        self.assertRegex(result.stdout, r'page 1 is only \d+% full: what starts page 2 \("Big box"\)')
        self.assertRegex(result.stdout, r"pdf/notes/L03-gap\.tex:\d+: line [\d.]+pt too wide: x{40}")
        self.assertTrue(os.path.isfile(os.path.join(self.subject, "pdf", "notes", "L03-gap.pdf")))

    def test_compile_error_keeps_old_pdf(self):
        self.add("notes/L04-err.md", "# L04\n\nText $\\undefinedmacro x$.\n")
        self.add("pdf/notes/L04-err.pdf", "old")
        result = run("notes/L04-err.md", cwd=self.subject)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(statuses(result.stdout), {"notes/L04-err.md": "failed"})
        self.assertRegex(result.stdout, r"pdf/notes/L04-err\.tex:\d+: Undefined control sequence\.")
        with open(os.path.join(self.subject, "pdf", "notes", "L04-err.pdf"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "old")

    def test_template_without_markers(self):
        with open(TEMPLATE, encoding="utf-8") as fh:
            template = fh.read()
        template = template.replace(r"{0pt}{\docheadingmark}", "{0pt}{}")
        template = re.sub(r"%\n  \\typeout\{prof-eng: textarea.*?\}\}", "}", template, flags=re.S)
        self.assertNotIn("textarea", template)
        self.add("_templates/document.tex", template)
        self.add("notes/L01-x.md", "# L01\n\n## Part\n\nText.\n")
        result = run("notes/L01-x.md", cwd=self.subject)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("does not log its text area: page checks skipped", result.stdout)

    @unittest.skipUnless(shutil.which("pdflatex"), "no pdflatex")
    def test_pdflatex_without_latexmk(self):
        tools = os.path.join(self.subject, ".tools")
        os.mkdir(tools)
        for tool in ("pdflatex", "pdftotext", "pdfinfo"):
            with open(os.path.join(tools, tool), "w") as fh:
                fh.write(f'#!/bin/sh\nexec "{shutil.which(tool)}" "$@"\n')
            os.chmod(os.path.join(tools, tool), 0o755)
        self.add("notes/L03-gap.md", TALL_CALLOUT + "\n> [!tip]- Answer\n> Yes.\n")
        result = run("notes/L03-gap.md", cwd=self.subject, path=tools)
        self.assertEqual(statuses(result.stdout), {"notes/L03-gap.md": "layout-warnings"}, result.stdout)
        text = subprocess.run(["pdftotext", os.path.join(self.subject, "pdf", "notes", "L03-gap.pdf"), "-"],
                              capture_output=True, text=True).stdout
        self.assertIn("1/2", text)  # page total and answer page resolved by the reruns
        self.assertIn("Answer 1, p. 2", text)


if __name__ == "__main__":
    unittest.main()
