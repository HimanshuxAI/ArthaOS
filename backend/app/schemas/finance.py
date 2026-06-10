from datetime import date, datetime

from pydantic import BaseModel, Field


class TransactionOut(BaseModel):
    id: int
    date: date
    description: str
    amount: float
    type: str
    category: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MetricOut(BaseModel):
    revenue: float
    expenses: float
    profit: float
    tax_estimate: float


class DashboardOut(BaseModel):
    metrics: MetricOut
    kpis: dict
    health_score: dict
    revenue_analytics: dict
    expense_analytics: dict
    cash_flow: dict
    forecast: dict
    insights: list[dict]
    notifications: list[dict]
    subscriptions: list[dict]
    budget_progress: list[dict]
    goal_progress: list[dict]
    revenue_trend: list[dict]
    expense_breakdown: dict[str, float]
    monthly_profit: list[dict]
    transactions: list[TransactionOut]


class UploadOut(BaseModel):
    imported: int
    report: MetricOut


class ChatIn(BaseModel):
    message: str


class ChatOut(BaseModel):
    answer: str


class BudgetCreate(BaseModel):
    category: str = Field(min_length=2, max_length=80)
    monthly_limit: float = Field(gt=0)
    period: str = Field(default="monthly", pattern="^(monthly)$")


class BudgetOut(BaseModel):
    id: int
    category: str
    monthly_limit: float
    period: str
    spent: float = 0
    remaining: float = 0
    progress_percent: float = 0


class GoalCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    target_amount: float = Field(gt=0)
    category: str = Field(default="General", max_length=80)
    due_date: date | None = None


class GoalOut(BaseModel):
    id: int
    name: str
    target_amount: float
    current_amount: float
    category: str
    due_date: date | None
    status: str
    progress_percent: float = 0


class NotificationOut(BaseModel):
    id: int | None = None
    type: str
    title: str
    message: str
    severity: str
    read: bool = False
