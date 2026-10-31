# Study-plan revision scope

The study-plan form previously sent weak concepts aggregated from every saved quiz. A Biology quiz could therefore influence a History plan.

Newly generated PDF quizzes retain their source material ID when graded and saved. The ID is captured when generation succeeds, so changing the current selection before submitting cannot reassign the result to a different PDF.

New plans now use:

- With a selected PDF: only quiz results recorded for that PDF.
- Without a selected PDF: only general/legacy results whose quiz topic matches the entered subject after case, whitespace, underscore and hyphen normalisation. Subject symbols remain significant, so C++, C# and C do not merge.

Matching is deliberately conservative. The app does not infer that a “Photosynthesis” quiz belongs to a “Biology” subject. Use the same general subject label, or choose the PDF used for the quiz. A model instruction also tells the planner to omit unrelated weak topics rather than override the requested subject.

Old scores remain readable. Results without a source ID cannot be safely assigned to a PDF and are excluded from PDF-specific priorities. No database migration, account rewrite, or file deletion is required. Overall progress remains aggregated across subjects as before.

Existing saved plans do not change. Generate a new plan to apply the filter. This fixes the input-scope bug, not arbitrary factual mistakes in generated content.

Validation: nine new regression tests cover Biology/History isolation, independent concept scores, normalisation, significant subject symbols, selected-PDF isolation, general/PDF separation, legacy records, source-ID persistence, and the generated plan request prompt. Full regression suite: 91 tests. Production compilation includes TypeScript validation. No real accounts or Groq requests are required for these tests.
