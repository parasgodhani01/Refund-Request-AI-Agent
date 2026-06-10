"""
refund_agent.py
───────────────
LangGraph-powered Refund Request AI Agent

Graph Flow:
  START
    │
    ▼
  extract_info          ← Parse order ID & reason from user message
    │
    ▼
  validate_order        ← Look up order in database
    │
    ├─ not_found ──────► respond (order not found)
    │
    ▼
  retrieve_policy       ← FAISS similarity search for relevant policies
    │
    ▼
  evaluate_eligibility  ← LLM decides: APPROVE / DENY / ESCALATE / PARTIAL
    │
    ├─ escalate ───────► escalate_handler
    │
    ▼
  generate_response     ← Draft final customer-facing response
    │
    ▼
  END
"""

from __future__ import annotations

import json
import os
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from knowledge_base import get_retriever
from order_db import get_days_since_purchase, get_order

# ──────────────────────────────────────────────
# State Definition
# ──────────────────────────────────────────────


class RefundState(TypedDict):
    # Conversation history
    messages: Annotated[list, add_messages]

    # Extracted from user message
    order_id: str | None
    refund_reason: str | None
    user_message: str

    # Order details
    order_details: dict | None
    days_since_purchase: int | None

    # Policy retrieval
    relevant_policies: str | None

    # Decision
    decision: Literal["APPROVE", "DENY", "ESCALATE", "PARTIAL", "NOT_FOUND", "PENDING"]
    decision_reasoning: str | None
    refund_amount: float | None

    # Final response
    final_response: str | None
    requires_escalation: bool


# ──────────────────────────────────────────────
# Node Implementations
# ──────────────────────────────────────────────


def build_llm(api_key: str | None = None) -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        openai_api_key=api_key or os.getenv("OPENAI_API_KEY"),
    )


# ── Node 1: Extract Order Info ─────────────────


def extract_info(state: RefundState) -> RefundState:
    """
    Use LLM to extract the order ID and refund reason from the user's message.
    """
    llm = build_llm()
    user_msg = state["user_message"]

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content=(
                    "You are a helpful assistant that extracts structured information "
                    "from customer refund requests. Extract the order ID (format: ORD-XXXX) "
                    "and the main reason for the refund request. "
                    "Respond ONLY with a JSON object: "
                    '{"order_id": "ORD-XXXX or null", "refund_reason": "brief reason"}'
                )
            ),
            HumanMessage(content=user_msg),
        ]
    )

    response = llm.invoke(prompt.format_messages())
    try:
        # Strip markdown fences if present
        raw = response.content.strip().strip("```json").strip("```").strip()
        extracted = json.loads(raw)
        order_id = extracted.get("order_id")
        refund_reason = extracted.get("refund_reason", "Not specified")
    except Exception:
        order_id = None
        refund_reason = "Could not parse reason"

    return {
        **state,
        "order_id": order_id,
        "refund_reason": refund_reason,
        "messages": state["messages"] + [HumanMessage(content=user_msg)],
    }


# ── Node 2: Validate Order ─────────────────────


def validate_order(state: RefundState) -> RefundState:
    """Look up the order in our database."""
    order_id = state.get("order_id")

    if not order_id:
        return {**state, "order_details": None, "decision": "NOT_FOUND"}

    order = get_order(order_id)
    if not order:
        return {**state, "order_details": None, "decision": "NOT_FOUND"}

    days = get_days_since_purchase(order_id)
    return {
        **state,
        "order_details": order,
        "days_since_purchase": days,
        "decision": "PENDING",
    }


# ── Node 3: Retrieve Relevant Policies ────────


