# Фудграм 

## Как запустить проект локально (через Docker)

1.  **Клонируй репозиторий:**:
    ```bash
    git clone https://github.com/Instmois/foodgram-st
    cd foodgram-st
    ```

2.  **Создай файл `.env`:** В **корневой папке** проекта (там, где `requirements.txt`, `Dockerfile`) создай файл с именем `.env`. Скопируй туда вот это и оставь как есть:
    ```dotenv
    # .env
    POSTGRES_DB=postgres
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=postgres
    DB_HOST=db
    DB_PORT=5432
    ```

3.  **Запусти Docker Compose:** Перейди в папку `infra` и выполни команду:
    ```bash
    cd infra
    docker compose up --build
    ```

4.  **Готово!**
    *   **Сайт:** [http://localhost/](http://localhost/)
    *   **Админка:** [http://localhost/admin/](http://localhost/admin/) 
    *   **API Документация:** [http://localhost/api/docs/](http://localhost/api/docs/)

5.  **Создай суперюзера (если база чистая):** Открой *другой* терминал (не закрывая тот, где работает `docker compose`), перейди в папку `infra` и выполни:
    ```bash
    docker compose exec backend python backend/manage.py createsuperuser
    ```
    Следуй инструкциям, чтобы создать админа.