"""
Database Helper Module (database/db_helper.py)
----------------------------------------------
Provides direct interfaces with the database (Typed Tools) enforcing security layers:
1. IDOR protection by binding `customer_id` to all queries.
2. Read-only mode enforcement (`PRAGMA query_only = ON` & SQLite Authorizer).
3. Two-Phase Confirmation Protocol for state-modifying actions.
4. Automatic Arabic-to-English digit normalization.
"""

import sqlite3
import secrets
from pathlib import Path
from typing import Dict, Any, List, Optional

# Main Database Path
DB_PATH = Path(__file__).parent / "ecommerce.db" # Get the path to the database file (database/ecommerce.db)

# Temporary store for confirmation tokens (Two-Phase Confirmations)
PENDING_CONFIRMATIONS: Dict[str, Dict[str, Any]] = {}


# ==========================================
# 1. Input Utilities
# ==========================================

def normalize_digits(text: str) -> str:
    """
    Converts Arabic-Indic digits (٠١٢٣٤٥٦٧٨٩) to standard English digits (0123456789).
    """
    if not text:
        return ""
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    english_digits = "0123456789"
    translation_table = str.maketrans(arabic_digits, english_digits)
    return str(text).translate(translation_table)


# ==========================================
# 2. SQLite Security Engine
# ==========================================

def _sqlite_authorizer(action_code: int, arg1: Optional[str], arg2: Optional[str], 
                       db_name: Optional[str], trigger_name: Optional[str]) -> int:
    """
    SQLite authorizer callback to block unauthorized statements during read operations.
    """
    allowed_actions = {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
    }
    
    if action_code in allowed_actions:
        return sqlite3.SQLITE_OK
    
    return sqlite3.SQLITE_DENY


def get_read_connection() -> sqlite3.Connection:
    """
    Creates a secure read-only SQLite connection enforcing PRAGMA query_only and authorizer.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found at: {DB_PATH}")
        
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    
    conn.execute("PRAGMA query_only = ON;")
    conn.set_authorizer(_sqlite_authorizer)
    return conn


def get_write_connection() -> sqlite3.Connection:
    """
    Creates a database connection for authorized write operations.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found at: {DB_PATH}")
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================
# 3. Typed Reader Tools
# ==========================================

