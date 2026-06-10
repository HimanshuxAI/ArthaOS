from datetime import date

from app.services.chat import answer_financial_question
from app.services.intelligence import (
    analyze_finances,
    detect_subscriptions,
    generate_forecast,
)


def _phase2_transactions():
    return [
        {"date": date(2026, 1, 5), "description": "CLIENT ALPHA RETAINER", "amount": 100000.0, "type": "income", "category": "Business Revenue"},
        {"date": date(2026, 1, 6), "description": "CLIENT BETA PROJECT", "amount": 50000.0, "type": "income", "category": "Business Revenue"},
        {"date": date(2026, 1, 10), "description": "FIGMA", "amount": 5000.0, "type": "expense", "category": "Software"},
        {"date": date(2026, 1, 11), "description": "LINKEDIN ADS", "amount": 10000.0, "type": "expense", "category": "Marketing"},
        {"date": date(2026, 1, 12), "description": "STARBUCKS", "amount": 2500.0, "type": "expense", "category": "Food"},
        {"date": date(2026, 2, 5), "description": "CLIENT ALPHA RETAINER", "amount": 110000.0, "type": "income", "category": "Business Revenue"},
        {"date": date(2026, 2, 6), "description": "CLIENT GAMMA PROJECT", "amount": 60000.0, "type": "income", "category": "Business Revenue"},
        {"date": date(2026, 2, 10), "description": "FIGMA", "amount": 5000.0, "type": "expense", "category": "Software"},
        {"date": date(2026, 2, 11), "description": "LINKEDIN ADS", "amount": 14200.0, "type": "expense", "category": "Marketing"},
        {"date": date(2026, 2, 12), "description": "SWIGGY", "amount": 3500.0, "type": "expense", "category": "Food"},
    ]


def test_phase2_intelligence_calculates_kpis_health_and_risk():
    intelligence = analyze_finances(_phase2_transactions(), cash_reserve=400000)

    assert intelligence["kpis"]["cash_flow"] == 312800.0
    assert intelligence["kpis"]["monthly_growth"] == 13.33
    assert intelligence["kpis"]["savings_rate"] == 91.74
    assert 80 <= intelligence["health_score"]["score"] <= 100
    assert intelligence["health_score"]["label"] == "Healthy Business"
    assert intelligence["revenue_analytics"]["best_month"]["month"] == "2026-02"
    assert intelligence["revenue_analytics"]["largest_income_source"]["source"] == "CLIENT ALPHA"
    assert any("Marketing spend increased by 42%" in alert["message"] for alert in intelligence["notifications"])
    assert len(intelligence["insights"]) >= 10


def test_subscription_detector_groups_recurring_payments():
    subscriptions = detect_subscriptions(_phase2_transactions())

    assert subscriptions[0]["merchant"] == "FIGMA"
    assert subscriptions[0]["monthly_cost"] == 5000.0
    assert subscriptions[0]["annual_cost"] == 60000.0


def test_forecast_predicts_next_month_with_confidence():
    forecast = generate_forecast(_phase2_transactions())

    assert forecast["next_month_revenue"] > 170000
    assert forecast["next_month_expenses"] > 27000
    assert forecast["expected_profit"] > 140000
    assert forecast["confidence"] in {"medium", "high"}


def test_cfo_chat_answers_phase2_questions():
    transactions = _phase2_transactions()

    assert "can afford" in answer_financial_question("Can I afford a ₹1 lakh laptop?", transactions, cash_reserve=400000).lower()
    assert "Marketing" in answer_financial_question("What should I reduce?", transactions)
    assert "FIGMA" in answer_financial_question("What subscription services am I paying for?", transactions)
    assert "tax" in answer_financial_question("What is my expected tax?", transactions).lower()
