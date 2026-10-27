# prof-eng

A Claude Code skill that helps engineering students study one subject at a time. It turns each lecture's slides into a detailed study note, turns past exams and homework into one cheatsheet per lecture, and builds the sheet you may bring to the exam. Everything for a subject lives in one folder that you open as an Obsidian vault.

```
/prof-eng init                      # once per subject: exam rules, tools, conventions
/prof-eng notes                     # phase 1: next lecture -> notes/L03-fourier-series.md
/prof-eng lecture-cheatsheet        # phase 2: next past exam -> solutions + cheatsheets/L03-cheatsheet.md
/prof-eng exam-sheet                # phase 3: A4 LaTeX sheet, open-book index, or nothing
/prof-eng status                    # what is left, what changed, what to review
```

## Requirements

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview).
- [Obsidian](https://obsidian.md): open each subject folder as a vault. Other Markdown viewers show callouts and `#page=` slide links incorrectly.
- Python 3, recommended: used for link checks, code checks of solutions and change detection. Optional Python packages: `sympy` (symbolic checks), `pypdf` (exact page counts), `PyMuPDF` (slide pictures).
- Optional: poppler (`pdftoppm`) or PyMuPDF to embed pictures of complex slide figures in the notes; a LaTeX distribution with `latexmk` (TeX Live, MiKTeX or MacTeX) to compile the A4 notes sheet and the [PDF output](#pdf-output), or compile the `.tex` in [Overleaf](https://www.overleaf.com); MATLAB, if you choose it at `init`.
- Optional, for PDF output: poppler's `pdftotext` and `pdfinfo` to check the page breaks of each PDF, and the Mermaid CLI (`mmdc`) to draw Mermaid diagrams in the PDFs.

## Install

The repo is public, so you don't need a GitHub login or collaborator access to clone it.

**Option A: let Claude do it.** Give Claude Code this prompt:

> Clone the repository at `https://github.com/teoperic/prof-eng-skill.git` into `~/prof-eng-skill` (if it already exists, run `git pull` there instead). Then make the skill available to me by symlinking `~/prof-eng-skill/skills/prof-eng` to `~/.claude/skills/prof-eng` (copy the folder instead if symlinks do not work on my system). Afterwards check that `~/.claude/skills/prof-eng/SKILL.md` exists and tell me whether I need to restart Claude Code for `/prof-eng` to appear.

**Option B: manual.** macOS/Linux:

```
git clone https://github.com/teoperic/prof-eng-skill.git ~/prof-eng-skill
mkdir -p ~/.claude/skills
ln -s ~/prof-eng-skill/skills/prof-eng ~/.claude/skills/prof-eng
```

Windows (PowerShell):

```
git clone https://github.com/teoperic/prof-eng-skill.git $HOME\prof-eng-skill
New-Item -ItemType Directory -Force $HOME\.claude\skills
Copy-Item -Recurse $HOME\prof-eng-skill\skills\prof-eng $HOME\.claude\skills\prof-eng
```

If `/prof-eng` does not show up, restart Claude Code.

**Update:** run `git pull` in `~/prof-eng-skill`. Symlink installs update immediately; Windows copy installs must copy the folder again. Subject folders keep no copies of the skill's templates, so the next run in every subject uses the updated ones. After an update, `/prof-eng status` reports a newer skill version, `/prof-eng init` adds any new settings, and `/prof-eng pdf` rebuilds the PDFs.

## Quick start

1. Create a folder for the subject (no spaces in the name, for example `Signals-and-Systems`).
2. Inside it, create `slides/` and put the lecture PDFs there. Put past exams in `exams/`, homework sheets in `homework/` and the textbook, if the course follows one, in `book/`.
3. Open the folder as an Obsidian vault.
4. Open Claude Code in that folder and run `/prof-eng init`. Answer its questions: what you may bring to the exam, which aids are allowed, which tools Claude may use, whether there is a textbook, and whether you want PDFs as well as Markdown. Then confirm the lecture IDs and homework mapping and approve the conventions it extracted (or edit `CLAUDE.md` first).
5. Run `/prof-eng notes`.

## Commands

| Command | What it does |
|---|---|
| `/prof-eng init` | Sets up the subject folder. Asks what you may bring to the exam (open or closed book, allowed aids), which tools Claude may use (Python, MATLAB, other), whether the course follows a textbook and whether you want PDFs next to the Markdown files. Then reads the first few lectures and proposes the course conventions (notation, units, methods, exam style), lecture IDs and homework mapping for your approval. Run once per subject. |
| `/prof-eng notes [Lxx]` | Turns one lecture into a detailed study note. Without an argument it takes the next lecture that has no note yet. |
| `/prof-eng lecture-cheatsheet [exam or Lxx] [--full]` | Adds one source to the lecture cheatsheets. A source is one past exam, or one lecture's homework and worked examples (`Lxx`), so courses without past exams still get cheatsheets. It solves and checks the source, then merges its problem types into the cheatsheet of the lecture each type belongs to. Without an argument it takes the next unprocessed exam, then the next lecture with unprocessed homework or examples. `--full` also rebuilds the formula section of every cheatsheet from the notes. |
| `/prof-eng exam-sheet` | Builds what you may bring to the exam, following the exam rules from `init`: nothing for a closed-book exam, a LaTeX A4 sheet (1 or 2 pages) when a notes sheet is allowed, or an index that tells you which lecture cheatsheet to open for each type of question in an open-book exam. Rerun it after new notes or cheatsheet runs. |
| `/prof-eng status` | Shows which lectures and exams are processed, what needs your review, changed source PDFs, an out-of-date exam sheet, missing or outdated PDFs, version drift and any warnings. |
| `/prof-eng check` | Verifies that all links and images resolve and every slide is covered by a note. |
| `/prof-eng pdf [file\|all]` | Rebuilds the PDF versions of notes, cheatsheets, solutions and the open-book index (only if you chose PDF output at `init`). Without an argument it rebuilds the missing and outdated PDFs, `all` rebuilds every one, and a file name rebuilds that file. Runs scripts only, so it uses almost none of your Claude usage. |
| `/prof-eng help` | Shows this table. |

## Weekly routine

- New lecture uploaded: put the PDF in `slides/`, run `/prof-eng notes`, then read the note next to the slides and set `status: reviewed` in its frontmatter.
- New past exam or homework: put it in `exams/` or `homework/`, then run `/prof-eng lecture-cheatsheet` once per source.
- Before the exam: run `/prof-eng exam-sheet`, then compile or print the result.
- Any time: `/prof-eng status` shows what is left, whether the exam sheet is out of date, and whether a professor re-uploaded a PDF.

## Exam formats

`init` asks what you may bring to the exam, and `/prof-eng exam-sheet` follows that answer:

- **Closed book:** nothing is built. Study from the lecture cheatsheets.
- **Single- or double-sided A4 sheet of notes:** a dense LaTeX sheet in `exam-sheet/exam-sheet.tex`, chronological by lecture, with each lecture's formulas and short definitions. If LaTeX is installed it is compiled to `exam-sheet/exam-sheet.pdf` and trimmed to 1 or 2 pages; otherwise compile it yourself (for example in Overleaf). To change the font size, line spacing or number of columns, edit the settings block at the top of the `.tex` file:

  ```latex
  \newcommand{\sheetfontsize}{7pt}     % font size (try 6pt-9pt)
  \newcommand{\sheetleading}{8pt}      % line spacing, about 1.15 x font size
  \newcommand{\sheetcolumns}{3}        % 2 or 3 columns
  ```

  The skill never changes the font size itself; it suggests one in its report if the sheet is far over or under the page budget.
- **Open book:** `EXAM-SHEET.md`, an index that tells you, for each type of question, which lecture cheatsheet and recipe card to open. The first time, it asks whether you also want `EXAM-SHEET-print.md`, a version without links that you can print from Obsidian. With PDF output, both also come as ready-to-print PDFs in `pdf/`.

## PDF output

If you choose "Markdown + PDF" at `init` (or later set `output_format: pdf` in the subject's `CLAUDE.md`), every note, cheatsheet, solution file and open-book index also gets a PDF, compiled locally with LaTeX:

- The PDFs live in `pdf/`, which mirrors the folder layout: `notes/L07-laplace-transform.md` becomes `pdf/notes/L07-laplace-transform.pdf`.
- 12pt on A4, with page breaks that keep headings with their text, callouts and short tables in one piece, and equations with the sentence that introduces them.
- Links stay clickable: slide links open the slide PDF at that page, and links to other notes or cheatsheets open their PDF at that heading. Self-test answers move to an "Answers" section at the end, with page references for paper.
- The Markdown stays the source. Each PDF is rebuilt from it after every run that changes the file; `/prof-eng pdf` rebuilds missing or outdated PDFs without using Claude for the content.
- Never edit the generated `.tex` files in `pdf/`; they are overwritten on every build.

Without LaTeX, the skill still writes the `.tex` files and `/prof-eng status` lists them as not compiled. You can compile them in Overleaf: upload the `.tex` together with the images it uses (`notes/img/`, `solutions/img/`, and `.prof-eng-build/mermaid/` for drawn diagrams), keeping the same folder layout.

## Confidence flags

Every solution and recipe card carries one label:

| Label | Meaning |
|---|---|
| `algebra-checked` | Code checking the maths was saved in `solutions/checks/`, ran, and agrees. |
| `matches-solution` | An independent solve agrees with a solution file in `exams/` or the textbook's solution. |
| `consistent-with-lectures` | Method and result match the lectures, without a code check. |
| `uncertain` | Something disagrees or is unclear. Spot-check these first. |

`algebra-checked` only means the maths of Claude's setup is right. Always compare the **Given** line with the PDF, because a misread statement or figure is the most common error and no code check can catch it. Solution files from other students (`<exam>-solution.pdf` in `exams/`) are compared against, never trusted.

## Homework and academic integrity

The skill never solves homework that you say is currently graded or not yet submitted. It only transcribes the statements and sorts them into problem types; rerun `/prof-eng lecture-cheatsheet Lxx` after the deadline. Solution files put all problem statements first, so try each problem before you read its solution.

## Cost and usage

Every run reads a whole lecture or exam as PDF pages (plus some textbook pages and a verification pass), which uses a noticeable share of your Claude plan's usage. Run one command at a time, and expect long lectures or scanned exams to cost more. If a run is cut off, run the same command again; it resumes where it stopped.

## Copyright and privacy

This repo is public, so contributors must never commit slides, exams, homework, books, notes, images or solutions from real courses. Subject folders get a `.gitignore` for the source material, but notes, slide images, cheatsheets, solutions and their PDFs are derived from copyrighted material too: keep subject folders out of any public repo, and share notes only if your university allows it.

## Limitations

- Notes follow the professor's notation and may contain errors. Open the note next to the slides when you study.
- Handwritten or low-quality scans, which are common for past exams, may be misread.
- The page fit of the LaTeX sheet is only checked when LaTeX is installed, and the page breaks of the PDFs only when LaTeX and poppler are installed.

## Development

`python3 -m unittest discover tests` runs the script tests. `python3 tests/make_fixtures.py /tmp/demo` creates a small synthetic subject folder to try the skill on.

## License

MIT. See [LICENSE](LICENSE).
