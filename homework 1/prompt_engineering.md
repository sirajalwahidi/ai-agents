# Prompt Engineering Concepts & Reflection — CSE 491 Homework 1

In this homework, we transformed a single system prompt chatbot into a multi-expert AI agent system using structured prompt engineering techniques. Below are 3 key prompt engineering concepts applied in the project, along with an evaluation of their effectiveness and real-world edge-case solutions.

---

## 1. Role-Based Persona Prompting (Expert Specialization)
* **Concept:** Assigning distinct system personas, constraints, and domain limits to individual LLM calls using a shared template (`MASTER_TEMPLATE`).
* **Implementation:** Instead of using a single general-purpose system prompt to handle SQL, Python execution, and content synthesis simultaneously, we specialized each agent via template parameters (`role`, `domain`, and `specific_instructions`).
* **Effectiveness:** Highly Effective. By constraining each expert's operational scope (e.g., forcing the `Database Read Expert` to output ONLY raw SQLite `SELECT` queries without markdown code fences or conversational filler), syntax accuracy increased drastically, completely eliminating output parsing errors.

---

## 2. Few-Shot In-Context Learning (Pattern Enforcement & Schema Join Fix)
* **Concept:** Providing concrete input-output examples directly within the system prompt to guide the LLM's structural formatting and execution logic without model fine-tuning.
* **Implementation:** We seeded representative examples into the `few_shot_examples` field in the `llm_roles` database table. This served two crucial functions:
  1. Guiding the `Orchestrator` to format execution plans as evaluable Python list strings (e.g., `["handle_ai_chat_request(...)"]`) for `eval()`.
  2. Training the `Database Write Expert` to handle schema-mismatch edge cases by executing a two-step relational query (`SELECT experience_id FROM experiences JOIN positions JOIN institutions ...`) to resolve the target ID before invoking `db.insertRows()`.
* **Effectiveness:** Critical to System Stability. Without explicit few-shot patterns, the Write Expert attempted to pass SQL subqueries inside string arrays to `db.insertRows()`, triggering SQLite parameterization errors. Supplying a multi-step Python execution pattern in the few-shot context completely resolved this relational edge case.

---

## 3. Task Decomposition and Multi-Agent Orchestration
* **Concept:** Breaking complex, compound user prompts into a deterministic sequence of simple, independent sub-tasks executed by specialized agents.
* **Implementation:** The `Orchestrator` receives compound requests (e.g., *"Does he know Rust? If not, add it to his Independent Technical Services experience."*), breaks them down into an ordered execution list (`Database Read Expert` check first, followed by `Database Write Expert` update), and processes their responses sequentially.
* **Effectiveness:** Highly Effective. Task decomposition prevents logical hallucinations and enables stateful decision-making. Empirical testing demonstrated that combining task decomposition with structured multi-agent context ensures database mutations occur strictly when prerequisite query conditions are satisfied.