def get_order_status(customer_id: int, order_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Fetches the status of a specific order or recent orders for a customer.
    Protected against IDOR by enforcing customer_id in the query predicate.
    """
    customer_id = int(normalize_digits(str(customer_id)))
    if order_id is not None:
        order_id = int(normalize_digits(str(order_id)))

    with get_read_connection() as conn:
        cursor = conn.cursor()
        
        if order_id:
            query = """
                SELECT order_id, customer_id, order_date, status, total_amount, shipping_address
                FROM orders
                WHERE order_id = ? AND customer_id = ?
            """
            cursor.execute(query, (order_id, customer_id))
            order = cursor.fetchone()
            
            if not order:
                return {
                    "success": False, 
                    "error": f"Order #{order_id} not found or does not belong to this account."
                }
            
            return {
                "success": True,
                "data": dict(order)
            }
        else:
            query = """
                SELECT order_id, order_date, status, total_amount, shipping_address
                FROM orders
                WHERE customer_id = ?
                ORDER BY order_date DESC
                LIMIT 5
            """
            cursor.execute(query, (customer_id,))
            orders = [dict(row) for row in cursor.fetchall()]
            
            return {
                "success": True,
                "count": len(orders),
                "data": orders
            }


def track_shipment(customer_id: int, tracking_number: Optional[str] = None, order_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Tracks shipment status for an order.
    Verifies ownership by joining shipments with orders on customer_id.
    """
    customer_id = int(normalize_digits(str(customer_id)))
    
    with get_read_connection() as conn:
        cursor = conn.cursor()
        
        if tracking_number:
            tracking_number = normalize_digits(str(tracking_number)).strip()
            query = """
                SELECT s.tracking_number, s.order_id, s.carrier, s.current_location, 
                       s.estimated_delivery, s.status AS shipment_status
                FROM shipments s
                JOIN orders o ON s.order_id = o.order_id
                WHERE s.tracking_number = ? AND o.customer_id = ?
            """
            cursor.execute(query, (tracking_number, customer_id))
        elif order_id:
            order_id = int(normalize_digits(str(order_id)))
            query = """
                SELECT s.tracking_number, s.order_id, s.carrier, s.current_location, 
                       s.estimated_delivery, s.status AS shipment_status
                FROM shipments s
                JOIN orders o ON s.order_id = o.order_id
                WHERE s.order_id = ? AND o.customer_id = ?
            """
            cursor.execute(query, (order_id, customer_id))
        else:
            return {
                "success": False, 
                "error": "Please provide a tracking number or order ID."
            }

        shipment = cursor.fetchone()
        if not shipment:
            return {
                "success": False, 
                "error": "No matching shipment found or access unauthorized."
            }

        return {
            "success": True,
            "data": dict(shipment)
        }


# ==========================================
# 4. Two-Phase Writer Tools
# ==========================================

def cancel_order(customer_id: int, order_id: int, confirm_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Cancels an order via Two-Phase Confirmation Protocol.
    - Phase 1: Proposes cancellation and generates a confirmation token.
    - Phase 2: Executes actual cancellation upon valid token presentation with re-validation.
    """
    customer_id = int(normalize_digits(str(customer_id)))
    order_id = int(normalize_digits(str(order_id)))

    # Phase 2: Execution upon token validation
    if confirm_token:
        pending = PENDING_CONFIRMATIONS.get(confirm_token)
        if not pending or pending["action"] != "cancel_order" or pending["order_id"] != order_id or pending["customer_id"] != customer_id:
            return {
                "success": False,
                "error": "Confirmation token is invalid or expired. Please initiate cancellation again."
            }

        with get_write_connection() as conn:
            cursor = conn.cursor()
            
            # Re-check order status at commit time
            cursor.execute("SELECT status FROM orders WHERE order_id = ? AND customer_id = ?", (order_id, customer_id))
            row = cursor.fetchone()
            
            if not row:
                return {"success": False, "error": "Order not found or unauthorized."}
            if row["status"] in ["shipped", "delivered", "cancelled"]:
                return {"success": False, "error": f"Cannot cancel order in status: {row['status']}."}

            cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = ? AND customer_id = ?", (order_id, customer_id))
            conn.commit()

        del PENDING_CONFIRMATIONS[confirm_token]
        return {
            "success": True,
            "message": f"Order #{order_id} has been successfully cancelled."
        }

    # Phase 1: Proposal generation
    status_check = get_order_status(customer_id=customer_id, order_id=order_id)
    if not status_check["success"]:
        return status_check

    current_status = status_check["data"]["status"]
    if current_status in ["shipped", "delivered", "cancelled"]:
        return {
            "success": False,
            "error": f"Order #{order_id} cannot be cancelled because it is currently ({current_status})."
        }

    token = secrets.token_hex(4)
    PENDING_CONFIRMATIONS[token] = {
        "action": "cancel_order",
        "customer_id": customer_id,
        "order_id": order_id
    }

    return {
        "success": True,
        "requires_confirmation": True,
        "confirm_token": token,
        "proposal_message": f"Are you sure you want to cancel Order #{order_id}? To confirm, please provide the confirmation token ({token})."
    }


def update_shipping_address(customer_id: int, order_id: int, new_address: str, confirm_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Updates shipping address for a pending order via Two-Phase Protocol.
    """
    customer_id = int(normalize_digits(str(customer_id)))
    order_id = int(normalize_digits(str(order_id)))
    new_address = new_address.strip()

    if not new_address:
        return {"success": False, "error": "Please provide a valid new shipping address."}

    # Phase 2: Execution upon token validation
    if confirm_token:
        pending = PENDING_CONFIRMATIONS.get(confirm_token)
        if not pending or pending["action"] != "update_shipping_address" or pending["order_id"] != order_id or pending["customer_id"] != customer_id:
            return {
                "success": False,
                "error": "Confirmation token is invalid or expired."
            }

        with get_write_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT status FROM orders WHERE order_id = ? AND customer_id = ?", (order_id, customer_id))
            row = cursor.fetchone()
            
            if not row:
                return {"success": False, "error": "Order not found."}
            if row["status"] in ["shipped", "delivered", "cancelled"]:
                return {"success": False, "error": f"Cannot update address for order in status: {row['status']}."}

            cursor.execute(
                "UPDATE orders SET shipping_address = ? WHERE order_id = ? AND customer_id = ?",
                (pending["new_address"], order_id, customer_id)
            )
            conn.commit()

        del PENDING_CONFIRMATIONS[confirm_token]
        return {
            "success": True,
            "message": f"Shipping address for Order #{order_id} updated to: '{pending['new_address']}' successfully."
        }

    # Phase 1: Proposal generation
    status_check = get_order_status(customer_id=customer_id, order_id=order_id)
    if not status_check["success"]:
        return status_check

    current_status = status_check["data"]["status"]
    if current_status in ["shipped", "delivered", "cancelled"]:
        return {
            "success": False,
            "error": f"Cannot update shipping address because Order #{order_id} is currently ({current_status})."
        }

    token = secrets.token_hex(4)
    PENDING_CONFIRMATIONS[token] = {
        "action": "update_shipping_address",
        "customer_id": customer_id,
        "order_id": order_id,
        "new_address": new_address
    }

    return {
        "success": True,
        "requires_confirmation": True,
        "confirm_token": token,
        "proposal_message": f"Confirm updating shipping address for Order #{order_id} to: '{new_address}'? Please provide the confirmation token ({token})."
    }


# ==========================================
# 5. Human-in-the-Loop Support Tickets
# ==========================================

def create_support_ticket(customer_id: int, issue_description: str, order_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Creates a support ticket and escalates to a human agent when automated handling is insufficient.
    """
    customer_id = int(normalize_digits(str(customer_id)))
    if order_id:
        order_id = int(normalize_digits(str(order_id)))

    with get_write_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO support_tickets (customer_id, order_id, issue_description, status)
            VALUES (?, ?, ?, 'escalated_to_human')
            """,
            (customer_id, order_id, issue_description)
        )
        ticket_id = cursor.lastrowid
        conn.commit()

    return {
        "success": True,
        "ticket_id": ticket_id,
        "message": f"Support ticket #{ticket_id} created successfully. A human support agent will contact you regarding: '{issue_description}'."
    }