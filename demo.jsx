import { useState, useEffect } from "react";

const ORDERS = {
  "ORD-1001": { product: "Sony WH-1000XM5 Headphones", category: "electronics", price: 349.99, days: 10, membership: "premium", opened: true, defective: false },
  "ORD-1002": { product: "Nike Running Shoes", category: "clothing", price: 129.99, days: 45, membership: "standard", opened: true, defective: false },
  "ORD-1003": { product: "Adobe Photoshop License", category: "software", price: 54.99, days: 5, membership: "standard", opened: true, defective: false },
  "ORD-1004": { product: "Dell XPS 15 Laptop", category: "electronics", price: 1499.99, days: 3, membership: "premium", opened: false, defective: false },
  "ORD-1005": { product: "Custom Engraved Watch", category: "personalized", price: 250.00, days: 7, membership: "standard", opened: true, defective: false },
  "ORD-1006": { product: "Samsung 4K Smart TV", category: "electronics", price: 799.99, days: 2, membership: "standard", opened: true, defective: true },
  "ORD-1007": { product: "Winter Jacket", category: "clothing", price: 199.99, days: 20, membership: "premium", opened: true, defective: false },
};

const NON_REFUNDABLE = ["software", "personalized"];
const ELECTRONICS_WINDOW = 15;
const STANDARD_WINDOW = 30;
const PREMIUM_WINDOW = 60;

function simulateAgent(orderIdRaw, reason) {
  const orderId = orderIdRaw.trim().toUpperCase();
  const order = ORDERS[orderId];
  
  const steps = [];
  
  // Node 1: Extract
  steps.push({ node: "extract_info", status: "done", detail: `Extracted Order ID: ${orderId || "not found"} · Reason: "${reason || 'not specified'}"` });
  
  if (!order) {
    steps.push({ node: "validate_order", status: "error", detail: "Order not found in database." });
    return { steps, decision: "NOT_FOUND", response: `I couldn't locate order **${orderId}** in our system. Please check your order ID (format: ORD-XXXX) in your confirmation email and try again.`, refundAmount: null, order: null };
  }

  // Node 2: Validate
  steps.push({ node: "validate_order", status: "done", detail: `Found: ${order.product} · $${order.price} · ${order.days} days ago · ${order.membership} member` });
  
  // Node 3: FAISS Retrieve
  const policies = [];
  if (order.defective) policies.push("POL-006: Defective items → full refund within 90 days");
  if (order.category === "electronics") policies.push("POL-003: Electronics → 15-day opened return (15% restocking fee)");
  if (order.category === "clothing") policies.push("POL-005: Clothing → 30-day return, tags required");
  if (NON_REFUNDABLE.includes(order.category)) policies.push("POL-007: Non-refundable categories");
  policies.push(order.membership === "premium" ? "POL-002: Premium members → 60-day window" : "POL-001: Standard → 30-day window");
  policies.push("POL-008: Refund methods & processing times");
  steps.push({ node: "retrieve_policy", status: "done", detail: `Retrieved ${policies.length} relevant policies via FAISS:\n${policies.join("\n")}` });
  
  // Node 4: Evaluate
  const window = order.membership === "premium" ? PREMIUM_WINDOW : STANDARD_WINDOW;
  let decision, refundAmount, reasoning;
  
  if (NON_REFUNDABLE.includes(order.category)) {
    decision = "DENY";
    refundAmount = 0;
    reasoning = `${order.category === "software" ? "Software licenses" : "Personalized items"} are non-refundable per POL-007.`;
  } else if (order.defective) {
    decision = "APPROVE";
    refundAmount = order.price;
    reasoning = "Defective item qualifies for full refund within 90-day window per POL-006.";
  } else if (order.days > window) {
    if (order.days <= 60 && order.membership !== "premium") {
      decision = "PARTIAL";
      refundAmount = +(order.price * 0.90).toFixed(2);
      reasoning = `Return is outside the 30-day window but within 60 days. 10% late-return fee applied per POL-010.`;
    } else {
      decision = "DENY";
      refundAmount = 0;
      reasoning = `Return window of ${window} days has expired (${order.days} days since purchase).`;
    }
  } else if (order.category === "electronics" && order.opened && order.days > ELECTRONICS_WINDOW) {
    decision = "PARTIAL";
    refundAmount = +(order.price * 0.85).toFixed(2);
    reasoning = "Opened electronics returned after 15-day window. 15% restocking fee applied per POL-003.";
  } else if (order.category === "electronics" && order.opened) {
    decision = "PARTIAL";
    refundAmount = +(order.price * 0.85).toFixed(2);
    reasoning = "Opened electronics subject to 15% restocking fee per POL-003.";
  } else {
    decision = "APPROVE";
    refundAmount = order.price;
    reasoning = `Item meets all return requirements: within ${window}-day window (${order.days} days), eligible category, ${order.opened ? "" : "unopened, "}${order.membership} member.`;
  }
  
  steps.push({ node: "evaluate_eligibility", status: "done", detail: reasoning });
  
  // Node 5: Generate Response
  let response;
  if (decision === "APPROVE") {
    response = `Great news! Your refund request for **${order.product}** (${orderId}) has been **approved**.\n\nA full refund of **$${refundAmount.toFixed(2)}** will be processed to your original payment method within 5-7 business days.\n\n${reasoning}`;
  } else if (decision === "PARTIAL") {
    response = `We've reviewed your refund request for **${order.product}** (${orderId}).\n\nA **partial refund of $${refundAmount.toFixed(2)}** has been approved. ${reasoning}\n\nThe refund will be processed within 5-7 business days.`;
  } else {
    response = `Thank you for reaching out about order ${orderId} (**${order.product}**).\n\nUnfortunately, we're unable to process a refund at this time. ${reasoning}\n\nIf you have further questions, our customer support team is happy to help!`;
  }
  steps.push({ node: "generate_response", status: "done", detail: "Response drafted and sent to customer." });
  
  return { steps, decision, response, refundAmount, order, orderId };
}

