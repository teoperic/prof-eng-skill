"""Tests for scripts/md_to_tex.py, the Markdown to LaTeX converter of the PDF output.

Unit tests convert small Markdown snippets in a temporary subject folder and
check the LaTeX body. The compile tests (skipped without LaTeX) convert the
sample files of make_fixtures.py, compile them with the real template and
check the log and the link targets in the PDFs.

Run from the repo root: python3 -m unittest discover tests
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zlib
from unittest import mock
from urllib.parse import unquote

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "skills", "prof-eng", "scripts")
TEMPLATE = os.path.join(os.path.dirname(HERE), "skills", "prof-eng", "templates", "document.tex")
FORMATTING = os.path.join(os.path.dirname(HERE), "skills", "prof-eng", "references", "formatting.md")
sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)

from make_fixtures import SAMPLES, make_subject, write_png, write_samples  # noqa: E402
import check_links  # noqa: E402
import md_to_tex  # noqa: E402


def write(path, text, dedent=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(textwrap.dedent(text).lstrip("\n") if dedent else text)


def run(*args, cwd=None):
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, "md_to_tex.py"), *args],
                          capture_output=True, text=True, timeout=120, cwd=cwd)


class TempSubjectTest(unittest.TestCase):
    def setUp(self):
        self.subject = tempfile.mkdtemp(prefix="prof-eng-md2tex-")
        with open(TEMPLATE, encoding="utf-8") as fh:
            self.template = fh.read()

    def tearDown(self):
        shutil.rmtree(self.subject)

    def convert(self, text, rel="notes/L07-laplace.md"):
        """(body LaTeX, error messages) for Markdown text stored at rel."""
        path = os.path.join(self.subject, rel)
        write(path, text)
        tex = md_to_tex.mirror_path(self.subject, rel, ".tex")
        converter = md_to_tex.Converter(path, self.subject, tex, self.template)
        with open(path, encoding="utf-8") as fh:
            out = converter.convert(fh.read(), "%%BODY%%")
        return out.split("\n", 1)[1], [message for _, message in converter.errors]

    def body(self, text, rel="notes/L07-laplace.md"):
        body, errors = self.convert(text, rel)
        self.assertEqual(errors, [])
        return body


class FrontmatterAndHeadingsTest(TempSubjectTest):
    NOTE = """
        ---
        course: Signals & Systems
        lecture: 7
        status: draft        # draft | reviewed
        tags: [lecture]
        ---
        # L07 – Laplace transform

        ## Core content
        ### 2. Partial fractions
        #### Detail
    """

    def test_title_meta_and_draft(self):
        body = self.body(self.NOTE)
        self.assertTrue(body.startswith("\\profengdrafttrue\n"))
        self.assertRegex(body, r"\\profengtitle\{L07 – Laplace transform\}"
                               r"\{Signals \\& Systems · Lecture 7 · built \d{4}-\d\d-\d\d\}")

    def test_reviewed_and_no_frontmatter(self):
        self.assertNotIn("profengdrafttrue", self.body(self.NOTE.replace("draft ", "reviewed ")))
        body = self.body("# L07 – cheatsheet\n\nText.\n", "cheatsheets/L07-cheatsheet.md")
        self.assertIn("\\profengtitle{L07 – cheatsheet}{}", body)

    def test_levels_unstarred_with_labels(self):
        body = self.body(self.NOTE)
        self.assertIn("\\section{Core content}\\label{core-content}", body)
        self.assertIn("\\subsection{2. Partial fractions}\\label{2.2e-partial-fractions}", body)
        self.assertIn("\\subsubsection{Detail}\\label{detail}", body)

    def test_label_matches_check_links_anchor(self):
        # the heading key check_links stores and the key of a decoded link anchor give one name
        path = os.path.join(self.subject, "notes", "L07-laplace.md")
        heading = "R3 – Step response (2nd order) of `x`"
        write(path, f"# T\n\n### {heading}\n")
        stored = check_links.headings(path) - {"t"}
        self.assertEqual(len(stored), 1)
        anchor = "R3%20–%20Step%20response%20(2nd%20order)%20of%20"
        self.assertEqual(check_links.check_target(path, "#" + anchor), ("ok", ""))
        name = md_to_tex.dest_name(check_links.anchor_key(unquote(anchor)))
        self.assertEqual(name, md_to_tex.dest_name(next(iter(stored))))
        self.assertIn(f"{{{name}}}", self.body(f"# T\n\n## {heading}\n"))  # a recipe card's label
        self.assertRegex(name, r"^[a-z0-9.\-]+$")

    def test_duplicate_heading_gets_second_label(self):
        body = self.body("# T\n\n## Example\n\n## Example\n")
        self.assertIn("\\label{example}", body)
        self.assertIn("\\label{example:2}", body)

    def test_heading_with_math_gets_bookmark_text(self):
        body = self.body("# T\n\n## The $H(s)$ form\n")
        self.assertIn("\\section{\\texorpdfstring{The $H(s)$ form}{The H(s) form}}", body)

    def test_later_h1_starts_a_part(self):
        body = self.body("# Index\n\nText.\n\n# L07 cheatsheet\n\nMore.\n", "EXAM-SHEET-print.md")
        self.assertIn("\\docpart{L07 cheatsheet}{l07-cheatsheet}", body)


class TextTest(TempSubjectTest):
    def test_each_line_is_a_paragraph(self):
        body = self.body("# T\n\n**Frequency:** 5 of 6\n**Recognize it:** a step\n")
        self.assertIn("\\textbf{Frequency:} 5 of 6\n\n\\textbf{Recognize it:} a step", body)

    def test_emphasis_and_code(self):
        body = self.body("# T\n\n**bold** *italic* ***both*** `a_b{c}` x * y\n")
        self.assertIn("\\textbf{bold} \\emph{italic} \\textbf{\\emph{both}} \\texttt{a\\_b\\{c\\}} x * y", body)

    def test_escaping(self):
        body = self.body("# T\n\n50% & a_b #3 {x} ~ ^ back\\slash\n")
        self.assertIn("50\\% \\& a\\_b \\#3 \\{x\\} \\textasciitilde{} \\textasciicircum{} "
                      "back\\textbackslash{}slash", body)

    def test_markdown_escapes(self):
        self.assertIn("\\$ and * and \\_", self.body("# T\n\n\\$ and \\* and \\_\n"))

    def test_unicode_passes_to_the_template(self):
        body = self.body("# T\n\nτ ≈ 1 ms – Ω, µF, 20 °C, ü, ß, “quoted” …\n")
        self.assertIn("τ ≈ 1 ms – Ω, µF, 20 °C, ü, ß, “quoted” …", body)

    def test_unknown_character(self):
        _, errors = self.convert("# T\n\nDone ✅\n")
        self.assertEqual(len(errors), 1)
        self.assertIn("U+2705", errors[0])

    def test_character_declared_in_template_is_allowed(self):
        self.template += "\n\\DeclareUnicodeCharacter{2705}{\\checkmark}\n"
        self.assertIn("Done ✅", self.body("# T\n\nDone ✅\n"))

    def test_horizontal_rule(self):
        self.assertIn("\\docrule", self.body("# T\n\nText.\n\n---\n\nMore.\n"))


class MathTest(TempSubjectTest):
    INLINE = r"$\frac{a_1}{b^{2}} + \{x\} \% \text{k}\Omega$"
    DISPLAY = "$$\n\\begin{aligned}\nv(t) &= V_0\\, e^{-t/\\tau} \\\\\ni(t) &= -\\frac{V_0}{R}\n\\end{aligned}\n$$"

    def test_inline_math_unchanged(self):
        self.assertIn(f"Value {self.INLINE} here.", self.body(f"# T\n\nValue {self.INLINE} here.\n"))

    def test_display_math_unchanged_and_kept_with_lead_in(self):
        body = self.body(f"# T\n\nThe current is\n\n{self.DISPLAY}\n\nAfter.\n")
        self.assertIn("The current is\n" + self.DISPLAY + "\n\nAfter.", body)

    def test_display_math_without_lead_in(self):
        body = self.body(f"# T\n\n## H\n\n{self.DISPLAY}\n")
        self.assertIn("\\noindent%\n" + self.DISPLAY, body)

    def test_one_line_display(self):
        self.assertIn("Text\n$$ x = 1 $$", self.body("# T\n\nText\n$$ x = 1 $$\n"))

    def test_math_with_markdown_characters(self):
        body = self.body("# T\n\n*a* $a*b*c_d_e$ and `$x$`\n")
        self.assertIn("\\emph{a} $a*b*c_d_e$ and \\texttt{\\$x\\$}", body)

    def test_stray_dollar(self):
        _, errors = self.convert("# T\n\nCosts $5 and $6.\n")
        self.assertTrue(any("unmatched $" in e for e in errors), errors)

    def test_unclosed_display(self):
        _, errors = self.convert("# T\n\n$$\nx = 1\n")
        self.assertTrue(any("never closed" in e for e in errors), errors)


class ListTest(TempSubjectTest):
    def test_nested_lists(self):
        body = self.body("# T\n\n- one\n  - inner\n  - inner two\n- two\n")
        self.assertIn("\\begin{itemize}\n\\item{} one\n\n\\begin{itemize}\n\\item{} inner\n"
                      "\\item{} inner two\n\\end{itemize}\n\\item{} two\n\\end{itemize}", body)

    def test_ordered_with_start_and_nested_bullets(self):
        body = self.body("# T\n\n3. third\n   - sub\n4. fourth\n")
        self.assertIn("\\begin{enumerate}[start=3]\n\\item{} third", body)
        self.assertIn("\\item{} sub", body)

    def test_continuation_line_in_item(self):
        body = self.body("# T\n\n1. Step\n   with a second line\n2. Next\n")
        self.assertIn("\\item{} Step\n\nwith a second line\n\\item{} Next", body)

    def test_item_starting_with_bracket(self):
        self.assertIn("\\item{} [sic] text", self.body("# T\n\n- [sic] text\n"))


class TableTest(TempSubjectTest):
    def table(self, rows):
        return "| Formula | Meaning | Section |\n|---|:-:|--:|\n" + "".join(
            f"| $x_{n}$ | meaning {n} \\| alias | [1. Topic](#1.%20Topic) |\n" for n in range(rows))

    def test_short_table(self):
        body = self.body("# T\n\n## 1. Topic\n\n" + self.table(3))
        self.assertIn("\\docshorttable{\\begin{tabularx}{\\linewidth}{", body)
        self.assertIn("\\textbf{Formula} & \\textbf{Meaning} & \\textbf{Section} \\\\", body)
        self.assertIn("$x_0$ & meaning 0 | alias & \\hyperref[1.2e-topic]{1. Topic} \\\\", body)
        self.assertNotIn("xltabular", body)

    def test_alignment_and_wrapping_column(self):
        spec = md_to_tex.Converter.table_spec(md_to_tex.Block(
            "table", 1, header=["a", "b", "c"], aligns=["l", "c", "r"],
            rows=[(2, ["x", "a long description that has to wrap", "1"])]))
        self.assertEqual(spec, "l>{\\centering\\arraybackslash}Xr")

    def test_long_table_repeats_header(self):
        body = self.body("# T\n\n## 1. Topic\n\n" + self.table(md_to_tex.LONG_TABLE_ROWS + 1))
        self.assertIn("\\begin{xltabular}{\\linewidth}", body)
        self.assertEqual(body.count("\\textbf{Formula}"), 2)
        self.assertIn("\\endfirsthead", body)
        self.assertIn("\\endhead", body)

    def test_long_table_in_box_stays_short(self):
        rows = self.table(md_to_tex.LONG_TABLE_ROWS + 1).replace("\n|", "\n> |")
        body = self.body("# T\n\n## 1. Topic\n\n> [!note] Table\n> " + rows)
        self.assertNotIn("xltabular", body)

    def test_too_many_cells(self):
        _, errors = self.convert("# T\n\n| a | b |\n|---|---|\n| 1 | 2 | 3 |\n")
        self.assertTrue(any("3 cells" in e for e in errors), errors)


class CalloutTest(TempSubjectTest):
    def test_callout_with_body(self):
        body = self.body("# T\n\n> [!important] Key result\n> The time constant is $\\tau = RC$.\n")
        self.assertIn("\\begin{callout}{important}{Key result}\nThe time constant is $\\tau = RC$.\n"
                      "\\end{callout}", body)

    def test_title_only_and_default_title(self):
        body = self.body("# T\n\n> [!question] Slide 17: unreadable.\n\n> [!note]\n> Body.\n")
        self.assertIn("\\calloutline{question}{Slide 17: unreadable.}", body)
        self.assertIn("\\begin{callout}{note}{Note}", body)

    def test_collapsed_other_callout_in_place(self):
        body = self.body("# T\n\n> [!example]- Worked example\n> Steps.\n")
        self.assertIn("\\begin{callout}{example}{Worked example}\nSteps.\n\\end{callout}", body)

    def test_answers_move_to_the_end(self):
        body = self.body("# T\n\n## Self-test\n1. Q one?\n\n> [!tip]- Answer\n> A one.\n\n"
                         "2. Q two?\n\n> [!tip]- Answer (short)\n> A two.\n\n## Slide coverage\nEnd.\n")
        self.assertIn("\\docanswerlink{1}", body)
        self.assertIn("\\begin{enumerate}[start=2]", body)
        answers = body.index("\\section{Answers}")
        self.assertGreater(answers, body.index("\\section{Slide coverage}"))
        self.assertIn("\\begin{docanswer}{1}{Answer 1}\nA one.\n\\end{docanswer}", body[answers:])
        self.assertIn("\\begin{docanswer}{2}{Answer 2 (short)}\nA two.", body[answers:])
        self.assertNotIn("A one.", body[:answers])

    def test_unknown_type_and_plain_quote(self):
        _, errors = self.convert("# T\n\n> [!success] Done\n\n> plain quote\n")
        self.assertEqual(len(errors), 2, errors)
        self.assertIn("[!success]", errors[0])
        self.assertIn("plain block quote", errors[1])


class BoxTest(TempSubjectTest):
    def test_recipe_card(self):
        body = self.body("# L07 – cheatsheet\n\n## Recipes\n### R3 – Step response\n**Frequency:** 5 of 6\n"
                         "**Steps:**\n1. One\n\n## Formulas and constants\nText.\n",
                         "cheatsheets/L07-cheatsheet.md")
        self.assertIn("\\begin{recipecard}{R3 – Step response}{r3-.e2.80.93-step-response}\n"
                      "\\textbf{Frequency:} 5 of 6", body)
        self.assertLess(body.index("\\end{recipecard}"), body.index("\\section{Formulas and constants}"))

    def test_solution_file(self):
        body = self.body("---\nexam: 2023-jan\nstatus: reviewed\n---\n# Exam – solutions\n\n## Questions\n"
                         "### Q1 (15 pts) – type R3\nStatement.\n\n## Solutions\n### Q1 solution\n"
                         "**Solution:** done.\n#### Remark\nNote.\n### Q2 solution\nTwo.\n",
                         "solutions/exam-2023-jan.md")
        self.assertIn("\\subsection{Q1 (15 pts) – type R3}", body)
        self.assertIn("\\clearpage\n\n\\section{Solutions}", body)
        self.assertIn("\\begin{solutionbox}{Q1 solution}{q1-solution}", body)
        self.assertIn("\\phantomsection\\label{remark}\\textbf{Remark}", body)
        self.assertEqual(body.count("\\begin{solutionbox}"), 2)


class LinkAndImageTest(TempSubjectTest):
    def test_same_file(self):
        body = self.body("# T\n\n## 1. Topic\n[see](#1.%20Topic) and [nested](#T#1.%20topic)\n")
        self.assertIn("\\hyperref[1.2e-topic]{see} and \\hyperref[1.2e-topic]{nested}", body)

    def test_missing_same_file_heading(self):
        _, errors = self.convert("# T\n\n[see](#Nowhere)\n")
        self.assertEqual(errors, ["link to a missing heading: #Nowhere"])

    def test_in_scope_markdown_becomes_pdf(self):
        body = self.body("# T\n\n[card](../cheatsheets/L07-cheatsheet.md#R3%20–%20Step%20response) "
                         "[note](L06-z.md)\n")
        self.assertIn("\\href{../cheatsheets/L07-cheatsheet.pdf\\#r3-.e2.80.93-step-response}{card}", body)
        self.assertIn("\\href{L06-z.pdf}{note}", body)

    def test_from_subject_root(self):
        body = self.body("# Sheet\n\n[R3](cheatsheets/L07-cheatsheet.md#R3%20–%20Step) "
                         "[L07 note](notes/L07-laplace.md)\n", "EXAM-SHEET.md")
        self.assertIn("\\href{cheatsheets/L07-cheatsheet.pdf\\#r3-.e2.80.93-step}{R3}", body)
        self.assertIn("\\href{notes/L07-laplace.pdf}{L07 note}", body)

    def test_source_pdf_page(self):
        body = self.body("# T\n\n[slide 14](../slides/L07.pdf#page=14) [book](../book/b.pdf)\n")
        self.assertIn("\\href[page=14]{../../slides/L07.pdf}{slide 14}", body)
        self.assertIn("\\href{../../book/b.pdf}{book}", body)

    def test_out_of_scope_markdown_and_check_file(self):
        body = self.body("# T\n\n[index](../00-index.md) [check](checks/2023-jan-Q1.py)\n",
                         "solutions/exam-2023-jan.md")
        self.assertIn("\\href{../../00-index.md}{index}", body)
        self.assertIn("\\href{../../solutions/checks/2023-jan-Q1.py}{check}", body)

    def test_external(self):
        body = self.body("# T\n\n[site](https://example.org/a_b?x=1&y=2#frag%20x)\n")
        self.assertIn("\\href{https://example.org/a_b?x=1\\&y=2\\#frag\\%20x}{site}", body)

    def test_link_text_with_math_and_bold(self):
        body = self.body("# T\n\n## 1. Topic\n[**$H(s)$** form](#1.%20Topic)\n")
        self.assertIn("\\hyperref[1.2e-topic]{\\textbf{$H(s)$} form}", body)

    def test_image(self):
        write_png(os.path.join(self.subject, "notes", "img", "L07-s14.png"))
        body = self.body("# T\n\n![Slide 14](img/L07-s14.png)\n")
        self.assertIn("\\docfigure{../../notes/img/L07-s14.png}{Slide 14}", body)

    def test_missing_image(self):
        _, errors = self.convert("# T\n\n![Slide 14](img/none.png)\n")
        self.assertEqual(errors, ["image not found: img/none.png"])


class CodeTest(TempSubjectTest):
    def test_language(self):
        body = self.body("# T\n\n```matlab\nx = 1;  % comment\n```\n\n```\nplain\n```\n")
        self.assertIn("\\begin{codebox}[language=Matlab]\nx = 1;  % comment\n\\end{codebox}", body)
        self.assertIn("\\begin{codebox}\nplain\n\\end{codebox}", body)

    def test_non_ascii_code(self):
        _, errors = self.convert("# T\n\n```python\ntau = 1  # τ\n```\n")
        self.assertEqual(len(errors), 1)
        self.assertIn("plain ASCII", errors[0])

    def test_mermaid_without_mmdc(self):
        with mock.patch("md_to_tex.shutil.which", return_value=None):
            body = self.body("# T\n\n```mermaid\ngraph LR\n  A --> B\n```\n")
        self.assertIn("\\begin{mermaidsource}\ngraph LR\n  A --> B\n\\end{mermaidsource}", body)

    def test_mermaid_with_mmdc(self):
        tools = os.path.join(self.subject, "tools")
        write(os.path.join(tools, "mmdc"), f"""\
            #!{sys.executable}
            import sys
            sys.path.insert(0, {HERE!r})
            from pdfgen import write_pdf
            write_pdf(sys.argv[sys.argv.index("-o") + 1], ["diagram"])
        """)
        os.chmod(os.path.join(tools, "mmdc"), 0o755)
        with mock.patch.dict(os.environ, {"PATH": tools + os.pathsep + os.environ.get("PATH", "")}):
            body = self.body("# T\n\n```mermaid\ngraph LR\n  A --> B\n```\n")
        self.assertIn("\\docfigure{../../.prof-eng-build/mermaid/notes-L07-laplace-1.pdf}{Diagram}", body)
        self.assertTrue(os.path.isfile(os.path.join(self.subject, ".prof-eng-build", "mermaid",
                                                    "notes-L07-laplace-1.pdf")))


class UnsupportedTest(TempSubjectTest):
    CASES = {
        "[[L06-z]]": "wikilink",
        "![[img.png]]": "embed",
        "text[^1]": "footnote",
        "a ==marked== word": "highlight",
        "~~gone~~": "strikethrough",
        "line<br>break": "raw HTML",
        "<!-- hidden -->": "HTML comment",
        "<https://example.org>": "autolink",
        "%% comment %%": "Obsidian comment",
        "_italic_ word": "_italic_",
        "[text][ref]": "reference link",
        "[ref]: https://example.org": "link reference definition",
        "- [ ] task": "task list",
        "##### Deep": "heading level 5",
        "inline $$x$$ math": "$$ inside a line",
        "\\begin{align} x \\end{align}": "LaTeX environment",
        "text ![pic](img/a.png) inline": "image inside text",
        "Title\n===": "setext",
        "```python\nnot closed": "never closed",
    }

    def test_each_construct_reports_its_line(self):
        for markdown, what in self.CASES.items():
            with self.subTest(markdown=markdown):
                _, errors = self.convert(f"# T\n\nFine line.\n\n{markdown}\n")
                self.assertEqual(len(errors), 1, errors)
                self.assertIn(what, errors[0])

    def test_cli_prints_file_and_line_and_writes_nothing(self):
        write(os.path.join(self.subject, "notes", "L07-x.md"), "# T\n\nOk.\n\nSee [[L06-z]].\n")
        result = run("notes/L07-x.md", cwd=self.subject)
        self.assertEqual(result.returncode, 1)
        self.assertIn("notes/L07-x.md:5: unsupported Markdown: wikilink", result.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.subject, "pdf")))

    def test_underscores_inside_words_are_text(self):
        self.assertIn("snake\\_case\\_name", self.body("# T\n\nsnake_case_name\n"))


class NotSupportedListTest(TempSubjectTest):
    """formatting.md's "Not supported" list and the converter's messages stay in sync."""
    ITEMS = {  # item of the list -> Markdown that shows it
        "wikilinks and embeds": ["[[L06-z]]", "![[img.png]]"],
        "plain `>` quotes": ["> quoted"],
        "other callout types": ["> [!danger] Careful"],
        "`==highlight==`": ["a ==marked== word"],
        "`~~strikethrough~~`": ["~~gone~~"],
        "`_italic_` (use `*italic*`)": ["_italic_ word"],
        "footnotes": ["text[^1]"],
        "HTML and HTML comments": ["line<br>break", "<!-- hidden -->"],
        "autolinks `<https://…>` (use `[text](url)`)": ["<https://example.org>"],
        "`%%` comments": ["%% comment %%"],
        "task lists `- [ ]`": ["- [ ] task"],
        "reference links `[text][ref]`": ["[text][ref]", "[ref]: https://example.org"],
        "underlined (setext) headings": ["Title\n==="],
        "`#####` and deeper": ["##### Deep"],
        "headings inside a list or callout": ["- item\n  ## Inside", "> [!note] T\n> ## Inside"],
        "images inside a sentence or from a URL": ["text ![pic](img/a.png) inline",
                                                   "![pic](https://example.org/a.png)"],
        "image paths with spaces": ["![pic](img/a%20b.png)"],
        "`$$` inside a line of text": ["inline $$x$$ math"],
        "LaTeX environments outside `$$`": ["\\begin{align} x \\end{align}"],
        "characters that are neither built into pdflatex nor declared in the template "
        "(for example Chinese, emoji, rare symbols)": ["汉", "🙂"],
    }
    # messages about broken syntax rather than an unsupported construct: not in the list
    MALFORMED = ("never closed", "cells under a header", "delimiter row", "unmatched $", "\\end{codebox}")

    def errors(self):
        """{snippet: error messages}; the image file exists, so only its path is wrong."""
        write_png(os.path.join(self.subject, "notes", "img", "a b.png"))
        return {snippet: self.convert(f"# T\n\nFine line.\n\n{snippet}\n")[1]
                for snippets in self.ITEMS.values() for snippet in snippets}

    def test_list_matches_items(self):
        with open(FORMATTING, encoding="utf-8") as fh:
            sentence = re.search(r"^Not supported: (.*?)\. ", fh.read(), re.M).group(1)
        items = [re.sub(r"^and ", "", item) for item in re.split(r",\s*(?![^()]*\))", sentence)]
        self.assertEqual(sorted(items), sorted(self.ITEMS))

    def test_each_item_is_rejected(self):
        for snippet, errors in self.errors().items():
            with self.subTest(snippet=snippet):
                self.assertEqual(len(errors), 1, errors)

    def test_each_converter_message_is_listed(self):
        with open(os.path.join(SCRIPTS, "md_to_tex.py"), encoding="utf-8") as fh:
            calls = re.findall(r"self\.unsupported\([^,]+,\s*f?\"([^\n]*)", fh.read())
        whats = [call for call in calls if not any(m in call for m in self.MALFORMED)]
        whats += [what for _, what in md_to_tex.UNSUPPORTED]
        reported = [e for errors in self.errors().values() for e in errors]
        for what in whats:
            prefix = "unsupported Markdown: " + re.split(r"[{:\"]", what)[0]
            with self.subTest(message=what):
                self.assertTrue(any(e.startswith(prefix) for e in reported),
                                "no ITEMS snippet triggers it; list it in formatting.md or in MALFORMED")


class CommandLineTest(TempSubjectTest):
    def test_default_output_and_fallback_template(self):
        write(os.path.join(self.subject, "notes", "L07-x.md"), "# T\n\nOk.\n")
        result = run(os.path.join(self.subject, "notes", "L07-x.md"), "--subject", self.subject)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("_templates/document.tex is missing", result.stderr)
        self.assertEqual(result.stdout.strip(), "wrote " + os.path.join("pdf", "notes", "L07-x.tex"))
        with open(os.path.join(self.subject, "pdf", "notes", "L07-x.tex"), encoding="utf-8") as fh:
            tex = fh.read()
        self.assertTrue(tex.startswith("% ===================== SETTINGS"))
        self.assertIn("% Generated by md_to_tex.py from notes/L07-x.md.", tex)
        self.assertNotIn("%%BODY%%", tex)

    def test_subject_template_and_out(self):
        write(os.path.join(self.subject, "_templates", "document.tex"),
              "\\documentclass{article}\\begin{document}\n%%BODY%%\n\\end{document}\n")
        write(os.path.join(self.subject, "EXAM-SHEET.md"), "# Sheet\n")
        out = os.path.join(self.subject, "elsewhere", "x.tex")
        result = run(os.path.join(self.subject, "EXAM-SHEET.md"), "--subject", self.subject, "--out", out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("missing", result.stderr)
        with open(out, encoding="utf-8") as fh:
            self.assertTrue(fh.read().startswith("\\documentclass{article}"))

    def test_template_without_body_line(self):
        write(os.path.join(self.subject, "_templates", "document.tex"), "\\documentclass{article}\n")
        write(os.path.join(self.subject, "notes", "L07-x.md"), "# T\n")
        self.assertEqual(run("notes/L07-x.md", cwd=self.subject).returncode, 2)

    def test_files_without_pdf_version(self):
        for rel in ("00-index.md", "progress.md", "solutions/problem-types.md", "notes/sub/L07.md"):
            with self.subTest(rel=rel):
                write(os.path.join(self.subject, rel), "# X\n")
                result = run(rel, cwd=self.subject)
                self.assertEqual(result.returncode, 2)
                self.assertIn("no PDF version", result.stderr)

    def test_missing_file_and_outside_subject(self):
        self.assertEqual(run("notes/none.md", cwd=self.subject).returncode, 2)
        self.assertEqual(run(TEMPLATE, "--subject", self.subject).returncode, 2)


# ---- compile tests ----

def latex_tool():
    return shutil.which("latexmk") or shutil.which("pdflatex")


def compile_tex(tex):
    """Compile tex in its own folder; return (returncode, log text)."""
    folder, name = os.path.split(tex)
    if shutil.which("latexmk"):
        runs = [["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", name]]
    else:
        runs = [["pdflatex", "-interaction=nonstopmode", "-halt-on-error", name]] * 2
    for cmd in runs:
        result = subprocess.run(cmd, cwd=folder, capture_output=True, timeout=300)
        if result.returncode:
            break
    with open(tex[:-4] + ".log", encoding="latin-1") as fh:
        return result.returncode, fh.read()


def pdf_objects(pdf):
    """The PDF's bytes plus its decompressed streams (link actions live in object streams)."""
    with open(pdf, "rb") as fh:
        data = fh.read()
    parts = [data]
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        try:
            parts.append(zlib.decompress(match.group(1)))
        except zlib.error:
            pass
    return b"".join(parts)


