import os
from datetime import datetime
from flask import Flask, request, jsonify
from uuid import UUID

from domain.exceptions import TransitionNotAllowed, DomainInvariantViolation, EntityNotFound, GatewayUnresolved, InvalidValueObject
from infrastructure.memory import ShiftedClock, InMemoryBookRepository, InMemoryReaderRepository, InMemoryLoanRepository
from application.services import LendingProcess
from domain.value_objects import BookId, ReaderId, LoanId, ISBN

# импортируем агрегаты для создания тестовых данных
from domain.book import Book
from domain.reader import Reader

app = Flask(__name__)

# инициализация зависимостей
clock = ShiftedClock()
books = InMemoryBookRepository()
readers = InMemoryReaderRepository()
loans = InMemoryLoanRepository()
service = LendingProcess(books, readers, loans, clock)

# генерация тестовых данных (SEED) 
# создаем 3 книги и 1 читателя чтобы было с чем тестировать
BOOK_ID = "11111111-1111-1111-1111-111111111111"
READER_ID = "22222222-2222-2222-2222-222222222222"

seed_book = Book(BookId(UUID(BOOK_ID)), "Тестовая книга", "Тестовый автор", ISBN("1234567890"))
seed_book.add_copy()
seed_book.add_copy() # 2 экземпляр
seed_book.add_copy() # 3 экземпляр
books.save(seed_book)

seed_reader = Reader(ReaderId(UUID(READER_ID)), "Тестовый читатель", "test@test.com")
readers.save(seed_reader)

# глобальные обработчики 
@app.errorhandler(TransitionNotAllowed)
def handle_transition(e): return jsonify({"error": "transition_not_allowed", "message": str(e)}), 409

@app.errorhandler(DomainInvariantViolation)
def handle_invariant(e): return jsonify({"error": "invariant_violation", "message": str(e)}), 422

@app.errorhandler(EntityNotFound)
def handle_not_found(e): return jsonify({"error": "not_found", "message": str(e)}), 404

@app.errorhandler(GatewayUnresolved)
def handle_gateway(e): return jsonify({"error": "gateway_unresolved", "message": str(e)}), 500

@app.errorhandler(ValueError)
def handle_value(e): return jsonify({"error": "invalid_data", "message": str(e)}), 422

@app.errorhandler(InvalidValueObject)
def handle_vo(e): return jsonify({"error": "invalid_data", "message": str(e)}), 422

# маршруты 
@app.route('/health', methods=['GET'])
def health(): return jsonify({"status": "ok"}), 200

# чтобы удобно посмотреть какие id сгенерировались
@app.route('/debug/seed', methods=['GET'])
def get_seed():
    return jsonify({
        "book_id": BOOK_ID,
        "reader_id": READER_ID
    })

@app.route('/loans/<loan_id>', methods=['GET'])
def get_loan(loan_id):
    loan = loans.get(LoanId(UUID(loan_id)))
    return jsonify({
        "id": str(loan.id.value),
        "status": loan.status,
        "allowed_events": list(loan.allowed_events),
        "journal": [str(ev) for ev in loan.events]
    })

@app.route('/loans', methods=['POST'])
def create_loan():
    data = request.json
    if not data or 'book_id' not in data or 'reader_id' not in data:
        raise ValueError("Неверные данные. Нужны book_id и reader_id")
    
    loan = service.create_loan(BookId(UUID(data['book_id'])), ReaderId(UUID(data['reader_id'])))
    return jsonify({"loan_id": str(loan.id.value), "status": loan.status}), 201

@app.route('/loans/<loan_id>/issue', methods=['POST'])
def issue(loan_id):
    service.issue_book(LoanId(UUID(loan_id)))
    return jsonify({"status": "ok"}), 200

@app.route('/loans/<loan_id>/return', methods=['POST'])
def return_book(loan_id):
    data = request.json or {}
    service.receive_book(LoanId(UUID(loan_id)), data.get('is_damaged', False))
    return jsonify({"status": "ok"}), 200

@app.route('/internal/tick', methods=['POST'])
def tick():
    data = request.json or {}
    if "now" in data:
        target_time = datetime.fromisoformat(data["now"])
        try:
            clock.set_time(target_time)
        except ValueError as e:
            return jsonify({"error": "clock_moved_back", "message": str(e)}), 422
    
    service.on_expire_3d()
    service.on_expire_14d()
    service.on_expire_30d()
    return jsonify({"status": "time_advanced", "current_time": str(clock.now())}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))
