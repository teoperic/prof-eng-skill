"""Compile checks for templates/document.tex, the preamble of the PDF output.

The stress test fills the template with synthetic LaTeX (paragraphs of 1-12
lines, headings, callouts, recipe cards, display equations, lists with a
lead-in line, a long table),
compiles it and reads the word positions back with pdftotext -bbox-layout to
check the page-break rules. The after-heading test puts each construct directly
under a heading and slides the pair down the page in 3pt steps, because the
breaks that strand a heading only happen at a few exact heights. Every word carries a tag such as P007 (paragraph 7),
H012 (heading 12), C005 (callout 5), R002 (recipe card 2, or one of its fields), E009 (equation
after paragraph 9) or T001 (long table 1), so each text line on a page can be
traced to the block it came from.

Skipped without latexmk/pdflatex or pdftotext.
Run from the repo root: python3 -m unittest discover tests
"""
import concurrent.futures
import html
import os
import random
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(REPO, "skills", "prof-eng", "templates", "document.tex")

MARGIN_PT = 25 / 25.4 * 72  # \docmargin in points: header and footer sit outside
WORDS = ("alpha beta gamma delta signal system filter linear response input output "
         "transfer pole zero gain phase time constant voltage current").split()
TAG = re.compile(r"([PHCRET])(\d{3})$")
HEADING_LEVELS = ("section", "subsection", "subsubsection")


def latex_tool():
    return shutil.which("latexmk") or shutil.which("pdflatex")


def compile_body(body, workdir, name="doc", single_pass=False):
    """Fill the template with body, compile in workdir; return (returncode, pdf, log).

    single_pass runs pdflatex once: the page total in the footer stays unresolved,
    which does not change the layout of the text area.
    """
    with open(TEMPLATE, encoding="utf-8") as fh:
        tex = fh.read().replace("%%BODY%%", body)
    with open(os.path.join(workdir, name + ".tex"), "w", encoding="utf-8") as fh:
        fh.write(tex)
    tool = latex_tool()
    if single_pass and shutil.which("pdflatex"):
        tool = shutil.which("pdflatex")
    if tool.endswith("latexmk"):
        cmd = [tool, "-pdf", "-interaction=nonstopmode", "-halt-on-error", name + ".tex"]
        runs = 1
    else:
        cmd = [tool, "-interaction=nonstopmode", "-halt-on-error", name + ".tex"]
        runs = 1 if single_pass else 2  # second run resolves \pageref{LastPage}
    for _ in range(runs):
        result = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=300)
        if result.returncode:
            break
    with open(os.path.join(workdir, name + ".log"), encoding="latin-1") as fh:
        log = fh.read()
    return result.returncode, os.path.join(workdir, name + ".pdf"), log


def body_lines(pdf):
    """Per page, the text lines inside the text area: lists of words, top to bottom."""
    out = subprocess.run(["pdftotext", "-bbox-layout", pdf, "-"],
                         capture_output=True, text=True, check=True).stdout
    pages = []
    for page in re.finditer(r'<page width="[\d.]+" height="([\d.]+)">(.*?)</page>', out, re.S):
        height = float(page.group(1))
        lines = []
        for line in re.finditer(r'<line xMin="[\d.]+" yMin="([\d.]+)" xMax="[\d.]+" '
                                r'yMax="([\d.]+)">(.*?)</line>', page.group(2), re.S):
            y_min, y_max = float(line.group(1)), float(line.group(2))
            # descenders of the last line reach below the text area, so test the
            # line's top against the bottom edge and its bottom against the top edge
            if y_max < MARGIN_PT or y_min > height - MARGIN_PT:
                continue
            words = [html.unescape(w) for w in re.findall(r"<word [^>]*>(.*?)</word>", line.group(3))]
            lines.append((y_min, words))
        lines.sort(key=lambda item: item[0])
        pages.append([words for _, words in lines])
    return pages


def line_tag(words):
    """The block tag of a text line ('P007'), or None for untagged lines."""
    for word in words:
        match = TAG.search(word)
        if match:
            return match.group(1) + match.group(2)
    return None


def tagged(rng, tag, count):
    return " ".join(rng.choice(WORDS) + tag for _ in range(count))


