# 🛒 Smart E-Commerce Support & Order Tracking Multi-Agent System

🌐 **Language / اللغة:** **English** | [العربية](README_AR.md)

> **Final Project — AI Agents Course (CSE 491)**  
> **Root Directory:** `final-project-ecommerce-support-agent`

---

## 📌 1. Project Overview

The **Smart E-Commerce Support Agent** is an autonomous multi-agent system designed for e-commerce customer support. The system automatically processes and answers customer queries regarding order status, shipment tracking, and shipping updates with high precision, using session-bound authorization and layered security guardrails to protect customer data.

* **Target Audience:** E-commerce store owners, customer support teams, and technical helpdesk departments.
* **Core Objective:** Build a production-grade intelligent agent system combining Natural Language Understanding (LLM), Typed Function Calling, Dynamic Schema Awareness, Session Authorization, and Human-Centered Design principles.

---

## 🏗️ 2. Agent Architecture & Security Layers

The project adheres strictly to the fundamental AI Agent formulation:
$$\text{AI Agent} = \text{LLM} + \text{Planning} + \text{Tooling}$$

The system consists of **5 specialized components** wrapped inside strict security and verification layers:

1. **Orchestrator Agent:** Analyzes customer input, normalizes language/digits, performs intent detection, and routes queries to narrow, typed domain tools.
2. **Typed Reader Tools (`get_order_status`, `track_shipment`):** Parameterized read-only interfaces. Reads run on a read-only SQLite connection (URI `mode=ro`) with `PRAGMA query_only = ON` and a SQLite authorizer that blocks access to unauthorized tables and columns. The `customer_id` is bound to the authenticated session, never chosen by the model.
3. **Typed Writer Tools with Two-Phase Confirmation (`cancel_order`, `update_shipping_address`):** Prepares state-modifying actions via a two-phase protocol (Proposal -> User Confirmation Token -> Execution) to enforce human-in-the-loop validation in code rather than prompt-only guardrails. Execution re-validates ownership and order state at commit time.
4. **Grounding Verification Loop:** A secondary self-critique mechanism that inspects generated response drafts against raw tool outputs to detect and reduce ungrounded claims.
5. **Human-in-the-Loop (HITL) Escalation (`create_support_ticket`):** Suspends agent autonomy and logs structured tickets for human support upon low model confidence, complex financial claims, or explicit customer requests.

---

## 🔄 3. Technical Flow Diagram

```text
              +----------------------------------+
              | Customer Input (Arabic/English)  |
              +----------------------------------+
                               |
                               v
              +----------------------------------+
              |   Language & Digit Normalizer    |
              +----------------------------------+
                               |
                               v
              +----------------------------------+
              | Session Auth (bound customer_id) |
              +----------------------------------+
                               |
                               v
              +----------------------------------+
              |        Orchestrator Agent        |
              +----------------------------------+
                   /           |            \
                  /            |             \
                 v             v              v
       +--------------+ +--------------+ +--------------------+
       | Typed Read   | | Typed Write  | | Human-in-the-Loop  |
       |    Tools     | | (Two-Phase)  | |    Escalation      |
       +--------------+ +--------------+ +--------------------+
              \                |                   |
               \               v                   v
                ---> +-------------------+    +----------------+
                     |  SQLite Database  |    |  Human Agent   |
                     |  (ecommerce.db)   |    +----------------+
                     +-------------------+
                               |
                               v
                     +-------------------+
                     |     Grounding     |
                     | Verification Loop |
                     +-------------------+
                               |
                               v
                     +-------------------+
                     |   Send Response   |
                     +-------------------+
```

**Data access paths:**

* **Reads:** read-only connection + authorizer + session-scoped `customer_id`.
* **Writes:** parameterized statements only, executed after user confirmation, with ownership/state checks and an audit record.

---

## 🛠️ 4. Tech Stack & Security Tools

* **Language:** Python 3.10+
* **Primary LLM:** Google Gemini API (`google-genai` SDK v1.0+)
* **Tool Calling:** Native Parameterized Function Calling
* **Database & Security:** SQLite3 (`ecommerce.db`) with URI read-only mode, `PRAGMA query_only`, a SQLite authorizer, and session-bound `customer_id` authorization.
* **Input Utilities:** Custom Arabic-Indic digit normalizer and multi-lingual prompt handling.
* **User Interface:** Interactive Command-Line Interface (CLI) with real-time reasoning trace output.
* **Environment Management:** `python-dotenv` for API key security.

---

## 📁 5. Directory Structure

```text
final-project-ecommerce-support-agent/
│
├── database/
│   ├── schema.sql           # SQL DDL script defining all 4 relational tables
│   ├── seed_data.sql        # Mock data insertion script (Customers, Orders, Shipments)
│   ├── db_setup.py          # Database initialization & table creation runner
│   └── db_helper.py         # Secure typed execution tools & SQLite authorizer engine
│
├── .env                    # Environment variables (GEMINI_API_KEY)
├── requirements.txt        # Python dependency manifest
├── README_EN.md            # Complete project documentation (English)
├── README_AR.md            # Arabic project documentation
├── main.py                 # Application entry point and orchestrator execution loop
└── design_doc.pdf          # Architectural Design Specification Document
```

