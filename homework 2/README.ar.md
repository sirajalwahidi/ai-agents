# CSE 491 — الوكلاء الذكاء الاصطناعي: الواجب المنزلي 2

*[Read this file in English](README.md)*

## ما الذي تبنيه

أعطاك الواجب المنزلي 1 نظام وكلاء متعدد الخبراء قادرًا على القراءة من قاعدة بيانات حقيقية والكتابة إليها. الواجب المنزلي 2 يدفع بالسؤالين اللذين يفرضهما ذلك التصميم مباشرة:

1. **خبير قراءة قاعدة البيانات (Database Read Expert) يفهم التهجئة الحرفية فقط.** اسأله "منذ متى يعمل في MSU؟" فسيولّد `WHERE name = 'MSU'` — وهو استعلام لا يطابق شيئًا، لأن قاعدة البيانات تخزّن الاسم كـ `'Michigan State University'`. الذكاء الاصطناعي لا "يعرف" أن هذين يشيران إلى الشيء نفسه؛ إنه ببساطة يطابق نصًا حرفيًا. **البحث الدلالي (Semantic Search) يحل هذه المشكلة.** ستحوّل نص كل صف إلى *تضمين متجهي (vector embedding)* — قائمة من الأرقام تلتقط المعنى لا التهجئة — بحيث يقع "MSU" و"Michigan State University" قريبين من بعضهما في ذلك الفضاء المتجهي رغم أن السلسلتين النصيتين لا تشتركان في أي حرف. ثلاثة أشياء يجب أن تخرج بها من هذا النصف من الواجب:
   - التضمين المتجهي أداة بحث عن التشابه، وليس استدعاء ذكاء اصطناعي آخر — تحسبه مرة واحدة لكل صف، ثم تقارن المتجهات بعملية حسابية بسيطة (تشابه جيب التمام / cosine similarity)، دون أي "تفكير" من النموذج وقت الاستعلام.
   - أصبح لدى المنسّق (Orchestrator) الآن **خبير رابع يختار من بينه** — خبير جديد للبحث الدلالي في قاعدة البيانات (Database Semantic Search Expert)، إلى جانب خبراء القراءة والكتابة والمحتوى — وعليه أن *يقرر* متى يحتاج الطلب إلى هذا الخبير بدلًا من خبير القراءة الذي يطابق النص حرفيًا. هذا القرار هو نموذج صغير وحقيقي لنمط "فكّر ثم تصرف" (Thought → Action) الذي يقوم عليه معظم أطر عمل الوكلاء: فكّر فيما هو مطلوب، اختر الأداة الصحيحة، ثم فوّض المهمة إليها. إبقاء البحث الدلالي خبيرًا مستقلًا بذاته (له دوره الخاص ودالة تنفيذ خاصة به) بدلًا من كونه شيئًا ثانيًا قد يقوله خبير القراءة، يُبقي هذا القرار توجيهًا يعرف المنسّق أصلًا كيف يقوم به، بدلًا من شكل جديد من المخرجات يتوجّب على كل دالة لاحقة أن "تستنشقه" وتتعرّف عليه.
   - تُحسب التضمينات **مرة واحدة فقط، عند كتابة البيانات** (`insertRows`)، لا يُعاد حسابها مع كل سؤال — وهذه مفاضلة مهمة بين التكلفة والتصميم المعماري سترى انعكاسها مباشرة في الكود.

2. **خبير كتابة قاعدة البيانات (Database Write Expert) يُشغّل بالفعل كودًا مولَّدًا آليًا على قاعدة بيانات حقيقية باستخدام `exec()`.** قسم "القيود المعروفة" في الواجب المنزلي 1 أشار إلى هذه النقطة ثم تجاوزها. الواجب المنزلي 2 لا يستطيع تجاوزها: بمجرد أن يصبح بمقدور الوكيل حذف بيانات، لا بد من *شيء* يمنعه من فعل ذلك دون إشراف. ستبني **آلية تحقّق بشري (Human Validation Workflow)** — أي طلب يبدو إتلافيًا ("احذف"، "أزل"، ...) يتوقف وينتظر موافقة صريحة بـ"نعم" قبل تنفيذ أي شيء فعليًا. ثلاثة أشياء يجب أن تخرج بها من هذا النصف:
   - طلبات HTTP وWebSocket عديمة الحالة (stateless) — كل رسالة تصل دون أي ذاكرة عن الرسالة السابقة. تأكيد إجابة "نعم" مقابل الطلب المعلَّق *الصحيح* يتطلب تخزين حالة على الخادم عمدًا (باستخدام `session` في Flask) بين الرسائل.
   - فحص الكلمات المفتاحية الذي ستبنيه (`assess_message_risk`) مبسّط عن قصد — سريع ويمكن التنبؤ بسلوكه، وليس استدعاءً آخر للذكاء الاصطناعي. إنه خيار تصميمي حقيقي له ثغرات حقيقية، والمقصود منه أن يُناقَش (انظر "أسئلة للتفكير")، لا أن يكون حلًا نهائيًا.
   - يحدث فحص التأكيد **قبل** استدعاء المنسّق (Orchestrator) على الإطلاق، وليس مدفونًا داخل توجيه الخبراء — بحيث يبقى سؤال "هل من الآمن فعل هذا؟" منفصلًا معماريًا عن سؤال "كيف ننفذه؟".