def retrieve_policy(state: RefundState) -> RefundState:
    """Query FAISS for policies relevant to this refund request."""
    order = state.get("order_details", {}) or {}
    reason = state.get("refund_reason", "")
    category = order.get("category", "general")

    query = f"Refund policy for {category} product. Reason: {reason}"

    try:
        retriever = get_retriever()
        docs = retriever.invoke(query)
        policy_text = "\n\n".join(
            [f"[{d.metadata.get('policy_id', 'N/A')}] {d.page_content}" for d in docs]
        )
    except Exception as e:
        policy_text = f"Policy retrieval failed: {e}. Apply standard 30-day return policy."

    return {**state, "relevant_policies": policy_text}


# ── Node 4: Evaluate Eligibility ──────────────


def evaluate_eligibility(state: RefundState) -> RefundState:
    """
    Core decision engine — LLM + retrieved policies determine the outcome.
    """
    llm = build_llm()
    order = state["order_details"]
    days = state["days_since_purchase"]
    policies = state["relevant_policies"]
    reason = state["refund_reason"]

    system_prompt = f"""You are a Refund Eligibility Specialist. Analyze the refund request 
against company policies and make a fair, accurate decision.

RETRIEVED POLICIES:
{policies}

ORDER DETAILS:
- Order ID: {order['order_id']}
- Product: {order['product']}
- Category: {order['category']}
- Purchase Price: ${order['price']:.2f}
- Days Since Purchase: {days}
- Membership Level: {order['membership']}
- Item Opened: {order.get('opened', False)}
- Reported Defective: {order.get('reported_defective', False)}
- Tags Attached: {order.get('tags_attached', 'N/A')}

CUSTOMER REFUND REASON: {reason}

Make ONE of these decisions:
- APPROVE: Full refund is warranted
- PARTIAL: Partial refund with deduction (specify amount)
- DENY: Request does not meet policy requirements
- ESCALATE: Unusual case requiring human review

Respond ONLY with JSON:
{{
  "decision": "APPROVE|PARTIAL|DENY|ESCALATE",
  "refund_amount": <float or null>,
  "reasoning": "<clear explanation referencing specific policies>"
}}"""

    response = llm.invoke([SystemMessage(content=system_prompt)])
    try:
        raw = response.content.strip().strip("```json").strip("```").strip()
        result = json.loads(raw)
        decision = result.get("decision", "ESCALATE")
        reasoning = result.get("reasoning", "")
        refund_amount = result.get("refund_amount")
    except Exception:
        decision = "ESCALATE"
        reasoning = "Could not evaluate automatically."
        refund_amount = None

    return {
        **state,
        "decision": decision,
        "decision_reasoning": reasoning,
        "refund_amount": refund_amount,
        "requires_escalation": decision == "ESCALATE",
    }


# ── Node 5: Escalation Handler ─────────────────


def escalate_handler(state: RefundState) -> RefundState:
    """Handle escalated cases — generates escalation confirmation."""
    llm = build_llm()
    order = state["order_details"]

    prompt = f"""Write a professional, empathetic customer service message explaining that 
the refund request for order {order['order_id']} ({order['product']}) has been escalated 
to the Customer Experience team for review. 

Reasoning: {state.get('decision_reasoning', 'Requires specialist review')}

Key points to include:
- Acknowledge the customer's request
- Explain it's been escalated for specialist review
- Provide a timeline (2-3 business days, 24 hours for premium members)
- Membership: {order.get('membership', 'standard')}
- Offer a ticket/case number format: ESC-{order['order_id'][-4:]}
- Warm, professional tone"""

    response = llm.invoke([HumanMessage(content=prompt)])
    return {**state, "final_response": response.content}


# ── Node 6: Generate Response ─────────────────


