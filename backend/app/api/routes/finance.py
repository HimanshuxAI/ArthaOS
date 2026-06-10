from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.encryption import decrypt_financial_text, encrypt_financial_text
from app.models import AIInsight, Budget, FinancialScore, Forecast, Goal, Notification, Report, Subscription, Transaction, User
from app.schemas.finance import (
    BudgetCreate,
    BudgetOut,
    ChatIn,
    ChatOut,
    DashboardOut,
    GoalCreate,
    GoalOut,
    MetricOut,
    NotificationOut,
    TransactionOut,
    UploadOut,
)
from app.services.ai import enhance_answer_with_llm
from app.services.audit import log_audit
from app.services.categorizer import categorize_transaction
from app.services.chat import answer_financial_question
from app.services.finance import build_report
from app.services.intelligence import analyze_finances
from app.services.parser import StatementParseError, parse_statement
from app.services.pdf import build_monthly_report_pdf, build_pl_pdf

router = APIRouter(tags=["finance"])
SUPPORTED_BANKS = {"HDFC", "SBI", "ICICI", "AXIS"}


def _user_transactions(db: Session, user_id: int) -> list[Transaction]:
    return db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.date.desc(), Transaction.id.desc()).all()


def _transaction_dicts(rows: list[Transaction]) -> list[dict]:
    return [
        {"date": row.date, "description": decrypt_financial_text(row.description), "amount": row.amount, "type": row.type, "category": row.category}
        for row in rows
    ]


def _cash_reserve(transactions: list[dict]) -> float:
    return max(0, sum(float(tx["amount"]) if tx["type"] == "income" else -float(tx["amount"]) for tx in transactions))


def _budget_dicts(db: Session, user_id: int) -> list[dict]:
    return [
        {"id": row.id, "category": row.category, "monthly_limit": row.monthly_limit, "period": row.period}
        for row in db.query(Budget).filter(Budget.user_id == user_id).all()
    ]


def _goal_dicts(db: Session, user_id: int) -> list[dict]:
    return [
        {
            "id": row.id,
            "name": row.name,
            "target_amount": row.target_amount,
            "current_amount": row.current_amount,
            "category": row.category,
            "due_date": row.due_date,
            "status": row.status,
        }
        for row in db.query(Goal).filter(Goal.user_id == user_id).all()
    ]


def _transaction_out(row: Transaction) -> TransactionOut:
    return TransactionOut(
        id=row.id,
        date=row.date,
        description=decrypt_financial_text(row.description),
        amount=row.amount,
        type=row.type,
        category=row.category,
        created_at=row.created_at,
    )


def _intelligence(db: Session, user_id: int, transactions: list[dict]) -> dict:
    return analyze_finances(transactions, budgets=_budget_dicts(db, user_id), goals=_goal_dicts(db, user_id), cash_reserve=_cash_reserve(transactions))


def _materialize_intelligence(db: Session, user_id: int, intelligence: dict) -> None:
    for model in (FinancialScore, Subscription, Forecast, AIInsight, Notification):
        db.query(model).filter(model.user_id == user_id).delete()

    score = intelligence["health_score"]
    db.add(FinancialScore(user_id=user_id, score=score["score"], label=score["label"], factors=score["factors"], explanation=score["explanation"]))
    forecast = intelligence["forecast"]
    db.add(Forecast(user_id=user_id, **forecast))
    for item in intelligence["subscriptions"]:
        db.add(
            Subscription(
                user_id=user_id,
                merchant=item["merchant"],
                category=item["category"],
                monthly_cost=item["monthly_cost"],
                annual_cost=item["annual_cost"],
                renewal_alert=item["renewal_alert"],
            )
        )
    for insight in intelligence["insights"]:
        db.add(AIInsight(user_id=user_id, **insight))
    for notification in intelligence["notifications"]:
        db.add(Notification(user_id=user_id, **notification))


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardOut:
    rows = _user_transactions(db, current_user.id)
    txs = _transaction_dicts(rows)
    report = build_report(txs)
    intelligence = _intelligence(db, current_user.id, txs)
    return DashboardOut(
        metrics=MetricOut(**{key: report[key] for key in ("revenue", "expenses", "profit", "tax_estimate")}),
        kpis=intelligence["kpis"],
        health_score=intelligence["health_score"],
        revenue_analytics=intelligence["revenue_analytics"],
        expense_analytics=intelligence["expense_analytics"],
        cash_flow=intelligence["cash_flow"],
        forecast=intelligence["forecast"],
        insights=intelligence["insights"],
        notifications=intelligence["notifications"],
        subscriptions=intelligence["subscriptions"],
        budget_progress=intelligence["budget_progress"],
        goal_progress=intelligence["goal_progress"],
        revenue_trend=report["revenue_trend"],
        expense_breakdown=report["expense_breakdown"],
        monthly_profit=intelligence["monthly_profit"],
        transactions=[_transaction_out(row) for row in rows],
    )


