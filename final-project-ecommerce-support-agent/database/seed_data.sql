-- 1. Insert Sample Customers
INSERT INTO customers (name, email, phone) VALUES
('Ahmad Hassan', 'ahmad@example.com', '+970599123456'),
('Sara Ali', 'sara@example.com', '+970599654321'),
('Omar Khaled', 'omar@example.com', '+970599888777');

-- 2. Insert Sample Orders
INSERT INTO orders (customer_id, status, total_amount, shipping_address) VALUES
(1, 'pending', 250.50, 'Nablus, Main Street, Bldg 4'),
(1, 'delivered', 120.00, 'Nablus, Main Street, Bldg 4'),
(2, 'processing', 499.99, 'Ramallah, Al-Irsal St, Apt 12'),
(3, 'pending', 85.00, 'Hebron, Ein Sara, House 9');

-- 3. Insert Sample Shipments
INSERT INTO shipments (tracking_number, order_id, carrier, current_location, estimated_delivery, status) VALUES
('TRK-1001', 1, 'Aramex', 'Hub Central - Nablus', '2026-10-01', 'in_transit'),
('TRK-1002', 2, 'DHL', 'Delivered to Customer', '2026-09-25', 'delivered'),
('TRK-1003', 3, 'FedEx', 'Warehouse - Processing', '2026-10-03', 'label_created');

-- 4. Insert Sample Support Tickets
INSERT INTO support_tickets (order_id, customer_id, status, issue_description) VALUES
(1, 1, 'bot_active', 'Customer asking about current shipment location for order #1'),
(3, 2, 'escalated_to_human', 'Customer requested address change while order is processing');