def generate_response(state: RefundState) -> RefundState:
    """Draft the final customer-facing response."""
    llm = build_llm()
    decision = state["decision"]
    order = state.get("order_details") or {}
    reasoning = state.get("decision_reasoning", "")
    refund_amount = state.get("refund_amount")

    if decision == "NOT_FOUND":
        response = (
            f"I'm sorry, but I couldn't locate an order with ID **{state.get('order_id', 'unknown')}** "
            "in our system. Please double-check your order ID (format: ORD-XXXX) and try again. "
            "You can find your order ID in your confirmation email or account order history."
        )
    else:
        amount_str = ""
        if refund_amount is not None:
            amount_str = f" of **${refund_amount:.2f}**"
        elif decision == "APPROVE":
            amount_str = f" of **${order.get('price', 0):.2f}**"

        prompt = f"""Write a professional, friendly customer service response for a refund request.

Decision: {decision}
Order: {order.get('order_id')} — {order.get('product')}
Refund Amount: {f'${refund_amount:.2f}' if refund_amount else ('Full: $' + str(order.get('price', 0))) if decision == 'APPROVE' else 'N/A'}
Reasoning: {reasoning}
Customer Membership: {order.get('membership', 'standard')}

Guidelines:
- Be empathetic and professional
- Clearly state the decision upfront
- Explain the reason briefly
- For APPROVE: mention 5-7 day processing time (3-5 days for PayPal)
- For PARTIAL: specify the amount and why a deduction applies
- For DENY: be compassionate, reference the specific policy, suggest alternatives if any
- End with an offer to help further"""

        response_msg = llm.invoke([HumanMessage(content=prompt)])
        response = response_msg.content

    return {
        **state,
        "final_response": response,
        "messages": state["messages"] + [AIMessage(content=response)],
    }


# ──────────────────────────────────────────────
# Routing Functions
# ──────────────────────────────────────────────


def route_after_validation(state: RefundState) -> str:
    if state.get("decision") == "NOT_FOUND":
        return "generate_response"
    return "retrieve_policy"


def route_after_evaluation(state: RefundState) -> str:
    if state.get("decision") == "ESCALATE":
        return "escalate_handler"
    return "generate_response"


# ──────────────────────────────────────────────
# Build the LangGraph
# ──────────────────────────────────────────────


def build_refund_graph() -> StateGraph:
    graph = StateGraph(RefundState)

    # Add nodes
    graph.add_node("extract_info", extract_info)
    graph.add_node("validate_order", validate_order)
    graph.add_node("retrieve_policy", retrieve_policy)
    graph.add_node("evaluate_eligibility", evaluate_eligibility)
    graph.add_node("escalate_handler", escalate_handler)
    graph.add_node("generate_response", generate_response)

    # Add edges
    graph.add_edge(START, "extract_info")
    graph.add_edge("extract_info", "validate_order")
    graph.add_conditional_edges(
        "validate_order",
        route_after_validation,
        {
            "generate_response": "generate_response",
            "retrieve_policy": "retrieve_policy",
        },
    )
    graph.add_edge("retrieve_policy", "evaluate_eligibility")
    graph.add_conditional_edges(
        "evaluate_eligibility",
        route_after_evaluation,
        {
            "escalate_handler": "escalate_handler",
            "generate_response": "generate_response",
        },
    )
    graph.add_edge("escalate_handler", END)
    graph.add_edge("generate_response", END)

    return graph.compile()


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────


def process_refund_request(user_message: str) -> dict:
    """
    Process a refund request and return the full state.

    Args:
        user_message: Natural language refund request from the customer

    Returns:
        dict with keys: decision, final_response, order_details, refund_amount, etc.
    """
    app = build_refund_graph()

    initial_state: RefundState = {
        "messages": [],
        "order_id": None,
        "refund_reason": None,
        "user_message": user_message,
        "order_details": None,
        "days_since_purchase": None,
        "relevant_policies": None,
        "decision": "PENDING",
        "decision_reasoning": None,
        "refund_amount": None,
        "final_response": None,
        "requires_escalation": False,
    }

    result = app.invoke(initial_state)
    return result


if __name__ == "__main__":
    # Quick smoke test
    test_message = "I'd like to return my order ORD-1006. The TV I received is defective."
    result = process_refund_request(test_message)
    print(f"\n{'='*60}")
    print(f"Decision: {result['decision']}")
    print(f"\nResponse:\n{result['final_response']}")
