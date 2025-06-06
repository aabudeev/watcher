# Watcher

## Цели проекта

Система Watcher предназначена для мониторинга данных токенов блокчейна, обработки финансовой информации и предоставления своевременных обновлений через интерфейс Telegram-бота. Основные цели:
- Автоматизация сбора и обработки данных токенов.
- Предоставление аналитики о производительности токенов (например, процент прибыли/убытков, рыночная капитализация и объем торгов).
- Обеспечение администраторам системы инструментов для мониторинга и управления в реальном времени через Telegram-бот.

---

## Общее описание системы

Система организована в виде модульного конвейера, состоящего из следующих ключевых компонентов:

1. **Главное приложение Watcher (`watcher.py`)**
   - **Назначение**: Является точкой входа для системы. Инициализирует все компоненты, включая базу данных, Telegram-бота и планировщик, и запускает главный цикл событий.
   - **Ключевые функции**:
     - `initialize_application`: Настраивает Telegram-бота и его обработчики команд.
     - `setup_scheduler`: Настраивает периодические задачи для сбора и обработки данных токенов.
     - `run_main_loop`: Координирует жизненный цикл приложения.
   - **Взаимодействия**:
     - Взаимодействует с модулями `DatabaseOperations`, `Config`, `Scheduler` и `TelegramBot`.
     - Управляет жизненным циклом Telegram-бота и планировщика.

2. **Модуль утилит (`watcher_utility.py`)**
   - **Назначение**: Предоставляет вспомогательные функции для логирования, управления временем, форматирования данных и финансовых расчетов.
   - **Ключевые функции**:
     - `setup_logging`: Настраивает логирование с использованием ротации файлов.
     - `get_pnl`: Рассчитывает проценты прибыли/убытков.
     - `simplify`: Упрощает большие числовые значения для удобочитаемости.
     - `get_worth`: Вычисляет общую стоимость покупки, текущую стоимость и PnL (прибыль/убытки).
   - **Взаимодействия**: Используется во всех модулях для общих задач, таких как логирование и обработка данных.

3. **Модуль конфигурации (`watcher_config.py`)**
   - **Назначение**: Управляет настройками системы, включая параметры базы данных, прокси SOCKS5 и учетные данные Telegram API.
   - **Ключевые особенности**:
     - Шифрует и расшифровывает конфиденциальные данные с использованием `cryptography.Fernet`.
     - Асинхронно инициализирует параметры конфигурации из базы данных MongoDB.
   - **Взаимодействия**: Используется главным приложением и другими модулями, которые требуют параметры конфигурации.

4. **Операции с базой данных (`watcher_database.py`)**
   - **Назначение**: Обрабатывает все взаимодействия с базой данных MongoDB для хранения и извлечения данных токенов.
   - **Ключевые функции**:
     - `add_entry`: Добавляет новые записи в базу данных.
     - `get_latest_entry`: Извлекает самые последние данные.
     - `get_latest_gas_price`: Получает последнюю цену газа.
   - **Взаимодействия**: Используется модулями `Scheduler` и `TelegramBot` для доступа и хранения данных.

5. **HTTP-запросы (`watcher_requests.py`)**
   - **Назначение**: Выполняет HTTP-запросы для получения данных токенов и цен на газ, а также отправляет сообщения или файлы через Telegram.
   - **Ключевые функции**:
     - `make_request`: Обрабатывает HTTP-запросы с логикой повторных попыток и использованием прокси SOCKS5 (при необходимости).
     - `send_message`: Отправляет сообщения в Telegram с использованием Bot API.
     - `get_token_data`: Получает данные токенов из API, связанных с блокчейном.
   - **Взаимодействия**: Используется модулями `Scheduler` и `TelegramBot` для внешней связи.

