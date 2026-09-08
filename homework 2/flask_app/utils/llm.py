"""
llm.py — sends messages to an AI language model via the OpenRouter API.

This file is the bridge between your Flask app and an AI model (GPT-3.5).
When a student types a message in the chat, it travels here, gets sent to
OpenRouter, and the AI's reply comes back.

KEY CONCEPTS:
  - API (Application Programming Interface): a way for two programs to talk
    to each other over the internet. OpenRouter exposes an API we can call.
  - HTTP POST request: sending data to a server (like submitting a form).
    We POST the conversation to OpenRouter and it POSTs back the AI reply.
  - System prompt: instructions given to the AI before the conversation starts.
    Think of it as the AI's job description.
"""

import os
import re
import requests
from flask import session
from jinja2 import Template

# The URL we send our messages to.
# OpenRouter acts as a single gateway to many different AI models.
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Which AI model to use. OpenRouter supports many models.
# Models with ':free' suffix are free to use — no API credits needed.
# See all available models at: https://openrouter.ai/models
# QUESTION: What would change if you switched to a different model?
#           Try 'google/gemma-2-9b-it:free' or 'mistralai/mistral-7b-instruct:free'.
DEFAULT_MODEL = "openai/gpt-4o-mini"

# 1. القالب الرئيسي الموحد لجميع الخبراء (Master Prompt Template)
# يتم استخدام Jinja2 لتمرير المتغيرات بشكل ديناميكي (مثل تعليمات الخبير، السياق، والأمثلة)

MASTER_TEMPLATE = Template(
    """\
You are a {{ role }}, an expert in {{ domain }}.

{{ specific_instructions }}
{% if background_context %}
Context:
{{ background_context }}
{% endif %}
{% if few_shot_examples %}
Examples:
{{ few_shot_examples }}
{% endif %}
Request: {{ request }}
""",
    trim_blocks=True,
    lstrip_blocks=True,
)


def fill_template(
    role,
    domain,
    specific_instructions,
    request,
    background_context="",
    few_shot_examples="",
):
    """
    الدالة: fill_template
    الوظيفة: دمج بيانات خبير معين مع القالب الرئيسي لإنتاج الـ System Prompt النهائي.
    ملاحظة: المقاطع الشرطية {% if %} في القالب تتكفل بإلغاء عناوين "Context:" أو "Examples:"
    تلقائياً إذا كانت النصوص الخاصة بها فارغة منعاً لإرباك النموذج.
    """
    return MASTER_TEMPLATE.render(
        role=role,
        domain=domain,
        specific_instructions=specific_instructions,
        background_context=background_context,
        few_shot_examples=few_shot_examples,
        request=request,
    ).strip()