@unittest.skipUnless(latex_tool(), "no LaTeX installed (latexmk or pdflatex)")
class CompileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="prof-eng-md2tex-compile-")
        cls.subject = make_subject(cls.tmp)
        write_samples(cls.subject)
        cls.results = {}
        for rel in SAMPLES:
            with mock.patch("md_to_tex.shutil.which", return_value=None):  # same output with or without mmdc
                converted = run(rel, cwd=cls.subject)
            if converted.returncode:
                raise AssertionError(f"{rel}: md_to_tex.py failed:\n{converted.stderr}")
            tex = md_to_tex.mirror_path(cls.subject, rel, ".tex")
            cls.results[rel] = compile_tex(tex) + (tex[:-4] + ".pdf",)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_compiles_without_warnings(self):
        for rel, (code, log, _) in self.results.items():
            with self.subTest(rel=rel):
                self.assertEqual(code, 0, log[-3000:])
                for warning in ("Overfull", "Underfull \\vbox", "undefined", "multiply defined",
                                "Using nobreak failed", "Token not allowed"):
                    self.assertNotIn(warning, log)

    def test_cross_pdf_links_name_existing_destinations(self):
        names = {rel: set(re.findall(rb"\(([^()]*)\) \d+ 0 R", pdf_objects(pdf)))
                 for rel, (_, _, pdf) in self.results.items()}
        card = b"r2-.e2.80.93-time-constant-of-an-rc-circuit"
        self.assertIn(card, names["cheatsheets/L02-cheatsheet.md"])
        self.assertIn(b"1.2e-time-constant", names["notes/L02-rc-circuits.md"])
        for rel in ("notes/L02-rc-circuits.md", "EXAM-SHEET.md"):
            self.assertIn(b"/GoToR/D(" + card + b")", pdf_objects(self.results[rel][2]), rel)

    def test_slide_link_opens_page(self):
        objects = pdf_objects(self.results["notes/L02-rc-circuits.md"][2])
        self.assertIn(b"/F(../../slides/L02-rc-circuits.pdf)", objects)
        self.assertIn(b"/GoToR/D[2/Fit]", objects)  # page 3, counted from 0

    def test_supported_characters_compile(self):
        # every character the converter lets through, in text; the declared ones also in math
        with open(TEMPLATE, encoding="utf-8") as fh:
            template = fh.read()
        declared = [chr(int(h, 16)) for h in md_to_tex.DECLARED_RE.findall(template)]
        text = "".join(sorted(c for c in md_to_tex.BUILTIN_CHARS | set(declared)
                              if c.isprintable() and c not in md_to_tex.TEXT_ESCAPES and c != "\xad"))
        body = (f"\\profengtitle{{Characters}}{{}}\n{text}\n\n"
                + "$" + "{}".join(declared) + "$\n")
        folder = tempfile.mkdtemp(prefix="prof-eng-chars-")
        try:
            tex = os.path.join(folder, "chars.tex")
            with open(tex, "w", encoding="utf-8") as fh:
                fh.write(template.replace("%%BODY%%", body))
            code, log = compile_tex(tex)
            self.assertEqual(code, 0, log[-3000:])
        finally:
            shutil.rmtree(folder)


if __name__ == "__main__":
    unittest.main()