مجتمعَين، فإن محور هذا الواجب هو **نمو القدرة والأمان معًا**: يصبح الوكيل أذكى (يستطيع الآن فهم الطلبات المعاد صياغتها أو المختصرة أو الفئوية) في الوقت ذاته الذي يصبح فيه أكثر حذرًا (لم يعد بإمكانه تنفيذ طلب إتلافي دون أن يسأل أولًا). لا غنى عن أي من النصفين — فوكيل أذكى لا يزال يحذف البيانات دون إشراف ليس أكثر أمانًا فعليًا من وكيل الواجب المنزلي 1، ووكيل حذر لا يستطيع فهم "MSU" ليس أكثر فائدة فعليًا.

يقدّم هذا الدليل كودًا جاهزًا لكل جزء، تمامًا كما في الواجب المنزلي 1 — مهمتك أن تتابع الخطوات، وتكتب الكود بنفسك، وتفهم ما يفعله كل جزء، وتختبره.

---

## كيف يعمل النظام

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

كل ما جاء في الواجب المنزلي 1 (الخبراء الأربعة الأصليون، قالب الأوامر المشترك، تدفّق التخطيط-ثم-التنفيذ الخاص بالمنسّق) يبقى دون تغيير في الأساس — ودالة `execute_read_query` تحديدًا لا تُمسّ إطلاقًا في هذا الواجب. هذا الواجب يضيف *خبيرًا* جديدًا واحدًا يمكن للمنسّق التوجيه إليه (خبير البحث الدلالي، وله دالة تنفيذ خاصة به هي `execute_semantic_search`)، وقدرة جديدة واحدة لخبير الكتابة (الحذف)، وبوابة جديدة واحدة أمام كل ذلك (التحقق).

---

## أمثلة على تدفّق العمل

**مثال 1 — البحث الدلالي يحلّ اختصارًا ("Find my MSU experience")**

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
     |  (joined in automatically, see Step 1.4)
     v
Orchestrator's synthesis call turns the row + positions into:
     "You worked at Michigan State University as an Instructor and a
      Researcher, both starting January 2019."
     v