def send_message(user_message, system_prompt="You are a helpful assistant."):
    """
    Send a message to the AI and return its response as a string.

    Args:
        user_message  (str): The message the user typed in the chat.
        system_prompt (str): Instructions that define how the AI should behave.
                             This is sent before the user message, every time.

    Returns:
        str: The AI's reply text, or an error message if something went wrong.

    HOW IT WORKS:
        We build a 'messages' list with two entries:
          1. system — gives the AI its instructions (the resume context)
          2. user   — the student's actual question
        We send this list to OpenRouter, which forwards it to the AI model
        and returns the generated reply.

    # NOTE: This function has no memory — each call starts fresh.
    #       Every message includes the full system prompt but no chat history.
    # QUESTION: How would you modify this to remember previous messages?
    #           Hint: you would need to store past messages and include them
    #           in the 'messages' list between the system and user entries.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")

    # If the .env file is missing or the key was not filled in, tell the user
    # immediately rather than making a doomed API call that will just hang.
    if not api_key or api_key == "paste-your-key-here":
        return "⚠️ No API key found. Add your OpenRouter key to the .env file and restart the app."

    # The Authorization header tells OpenRouter who we are.
    # "Bearer" is just a standard prefix for API key authentication.
    # NEVER hardcode the api_key here — always load it from the .env file.
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8080",  # identifies our app to OpenRouter
    }

    # The messages list defines the conversation context for the AI.
    # 'system' sets the AI's role and knowledge before it sees our question.
    # 'user' is the message the student actually typed.
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # Send the HTTP POST request to OpenRouter.
    # timeout=30 means: give up if we don't hear back within 30 seconds.
    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json={"model": DEFAULT_MODEL, "messages": messages},
        timeout=30,
    )

    result = response.json()

    # OpenRouter sometimes returns HTTP 200 but with an 'error' field instead
    # of 'choices' — this happens with a bad API key or an invalid request.
    # QUESTION: Print result here and see what OpenRouter actually sends back.
    if "error" in result:
        error_message = result["error"].get("message", "Unknown API error")
        return f"⚠️ OpenRouter error: {error_message}"

    if "choices" not in result:
        return f"⚠️ Unexpected response from OpenRouter: {result}"

    return result["choices"][0]["message"]["content"]


import re
from jinja2 import Template


# ==========================================
# الدالة الرئيسية لتوجيه الرسائل للخبراء
# ==========================================
def handle_ai_chat_request(db, role, message):
    """
    الدالة: handle_ai_chat_request
    الوظيفة: توجيه رسالة المستخدم إلى الخبير المحدد، جلب إعداداته، بناء الـ Prompt، وتمرير المخرجات.
    """
    # إذا لم يُحدد دور، يتم استخدام النمط القديم المباشر (كـ Fallback)
    if role is None:
        return send_message(message)

    # جلب إعدادات الخبير المحدد من جدول llm_roles في قاعدة البيانات
    config = db.getLLMRoles()[role]
    background_context = config["background_context"] or ""

    # خبير المحتوى (Content Expert): يجلب نص السيرة الذاتية المباشر كـ Context
    if role == "Content Expert":
        background_context += "\n" + db.getResumeText()

    # (fill_template) باستخدام القالب الموحد System Prompt بناء الـ
    system_prompt = fill_template(
        role=config["role"],
        domain=config["domain"],
        specific_instructions=config["specific_instructions"],
        background_context=background_context,
        few_shot_examples=config["few_shot_examples"] or "",
        request=message,
    )

    # إرسال الطلب إلى النموذج وجلب النتيجة
    output = send_message(message, system_prompt).strip()
    print(
        f"[{role}] generated:\n{output}\n"
    )  # طباعة المخرجات في الـ Terminal للمتابعة والتقييم

    # توجيه المخرجات للدالة المناسبة حسب نوع الخبير
    if role == "Database Read Expert":
        return execute_read_query(db, output)
    if role == "Database Write Expert":
        return execute_write_action(db, output)
    if role == "Database Semantic Search Expert":
        return execute_semantic_search(db, output)
    if role == "Orchestrator":
        return run_orchestrator_plan(db, message, output)

    return output  # بالنسبة لـ Content Expert، النتيجة هي الإجابة النهائية مباشرة


# ==========================================
# 1. تنفيذ استعلامات القراءة (Read Query)
# ==========================================

def execute_read_query(db, sql):
    """
    الدالة: execute_read_query
    الوظيفة: تشغيل استعلام SQL الناتج عن (Database Read Expert).
    الأمان: يرفض أي استعلام لا يبدأ بـ SELECT لضمان عدم التعديل على البيانات من هذا الخبير.
    """
    if not sql.strip().upper().startswith("SELECT"):
        return "Sorry, I couldn't safely answer that question."
    try:
        return str(db.query(sql))
    except Exception as error:
        print(f"Read Expert query failed: {error}")
        return "Sorry, that question couldn't be answered."

    
# ==========================================
# 2. تنفيذ البحث الدلالي (Semantic Search Expert)
# ==========================================

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

    الوظيفة بالمختصر:
    تنفيذ خبير البحث الدلالي؛ تقوم بتفكيك نص المخرجات المنسق بصيغة "table|query" عند أول رمز "|"،
    وتمرر اسم الجدول واستعلام البحث إلى دالة db.semanticSearch() لطلب النتائج، مع معالجة الاستثناءات برسال تفادية لمنع توقف الخادم.
    """
    try:
        # تنظيف النص من أية إشارات مائلة عكسية (\) قد يضيفها النموذج تلقائياً
        clean_output = output.replace('\\|', '|').replace('\\', '').strip()
        table, query_text = clean_output.split('|', 1)
        return str(db.semanticSearch(table.strip(), query_text.strip()))
    except Exception as error:
        print(f"Semantic search failed: {error}")
        return "Sorry, that question couldn't be answered."
    

