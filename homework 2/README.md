# CSE 491 — AI Agents: Homework 2

*[اقرأ هذا الملف بالعربية](README.ar.md)*

## What You're Building

Homework 1 gave you a multi-expert agent system that could read from and write to a real database. Homework 2 pushes on the two questions that setup immediately raises:

1. **The Database Read Expert only understands exact spelling.** Ask "How long did they work at MSU?" and it generates `WHERE name = 'MSU'` — which matches nothing, because the database stores `'Michigan State University'`. The AI doesn't know these refer to the same thing; it's just pattern-matching text. **Semantic search fixes this.** You'll turn each row's text into a *vector embedding* — a list of numbers that captures meaning, not spelling — so "MSU" and "Michigan State University" land close together in that vector space even though the strings share zero characters in common. Three things to take away from this half of the assignment:
   - An embedding is a similarity-search tool, not another AI chat call — you compute it once per row, then compare vectors with simple math (cosine similarity), no model reasoning involved at query time.
   - The Orchestrator now has a **fourth expert to choose from** — a new Database Semantic Search Expert, alongside Read/Write/Content — and has to *decide* when a request calls for it instead of the exact-matching Read Expert. That decision is a small, real instance of the "Thought → Action" pattern behind most agent frameworks: think about what's being asked, choose the right tool, delegate to it. Keeping semantic search as its own expert (its own role, its own executor function) rather than a second thing the Read Expert might say keeps that choice a routing decision the Orchestrator already knows how to make, instead of a new shape of output every downstream function has to sniff out.
   - Embeddings get computed **once, when data is written** (`insertRows`), not recomputed on every question — an important cost/architecture tradeoff you'll see reflected directly in the code.