def stress_body(seed=7, blocks=260):
    """Synthetic LaTeX body; returns (body, lead-ins, long-table tag).

    lead-ins are (lead-in paragraph tag, tag of what must start on its last page):
    a display equation or the first item of a list.
    """
    rng = random.Random(seed)
    counters = {k: 0 for k in "PHCRET"}
    parts = [r"\profengdrafttrue",
             r"\profengtitle{Stress test}{Synthetic \textperiodcentered{} built by test\_document\_tex.py}"]
    lead_ins = []
    long_table = None

    def next_tag(kind):
        counters[kind] += 1
        return f"{kind}{counters[kind]:03d}"

    def paragraph(lines):
        tag = next_tag("P")
        return tag, tag + " " + tagged(rng, tag, max(1, 8 * lines - 2))

    for _ in range(blocks):
        kind = rng.choices(["par", "sec", "subsec", "callout", "eq", "list", "recipe", "table"],
                           [50, 6, 10, 12, 10, 6, 4, 1])[0]
        if kind == "par":
            parts.append(paragraph(rng.randint(1, 12))[1])
        elif kind in ("sec", "subsec"):
            tag = next_tag("H")
            cmd = "section" if kind == "sec" else "subsection"
            parts.append(f"\\{cmd}{{{tag} {tagged(rng, tag, rng.randint(1, 3))}}}\\label{{{tag.lower()}}}")
        elif kind == "callout":
            tag = next_tag("C")
            if rng.random() < 0.2:
                parts.append(f"\\calloutline{{note}}{{{tag} {tagged(rng, tag, 4)}}}")
            else:
                ctype = rng.choice(["note", "abstract", "important", "example",
                                    "warning", "question", "info", "tip"])
                body = "\n\n".join(tagged(rng, tag, 8 * rng.randint(1, 4)) for _ in range(rng.randint(1, 2)))
                parts.append(f"\\begin{{callout}}{{{ctype}}}{{{tag} {tagged(rng, tag, 2)}}}\n"
                             f"{body}\n\\end{{callout}}")
        elif kind == "eq":
            tag, text = paragraph(rng.randint(1, 4))
            eq = "E" + tag[1:]
            lead_ins.append((tag, eq))
            parts.append(text + f" as{tag} follows{tag}\n$$\n\\text{{" + eq + r"} = \frac{a+b}{c}\, e^{-t/\tau}" + "\n$$")
        elif kind == "list":
            tag, text = paragraph(rng.randint(1, 3))
            items = [next_tag("P") for _ in range(rng.randint(2, 8))]
            lead_ins.append((tag, items[0]))
            parts.append(text + f" Steps{tag}\n\\begin{{enumerate}}\n"
                         + "\n".join(f"\\item {item} {tagged(rng, item, 8 * rng.randint(1, 2))}" for item in items)
                         + "\n\\end{enumerate}")
        elif kind == "recipe":
            tag = next_tag("R")
            steps = "\n".join(f"\\item {tagged(rng, tag, 8 * rng.randint(1, 2))}"
                              for _ in range(rng.randint(2, 12)))
            parts.append(f"\\begin{{recipecard}}{{{tag} {tagged(rng, tag, 2)}}}{{{tag.lower()}}}\n"
                         f"\\textbf{{Frequency{tag}:}} {tagged(rng, tag, 6)}\n"
                         f"\\begin{{enumerate}}\n{steps}\n\\end{{enumerate}}\n\\end{{recipecard}}")
        elif kind == "table" and long_table is None:
            tag = next_tag("T")
            long_table = tag
            header = f"Slides{tag} & Section{tag} \\\\"
            rows = "\n".join(f"{n}{tag} & {tagged(rng, tag, 3)} \\\\" for n in range(1, 61))
            parts.append(f"\\begin{{xltabular}}{{\\linewidth}}{{lX}}\n\\toprule\n{header}\n\\midrule\n"
                         f"\\endfirsthead\n\\toprule\n{header}\n\\midrule\n\\endhead\n"
                         f"\\bottomrule\n\\endlastfoot\n{rows}\n\\end{{xltabular}}")
    return "\n\n".join(parts) + "\n", lead_ins, long_table


