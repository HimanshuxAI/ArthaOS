from datetime import date

from app.services.categorizer import categorize_transaction
from app.services.chat import answer_financial_question
from app.services.finance import build_report, estimate_tax
from app.services.parser import parse_csv_statement


def test_csv_parser_normalizes_common_bank_columns():
    csv_text = """Date,Narration,Debit,Credit
2026-01-05,STARBUCKS,400,
2026-01-06,UPWORK GLOBAL,,50000
"""

    transactions = parse_csv_statement(csv_text, bank="HDFC")

    assert transactions == [
        {
            "date": date(2026, 1, 5),
            "description": "STARBUCKS",
            "amount": 400.0,
            "type": "expense",
        },
        {
            "date": date(2026, 1, 6),
            "description": "UPWORK GLOBAL",
            "amount": 50000.0,
            "type": "income",
        },
    ]


def test_categorizer_maps_known_merchants_and_income():
    assert categorize_transaction("STARBUCKS", "expense") == "Food"
    assert categorize_transaction("LINKEDIN ADS", "expense") == "Marketing"
    assert categorize_transaction("FIGMA", "expense") == "Software"
    assert categorize_transaction("GOOGLE CLOUD", "expense") == "Software"
    assert categorize_transaction("UPWORK FREELANCE", "income") == "Freelance Income"


def test_report_calculates_profit_tax_and_breakdowns():
    transactions = [
        {"date": date(2026, 1, 1), "amount": 500000.0, "type": "income", "category": "Freelance Income"},
        {"date": date(2026, 1, 2), "amount": 100000.0, "type": "expense", "category": "Software"},
        {"date": date(2026, 2, 2), "amount": 50000.0, "type": "expense", "category": "Marketing"},
    ]

    report = build_report(transactions)

    assert report["revenue"] == 500000.0
    assert report["expenses"] == 150000.0
    assert report["profit"] == 350000.0
    assert report["tax_estimate"] == 17500.0
    assert report["expense_breakdown"] == {"Software": 100000.0, "Marketing": 50000.0}
    assert report["monthly_profit"][0] == {"month": "2026-01", "profit": 400000.0}


def test_tax_estimate_uses_mvp_slabs():
    assert estimate_tax(250000) == 0
    assert estimate_tax(500000) == 25000
    assert estimate_tax(900000) == 90000
    assert estimate_tax(1200000) == 240000


def test_chat_answers_financial_questions_from_transactions():
    transactions = [
        {"date": date(2026, 1, 1), "description": "STARBUCKS", "amount": 400.0, "type": "expense", "category": "Food"},
        {"date": date(2026, 1, 2), "description": "GOOGLE CLOUD", "amount": 2000.0, "type": "expense", "category": "Software"},
        {"date": date(2026, 1, 3), "description": "CLIENT PAYMENT", "amount": 100000.0, "type": "income", "category": "Freelance Income"},
    ]

    assert "₹400" in answer_financial_question("How much did I spend on food?", transactions)
    assert "GOOGLE CLOUD" in answer_financial_question("What was my biggest expense?", transactions)
    assert "₹97,600" in answer_financial_question("How much profit did I make?", transactions)
    assert "Software" in answer_financial_question("What category costs the most?", transactions)
