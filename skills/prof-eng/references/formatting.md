# Formatting rules

These rules apply to every file the skill writes in a subject folder. The subject folder is opened as an Obsidian vault, so the target is Obsidian-flavored Markdown that also stays readable as plain Markdown.

## Markdown and callouts

- YAML frontmatter at the top of notes and solution files, exactly the fields in the template.
- Callout types in use: `note`, `abstract`, `important`, `example`, `warning`, `question`, `info`, `tip`. A collapsed callout adds `-` (`> [!tip]- Answer`).
- One callout per idea, a few lines at most. A callout is a highlight, not a container for a whole section.
- Tables for anything with columns (notation, formula boxes, coverage, catalogs).

Standard callouts with fixed wording (rules 3, 4 and 6 of SKILL.md):

```markdown
> [!info] Added context (not in slides)
> One or two sentences of explanation that is in neither the slides nor the book.

> [!info] From the book (p. 123)
> What the book adds. [Book p. 123](../book/<file>.pdf#page=135)

> [!question] Slide 17: the exponent of the second term is unreadable (looks like 2 or 3).

> [!warning] Conflict
> Slides (L04, slide 9): $v$ is the voltage across the capacitor.
> Exam 2023-jan Q2: $v$ is the voltage across the resistor.
```

## Math

- Inline math `$...$`, display math `$$...$$` with the `$$` on their own lines.
- Multiline derivations use `aligned` inside one display block.
- No multiline math inside callouts (Obsidian breaks it). Put the display block right after the callout instead.
- No `\tag`, no equation numbering. No `\begin{align}` outside `$$` (use `aligned`).
- No stray `$` in text: write "USD 5", not a dollar sign.
- Use the professor's symbols from the Notation table in `CLAUDE.md`.

Good:

```markdown
> [!important] Key result
> The time constant is $\tau = RC$.

$$
\begin{aligned}
v(t) &= V_0\, e^{-t/\tau} \\
i(t) &= -\frac{V_0}{R}\, e^{-t/\tau}
\end{aligned}
$$
```

Bad (multiline math inside a callout, `\tag`, `align` without `$$`):

```markdown
> [!important] Key result
> $$
> v(t) = V_0 e^{-t/\tau} \tag{1}
> $$
\begin{align} i(t) = ... \end{align}
```

## Links

- Standard relative Markdown links only: `[text](relative/path.md)`. No wikilinks (`[[...]]`).
- Heading anchors use the exact heading text, with spaces URL-encoded as `%20`: the heading `### 2. Partial fractions` is linked as `[L07 §2](../notes/L07-laplace-transform.md#2.%20Partial%20fractions)`. Links inside the same file start with `#`.
- Slide links: `[slide 14](../slides/L07.pdf#page=14)` (use the real slide file name).
- Book links use the PDF page number, not the printed page: printed p. 123 with offset 12 is `[book p. 123](../book/<file>.pdf#page=135)`. The offset is in `00-index.md`.
- Paths are relative to the file that contains the link. From `notes/` a slide is `../slides/…`; from `EXAM-SHEET.md` (subject root) a cheatsheet is `cheatsheets/…`.

## Headings

- Headings that are link targets must not contain LaTeX, `#`, `|`, `^`, `[`, `]` or backticks; these break anchors. Write `### 3. Transfer function of an RC filter`, not `### 3. $H(s)$ of an RC filter`.
- Keep headings short and unique within a file (two `### Example` headings cannot both be linked).

## Images

- Only rendered slide or exam pages (SKILL.md rule 5), rendered at about 150 dpi with `scripts/render_page.py`.
- Standard image syntax with a relative path and a meaningful alt text: `![Slide 14](img/L07-s14.png)` in a note, `![Page 2](img/2023-jan-p2.png)` in a solution.
- The image goes directly under the figure's written description, never instead of it.
- No `![[...]]` embeds and no note transclusion.

## Files and length

- No spaces in file or folder names. Notes are `Lxx-slug.md` with a short lowercase slug (`L07-laplace-transform.md`).
- Note length: aim for 10–25k characters. Longer notes are allowed and are never split into several files.
- Write in English. A term the slides give in another language keeps the original in brackets on first use: "transfer function (Übertragungsfunktion)".

## Print version (`EXAM-SHEET-print.md`)

- Only after the user said yes (`print_version: yes`).
- No links (replace with plain references: "L07 cheatsheet, R3", "L07 §2"), no images, no collapsed callouts, no "Go deeper" lines.

