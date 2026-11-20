# IEEE Access draft — VaultTrust

**The master copy is `VaultTrust_IEEE_Access.docx`.** Since 18 Oct 2026 the authors edit it directly in
Word. Every number in the first draft came from `reports/eval/*.json`, and every reference is verified in
`docs/LITERATURE_NOTES.md`.

| File | Status |
|---|---|
| `VaultTrust_IEEE_Access.docx` | **Master.** Two-column IEEE Access-like layout, 10 pages, 14 figures, 6 tables, 43 references. Edit this one. |
| `VaultTrust_IEEE_Access.pdf` | Export of the 23 Oct version. Re-export from Word after editing (File → Save as → PDF). |
| `VaultTrust_IEEE_Access_backup_2026-10-21.docx` | The authors' version just before the 21 Oct edits (related work, wording). |
| `VaultTrust_IEEE_Access_backup_2026-10-23.docx` | The authors' version just before the 23 Oct edit (five report figures added). |
| `main.tex` | LaTeX first draft (17 Oct). **Frozen, not kept in sync with the Word file.** |
| `figures/`, `make_figures.py` | Figures, copied and trimmed from the report and evaluation outputs. No figure shows a face. |
| `build_docx.py` | Turns `main.tex` into a new .docx. Refuses to overwrite an existing file, so it can't replace the master. |

## Submitting

* IEEE Access asks for a source file (**Word or LaTeX**) and a matching PDF. When the Word draft is final,
  paste its content into the **official IEEE Access Word template** (from the IEEE Access "Submission
  Guidelines" page). This file imitates the template's look but isn't the template itself.
* `main.tex` is out of date as soon as the Word file changes. Use it only if you decide to switch to
  LaTeX/Overleaf, and copy your Word edits into it first.

## Before submitting

Done on 21 Oct: related work on chaotic/hash-chain OTPs (§II-D, refs [23]–[25]); new §II-F on face
authentication in payments with comparison Table 1 (refs [29]–[34]); field-use participants and consent;
CPU and RAM; Acknowledgment incl. AI-use disclosure; Kong et al. reference checked.
Done on 23 Oct: report Figs. 7.16, 7.1, 7.3, 7.6 and 7.13 added as Figs. 5, 7, 8, 10 and 12, with text
references; all figures renumbered in order of first mention.

| # | Still open | Who |
|---|---|---|
| 1 | Corresponding author's e-mail (last yellow `[TODO]`, page 1), author order, ORCID iDs (submitting author needs a public ORCID) | team + guide |
| 2 | Official school name in the affiliation | team |
| 3 | Biographies: three are one line; expand them (IEEE Access requires one per author) | each author |
| 4 | Ethics: ask the guide whether VIT needs an approval statement for the field use with volunteers | team + guide |
| 5 | Skim the 9 new sources (abstracts are summarised in `docs/LITERATURE_NOTES.md`) so you can defend them | team |
| 6 | Grammar pass (IEEE Access rejects poor grammar; Paperpal Preflight is offered on their site) | team |
| 7 | Funding line under the affiliation | guide |

Editing tips for the Word file: references are typed numbers ([1]–[43], in order of first citation), and
so are figure, table and equation numbers. If you add, remove or move one, renumber by hand.

## Submission facts (checked 17 Oct 2026)

* Manuscript type "Research Article" (or "Applied Research"); 3–10 keywords at submission; abbreviations
  defined at first use (also after the abstract).
* APC **US$2,160** if accepted. No page limit; keep under 20 pages.
* **No simultaneous submission elsewhere.** An ICCIT version must wait for the Access decision or be a
  clearly different paper.

## Reviewer questions to expect

* Why no public benchmark (OULU-NPU, CASIA-FASD, Replay-Attack)? → stated in Limitations; the strongest
  improvement would be adding one.
* Small webcam population (2 people for PAD, 5 users in field use) → stated, with confidence intervals.
* Independence assumption for L in the combination study → stated in Setup and Limitations.