Chat panel shows that reply. No SQL string match was ever attempted.
```

**مثال 2 — استعلام دلالي مركّب ("What AI skills do I have?")**

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

**مثال 3 — طلب إتلافي يُطلَب تأكيده ("Delete all my skills")**

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

**مثال 4 — الطلب نفسه، لكن مُلغى ("Delete all my skills" ← "no")**

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

أي إجابة ليست "yes" أو "no" (مثل "ربما"، أو رسالة غير ذات صلة كُتبت خطأً) تُبقي `pending_validation` كما هو وتعيد السؤال، بدلًا من الإلغاء الصامت أو المتابعة الصامتة.

---

## خريطة ملفات المشروع

أنت تبني فوق كودك من الواجب المنزلي 1. انسخ `homework 1/flask_app` و`app.py` إلى مجلد جديد باسم `homework 2/`، ثم قم بهذه التعديلات:

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

لا تغييرات على `requirements.txt` أو ملف `.env` — البحث الدلالي يعيد استخدام مكتبة `requests` نفسها ومفتاح `OPENROUTER_API_KEY` نفسه الذي تستخدمه استدعاءات الدردشة أصلًا (انظر الخطوة 1.0).

---

## البناء خطوة بخطوة

### الخطوة 1: البحث الدلالي

#### 1.0 لماذا OpenRouter، لا مفتاح API ثانٍ

النسخة الرسمية من هذا الواجب في المقرر تستدعي واجهة برمجة تطبيقات OpenAI للتضمينات مباشرة. أما في هذه البنية، فكل استدعاءات الدردشة تمر أصلًا عبر OpenRouter (دالة `send_message` في `flask_app/utils/llm.py`) — وOpenRouter يوفّر أيضًا نقطة نهاية **تضمينات (embeddings)** متوافقة مع OpenAI، فلا داعٍ لإدخال مزوّد ثانٍ أو مفتاح سري ثانٍ. مفتاح `OPENROUTER_API_KEY` واحد يغطي كلًا من الدردشة والتضمينات.

#### 1.1 خدمة التضمين

أنشئ الملف `flask_app/utils/embeddings.py`:

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

**جرّبها بمعزل عن الباقي** — نفّذ `python -c "from flask_app.utils.embeddings import generate_embedding; print(len(generate_embedding('hello world')))"` من داخل مجلد `homework 2`، ويجب أن تحصل على الناتج `1536`.

#### 1.2 أضف عمود `embedding` إلى كل جدول

SQLite لا يملك نوع بيانات متجهي أصلي (بخلاف امتداد `pgvector` في Postgres)، لذا سنخزّن التضمين كنص JSON — أي قائمة من 1536 رقمًا عشريًا محوّلة إلى سلسلة نصية. أضف سطرًا واحدًا إلى كل من `institutions.sql` و`positions.sql` و`experiences.sql` و`skills.sql` (وليس `llm_roles.sql` — إذ لا داعٍ للبحث الدلالي في إعدادات الخبراء أنفسهم):

```sql
embedding TEXT DEFAULT NULL,  -- JSON-encoded vector, for semantic search
```

#### 1.3 توليد التضمينات تلقائيًا عند الإدراج وعند بدء التشغيل

في `flask_app/utils/database.py`، أضف بالقرب من الأعلى (تحت `TABLE_ORDER`):

```python
import json
import math
from flask_app.utils.embeddings import generate_embedding

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

أعد كتابة `insertRows` بحيث تلتقط معرّف الصف الجديد وتضمّنه (تولّد له تضمينًا) فور إدراجه (هذا يحتاج إلى `cursor.lastrowid`، وهو ما لا تكشفه `self.query()`، لذا تفتح الدالة اتصالها الخاص بدلًا من استدعاء `self.query()`):

```python
def insertRows(self, table, columns, values):
    value_sql, bound_params = [], []
    for value in values:
        if isinstance(value, str) and value.strip().startswith("(SELECT"):
            value_sql.append(value)
        else:
            value_sql.append("?")
            bound_params.append(value)
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(value_sql)})"

    connection = sqlite3.connect(self.db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    cursor = connection.cursor()
    cursor.execute(sql, tuple(bound_params))
    new_row_id = cursor.lastrowid
    connection.commit()
    connection.close()

    if table in EMBEDDING_FIELDS:
        self._updateEmbedding(table, new_row_id)
```

أضف الدالة المساعدة التي تستدعيها، إلى جانب تعبئة تلقائية (backfill) عند بدء التشغيل للصفوف المزروعة من ملفات CSV (والتي لا تمر أبدًا عبر `insertRows`):

```python
def _updateEmbedding(self, table, row_id):
    """Regenerate and store one row's embedding from its EMBEDDING_FIELDS columns."""
    id_column = ID_COLUMNS[table]
    rows = self.query(f"SELECT * FROM {table} WHERE {id_column} = ?", (row_id,))
    if not rows:
        return
    row = rows[0]
    text = " ".join(str(row[field]) for field in EMBEDDING_FIELDS[table] if row.get(field))
    embedding = generate_embedding(text)

    connection = sqlite3.connect(self.db_path)
    connection.execute(f"UPDATE {table} SET embedding = ? WHERE {id_column} = ?",
                        (json.dumps(embedding), row_id))
    connection.commit()
    connection.close()


def backfillEmbeddings(self):
    """
    Generate embeddings for any row that doesn't have one yet. Safe to
    call every startup -- a row with embedding IS NOT NULL is already
    done and gets skipped.
    """
    for table in EMBEDDING_FIELDS:
        id_column = ID_COLUMNS[table]
        rows = self.query(f"SELECT {id_column} FROM {table} WHERE embedding IS NULL")
        for row in rows:
            self._updateEmbedding(table, row[id_column])
        if rows:
            print(f"  Generated embeddings for {len(rows)} {table} row(s)")
```

