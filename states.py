from domain.exceptions import TransitionNotAllowed

class LoanState:
    name = ""
    allowed_events = frozenset()

    def checkout(self, loan, now): raise TransitionNotAllowed(self.name, "checkout")
    def return_book(self, loan, now, is_damaged): raise TransitionNotAllowed(self.name, "return_book")
    def extend(self, loan, now, has_queue): raise TransitionNotAllowed(self.name, "extend")
    def cancel(self, loan, now): raise TransitionNotAllowed(self.name, "cancel")
    def expire_14d(self, loan, now): raise TransitionNotAllowed(self.name, "expire_14d")
    def expire_30d(self, loan, now): raise TransitionNotAllowed(self.name, "expire_30d")
    def reject(self, loan, now): raise TransitionNotAllowed(self.name, "reject")

class ReservedState(LoanState):
    name = "Забронирована"
    allowed_events = frozenset({"checkout", "cancel", "reject"})
    
    def checkout(self, loan, now):
        return IssuedState() 
    def cancel(self, loan, now):
        return CancelledState()
    def reject(self, loan, now):
        return RejectedState()

class IssuedState(LoanState):
    name = "Выдана"
    allowed_events = frozenset({"return_book", "extend", "expire_14d"})
    
    def return_book(self, loan, now, is_damaged):
        return ReturnedState()
    def extend(self, loan, now, has_queue):
        from domain.exceptions import DomainInvariantViolation
        if has_queue:
            raise DomainInvariantViolation("Нельзя продлить книгу: есть очередь")
        return self
    def expire_14d(self, loan, now):
        return OverdueState()

class OverdueState(LoanState):
    name = "Просрочена"
    allowed_events = frozenset({"return_book", "expire_30d"})
    
    def return_book(self, loan, now, is_damaged):
        return ReturnedState()
    def expire_30d(self, loan, now):
        return BlockedState()

class ReturnedState(LoanState):
    name = "Возвращена"
    allowed_events = frozenset()

class CancelledState(LoanState):
    name = "Отменена"
    allowed_events = frozenset()

class RejectedState(LoanState):
    name = "Отклонена"
    allowed_events = frozenset()

class BlockedState(LoanState):
    name = "Заблокирована"
    allowed_events = frozenset()