6. **Планировщик (`watcher_scheduler.py`)**
   - **Назначение**: Организует периодический сбор и обработку данных токенов.
   - **Ключевые функции**:
     - `merge_chain_addr`: Объединяет адреса токенов по их блокчейнам.
     - `collect`: Собирает, обрабатывает и сохраняет данные токенов.
   - **Взаимодействия**: Работает с модулями `Config`, `DatabaseOperations` и `Requests`.

7. **Telegram-бот (`watcher_telegram_bot.py`)**
   - **Назначение**: Предоставляет интерфейс для администраторов для взаимодействия с системой через Telegram.
   - **Ключевые особенности**:
     - Поддерживает команды `/help`, `/gas`, `/info`, `/restart`.
     - Обрабатывает нажатия кнопок для различных функций.
     - Уведомляет администраторов о несанкционированных попытках доступа.
   - **Взаимодействия**: Непосредственно взаимодействует с модулями `Requests` и `DatabaseOperations`.

---

## Ключевые процессы и алгоритмы

### 1. **Сбор и обработка данных**
   - **Процесс**:
     - Метод `Scheduler.collect` объединяет адреса токенов, получает данные токенов и вычисляет финансовые метрики, такие как прибыль/убытки (PnL).
     - Данные анализируются и проверяются перед сохранением в базу данных.
   - **Алгоритм**:
     - Получение данных токенов из внешних API.
     - Объединение данных конфигурации с полученными данными.
     - Вычисление финансовых метрик с использованием утилит.
     - Генерация отчета при обнаружении значительных изменений.

### 2. **Взаимодействие с Telegram-ботом**
   - **Процесс**:
     - Бот слушает команды администратора или нажатия кнопок.
     - В зависимости от ввода, извлекает данные из базы данных или запускает действия, такие как перезапуск системы.
   - **Алгоритм**:
     - Проверка прав доступа пользователя.
     - Выполнение соответствующего обработчика команд (например, `handle_info` для получения сводной информации, `handle_restart` для перезапуска приложения).

### 3. **Логирование и обработка ошибок**
   - **Процесс**:
     - Логи создаются для всех значимых событий, включая ошибки, этапы обработки данных и взаимодействия с пользователем.
   - **Алгоритм**:
     - Использование ротации файлов для управления логами.
     - Фильтрация записей логов для включения названий функций для улучшения трассировки.

---

## Описание модулей и взаимодействия

| **Модуль**        | **Описание**                                                                 | **Взаимодействует с**                   |
|--------------------|-----------------------------------------------------------------------------|-----------------------------------------|
| `watcher.py`       | Главное приложение; инициализирует и запускает компоненты.                   | Все модули                              |
| `utility.py`       | Предоставляет вспомогательные функции для логирования, форматирования и расчетов. | Используется во всех модулях.          |
| `config.py`        | Управляет настройками приложения и шифрованием конфиденциальных данных.      | `watcher.py`, `Scheduler`, `Requests`.  |
| `database.py`      | Обрабатывает операции с базой данных для хранения и извлечения данных токенов. | `Scheduler`, `TelegramBot`.             |
| `requests.py`      | Выполняет HTTP-запросы и обрабатывает отправку сообщений в Telegram.         | `Scheduler`, `TelegramBot`.             |
| `scheduler.py`     | Периодически собирает, обрабатывает и отправляет данные токенов.             | `Config`, `DatabaseOperations`, `Requests`. |
| `telegramBot.py`   | Реализует команды Telegram-бота и обработку нажатий кнопок.                 | `Requests`, `DatabaseOperations`.       |

---

## Выводы

Система Watcher успешно достигает своей цели автоматизации мониторинга данных блокчейна и предоставления обновлений в реальном времени через Telegram-бот. Модульная структура обеспечивает удобство сопровождения и расширения. Основные выводы:
- Эффективное использование асинхронного программирования для обработки задач в реальном времени.
- Безопасная обработка конфиденциальных данных с использованием шифрования.
- Комплексная обработка ошибок и логирование для надежной работы.

---

## Сводная информация и меню бота
![инфо](images/img_01.jpg)

## Репорт
![репорт](images/img_02.jpg)
