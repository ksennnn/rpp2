from .exceptions import DomainInvariantViolation
from .value_objects import ReaderId

class Reader:
    """Агрегат Reader. Корень агрегата"""

    def __init__(self, reader_id: ReaderId, full_name: str, contacts: str):
        if not full_name.strip():
            raise DomainInvariantViolation("Имя читателя не может быть пустым")
        if not contacts.strip():
            raise DomainInvariantViolation("Контакты не могут быть пустыми")
        self._id = reader_id
        self._full_name = full_name
        self._contacts = contacts

    @property
    def id(self) -> ReaderId:
        return self._id

    @property
    def full_name(self) -> str:
        return self._full_name

    @property
    def contacts(self) -> str:
        return self._contacts

    def update_contacts(self, new_contacts: str) -> None:
        if not new_contacts.strip():
            raise DomainInvariantViolation("Контакты не могут быть пустыми")
        self._contacts = new_contacts