@router.post("/upload", response_model=UploadOut)
async def upload_statement(
    bank: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadOut:
    normalized_bank = bank.upper()
    suffix = Path(file.filename or "").suffix.lower()
    if normalized_bank not in SUPPORTED_BANKS:
        raise HTTPException(status_code=400, detail="Supported banks: HDFC, SBI, ICICI, Axis")
    if suffix not in {".csv", ".pdf"}:
        raise HTTPException(status_code=400, detail="Only CSV and PDF files are supported")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File is too large. Maximum size is 10MB.")

    settings = get_settings()
    path = settings.upload_dir / f"{current_user.id}-{uuid4().hex}{suffix}"
    path.write_bytes(content)

    try:
        parsed = parse_statement(path, normalized_bank)
    except StatementParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    for item in parsed:
        description = item["description"]
        db.add(
            Transaction(
                user_id=current_user.id,
                date=item["date"],
                description=encrypt_financial_text(description),
                amount=item["amount"],
                type=item["type"],
                category=categorize_transaction(description, item["type"]),
            )
        )
    db.commit()

    rows = _user_transactions(db, current_user.id)
    txs = _transaction_dicts(rows)
    report_data = build_report(txs)
    intelligence = _intelligence(db, current_user.id, txs)
    report = Report(
        user_id=current_user.id,
        revenue=report_data["revenue"],
        expenses=report_data["expenses"],
        profit=report_data["profit"],
        tax_estimate=report_data["tax_estimate"],
    )
    db.add(report)
    _materialize_intelligence(db, current_user.id, intelligence)
    log_audit(db, current_user.id, "statement.uploaded", "transactions", {"imported": len(parsed), "bank": normalized_bank})
    db.commit()
    return UploadOut(imported=len(parsed), report=MetricOut(**{key: report_data[key] for key in ("revenue", "expenses", "profit", "tax_estimate")}))


@router.post("/chat", response_model=ChatOut)
async def chat(payload: ChatIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ChatOut:
    rows = _user_transactions(db, current_user.id)
    txs = _transaction_dicts(rows)
    deterministic = answer_financial_question(payload.message, txs, cash_reserve=_cash_reserve(txs))
    report = build_report(txs)
    log_audit(db, current_user.id, "cfo_chat.asked", "chat", {"message_length": len(payload.message)})
    db.commit()
    answer = await enhance_answer_with_llm(payload.message, deterministic, report)
    return ChatOut(answer=answer)


@router.get("/reports/latest.pdf")
def latest_report_pdf(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    rows = _user_transactions(db, current_user.id)
    report = build_report(_transaction_dicts(rows))
    log_audit(db, current_user.id, "report.exported", "reports", {"type": "pl"})
    db.commit()
    return Response(
        content=build_pl_pdf(report),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="arthaos-profit-loss.pdf"'},
    )


@router.get("/analytics")
def analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = _user_transactions(db, current_user.id)
    txs = _transaction_dicts(rows)
    return _intelligence(db, current_user.id, txs)


@router.get("/forecasts")
def forecasts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = _user_transactions(db, current_user.id)
    return _intelligence(db, current_user.id, _transaction_dicts(rows))["forecast"]


@router.get("/subscriptions")
def subscriptions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = _user_transactions(db, current_user.id)
    return _intelligence(db, current_user.id, _transaction_dicts(rows))["subscriptions"]


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[NotificationOut]:
    rows = _user_transactions(db, current_user.id)
    generated = _intelligence(db, current_user.id, _transaction_dicts(rows))["notifications"]
    return [NotificationOut(**item) for item in generated]


@router.get("/budgets", response_model=list[BudgetOut])
def budgets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[BudgetOut]:
    rows = _user_transactions(db, current_user.id)
    intelligence = _intelligence(db, current_user.id, _transaction_dicts(rows))
    return [BudgetOut(**item) for item in intelligence["budget_progress"]]


@router.post("/budgets", response_model=BudgetOut, status_code=201)
def create_budget(payload: BudgetCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> BudgetOut:
    budget = Budget(user_id=current_user.id, category=payload.category, monthly_limit=payload.monthly_limit, period=payload.period)
    db.add(budget)
    log_audit(db, current_user.id, "budget.created", "budgets", {"category": payload.category})
    db.commit()
    db.refresh(budget)
    rows = _user_transactions(db, current_user.id)
    progress = _intelligence(db, current_user.id, _transaction_dicts(rows))["budget_progress"]
    item = next((row for row in progress if row["id"] == budget.id), {"id": budget.id, "category": budget.category, "monthly_limit": budget.monthly_limit, "period": budget.period})
    return BudgetOut(**item)


@router.get("/goals", response_model=list[GoalOut])
def goals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[GoalOut]:
    rows = _user_transactions(db, current_user.id)
    intelligence = _intelligence(db, current_user.id, _transaction_dicts(rows))
    return [GoalOut(**item) for item in intelligence["goal_progress"]]


@router.post("/goals", response_model=GoalOut, status_code=201)
def create_goal(payload: GoalCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GoalOut:
    goal = Goal(
        user_id=current_user.id,
        name=payload.name,
        target_amount=payload.target_amount,
        category=payload.category,
        due_date=payload.due_date,
    )
    db.add(goal)
    log_audit(db, current_user.id, "goal.created", "goals", {"name": payload.name})
    db.commit()
    db.refresh(goal)
    rows = _user_transactions(db, current_user.id)
    progress = _intelligence(db, current_user.id, _transaction_dicts(rows))["goal_progress"]
    item = next(
        (row for row in progress if row["id"] == goal.id),
        {
            "id": goal.id,
            "name": goal.name,
            "target_amount": goal.target_amount,
            "current_amount": goal.current_amount,
            "category": goal.category,
            "due_date": goal.due_date,
            "status": goal.status,
        },
    )
    return GoalOut(**item)


@router.get("/reports/monthly.pdf")
def monthly_report_pdf(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    rows = _user_transactions(db, current_user.id)
    txs = _transaction_dicts(rows)
    report = build_report(txs)
    intelligence = _intelligence(db, current_user.id, txs)
    log_audit(db, current_user.id, "report.exported", "reports", {"type": "monthly"})
    db.commit()
    return Response(
        content=build_monthly_report_pdf(report, intelligence),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="arthaos-monthly-cfo-report.pdf"'},
    )
