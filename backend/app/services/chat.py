import re

from app.services.finance import build_report
from app.services.intelligence import analyze_finances


def _rupees(value: float) -> str:
    return f"₹{value:,.0f}"


def answer_financial_question(question: str, transactions: list[dict], cash_reserve: float = 0) -> str:
    q = question.lower()
    report = build_report(transactions)
    intelligence = analyze_finances(transactions, cash_reserve=cash_reserve)

    if "food" in q:
        total = sum(float(tx["amount"]) for tx in transactions if tx["type"] == "expense" and tx.get("category") == "Food")
        return f"You spent {_rupees(total)} on Food across the uploaded transactions."

    if "biggest expense" in q:
        expenses = [tx for tx in transactions if tx["type"] == "expense"]
        if not expenses:
            return "I could not find any expenses yet."
        biggest = max(expenses, key=lambda tx: float(tx["amount"]))
        return f"Your biggest expense was {biggest['description']} at {_rupees(float(biggest['amount']))}."

    if "profit" in q:
        return f"Your net profit is {_rupees(report['profit'])}: revenue of {_rupees(report['revenue'])} minus expenses of {_rupees(report['expenses'])}."

    if "laptop" in q or "afford" in q:
        amounts = [int(value.replace(",", "")) for value in re.findall(r"₹?\s?([0-9][0-9,]{3,})", question)]
        requested = float(amounts[0]) if amounts else 100000.0
        available = max(cash_reserve, report["profit"])
        if available >= requested * 1.5:
            return f"You can afford {_rupees(requested)} while keeping a buffer. Current available profit/cash is about {_rupees(available)}."
        return f"Delay this purchase. {_rupees(requested)} would materially reduce your available buffer of {_rupees(available)}."

    if "reduce" in q or "cut" in q:
        breakdown = intelligence["expense_analytics"]["breakdown_by_category"]
        if not breakdown:
            return "I do not see enough expenses yet to recommend reductions."
        category, amount = max(breakdown.items(), key=lambda item: item[1])
        return f"Start with {category}. It is your largest cost bucket at {_rupees(amount)}; reducing it by 10% saves about {_rupees(amount * 0.10)}."

    if "expected tax" in q or "tax" in q:
        return f"Your current estimated tax is {_rupees(report['tax_estimate'])}. The forecasted annualized tax is {_rupees(intelligence['forecast']['expected_tax'])}."

    if "subscription" in q or "services" in q:
        subscriptions = intelligence["subscriptions"]
        if not subscriptions:
            return "I could not detect recurring subscription services yet."
        items = ", ".join(f"{item['merchant']} ({_rupees(item['monthly_cost'])}/month)" for item in subscriptions[:5])
        return f"Detected subscription services: {items}."

    if "category" in q and ("cost" in q or "most" in q):
        breakdown = report["expense_breakdown"]
        if not breakdown:
            return "I could not find any expense categories yet."
        category, amount = max(breakdown.items(), key=lambda item: item[1])
        return f"{category} costs the most at {_rupees(amount)}."

    return (
        f"Revenue is {_rupees(report['revenue'])}, expenses are {_rupees(report['expenses'])}, "
        f"net profit is {_rupees(report['profit'])}, and estimated tax is {_rupees(report['tax_estimate'])}."
    )