2. **The Database Write Expert already runs generated code against a real database with `exec()`.** Homework 1's "Known Limitations" flagged this and moved on. Homework 2 doesn't get to move on: once an agent can delete data, *something* has to stop it from doing that unsupervised. You'll build a **human validation workflow** — a request that looks destructive ("delete", "remove", …) gets paused and requires an explicit "yes" before anything actually runs. Three things to take away from this half:
   - HTTP and WebSocket requests are stateless — each message arrives with no memory of the last one. Confirming a "yes" answer against the *right* pending request requires deliberately storing state server-side (Flask's `session`) between messages.
   - The keyword check you'll build (`assess_message_risk`) is intentionally simple — fast and predictable, not another AI call. It's a real design choice with real gaps, meant to be discussed (see "Questions to Think About"), not a finished solution.
   - The confirmation check happens **before** the Orchestrator is ever invoked, not buried inside expert routing — keeping "is this safe to do?" architecturally separate from "how do we do it?".

Put together, this homework's theme is **capability and safety growing together**: the agent gets smarter (it can now understand paraphrased, abbreviated, or categorical requests) at the same time it gets more guarded (it can no longer act on a destructive request without asking first). Neither half is optional — a smarter agent that still deletes data unsupervised isn't actually safer than Homework 1's, and a cautious agent that can't resolve "MSU" isn't actually more useful.

This guide gives you working code for every piece, same as Homework 1 — your job is to follow along, type it in, understand what each part does, and test it.

---

## How It Works

```
You (browser)
     |  type a message → JavaScript emits 'send_message' over WebSocket
     v
Flask + Socket.IO   (flask_app/utils/socket_events.py)
     |
     |  Is a validation question already pending from the last message?
     |    YES -> handle_validation_response()  (see Step 2)
     |    NO, but does THIS message look destructive?
     |      YES -> request_human_validation()  -- pause and ask, stop here
     |      NO  -> proceed to the Orchestrator as normal
     v
llm.py: Orchestrator
     |  decides which experts are needed, in what order
     v
llm.py: run_orchestrator_plan()
     |  runs each expert call in order -- the Orchestrator picks WHICH
     |  expert(s) a request needs; each expert has its own executor:
     |     Database Read Expert            → execute_read_query()        → SQL SELECT (exact matching)
     |     Database Semantic Search Expert → execute_semantic_search()   → db.semanticSearch() (Step 1)
     |     Database Write Expert           → execute_write_action()      → Python (insert OR delete) (Step 2)
     |     Content Expert                  → answers from the resume text directly
     |  makes ONE final call to turn the raw results into a clean answer
     v
Flask emits 'receive_message' back over WebSocket
     |
     v
JavaScript displays the reply AND refreshes the resume panel
```

Everything from Homework 1 (the four original experts, the shared prompt template, the Orchestrator's plan-then-execute flow) is unchanged underneath — `execute_read_query` in particular is not touched at all this homework. This homework adds one new *expert* the Orchestrator can route to (Database Semantic Search Expert, with its own executor function `execute_semantic_search`), one new capability for the Write Expert (deletion), and one new gate in front of all of it (validation).

---

## Example Flows

**Example 1 — semantic search resolves an abbreviation ("Find my MSU experience")**

```
User message
     v
Orchestrator decides this reference might not match the DB's exact text,
and generates a 1-step plan naming the Semantic Search Expert instead of
the Read Expert:
     ["handle_ai_chat_request(role=\"Database Semantic Search Expert\", message=\"Find my MSU experience\")"]
     v
Database Semantic Search Expert responds with exactly one line:
     institutions|MSU
     v
execute_semantic_search() splits that on '|' and calls
db.semanticSearch('institutions', 'MSU')
     |  embeds the query text, compares it against every institution's
     |  stored embedding by cosine similarity, and returns the closest
     |  match -- 'Michigan State University' -- along with its positions
     |  (joined in automatically, see Step 1.7)
     v
Orchestrator's synthesis call turns the row + positions into:
     "You worked at Michigan State University as an Instructor and a
      Researcher, both starting January 2019."
     v
Chat panel shows that reply. No SQL string match was ever attempted.
```

**Example 2 — a complex semantic query ("What AI skills do I have?")**

```
User message
     v
Orchestrator again picks the Semantic Search Expert (not Read Expert,
not Content Expert) for this table:
     ["handle_ai_chat_request(role=\"Database Semantic Search Expert\", message=\"What AI skills do I have?\")"]
     v
Database Semantic Search Expert responds:
     skills|AI and machine learning
     v
db.semanticSearch() ranks every skill by similarity to that phrase.
"Machine Learning" and "Deep Learning" score far higher than "Python",
"Javascript", "HTML" or "CSS" -- none of which contain the word "AI" at
all, yet the two ML-related skills are still correctly surfaced first.
     v
Chat panel lists Machine Learning and Deep Learning as your AI skills.
```

**Example 3 — a destructive request gets confirmed ("Delete all my skills")**

```
User message: "Delete all my skills"
     v
socket_events.py: assess_message_risk() sees "delete" -> True
     v
request_human_validation() stores the ORIGINAL message in
session['pending_validation'] and replies with a question instead of
acting:
     "This looks like it could delete or modify data: 'Delete all my
      skills'. Are you sure you want to proceed? (yes/no)"
     v
Chat panel shows that question. Nothing in the database has changed yet.
     v
User's NEXT message: "yes"
     v
socket_events.py sees session['pending_validation'] is set, so this
message is NOT treated as a new request -- it goes to
handle_validation_response() instead
     v
"yes" -> clear the pending state, run the ORIGINAL message
("Delete all my skills") through the normal Orchestrator flow
     v
Database Write Expert generates:
     total = db.query("SELECT COUNT(*) as total FROM skills")[0]['total']
     db.query("DELETE FROM skills")
     outcome = f"Deleted {total} row(s) from the skills table."
     v
Chat panel shows: "Deleted 6 row(s) from the skills table."
Browser refreshes the resume panel -- the skill badges are gone.
```

**Example 4 — the same request, cancelled ("Delete all my skills" → "no")**

```
User message: "Delete all my skills"  ->  same confirmation question as above
     v
User's next message: "no"
     v
handle_validation_response() clears session['pending_validation'] and
replies: "Okay, I won't do that. The request was cancelled."
     v
The Write Expert never runs. The database is untouched.
```

An answer that isn't "yes" or "no" (e.g. "maybe", or a totally unrelated message typed by mistake) leaves `pending_validation` in place and re-asks, instead of silently cancelling or silently proceeding.

---

## Project File Map

You're extending your Homework 1 codebase. Copy `homework 1/flask_app` and `app.py` into a new `homework 2/` folder, then make these changes:

```
homework 2/
├── app.py                              ← unchanged, copy as-is
│
└── flask_app/
    ├── __init__.py                     ← MODIFY: call db.backfillEmbeddings() on startup
    ├── routes.py                       ← unchanged, copy as-is
    │
    ├── utils/
    │   ├── embeddings.py               ← NEW: generate_embedding()
    │   ├── llm.py                      ← MODIFY: new Semantic Search Expert executor +
    │   │                                  role dispatch, plus validation workflow
    │   │                                  (execute_read_query itself is untouched)
    │   ├── socket_events.py            ← MODIFY: validation gate before the Orchestrator
    │   └── database.py                 ← MODIFY: embedding storage + semanticSearch()
    │
    ├── templates/                      ← unchanged, copy as-is (no new UI needed --
    │                                      confirmation is just a normal chat message)
    │
    └── database/
        ├── create_tables/
        │   ├── institutions.sql        ← MODIFY: add embedding column
        │   ├── positions.sql           ← MODIFY: add embedding column
        │   ├── experiences.sql         ← MODIFY: add embedding column
        │   ├── skills.sql              ← MODIFY: add embedding column
        │   └── llm_roles.sql           ← unchanged, copy as-is
        └── initial_data/
            └── llm_roles.csv           ← MODIFY: add a Database Semantic Search Expert
                                           row, and teach the Orchestrator when to use it
```

No changes to `requirements.txt` or your `.env` — semantic search reuses the same `requests` library and the same `OPENROUTER_API_KEY` your chat calls already use (see Step 1.0).

---

## Building It

This section is written as a lab, not a summary — every step names the exact file to open, the exact code to type, and a check-in stage to run before moving to the next step. **Do not skip the check-in stages.** If you skip one and something breaks two steps later, you'll have three steps' worth of changes to search through instead of one. If a check-in stage doesn't match what's described, stop and fix it before continuing — everything after it assumes it worked.

**Before you start:**

- [ ] Your `homework 1` folder is fully working (all four Homework 1 test prompts from that README pass).
- [ ] You've copied `homework 1/app.py` and `homework 1/flask_app` into a new `homework 2/` folder (see "Project File Map" above for the exact target layout).
- [ ] Your terminal's current directory is `homework 2/` and your virtual environment is activated (`source ../venv/bin/activate`, or `venv\Scripts\activate` on Windows) for every command below.
- [ ] Your `.env` file (at the repo root, one level up) has a real `OPENROUTER_API_KEY` — not the placeholder text.

We build in a specific order, and the order matters: **storage, then the writer, then the reader.** You can't search embeddings that don't exist yet, and you can't generate an embedding without somewhere to put it.

### Step 1: Semantic search

#### 1.0 — Understand why we're using OpenRouter for this

The official course version of this assignment calls OpenAI's embeddings API directly, with its own separate API key. This codebase already routes every chat call through OpenRouter instead (`flask_app/utils/llm.py`'s `send_message` function) — and OpenRouter also proxies an OpenAI-compatible **embeddings** endpoint at a different URL. So instead of adding a second provider and a second secret to manage, this port reuses the one `OPENROUTER_API_KEY` you already have for both chat and embeddings. Keep that in mind as you read the next step: there is no new key to go acquire.

#### 1.1 — Create the embedding-generation file

1. Create a new, empty file at exactly this path: **`flask_app/utils/embeddings.py`** (same folder as `llm.py`, `database.py`, and `socket_events.py`).
2. Copy the entire block below into that new file — nothing needs editing, this is a complete file on its own:

```python
import os
import requests

OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def generate_embedding(text):
    """
    Return a 1536-number vector representing the meaning of `text`.
    Falls back to a vector of all zeros if the API key is missing/invalid
    or the request fails -- a zero vector never scores as a strong match
    against anything, so a bad embedding just means that row won't be
    found by semantic search until it's fixed, rather than crashing the
    insert/startup that triggered it.
    """
    api_key = os.getenv('OPENROUTER_API_KEY')

    if not text or not text.strip() or not api_key or api_key == 'paste-your-key-here':
        return [0.0] * EMBEDDING_DIMENSIONS

    try:
        response = requests.post(
            OPENROUTER_EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": EMBEDDING_MODEL, "input": text.strip()},
            timeout=30,
        )
        return response.json()['data'][0]['embedding']
    except Exception as error:
        print(f"Embedding generation failed: {error}")
        return [0.0] * EMBEDDING_DIMENSIONS
```

3. Save the file.

**What you just wrote, in plain terms:** `generate_embedding(text)` takes any string and hands back a list of 1536 numbers, by making one HTTP request to OpenRouter's `/embeddings` endpoint — the same pattern `send_message` already uses for `/chat/completions`, just a different URL and a different piece of the JSON response (`data[0]['embedding']` instead of `choices[0]['message']['content']`). The `try/except` means a missing key, a network hiccup, or a malformed response never crashes whatever called it — it just gets back a harmless all-zero vector instead.

**✅ Check-In Stage 1.1 — test this file completely on its own, before touching any other file.** In your terminal (inside `homework 2`, venv active):

```bash
python -c "from flask_app.utils.embeddings import generate_embedding; v = generate_embedding('hello world'); print(len(v), v[:5])"
```

Expected output: `1536` followed by five small decimal numbers, e.g. `1536 [0.0113, -0.0271, 0.0042, -0.0198, 0.0075]`. The exact numbers don't matter — only that there are 1536 of them and they're not all zero.

- If you see `1536 [0.0, 0.0, 0.0, 0.0, 0.0]`: your API key isn't being found. Check that `../.env` exists and has a real key (not `paste-your-key-here`), and that you're running the command from inside `homework 2` (python-dotenv searches upward from your current directory).
- If you see `ModuleNotFoundError: No module named 'flask_app'`: you're not in the `homework 2` folder, or the file isn't saved at the exact path above.
- If you see a different error, read it — it'll usually point at a typo in the code you just pasted.

Do not continue to 1.2 until this prints `1536` with non-zero numbers.

#### 1.2 — Add a column to store each row's embedding

SQLite has no native vector/array column type (unlike Postgres's `pgvector` extension, which the official spec uses), so we store each embedding as a JSON-encoded string — literally the text `"[0.0113, -0.0271, ...]"` sitting in a `TEXT` column.

Open `flask_app/database/create_tables/institutions.sql`. It currently ends like this:

```sql
CREATE TABLE IF NOT EXISTS institutions (
    inst_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    department  TEXT,
    address     TEXT,
    city        TEXT,
    state       TEXT,
    zip         TEXT
);
```

Add a new column line right before the closing `zip TEXT` line's closing parenthesis — i.e. add a comma to the end of the `zip TEXT` line, then add this new line before the final `);`:

```sql
    embedding   TEXT DEFAULT NULL  -- JSON-encoded vector, for semantic search
```

Save the file. Now repeat the same idea in the other three table files — **open each one, add a comma to what is currently the last column line, then add an `embedding TEXT DEFAULT NULL` line right before the closing `);`:**

- `flask_app/database/create_tables/positions.sql` — add it after the `end_date TEXT` line.
- `flask_app/database/create_tables/experiences.sql` — add it after the `end_date TEXT` line.
- `flask_app/database/create_tables/skills.sql` — add it after the `skill_level INTEGER NOT NULL` line.

**Do not** add this column to `llm_roles.sql` — there's no reason to semantically search the experts' own configuration rows, so leave that file untouched.

There's no standalone checkpoint for this step (an empty/unused column doesn't do anything observable yet) — you'll see it take effect in Check-In Stage 1.6.

#### 1.3 — Add the embedding configuration to `database.py`

Open `flask_app/utils/database.py`. Near the top of the file, find these lines (they should look exactly like this from Homework 1):

```python
import sqlite3
import csv
import os
from io import StringIO

# Path to the SQLite database file — created automatically on first run
DB_PATH = 'flask_app/database/resume.db'

TABLE_ORDER = ['institutions', 'positions', 'experiences', 'skills', 'llm_roles']
```

Change the import block at the top to add three new imports, and add two new dictionaries directly below `TABLE_ORDER`:

```python
import sqlite3
import csv
import os
import json
import math
from io import StringIO

from flask_app.utils.embeddings import generate_embedding

# Path to the SQLite database file — created automatically on first run
DB_PATH = 'flask_app/database/resume.db'

TABLE_ORDER = ['institutions', 'positions', 'experiences', 'skills', 'llm_roles']

# Which columns get combined into the text that gets embedded for each
# table, and each table's primary key column.
EMBEDDING_FIELDS = {
    'institutions': ['name', 'department'],
    'positions':    ['title', 'responsibilities'],
    'experiences':  ['name', 'description'],
    'skills':       ['name'],
}
ID_COLUMNS = {
    'institutions': 'inst_id',
    'positions':    'position_id',
    'experiences':  'experience_id',
    'skills':       'skill_id',
}
```

Save the file. `EMBEDDING_FIELDS` says which columns get combined into one string before embedding (e.g. an institution's `name` + `department`); `ID_COLUMNS` records each table's primary-key column name so the code below can look up "the row that was just inserted" generically, without a table-specific `if` for every table. Nothing runs differently yet — you've only added configuration.

#### 1.4 — Rewrite `insertRows` so new rows get embedded automatically

Still in `database.py`, find your existing `insertRows` method (near the bottom of the `database` class). It currently looks like this:

```python
def insertRows(self, table, columns, values):
    """
    Insert one row into `table`. Any value that starts with "(SELECT" is
    inlined directly into the SQL instead of bound as a parameter, so the
    Database Write Expert's generated code can resolve a foreign key by
    name instead of needing to know the numeric ID, e.g.
        "(SELECT experience_id FROM experiences WHERE name = 'MSU Research')"
    """
    value_sql, bound_params = [], []
    for value in values:
        if isinstance(value, str) and value.strip().startswith("(SELECT"):
            value_sql.append(value)
        else:
            value_sql.append("?")
            bound_params.append(value)
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(value_sql)})"
    self.query(sql, tuple(bound_params))
```

Replace the entire method (all of the code above, from `def insertRows` down to the final `self.query(sql, tuple(bound_params))` line) with this version:

```python
def insertRows(self, table, columns, values):
    """
    Insert one row into `table`. Any value that starts with "(SELECT" is
    inlined directly into the SQL instead of bound as a parameter, so the
    Database Write Expert's generated code can resolve a foreign key by
    name instead of needing to know the numeric ID, e.g.
        "(SELECT experience_id FROM experiences WHERE name = 'MSU Research')"

    Homework 2: if `table` is one of EMBEDDING_FIELDS, the new row's
    embedding is generated and stored right after the insert -- this
    needs the new row's ID (self.query() doesn't return one), so this
    method opens its own connection instead of calling self.query().
    """
    value_sql, bound_params = [], []
    for value in values:
        if isinstance(value, str) and value.strip().startswith("(SELECT"):
            value_sql.append(value)
        else:
            value_sql.append("?")
            bound_params.append(value)
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(value_sql)})"

    connection = sqlite3.connect(self.db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        cursor = connection.cursor()
        cursor.execute(sql, tuple(bound_params))
        new_row_id = cursor.lastrowid
        connection.commit()
    finally:
        connection.close()

    if table in EMBEDDING_FIELDS:
        self._updateEmbedding(table, new_row_id)
```

**What changed and why:** the old version handed the SQL straight to `self.query()`, which opens its own connection internally and doesn't tell you what ID the new row got. This version opens the connection itself so it can read `cursor.lastrowid` — SQLite's built-in "ID of the row I just inserted" — and then, only for tables that are in `EMBEDDING_FIELDS`, calls a helper (`_updateEmbedding`, which you'll write next) to generate and store that row's embedding immediately. The `try`/`finally` guarantees `connection.close()` runs even if `cursor.execute()` raises an error — the same reasoning Step 2.0 walks through in detail for `query()`, applied here from the start since this method is brand new.

Save the file. This method now references `self._updateEmbedding`, which doesn't exist yet — that's fine, Python doesn't check that a method exists until it's actually called, and nothing calls `insertRows` yet in this checkpoint-free step. Continue to 1.5 before testing anything.

#### 1.5 — Add the embedding-storage helpers

Still in `database.py`, add the following two methods. Put them right after `insertRows` (the method you just finished editing):

```python
def _updateEmbedding(self, table, row_id):
    """
    Regenerate and store the embedding for one row, combining that
    table's EMBEDDING_FIELDS columns into a single string first (e.g.
    an institution's name + department). Stored as JSON text since
    SQLite has no native vector/array column type.
    """
    id_column = ID_COLUMNS[table]
    rows = self.query(f"SELECT * FROM {table} WHERE {id_column} = ?", (row_id,))
    if not rows:
        return

    row = rows[0]
    text = " ".join(str(row[field]) for field in EMBEDDING_FIELDS[table] if row.get(field))
    embedding = generate_embedding(text)

    connection = sqlite3.connect(self.db_path)
    try:
        connection.execute(
            f"UPDATE {table} SET embedding = ? WHERE {id_column} = ?",
            (json.dumps(embedding), row_id),
        )
        connection.commit()
    finally:
        connection.close()


def backfillEmbeddings(self):
    """
    Generate embeddings for any row that doesn't have one yet.

    insertRows() embeds new rows automatically, but the CSV-seeded
    starting data (loaded by _seed_table on every startup) never goes
    through insertRows -- so this fills in the gap. Safe to call every
    startup: a row with embedding IS NOT NULL is already done and gets
    skipped, so re-running this after the first startup is a no-op.
    """
    for table in EMBEDDING_FIELDS:
        id_column = ID_COLUMNS[table]
        rows = self.query(f"SELECT {id_column} FROM {table} WHERE embedding IS NULL")
        for row in rows:
            self._updateEmbedding(table, row[id_column])
        if rows:
            print(f"  Generated embeddings for {len(rows)} {table} row(s)")
```

Save the file. `_updateEmbedding` handles a single row: look it up, glue its configured fields into one string, embed that string, write the result back. `backfillEmbeddings` handles the *other* way rows get into your tables — the CSV files loaded at startup — by finding every row that still has `embedding IS NULL` and running `_updateEmbedding` on each one. Notice `backfillEmbeddings` is written to be safe to call on every single startup: once a row has an embedding, the `WHERE embedding IS NULL` filter skips it, so calling this repeatedly does no wasted work.

**✅ Check-In Stage 1.5 — test both new methods directly, without running the full app.** Run this from your terminal:

```bash
python -c "
from flask_app.utils.database import database
db = database()
db.createTables(purge=True)
db.backfillEmbeddings()
"
```

Expected output: the usual `Loaded data for table: ...` lines, followed by four new lines like:
```
  Generated embeddings for 3 institutions row(s)
  Generated embeddings for 4 positions row(s)
  Generated embeddings for 6 experiences row(s)
  Generated embeddings for 4 skills row(s)
```
(Your exact row counts will match whatever's in your own CSV files.) If you run the exact same command a second time, those four lines should **not** reappear — that's `backfillEmbeddings` correctly skipping rows that already have an embedding. If you get a `KeyError` or `NameError`, re-check Step 1.3's dictionaries and Step 1.4's edit for typos.

#### 1.6 — Call `backfillEmbeddings()` when the app starts

Open `flask_app/__init__.py`. Find this block inside `create_app()`:

```python
    db = database()
    print("Setting up database...")
    db.createTables(purge=True)
    print("Database ready.")
```

Add one line between `createTables` and the "Database ready." print:

```python
    db = database()
    print("Setting up database...")
    db.createTables(purge=True)
    db.backfillEmbeddings()   # Homework 2: embed any CSV-seeded row that doesn't have one yet
    print("Database ready.")
```

Save the file.

**✅ Check-In Stage 1.6 — run the actual app for the first time this homework.** From `homework 2/`:

```bash
python app.py
```

Watch the startup log. You should see the same four `Generated embeddings for N ... row(s)` lines as Check-In Stage 1.5. Stop the server (`Ctrl+C`) and run `python app.py` again — this time, those four lines should be gone (every row already has an embedding from the first run), leaving just `Setting up database...` / the `Loaded data...` lines / `Database ready.`. Leave the server running (or restart it once more) and move to Step 1.7.

#### 1.7 — Add semantic search itself

Still in `database.py`, add these two more methods, again right after the ones you just added (`_updateEmbedding` and `backfillEmbeddings`):

```python
def semanticSearch(self, table, query_text, top_k=3):
    """
    Return the top_k rows in `table` whose embedding is closest in
    MEANING to query_text, ranked by cosine similarity -- e.g.
    searching institutions for "MSU" finds the row named "Michigan
    State University" even though the strings don't match at all.

    This is a from-scratch, SQLite-friendly stand-in for what
    pgvector's `<=>` operator + an ivfflat index give you natively in
    Postgres: here, similarity is computed in Python by scanning every
    embedded row (fine at this dataset's size -- see README "Known
    Limitations" for why this wouldn't scale to a huge table).

    For 'institutions', each result also gets its `positions` attached
    (title/responsibilities/start_date/end_date) via a normal SQL join
    -- this is what lets a single Semantic Search Expert call answer
    "how long did they work at MSU?"-style questions without a second
    AI call.
    """
    id_column = ID_COLUMNS[table]
    query_embedding = generate_embedding(query_text)

    rows = self.query(f"SELECT * FROM {table} WHERE embedding IS NOT NULL")
    scored = [(self._cosineSimilarity(query_embedding, json.loads(row['embedding'])), row) for row in rows]
    scored.sort(key=lambda pair: pair[0], reverse=True)

    results = []
    for similarity, row in scored[:top_k]:
        visible = {key: value for key, value in row.items() if key != 'embedding'}
        visible['similarity'] = round(similarity, 3)
        if table == 'institutions':
            visible['positions'] = self.query(
                "SELECT title, responsibilities, start_date, end_date FROM positions WHERE inst_id = ?",
                (row['inst_id'],),
            )
        results.append(visible)
    return results


def _cosineSimilarity(self, vector_a, vector_b):
    """
    Return how similar two embedding vectors are, from -1 (opposite
    meaning) to 1 (identical meaning). This is the standard way to
    compare embeddings: the dot product measures how much the two
    vectors point in the same direction, normalized by their lengths
    so longer text doesn't automatically score higher.
    """
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)
```

Save the file. `_cosineSimilarity` is pure math with no database or API calls in it — feed it two equal-length lists of numbers, get back one number between -1 and 1. `semanticSearch` is the part that actually uses it: embed the search text once, pull every row that has a stored embedding, score each one against the search text, sort, and return the best `top_k` (default 3).

**✅ Check-In Stage 1.7 — test semantic search directly, before wiring it into the chat.** With the app stopped (`Ctrl+C` if it's still running), run:

```bash
python -c "
from flask_app.utils.database import database
db = database()
for r in db.semanticSearch('institutions', 'MSU'):
    print(r['name'], '->', r['similarity'])
"
```

Expected output: your institution named something like `Michigan State University` listed first, with a similarity noticeably higher (e.g. `0.70`) than the other institutions in your data (e.g. `0.2`–`0.3`). The exact numbers will vary with your own resume data, but the *top* result should always be the institution that's actually a paraphrase/abbreviation match — if instead the results look randomly ordered or all scored near `0.0`, re-check that Check-In Stage 1.6 actually populated the `embedding` columns (query your database directly with a SQLite browser or `sqlite3` if you want to confirm).

#### 1.8 — Add an executor for the new Semantic Search Expert

Now for the part that actually changes what your chatbot can answer. Open `flask_app/utils/llm.py`. Find `handle_ai_chat_request` — the function that routes a message to whichever expert's `role` was passed in:

```python
    if role == "Database Read Expert":
        return execute_read_query(db, output)
    if role == "Database Write Expert":
        return execute_write_action(db, output)
    if role == "Orchestrator":
        return run_orchestrator_plan(db, message, output)
    return output   # Content Expert -- output is already the final answer
```

Add one more `if` branch, for a brand-new role name — put it wherever you like among the others, e.g. right after the `Database Read Expert` check:

```python
    if role == "Database Read Expert":
        return execute_read_query(db, output)
    if role == "Database Write Expert":
        return execute_write_action(db, output)
    if role == "Database Semantic Search Expert":
        return execute_semantic_search(db, output)
    if role == "Orchestrator":
        return run_orchestrator_plan(db, message, output)
    return output   # Content Expert -- output is already the final answer
```

Leave `execute_read_query` completely alone — do not edit it. Semantic search isn't a second thing the Read Expert might say; it's a distinct expert with its own role name and its own executor function, exactly the same pattern as `Database Read Expert` → `execute_read_query` and `Database Write Expert` → `execute_write_action`. Now add that new executor function. A good place is right after `execute_read_query`:

```python
def execute_semantic_search(db, output):
    """
    Run the Database Semantic Search Expert's output.

    Homework 2: this is a separate expert (its own role, its own executor
    function here) rather than a second thing the Read Expert might say --
    the Orchestrator picks this role instead of "Database Read Expert" in
    its plan whenever a request names something by an abbreviation,
    paraphrase, or general category that might not match the database's
    exact wording (e.g. "MSU", "AI skills"). See semanticSearch() in
    database.py for how the actual comparison works.

    The expert is told (see llm_roles.csv) to respond with exactly one
    line in the form "<table>|<search text>" -- deliberately the simplest
    format that still carries both pieces of information, so parsing it
    is one string split, not a regex.
    """
    try:
        table, query_text = output.strip().split('|', 1)
        return str(db.semanticSearch(table.strip(), query_text.strip()))
    except Exception as error:
        print(f"Semantic search failed: {error}")
        return "Sorry, that question couldn't be answered."
```

Save the file. Notice what this function does *not* need: no regular expressions, no parsing multiple possible shapes of text. It splits the expert's one-line output on the first `|` character into two pieces — the table name and the search text — strips whitespace off each, and hands them straight to `db.semanticSearch()`. If the expert's output is ever malformed (no `|` in it, an unknown table name, anything else), the `try/except` catches it and returns a friendly error instead of crashing the chat.

This function exists now, and `handle_ai_chat_request` knows to call it for the `"Database Semantic Search Expert"` role — but nothing in your `llm_roles` table defines that role yet, so the Orchestrator has no way to know it exists or when to use it. That's the last piece of Step 1.

#### 1.9 — Add the Semantic Search Expert's configuration, and teach the Orchestrator about it

Open `flask_app/database/initial_data/llm_roles.csv`. This is the trickiest file to hand-edit directly (it's one giant line per expert, with commas and quotes that have to follow CSV escaping rules), so you have two options:

- **Recommended:** open it in a spreadsheet program (Excel, Google Sheets, LibreOffice Calc), add a new row and edit the **Orchestrator** row's cells using the content below, then re-export/save as CSV. The spreadsheet program handles all the quoting for you.
- **If editing the raw text file directly:** be very careful to keep every field on one line (no real line breaks inside a field) and to wrap any field containing a comma in double quotes, doubling any literal `"` characters inside it (e.g. a literal quote becomes `""`) — this is standard CSV escaping, and it's exactly what Homework 1's README already warned you about.

You are **not** changing the Database Read Expert row at all this step — leave it exactly as it is from Homework 1. There are two changes to make instead:

**First, add a brand-new row** for the Database Semantic Search Expert, with these five columns:

| Column | Content |
|---|---|
| `role` | `Database Semantic Search Expert` |
| `domain` | semantic (meaning-based) search over the resume database |
| `specific_instructions` | Respond with exactly one line in the form `<table>\|<search text>` — the table to search and the text to search for, separated by a single `\|` character. Valid tables: institutions, positions, experiences, skills. No markdown, no explanation, nothing else on the line. |
| `background_context` | institutions holds places someone studied or worked (matched on name + department); positions holds job titles (matched on title + responsibilities); experiences holds specific projects (matched on name + description); skills holds individual skills (matched on name). This expert exists for requests that name something by an abbreviation, paraphrase, or general category that might not match the database's exact wording — e.g. 'MSU' for an institution, or 'AI skills' for a category of skills — where the Database Read Expert's exact SQL matching would find nothing. |
| `few_shot_examples` | Q: Find my MSU experience -> `institutions\|MSU` \| Q: What AI skills do I have? -> `skills\|AI and machine learning` |

(The row's own field is delimited with `|`, and that same character also shows up *inside* two of that row's own field values, as the separator the expert's output uses — that's a coincidence of this particular design, not a conflict: one is a character inside a CSV cell's text, the other is CSV structure itself, and they don't interact.)

**Second, update the existing Orchestrator row** so it knows the new expert exists and when to prefer it:

| Column | New content |
|---|---|
| `specific_instructions` | Respond with a Python list of strings, each an exact call in the form `handle_ai_chat_request(role="<Expert Name>", message="<message>")`. Order matters — later calls can depend on earlier results. Only use these role names: Database Read Expert, Database Write Expert, **Database Semantic Search Expert**, Content Expert. *(the only change here is adding the new role name to the allow-list)* |
| `background_context` | Available experts: Database Read Expert (answers questions from the DB using exact SQL), Database Write Expert (modifies the DB, including deletions), **Database Semantic Search Expert (answers questions using semantic/fuzzy matching when the exact wording might not match, e.g. 'MSU' or 'AI skills')**, Content Expert (answers from the currently visible resume content). |
| `few_shot_examples` | *(keep the existing React example, and add these two new examples after it, each separated by `\|`)*: Request: Find my MSU experience -> `["handle_ai_chat_request(role=\"Database Semantic Search Expert\", message=\"Find my MSU experience\")"]` \| Request: What AI skills do I have? -> `["handle_ai_chat_request(role=\"Database Semantic Search Expert\", message=\"What AI skills do I have?\")"]` |

**Don't skip that second few-shot example.** With only the MSU example present, testing this exact setup showed the Orchestrator would sometimes route "What AI skills do I have?" to the Content Expert instead of the new Semantic Search Expert — a plausible-looking guess that happened to work by coincidence (the Content Expert can read resume text directly), but skipped the actual semantic ranking the rubric wants to see. One additional, on-topic few-shot example fixed it completely. This is worth remembering as a general lesson, not just a one-off fix: **a new role is only as reliable as the examples that show it being used** — one example covering one kind of question doesn't automatically generalize to a different kind of question, even one that looks similar to a human reader.

Save the file. Restart the app (`Ctrl+C`, then `python app.py`) so it re-seeds the `llm_roles` table from your edited CSV — remember, `createTables(purge=True)` drops and recreates every table on every startup, so a CSV edit only takes effect after a restart.

**✅ Check-In Stage 1.9 — the real end-to-end test.** With the app running, open `http://localhost:8080/resume` in your browser and type into the chat:

```
Find my MSU experience
```

Watch your terminal at the same time. You should see lines like:
```
[Orchestrator] generated:
["handle_ai_chat_request(role=\"Database Semantic Search Expert\", message=\"Find my MSU experience\")"]

[Orchestrator] executing: handle_ai_chat_request(role="Database Semantic Search Expert", message="Find my MSU experience")
[Database Semantic Search Expert] generated:
institutions|MSU
```
and the chat reply should correctly name your institution (e.g. "Michigan State University") along with accurate details about it. Then try:
```
What AI skills do I have?
```
and confirm the console shows the Orchestrator routing to `Database Semantic Search Expert` again (not `Content Expert`), with a generated line like `skills|AI and machine learning`, and that the reply lists skills related to AI/machine learning even if none of them literally contain the word "AI".

If the Orchestrator routes either question to the wrong expert, re-read your CSV edits above for typos or missing content, and double-check both new few-shot examples are present on the Orchestrator row — the model is following your prompt text and examples exactly, so if it's choosing the wrong expert, the prompt it's receiving doesn't clearly point it there yet.

**Step 1 is done once both of those check-in stage questions work correctly.** Take a short break before Step 2 — it's a separate feature built on top of what you already have working.

### Step 2: Human validation workflow

This step adds one new capability (the Write Expert can now delete rows, not just insert them) and one new safety gate in front of the whole chat flow (a yes/no confirmation before anything destructive runs) — but it starts with fixing a bug in code Step 1 didn't touch, because Step 2 is what finally exposes it.

#### 2.0 — Fix a connection leak that deletion failures are about to expose

Open `flask_app/utils/database.py` and find `query()` — the core method every other method in this file calls through, unchanged since Homework 0:

```python
def query(self, sql, params=()):
    connection = sqlite3.connect(self.db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute(sql, params)
    results = []
    if sql.strip().upper().startswith(('SELECT', 'PRAGMA')):
        results = [dict(row) for row in cursor.fetchall()]
    connection.commit()
    connection.close()
    return results
```

**Here's the bug, and why nothing exposed it until now:** if `cursor.execute(sql, params)` raises an exception, every line after it — including `connection.close()` — never runs. That connection stays open, holding a lock on the database file. Through Homework 0 and Homework 1, this never mattered in practice, because nothing routinely made `cursor.execute()` fail. It matters now: once the Write Expert can generate `DELETE FROM experiences` (Step 2.3) against a table that `skills` still has foreign-key references into, that `DELETE` is *supposed* to fail — that's the whole point of `PRAGMA foreign_keys = ON` from Homework 1, catching a bad delete instead of silently corrupting data. But with the connection leak, that expected failure leaves a connection open — and the very next database call anywhere in the app, for any user, fails with `sqlite3.OperationalError: database is locked`, with no obvious connection to what actually caused it. This is exactly the kind of thing "test with a variety of questions, not just the two from the rubric" catches and a narrow test doesn't.

Fix it by wrapping the risky part in `try`/`finally`, so `connection.close()` always runs:

```python
def query(self, sql, params=()):
    connection = sqlite3.connect(self.db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute(sql, params)
        results = []
        if sql.strip().upper().startswith(('SELECT', 'PRAGMA')):
            results = [dict(row) for row in cursor.fetchall()]
        connection.commit()
    finally:
        connection.close()
    return results
```

`finally` runs whether the `try` block finishes normally or raises — so `connection.close()` is now unconditional. The exception itself still propagates upward exactly as before (closing a connection doesn't swallow the error), so `execute_write_action`'s `except` block still catches it and reports `"Operation was unsuccessful."` — the only thing that changes is that the lock is always released, instead of only when nothing went wrong.

**✅ Check-In Stage 2.0 — confirm a failed delete doesn't lock out the next request.** Restart the app, and in the chat, try a delete that's *expected* to fail — one against a table something else still points to:

```
Delete all my experiences
```

then reply `yes`. You should see `Write Expert code failed: FOREIGN KEY constraint failed` in the console, and a reply along the lines of *"Operation was unsuccessful."* Immediately after, without restarting the app, ask an ordinary question:

```
What is this page about?
```

If that answers normally, the fix worked. If it (or anything else) fails with `database is locked`, the `try`/`finally` isn't wrapping the whole risky section — double-check the indentation matches the code block above exactly.

#### 2.1 — Add the risk-detection and confirmation functions

Open `flask_app/utils/llm.py` again. Near the top of the file, find your existing imports:

```python
import os
import re
import requests
from jinja2 import Template
```

Add one new import line:

```python
import os
import re
import requests
from flask import session
from jinja2 import Template
```

Now scroll to the **very end** of the file (after `run_orchestrator_plan`, which should be the last function from Homework 1/Step 1). Add this entire new block at the bottom:

```python
# ======================================================================
# HOMEWORK 2 — HUMAN VALIDATION WORKFLOW
#
# The Write Expert above genuinely deletes/modifies rows via exec(). These
# three functions gate that behind an explicit yes/no confirmation for any
# message that looks destructive, instead of letting it run unsupervised.
# See homework 2/README.md Step 2 for the full walkthrough of why this
# needs Flask's session (HTTP/WebSocket requests are otherwise stateless --
# nothing else ties "yes" back to the request it's confirming).
# ======================================================================

# A fast, predictable keyword scan -- not another AI call -- runs BEFORE
# anything gets anywhere near the Orchestrator or exec(). See the README's
# "Known Limitations" for the tradeoffs of this over real intent
# classification.
DANGEROUS_KEYWORDS = ['delete', 'remove', 'clear', 'drop', 'destroy']


def assess_message_risk(message):
    """
    Return True if `message` contains a keyword associated with a
    destructive/irreversible database action.
    """
    lowered = message.lower()
    return any(keyword in lowered for keyword in DANGEROUS_KEYWORDS)


def request_human_validation(message):
    """
    Pause a risky request and ask the user to confirm before anything
    runs. Stashes the original message in the Flask session under
    'pending_validation' -- the NEXT message the user sends is then
    checked (in socket_events.py) against that key, so it's interpreted
    as the yes/no answer to THIS question rather than a new, unrelated
    chat message.
    """
    session['pending_validation'] = message
    return (
        f'This looks like it could delete or modify data: "{message}". '
        f'Are you sure you want to proceed? (yes/no)'
    )


def handle_validation_response(db, response):
    """
    Called instead of the normal chat flow whenever session has a
    'pending_validation' entry waiting -- i.e. the previous reply was a
    request_human_validation() confirmation prompt, and this message is
    (hopefully) the user's yes/no answer to it.

    "yes"    -> clear the pending state, run the ORIGINAL message through
                the normal Orchestrator flow (this is where the actual
                delete/write finally happens)
    "no"     -> clear the pending state, cancel -- nothing ever reaches
                the Orchestrator or exec()
    anything else -> keep the pending state active and ask again, so a
                typo or unrelated reply doesn't silently cancel or
                silently proceed
    """
    original_message = session['pending_validation']
    normalized = response.strip().lower()

    if normalized in ('yes', 'y'):
        session.pop('pending_validation')
        return handle_ai_chat_request(db, role="Orchestrator", message=original_message)

    if normalized in ('no', 'n'):
        session.pop('pending_validation')
        return "Okay, I won't do that. The request was cancelled."

    return f'Please answer "yes" or "no" -- do you want me to proceed with: "{original_message}"?'
```

Save the file. Read through the three functions once before moving on: `assess_message_risk` is a one-line check with no side effects (it just returns `True`/`False`); `request_human_validation` is the only place that *writes* to `session`; `handle_validation_response` is the only place that *reads and clears* it. Nothing calls any of these three functions yet — that wiring is Step 2.2.

**✅ Check-In Stage 2.1 — test the risk check in isolation.** This one doesn't need `session`, so it's a plain one-liner:

```bash
python -c "
from flask_app.utils.llm import assess_message_risk
print(assess_message_risk('Delete all my skills'))
print(assess_message_risk('What is this page about?'))
"
```

Expected output: `True` then `False`.

#### 2.2 — Gate the chat handler through the new functions

Open `flask_app/utils/socket_events.py`. It currently looks like this in full:

```python
from flask import current_app
from flask_socketio import emit
from flask_app import socketio
from flask_app.utils.llm import handle_ai_chat_request

# db is attached to the Flask app instance by create_app() in __init__.py
# (app.db = db). Flask-SocketIO runs event handlers inside an app context,
# so current_app.db reaches that same shared instance here too -- no
# separate module-level variable needed.


@socketio.on('send_message')
def handle_message(data):
    user_message = data.get('message', '').strip()

    if not user_message:
        return

    try:
        db = current_app.db
        ai_response = handle_ai_chat_request(db, role="Orchestrator", message=user_message)
    except Exception as error:
        print(f"LLM error: {error}")
        ai_response = "Sorry, something went wrong answering that."

    emit('receive_message', {'response': ai_response})
```

Replace the whole file's contents with this version:

```python
from flask import current_app, session
from flask_socketio import emit
from flask_app import socketio
from flask_app.utils.llm import (
    handle_ai_chat_request,
    assess_message_risk,
    request_human_validation,
    handle_validation_response,
)

# db is attached to the Flask app instance by create_app() in __init__.py
# (app.db = db). Flask-SocketIO runs event handlers inside an app context,
# so current_app.db reaches that same shared instance here too -- no
# separate module-level variable needed.
#
# `session` (Homework 2) works here the same way: Flask-SocketIO ties its
# event handlers to the same signed session cookie the page's HTTP requests
# use, so state stashed here in one message (see request_human_validation
# in llm.py) is still there on the next.


@socketio.on('send_message')
def handle_message(data):
    user_message = data.get('message', '').strip()

    if not user_message:
        return

    try:
        db = current_app.db
        if session.get('pending_validation'):
            ai_response = handle_validation_response(db, user_message)
        elif assess_message_risk(user_message):
            ai_response = request_human_validation(user_message)
        else:
            ai_response = handle_ai_chat_request(db, role="Orchestrator", message=user_message)
    except Exception as error:
        print(f"LLM error: {error}")
        ai_response = "Sorry, something went wrong answering that."

    emit('receive_message', {'response': ai_response})
```

Save the file. Read the new `handle_message` body carefully — it's a 3-way `if`/`elif`/`else`, checked in this exact order, and the order is what makes the whole workflow correct:

1. **Is a confirmation already pending?** (`session.get('pending_validation')`) If so, this message is treated as the yes/no answer, full stop — it never reaches the Orchestrator as a "new" request.
2. **Otherwise, does *this* message look risky?** (`assess_message_risk(...)`) If so, pause and ask — again, it never reaches the Orchestrator this turn.
3. **Otherwise**, proceed exactly as Homework 1 did.

You do not need to change anything in `llm.py`'s `handle_ai_chat_request` for this — the gate lives entirely in this one function, one layer above it.

**✅ Check-In Stage 2.2 — confirm the gate blocks a destructive message.** Restart the app if it's running, open the chat, and type:

```
Delete all my skills
```

Expected: the chat replies with a confirmation question (something like *"This looks like it could delete or modify data..."*), **not** an immediate deletion. Refresh the page and confirm your skills are all still there — nothing should have changed in the database yet, because the Write Expert was never invoked.

Now reply:

```
no
```

Expected: a cancellation message (*"Okay, I won't do that..."*), and your skills are still all present after a page reload.

If instead the chat immediately deletes something, double check you replaced the *entire* file in 2.2 (especially the `if session.get('pending_validation')` line) and that you're not still running an old process (`Ctrl+C` and restart `python app.py` fully).

#### 2.3 — Give the Write Expert deletion capability

Right now, even if you answer "yes" to a delete confirmation, the Write Expert's prompt (from `llm_roles.csv`) only ever told it how to *insert* rows — it has no idea deletion is a valid action, so it may generate broken or unhelpful code. Fix that by updating the **Database Write Expert** row in `flask_app/database/initial_data/llm_roles.csv` (same editing approach as Step 1.9 — spreadsheet program recommended). Update these two columns:

| Column | New content |
|---|---|
| `specific_instructions` | Respond with executable Python only, calling `db.insertRows(table, columns, values)` for additions, or `db.query(...)` for deletions (e.g. `DELETE FROM <table> WHERE ...`). For an addition, first use `db.query(...)` to check whether the item already exists. For a deletion, first use `db.query(...)` with a `SELECT COUNT(*)` to know how many rows will be affected before deleting them. End your code by assigning a variable named `outcome` to the exact message to show the user: `'New <element> added to the <table> table.'` after an insert, `'Element already exists in the <table> table.'` if you found it already there and skipped the insert, or `'Deleted <N> row(s) from the <table> table.'` after a delete — filling in `<element>`/`<table>`/`<N>` with the real values you used. No markdown, no explanation. |
| `background_context` | *(keep everything already there from Homework 1, and add this sentence to the end of it)*: Each table also has an internal embedding column, maintained automatically — never set it yourself. `db.query(sql)` can also run `DELETE` statements directly (not just `SELECT`), which is how deletion/removal requests should be implemented. |
| `few_shot_examples` | *(keep the existing insert example, and add this second example after it, separated by `\|`)*: Request: Delete all his skills -> `total = db.query('SELECT COUNT(*) as total FROM skills')[0]['total']; db.query('DELETE FROM skills'); outcome = f'Deleted {total} row(s) from the skills table.'` |

You do **not** need to change `execute_write_action` in `llm.py` for this — it already runs whatever Python the Write Expert generates via `exec()`, and `db.query()` already executes arbitrary SQL (insert or delete), so this is entirely a prompt-configuration change, not a code change.

Save the CSV, and restart the app so the edited row gets re-seeded.

**✅ Check-In Stage 2.3 — confirm "yes" actually executes.** With the app running, type:

```
Delete all my skills
```

then reply:

```
yes
```

Expected: your terminal shows the Write Expert generating code that calls `db.query('DELETE FROM skills')` (or similar), the chat replies with something like *"Deleted 6 row(s) from the skills table."*, and — without a manual page reload — the skill badges disappear from the resume panel on screen. Reload the page to double-check they're really gone from the database, not just hidden.

**Restart the app one more time before moving on**, so `createTables(purge=True)` reseeds fresh data — otherwise you'll spend Step 3 testing against a resume with no skills left in it.

### Step 3: Test it end to end

| Test input | What happens | What you should see |
|---|---|---|
| "Find my MSU experience" | Orchestrator routes to the Semantic Search Expert | Console prints `institutions\|MSU`; reply correctly names Michigan State University |
| "What AI skills do I have?" | Orchestrator routes to the Semantic Search Expert over `skills` | Reply lists skills like "Machine Learning"/"Deep Learning" even without the word "AI" appearing anywhere |
| "Delete all my skills" | `assess_message_risk` → `True` | Chat asks for yes/no confirmation; nothing deleted yet |
| ...then "no" | `handle_validation_response` | "Request was cancelled"; skill count unchanged |
| "Delete all my skills" again, then "yes" | `handle_validation_response` → Orchestrator → Write Expert | "Deleted N row(s)..."; resume panel updates; skill count is 0 |
| "How long did they work at Michigan State University?" (exact name) | Orchestrator may route to either the Read Expert or the Semantic Search Expert — both work | Still an accurate reply, same as Homework 1 |

If a step misbehaves, the console `print()` lines (from `handle_ai_chat_request` and `[Orchestrator] executing: ...`) are your first debugging tool, same as Homework 1.

> **Watch your API usage.** Every semantic search adds one embeddings call in addition to the chat calls Homework 1 already made — a compound question that also needs an abbreviation resolved can now cost more model/embedding calls than either homework alone. Test deliberately rather than repeatedly re-running the same prompt while debugging.

---

## Known Limitations

This design was tested against a real model with a wide range of questions — not just the two rubric scenarios — before being written up. One real bug turned up during that testing and is already fixed in the steps above (Step 2.0); it's documented here so you understand *why* the code looks the way it does, not because you need to fix it again:

- **`query()` used to leak a connection on failure.** If `cursor.execute()` raised an exception (e.g. a `FOREIGN KEY` violation from a blocked delete), every line after it — including `connection.close()` — never ran, leaving that connection open and holding a lock. This was invisible through Homework 0 and Homework 1, where nothing routinely failed a query, but Homework 2's deletion flow makes that kind of failure *expected and routine* (that's the whole point of catching a bad delete instead of corrupting data). Left unfixed, one blocked delete would lock every subsequent database call in the app with a `database is locked` error that gave no hint what actually caused it. Fixed by wrapping the connection's use in `try`/`finally` in `query()`, `insertRows()`, and `_updateEmbedding()`.

A few more things you should expect, not fix — they're inherent to this design, not bugs in it:

- **Brute-force similarity search, not an index.** `semanticSearch` scans every embedded row and computes cosine similarity in Python. This is the from-scratch, SQLite-only stand-in for Postgres's `pgvector` + `ivfflat` index (which the official course spec uses) — fine at this dataset's size (a handful of institutions/experiences/skills), but wouldn't scale to a table with millions of rows the way a real vector index would.
- **Keyword-only risk detection.** `assess_message_risk` is a substring scan for `delete`/`remove`/`clear`/`drop`/`destroy` — it has no idea what the message actually *means*. "Please don't delete anything" triggers it (a false positive); a request that's destructive without using any of those words wouldn't (a false negative, e.g. "empty out my skills list"). This is a deliberate simplification, not a bug — see "Questions to Think About" #2.
- **The Orchestrator's expert choice isn't guaranteed correct.** Nothing stops the model from routing a question to the Read Expert when the Semantic Search Expert would've served it better, or vice versa — it's a judgment call baked into the Orchestrator's prompt and few-shot examples (Step 1.9), not something enforced in code. This isn't hypothetical: during testing, "What AI skills do I have?" was initially routed to the Content Expert instead of the Semantic Search Expert, purely because only one few-shot example (the MSU one) demonstrated the new role — adding a second example that actually matched the skills-table scenario fixed it. The general lesson survives even after that fix: a role is only as reliable as the examples that demonstrate it, and there's no guarantee every possible phrasing generalizes correctly from the examples you happened to write.
- **Deleting a row with dependents can fail.** `positions.sql`/`experiences.sql`/`skills.sql` declare real `FOREIGN KEY` constraints, enforced since Homework 1's `PRAGMA foreign_keys = ON`. Deleting from a table that something else still references (e.g. deleting an `experience` while `skills` rows still point at it) raises an integrity error, which `execute_write_action` catches and reports as `"Operation was unsuccessful."` rather than silently orphaning data — but it also means "delete everything" only cleanly succeeds on leaf tables like `skills`. Test with that in mind.

---

## Questions to Think About

You don't need to submit answers, but you'll be asked about these:

1. **Why embed at write-time instead of query-time?** What would change (correctness, cost, latency) if `semanticSearch` computed every row's embedding fresh on each call, instead of reading precomputed ones from the `embedding` column?
2. **Keyword scan vs. real risk assessment.** What's a message that should be flagged as risky but isn't, given `DANGEROUS_KEYWORDS`? What's one that gets flagged but shouldn't be? What would a more robust (but more expensive) check look like?
3. **Why gate in `socket_events.py` instead of inside `handle_ai_chat_request`?** The validation check could have lived one layer deeper, checked on every expert call instead of once per user message. What would break, or become redundant, if it did?
4. **Semantic search versus exact SQL — who should decide?** Right now the Orchestrator chooses which expert to route a request to, based on its prompt instructions and few-shot examples — and Step 1.9 showed that choice can be fragile until the examples actually cover the case. What would it take to make that decision more reliable — and is that a prompting problem, a code problem, or both?
5. **What's still missing for a real production system?** Homework 1 asked this about `eval()`/`exec()`. Now that there's a confirmation gate in front of destructive actions, what's still missing before you'd trust this with a stranger's real data — audit logging? Undo? Rate limiting? Something else?

---

## Submitting

Push your work to your fork:

```bash
cd "homework 2"
git add .
git commit -m "Homework 2"
git push origin main
```

Then record a short demo video (see `documentation/rubric.md` for exactly what to show and how it's graded), and submit **both** of the following via the course submission form:

1. Your demo video
2. Your fork's GitHub URL (e.g. `https://github.com/YOUR-USERNAME/ai-agents`) so the grader can view your code