def after_heading_constructs():
    """name -> LaTeX that follows a heading; every word tagged so lines can be traced."""
    rng = random.Random(3)
    head = "SlidesT001 & SectionT001 \\\\"
    rows = "\n".join(f"{n}T001 & {tagged(rng, 'T001', 3)} \\\\" for n in range(1, 31))
    return {
        "paragraph": tagged(rng, "P001", 40),
        **{f"then-{level}": f"\\{level}{{H002 innerH002}}\n" + tagged(rng, "P001", 40)
           for level in HEADING_LEVELS},
        "callout": "\\begin{callout}{important}{C001 titleC001}\n" + tagged(rng, "C001", 40) + "\n\\end{callout}",
        "calloutline": "\\calloutline{question}{C001 " + tagged(rng, "C001", 6) + "}",
        "recipecard": ("\\begin{recipecard}{R001 cardR001}{r001}\n"
                       + "\n\n".join(tagged(rng, "R001", 16) for _ in range(6)) + "\n\\end{recipecard}"),
        # the real card layout: short fields, then "Steps:" with a list right after it
        "recipe-steps": ("\\begin{recipecard}{R002 cardR002}{r002}\n"
                         f"FrequencyR003 {tagged(rng, 'R003', 5)}\n\n"
                         f"RecognizeR004 {tagged(rng, 'R004', 14)}\n\n"
                         "StepsR005\n\\begin{enumerate}\n"
                         + "\n".join(f"\\item {tagged(rng, f'R{n:03d}', 10)}" for n in range(11, 16))
                         + f"\n\\end{{enumerate}}\nKeyR006 {tagged(rng, 'R006', 6)}\n\\end{{recipecard}}"),
        "codebox": "\\begin{codebox}\n" + "\n".join(f"lineK001 = {n};" for n in range(12)) + "\n\\end{codebox}",
        "itemize": "\\begin{itemize}\n" + "\n".join(f"\\item {tagged(rng, f'P{n:03d}', 6)}" for n in range(11, 16))
                   + "\n\\end{itemize}",
        "shorttable": ("\\docshorttable{\\begin{tabularx}{\\linewidth}{lX}\\toprule\n" + head + "\n\\midrule\n"
                       + "\n".join(f"{n}T001 & {tagged(rng, 'T001', 3)} \\\\" for n in range(1, 6))
                       + "\n\\bottomrule\n\\end{tabularx}}"),
        "longtable": (f"\\begin{{xltabular}}{{\\linewidth}}{{lX}}\n\\toprule\n{head}\n\\midrule\n\\endfirsthead\n"
                      f"\\toprule\n{head}\n\\midrule\n\\endhead\n\\bottomrule\n\\endlastfoot\n{rows}\n"
                      "\\end{xltabular}"),
        "equation": tagged(rng, "P001", 10) + "\n$$\n\\text{E001} = \\frac{a+b}{c}\n$$",
        "lead-in-list": (tagged(rng, "P001", 10) + "\n\\begin{enumerate}\n"
                         + "\n".join(f"\\item {tagged(rng, f'P{n:03d}', 12)}" for n in range(21, 29))
                         + "\n\\end{enumerate}"),
    }


def sliding_body(level, step_pt=3):
    """Every construct under a heading of this level, pushed down the page in steps.

    Each instance starts on a fresh page with the heading H001, so the pages of one
    instance run from a page with H001 to the next one.
    """
    parts = []
    for construct in after_heading_constructs().values():
        for top in range(0, 640, step_pt):  # the text area is 700pt high
            parts.append(f"\\clearpage\n\\vspace*{{{top}pt}}\n\\{level}{{H001 headingH001}}\n" + construct)
    return "\n\n".join(parts) + "\n"


def instances(pages):
    """Split the pages of a sliding document into instances (lists of pages)."""
    groups = []
    for lines in pages:
        if not groups or any(words and words[0] == "H001" for words in lines):
            groups.append([])
        groups[-1].append(lines)
    return groups


def where_tags(pages):
    """tag -> {page index: number of lines} over the given pages."""
    where = {}
    for index, lines in enumerate(pages):
        for words in lines:
            tag = line_tag(words)
            if tag:
                counts = where.setdefault(tag, {})
                counts[index] = counts.get(index, 0) + 1
    return where


def layout_problems(pages, lead_ins=()):
    """Page-break rule violations in pages whose tags are unique (one document or instance)."""
    where = where_tags(pages)
    problems = []
    for tag, counts in sorted(where.items()):
        if tag[0] in "PR" and len(counts) > 1 and min(counts.values()) < 2:
            problems.append(f"{tag} split with a single line: page -> lines {counts}")
        if tag[0] == "C" and len(counts) > 1:
            problems.append(f"callout {tag} split over pages {sorted(counts)}")
    for index, lines in enumerate(pages[:-1]):
        if lines and (line_tag(lines[-1]) or "").startswith("H"):
            problems.append(f"heading at the bottom of a page: {' '.join(lines[-1])}")
    for lead, follower in lead_ins:
        if lead in where and min(where.get(follower, {-1: 0})) != max(where[lead]):
            problems.append(f"{follower} does not start on the page that ends its lead-in {lead}")
    return problems


def build_stress(workdir, seed=7):
    """Compile the stress document in workdir; return (returncode, pdf, log, lead_ins, long_table)."""
    body, lead_ins, long_table = stress_body(seed)
    code, pdf, log = compile_body(body, workdir, "stress")
    return code, pdf, log, lead_ins, long_table