في `flask_app/__init__.py`، استدعِها مرة واحدة مباشرة بعد `db.createTables(purge=True)`:

```python
db.createTables(purge=True)
db.backfillEmbeddings()
```

أعد تشغيل التطبيق مرة واحدة وتفقّد سجل بدء التشغيل — يجب أن ترى `Generated embeddings for N <table> row(s)` لكل جدول من جداولك الأربعة. أعد التشغيل مرة أخرى دون تغيير أي بيانات، ويجب أن تختفي تلك الأسطر (لأن كل صف أصبح لديه تضمين بالفعل).

#### 1.4 البحث الدلالي نفسه

أضف `semanticSearch` والدالة المساعدة لحساب تشابه جيب التمام إلى `database.py`:

```python
def semanticSearch(self, table, query_text, top_k=3):
    """
    Return the top_k rows in `table` whose embedding is closest in
    MEANING to query_text, ranked by cosine similarity. This is a
    from-scratch, SQLite-friendly stand-in for what pgvector's `<=>`
    operator + an ivfflat index give you natively in Postgres -- here,
    similarity is computed in Python by scanning every embedded row.

    For 'institutions', each result also gets its `positions` attached
    via a normal SQL join -- this is what lets a single Semantic Search
    Expert call answer "how long did they work at MSU?"-style questions
    without a second round trip.
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
    """-1 (opposite meaning) to 1 (identical meaning)."""
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)
```

#### 1.5 أضف مُنفِّذًا لخبير البحث الدلالي الجديد

البحث الدلالي هنا **خبير مستقل بذاته** (له اسم دور خاص به، ودالة تنفيذ خاصة به) وليس شيئًا ثانيًا قد يقوله خبير القراءة — تمامًا كما أن `Database Read Expert` مرتبط بـ `execute_read_query` و`Database Write Expert` مرتبط بـ `execute_write_action`. في `flask_app/utils/llm.py`، اترك `execute_read_query` كما هي دون أي تعديل، وأضف فرعًا جديدًا في `handle_ai_chat_request`:

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

ثم أضف دالة التنفيذ الجديدة نفسها، في مكان قريب من `execute_read_query`:

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

لاحظ ما لا تحتاجه هذه الدالة: لا تعبيرات نمطية (regex)، ولا تحليل لعدة أشكال محتملة من النص. هي فقط تقسّم سطر رد الخبير على أول محرف `|` إلى جزأين — اسم الجدول ونص البحث — وتمرّرهما مباشرة إلى `db.semanticSearch()`.

#### 1.6 أضف إعداد خبير البحث الدلالي، وعلّم المنسّق متى يستخدمه

افتح `flask_app/database/initial_data/llm_roles.csv`. **لا تُغيّر صف Database Read Expert إطلاقًا** — اتركه كما هو من الواجب المنزلي 1. هناك تعديلان مطلوبان بدلًا من ذلك:

**أولًا، أضف صفًا جديدًا تمامًا** لخبير البحث الدلالي (`Database Semantic Search Expert`)، بحيث يوجّهه `specific_instructions` إلى الرد بسطر واحد بالضبط بالصيغة `<table>|<search text>` (اسم الجدول، ثم محرف `|`، ثم نص البحث)، ويشرح `background_context` ماذا يخزّن كل جدول وماذا يُطابَق فيه (institutions على name+department، وهكذا)، ويوضّح متى يُستخدَم هذا الخبير بدلًا من خبير القراءة (عندما يكون الاسم اختصارًا أو إعادة صياغة قد لا تطابق نص قاعدة البيانات الحرفي)، مع أمثلة قليلة (few-shot) توضّح الصيغة، مثل: `institutions|MSU` و`skills|AI and machine learning`.

**ثانيًا، حدّث صف Orchestrator** الموجود بحيث:
- تضيف `Database Semantic Search Expert` إلى قائمة أسماء الأدوار المسموح بها في `specific_instructions`.
- تذكر هذا الخبير الجديد ومتى يُفضَّل استخدامه في `background_context`.
- تضيف مثالين جديدين إلى `few_shot_examples` يوضّحان خطة من خطوة واحدة تستدعي `Database Semantic Search Expert` — أحدهما لسؤال "Find my MSU experience"، والآخر لسؤال "What AI skills do I have?".

