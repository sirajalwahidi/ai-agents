import os
import sys
import io
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Set output encoding to UTF-8 to handle all characters properly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Import secured database helper tools
from database.db_helper import (
    get_order_status,
    track_shipment,
    cancel_order,
    update_shipping_address,
    create_support_ticket,
)

# 1. Load API key from environment variables (.env)
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in .env file.")
    print("Please set your GEMINI_API_KEY inside the .env file.")
    sys.exit(1)

# Initialize Gemini API client
client = genai.Client(api_key=api_key)

# 2. Simulate authenticated customer session context
# Binding customer ID directly to session prevents IDOR vulnerabilities
CURRENT_CUSTOMER_ID = 1  # Customer ID #1: Ahmad Hassan


# 3. Session-bound tool wrappers
def check_order_status(order_id: Optional[int] = None) -> dict:
    """Fetches order status for the currently authenticated customer."""
    return get_order_status(customer_id=CURRENT_CUSTOMER_ID, order_id=order_id)

def track_order_shipment(tracking_number: Optional[str] = None, order_id: Optional[int] = None) -> dict:
    """Tracks shipment details for an order belonging to the current customer."""
    return track_shipment(customer_id=CURRENT_CUSTOMER_ID, tracking_number=tracking_number, order_id=order_id)

def request_order_cancellation(order_id: int, confirm_token: Optional[str] = None) -> dict:
    """Proposes or executes order cancellation using the Two-Phase protocol."""
    return cancel_order(customer_id=CURRENT_CUSTOMER_ID, order_id=order_id, confirm_token=confirm_token)

def request_address_update(order_id: int, new_address: str, confirm_token: Optional[str] = None) -> dict:
    """Proposes or executes a shipping address update using the Two-Phase protocol."""
    return update_shipping_address(customer_id=CURRENT_CUSTOMER_ID, order_id=order_id, new_address=new_address, confirm_token=confirm_token)

def escalate_to_human_agent(issue_description: str, order_id: Optional[int] = None) -> dict:
    """Escalates an issue by creating a support ticket for a human agent."""
    return create_support_ticket(customer_id=CURRENT_CUSTOMER_ID, issue_description=issue_description, order_id=order_id)


# 4. System Instructions & Guardrails
SYSTEM_INSTRUCTION = """
You are the Orchestrator Support Agent for a Smart E-Commerce platform.
Your objective is to provide fast, precise, and secure customer support strictly grounded in data returned by your available tools.

Strict Operating Rules & Security Guardrails:
1. Always rely ONLY on data returned by tool calls. Never make up or assume order details, delivery dates, tracking codes, or status updates (Zero Hallucination).
2. For order status or shipment tracking inquiries, use `check_order_status` or `track_order_shipment`.
3. State-modifying actions (cancellation or address updates):
   - Phase 1: Call `request_order_cancellation` or `request_address_update` without a `confirm_token`.
   - Present the tool's proposal message and the generated `confirm_token` to the user, asking for confirmation.
   - Phase 2: ONLY when the user explicitly provides the confirmation token, invoke the tool again passing the `confirm_token`.
4. Escalation: If the customer requests human support, expresses frustration, or presents complex/unsupported claims, invoke `escalate_to_human_agent`.
5. Respond professionally, clearly, and concisely in English.
"""

def run_support_agent():
    print("=" * 70)
    print("🤖 Smart E-Commerce Support Agent (Orchestrator Mode Enabled)")
    print(f"👤 Authenticated Session: Customer ID #{CURRENT_CUSTOMER_ID} (Ahmad Hassan)")
    print("Type your inquiry below (Type 'exit' or 'quit' to end session)")
    print("=" * 70)

    # Initialize chat session with model and registered tools
    chat = client.chats.create(
        model="gemini-3.8-flash", #this is the model that is used for the support agent 
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[
                check_order_status,
                track_order_shipment,
                request_order_cancellation,
                request_address_update,
                escalate_to_human_agent
            ],
            temperature=0.2,
        )
    )

    while True:
        try:
            user_input = input("\n👤 Customer: ").strip()
            if user_input.lower() in ['exit', 'quit']:
                print("\n👋 Thank you for reaching out to Smart E-Commerce Support. Have a great day!")
                break

            if not user_input:
                continue

            response = chat.send_message(user_input)
            print(f"\n🤖 Agent: {response.text}")

        except Exception as e:
            print(f"\n⚠️ Error during processing: {e}")

if __name__ == "__main__":
    run_support_agent()