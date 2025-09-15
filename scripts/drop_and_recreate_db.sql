-- Скрипт для полного удаления и пересоздания базы данных
-- ВНИМАНИЕ: Этот скрипт удалит ВСЕ данные в базе данных!

-- Отключаем все активные соединения с базой данных
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'masterbot'
  AND pid <> pg_backend_pid();

-- Удаляем базу данных
DROP DATABASE IF EXISTS masterbot;

-- Пересоздаем базу данных
CREATE DATABASE masterbot
    WITH 
    OWNER = masterbot
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TEMPLATE = template0;

-- Устанавливаем привилегии
GRANT ALL PRIVILEGES ON DATABASE masterbot TO masterbot;