# CSE 491 — AI Agents: Homework 2 Rubric

This assignment is graded on a 100 point scale. All grading is based on your demo video.

## Functional Requirements

| # | Requirement | Points | How to demonstrate |
|---|-------------|--------|--------------------|
| 1 | **Semantic Search** — ask something like "Find my MSU experience" | 25 | Show the console printing the Orchestrator routing the request to the `Database Semantic Search Expert` (not the Database Read Expert), and the chat correctly resolving the abbreviation (e.g. "MSU" → "Michigan State University") with accurate info about that institution |
| 2 | **Complex Semantic Query** — ask something like "What AI skills do I have?" | 25 | Show the console printing the `Database Semantic Search Expert` searching `skills`, and the reply correctly returning semantically related skills (e.g. "machine learning", "deep learning") even when none of them contain the word "AI" |
| 3 | **Human Validation Workflow** — ask something like "Delete all my skills" | 25 | Show the chat asking for confirmation instead of acting immediately; show that answering "no" cancels with nothing changed, and that answering "yes" (on a repeat run) actually performs the deletion and the resume panel updates |
| 4 | **Database Schema** — the `embedding` column | 25 | Show, via a query or a database browser, that `institutions`, `positions`, `experiences`, and `skills` each have an `embedding` column, and that rows contain a populated JSON-encoded vector (not `NULL`) |

## Grading Policy

- Each requirement uses **all-or-nothing** grading. You receive the full points or zero — no partial credit.
- Points are awarded based on **functionality demonstrated in the video**, not code quality or implementation choices.
- Even if your app works perfectly, you receive **zero points** for any requirement not clearly shown in your video.

## Demo Video Structure

- State your full name at the start
- Say: *"I will now demonstrate the functional requirements for CSE 491 Homework 2"*
- Announce each requirement before demonstrating it
- Keep the console/terminal visible on screen for requirements 1–3 — the graded output includes what gets printed there
- Clear audio and video required

## Submission Checklist

- [ ] `embeddings.py` exists and `generate_embedding()` returns a 1536-number vector
- [ ] `institutions`, `positions`, `experiences`, and `skills` all have an `embedding` column, populated for every row (seeded and newly inserted)
- [ ] `database.py` has `semanticSearch()`, and `insertRows()`/`backfillEmbeddings()` keep embeddings up to date
- [ ] `llm_roles` includes a `Database Semantic Search Expert` row and an updated `Orchestrator` row (allow-list + few-shot examples) that routes to it; `execute_semantic_search()` in `llm.py` dispatches its `<table>|<search text>` output to `db.semanticSearch()`
- [ ] `assess_message_risk()`, `request_human_validation()`, and `handle_validation_response()` exist in `llm.py`, and `socket_events.py` gates chat through them before the Orchestrator
- [ ] A "yes" answer actually executes the original request; a "no" answer cancels it; an unrecognized answer re-prompts without losing the pending request
- [ ] Code pushed to your fork: `git push origin main`
- [ ] Fork URL included in your submission (e.g. `https://github.com/YOUR-USERNAME/ai-agents`) so the grader can access your code
- [ ] Demo video recorded and uploaded via the homework submission form
