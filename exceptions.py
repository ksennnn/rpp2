class DomainError(Exception):
    """Базовое доменное исключение"""

class DomainInvariantViolation(DomainError):
    """Нарушение инварианта агрегата"""

class InvalidValueObject(DomainError):
    """Некорректное значение объекта-значения"""

class EntityNotFound(DomainError):
    """Сущность не найдена в репозитории"""

class TransitionNotAllowed(DomainError):
    """Событие недопустимо в текущем состоянии"""
    def __init__(self, state: str, event: str):
        super().__init__(f"Событие '{event}' недопустимо в состоянии '{state}'")

class GatewayUnresolved(DomainError):
    """Ни одно условие шлюза не выполнено"""