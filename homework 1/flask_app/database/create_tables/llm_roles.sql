-- File: llm_roles.sql
-- الوظيفة: -- إنشاء جدول لتخزين أدوار وإعدادات خبراء الذكاء الاصطناعي
CREATE TABLE
    IF NOT EXISTS llm_roles (
        -- المعرف الفريد لكل دور/خبير (يتم زيادته تلقائياً)
        role_id INTEGER PRIMARY KEY AUTOINCREMENT,
        -- اسم الدور (مثل: Database Read Expert)، ويجب أن يكون فريداً ولا يتكرر
        role TEXT NOT NULL UNIQUE,
        -- المجال أو التخصص الذي يعمل فيه الخبير (مثلاً: SQL Query Generation)
        domain TEXT NOT NULL,
        -- التعليمات الصريحة والمباشرة الموجهة للنموذج لضبط سلوكه (System Instructions)
        specific_instructions TEXT NOT NULL,
        -- الخلفية والسياق العام (مثل هيكلية جداول قاعدة البيانات المتاحة له)
        background_context TEXT,
        -- أمثلة توضيحية لمدخلات ومخرجات متوقعة تدرب النموذج على النمط المطلوب (Few-Shot Examples)
        few_shot_examples TEXT
    );