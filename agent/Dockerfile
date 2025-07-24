# Этап сборки зависимостей
FROM python:3.12-slim AS builder

WORKDIR /app

# Установка uv
RUN pip install uv

# Копирование файлов зависимостей
COPY pyproject.toml uv.lock litellm-1.72.3-py3-none-any.whl ./

# Установка зависимостей в виртуальное окружение
RUN uv sync --frozen

# Этап создания финального образа
FROM python:3.12-slim AS runtime

WORKDIR /app

# Копирование виртуального окружения из этапа сборки
COPY --from=builder /app/.venv /app/.venv

# Активация виртуального окружения
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Копирование исходного кода приложения
COPY app ./app

# Команда для запуска приложения
CMD ["python", "-m", "app"]