---

## 🗄️ 6. Database Schema (`ecommerce.db`)

The relational database comprises 4 normalized tables:

* **`customers`**: Stores customer identity records (`customer_id`, `name`, `email`, `phone`).
* **`orders`**: Tracks order lifecycle (`order_id`, `customer_id`, `order_date`, `status`, `total_amount`, `shipping_address`).
* **`shipments`**: Details logistics data (`tracking_number`, `order_id`, `carrier`, `current_location`, `estimated_delivery`, `status`).
* **`support_tickets`**: Manages HITL escalation workflow states (`ticket_id`, `order_id`, `status`: `bot_active` | `escalated_to_human` | `resolved`).

---

## 📊 7. Evaluation Metrics & Empirical Results

Agent performance was benchmarked across standard criteria using full end-to-end test scenarios in the execution environment:

| Metric | Definition | Benchmark / Empirical Result | Status / Notes |
| :--- | :--- | :--- | :--- |
| **Task Success Rate (TSR)** | Percentage of customer queries resolved accurately with grounded factual responses and zero security violations. | **100%** | Successfully passed read queries, IDOR boundary checks, shipment tracking, and illegal state cancellation blocks. |
| **Human-Intervention Rate (HIR)** | Ratio of complex or disputed tickets escalated to human support vs. resolved autonomously by the agent. | **20%** | 1 out of 5 core test scenarios triggered escalation (created Ticket #3 for order missing item claims). |
| **Time to Completion (TTC)** | Average latency to retrieve verified data, execute tools, and formulate grounded responses. | **1.8s – 2.5s** | High responsiveness leveraging direct SQLite native tools and Gemini Flash reasoning. |

### 🛡️ Security & Integrity Verification
* **IDOR Protection:** Verified that cross-account queries (e.g., Customer #1 accessing Order #3) are strictly denied at the database layer.
* **Two-Phase Protocol:** Verified that state modifications (cancellations/address updates) require valid confirmation tokens, successfully blocking unauthorized or bad-token executions.
* **State Logic Enforcement:** Verified that non-cancellable order states (e.g., `delivered` / `shipped`) automatically halt modification and offer human escalation.

---

## 🚀 8. Setup & Execution Guide

### 1️⃣ Virtual Environment Setup & Dependency Installation:
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2️⃣ API Key Configuration:
Create a `.env` file in the project root directory:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 3️⃣ Initialize Database & Seed Data:
```bash
python database/db_setup.py
```

### 4️⃣ Run Application:
```bash
python main.py
```

---

## 📅 9. Implementation Timeline (4-Week Schedule)

* **Week 1:** Project scope approval, System Design Document finalizing, and SQLite relational DB setup.
* **Week 2:** Orchestrator development and typed Read/Write function-calling tools integration.
* **Week 3:** Grounding Verification Loop integration and Human-in-the-Loop escalation handler implementation.
* **Week 4:** End-to-end evaluation, presentation preparation, and final repository submission.

---

## 🔮 10. Future Roadmap & Phase 2 (Production MVP Expansion)

While **Phase 1** successfully establishes a secure, single-session CLI proof-of-concept, the following architectural upgrades are designed to transition the agent system into a distributed, multi-tenant enterprise solution:

### 1️⃣ Distributed State & Memory Management (Redis Integration)
* **Current Limitation:** Confirmation tokens for two-phase tools are stored in local process memory (`PENDING_CONFIRMATIONS` dictionary).
* **Phase 2 Upgrade:** Migrate pending action tokens and session states to a **Redis cache** with Time-To-Live (TTL) expiration. This allows horizontal scaling across multiple application workers without losing confirmation states.

### 2️⃣ Enterprise Relational Backend (PostgreSQL Migration)
* **Current Limitation:** SQLite manages transactional concurrency via file-level locking, suitable for local validation.
* **Phase 2 Upgrade:** Transition to **PostgreSQL** with connection pooling to support concurrent write operations (e.g., simultaneous address updates and ticket creations by hundreds of active customer sessions).

### 3️⃣ Real-Time Human Support Dashboard (WebSockets / Flask-SocketIO)
* **Current Limitation:** Escalated tickets are stored in `support_tickets` and logged to the terminal console.
* **Phase 2 Upgrade:** Build a web-based GUI featuring a live chat widget for customers and a real-time ticketing dashboard for support reps, utilizing **WebSockets** for instant escalation alerts and live takeover.

### 4️⃣ Live Logistics Integration & Multimodal Processing
* **Current Limitation:** Logistics queries fetch mock shipment data from `shipments` table.
* **Phase 2 Upgrade:** Integrate native REST API webhooks for third-party carriers (e.g., Aramex, DHL) and implement multimodal OCR for customer invoice/receipt validation during return requests.

---

**Author:** Siraj Alwahidi  
**Course Instructors & TAs:** SPOCS AI Agents Course Team
