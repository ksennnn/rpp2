# Лабораторная работа №5 — бонусная программа

Реализация микросервисного приложения с RabbitMQ direct/fanout, PostgreSQL и Docker Compose.

## Запуск

Требуется Docker Desktop / Docker Engine с Compose v2.

```bash
docker compose up --build -d
docker compose ps
```

API: http://localhost:8000/docs  
Notifier: http://localhost:8001/docs  
Analytics: http://localhost:8002/docs  
RabbitMQ Management: http://localhost:15672 (loyalty / loyalty)

Таблицы PostgreSQL автоматически создаются worker при старте через SQLAlchemy `metadata.create_all`.

## Пример работы

Покупка (5% от 2490 = 124 балла):

```bash
curl -X POST http://localhost:8000/operations -H 'Content-Type: application/json' -d '{"operation_id":"S12-K03-000154","type":"purchase","customer_id":"C1042","store_id":"S12","check_number":"S12-000154","amount":"2490.00","occurred_at":"2026-11-10T14:32:05+07:00"}'
```

Оплата баллами (не более 30% чека):

```bash
curl -X POST http://localhost:8000/operations -H 'Content-Type: application/json' -d '{"operation_id":"S12-K03-000155","type":"redeem","customer_id":"C1042","store_id":"S12","check_number":"S12-000154","amount":"500.00","points":100,"occurred_at":"2026-11-10T14:35:00+07:00"}'
```

Возврат покупки:

```bash
curl -X POST http://localhost:8000/operations -H 'Content-Type: application/json' -d '{"operation_id":"S12-K03-000156","type":"return","customer_id":"C1042","store_id":"S12","check_number":"S12-000154","occurred_at":"2026-11-10T15:00:00+07:00"}'
```

Проверка результатов:

```bash
curl http://localhost:8000/operations/S12-K03-000154
curl http://localhost:8000/accounts/C1042
curl 'http://localhost:8001/notifications?customer_id=C1042'
curl http://localhost:8001/stats
curl http://localhost:8002/stores
curl http://localhost:8002/stats
```

## Архитектура и очереди

- `loyalty` — durable direct exchange; `operations` — durable quorum queue, routing key `operation`.
- `loyalty.events` — durable fanout exchange; очереди `notifier.events` и `analytics.events` — durable quorum.
- Worker обрабатывает сообщения последовательно (`prefetch_count=1`), фиксирует транзакцию PostgreSQL, затем публикует событие с publisher confirms и подтверждает входящее сообщение.
- Уведомления и аналитика хранят агрегаты в памяти и очищаются после перезапуска соответствующего сервиса.

## Важные замечания

1. `UNSUBSCRIBED` задаётся списком customer_id через запятую в переменной окружения notifier.
2. Для учебного стенда логин/пароль `loyalty` демонстрационные; перед реальным использованием замените их.
3. После `docker compose down -v` тома с данными удаляются.
4. В RabbitMQ Management откройте вкладки Exchanges и Queues и сделайте скриншоты для отчёта.
5. Формат входных данных проверяет API; бизнес-правила и причины отказа обрабатываются worker.