**لا تتجاهل المثال الثاني.** عند اختبار هذا التصميم بمثال واحد فقط (المتعلق بـ MSU)، كان المنسّق أحيانًا يوجّه سؤال "What AI skills do I have?" إلى خبير المحتوى (Content Expert) بدلًا من خبير البحث الدلالي الجديد — تخمين بدا معقولًا ونجح بالمصادفة (لأن خبير المحتوى يقرأ نص السيرة الذاتية مباشرة)، لكنه تجاوز عملية الترتيب الدلالي الفعلية التي يريد معيار التقييم رؤيتها. إضافة مثال واحد إضافي ومطابق تمامًا حلّت المشكلة تمامًا. هذا درس عام يستحق التذكّر، لا مجرد إصلاح لمرة واحدة: **الدور الجديد موثوق بقدر الأمثلة التي توضّح استخدامه فقط** — مثال واحد يغطي نوعًا واحدًا من الأسئلة لا يعمّم تلقائيًا على نوع مختلف من الأسئلة، حتى لو بدا مشابهًا لقارئ بشري.

راجع ملف CSV المُسلَّم للصياغة الدقيقة لكل هذه الحقول. حافظ على أن يكون كل حقل في سطر واحد، وهو نفس القيد الذي فرضه محمّل CSV في الواجب المنزلي 1.

### الخطوة 2: آلية التحقّق البشري

#### 2.0 أصلح تسريب اتصال ستكشفه عمليات الحذف الفاشلة

افتح `flask_app/utils/database.py` وابحث عن `query()` — الدالة الأساسية التي تمر عبرها كل دالة أخرى في هذا الملف، دون تغيير منذ الواجب المنزلي 0. المشكلة: إن أثار `cursor.execute(sql, params)` استثناءً (مثل انتهاك قيد `FOREIGN KEY`)، فإن كل الأسطر التالية — بما فيها `connection.close()` — لا تُنفَّذ أبدًا، فيبقى الاتصال مفتوحًا وحاجزًا لقفل على ملف قاعدة البيانات. لم تكن هذه مشكلة عمليًا طوال الواجبين 0 و1 لأن لا شيء كان يجعل `cursor.execute()` يفشل بانتظام. لكنها تصبح مشكلة الآن: بمجرد أن يستطيع خبير الكتابة توليد `DELETE FROM experiences` على جدول لا تزال صفوف `skills` تشير إليه (الخطوة 2.3)، فإن فشل ذلك الحذف *متوقَّع ومقصود* — لكنه، بسبب هذا التسريب، يترك اتصالًا مفتوحًا، وأي استدعاء لاحق لقاعدة البيانات في أي مكان من التطبيق سيفشل برسالة `database is locked` غامضة الصلة بالسبب الحقيقي. هذا بالضبط نوع الخلل الذي يكشفه اختبار مجموعة متنوعة من الأسئلة، لا الاكتفاء بمثالي معيار التقييم فقط.

أصلحه بلف الجزء الخطر بـ `try`/`finally` بحيث يُنفَّذ `connection.close()` دائمًا:

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

طبّق النمط نفسه (فتح الاتصال داخل `try`، وإغلاقه في `finally`) على `insertRows` و`_updateEmbedding` اللتين كتبتهما في الخطوة 1 — كلتاهما تفتحان اتصالًا خاصًا بهما بنفس الطريقة، ومن الأسلم كتابتهما بهذا الشكل الصحيح منذ البداية.

**اختبار سريع:** بعد إعادة تشغيل التطبيق، جرّب طلب حذف من المتوقَّع أن يفشل (مثل "Delete all my experiences" ثم "yes")، ثم اطرح مباشرة سؤالًا عاديًا (مثل "What is this page about?"). إن أُجيب عن السؤال العادي بشكل طبيعي، فالإصلاح ناجح؛ وإن ظهرت رسالة `database is locked`، فتأكد من أن `try`/`finally` يغلّف كامل الجزء الذي قد يفشل، بنفس المسافة البادئة الموضحة أعلاه.

#### 2.1 اكتشاف الخطورة والتوقف

في `llm.py`، أضف:

