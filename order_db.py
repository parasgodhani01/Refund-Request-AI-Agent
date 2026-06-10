"""
order_db.py
───────────
Simulated order database.  In production, replace lookup functions
with calls to your actual order management system / API.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

# ──────────────────────────────────────────────
# Mock Orders  (order_id → order details)
# ──────────────────────────────────────────────

today = date.today()

ORDERS: dict[str, dict] = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "customer_name": "Alice Johnson",
        "customer_email": "alice@example.com",
        "product": "Sony WH-1000XM5 Headphones",
        "category": "electronics",
        "price": 349.99,
        "purchase_date": today - timedelta(days=10),
        "status": "delivered",
        "membership": "premium",
        "opened": True,
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "customer_name": "Bob Martinez",
        "customer_email": "bob@example.com",
        "product": "Nike Running Shoes",
        "category": "clothing",
        "price": 129.99,
        "purchase_date": today - timedelta(days=45),
        "status": "delivered",
        "membership": "standard",
        "opened": True,
    },
    "ORD-1003": {
        "order_id": "ORD-1003",
        "customer_name": "Carol White",
        "customer_email": "carol@example.com",
        "product": "Adobe Photoshop License",
        "category": "software",
        "price": 54.99,
        "purchase_date": today - timedelta(days=5),
        "status": "delivered",
        "membership": "standard",
        "opened": True,
    },
    "ORD-1004": {
        "order_id": "ORD-1004",
        "customer_name": "David Kim",
        "customer_email": "david@example.com",
        "product": 'Dell XPS 15 Laptop',
        "category": "electronics",
        "price": 1499.99,
        "purchase_date": today - timedelta(days=3),
        "status": "delivered",
        "membership": "premium",
        "opened": False,
    },
    "ORD-1005": {
        "order_id": "ORD-1005",
        "customer_name": "Eva Chen",
        "customer_email": "eva@example.com",
        "product": "Custom Engraved Watch",
        "category": "personalized",
        "price": 250.00,
        "purchase_date": today - timedelta(days=7),
        "status": "delivered",
        "membership": "standard",
        "opened": True,
    },
    "ORD-1006": {
        "order_id": "ORD-1006",
        "customer_name": "Frank Lee",
        "customer_email": "frank@example.com",
        "product": "Samsung 4K Smart TV",
        "category": "electronics",
        "price": 799.99,
        "purchase_date": today - timedelta(days=2),
        "status": "delivered",
        "membership": "standard",
        "opened": True,
        "reported_defective": True,
    },
    "ORD-1007": {
        "order_id": "ORD-1007",
        "customer_name": "Grace Park",
        "customer_email": "grace@example.com",
        "product": "Winter Jacket",
        "category": "clothing",
        "price": 199.99,
        "purchase_date": today - timedelta(days=20),
        "status": "delivered",
        "membership": "premium",
        "opened": True,
        "tags_attached": True,
    },
}


def get_order(order_id: str) -> Optional[dict]:
    """Return order details or None if not found."""
    return ORDERS.get(order_id.upper())


def get_days_since_purchase(order_id: str) -> Optional[int]:
    order = get_order(order_id)
    if not order:
        return None
    return (date.today() - order["purchase_date"]).days


def list_sample_orders() -> list[str]:
    return list(ORDERS.keys())
