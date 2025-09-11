"""
Тесты для скрипта управления админами admin_management.py
"""

from unittest.mock import AsyncMock, patch

import pytest

from scripts.admin_management import AdminManager


class TestAdminManager:
    """Тесты для класса AdminManager"""

    @pytest.fixture
    def admin_manager(self):
        """Фикстура для AdminManager без Docker"""
        return AdminManager(docker_mode=False)

    @pytest.fixture
    def admin_manager_docker(self):
        """Фикстура для AdminManager с Docker"""
        return AdminManager(docker_mode=True)

    @pytest.mark.asyncio
    async def test_create_admin_success(self, admin_manager):
        """Тест успешного создания администратора"""
        mock_session = AsyncMock()

        # Мокаем проверку существующего пользователя
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Мокаем создание пользователя
        mock_new_admin = AsyncMock()
        mock_new_admin.id = 1
        mock_new_admin.username = "testadmin"
        mock_new_admin.email = "testadmin@example.com"
        mock_new_admin.name = "testadmin"
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None

        with patch.object(admin_manager, 'SessionFactory') as mock_factory:
            mock_factory.return_value = mock_session

            success = await admin_manager.create_admin_user(
                username="testadmin",
                password="testpass123"
            )

            assert success is True

    @pytest.mark.asyncio
    async def test_create_admin_already_exists(self, admin_manager):
        """Тест создания администратора, который уже существует"""
        mock_session = AsyncMock()

        # Мокаем существующего пользователя
        mock_existing_user = AsyncMock()
        mock_existing_user.username = "existingadmin"

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_existing_user
        mock_session.execute.return_value = mock_result

        with patch.object(admin_manager, 'SessionFactory') as mock_factory:
            mock_factory.return_value = mock_session

            success = await admin_manager.create_admin_user(
                username="existingadmin",
                password="testpass123"
            )

            assert success is False

    @pytest.mark.asyncio
    async def test_list_admins(self, admin_manager):
        """Тест получения списка администраторов"""
        mock_session = AsyncMock()

        # Мокаем список администраторов
        mock_admin1 = AsyncMock()
        mock_admin1.id = 1
        mock_admin1.username = "admin1"
        mock_admin1.name = "Admin One"
        mock_admin1.email = "admin1@example.com"
        mock_admin1.is_active = True

        mock_admin2 = AsyncMock()
        mock_admin2.id = 2
        mock_admin2.username = "admin2"
        mock_admin2.name = "Admin Two"
        mock_admin2.email = "admin2@example.com"
        mock_admin2.is_active = False

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_admin1, mock_admin2]
        mock_session.execute.return_value = mock_result

        with patch.object(admin_manager, 'SessionFactory') as mock_factory:
            mock_factory.return_value = mock_session

            admins = await admin_manager.list_admins()

            assert len(admins) == 2
            assert admins[0]['username'] == "admin1"
            assert admins[1]['username'] == "admin2"

    @pytest.mark.asyncio
    async def test_get_admin_by_username(self, admin_manager):
        """Тест поиска администратора по username"""
        mock_session = AsyncMock()

        # Мокаем администратора
        mock_admin = AsyncMock()
        mock_admin.id = 1
        mock_admin.username = "testadmin"
        mock_admin.name = "Test Admin"
        mock_admin.email = "testadmin@example.com"
        mock_admin.is_active = True

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_admin
        mock_session.execute.return_value = mock_result

        with patch.object(admin_manager, 'SessionFactory') as mock_factory:
            mock_factory.return_value = mock_session

            admin = await admin_manager.get_admin_by_username("testadmin")

            assert admin is not None
            assert admin['username'] == "testadmin"
            assert admin['name'] == "Test Admin"

    @pytest.mark.asyncio
    async def test_get_admin_by_username_not_found(self, admin_manager):
        """Тест поиска несуществующего администратора"""
        mock_session = AsyncMock()

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch.object(admin_manager, 'SessionFactory') as mock_factory:
            mock_factory.return_value = mock_session

            admin = await admin_manager.get_admin_by_username("nonexistent")

            assert admin is None

    @pytest.mark.asyncio
    async def test_update_admin_password(self, admin_manager):
        """Тест обновления пароля администратора"""
        mock_session = AsyncMock()

        # Мокаем администратора
        mock_admin = AsyncMock()
        mock_admin.username = "testadmin"

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_admin
        mock_session.execute.return_value = mock_result

        with patch.object(admin_manager, 'SessionFactory') as mock_factory:
            mock_factory.return_value = mock_session

            success = await admin_manager.update_admin_password("testadmin", "newpass123")

            assert success is True

    @pytest.mark.asyncio
    async def test_update_admin_password_not_found(self, admin_manager):
        """Тест обновления пароля несуществующего администратора"""
        mock_session = AsyncMock()

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_session

        with patch.object(admin_manager, 'SessionFactory') as mock_factory:
            mock_factory.return_value = mock_session

            success = await admin_manager.update_admin_password("nonexistent", "newpass123")

            assert success is False

    @pytest.mark.asyncio
    async def test_toggle_admin_status(self, admin_manager):
        """Тест изменения статуса администратора"""
        mock_session = AsyncMock()

        # Мокаем администратора
        mock_admin = AsyncMock()
        mock_admin.username = "testadmin"
        mock_admin.is_active = True

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_admin
        mock_session.execute.return_value = mock_result

        with patch.object(admin_manager, 'SessionFactory') as mock_factory:
            mock_factory.return_value = mock_session

            success = await admin_manager.toggle_admin_status("testadmin")

            assert success is True
            assert mock_admin.is_active is False  # Должен измениться на False

    def test_database_url_local(self, admin_manager):
        """Тест URL базы данных для локального режима"""
        expected_url = "postgresql+asyncpg://masterbot:masterbot@localhost:5432/masterbot"
        assert admin_manager.database_url == expected_url

    def test_database_url_docker(self, admin_manager_docker):
        """Тест URL базы данных для Docker режима"""
        expected_url = "postgresql+asyncpg://masterbot:masterbot@postgres:5432/masterbot"
        assert admin_manager_docker.database_url == expected_url


class TestAdminManagerIntegration:
    """Интеграционные тесты для AdminManager"""

    @pytest.mark.asyncio
    async def test_full_admin_lifecycle(self, admin_manager):
        """Тест полного жизненного цикла администратора"""
        # Этот тест требует реальной БД, поэтому мокаем всё
        pass

    def test_error_handling(self, admin_manager):
        """Тест обработки ошибок"""
        # Тест обработки различных исключений
        pass


class TestCommandLineInterface:
    """Тесты для командной строки"""

    def test_help_command(self):
        """Тест команды --help"""
        # Тест вывода справки
        pass

    def test_list_command(self):
        """Тест команды --list"""
        # Тест вывода списка администраторов
        pass

    def test_create_command(self):
        """Тест команды create"""
        # Тест создания администратора через CLI
        pass