```python
from flask import session

DANGEROUS_KEYWORDS = ['delete', 'remove', 'clear', 'drop', 'destroy']


def assess_message_risk(message):
    """A fast, predictable keyword scan -- not another AI call."""
    lowered = message.lower()
    return any(keyword in lowered for keyword in DANGEROUS_KEYWORDS)


def request_human_validation(message):
    """
    Stash the original message in the Flask session so the NEXT message
    can be recognized as its yes/no answer instead of a new, unrelated
    chat message -- HTTP/WebSocket requests are otherwise stateless.
    """
    session['pending_validation'] = message
    return (f'This looks like it could delete or modify data: "{message}". '
            f'Are you sure you want to proceed? (yes/no)')


def handle_validation_response(db, response):
    """Called instead of the normal chat flow while a validation is pending."""
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

تعمل `session` هنا بنفس طريقة عمل `current_app` — فـ Flask-SocketIO يربط معالِجات الأحداث بنفس ملف تعريف الارتباط (session cookie) الموقَّع الذي تستخدمه طلبات HTTP الخاصة بصفحتك، و`app.secret_key` مضبوط أصلًا في `__init__.py` منذ الواجب المنزلي 0، لذا يعمل هذا دون أي إعداد إضافي.

#### 2.2 مرّر الدردشة عبر هذه البوابة، قبل المنسّق

في `flask_app/utils/socket_events.py`، حدّث الاستيرادات وأعد كتابة `handle_message`:

```python
from flask import current_app, session
from flask_app.utils.llm import (
    handle_ai_chat_request,
    assess_message_risk,
    request_human_validation,
    handle_validation_response,
)

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

يحدث الفحص **هنا** — قبل استدعاء المنسّق على الإطلاق — لا داخل `handle_ai_chat_request`. هذا يُبقي بوابة الأمان منفصلة معماريًا عن توجيه الخبراء، ويعني أنها تُنفَّذ مرة واحدة فقط لكل طلب مستخدم، لا مرة لكل استدعاء داخلي قد يجريه المنسّق.

#### 2.3 اجعل خبير الكتابة قادرًا فعليًا على الحذف

لكي يكون لإجابة "نعم" شيء حقيقي تُثبته، يحتاج خبير الكتابة إلى قدرة على الحذف، لا الإدراج فقط. لا تحتاج `execute_write_action` إلى أي تعديل في الكود — فـ `db.query()` تُنفّذ أصلًا أي SQL، سواء إدراجًا أو حذفًا — هذا مجرد تغيير في الأوامر (prompt). حدّث صف **Database Write Expert** في `llm_roles.csv`: علّمه أن طلب الحذف/الإزالة يجب أن يولّد `db.query("DELETE FROM <table> WHERE ...")` (مع عدّ الصفوف المتأثرة أولًا، لأن `DELETE` نفسها لا تُعيد أي صفوف)، وأن يضبط `outcome` إلى رسالة على شاكلة `"Deleted N row(s) from the <table> table."` راجع ملف CSV المُسلَّم للصياغة الدقيقة ومثال عملي (few-shot).

### الخطوة 3: اختبره من البداية إلى النهاية

| المُدخَل التجريبي | ما يحدث | ما يجب أن تراه |
|---|---|---|
| "Find my MSU experience" | يوجّه المنسّق الطلب إلى خبير البحث الدلالي | الطرفية تطبع `institutions\|MSU`؛ الرد يذكر "Michigan State University" بشكل صحيح |
| "What AI skills do I have?" | يوجّه المنسّق الطلب إلى خبير البحث الدلالي على جدول `skills` | الرد يسرد مهارات مثل "Machine Learning"/"Deep Learning" حتى دون ظهور كلمة "AI" في أي مكان |
| "Delete all my skills" | `assess_message_risk` → `True` | تطلب الدردشة تأكيدًا بنعم/لا؛ لا شيء يُحذف بعد |
| ...ثم "no" | `handle_validation_response` | "تم إلغاء الطلب"؛ عدد المهارات دون تغيير |
| "Delete all my skills" مجددًا، ثم "yes" | `handle_validation_response` → المنسّق → خبير الكتابة | "تم حذف N صف/صفوف..."؛ لوحة السيرة الذاتية تتحدّث؛ عدد المهارات يصبح 0 |
| "How long did they work at Michigan State University?" (بالاسم الكامل الدقيق) | قد يوجّه المنسّق الطلب إلى خبير القراءة أو خبير البحث الدلالي — كلاهما يعمل | رد دقيق كما في الواجب المنزلي 1 |

إذا أخطأت إحدى الخطوات، فإن أسطر `print()` في الطرفية (من `handle_ai_chat_request` ومن `[Orchestrator] executing: ...`) هي أول أداة تصحيح تلجأ إليها، تمامًا كما في الواجب المنزلي 1.

