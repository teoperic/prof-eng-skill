"""Repo-level checks: templates and README stay consistent with the skill.

Run from the repo root: python3 -m unittest discover tests
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, "skills", "prof-eng")
sys.path.insert(0, os.path.join(SKILL, "scripts"))

from slide_pages import page_count  # noqa: E402


def commands_table(text):
    """The first Markdown table that starts with '| Command |'."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("| Command |"):
            table = []
            for row in lines[i:]:
                if not row.startswith("|"):
                    break
                table.append(row.rstrip())
            return table
    return None


class ReadmeTableTest(unittest.TestCase):
    def test_readme_table_matches_commands_md(self):
        with open(os.path.join(SKILL, "references", "commands.md"), encoding="utf-8") as fh:
            reference = commands_table(fh.read())
        with open(os.path.join(REPO, "README.md"), encoding="utf-8") as fh:
            readme = commands_table(fh.read())
        self.assertIsNotNone(reference, "no commands table in references/commands.md")
        self.assertIsNotNone(readme, "no commands table in README.md")
        self.assertEqual(readme, reference, "README.md table differs from references/commands.md")


class ExamSheetTemplateTest(unittest.TestCase):
    TEX = os.path.join(SKILL, "templates", "exam-sheet.tex")

    def test_settings_block_at_top(self):
        with open(self.TEX, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        self.assertIn("SETTINGS: edit here", lines[0])
        block = "\n".join(lines[:8])
        for name in ("\\sheetfontsize", "\\sheetleading", "\\sheetcolumns"):
            self.assertIn(name, block)
        self.assertLess(
            next(i for i, l in enumerate(lines) if "SETTINGS" in l),
            next(i for i, l in enumerate(lines) if l.startswith("\\documentclass")),
        )

    def test_compiles_to_one_a4_page(self):
        tool = shutil.which("latexmk") or shutil.which("pdflatex")
        if not tool:
            self.skipTest("no LaTeX installed (latexmk or pdflatex)")
        tmp = tempfile.mkdtemp(prefix="prof-eng-tex-")
        try:
            with open(self.TEX, encoding="utf-8") as fh:
                tex = fh.read()
            sample = "\n".join(
                f"\\lecture{{L{n:02d}}}{{Sample lecture {n}}}\n"
                f"\\defn{{Term {n}}}{{A short synthetic definition.}}\n"
                f"$$ u_{n} = R_{n} i_{n} \\qquad \\tau_{n} = R_{n} C_{n} $$"
                for n in range(1, 13)
            )
            tex = tex.replace("% ---- end of content ----", sample + "\n% ---- end of content ----")
            path = os.path.join(tmp, "exam-sheet.tex")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(tex)
            if tool.endswith("latexmk"):
                cmd = [tool, "-pdf", "-interaction=nonstopmode", "-halt-on-error", "exam-sheet.tex"]
            else:
                cmd = [tool, "-interaction=nonstopmode", "-halt-on-error", "exam-sheet.tex"]
            result = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=300)
            self.assertEqual(result.returncode, 0, result.stdout[-3000:])
            pdf = os.path.join(tmp, "exam-sheet.pdf")
            count, _ = page_count(pdf)
            self.assertEqual(count, 1)
            if shutil.which("pdfinfo"):
                info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
                self.assertIn("595.276 x 841.89", info)  # A4 in points
        finally:
            shutil.rmtree(tmp)


class DocumentTemplateTest(unittest.TestCase):
    TEX = os.path.join(SKILL, "templates", "document.tex")

    def test_settings_block_at_top(self):
        with open(self.TEX, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        self.assertIn("SETTINGS: edit here", lines[0])
        block = "\n".join(lines[:8])
        for name in ("\\docfontsize", "\\docpaper", "\\docmargin", "\\doclinespread"):
            self.assertIn(name, block)
        self.assertIn("{12pt}", block)
        self.assertIn("{a4paper}", block)
        self.assertLess(
            next(i for i, l in enumerate(lines) if "SETTINGS" in l),
            next(i for i, l in enumerate(lines) if "\\documentclass" in l),
        )

    def test_body_placeholder(self):
        with open(self.TEX, encoding="utf-8") as fh:
            text = fh.read()
        self.assertEqual(text.count("%%BODY%%"), 1)
        self.assertLess(text.index("\\begin{document}"), text.index("%%BODY%%"))
        self.assertLess(text.index("%%BODY%%"), text.index("\\end{document}"))


class ClaudeTemplateTest(unittest.TestCase):
    def test_output_format_field(self):
        with open(os.path.join(SKILL, "templates", "CLAUDE.md"), encoding="utf-8") as fh:
            text = fh.read()
        frontmatter = text.split("---")[1]
        self.assertRegex(frontmatter, r"\noutput_format: unset +# markdown \| pdf \| unset")


class NoCourseMaterialTest(unittest.TestCase):
    def test_no_pdfs_or_images_in_repo(self):
        found = []
        for dirpath, dirnames, filenames in os.walk(REPO):
            dirnames[:] = [d for d in dirnames if d != ".git"]
            for name in filenames:
                if name.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".docx", ".pptx")):
                    found.append(os.path.relpath(os.path.join(dirpath, name), REPO))
        self.assertEqual(found, [], "binary course-like files in the repo")


if __name__ == "__main__":
    unittest.main()
