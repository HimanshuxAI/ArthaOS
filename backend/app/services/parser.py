import csv
import io
from datetime import date, datetime
from pathlib import Path

from pypdf import PdfReader

DATE_COLUMNS = ("date", "txn date", "transaction date", "value date")
DESCRIPTION_COLUMNS = ("description", "narration", "particulars", "details", "remarks")
DEBIT_COLUMNS = ("debit", "withdrawal", "withdrawals", "dr", "paid out")
CREDIT_COLUMNS = ("credit", "deposit", "deposits", "cr", "paid in")
AMOUNT_COLUMNS = ("amount", "transaction amount")
TYPE_COLUMNS = ("type", "transaction type", "dr/cr")


class StatementParseError(ValueError):
    pass


def _clean_money(value: str | None) -> float:
    if not value:
        return 0
    cleaned = value.replace(",", "").replace("₹", "").strip()
    if not cleaned:
        return 0
    return abs(float(cleaned))


def _parse_date(value: str) -> date:
    cleaned = value.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise StatementParseError(f"Unsupported date format: {value}")


def _find(row: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    normalized = {key.strip().lower(): value for key, value in row.items() if key}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def parse_csv_statement(csv_text: str, bank: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise StatementParseError("CSV has no header row")

    transactions = []
    for row in reader:
        raw_date = _find(row, DATE_COLUMNS)
        description = _find(row, DESCRIPTION_COLUMNS)
        if not raw_date or not description:
            continue

        debit = _clean_money(_find(row, DEBIT_COLUMNS))
        credit = _clean_money(_find(row, CREDIT_COLUMNS))
        amount_value = _clean_money(_find(row, AMOUNT_COLUMNS))
        raw_type = (_find(row, TYPE_COLUMNS) or "").lower()

        if credit:
            tx_type = "income"
            amount = credit
        elif debit:
            tx_type = "expense"
            amount = debit
        elif amount_value:
            tx_type = "income" if "cr" in raw_type or "credit" in raw_type else "expense"
            amount = amount_value
        else:
            continue

        transactions.append(
            {
                "date": _parse_date(raw_date),
                "description": description.strip(),
                "amount": amount,
                "type": tx_type,
            }
        )

    if not transactions:
        raise StatementParseError(f"No transactions found for {bank} statement")
    return transactions


def parse_pdf_statement(path: Path, bank: str) -> list[dict]:
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        raise StatementParseError("PDF text extraction failed. Upload a text-based PDF or CSV.")

    # MVP fallback: accept comma-separated rows embedded in text-based bank PDFs.
    csv_like_lines = [line for line in text.splitlines() if line.count(",") >= 3]
    if not csv_like_lines:
        raise StatementParseError("Could not detect tabular statement rows in PDF.")
    return parse_csv_statement("\n".join(csv_like_lines), bank)


def parse_statement(path: Path, bank: str) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return parse_csv_statement(path.read_text(encoding="utf-8-sig"), bank)
    if suffix == ".pdf":
        return parse_pdf_statement(path, bank)
    raise StatementParseError("Only CSV and PDF statements are supported")
