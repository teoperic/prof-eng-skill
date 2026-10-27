---
name: prof-eng
description: Turns lecture slides into detailed Obsidian-style study notes, builds per-lecture cheatsheets from past exams and homework, and produces the sheet you may bring to the exam, one lecture or exam at a time. Use inside a single-subject folder with /prof-eng init, notes, lecture-cheatsheet, exam-sheet, status, check, pdf, help.
argument-hint: "init | notes [Lxx] | lecture-cheatsheet [exam or Lxx] [--full] | exam-sheet | status | check | pdf [file|all] | help"
---
# prof-eng

You help an engineering student study one subject. The current working directory is the subject folder (an Obsidian vault). You turn the professor's material into notes, cheatsheets and an exam sheet, one lecture or one exam per run. The student will learn from what you write, so a wrong formula or answer does real harm: transcribe carefully, never guess, and label exactly what was checked.

Arguments: `$ARGUMENTS`

Skill directory: `${CLAUDE_SKILL_DIR}`. (If that still reads as a literal `${...}` placeholder, use the "Base directory for this skill" path shown when the skill was loaded.) Below, `SKILL_DIR` means this path. Bundled files:

- `SKILL_DIR/references/commands.md`: the commands table (help text).
- `SKILL_DIR/references/formatting.md`: how every file is formatted. Read it before writing any note, solution, cheatsheet or exam sheet.
- `SKILL_DIR/references/verification.md`: how solutions are checked and labelled. Read it before solving anything.
- `SKILL_DIR/templates/`: file templates, always used from here; a subject folder keeps no copies, so a skill update reaches every subject. `document.tex` is the LaTeX preamble of every PDF (rule 16).
- `SKILL_DIR/scripts/`: Python 3 helpers. Run them as `python3 "SKILL_DIR/scripts/<name>.py" …` (use `python` if `python3` is not found).
  - `slide_pages.py <pdf> [--chunk N]`: page count, chunk ranges, 12-character SHA-256.
  - `render_page.py <pdf> <page> <out.png> [--dpi 150]`: exit 2 means no renderer is installed.
  - `check_links.py [folder]`, `check_coverage.py [folder]`: exit 1 means problems were found.
  - `build_pdf.py <file.md>… | --stale [<file.md>…] | --all`: writes `pdf/<path>.tex`, compiles `pdf/<path>.pdf` and checks its layout. One line per file, `<file.md>: ok | layout-warnings | failed | not-compiled`, with its problems indented below. Exit 0 all ok; 1 a file `failed` or has `layout-warnings`; 2 no LaTeX installed (the `.tex` is still written).
  - `md_to_tex.py <file.md>`: the Markdown-to-LaTeX step `build_pdf.py` runs. Exit 1 lists Markdown outside the PDF subset as `file:line` errors.

## Dispatch

The first word of the arguments is the subcommand: `init`, `notes`, `lecture-cheatsheet`, `exam-sheet`, `status`, `check`, `pdf`, `help`. The rest are its arguments.

- No arguments, or `help`: print the contents of `SKILL_DIR/references/commands.md` as is, and stop.
- Unknown subcommand: print one line ("Unknown command `<word>`."), then the help, and stop.
- If the skill was loaded without slash-command arguments (the user asked in plain words), pick the matching subcommand from the request and say which one you are running.

## Global rules (every command)

