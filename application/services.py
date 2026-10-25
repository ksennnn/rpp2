from datetime import datetime, timedelta
from uuid import uuid4

from domain.loan import Loan
from domain.book import Book
from domain.reader import Reader
from domain.value_objects import BookId, CopyId, LoanId, LoanPeriod, ReaderId
from domain.exceptions import GatewayUnresolved, EntityNotFound
from domain.events import *

from application.ports import Clock
from infrastructure.memory import InMemoryBookRepository, InMemoryReaderRepository, InMemoryLoanRepository

class LendingProcess:
    def __init__(self, books: InMemoryBookRepository, readers: InMemoryReaderRepository, loans: InMemoryLoanRepository, clock: Clock):
        self._books = books
        self._readers = readers
        self._loans = loans
        self._clock = clock

    def check_reader_debt(self, reader_id: ReaderId) -> bool:
        return False

    def create_loan(self, book_id: BookId, reader_id: ReaderId, days: int = 14) -> Loan:
        book = self._books.get(book_id)
        reader = self._readers.get(reader_id)
        
        if self.check_reader_debt(reader_id):
            raise GatewayUnresolved("Читатель имеет задолженность")

        free_copies = [c for c in book.copies() if not c.on_loan]
        if not free_copies:
            raise GatewayUnresolved("Нет свободных экземпляров")
        
        copy_id = free_copies[0].id
        issue_date = self._clock.now().date()
        due_date = issue_date + timedelta(days=days)

        period = LoanPeriod(issue_date=issue_date, due_date=due_date)
        loan = Loan(LoanId(uuid4()), book.id, copy_id, reader.id, period, self._clock.now())
        
        # бронируем физический экземпляр
        book.checkout(copy_id) 
        self._books.save(book)
        self._loans.save(loan)
        return loan

    def issue_book(self, loan_id: LoanId):
        loan = self._loans.get(loan_id)
        # книга уже забронирована, просто меняем статус заявки
        loan.checkout(self._clock.now())
        self._loans.save(loan)

    def receive_book(self, loan_id: LoanId, is_damaged: bool):
        loan = self._loans.get(loan_id)
        book = self._books.get(loan.book_id)
        
        loan.return_book(self._clock.now(), is_damaged)
        
        # если есть штраф, списываем его через платежную систему
        if loan.fine.amount > 0:
            self._payments.charge(float(loan.fine.amount))
            
        book.return_copy(loan.copy_id)
        
        self._loans.save(loan)
        self._books.save(book)

    def on_expire_3d(self):
        for loan in self._loans.get_all():
            if "cancel" in loan.allowed_events:
                book = self._books.get(loan.book_id)
                book.return_copy(loan.copy_id)
                self._books.save(book)
                
                loan.cancel(self._clock.now())
                self._loans.save(loan)

    def on_expire_14d(self):
        now = self._clock.now()
        for loan in self._loans.get_all():
            if "expire_14d" in loan.allowed_events:
                # проверяем что прошло 14 дней или больше
                if now.date() > loan.period.due_date:
                    loan.expire_14d(now)
                    self._loans.save(loan)

    def on_expire_30d(self):
        now = self._clock.now()
        for loan in self._loans.get_all():
            if "expire_30d" in loan.allowed_events:
                # проверяем что прошло 30 дней с момента просрочки
                days_overdue = (now.date() - loan.period.due_date).days
                if days_overdue > 30:
                    loan.expire_30d(now)
                    self._loans.save(loan)