## LaTeX notes sheet (`exam-sheet/exam-sheet.tex`)

- Built from `_templates/exam-sheet.tex`; keep its settings block at the very top (font size, line spacing, columns, paper).
- 2 or 3 columns (`multicols*`, read top to bottom, then left to right), chronological by lecture: `\lecture{L07}{Laplace transform}` then that lecture's formulas and short definitions.
- Math copied from the notes must compile in plain LaTeX: no Obsidian-only syntax, no callouts, no links, no images, no Markdown. Lecture references are plain text ("L07 §2").
- Escape LaTeX special characters in text (`%`, `&`, `_`, `#`).

## PDF output

Only with `output_format: pdf` in `CLAUDE.md` (SKILL.md rule 16). The `.md` stays the source: `build_pdf.py` converts it to LaTeX and compiles it. Never write or edit the `.tex`; it is regenerated on every build. Change content in the `.md` and layout in `_templates/document.tex` (font size, paper, margins and line spacing are in its settings block at the top).

Files and folders:

- Notes, cheatsheets, `solutions/exam-*.md`, `solutions/hw-Lxx.md`, `EXAM-SHEET.md` and `EXAM-SHEET-print.md` get a PDF. Other files (`00-index.md`, `progress.md`, `problem-types.md`, `CLAUDE.md`) do not.
- `pdf/` mirrors the Markdown tree: `notes/L07-x.md` → `pdf/notes/L07-x.tex` and `pdf/notes/L07-x.pdf`; `EXAM-SHEET.md` → `pdf/EXAM-SHEET.pdf`. Auxiliary files go to `.prof-eng-build/`.

Supported Markdown (everything else stops the build with a `file:line` error):

- YAML frontmatter; one `#` title (further `#` headings, as in the print version, each start a new part on a new page); `##` to `####`.
- Paragraphs. Every line is its own paragraph, as Obsidian shows it.
- `**bold**`, `*italic*`, `` `code` ``, nested `-` and `1.` lists, pipe tables, `---`.
- `$...$` and `$$...$$`, passed through unchanged. A display block stays on the page of the paragraph just above it.
- Callouts of the eight types above, including collapsed ones.
- Images on a line of their own, with a local path.
- Fenced code blocks, plain ASCII only, with an optional language tag (`matlab`, `python`, …), and Mermaid blocks.
- Relative links and `http(s)` links.

Not supported: wikilinks and embeds, plain `>` quotes, other callout types, `==highlight==`, `~~strikethrough~~`, `_italic_` (use `*italic*`), footnotes, HTML and HTML comments, autolinks `<https://…>` (use `[text](url)`), `%%` comments, task lists `- [ ]`, reference links `[text][ref]`, underlined (setext) headings, `#####` and deeper, headings inside a list or callout, images inside a sentence or from a URL, image paths with spaces, `$$` inside a line of text, LaTeX environments outside `$$`, and characters that are neither built into pdflatex nor declared in the template (for example Chinese, emoji, rare symbols). Write a symbol as LaTeX math (`$\alpha$`) or add a `\DeclareUnicodeCharacter` line to `_templates/document.tex`; Greek letters and common math symbols such as `τ`, `≤` and `×` are already declared.

How the PDF differs from the Markdown:

- Links still work. A link to another file with a PDF opens that PDF at the same heading; a slide or book link opens the source PDF at that page (in desktop viewers such as Okular, Evince, Acrobat and Skim). Links within the file jump to the heading.
- Collapsed `> [!tip]- Answer` callouts move to an "Answers" section at the end. In their place stands "Answer n, p. x", linked to the answer, and each answer links back to its question. Other collapsed callouts are shown open.
- Headings `R<n> – <title>` become recipe-card boxes and `Q<n> solution` headings become solution boxes. Solution files start `## Solutions` on a new page.
- Callouts and tables of up to 15 rows never split across pages, so a callout taller than a page runs off its bottom (a layout warning): keep callouts short (as above) and tables inside callouts shorter still. Longer tables outside a callout may split and repeat their header on each page. Recipe cards, solution boxes and code blocks may split.
- A Mermaid block is drawn if `mmdc` is installed; otherwise the PDF shows its source. So redraw simple figures as tables rather than Mermaid.
- Files with `status: draft` (notes and solutions) carry a "DRAFT – not reviewed" header on every page.
