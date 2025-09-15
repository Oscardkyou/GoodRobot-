#!/bin/bash
# Скрипт для прямого удаления проблемных ENUM типов в PostgreSQL
# Запускать только когда контейнер postgres запущен

set -e

echo "🔧 Начинаем исправление проблем с ENUM типами в PostgreSQL..."

# Удаляем таблицы, зависящие от проблемных типов
echo "🗑️ Удаляем таблицы, зависящие от проблемных типов..."
docker compose exec postgres psql -U postgres -d masterbot -c "DROP TABLE IF EXISTS chat_sessions CASCADE;"
docker compose exec postgres psql -U postgres -d masterbot -c "DROP TABLE IF EXISTS chat_messages CASCADE;"

# Удаляем проблемные ENUM типы
echo "🗑️ Удаляем проблемные ENUM типы..."
docker compose exec postgres psql -U postgres -d masterbot -c "DROP TYPE IF EXISTS chat_session_status_enum CASCADE;"
docker compose exec postgres psql -U postgres -d masterbot -c "DROP TYPE IF EXISTS chat_message_type_enum CASCADE;"

# Сбрасываем статус миграций
echo "🔄 Сбрасываем статус миграций..."
docker compose exec postgres psql -U postgres -d masterbot -c "DELETE FROM alembic_version WHERE version_num = 'd90c3fb44c85';"

echo "✅ Исправление завершено. Теперь перезапустите проект командой:"
echo "docker compose down && docker compose up -d"