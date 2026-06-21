"""
knowledge_base.py
─────────────────
Builds a FAISS vector store loaded with refund policies, product categories,
and FAQ documents.  The retriever is used by the LangGraph agent to ground
every decision in company policy.
"""

from __future__ import annotations

import os
from typing import List

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

POLICY_DOCUMENTS: List[dict] = [
    # ── General Return Policy ─────────────────
    {
        "content": (
            "Standard Return Policy: Customers may return most items within 30 days "
            "of purchase for a full refund. Items must be unused, in original packaging, "
            "and accompanied by proof of purchase. Refunds are processed within 5-7 "
            "business days to the original payment method."
        ),
        "metadata": {"category": "general", "policy_id": "POL-001"},
    },
    {
        "content": (
            "Extended Return Window: Premium members are eligible for a 60-day return "
            "window on all purchases. Standard members receive the default 30-day window. "
            "Holiday purchases made between November 1 and December 31 may be returned "
            "until January 31 of the following year."
        ),
        "metadata": {"category": "general", "policy_id": "POL-002"},
    },
    # ── Electronics ───────────────────────────
    {
        "content": (
            "Electronics Return Policy: Electronics may be returned within 15 days of "
            "purchase if unopened. Opened electronics have a 15-day return window but "
            "are subject to a 15% restocking fee. Defective electronics are eligible "
            "for a full refund or exchange within 30 days regardless of opened status. "
            "Software, digital downloads, and activated gift cards are non-refundable."
        ),
        "metadata": {"category": "electronics", "policy_id": "POL-003"},
    },
    {
        "content": (
            "Laptop & Computer Returns: Laptops and desktop computers must be returned "
            "within 15 days. If the device has been opened, a diagnostic fee of $25 "
            "applies. All personal data should be wiped before return. Factory reset "
            "must be performed by the customer prior to sending back."
        ),
        "metadata": {"category": "electronics", "policy_id": "POL-004"},
    },
    # ── Clothing & Apparel ────────────────────
    {
        "content": (
            "Clothing Return Policy: Clothing items may be returned within 30 days with "
            "tags attached and unworn. Swimwear, underwear, and pierced jewelry are "
            "final sale and cannot be returned for hygiene reasons. Sale items marked "
            "'Final Sale' are not eligible for returns or exchanges."
        ),
        "metadata": {"category": "clothing", "policy_id": "POL-005"},
    },
    # ── Damaged / Defective Items ─────────────
    {
        "content": (
            "Damaged or Defective Items: If you received a damaged, defective, or "
            "incorrect item, you are eligible for a full refund or replacement at no "
            "cost within 90 days of purchase. Please provide photographic evidence of "
            "the damage when submitting your refund request. Return shipping is "
            "prepaid by the company for damaged/defective items."
        ),
        "metadata": {"category": "damaged", "policy_id": "POL-006"},
    },
    # ── Non-Refundable Items ──────────────────
    {
        "content": (
            "Non-Refundable Items: The following items cannot be returned or refunded: "
            "digital downloads, software licenses, perishable goods, customized/personalized "
            "items, hazardous materials, live plants, gift cards (once activated), "
            "downloadable software, and items marked as 'Final Sale' at time of purchase."
        ),
        "metadata": {"category": "non-refundable", "policy_id": "POL-007"},
    },
    # ── Refund Methods ────────────────────────
    {
        "content": (
            "Refund Methods: Refunds are issued to the original payment method. Credit "
            "card refunds take 5-7 business days. PayPal refunds take 3-5 business days. "
            "Store credit is available immediately as an alternative. Customers may "
            "choose store credit to receive 110% of the item's value (a 10% bonus). "
            "Cash refunds are only available for cash purchases made in-store."
        ),
        "metadata": {"category": "refund_methods", "policy_id": "POL-008"},
    },
    # ── Escalation Policy ────────────────────
    {
        "content": (
            "Escalation & Special Circumstances: Refund requests outside the standard "
            "window or for non-refundable items may be escalated to the Customer "
            "Experience team for review. Medical emergencies, natural disasters, or "
            "documented extenuating circumstances may qualify for exception approvals. "
            "Escalations are reviewed within 2-3 business days. Customers with VIP "
            "or loyalty status receive priority escalation handling within 24 hours."
        ),
        "metadata": {"category": "escalation", "policy_id": "POL-009"},
    },
    # ── Partial Refunds ───────────────────────
    {
        "content": (
            "Partial Refunds: Partial refunds may be issued when: items are returned "
            "without original packaging (20% deduction), items show signs of use beyond "
            "inspection (up to 50% deduction), bundled items are returned partially "
            "(refund for returned items minus bundle discount), or items are returned "
            "outside the standard window but within 60 days (10% late-return fee)."
        ),
        "metadata": {"category": "partial_refunds", "policy_id": "POL-010"},
    },
]


FAISS_INDEX_PATH = "faiss_refund_index"


def build_knowledge_base(openai_api_key: str | None = None) -> FAISS:
    """
    Create a FAISS vector store from the policy documents.
    Pass openai_api_key or set OPENAI_API_KEY env variable.
    """
    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)

    documents = [
        Document(page_content=doc["content"], metadata=doc["metadata"])
        for doc in POLICY_DOCUMENTS
    ]

    vector_store = FAISS.from_documents(documents, embeddings)
    vector_store.save_local(FAISS_INDEX_PATH)
    print(f"FAISS index built with {len(documents)} policy documents.")
    return vector_store


def load_knowledge_base(openai_api_key: str | None = None) -> FAISS:
    """Load existing FAISS index or build a new one."""
    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)

    if os.path.exists(FAISS_INDEX_PATH):
        vector_store = FAISS.load_local(
            FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True
        )
        print("FAISS index loaded from disk.")
    else:
        vector_store = build_knowledge_base(api_key)

    return vector_store


def get_retriever(openai_api_key: str | None = None, k: int = 3):
    """Return a LangChain retriever backed by FAISS."""
    vector_store = load_knowledge_base(openai_api_key)
    return vector_store.as_retriever(search_type="similarity", search_kwargs={"k": k})


if __name__ == "__main__":
    build_knowledge_base()
