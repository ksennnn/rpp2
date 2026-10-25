from dataclasses import dataclass
from uuid import uuid4

from .exceptions import DomainInvariantViolation, EntityNotFound
from .value_objects import BookId, CopyId, ISBN

@dataclass
class Copy:
    """Внутренняя сущность агрегата Book. Снаружи недоступна напрямую"""

    id: CopyId
    on_loan: bool = False

class Book:
    """
    Агрегат Book. Корень агрегата.
    Хранит метаданные книги и список экземпляров.
    Инкапсулирует инварианты: количество выданных ≤ общего количества;
    экземпляр не может быть выдан дважды.
    """

    def __init__(self, book_id: BookId, title: str, author: str, isbn: ISBN):
        if not title.strip():
            raise DomainInvariantViolation("Название книги не может быть пустым")
        if not author.strip():
            raise DomainInvariantViolation("Автор не может быть пустым")

        self._id = book_id
        self._title = title
        self._author = author
        self._isbn = isbn
        self._copies: list[Copy] = []

    # только чтение, без сеттеров 
    @property
    def id(self) -> BookId:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def author(self) -> str:
        return self._author

    @property
    def isbn(self) -> ISBN:
        return self._isbn

    def copies(self) -> tuple[Copy, ...]:
        return tuple(self._copies)

    # изменение состояния только через методы корня 
    def add_copy(self) -> CopyId:
        copy = Copy(id=CopyId(uuid4()))
        self._copies.append(copy)
        return copy.id

    def available_count(self) -> int:
        return sum(1 for c in self._copies if not c.on_loan)

    def _get_copy(self, copy_id: CopyId) -> Copy:
        for c in self._copies:
            if c.id == copy_id:
                return c
        raise EntityNotFound(f"Экземпляр {copy_id.value} не найден в книге")

    def checkout(self, copy_id: CopyId) -> None:
        """
        Инвариант 1: нельзя взять книгу, если нет свободных экземпляров.
        Дополнительно: конкретный экземпляр не может быть выдан дважды.
        """
        if self.available_count() <= 0:
            raise DomainInvariantViolation(
                "Нельзя выдать книгу: нет свободных экземпляров"
            )
        copy = self._get_copy(copy_id)
        if copy.on_loan:
            raise DomainInvariantViolation(
                "Этот экземпляр уже выдан другому читателю"
            )
        copy.on_loan = True

    def return_copy(self, copy_id: CopyId) -> None:
        copy = self._get_copy(copy_id)
        if not copy.on_loan:
            raise DomainInvariantViolation(
                "Нельзя вернуть экземпляр, который не выдан"
            )
        copy.on_loan = False
