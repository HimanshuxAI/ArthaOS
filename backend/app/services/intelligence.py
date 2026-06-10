from collections import Counter, defaultdict
from datetime import date, timedelta
from statistics import mean, pstdev

from app.services.finance import estimate_tax

SUBSCRIPTION_MERCHANTS = (
    "NETFLIX",
    "FIGMA",
    "GOOGLE CLOUD",
    "AWS",
    "CHATGPT",
    "OPENAI",
    "LINKEDIN PREMIUM",
    "CANVA",
    "ADOBE",
    "VERCEL",
)


def _money(value: float) -> float:
    return round(float(value), 2)


def _month(tx_date: date) -> str:
    return tx_date.strftime("%Y-%m")


def _week(tx_date: date) -> str:
    year, week, _ = tx_date.isocalendar()
    return f"{year}-W{week:02d}"


def _source(description: str) -> str:
    words = description.upper().replace("-", " ").split()
    if not words:
        return "UNKNOWN"
    if words[0] == "CLIENT" and len(words) > 1:
        return f"CLIENT {words[1]}"
    return " ".join(words[:2])


def _merchant(description: str) -> str:
    normalized = description.upper()
    for merchant in SUBSCRIPTION_MERCHANTS:
        if merchant in normalized:
            return merchant
    words = normalized.split()
    return " ".join(words[:2]) if words else "UNKNOWN"


def _monthly_totals(transactions: list[dict], tx_type: str) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for tx in transactions:
        if tx["type"] == tx_type:
            totals[_month(tx["date"])] += float(tx["amount"])
    return dict(sorted((month, _money(value)) for month, value in totals.items()))


def _growth_percent(monthly_revenue: dict[str, float]) -> float:
    values = list(monthly_revenue.values())
    if len(values) < 2 or values[-2] == 0:
        return 0
    return _money(((values[-1] - values[-2]) / values[-2]) * 100)


def _latest_month(transactions: list[dict]) -> str | None:
    if not transactions:
        return None
    return max(_month(tx["date"]) for tx in transactions)


