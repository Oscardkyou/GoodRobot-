#!/bin/bash

# Скрипт для выполнения Python-скриптов внутри контейнера admin
# Использование: ./run_script_in_container.sh <путь_к_скрипту_внутри_контейнера> [аргументы...]

set -e

if [ $# -lt 1 ]; then
  echo "Использование: $0 <путь_к_скрипту_внутри_контейнера> [аргументы...]"
  echo "Пример: $0 scripts/create_admin.py 123456789 admin password123"
  exit 1
fi

SCRIPT_PATH=$1
shift

# Проверяем, запущен ли контейнер
if ! docker compose ps --services --filter status=running | grep -q admin; then
  echo "Контейнер admin не запущен. Запускаем проект..."
  docker compose up -d
  echo "Ожидаем запуск контейнера (30 секунд)..."
  sleep 30
  
  # Проверяем снова
  if ! docker compose ps --services --filter status=running | grep -q admin; then
    echo "Ошибка: Контейнер admin не запустился. Проверьте логи docker compose logs."
    exit 1
  fi
fi

# Выполняем скрипт внутри контейнера
echo "Выполняем $SCRIPT_PATH внутри контейнера admin..."
docker compose exec admin python "$SCRIPT_PATH" "$@"

echo "Готово."
