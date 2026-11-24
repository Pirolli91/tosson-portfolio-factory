"""Summer-2027 Kia Finance America (KFA) Finance-Clause Checklist Stub.

DOCUMENT CHECKLIST GENERATOR ONLY — NOT LEGAL OR FINANCIAL ADVICE.

Standalone utility inside the isolated `kia_carnival` package. Produces a
structured pre-signing review checklist (and optional keyword scan of user-supplied
contract text) for evaluating retail installment contract clauses ahead of a
Summer-2027 KFA financing + early-payoff strategy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

CHECKLIST_DISCLAIMER_BANNER = (
    "DOCUMENT CHECKLIST GENERATOR ONLY — NOT LEGAL OR FINANCIAL ADVICE"
)


@dataclass(frozen=True)
class ChecklistRule:
    clause_id: str
    title: str
    what_to_verify: str
    document_section: str
    favorable_patterns: tuple[str, ...]
    risk_patterns: tuple[str, ...]


KFA_CHECKLIST_RULES: tuple[ChecklistRule, ...] = (
    ChecklistRule(
        clause_id="NO_MINIMUM_FINANCING_TERM",
        title="No Minimum Financing Term / Early-Payoff Hold Restriction",
        what_to_verify=(
            "Confirm the Retail Installment Sale Contract (RISC) contains NO borrower "
            "covenant requiring the loan to remain open for a minimum number of months "
            "or payments (e.g., 90 days / 3–6 payments) before payoff."
        ),
        document_section="Retail Installment Sale Contract — Prepayment / Payment Terms & Any Dealer Addendum",
        favorable_patterns=(
            r"may\s+prepay\s+.{0,50}\bat\s+any\s+time",
            r"no\s+minimum\s+(financing\s+)?term",
            r"pay\s+off\s+(early\s+)?at\s+any\s+time",
        ),
        risk_patterns=(
            r"minimum\s+(financing\s+)?(term|period)\s+of\s+\d+",
            r"must\s+(keep|maintain|make)\s+(at\s+least\s+)?\d+\s+(monthly\s+)?payments",
            r"early\s+payoff\s+(restriction|prohibited|not\s+permitted)",
            r"cannot\s+(be\s+)?paid\s+off\s+within\s+\d+",
        ),
    ),
    ChecklistRule(
        clause_id="ZERO_PREPAYMENT_PENALTY",
        title="Zero Prepayment Penalty",
        what_to_verify=(
            "Confirm the Federal Truth-in-Lending (TILA) disclosure box marks 'will not' "
            "for prepayment penalty and the contract explicitly states $0 / no penalty "
            "for paying off early."
        ),
        document_section="Federal TILA Disclosure Box ('Prepayment') & Prepayment Paragraph",
        favorable_patterns=(
            r"will\s+not\s+have\s+to\s+pay\s+a\s+penalty",
            r"no\s+prepayment\s+penalty",
            r"without\s+(a\s+)?prepayment\s+penalty",
            r"prepayment\s+penalty[:\s]+\$?0(\.00)?\b",
        ),
        risk_patterns=(
            r"may\s+have\s+to\s+pay\s+a\s+penalty",
            r"prepayment\s+(penalty|fee)\s+(of|applies|equal)",
            r"early\s+termination\s+fee\s+of\s+\$?[1-9]",
        ),
    ),
    ChecklistRule(
        clause_id="SIMPLE_INTEREST_DAILY_ACCRUAL",
        title="Simple-Interest Daily Accrual (Not Precomputed)",
        what_to_verify=(
            "Confirm finance charges accrue on a daily simple-interest basis on unpaid "
            "principal so early payoff eliminates unearned future interest (not "
            "precomputed / Rule of 78s)."
        ),
        document_section="How Finance Charge Is Figured / Simple Finance Charge Section",
        favorable_patterns=(
            r"simple\s+(interest|finance\s+charge)",
            r"daily\s+(basis|accrual)\s+on\s+the\s+unpaid",
            r"finance\s+charge\s+on\s+a\s+daily\s+basis",
        ),
        risk_patterns=(
            r"precomputed\s+(interest|finance\s+charge|contract)",
            r"rule\s+of\s+78s?",
            r"sum\s+of\s+the\s+digits",
        ),
    ),
    ChecklistRule(
        clause_id="DEALER_CHARGEBACK_VS_BORROWER_OBLIGATION",
        title="Dealer Rebate Chargeback vs. Borrower Contractual Obligation",
        what_to_verify=(
            "Verify that any KFA dealer-reserve/incentive chargeback remains strictly "
            "between KFA and the dealer — confirm NO borrower-signed addendum or "
            "side-agreement obligates the buyer to reimburse the dealer for lost rebate "
            "or reserve upon early payoff."
        ),
        document_section="Dealer Addenda, 'We Owe', Rebate Assignment & Side Agreements",
        favorable_patterns=(
            r"dealer\s+chargeback\s+(is\s+)?not\s+(the\s+)?borrower'?s?\s+obligation",
            r"no\s+borrower\s+(rebate\s+)?clawback",
            r"buyer\s+(has\s+)?no\s+obligation\s+to\s+repay\s+(dealer\s+)?rebate",
        ),
        risk_patterns=(
            r"(buyer|borrower)\s+(agrees\s+to|shall|must)\s+(repay|reimburse|refund)\s+(the\s+)?(dealer|rebate|incentive|chargeback)",
            r"rebate\s+clawback\s+from\s+(buyer|borrower)",
            r"chargeback\s+(fee|reimbursement)\s+(payable|owed)\s+by\s+(buyer|borrower)",
        ),
    ),
)


def _find_snippet(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    start = max(0, match.start() - 35)
    end = min(len(text), match.end() + 35)
    snippet = re.sub(r"\s+", " ", text[start:end]).strip()
    return snippet


def generate_kfa_finance_checklist(contract_text: str | None = None) -> dict[str, Any]:
    """Generate the Summer-2027 KFA pre-signing document checklist.

    If `contract_text` is provided, performs deterministic keyword/regex scanning
    to surface candidate clauses for human inspection. Output is strictly a
    document checklist generator only — NOT legal or financial advice.
    """
    has_text = bool(contract_text and contract_text.strip())
    items: list[dict[str, Any]] = []

    for rule in KFA_CHECKLIST_RULES:
        risk_hits: list[str] = []
        favorable_hits: list[str] = []
        if has_text and contract_text is not None:
            for pat in rule.risk_patterns:
                snip = _find_snippet(contract_text, pat)
                if snip:
                    risk_hits.append(snip)
            for pat in rule.favorable_patterns:
                snip = _find_snippet(contract_text, pat)
                if snip:
                    favorable_hits.append(snip)

        if risk_hits:
            status = "RISK_PHRASE_FOUND"
        elif favorable_hits:
            status = "FAVORABLE_PHRASE_FOUND"
        else:
            status = "NEEDS_MANUAL_REVIEW"

        items.append(
            {
                "clause_id": rule.clause_id,
                "title": rule.title,
                "status": status,
                "document_section": rule.document_section,
                "what_to_verify": rule.what_to_verify,
                "favorable_snippets": favorable_hits,
                "risk_snippets": risk_hits,
            }
        )

    return {
        "banner": CHECKLIST_DISCLAIMER_BANNER,
        "is_legal_or_financial_advice": False,
        "purpose": "Summer-2027 Kia Finance America (KFA) pre-signing document checklist generator",
        "contract_text_scanned": has_text,
        "summary_counts": {
            "RISK_PHRASE_FOUND": sum(1 for i in items if i["status"] == "RISK_PHRASE_FOUND"),
            "FAVORABLE_PHRASE_FOUND": sum(1 for i in items if i["status"] == "FAVORABLE_PHRASE_FOUND"),
            "NEEDS_MANUAL_REVIEW": sum(1 for i in items if i["status"] == "NEEDS_MANUAL_REVIEW"),
        },
        "checklist_items": items,
    }


def render_checklist_markdown(checklist: dict[str, Any]) -> str:
    lines: list[str] = [
        "## Summer-2027 KFA Finance-Clause Checklist Stub",
        "",
        f"> **NOTICE: {checklist['banner']}.**  ",
        "> This stub flags candidate keywords and produces a structured pre-signing review checklist.",
        "> Confirm every contract term directly on the final signed paperwork or with a qualified professional.",
        "",
        f"- **Contract Text Scanned:** `{'YES' if checklist['contract_text_scanned'] else 'NO (blank pre-signing checklist)'}`",
        "",
        "| Clause ID | Status | Check Item | Document Section |",
        "|---|---|---|---|",
    ]
    for item in checklist["checklist_items"]:
        lines.append(
            f"| `{item['clause_id']}` | `{item['status']}` | {item['title']} | {item['document_section']} |"
        )
    lines.append("")
    for item in checklist["checklist_items"]:
        lines.append(f"- **`{item['clause_id']}` ({item['status']}):** {item['what_to_verify']}")
        for snip in item["risk_snippets"]:
            lines.append(f"  - *Risk phrase match:* `...{snip}...`")
        for snip in item["favorable_snippets"]:
            lines.append(f"  - *Favorable phrase match:* `...{snip}...`")
    return "\n".join(lines) + "\n"
