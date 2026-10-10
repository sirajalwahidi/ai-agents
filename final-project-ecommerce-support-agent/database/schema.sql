-- Disable foreign keys temporarily for clean setup
PRAGMA foreign_keys = OFF;

-- Drop existing tables if re-initializing
DROP TABLE IF EXISTS support_tickets;
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

-- Re-enable Foreign Key enforcement
PRAGMA foreign_keys = ON;

-- 1. Customers Table
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT NOT NULL
);

-- 2. Orders Table
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK(status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')) NOT NULL,
    total_amount REAL NOT NULL,
    shipping_address TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- 3. Shipments Table
CREATE TABLE shipments (
    shipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_number TEXT UNIQUE NOT NULL,
    order_id INTEGER NOT NULL,
    carrier TEXT NOT NULL,
    current_location TEXT NOT NULL,
    estimated_delivery DATE NOT NULL,
    status TEXT CHECK(status IN ('label_created', 'in_transit', 'out_for_delivery', 'delivered', 'delayed', 'returned')) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

-- 4. Support Tickets Table (Human-In-The-Loop Escalation)
CREATE TABLE support_tickets (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    status TEXT CHECK(status IN ('bot_active', 'escalated_to_human', 'resolved')) NOT NULL DEFAULT 'bot_active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    issue_description TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);