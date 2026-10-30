# Flashcards and mind maps

Implemented on `feature/study-desk-ui`; the production branch is unchanged.

## Flashcards

- Select a PDF or enter a general topic; generate 5 or 10 cards.
- Reveal the answer, mark it **Know it** or **Review again**, and filter out known cards.
- Each deck keeps its own progress. Changing tools or reopening an account restores the saved deck data.
- Keep up to 10 decks. Download a deck as Markdown, reset its progress, or remove it after confirmation.

## Mind maps

- Select a PDF or enter a general topic.
- Explore connected concepts in a scrollable tree, collapse or expand branches, and select a concept for its explanation.
- PDF-based concepts link to supplied page references. Missing PDFs are reported rather than opening a different document.
- Keep up to 5 maps. Download an outline as Markdown or remove a map after confirmation.

## Storage and AI

Both tools extend the existing owner-scoped learning JSON in `clariqo_learning`. No new table, bucket, database policy or paid service is required. Old accounts without the optional new fields continue loading. Existing optimistic revision checks and account data deletion apply to decks and maps too. No user data is migrated or removed by this code change.

Generation uses the existing server-only Groq key, authentication, request bounds and rate limit. PDF mode uses bounded excerpts from the chosen document. General-topic content uses subject knowledge and is not independently fact-checked. References identify supplied excerpts; they do not guarantee factual correctness.

Structured AI responses and server validation enforce card counts, distinct questions, bounded content, valid excerpt numbers and a connected mind-map tree of up to four levels / 20 concepts. Malformed, cyclic, disconnected or unsupported study sets fail with an error instead of being saved.

Deck review is a simple self-rating system. It is not spaced repetition and does not claim measured mastery. PDFs remain subject to the existing 20 MiB per-file limit and account storage quotas; decks and maps consume the existing learning-record allowance.

## Verification

- 82 automated tests pass; TypeScript and production build checks pass.
- Automated checks cover legacy saved data, round-trip deck/map storage validation, set quotas, progress IDs, source references, duplicate cards, invalid graph structures, request validation, authenticated routing and provider failures.
- Real Groq tests used synthetic Java notes: five valid PDF flashcards, five structured general-topic cards without invented PDF references, and a 12-concept map with valid references after enabling strict JSON response schemas.
- Local interactive browser preview uses the actual React components with synthetic fixtures and an in-memory mocked generation callback. Reviewed answer reveal, known-card marking, review filtering, 10-card creation, deck switching, map creation, concept selection, branch collapse/expansion, Markdown map download and desktop/mobile layout. It does not create production accounts or test a signed-in cloud round-trip.
- Changes stay on the feature branch until merged/deployed. The preview is not the production site.
