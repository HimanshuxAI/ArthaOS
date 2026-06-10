from collections import defaultdict
from datetime import date


def estimate_tax(annual_profit: float) -> float:
    if annual_profit <= 300000:
        return 0
    if annual_profit <= 700000:
        return round(annual_profit * 0.05, 2)
    if annual_profit <= 1000000:
        return round(annual_profit * 0.10, 2)
    return round(annual_profit * 0.20, 2)


def build_report(transactions: list[dict]) -> dict:
    revenue = sum(float(tx["amount"]) for tx in transactions if tx["type"] == "income")
    expenses = sum(float(tx["amount"]) for tx in transactions if tx["type"] == "expense")
    expense_breakdown: dict[str, float] = defaultdict(float)
    revenue_trend: dict[str, float] = defaultdict(float)
    monthly_profit: dict[str, float] = defaultdict(float)

    for tx in transactions:
        tx_date = tx["date"]
        month = tx_date.strftime("%Y-%m") if isinstance(tx_date, date) else str(tx_date)[:7]
        amount = float(tx["amount"])
        if tx["type"] == "income":
            revenue_trend[month] += amount
            monthly_profit[month] += amount
        else:
            expense_breakdown[str(tx.get("category") or "Miscellaneous")] += amount
            monthly_profit[month] -= amount

    profit = revenue - expenses
    return {
        "revenue": round(revenue, 2),
        "expenses": round(expenses, 2),
        "profit": round(profit, 2),
        "tax_estimate": estimate_tax(profit),
        "expense_breakdown": dict(sorted(expense_breakdown.items())),
        "revenue_trend": [{"month": month, "revenue": round(value, 2)} for month, value in sorted(revenue_trend.items())],
        "monthly_profit": [{"month": month, "profit": round(value, 2)} for month, value in sorted(monthly_profit.items())],
    }