> **راقب استهلاكك لواجهة برمجة التطبيقات (API).** كل عملية بحث دلالي تضيف استدعاء تضمين واحدًا فوق استدعاءات الدردشة التي كان الواجب المنزلي 1 يجريها أصلًا — فسؤال مركّب يحتاج أيضًا إلى حل اختصار قد يكلّف الآن استدعاءات نموذج/تضمين أكثر من أي من الواجبين بمفرده. اختبر بتروٍّ بدلًا من إعادة تشغيل الاستعلام نفسه مرارًا أثناء تصحيح الأخطاء.

---

## القيود المعروفة

اختُبِر هذا التصميم مقابل نموذج حقيقي بمجموعة واسعة من الأسئلة — لا سيناريوهَي معيار التقييم فقط — قبل كتابة هذا الدليل. ظهرت خلال ذلك الاختبار مشكلة حقيقية واحدة، وهي مُصلَحة بالفعل في الخطوات أعلاه (الخطوة 2.0)؛ تُوثَّق هنا لتفهم *لماذا* يبدو الكود بهذا الشكل، لا لأنك بحاجة لإصلاحها مجددًا:

- **كانت `query()` تُسرّب اتصالًا عند الفشل.** إن أثار `cursor.execute()` استثناءً (مثل انتهاك قيد `FOREIGN KEY` من عملية حذف مرفوضة)، فإن كل سطر بعده — بما فيه `connection.close()` — لم يكن يُنفَّذ أبدًا، فيبقى الاتصال مفتوحًا حاجزًا لقفل. لم تكن هذه المشكلة ظاهرة خلال الواجبين 0 و1، إذ لم يكن شيء يجعل استعلامًا يفشل بانتظام، لكن تدفّق الحذف في الواجب المنزلي 2 يجعل هذا النوع من الفشل *متوقَّعًا وروتينيًا* (فهذا بالضبط سبب وجود القيد أصلًا: التقاط حذف سيئ بدلًا من إتلاف البيانات). لو تُرِكت دون إصلاح، لكان حذف واحد محظور يُقفل كل استدعاء لاحق لقاعدة البيانات في التطبيق برسالة `database is locked` لا تلمّح إلى السبب الحقيقي. أُصلِحت بلفّ استخدام الاتصال بـ `try`/`finally` في كل من `query()` و`insertRows()` و`_updateEmbedding()`.

أشياء أخرى يجب أن تتوقعها، لا أن تُصلحها — فهي متأصّلة في هذا التصميم، لا أخطاء فيه:

- **بحث تشابه بالقوة الغاشمة (brute-force)، لا فهرس حقيقي.** تفحص `semanticSearch` كل صف مُضمَّن وتحسب تشابه جيب التمام بلغة Python. هذا بديل مبني من الصفر ومناسب لـ SQLite عن فهرس `pgvector` + `ivfflat` في Postgres (الذي تستخدمه مواصفة المقرر الرسمية) — وهو مناسب لحجم هذه البيانات (عدد قليل من المؤسسات/الخبرات/المهارات)، لكنه لن يتوسّع ليناسب جدولًا بملايين الصفوف كما يفعل فهرس متجهي حقيقي.
- **اكتشاف الخطورة عبر الكلمات المفتاحية فقط.** `assess_message_risk` هي فحص لسلاسل فرعية مثل `delete`/`remove`/`clear`/`drop`/`destroy` — وهي لا "تفهم" معنى الرسالة فعليًا. رسالة مثل "من فضلك لا تحذف شيئًا" ستُفعّل الفحص (إيجابية زائفة)؛ وطلب إتلافي لا يستخدم أيًا من تلك الكلمات لن يُفعّله (سلبية زائفة، مثل "أفرغ قائمة مهاراتي"). هذا تبسيط مقصود، لا خطأ — انظر السؤال رقم 2 في "أسئلة للتفكير".
- **اختيار المنسّق للخبير المناسب غير مضمون الصحة دائمًا.** لا شيء يمنع النموذج من توجيه سؤال إلى خبير القراءة كان من الأفضل توجيهه إلى خبير البحث الدلالي، أو العكس — إنه قرار متروك لأوامر المنسّق النصية وأمثلته القليلة (الخطوة 1.6)، لا شيء مفروض في الكود. هذا ليس افتراضيًا: أثناء الاختبار، تم في البداية توجيه سؤال "What AI skills do I have?" إلى خبير المحتوى بدلًا من خبير البحث الدلالي، لمجرد أن مثالًا واحدًا فقط (الخاص بـ MSU) كان يوضّح استخدام الدور الجديد — وقد أصلحت المشكلة إضافةُ مثال ثانٍ مطابق فعليًا لسيناريو جدول المهارات. الدرس العام يبقى صحيحًا حتى بعد هذا الإصلاح: الدور موثوق بقدر الأمثلة التي توضّحه، ولا ضمانة أن كل صياغة ممكنة تُعمَّم بشكل صحيح انطلاقًا من الأمثلة التي كتبتَها أنت.
- **حذف صف له تبعيات قد يفشل.** تُعرِّف `positions.sql`/`experiences.sql`/`skills.sql` قيود `FOREIGN KEY` حقيقية، مفعّلة منذ `PRAGMA foreign_keys = ON` في الواجب المنزلي 1. حذف صف من جدول لا يزال شيء آخر يشير إليه (مثل حذف `experience` بينما لا تزال صفوف `skills` تشير إليه) يثير خطأ تكامل (integrity error)، تلتقطه `execute_write_action` وتُبلغ عنه بـ `"Operation was unsuccessful."` بدلًا من ترك بيانات يتيمة بصمت — لكن هذا يعني أيضًا أن "احذف كل شيء" ينجح بنظافة فقط على الجداول الطرفية مثل `skills`. اختبر مع أخذ ذلك بعين الاعتبار.

