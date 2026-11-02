# Chicken Shop — Backend

FastAPI + PostgreSQL backend для мобильного сайта по продаже курицы.
Реализован полный флоу: товары → слоты доставки → заказ → оплата → вебхук →
уведомление в Telegram + админ-панель (SQLAdmin) с экспортом в Excel.

Код полностью протестирован end-to-end (создание заказа → инициация оплаты →
вебхук → статус paid → админка → экспорт) перед выдачей.

## Быстрый запуск (Docker)

```bash
cp .env.example .env
# отредактировать .env: указать пароли, токен Telegram-бота, ключи платёжного провайдера
docker compose up --build
```

После запуска:
- API: http://localhost:8000/docs (Swagger)
- Админка: http://localhost:8000/admin (логин/пароль из .env)
- Экспорт заказов: http://localhost:8000/admin/orders/export (после логина в админку)

## Применение миграций

```bash
docker compose exec app alembic revision --autogenerate -m "init"
docker compose exec app alembic upgrade head
```

## Запуск без Docker (для разработки)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# указать DATABASE_URL на локальный/удалённый Postgres

alembic revision --autogenerate -m "init"
alembic upgrade head

uvicorn app.main:app --reload
```

## Структура

```
app/
├── main.py              # сборка FastAPI-приложения, роуты, админка
├── core/
│   ├── config.py         # настройки из .env
│   └── database.py       # async engine/session, Base
├── models/                # SQLAlchemy-модели (product, order, customer)
├── schemas/                # Pydantic-схемы запросов/ответов
├── api/
│   ├── products.py         # GET /api/products
│   ├── delivery.py         # GET /api/delivery-slots
│   ├── orders.py            # POST /api/orders, GET /api/orders/{id}
│   └── payments.py           # POST /api/payments/init, /webhook
├── services/
│   ├── payment_service.py    # интерфейс провайдера оплаты + DummyProvider
│   ├── telegram_service.py    # отправка уведомления о заказе
│   ├── excel_export.py         # экспорт заказов в Excel
│   └── scheduler.py             # автоотмена зависших неоплаченных заказов
└── admin/
    ├── auth.py             # логин/пароль для SQLAdmin
    └── views.py              # ModelView'ы + роут экспорта
```

## Что нужно донастроить перед продакшеном

1. **Платёжный провайдер** — в `app/services/payment_service.py` сейчас
   подключён `DummyProvider` (заглушка для разработки). Нужно реализовать
   класс под конкретного провайдера (Kaspi/CloudPayments/др.) по образцу
   `PaymentProvider`, реализовав `init_payment()` и `verify_and_parse_webhook()`
   по документации провайдера, и прописать его в `get_payment_provider()`.
2. **Telegram-бот** — создать бота через @BotFather, получить `TELEGRAM_BOT_TOKEN`,
   добавить бота в чат/канал и получить `TELEGRAM_CHAT_ID` (например через
   `https://api.telegram.org/bot<TOKEN>/getUpdates` после отправки любого сообщения в чат).
3. **CORS** — в `main.py` сейчас `allow_origins=["*"]`, на проде сузить до домена фронтенда.
4. **ADMIN_SECRET_KEY, ADMIN_PASSWORD** — обязательно заменить на случайные значения перед деплоем.
5. При необходимости ограничивать число заказов на слот доставки — добавить
   таблицу `delivery_slots` с капасити (см. комментарий в `app/api/delivery.py`).
