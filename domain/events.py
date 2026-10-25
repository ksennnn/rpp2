from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class LoanCreated:
    loan_id: str
    occurred_at: datetime

@dataclass(frozen=True)
class BookIssued:
    loan_id: str
    occurred_at: datetime

@dataclass(frozen=True)
class BookReturned:
    loan_id: str
    fine_amount: float
    is_damaged: bool
    occurred_at: datetime

@dataclass(frozen=True)
class LoanCancelled:
    loan_id: str
    occurred_at: datetime

@dataclass(frozen=True)
class LoanOverdue:
    loan_id: str
    occurred_at: datetime

@dataclass(frozen=True)
class LoanBlocked:
    loan_id: str
    occurred_at: datetime