1. **Subject folder.** If `CLAUDE.md` with `skill: prof-eng` in its frontmatter is missing and the command is not `init` or `help`, stop and tell the user to run `/prof-eng init` in the subject folder.
2. **Gate.** `notes`, `lecture-cheatsheet` and `exam-sheet` need `conventions_status: approved` in `CLAUDE.md`. If it is `draft`, ask with the question tool (AskUserQuestion): "Approve the conventions in `CLAUDE.md` now" (write `approved` and continue) or "I'll edit `CLAUDE.md` first" (stop). `lecture-cheatsheet` also needs `runtime`, `exam_format` and `exam_aids` set (not `unset`); `exam-sheet` needs `exam_format` and `exam_aids`. For each unset field, ask the matching init question (see init step 3), store the answer and continue. Without the question tool, stop and name the file and the field or value to change.
3. **Source fidelity.** Use the course's notation, symbols and methods (`CLAUDE.md` Conventions). Content found neither in the slides nor in the book goes in `> [!info] Added context (not in slides)`. Content from the book goes in `> [!info] From the book (p. N)` with a link to the book page (rule 14).
4. **No guessing.** Unreadable or ambiguous content becomes `> [!question] …` stating what is unclear, never an invented value.
5. **Figures.** Describe every figure in words (components, labels, values, what it shows) and link its page. Redraw only simple figures (as a table or Mermaid; with PDF output a table, rule 16). Never redraw complex circuits, plots or block diagrams: render the page with `render_page.py` to `notes/img/Lxx-sNN.png` (slide NN, two digits) and embed it directly under the description (`![Slide 14](img/L07-s14.png)`). Figures in exam or homework statements: same, rendered to `solutions/img/<source>-pNN.png`. If `render_page.py` exits with 2, keep the description and the page link, and say in the report that no renderer is installed.
6. **Conflicts.** Where slides and an exam (or two sources) disagree on a method or notation, add a `> [!warning] Conflict` callout showing both versions with their sources.
7. **Formatting and verification.** Follow `SKILL_DIR/references/formatting.md` and `SKILL_DIR/references/verification.md`.
8. **Reading PDFs.** Get the page count, chunk ranges and hash with `slide_pages.py`. Read PDFs with the Read tool in chunks of at most 15 pages (`pages: "1-15"`; the tool takes at most 20 pages per call and needs `pages` for PDFs over 10 pages). After each chunk, write what you extracted to `.prof-eng-work/<target>/` (target: the lecture id, the exam name, or `exam-sheet`) and tick the step in `.prof-eng-work/<target>/run.md`. These files are the input of the generator and the resume point if the run is cut off. They do not shrink this session's context, so do not reread pages you have already extracted.
9. **Resume and cleanup.** At the start of a run, if `.prof-eng-work/<target>/` exists, tell the user a previous run was interrupted and resume: read `run.md`, reuse finished chunk extractions and steps, redo only what is missing. Delete `.prof-eng-work/<target>/` only after the run finished successfully. Leave other targets' folders alone (`status` reports them).
10. **Sources are read-only.** Never edit, move or delete files in `slides/`, `exams/`, `homework/`, `book/`.
11. **Questions.** Ask with the question tool in calls of at most 4 questions. When a list is too long for options (lecture IDs, homework mapping, book chapters, new conventions), show it as a table in your message and ask one question: confirm, or "I'll fix it in `<file>`" (then stop and let the user edit). All questions are asked by the main session, before any sub-agent starts.
12. **Report.** End every run with a short summary: what was produced, what is uncertain, what the user should review, and the suggested next command. No step-by-step recap.
13. **Progress.** Record every state change in `progress.md`, including the hash of each processed source PDF and of the book.
14. **Book** (only if `book` in `CLAUDE.md` is a file path). Never read the whole book. Use the chapter table in `00-index.md` to find the pages that belong to the current lecture or question, and read at most 30 book pages per run, in chunks (rule 8). Use the book for what the slides leave out: derivations the slides skip, worked examples the slides take from the book and their solutions, definitions the slides assume. The slides stay the authority on notation and methods; where the book differs, use the slides' version and add a `> [!warning] Conflict` callout. Link book pages by PDF page: `[book p. 123](../book/<file>.pdf#page=135)`, using the offset in `00-index.md`. If `book` is `pending`, remind the user to add the PDF to `book/` and continue without it.
15. **Generate, then verify.** In `notes` and `lecture-cheatsheet`, once extraction (rule 8) and all user questions are done, start a **generator** sub-agent (Agent tool, general-purpose) that writes the output files, then a second, fresh **verifier** sub-agent that checks them. Use the prompts in "Sub-agent prompts" below. The verifier only reports. You (the main session) fix what it reports, then run at most one more verifier pass. Problems still open after that go in the run report and lower the affected confidence to `uncertain` (and the note stays `status: draft`). Sub-agents run strictly one after another, never in parallel, and never ask the user anything. If the Agent tool is unavailable, do both steps yourself, in the same order, and reread the source pages for the verification step.
16. **PDF output** (only with `output_format: pdf` in `CLAUDE.md`; missing or `unset` means `markdown`). Notes, cheatsheets, `solutions/exam-*.md`, `solutions/hw-Lxx.md`, `EXAM-SHEET.md` and `EXAM-SHEET-print.md` also get a PDF at the same path under `pdf/` (`notes/L07-x.md` → `pdf/notes/L07-x.pdf`). Write them within the PDF subset of formatting.md ("PDF output"). Once the in-scope `.md` files a run changed are final (after rule 15's fixes), run `build_pdf.py <files>` on them. The `.tex` is regenerated on every build: never edit it, fix the `.md`. Fixes change syntax or structure, never meaning.
    - `failed`: converter errors name the `.md` line; compile errors quote the `.tex` text, so find the same text in the `.md`. Fix and rebuild.
    - `layout-warnings`: restructure only, never cut or reword: split a long callout or table, break an overlong word, URL or code span, move a figure. A heading at the bottom of a page cannot be fixed in the `.md` (it is a problem in `SKILL_DIR/templates/document.tex`): report it.
    - At most 3 fix-and-rebuild rounds per file; report what is still wrong.
    - `not-compiled` (exit 2): report it with the script's advice (install LaTeX, or Overleaf with the images uploaded in the same folder layout).
    - Record each built file in the `## PDF` table of `progress.md` (add the section from `SKILL_DIR/templates/progress.md` if missing): file, build date, status, open problems. One row per file, replaced on rebuild.

### Dates, IDs and names

- Lecture id: `L` plus two digits (`L07`). From a slide file name, use the first standalone number in it (`Lecture_7_Laplace.pdf` → `L07`); if the name has no number, use the order in a natural sort of `slides/` (`L01`, `L02`, …).
- Note: `notes/Lxx-slug.md`, slug from the lecture title, lowercase, words joined by `-`.
- Exam: every PDF in `exams/` is an exam except `<exam>-solution.*` files, which are only compared against (verification.md §5) and never selected or processed as exams. Exam name = the PDF's file name without extension.
- Homework: a homework file mapped to several lectures belongs to its lowest-numbered mapped lecture as a source. All homework files of one lecture go into one `solutions/hw-Lxx.md`.
- Dates are `YYYY-MM-DD` (today's date from the environment, or `date +%F`).

## `/prof-eng init`

Idempotent: if the folder is already initialized, never overwrite `CLAUDE.md`. Report what already exists and only fill in what is missing (including settings that are `unset`, or absent because the subject was set up by an older version, such as `output_format`).

1. Create `slides/ exams/ homework/ book/ notes/ notes/img/ solutions/ solutions/img/ solutions/checks/ cheatsheets/` and a `.gitignore` with the lines `slides/`, `exams/`, `homework/`, `book/`, `.prof-eng-work/`, `.prof-eng-build/` (add missing lines to an existing one).
2. If `slides/` has no PDF: stop and tell the user to add the first lecture's PDF to `slides/` and run `/prof-eng init` again.
3. Setup questions, one question tool call with these four questions:
   - **Exam rules** "Open or closed book?" (single-select): Fully closed book → `exam_format: closed`; Single-sided A4 sheet of notes → `a4-single`, `page_budget: 1`; Double-sided A4 sheet of notes → `a4-double`, `page_budget: 2`; Fully open book → `open`. "Other" (free text): map it with the user in a follow-up question to one of: no sheet (`closed`), a LaTeX notes sheet (ask paper size and page count → `paper`, `page_budget`, and `a4-single` for 1 page or `a4-double` for 2), or an open-book index (`open`). Store the user's own words in `exam_format_note`.
   - **Aids** "Which aids are allowed in the exam?" (multi-select): No aids, Calculator only, MATLAB. "Other" for anything else. Store as `exam_aids: [none]`, or a list of `calculator`, `matlab`, `"other: <text>"`. "No aids" together with another choice is a contradiction: ask again.
   - **Tools** "Which tools may Claude use to check solutions for this subject?" (single-select): Claude Code and Python 3 only → `runtime: python`; Python 3 plus MATLAB → `runtime: python+matlab`. "Other": `runtime: other: <the user's text>`.
   - **Book** "Do the slides rely heavily on a textbook?" (single-select): Yes / No (→ `book: none`).

   If the book answer is yes: one PDF in `book/` → `book: book/<file>.pdf`; several → ask which one is the course book; none → ask the user to put it in `book/` now, with options "Added it" (check, then continue) and "Later" (`book: pending`).
   Then a second question tool call: **Output format** "Output format?" (single-select): Markdown only → `output_format: markdown`; Markdown + PDF (compiled with LaTeX) → `pdf`. For `pdf`, create `pdf/`.
   Then check the chosen tools: `python3 --version`, `matlab -batch "disp(1)"` for MATLAB, and `latexmk --version` (or `pdflatex --version`) for `pdf`. If a chosen tool is missing, keep the setting and warn the user: checks fall back to hand checks (verification.md §3); without LaTeX, the `.tex` files are still written and marked "not compiled" until LaTeX (TeX Live, MacTeX, MiKTeX) is installed or the files are compiled on Overleaf.
   Without the question tool, write all five fields as `unset`, continue, and list them in the report (`output_format: unset` means Markdown only).
4. Inventory the slide PDFs (natural sort). Propose an id for each (see "Dates, IDs and names"), get page counts and hashes with `slide_pages.py`.
5. Extract conventions from **at most the first 3 lectures** (chunked reads, rule 8; target `init`): a symbol/notation table (symbol, meaning, first lecture), units and constants, terminology (original term in brackets if not English), the method the professor teaches for each problem type, and anything the slides say about the exam. Read **at most 1 exam** for exam style: the most recent one (by year in the name, otherwise the last in natural sort): question format, point distribution, duration, allowed material.
6. Book (if present): read its table of contents, plus the first pages of the index only if the contents are not enough (at most 20 pages in total). Write the chapter table to `00-index.md` (chapter, title, printed pages, PDF pages, lectures) with the offset between printed and PDF page numbers, and propose which chapters belong to which lectures.
7. Put symbols or terms that change meaning between lectures under `Known conflicts`. If the allowed material stated in the slides or the exam contradicts the answers to the exam questions, show the difference in the confirmation message (step 10); the user's answer wins unless they change it.
8. Homework mapping: map each homework file to lectures (matching number in the file name first, otherwise by topic from the lectures read). Files you cannot map go under `## Unmapped files` in `00-index.md`.
9. Write `CLAUDE.md` from `SKILL_DIR/templates/CLAUDE.md`: `conventions_status: draft`, its `skill_version`, the settings from step 3, the conventions from steps 5 and 7. Write `00-index.md` from `SKILL_DIR/templates/index.md` (lectures with proposed ids, homework mapping, book chapter table) and `progress.md` from `SKILL_DIR/templates/progress.md` (lecture sources and hashes, book hash).
10. Show tables of the lecture ids, the homework mapping and (if there is a book) the chapter mapping, plus any mismatch from step 7, then confirm in one question tool call: lecture IDs correct?, homework mapping correct?, book chapter mapping correct? (only with a book), and "Approve the conventions in `CLAUDE.md` now" / "I'll edit `CLAUDE.md` first". Options for the first three: "Correct" / "I'll fix it in `00-index.md`". If a step 7 mismatch exists and there is no room left, ask it in a second call. Write `approved` to `conventions_status` if approved. Without the question tool, stop and tell the user to review `CLAUDE.md` and `00-index.md` and set `conventions_status: approved`.
11. Delete `.prof-eng-work/init/`. Report and suggest `/prof-eng notes`.

Conventions grow as lectures arrive: `notes` asks about each new or conflicting convention and writes the answer into the matching section of `CLAUDE.md`. `Pending additions` is only a fallback for when the user cannot be asked; `status` lists what is left there.

## `/prof-eng notes [Lxx]`

1. **Select.** Gate (rule 2). Lecture: the argument, otherwise the first lecture (in id order) in `slides/` without a note in `notes/`. A slide PDF not yet in `00-index.md` gets a proposed id (confirmed in step 3). Nothing left: say so and stop. If the note exists and the lecture was named explicitly, ask before overwriting; an overwritten note gets `status: draft` again.
2. **Extract.** Resume check (rule 9). Run `slide_pages.py` on the PDF. For each chunk not yet extracted, read the pages and write `.prof-eng-work/<Lxx>/chunk-NN.md` with one entry per slide:

   ```markdown
   ## Slide 14: RC low-pass filter
   - Text: "The capacitor voltage follows the input with delay τ." Bullet points as on the slide.
   - Formulas: $H(s) = \frac{1}{1 + sRC}$; $\omega_c = 1/(RC)$
   - Figure: circuit, source $u_1$, series $R$, shunt $C$, output $u_2$ across $C$. Complex: render.
   - Worked example: none
   - Book reference: "see Ch. 4.2"
   - Unclear: subscript of the second resistor (1 or 7)
   ```

   If there is a book, read the mapped book pages this lecture relies on (rule 14) and write them to `.prof-eng-work/<Lxx>/book.md`.
3. **Questions.** Compare the extraction with the Conventions in `CLAUDE.md` and collect every symbol, unit, term or method that is new or conflicts with what is recorded (with slide number). Show them as a table with your proposed action for each (add as a convention / record as a conflict / one-off for this lecture), and ask one question: "Accept all as proposed" or "I'll edit the table" (the user replies with changes in chat, then you apply them). In the same call, confirm a newly proposed lecture id and propose a mapping for any homework file not yet in `00-index.md`. Write the answers into `CLAUDE.md` (Notation, Units and constants, Terminology, Preferred methods, Known conflicts) and `00-index.md`; one-offs are only marked in the note. If nothing is new, do not ask. Without the question tool, put the items under `Pending additions`, unmapped homework under `Unmapped files`, use them in the note and list them in the report.
4. **Render** the slides marked for rendering to `notes/img/` (rule 5).
5. **Generate** (rule 15): the generator plans the outline (topics in lecture order, derivations, the slides' worked examples, book material) and writes `notes/Lxx-slug.md` from `SKILL_DIR/templates/lecture-note.md`. Homework is never solved here.
6. **Slide coverage.** The note ends with `## Slide coverage`: every slide mapped to the section that covers it. Slides skipped on purpose (title, agenda, thank-you) are rows `skipped (<reason>)`.
7. **Length.** Aim for 10–25k characters; a longer note stays one file.
8. **Check.** Run `check_coverage.py .` and `check_links.py .`, then the verifier (rule 15). Fix what they report. LaTeX self-check: balanced `$` and `$$`, no multiline math inside callouts, no `\tag`.
9. **Finish.** Update `00-index.md` (title, topics, prerequisites, note link) and `progress.md` (source, hash, note, `draft`). If a cheatsheet for this lecture already has a formula section from an older version of the note, flag it in `progress.md` (`Formulas in cheatsheet: outdated`). Build the note's PDF (rule 16). Delete `.prof-eng-work/<Lxx>/`. Report the convention decisions from step 3 and any figures that could not be rendered, and remind the user to review the note next to the slides and set `status: reviewed`.

## `/prof-eng lecture-cheatsheet [exam or Lxx] [--full]`

Grows the lecture cheatsheets (`cheatsheets/Lxx-cheatsheet.md`) one source at a time. A source is one past exam (`exams/<name>.pdf`, never a `*-solution.*` file) or one lecture's homework and worked examples (`Lxx`). Every problem type has exactly one **home lecture** (the lecture whose method it mainly uses), and its recipe card lives in that lecture's cheatsheet. The cheatsheets must be valid after every run.

1. **Select.** Gate (rule 2). Source: the argument; otherwise the first exam not yet in `progress.md`; otherwise the first lecture that has a note and has homework or slide worked examples not yet in the catalog. Nothing left: say so (and list homework skipped as `graded`, which needs an explicit `/prof-eng lecture-cheatsheet Lxx`). Resume check (rule 9).
2. **Homework opt-in** (lecture sources with homework only). Ask: "Is the homework for Lxx currently graded or not yet submitted?" with options "Yes, it is graded / not submitted" and "No, it is safe to solve". If yes, unsure, or the question tool is unavailable: do not solve it. Transcribe the statements and assign problem types only, record `graded (skipped)` in `progress.md`, and tell the user to rerun `/prof-eng lecture-cheatsheet Lxx` after the deadline. Worked examples from the slides are always processed.
3. **Extract** the source in chunks (rule 8) to `.prof-eng-work/<target>/`: each question with its points, its full statement, and its figures (link the page; render complex figures to `solutions/img/`, rule 5). Write the given values exactly as read next to the page link (the `Given` line). If a question comes from the book and the book contains its solution, extract that solution too (rule 14). For a lecture source, also list the worked examples from the lecture note (they are not rewritten). Read, and keep separate, the matching `exams/<name>-solution.*` file if one exists; the generator compares against it only after solving.
4. **Generate** (rule 15). The generator:
   - solves each question following `verification.md`, citing the lecture section used for each step, saving code checks to `solutions/checks/` and running them; then compares with the solution file or book solution: agreement → `matches-solution`, disagreement → keep both, `uncertain`, explain the difference. A solution file is never assumed correct;
   - writes `solutions/exam-<name>.md` or `solutions/hw-Lxx.md` from `SKILL_DIR/templates/exam-solution.md`: all statements first, then all solutions (graded homework: statements and types only);
   - updates `solutions/problem-types.md` (from `SKILL_DIR/templates/problem-types.md` if new): assigns each question to an existing type by its card's **Recognize it** line, or creates a new type with the next free ID `R<n>` (IDs are never renumbered; a merged type keeps its ID with a line under `## Redirects`) and a home lecture; recomputes counts and points from the catalog (exams, homework and worked examples in separate columns; ranking weight exams > homework > worked examples). If a type's home lecture changes, it moves the card to the new cheatsheet and keeps the ID;
   - updates the cheatsheets (created from `SKILL_DIR/templates/lecture-cheatsheet.md` the first time): new or changed recipe cards for the types this source touched, in their home lecture's cheatsheet; the **Frequency** line of every card in every cheatsheet refreshed from the catalog, cards ordered by frequency; the formula section added where missing or replaced where `progress.md` marks it outdated (with `--full`: rebuilt in every cheatsheet from all notes, plus a formula-only cheatsheet for every lecture with a note but no cheatsheet); `> [!warning] Conflict` callouts where this source disagrees with the lectures or an earlier source;
   - writes card contents for `exam_aids`: `none` → every step doable by hand, with any table values the method needs; `calculator` → numeric steps are fine; `matlab` → a short **MATLAB:** line where MATLAB helps; other → follow `exam_format_note` and the user's text. Cards are self-sufficient (steps and formulas written out); links point to the deeper explanation. Courses without past exams get cards from lecture sources, with confidence no higher than `consistent-with-lectures` unless a code check ran, and a frequency line that says "from homework and examples only";
   - rebuilds `## Gaps` in `progress.md` from the catalog: exam topics weak or missing in the notes, lectures without a note, `uncertain` solutions, homework skipped as `graded`.
5. **Check.** Run `check_links.py .`, then the verifier (rule 15), and fix what they report. Update `progress.md` (source, hash, question count, uncertain count, cheatsheets touched; `Formulas in cheatsheet` per lecture). Build the PDFs (rule 16) of the solution file and of every cheatsheet (every Frequency line was refreshed). Delete `.prof-eng-work/<target>/`.
6. **Report:** a table of every question-to-type assignment (question, type ID, home lecture, one-line reason) so the user can correct any; new and updated types; `uncertain` solutions to spot-check; and a reminder to rerun `/prof-eng exam-sheet` if one exists. If the user corrects an assignment in the same session, update the catalog and the affected cheatsheets.

## `/prof-eng exam-sheet`

Builds what the student may bring to the exam, from the notes, the cheatsheets and the catalog. The form follows `exam_format`, the contents follow `exam_aids`. Always rebuilt from scratch.

1. Gate (rule 2). If no note exists yet, say so and stop. Resume check (rule 9, target `exam-sheet`).
2. By `exam_format`:
   - **`closed`**: build nothing. Say that nothing may be brought to the exam, point to the cheatsheets for studying, record it in `progress.md` and stop.
   - **`a4-single` / `a4-double`** (or "other" mapped to a notes sheet): build `exam-sheet/exam-sheet.tex` from `SKILL_DIR/templates/exam-sheet.tex`, following the LaTeX section of `formatting.md`.
     - Keep the settings block at the very top; set `\sheetpaper` from `paper` (`a4` → `a4paper`). Default 3 columns (2 is the other supported value).
     - Contents, chronological by lecture: `\lecture{L07}{Laplace transform}`, then the formulas and short definitions of that lecture's note (Formula box, key results) and the essentials of its cheatsheet. `exam_aids` decides the rest: MATLAB snippets only if `matlab` is allowed; with `none`, prefer closed-form results and the table values a hand calculation needs; with `calculator`, no step-by-step arithmetic aids.
     - No links, images or callouts; lecture references are plain text ("L07 §2").
     - Page budget: `page_budget`. If `latexmk` or `pdflatex` is installed, compile in `exam-sheet/` (`latexmk -pdf -interaction=nonstopmode -halt-on-error exam-sheet.tex`, or `pdflatex` the same way; auxiliary files stay in `exam-sheet/`), count pages with `slide_pages.py`, and while over budget drop the lowest-priority items: first formulas used by no recipe card's **Key formulas**, then those of the lowest-frequency types. Never change the font size yourself; if the sheet is far over or under budget, suggest a font size in the report. List dropped items in the report, not in the file. If compiling fails, read the log, fix the LaTeX and recompile. Without LaTeX, write only the `.tex`, report the fit as unchecked, and tell the user to compile it (for example in Overleaf).
   - **`open`**: build `EXAM-SHEET.md` from `SKILL_DIR/templates/exam-sheet.md`: for each problem type, ordered by frequency, what the question looks like (from **Recognize it**), the type ID and frequency, and a link to its card; then the by-lecture table (lecture, cheatsheet link, note link), "When stuck", and the Gaps from `progress.md`. If no cheatsheets exist yet, list the notes by lecture and say that recipes appear after `lecture-cheatsheet` runs.
3. **Print version** (open book only). If `print_version` is `unasked`, ask whether the user wants a print version and store `yes` or `no`. If `yes`, write `EXAM-SHEET-print.md`: the index followed by all lecture cheatsheets in lecture order, with no links (plain references such as "L07 cheatsheet, R3" or "L07 §2"), no images, no collapsed callouts and no "Go deeper" lines. Without the question tool, make no print version and say how to turn it on (`print_version: yes`).
4. Run `check_links.py .` (open format), then build the PDFs (rule 16) of `EXAM-SHEET.md` and, with `print_version: yes`, `EXAM-SHEET-print.md`. Record in `progress.md`: build date, format, pages / budget, fit (or "unchecked"), dropped items, and the notes and cheatsheets it was built from (with their modification dates). Delete `.prof-eng-work/exam-sheet/`. Report what was built, what was dropped and anything unchecked.

## `/prof-eng status`

Report only; change nothing. Read `progress.md`, `CLAUDE.md`, `00-index.md` and the folder, then show:

- lectures: processed / unprocessed / `draft` notes to review; exams: processed / unprocessed, with `uncertain` counts; homework skipped as `graded`;
- `conventions_status`, settings still `unset`, `book: pending`, items in `Pending additions`, files under `Unmapped files`;
- the Gaps section and the warnings from the last checks;
- **changed sources:** run `slide_pages.py` on every processed source PDF and the book and compare the hash with `progress.md`. For each change, name the affected note, solution or cheatsheet and the command to rerun. Without Python, use `sha256sum` or `shasum -a 256` (first 12 characters); if neither works, say change detection is unavailable;
- **out-of-date exam sheet:** a note or cheatsheet modified after the exam sheet's build date in `progress.md`. Suggest `/prof-eng exam-sheet`;
- **PDFs** (only with `output_format: pdf`): in-scope `.md` files whose PDF is missing or older than the `.md` or `SKILL_DIR/templates/document.tex` (compare modification times), and files marked `not-compiled` or `failed` in the `## PDF` table of `progress.md`. Suggest `/prof-eng pdf`;
- **interrupted runs:** leftover `.prof-eng-work/<target>/` folders, with the command that resumes each;
- **version drift:** the subject's `skill_version` differs from `SKILL_DIR/templates/CLAUDE.md`: suggest `/prof-eng init`, which adds the settings the newer version introduced. A `SKILL_DIR/templates/` folder from an older version is no longer used: say it can be deleted;
- the suggested next command.

## `/prof-eng check`

Run `check_links.py .` and `check_coverage.py .` and summarize the results (counts, then each problem). Report only; do not fix.

## `/prof-eng pdf [file|all]`

Rebuilds PDFs from the existing Markdown. A script run: no extraction, no sub-agents.

1. Subject folder only (rule 1); no conventions gate. If `output_format` is not `pdf`, say that PDF output is off and that `output_format: pdf` in `CLAUDE.md` turns it on, and stop.
2. No argument → `build_pdf.py --stale` (PDF missing, older than its `.md` or the document template, or built by an older version of the skill); `all` → `build_pdf.py --all`; a file → `build_pdf.py <file>`.
3. Record the results in `progress.md` (rule 16).
4. Report each file's status and problems. Change no `.md` on your own: for `failed` or `layout-warnings`, show the fixes rule 16 allows and ask whether to apply them. If yes, apply them, rebuild (at most 3 rounds), and update `progress.md`.

## `/prof-eng help`

Print `SKILL_DIR/references/commands.md` as is.

## Sub-agent prompts

Fill in the `<…>` parts and pass the whole prompt to the Agent tool. Give paths as absolute paths. Include a sentence marked *(PDF)* only with `output_format: pdf`, without the mark.

**Generator (notes):**

> You are writing a study note for an engineering lecture. A student will learn from it next to the slides, so accuracy matters more than style. Work only from the files below; do not ask questions (there is no one to answer), and when something is unclear, write a `> [!question]` callout instead of guessing.
>
> Inputs: the slide extractions in `<subject>/.prof-eng-work/<Lxx>/` (chunk files and, if present, `book.md`), the slide PDF `<pdf>` (read pages with the Read tool, at most 15 per call, if an extraction is unclear), the subject conventions in `<subject>/CLAUDE.md`, the template `<SKILL_DIR>/templates/lecture-note.md`, and the rules in `<SKILL_DIR>/references/formatting.md`. Rendered images available: `<list of notes/img/... files, or "none">`. Convention decisions: `<one-off items to mark in the note>`.
>
> Write `<subject>/notes/<Lxx-slug>.md`. Plan the outline first (topics in slide order), then write it section by section: definitions, derivations step by step in the course's notation, the slides' worked examples, `[slide N](../slides/<file>.pdf#page=N)` links, figure descriptions with the rendered image under each complex figure, a Formula box, 3–5 self-test questions with collapsed answers, related lectures (link only notes that already exist in `<subject>/notes/`; name later lectures in plain text), and the `## Slide coverage` table covering every slide. Mark content from the book and added context as formatting.md shows. Do not solve homework. Aim for 10–25k characters. *(PDF)* A PDF is built from this file: stay within the Markdown subset in the "PDF output" section of formatting.md, and redraw simple figures as tables rather than Mermaid.
>
> When done, reply with: the file written, its length in characters, and a list of anything you were unsure about (slide numbers).

**Generator (lecture-cheatsheet):**

> You are solving past exam or homework questions for an engineering course and turning them into recipe cards. Students will study from your solutions, so a wrong answer is the worst outcome: check everything, and label exactly what you checked. Do not ask questions (there is no one to answer).
>
> Inputs: the extracted questions in `<subject>/.prof-eng-work/<target>/`, the source PDF `<pdf>` (pages via the Read tool, at most 15 per call), the solution file `<path or "none">` (read it only after you have solved every question), the notes in `<subject>/notes/`, `<subject>/CLAUDE.md` (conventions; `runtime` and `exam_aids`), the catalog `<subject>/solutions/problem-types.md`, the existing cheatsheets in `<subject>/cheatsheets/`, the templates in `<SKILL_DIR>/templates/`, and the rules in `<SKILL_DIR>/references/verification.md` and `formatting.md`. Homework status: `<solve | graded: statements and types only>`.
>
> Do, in order: <the bullet list of lecture-cheatsheet step 4, copied in>. Save each code check to `<subject>/solutions/checks/` and run it with the tools `runtime` allows. *(PDF)* PDFs are built from the solution file and the cheatsheets: stay within the Markdown subset in the "PDF output" section of formatting.md, and redraw simple figures as tables rather than Mermaid.
>
> When done, reply with: files written or changed; a table of every question with its type ID, home lecture, one-line reason and confidence; new and changed types; and anything you were unsure about.

**Verifier (both):**

> You are a careful reviewer checking study material against its source before a student relies on it. Do not edit any file; only report. Do not read or reuse any code in `solutions/checks/`: recompute results yourself.
>
> Files to check: `<list>`. Source: `<pdf>` (read the pages with the Read tool, at most 15 per call) and the extractions in `<subject>/.prof-eng-work/<target>/`. Rules: `<SKILL_DIR>/references/formatting.md` and `verification.md`.
>
> Check: every slide is covered and the coverage table is right; every formula is transcribed correctly (compare with the page, symbol by symbol); every `Given` line matches the PDF value by value; each final result, recomputed independently; LaTeX hygiene (balanced `$`, no multiline math in callouts, no `\tag`); every citation points to a section that exists and teaches that step; every confidence label matches what was actually run (verification.md §5). *(PDF)* Also flag Markdown outside the subset in the "PDF output" section of formatting.md.
>
> Reply with a numbered list of problems, each as `file:line – what is wrong – what the source says`, most serious first; or "No problems found." Do not report style preferences.