@unittest.skipUnless(latex_tool(), "no LaTeX installed (latexmk or pdflatex)")
class DocumentCompileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="prof-eng-doc-")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_a4_and_12pt(self):
        code, pdf, log = compile_body(r"\profengtitle{Sample}{}" "\nSome text.\n", self.tmp)
        self.assertEqual(code, 0, log[-3000:])
        self.assertIn("prof-eng: fontsize=12", log)
        self.assertNotIn("prof-eng: could not patch", log)  # package update broke a page-break fix
        if shutil.which("pdfinfo"):
            info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
            self.assertIn("595.276 x 841.89", info)  # A4 in points


NEEDS_TOOLS = (latex_tool() and shutil.which("pdftotext"), "needs LaTeX (latexmk or pdflatex) and pdftotext")
# seed 7 has the long table; the others once broke a page-break rule
STRESS_SEEDS = (7, 3, 9, 16, 26, 39)


@unittest.skipUnless(*NEEDS_TOOLS)
class PageBreakStressTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="prof-eng-stress-")
        cls.docs = {}
        for seed in STRESS_SEEDS:
            workdir = os.path.join(cls.tmp, str(seed))
            os.mkdir(workdir)
            code, pdf, log, lead_ins, long_table = build_stress(workdir, seed)
            if code:
                raise AssertionError(f"stress document (seed {seed}) failed to compile:\n" + log[-3000:])
            cls.docs[seed] = (body_lines(pdf), log, lead_ins, long_table)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_enough_pages_to_mean_something(self):
        for seed, (pages, _, lead_ins, _) in self.docs.items():
            self.assertGreater(len(pages), 15, f"seed {seed}")
            self.assertTrue(lead_ins, f"seed {seed}")

    def test_no_overfull_vbox(self):
        for seed, (_, log, _, _) in self.docs.items():
            self.assertNotIn("Overfull \\vbox", log, f"seed {seed}")
            self.assertNotIn("Using nobreak failed", log, f"seed {seed}")  # tcolorbox broke under a heading

    def test_page_break_rules(self):
        for seed, (pages, _, lead_ins, _) in self.docs.items():
            with self.subTest(seed=seed):
                self.assertEqual(layout_problems(pages, lead_ins), [])

    def test_long_table_repeats_header(self):
        pages, _, _, tag = self.docs[7]
        self.assertIsNotNone(tag)
        row_pages = {index for index, lines in enumerate(pages)
                     if any(line_tag(w) == tag and not w[0].startswith("Slides") for w in lines)}
        self.assertGreater(len(row_pages), 1, "long table did not span pages")
        for index in row_pages:
            self.assertTrue(any(w and w[0] == "Slides" + tag for w in pages[index]),
                            f"no table header on page {index + 1}")


@unittest.skipUnless(*NEEDS_TOOLS)
class AfterHeadingTest(unittest.TestCase):
    """Each construct right under a heading, at every height on the page (3pt steps)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="prof-eng-heading-")
        cls.docs = {}
        with concurrent.futures.ThreadPoolExecutor() as pool:  # ~3000 pages each
            results = pool.map(lambda level: compile_body(sliding_body(level), cls.tmp, level, single_pass=True),
                               HEADING_LEVELS)
            for level, (code, pdf, log) in zip(HEADING_LEVELS, results):
                if code:
                    raise AssertionError(f"sliding document ({level}) failed to compile:\n" + log[-3000:])
                cls.docs[level] = (instances(body_lines(pdf)), log)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_every_instance_present(self):
        expected = len(after_heading_constructs()) * len(range(0, 640, 3))
        for level, (groups, _) in self.docs.items():
            self.assertEqual(len(groups), expected, level)

    def test_no_overfull_vbox(self):
        for level, (_, log) in self.docs.items():
            self.assertNotIn("Overfull \\vbox", log, level)
            self.assertNotIn("Using nobreak failed", log, level)  # tcolorbox broke under a heading

    def test_page_break_rules(self):
        for level, (groups, _) in self.docs.items():
            problems = []
            for n, pages in enumerate(groups):
                tags = {line_tag(words) for lines in pages for words in lines}
                lead_ins = [(lead, f) for lead, f in (("P001", "E001"), ("P001", "P021"), ("R005", "R011"))
                            if f in tags]
                problems += [f"instance {n}: {p}" for p in layout_problems(pages, lead_ins)]
            with self.subTest(level=level):
                self.assertEqual(problems[:20], [])


if __name__ == "__main__":
    unittest.main()