def detect_subscriptions(transactions: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for tx in transactions:
        if tx["type"] != "expense":
            continue
        merchant = _merchant(tx["description"])
        if merchant in SUBSCRIPTION_MERCHANTS:
            grouped[merchant].append(tx)

    subscriptions = []
    for merchant, rows in grouped.items():
        months = {_month(tx["date"]) for tx in rows}
        if len(rows) < 2 and merchant not in SUBSCRIPTION_MERCHANTS:
            continue
        monthly_cost = _money(mean(float(tx["amount"]) for tx in rows))
        last_seen = max(tx["date"] for tx in rows)
        renewal = last_seen + timedelta(days=30)
        subscriptions.append(
            {
                "merchant": merchant,
                "category": rows[-1].get("category", "Software"),
                "monthly_cost": monthly_cost,
                "annual_cost": _money(monthly_cost * 12),
                "frequency_months": len(months),
                "renewal_alert": f"Likely renewal around {renewal.isoformat()}",
                "last_seen": last_seen.isoformat(),
            }
        )
    return sorted(subscriptions, key=lambda item: item["monthly_cost"], reverse=True)


def generate_forecast(transactions: list[dict]) -> dict:
    monthly_revenue = _monthly_totals(transactions, "income")
    monthly_expenses = _monthly_totals(transactions, "expense")
    revenue_values = list(monthly_revenue.values())
    expense_values = list(monthly_expenses.values())

    if not revenue_values and not expense_values:
        return {
            "next_month_revenue": 0,
            "next_month_expenses": 0,
            "expected_profit": 0,
            "expected_tax": 0,
            "confidence": "low",
        }

    revenue_average = mean(revenue_values or [0])
    expense_average = mean(expense_values or [0])
    revenue_trend = (revenue_values[-1] - revenue_values[0]) / max(len(revenue_values) - 1, 1) if len(revenue_values) > 1 else 0
    expense_trend = (expense_values[-1] - expense_values[0]) / max(len(expense_values) - 1, 1) if len(expense_values) > 1 else 0
    next_revenue = max(0, revenue_average + revenue_trend)
    next_expenses = max(0, expense_average + expense_trend)
    expected_profit = next_revenue - next_expenses
    months = max(len(set(_month(tx["date"]) for tx in transactions)), 1)
    confidence = "high" if months >= 6 else "medium" if months >= 2 else "low"
    return {
        "next_month_revenue": _money(next_revenue),
        "next_month_expenses": _money(next_expenses),
        "expected_profit": _money(expected_profit),
        "expected_tax": estimate_tax(expected_profit * 12),
        "confidence": confidence,
    }


def _health_score(
    revenue: float,
    expenses: float,
    profit: float,
    monthly_revenue: dict[str, float],
    income_sources: Counter,
    cash_reserve: float,
    monthly_growth: float,
) -> dict:
    savings_ratio = (profit / revenue * 100) if revenue else 0
    expense_ratio = (expenses / revenue * 100) if revenue else 100
    revenue_values = list(monthly_revenue.values())
    stability = 85 if len(revenue_values) < 2 else max(0, 100 - min(100, (pstdev(revenue_values) / max(mean(revenue_values), 1)) * 100))
    expense_control = max(0, 100 - expense_ratio)
    savings = max(0, min(100, savings_ratio))
    diversity = min(100, len(income_sources) * 25)
    reserves = min(100, (cash_reserve / max(expenses / max(len(monthly_revenue), 1), 1)) * 25) if expenses else 100
    growth = max(0, min(100, 50 + monthly_growth))
    tax_preparedness = 90 if profit > 0 else 50
    factors = {
        "Revenue Stability": _money(stability),
        "Expense Control": _money(expense_control),
        "Savings Ratio": _money(savings),
        "Income Diversity": _money(diversity),
        "Cash Reserves": _money(reserves),
        "Growth Rate": _money(growth),
        "Tax Preparedness": _money(tax_preparedness),
    }
    score = int(round(sum(factors.values()) / len(factors)))
    label = "Healthy Business" if score >= 75 else "Stable but Watchful" if score >= 55 else "Needs Attention"
    explanation = (
        f"Score is driven by {savings_ratio:.0f}% savings rate, "
        f"{len(income_sources)} income sources, and {monthly_growth:.0f}% latest revenue growth."
    )
    return {"score": score, "label": label, "factors": factors, "explanation": explanation}


def _budget_progress(transactions: list[dict], budgets: list[dict] | None) -> list[dict]:
    latest = _latest_month(transactions)
    rows = []
    for budget in budgets or []:
        spent = sum(
            float(tx["amount"])
            for tx in transactions
            if tx["type"] == "expense" and tx.get("category") == budget["category"] and (not latest or _month(tx["date"]) == latest)
        )
        limit = float(budget["monthly_limit"])
        rows.append({**budget, "spent": _money(spent), "remaining": _money(limit - spent), "progress_percent": _money((spent / limit) * 100 if limit else 0)})
    return rows


def _goal_progress(cash_reserve: float, goals: list[dict] | None) -> list[dict]:
    rows = []
    for goal in goals or []:
        current = float(goal.get("current_amount") or min(cash_reserve, float(goal["target_amount"])))
        target = float(goal["target_amount"])
        rows.append({**goal, "current_amount": _money(current), "progress_percent": _money((current / target) * 100 if target else 0)})
    return rows


def analyze_finances(
    transactions: list[dict],
    budgets: list[dict] | None = None,
    goals: list[dict] | None = None,
    cash_reserve: float = 0,
) -> dict:
    revenue = sum(float(tx["amount"]) for tx in transactions if tx["type"] == "income")
    expenses = sum(float(tx["amount"]) for tx in transactions if tx["type"] == "expense")
    profit = revenue - expenses
    monthly_revenue = _monthly_totals(transactions, "income")
    monthly_expenses = _monthly_totals(transactions, "expense")
    monthly_growth = _growth_percent(monthly_revenue)
    months_count = max(len(set(_month(tx["date"]) for tx in transactions)), 1)
    monthly_average = _money(expenses / months_count)
    burn_rate = _money(expenses / months_count)
    runway = _money(cash_reserve / burn_rate) if burn_rate else 999
    savings_rate = _money((profit / revenue) * 100) if revenue else 0
    income_sources = Counter(_source(tx["description"]) for tx in transactions if tx["type"] == "income")
    health_score = _health_score(revenue, expenses, profit, monthly_revenue, income_sources, cash_reserve, monthly_growth)

    category_breakdown: dict[str, float] = defaultdict(float)
    weekly_revenue: dict[str, float] = defaultdict(float)
    monthly_profit: dict[str, float] = defaultdict(float)
    for tx in transactions:
        amount = float(tx["amount"])
        if tx["type"] == "income":
            weekly_revenue[_week(tx["date"])] += amount
            monthly_profit[_month(tx["date"])] += amount
        else:
            category_breakdown[str(tx.get("category") or "Miscellaneous")] += amount
            monthly_profit[_month(tx["date"])] -= amount

    best_month = max(monthly_revenue.items(), key=lambda item: item[1], default=("", 0))
    worst_month = min(monthly_revenue.items(), key=lambda item: item[1], default=("", 0))
    largest_source = income_sources.most_common(1)[0] if income_sources else ("No income yet", 0)
    top_expenses = sorted(
        [tx for tx in transactions if tx["type"] == "expense"],
        key=lambda tx: float(tx["amount"]),
        reverse=True,
    )[:10]
    subscriptions = detect_subscriptions(transactions)
    forecast = generate_forecast(transactions)

    notifications = _notifications(transactions, monthly_expenses, monthly_growth, category_breakdown, income_sources, cash_reserve)
    insights = _insights(revenue, expenses, profit, monthly_growth, savings_rate, category_breakdown, income_sources, subscriptions, forecast, runway)

    return {
        "kpis": {
            "total_revenue": _money(revenue),
            "total_expenses": _money(expenses),
            "net_profit": _money(profit),
            "estimated_tax": estimate_tax(profit),
            "cash_flow": _money(profit),
            "monthly_growth": monthly_growth,
            "savings_rate": savings_rate,
            "business_health_score": health_score["score"],
            "money_in": _money(revenue),
            "money_out": _money(expenses),
            "net_cash": _money(profit),
            "burn_rate": burn_rate,
            "runway_months": runway,
            "monthly_average": monthly_average,
        },
        "health_score": health_score,
        "revenue_analytics": {
            "monthly_revenue": [{"month": month, "revenue": value} for month, value in monthly_revenue.items()],
            "weekly_revenue": [{"week": week, "revenue": _money(value)} for week, value in sorted(weekly_revenue.items())],
            "revenue_growth_percent": monthly_growth,
            "best_month": {"month": best_month[0], "revenue": _money(best_month[1])},
            "worst_month": {"month": worst_month[0], "revenue": _money(worst_month[1])},
            "average_monthly_revenue": _money(mean(monthly_revenue.values()) if monthly_revenue else 0),
            "largest_income_source": {"source": largest_source[0], "amount": _money(largest_source[1])},
        },
        "expense_analytics": {
            "breakdown_by_category": dict(sorted((key, _money(value)) for key, value in category_breakdown.items())),
            "monthly_comparison": [{"month": month, "expenses": value} for month, value in monthly_expenses.items()],
            "top_expenses": [
                {
                    "date": tx["date"].isoformat(),
                    "description": tx["description"],
                    "amount": _money(tx["amount"]),
                    "category": tx.get("category", "Miscellaneous"),
                }
                for tx in top_expenses
            ],
            "recurring_expenses": subscriptions,
        },
        "cash_flow": {
            "money_in": _money(revenue),
            "money_out": _money(expenses),
            "net_cash": _money(profit),
            "burn_rate": burn_rate,
            "runway_months": runway,
            "monthly_average": monthly_average,
        },
        "monthly_profit": [{"month": month, "profit": _money(value)} for month, value in sorted(monthly_profit.items())],
        "subscriptions": subscriptions,
        "forecast": forecast,
        "insights": insights,
        "notifications": notifications,
        "budget_progress": _budget_progress(transactions, budgets),
        "goal_progress": _goal_progress(cash_reserve, goals),
    }


def _notifications(
    transactions: list[dict],
    monthly_expenses: dict[str, float],
    monthly_growth: float,
    category_breakdown: dict[str, float],
    income_sources: Counter,
    cash_reserve: float,
) -> list[dict]:
    notifications: list[dict] = []
    if len(monthly_expenses) >= 2:
        months = list(monthly_expenses)
        latest_month, previous_month = months[-1], months[-2]
        for category in {tx.get("category") for tx in transactions if tx["type"] == "expense"}:
            latest = sum(float(tx["amount"]) for tx in transactions if tx["type"] == "expense" and tx.get("category") == category and _month(tx["date"]) == latest_month)
            previous = sum(float(tx["amount"]) for tx in transactions if tx["type"] == "expense" and tx.get("category") == category and _month(tx["date"]) == previous_month)
            if previous and latest > previous * 1.25:
                increase = round(((latest - previous) / previous) * 100)
                notifications.append(
                    {
                        "type": "unusual_spend",
                        "title": "Unusual spending detected",
                        "message": f"{category} spend increased by {increase}%.",
                        "severity": "warning",
                    }
                )
    if monthly_growth < -10:
        notifications.append({"type": "revenue_drop", "title": "Revenue dropped", "message": "Revenue dropped more than 10% this month.", "severity": "critical"})
    if income_sources:
        top_source, top_amount = income_sources.most_common(1)[0]
        total_income_rows = sum(income_sources.values())
        if top_amount / total_income_rows >= 0.7:
            notifications.append(
                {
                    "type": "client_concentration",
                    "title": "Client concentration risk",
                    "message": f"{top_source} contributes most of your income transactions.",
                    "severity": "warning",
                }
            )
    if cash_reserve and category_breakdown and cash_reserve < sum(category_breakdown.values()):
        notifications.append({"type": "cash_reserve", "title": "Cash reserve below target", "message": "Cash reserves are below one period of expenses.", "severity": "warning"})
    notifications.append({"type": "tax", "title": "Tax preparedness", "message": "Review estimated tax monthly and reserve cash before filing deadlines.", "severity": "info"})
    return notifications[:12]


def _insights(
    revenue: float,
    expenses: float,
    profit: float,
    monthly_growth: float,
    savings_rate: float,
    category_breakdown: dict[str, float],
    income_sources: Counter,
    subscriptions: list[dict],
    forecast: dict,
    runway: float,
) -> list[dict]:
    top_category = max(category_breakdown.items(), key=lambda item: item[1], default=("No expenses", 0))
    top_source = income_sources.most_common(1)[0] if income_sources else ("No income source", 0)
    subscription_total = sum(item["monthly_cost"] for item in subscriptions)
    concentration = (top_source[1] / max(sum(income_sources.values()), 1)) * 100 if income_sources else 0
    raw = [
        ("Revenue momentum", f"Revenue changed {monthly_growth:.0f}% in the latest month.", "positive" if monthly_growth >= 0 else "warning", "revenue"),
        ("Expense focus", f"{top_category[0]} is your largest cost category at ₹{top_category[1]:,.0f}.", "info", "expense"),
        ("Profitability", f"Net profit is ₹{profit:,.0f} after ₹{expenses:,.0f} of expenses.", "positive" if profit > 0 else "critical", "profit"),
        ("Savings rate", f"You are saving {savings_rate:.0f}% of revenue.", "positive" if savings_rate >= 25 else "warning", "cash"),
        ("Subscription load", f"Detected subscriptions cost about ₹{subscription_total:,.0f}/month.", "info", "subscription"),
        ("Income concentration", f"{top_source[0]} contributes about {concentration:.0f}% of observed income events.", "warning" if concentration >= 70 else "info", "risk"),
        ("Runway", f"You have enough cash for about {runway:.1f} months at the current burn rate.", "positive" if runway >= 4 else "warning", "cash"),
        ("Forecast", f"Next month profit is forecast at ₹{forecast['expected_profit']:,.0f} with {forecast['confidence']} confidence.", "info", "forecast"),
        ("Tax reserve", f"Expected tax from forecast annualized profit is ₹{forecast['expected_tax']:,.0f}.", "info", "tax"),
        ("Action", f"Review {top_category[0]} before adding new commitments.", "info", "recommendation"),
        ("Operating leverage", f"Every 1% expense reduction frees about ₹{expenses * 0.01:,.0f}.", "info", "recommendation"),
        ("Growth quality", "Revenue growth is healthiest when no single client dominates cash inflow.", "info", "risk"),
    ]
    return [{"title": title, "message": message, "severity": severity, "category": category} for title, message, severity, category in raw]