# ==========================================
# 3. تنفيذ أكواد التعديل والإضافة (Write Action)
# ==========================================

def execute_write_action(db, generated_code):
    """
    الدالة: execute_write_action
    الوظيفة: تنفيذ كود Python المولد بواسطة (Database Write Expert) باستخدام exec().
    ملاحظة: يتم تمرير NULL=None لتفادي الأخطاء إذا كتب النموذج NULL بدلاً من None.
    """
    local_vars = {}
    try:
        exec(generated_code, {"db": db, "NULL": None}, local_vars)
    except Exception as error:
        print(f"Write Expert code failed: {error}")
        return "Operation was unsuccessful."

    # استخراج الرسالة النهائية المحددة في متغير outcome داخل الكود المولد
    return local_vars.get("outcome", "Operation was unsuccessful.")


# ==========================================
# 4. تنفيذ وتنسيق خطة الـ Orchestrator
# ==========================================

def run_orchestrator_plan(db, original_request, plan_text):
    """
    الدالة: run_orchestrator_plan
    الوظيفة: تفكيك خطة الـ Orchestrator (قائمة استدعاءات Python)، تنفيذ كل خبير بالترتيب،
            ثم إجراء استدعاء أخير لتجميع وإعادة صياغة النتائج في رد واحد متناسق.
    """
    try:
        call_strings = eval(plan_text)  # تحويل النص إلى قائمة Python
    except Exception:
        print(f"Orchestrator returned an unparseable plan: {plan_text}")
        return "Sorry, I couldn't plan a response to that."

    results = []
    for call_string in call_strings:
        print(f"[Orchestrator] executing: {call_string}")
        # استخراج اسم الخبير والرسالة باستخدام الـ Regex
        match = re.search(r'role="([^"]*)",\s*message="([^"]*)"', call_string)
        role, message = match.group(1), match.group(2)

        # تنفيذ طلب الخبير المحدّد
        response = handle_ai_chat_request(db, role, message)
        results.append((role, message, response))

    # صياغة الملخص النهائي لإرساله للنموذج من أجل الصياغة النهائية
    steps_summary = "\n".join(f"{r}: {resp}" for r, m, resp in results)
    synthesis_prompt = (
        f'The user asked: "{original_request}"\n\n'
        f"Here is what each expert found or did:\n{steps_summary}\n\n"
        "Write ONE short, clear reply. A Database Write Expert step's result "
        "is already the exact message to show the user (e.g. 'New Python "
        "added to the skills table.') -- if one is present, reuse it "
        "verbatim rather than rephrasing it. Otherwise, summarize the "
        "other results in plain language. Never mention SQL, Python, code, "
        "or these internal steps."
    )
    return send_message(original_request, synthesis_prompt)


# ======================================================================
# HOMEWORK 2 — HUMAN VALIDATION WORKFLOW نظام الحماية والتأكيد البشري
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
# قائمة الكلمات المفتاحية الخطرة التي تشير إلى عمليات حذف أو تعديل تدميرية
DANGEROUS_KEYWORDS = ['delete', 'remove', 'clear', 'drop', 'destroy']


def assess_message_risk(message):
    """
    # إذا احتوت على أي كلمة خطرة لتحديد ما إذا كانت تحتاج تأكيداً True تفحص الرسالة وترجع 
    Return True if `message` contains a keyword associated with a
    destructive/irreversible database action.
    """
    lowered = message.lower()
    return any(keyword in lowered for keyword in DANGEROUS_KEYWORDS)


def request_human_validation(message):
    """
    # تُعلق الطلب الخطر وتحفظه في الـ session، ثم تطلب تأكيداً صريحاً من المستخدم بـ (yes/no)
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
    # (yes) تعالج رد المستخدم: تُنفذ الأمر الأصلي إذا كانت الإجابة،
     أو تُصلح وتُلغي إذا كانت (no)، أو تُعيد السؤال عند الإجابات الخاطئة
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
