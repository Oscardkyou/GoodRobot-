#!/bin/bash
# Скрипт для полного сброса базы данных и перезапуска проекта
# Использование: ./reset_db_and_restart.sh

set -e

echo "🔄 Останавливаем все контейнеры..."
docker compose down

echo "🔍 Поиск и удаление тома с данными PostgreSQL..."
PG_VOLUME=$(docker volume ls | grep -E 'goodrobot.*pgdata|pgdata.*goodrobot' | awk '{print $2}')

if [ -z "$PG_VOLUME" ]; then
  echo "⚠️  Том PostgreSQL не найден. Возможно, он уже был удален."
else
  echo "🗑️  Удаляем том $PG_VOLUME..."
  
  # Проверяем, используется ли том
  if docker volume rm "$PG_VOLUME" 2>/dev/null; then
    echo "✅ Том успешно удален."
  else
    echo "⚠️  Том используется. Останавливаем все контейнеры..."
    docker stop $(docker ps -aq) 2>/dev/null || true
    
    echo "🗑️  Повторная попытка удаления тома..."
    if docker volume rm "$PG_VOLUME" 2>/dev/null; then
      echo "✅ Том успешно удален."
    else
      echo "❌ Не удалось удалить том. Возможно, он все еще используется."
      echo "   Выполните следующие команды вручную:"
      echo "   docker stop \$(docker ps -aq)"
      echo "   docker rm \$(docker ps -aq)"
      echo "   docker volume rm $PG_VOLUME"
      exit 1
    fi
  fi
fi

echo "🚀 Запускаем проект заново..."
docker compose up --build -d

echo "⏳ Ожидаем запуска контейнеров (30 секунд)..."
sleep 30

echo "🔍 Проверяем статус контейнеров..."
if docker compose ps | grep -q "Up"; then
  echo "✅ Проект успешно запущен!"
  echo ""
  echo "🔑 Теперь вы можете создать администратора:"
  echo "   ./run_script_in_container.sh scripts/create_admin.py <TG_ID> <USERNAME> <PASSWORD>"
  echo ""
  echo "🧪 Или заполнить базу тестовыми данными:"
  echo "   ./run_script_in_container.sh scripts/seed_mock_masters.py"
else
  echo "❌ Что-то пошло не так. Проверьте логи:"
  echo "   docker compose logs"
fi