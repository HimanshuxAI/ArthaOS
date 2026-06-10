import io
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import Base, engine
from app.main import app


def test_user_can_register_upload_csv_view_dashboard_and_export_pdf(tmp_path):
    settings = get_settings()
    settings.upload_dir = tmp_path
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    auth_response = client.post(
        "/api/v1/auth/register",
        json={"name": "Aarav Mehta", "email": "aarav@example.com", "password": "strongpass123"},
    )
    assert auth_response.status_code == 201
    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    csv_bytes = b"Date,Narration,Debit,Credit\n2026-01-05,STARBUCKS,400,\n2026-01-06,UPWORK GLOBAL,,50000\n"
    upload_response = client.post(
        "/api/v1/upload",
        data={"bank": "HDFC"},
        files={"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=headers,
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["imported"] == 2

    dashboard = client.get("/api/v1/dashboard", headers=headers)
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["metrics"]["revenue"] == 50000
    assert body["metrics"]["expenses"] == 400
    assert body["metrics"]["profit"] == 49600
    assert body["kpis"]["cash_flow"] == 49600
    assert "health_score" in body
    assert "forecast" in body
    assert body["transactions"][0]["category"] == "Freelance Income"

    chat = client.post("/api/v1/chat", json={"message": "How much did I spend on food?"}, headers=headers)
    assert chat.status_code == 200
    assert "₹400" in chat.json()["answer"]

    pdf = client.get("/api/v1/reports/latest.pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    assert any(Path(tmp_path).iterdir())

    budget = client.post(
        "/api/v1/budgets",
        json={"category": "Food", "monthly_limit": 10000, "period": "monthly"},
        headers=headers,
    )
    assert budget.status_code == 201
    assert budget.json()["category"] == "Food"

    goal = client.post(
        "/api/v1/goals",
        json={"name": "Emergency Fund", "target_amount": 250000, "category": "Emergency Fund"},
        headers=headers,
    )
    assert goal.status_code == 201
    assert goal.json()["progress_percent"] >= 0

    assert client.get("/api/v1/analytics", headers=headers).status_code == 200
    assert client.get("/api/v1/forecasts", headers=headers).status_code == 200
    assert client.get("/api/v1/subscriptions", headers=headers).status_code == 200
    assert client.get("/api/v1/notifications", headers=headers).status_code == 200