const NODES = ["extract_info", "validate_order", "retrieve_policy", "evaluate_eligibility", "generate_response"];
const NODE_LABELS = {
  extract_info: "Extract Info",
  validate_order: "Validate Order",
  retrieve_policy: "Retrieve Policy\n(FAISS)",
  evaluate_eligibility: "Evaluate\nEligibility",
  generate_response: "Generate\nResponse",
  escalate_handler: "Escalate\nHandler",
};

const DECISION_STYLES = {
  APPROVE:    { bg: "#052e16", border: "#16a34a", text: "#4ade80", label: "✅ APPROVED" },
  PARTIAL:    { bg: "#1c1008", border: "#d97706", text: "#fbbf24", label: "⚡ PARTIAL REFUND" },
  DENY:       { bg: "#1c0505", border: "#dc2626", text: "#f87171", label: "❌ DENIED" },
  ESCALATE:   { bg: "#0c1a2e", border: "#3b82f6", text: "#60a5fa", label: "🔁 ESCALATED" },
  NOT_FOUND:  { bg: "#111827", border: "#4b5563", text: "#9ca3af", label: "🔍 NOT FOUND" },
};

export default function RefundAgentDemo() {
  const [userMessage, setUserMessage] = useState("");
  const [result, setResult] = useState(null);
  const [animStep, setAnimStep] = useState(-1);
  const [isRunning, setIsRunning] = useState(false);
  const [activeStep, setActiveStep] = useState(null);

  const sampleCases = [
    { label: "Defective TV", msg: "My Samsung TV (ORD-1006) stopped working on day one — it's completely defective!" },
    { label: "Software License", msg: "I need a refund for the Adobe license I bought, order ORD-1003." },
    { label: "Shoes (45 days)", msg: "I'd like to return my Nike shoes, order ORD-1002. They don't fit right." },
    { label: "Unopened Laptop", msg: "Please refund my Dell laptop order ORD-1004, I haven't opened it." },
    { label: "Custom Watch", msg: "I want to return my custom watch from order ORD-1005." },
    { label: "Invalid Order", msg: "I want a refund for order ORD-9999." },
  ];

  const handleSubmit = () => {
    if (!userMessage.trim()) return;
    setResult(null);
    setAnimStep(-1);
    setIsRunning(true);
    setActiveStep(null);

    // Extract order ID from message
    const match = userMessage.match(/ORD-\d+/i);
    const orderId = match ? match[0] : "ORD-0000";
    const computed = simulateAgent(orderId, userMessage);
    
    // Animate through steps
    computed.steps.forEach((_, i) => {
      setTimeout(() => {
        setAnimStep(i);
        if (i === computed.steps.length - 1) {
          setTimeout(() => {
            setResult(computed);
            setIsRunning(false);
          }, 400);
        }
      }, i * 700);
    });
  };

  const ds = result ? DECISION_STYLES[result.decision] || DECISION_STYLES.NOT_FOUND : null;

  return (
    <div style={{ fontFamily: "'DM Sans', 'Segoe UI', sans-serif", background: "#0a0e1a", minHeight: "100vh", color: "#e2e8f0", padding: "24px" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; }
        textarea { resize: none; }
        button { cursor: pointer; transition: all 0.15s; }
        button:hover { filter: brightness(1.1); }
        .node-active { animation: pulse 0.6s ease-in-out; }
        @keyframes pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.04)} }
        .slide-in { animation: slideIn 0.35s ease-out; }
        @keyframes slideIn { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0a0e1a; }
        ::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 3px; }
      `}</style>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: "#f1f5f9" }}>
          ↩️ Refund Request AI Agent
        </h1>
        <p style={{ margin: "4px 0 0", fontSize: 13, color: "#64748b" }}>
          LangGraph · FAISS Policy Retrieval · GPT-4o-mini
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, maxWidth: 1100 }}>
        {/* LEFT PANEL */}
        <div>
          {/* Input */}
          <div style={{ background: "#111827", border: "1px solid #1e293b", borderRadius: 12, padding: 16, marginBottom: 16 }}>
            <p style={{ margin: "0 0 10px", fontSize: 12, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#64748b" }}>Customer Request</p>
            <textarea
              value={userMessage}
              onChange={e => setUserMessage(e.target.value)}
              onKeyDown={e => e.key === "Enter" && e.ctrlKey && handleSubmit()}
              placeholder="E.g., I'd like to return my Sony headphones, order ORD-1001..."
              rows={3}
              style={{ width: "100%", background: "#0d1117", border: "1px solid #1e293b", borderRadius: 8, color: "#e2e8f0", padding: "10px 12px", fontSize: 14, outline: "none", fontFamily: "inherit" }}
            />
            <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
              {sampleCases.map(s => (
                <button key={s.label} onClick={() => setUserMessage(s.msg)}
                  style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 6, color: "#94a3b8", fontSize: 11, padding: "4px 10px" }}>
                  {s.label}
                </button>
              ))}
            </div>
            <button onClick={handleSubmit} disabled={isRunning}
              style={{ marginTop: 12, width: "100%", background: isRunning ? "#1e3a5f" : "linear-gradient(135deg, #2563eb, #1d4ed8)", border: "none", borderRadius: 8, color: "#fff", fontWeight: 600, fontSize: 14, padding: "10px 0", fontFamily: "inherit" }}>
              {isRunning ? "⟳ Processing..." : "🚀 Submit Request"}
            </button>
          </div>

          {/* Agent Graph */}
          <div style={{ background: "#111827", border: "1px solid #1e293b", borderRadius: 12, padding: 16 }}>
            <p style={{ margin: "0 0 14px", fontSize: 12, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#64748b" }}>Agent Graph</p>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 0 }}>
              <div style={{ fontSize: 11, color: "#475569", marginBottom: 4 }}>START</div>
              {NODES.map((node, i) => {
                const stepData = result?.steps.find(s => s.node === node);
                const isActive = animStep >= 0 && result?.steps[animStep]?.node === node;
                const isDone = result && result.steps.findIndex(s => s.node === node) <= animStep;
                const isCurrentAnim = !result && animStep === i;
                
                let borderColor = "#1e293b";
                let bgColor = "#0d1117";
                let textColor = "#475569";
                if (isActive || isCurrentAnim) { borderColor = "#3b82f6"; bgColor = "#0c1a2e"; textColor = "#60a5fa"; }
                else if (isDone) { borderColor = "#16a34a"; bgColor = "#052e16"; textColor = "#4ade80"; }

                return (
                  <div key={node} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <div style={{ width: 2, height: 14, background: isDone ? "#16a34a" : "#1e293b" }} />
                    <div className={isActive || isCurrentAnim ? "node-active" : ""}
                      style={{ background: bgColor, border: `2px solid ${borderColor}`, borderRadius: 8, padding: "8px 20px", textAlign: "center", minWidth: 140, cursor: "pointer", transition: "all 0.3s" }}
                      onClick={() => setActiveStep(stepData || null)}>
                      <div style={{ fontSize: 11, fontFamily: "'DM Mono', monospace", color: textColor, fontWeight: 500, whiteSpace: "pre" }}>
                        {NODE_LABELS[node]}
                      </div>
                      {(isDone) && <div style={{ fontSize: 10, color: "#16a34a", marginTop: 2 }}>✓ complete</div>}
                      {(isActive || isCurrentAnim) && <div style={{ fontSize: 10, color: "#60a5fa", marginTop: 2 }}>● running…</div>}
                    </div>
                  </div>
                );
              })}
              <div style={{ width: 2, height: 14, background: result ? "#16a34a" : "#1e293b" }} />
              <div style={{ fontSize: 11, color: result ? "#4ade80" : "#475569" }}>END</div>
            </div>

            {/* Step detail popup */}
            {activeStep && (
              <div style={{ marginTop: 14, background: "#0d1117", border: "1px solid #334155", borderRadius: 8, padding: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontWeight: 600, color: "#60a5fa", fontFamily: "'DM Mono', monospace" }}>{activeStep.node}</span>
                  <button onClick={() => setActiveStep(null)} style={{ background: "none", border: "none", color: "#64748b", fontSize: 16 }}>×</button>
                </div>
                <pre style={{ margin: 0, fontSize: 11, color: "#94a3b8", whiteSpace: "pre-wrap", fontFamily: "'DM Mono', monospace", lineHeight: 1.6 }}>{activeStep.detail}</pre>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div>
          {!result && !isRunning && (
            <div style={{ background: "#111827", border: "1px solid #1e293b", borderRadius: 12, padding: 32, textAlign: "center", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center" }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>🤖</div>
              <p style={{ color: "#475569", fontSize: 14 }}>Submit a refund request to see the AI agent process it in real-time.</p>
              <p style={{ color: "#334155", fontSize: 12 }}>Try a sample case on the left, or type your own with an order ID like ORD-1006.</p>
            </div>
          )}

          {isRunning && !result && (
            <div style={{ background: "#111827", border: "1px solid #1e293b", borderRadius: 12, padding: 24 }}>
              <p style={{ fontSize: 12, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#64748b", marginBottom: 14 }}>Processing Steps</p>
              {Array.from({ length: animStep + 1 }).map((_, i) => (
                <div key={i} className="slide-in" style={{ display: "flex", gap: 10, marginBottom: 12 }}>
                  <div style={{ width: 20, height: 20, borderRadius: "50%", background: "#16a34a", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, flexShrink: 0, marginTop: 1 }}>✓</div>
                  <div>
                    <div style={{ fontSize: 11, fontFamily: "'DM Mono', monospace", color: "#60a5fa", fontWeight: 500 }}>{NODES[i]}</div>
                    <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>Completed</div>
                  </div>
                </div>
              ))}
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4 }}>
                <div style={{ width: 20, height: 20, borderRadius: "50%", border: "2px solid #3b82f6", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#3b82f6", animation: "pulse 1s infinite" }} />
                </div>
                <div style={{ fontSize: 11, fontFamily: "'DM Mono', monospace", color: "#3b82f6" }}>
                  {NODES[animStep + 1] || "finalizing"}…
                </div>
              </div>
            </div>
          )}

          {result && (
            <div className="slide-in">
              {/* Decision card */}
              <div style={{ background: ds.bg, border: `2px solid ${ds.border}`, borderRadius: 12, padding: 20, marginBottom: 16 }}>
                <p style={{ margin: "0 0 6px", fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: ds.border }}>Decision</p>
                <div style={{ fontSize: 22, fontWeight: 700, color: ds.text }}>{ds.label}</div>
                {result.refundAmount > 0 && (
                  <div style={{ marginTop: 8, fontSize: 18, fontWeight: 600, color: "#4ade80" }}>
                    ${result.refundAmount.toFixed(2)} refund
                  </div>
                )}
              </div>

              {/* Order details */}
              {result.order && (
                <div style={{ background: "#111827", border: "1px solid #1e293b", borderRadius: 12, padding: 16, marginBottom: 16 }}>
                  <p style={{ margin: "0 0 10px", fontSize: 12, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#64748b" }}>Order Details</p>
                  {[
                    ["Order ID", result.orderId],
                    ["Product", result.order.product],
                    ["Category", result.order.category.charAt(0).toUpperCase() + result.order.category.slice(1)],
                    ["Price", `$${result.order.price.toFixed(2)}`],
                    ["Days Since Purchase", `${result.order.days} days`],
                    ["Membership", `${result.order.membership === "premium" ? "⭐ " : ""}${result.order.membership.charAt(0).toUpperCase() + result.order.membership.slice(1)}`],
                    ["Opened", result.order.opened ? "Yes" : "No"],
                    ["Defective", result.order.defective ? "⚠️ Yes" : "No"],
                  ].map(([k, v]) => (
                    <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid #0f172a", fontSize: 13 }}>
                      <span style={{ color: "#64748b" }}>{k}</span>
                      <span style={{ color: "#e2e8f0", fontWeight: 500 }}>{v}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Agent response */}
              <div style={{ background: "#111827", border: "1px solid #1e293b", borderRadius: 12, padding: 16 }}>
                <p style={{ margin: "0 0 10px", fontSize: 12, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#64748b" }}>Agent Response</p>
                <div style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.7 }}>
                  {result.response.split("\n").map((line, i) => (
                    <p key={i} style={{ margin: "0 0 6px" }}>
                      {line.split(/(\*\*[^*]+\*\*)/).map((part, j) =>
                        part.startsWith("**") ? <strong key={j} style={{ color: "#f1f5f9" }}>{part.slice(2,-2)}</strong> : part
                      )}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={{ marginTop: 24, fontSize: 11, color: "#334155", textAlign: "center" }}>
        <span>LangGraph Agent · FAISS Vector Store · GPT-4o-mini · 6 nodes · 10 policy documents</span>
      </div>
    </div>
  );
}
