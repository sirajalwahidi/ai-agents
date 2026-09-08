"""
database.py — manages all interactions with the SQLite database.

A database is an organized way to store and retrieve data. We use SQLite,
which stores everything in a single file (resume.db) — no server needed.

This file is organized as a class called `database`. You learned about classes
in your OOP course: a class bundles related data and functions together.
Here, the class bundles all database operations (creating tables, inserting
data, querying data) into one place.

HOW THE DATA IS ORGANIZED:
  institutions  (e.g. Michigan State University)
      └── positions  (e.g. Instructor)
              └── experiences  (e.g. CSE 491)
                      └── skills  (e.g. Python, level 10)
"""

import sqlite3
import csv
import os
import json
import math
from io import StringIO

from flask_app.utils.embeddings import generate_embedding

# Path to the SQLite database file — created automatically on first run
DB_PATH = 'flask_app/database/resume.db'

# Tables must be created in this order because of foreign key relationships.
# For example, 'positions' references 'institutions', so institutions must exist first.
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

class database:
    """
    Manages all interactions with the SQLite resume database.

    Usage:
        db = database()
        db.createTables(purge=True)   # sets up tables and loads CSV data
        data = db.getResumeData()     # returns the full resume as a dict
    """

    def __init__(self):
        """
        Store the path to the database file.
        Unlike PostgreSQL, SQLite needs no username, password, or host —
        just a file path.
        """
        self.db_path = DB_PATH

    # ------------------------------------------------------------------
    # CORE QUERY FUNCTION
    # ------------------------------------------------------------------

    def query(self, sql, params=()):
        """
        Execute any SQL statement and return results as a list of dicts.

        Args:
            sql    (str):   The SQL statement to run.
            params (tuple): Values to safely substitute into the SQL.

        Returns:
            list: A list of dicts for SELECT queries; empty list otherwise.

        WHY params INSTEAD OF F-STRINGS?
            Never put user input directly into SQL like:
                f"SELECT * FROM users WHERE name = '{name}'"
            A malicious user could type  '; DROP TABLE users; --  as their name.
            Using params=() tells SQLite to treat the value as data, not code.
            This is called "parameterized queries" and prevents SQL injection.
        """
        # Connect to the database file (creates it if it doesn't exist)
        connection = sqlite3.connect(self.db_path)
        try:
            # داخل الدالة query()، أضف تفعيل المفاتيح الأجنبية مباشرة بعد الاتصال:
            connection.execute("PRAGMA foreign_keys = ON") # تفعيل قيود العلاقات لضمان عدم إدخال معرفات خاطئة

            # row_factory lets us access columns by name: row['title']
            # instead of by index: row[0]
            connection.row_factory = sqlite3.Row

            cursor = connection.cursor()
            cursor.execute(sql, params)

            # Only fetch rows for queries that return data
            results = []
            if sql.strip().upper().startswith(('SELECT', 'PRAGMA')):
                results = [dict(row) for row in cursor.fetchall()]
            connection.commit()
        finally:
            connection.close()
        return results

    # ------------------------------------------------------------------
    # TABLE SETUP
    # ------------------------------------------------------------------

    def createTables(self, purge=False):
        """
        Create all database tables and load initial data from CSV files.

        Args:
            purge (bool): If True, drop existing tables first (fresh start).

        # QUESTION: What would happen if you ran the app twice without purge=True?
        #           The INSERT statements would try to insert duplicate IDs.
        #           Try it — comment out purge=True in __init__.py and restart.
        """
        data_folder = 'flask_app/database/'

        if purge:
            # Drop tables in reverse order so foreign keys don't block deletion
            for table in reversed(TABLE_ORDER):
                self.query(f"DROP TABLE IF EXISTS {table}")

        # Create each table using its .sql file, then seed it from its .csv file
        for table in TABLE_ORDER:
            self._create_table(data_folder, table)
            self._seed_table(data_folder, table)

    def _create_table(self, data_folder, table):
        """Read the .sql file for a table and execute it."""
        sql_file = os.path.join(data_folder, 'create_tables', f'{table}.sql')
        with open(sql_file) as f:
            self.query(f.read())

    def _seed_table(self, data_folder, table):
        """
        Load initial data from a CSV file into a table.

        The CSV files in flask_app/database/initial_data/ are where you
        customize the resume content. Each file corresponds to one table.

        # NOTE: Edit these CSV files to add your own resume data!
        #       Restart the app after editing to reload the database.
        """
        csv_file = os.path.join(data_folder, 'initial_data', f'{table}.csv')

        if not os.path.exists(csv_file):
            return

        with open(csv_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return

        columns = list(rows[0].keys())
        placeholders = ', '.join(['?' for _ in columns])
        column_names = ', '.join(columns)
        sql = f"INSERT OR IGNORE INTO {table} ({column_names}) VALUES ({placeholders})"

        # Convert "NULL" strings from CSV into Python None values
        values = [
            tuple(None if cell == 'NULL' else cell for cell in row.values())
            for row in rows
        ]

        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.executemany(sql, values)
        connection.commit()
        connection.close()
        print(f"  Loaded data for table: {table}")

    # ------------------------------------------------------------------
    # RESUME DATA
    # ------------------------------------------------------------------

    def getResumeData(self):
        """
        Return the full resume as a nested dictionary.

        Structure:
            {
              inst_id: {
                'name': '...', 'type': '...',
                'positions': {
                  position_id: {
                    'title': '...', 'start_date': '...',
                    'experiences': {
                      experience_id: {
                        'name': '...', 'description': '...',
                        'skills': { skill_id: {'name': '...', 'skill_level': 7} }
                      }
                    }
                  }
                }
              }
            }

        This nested structure is passed directly to the resume.html template,
        where Jinja2 loops over it to render the page.
        """
        resume = {}

        for institution in self.query("SELECT * FROM institutions"):
            inst_id = institution['inst_id']
            resume[inst_id] = dict(institution)
            resume[inst_id]['positions'] = {}

            positions = self.query(
                "SELECT * FROM positions WHERE inst_id = ? ORDER BY start_date DESC",
                (inst_id,)
            )

            for position in positions:
                pos_id = position['position_id']
                resume[inst_id]['positions'][pos_id] = dict(position)
                resume[inst_id]['positions'][pos_id]['experiences'] = {}

                experiences = self.query(
                    "SELECT * FROM experiences WHERE position_id = ? ORDER BY start_date DESC",
                    (pos_id,)
                )

                for experience in experiences:
                    exp_id = experience['experience_id']
                    resume[inst_id]['positions'][pos_id]['experiences'][exp_id] = dict(experience)
                    resume[inst_id]['positions'][pos_id]['experiences'][exp_id]['skills'] = {}

                    skills = self.query(
                        "SELECT * FROM skills WHERE experience_id = ?",
                        (exp_id,)
                    )

                    for skill in skills:
                        skill_id = skill['skill_id']
                        resume[inst_id]['positions'][pos_id]['experiences'][exp_id]['skills'][skill_id] = dict(skill)

        self._format_dates(resume)
        return resume

    def _format_dates(self, resume):
        """
        Convert raw date strings like '2019-01-01' to 'YYYY-MM' format.
        None end_dates become 'Present'.
        Modifies the resume dict in place.
        """
        for institution in resume.values():
            for position in institution['positions'].values():
                position['start_date'] = self._short_date(position['start_date'])
                position['end_date'] = self._short_date(position['end_date']) or 'Present'

                for experience in position['experiences'].values():
                    experience['start_date'] = self._short_date(experience['start_date'])
                    experience['end_date'] = self._short_date(experience['end_date']) or ''

    def _short_date(self, date_string):
        """Return just the 'YYYY-MM' part of a date string, or None."""
        if date_string:
            return str(date_string)[:7]
        return None

    def getResumeText(self):
        """
        Return the resume as a plain-text string, used as context for the AI.

        # NOTE: This is exactly what the AI reads about you before answering
        #       questions. Edit your CSV files to change what it knows.
        # QUESTION: What information would you add to make the AI more helpful?
        """
        resume = self.getResumeData()
        lines = []

        for institution in resume.values():
            lines.append(f"\nInstitution: {institution['name']} ({institution['type']}) — {institution.get('city', '')}, {institution.get('state', '')}")

            for position in institution['positions'].values():
                lines.append(f"  Position: {position['title']} ({position['start_date']} to {position['end_date']})")
                lines.append(f"  Responsibilities: {position.get('responsibilities', '')}")

                for experience in position['experiences'].values():
                    lines.append(f"    Experience: {experience['name']} — {experience.get('description', '')}")

                    for skill in experience['skills'].values():
                        lines.append(f"      Skill: {skill['name']} (level {skill['skill_level']}/10)")

        return '\n'.join(lines)


    def getLLMRoles(self):
        """
        Method: getLLMRoles
        الوظيفة: جلب جميع إعدادات الخبراء من جدول llm_roles وترتيبها كـ Dictionary 
                يكون مفتاحه هو اسم الخبير (Role Name).
        """
        rows = self.query("SELECT * FROM llm_roles")
        return {row['role']: row for row in rows}

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

        الوظيفة: إدخال صف جديد في جدول محدد وتوليد الـ Embedding له أوتوماتيكياً
        إذا كان الجدول يقع ضمن جداول التضمين (EMBEDDING_FIELDS).
        """
        value_sql, bound_params = [], []
        for value in values:
            # Check if value is a subquery for foreign keys (e.g., "(SELECT ...)")
            # التحقق مما إذا كانت القيمة عبارة عن استعلام فرعي لجلب المفتاح الأجنبي
            if isinstance(value, str) and value.strip().startswith("(SELECT"):
                value_sql.append(value)
            else:
                value_sql.append("?")
                bound_params.append(value)
                
        # Build SQL query string / بناء استعلام الإدخال SQL
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(value_sql)})"

        # Open dedicated connection to capture lastrowid safely
        # فتح اتصال خاص بقاعدة البيانات للحصول على معرف الصف الجديد (lastrowid)
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            cursor = connection.cursor()
            cursor.execute(sql, tuple(bound_params))
            
            # Retrieve the auto-generated ID of the newly inserted row
            # الحصول على الـ ID الخاص بالصف الذي تم إدخاله للتو
            new_row_id = cursor.lastrowid
            connection.commit()
        finally:
            # Ensure connection is closed even if execution fails
            # إغلاق الاتصال بأمان في جميع الأحوال
            connection.close()

        # If the table requires embeddings, generate and save it immediately
        # إذا كان الجدول يحتاج متجهات تضمينية، نقوم بتحديث الـ embedding للصف الجديد
        if table in EMBEDDING_FIELDS:
            self._updateEmbedding(table, new_row_id)


    def _updateEmbedding(self, table, row_id):
        """
        Regenerate and store the embedding for one row, combining that
        table's EMBEDDING_FIELDS columns into a single string first (e.g.
        an institution's name + department). Stored as JSON text since
        SQLite has no native vector/array column type.

        الوظيفة: إعادة توليد وحفظ المتجه التضميني (Embedding) لصف واحد عن طريق دمج
        الحقول المحددة وتوليد المتجه ثم حفظه كـ JSON داخل قاعدة البيانات.
        """
        id_column = ID_COLUMNS[table]
        rows = self.query(f"SELECT * FROM {table} WHERE {id_column} = ?", (row_id,))
        if not rows:
            return

        row = rows[0]
        # Glue configured fields into one string / دمج الأعمدة المحددة في نص واحد
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

        الوظيفة: التمرير على الجداول وتوليد الـ Embeddings لكل الصفوف التي لا تملك متجهاً بعد
        (أي التي تحتوي على embedding IS NULL)، لضمان تغطية البيانات الأولية (CSV).
        """
        for table in EMBEDDING_FIELDS:
            id_column = ID_COLUMNS[table]
            rows = self.query(f"SELECT {id_column} FROM {table} WHERE embedding IS NULL")
            for row in rows:
                self._updateEmbedding(table, row[id_column])
            if rows:
                print(f"  Generated embeddings for {len(rows)} {table} row(s)")   


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

        الوظيفة بالمختصر:
         تنفيذ البحث الدلالي؛ تقوم بتوليد متجه لنص الاستعلام ومقارنته بمتجهات صفوف الجدول
         باستخدام قياس تشابه جيب التمام (Cosine Similarity)، ثم ترتب النتائج وتُرجع أعلى (top_k) صفوف.
         - مثال: البحث عن "MSU" يرجع صف "Michigan State University" برغـم عدم تطابق النصوص حرفياً.
         - عند البحث في جدول 'institutions'، تدمج تفاصيل المناصب (positions) تلقائياً لإلغاء الحاجة لطلب إضافي.
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

        الوظيفة بالمختصر:
         قياس مدى تشابه "المعنى الدلالي" بين نصين تحوّلا إلى متجهين رقميين:
         - النتيجة القريبة من 1: تعني أن النصين يحملان نفس الفكرة (مثال: "مطوّر بايثون" و "مهندس برمجيات").
         - النتيجة القريبة من 0: تعني عدم وجود علاقة بين النصين (مثال: "مطوّر بايثون" و "وصفة بيتزا").
         تتم الحسبة برياضيات المتجهات: (الضرب النقطي ÷ حاصل ضرب طول المتجهين).
        """
        dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
        magnitude_a = math.sqrt(sum(a * a for a in vector_a))
        magnitude_b = math.sqrt(sum(b * b for b in vector_b))
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        return dot_product / (magnitude_a * magnitude_b)        