---

## أسئلة للتفكير

لست مطالبًا بتسليم إجابات، لكنك ستُسأل عن هذه الأسئلة:

1. **لماذا التضمين وقت الكتابة لا وقت الاستعلام؟** ماذا سيتغيّر (من ناحية الصحة، والتكلفة، وزمن الاستجابة) لو أن `semanticSearch` كانت تحسب تضمين كل صف من جديد مع كل استدعاء، بدلًا من قراءة تضمينات محسوبة مسبقًا من عمود `embedding`؟
2. **فحص الكلمات المفتاحية مقابل تقييم خطورة حقيقي.** ما مثال رسالة ينبغي أن تُصنَّف خطِرة لكنها لا تُصنَّف كذلك بناءً على `DANGEROUS_KEYWORDS`؟ وما مثال رسالة تُصنَّف خطِرة رغم أنها لا ينبغي أن تكون كذلك؟ كيف سيبدو فحص أكثر متانة (لكن أكثر تكلفة)؟
3. **لماذا وضعنا البوابة في `socket_events.py` لا داخل `handle_ai_chat_request`؟** كان يمكن لفحص التحقق أن يعيش طبقة أعمق، ويُفحَص عند كل استدعاء خبير بدلًا من مرة واحدة لكل رسالة مستخدم. ماذا سينكسر، أو يصبح زائدًا عن الحاجة، لو حدث ذلك؟
4. **البحث الدلالي مقابل SQL الدقيق — من يجب أن يقرر؟** الآن يختار المنسّق أي خبير يوجّه إليه الطلب، بناءً على تعليماته النصية وأمثلته القليلة — وقد أظهرت الخطوة 1.6 أن هذا القرار قد يكون هشًا حتى تغطي الأمثلة الحالة فعليًا. ماذا يتطلّب الأمر لجعل هذا القرار أكثر موثوقية — وهل هذه مشكلة صياغة أوامر، أم مشكلة كود، أم كلتاهما؟
5. **ما الذي لا يزال ناقصًا لنظام إنتاجي حقيقي؟** طرح الواجب المنزلي 1 هذا السؤال بخصوص `eval()`/`exec()`. الآن وقد أصبحت هناك بوابة تأكيد أمام الإجراءات الإتلافية، ما الذي لا يزال ناقصًا قبل أن تثق بهذا النظام مع بيانات حقيقية لشخص غريب؟ سجل تدقيق (audit logging)؟ إمكانية التراجع (undo)؟ تحديد معدل الطلبات (rate limiting)؟ شيء آخر؟

---

## التسليم

ادفع (push) عملك إلى نسختك (fork):

```bash
cd "homework 2"
git add .
git commit -m "Homework 2"
git push origin main
```

بعد ذلك، سجّل فيديو عرض قصيرًا (راجع `documentation/rubric.md` لمعرفة بالضبط ما يجب عرضه وكيفية تقييمه)، وسلّم **كلا الأمرين** التاليين عبر نموذج تسليم المقرر:

1. فيديو العرض التوضيحي الخاص بك
2. رابط GitHub الخاص بنسختك (fork) (مثل `https://github.com/YOUR-USERNAME/ai-agents`) ليتمكن المُقيِّم من الاطلاع على كودك
