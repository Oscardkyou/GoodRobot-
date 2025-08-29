"""Tests for order visibility between clients and masters."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, CallbackQuery, User as TelegramUser
from aiogram.fsm.context import FSMContext

from app.models import User, Order, Bid
from app.bot.handlers.client import order_bids_list
from app.bot.handlers.master import nearby_orders_button, view_order_details


@pytest.fixture
def mock_message():
    """Create mock message for testing."""
    message = AsyncMock(spec=Message)
    message.from_user = AsyncMock(spec=TelegramUser)
    message.from_user.id = 123456
    message.chat = AsyncMock()
    message.chat.id = 123456
    return message


@pytest.fixture
def mock_callback():
    """Create mock callback for testing."""
    callback = AsyncMock(spec=CallbackQuery)
    callback.from_user = AsyncMock(spec=TelegramUser)
    callback.from_user.id = 123456
    callback.message = AsyncMock(spec=Message)
    callback.message.chat = AsyncMock()
    callback.message.chat.id = 123456
    return callback


@pytest.fixture
def mock_state():
    """Create mock FSM state for testing."""
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {}
    return state


@pytest.mark.asyncio
async def test_client_can_view_order_details(mock_callback, mock_state):
    """Test that client can view their order details."""
    # Setup
    mock_callback.data = "order:1"
    
    client_user = User(id=1, tg_id=123456, name="Test Client", role="client")
    order = Order(
        id=1, 
        client_id=1,
        category="Test Category",
        zone="Test Zone",
        address="Test Address",
        description="Test Description",
        status="new"
    )
    
    # Mock database query results
    with patch("app.bot.handlers.client.SessionFactory") as mock_session_factory:
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Правильно настраиваем моки для асинхронных вызовов
        mock_execute = AsyncMock()
        mock_scalars = AsyncMock()
        mock_first = AsyncMock(return_value=client_user)
        mock_scalars.return_value.first = mock_first
        mock_execute.return_value.scalars = mock_scalars
        
        # Для запроса заказа
        mock_execute_order = AsyncMock()
        mock_scalars_order = AsyncMock()
        mock_first_order = AsyncMock(return_value=order)
        mock_scalars_order.return_value.first = mock_first_order
        mock_execute_order.return_value.scalars = mock_scalars_order
        
        # Для запроса количества ставок
        mock_execute_bids = AsyncMock()
        mock_scalar_bids = AsyncMock(return_value=2)
        mock_execute_bids.return_value.scalar = mock_scalar_bids
        
        # Настраиваем последовательность вызовов execute
        mock_session.execute.side_effect = [mock_execute, mock_execute_order, mock_execute_bids]
        
        # Import function locally to avoid circular imports
        from app.bot.handlers.client import view_order_client
        
        # Execute
        await view_order_client(mock_callback, mock_state)
        
        # Assert
        mock_callback.message.edit_text.assert_called_once()
        # Verify order details are shown
        call_args = mock_callback.message.edit_text.call_args[0][0]
        assert f"Заказ #{order.id}" in call_args
        assert order.category in call_args
        assert order.zone in call_args
        assert "Ставки" in call_args
        # Verify "Ставки" button is present
        reply_markup = mock_callback.message.edit_text.call_args[1]["reply_markup"]
        assert any("Ставки" in btn.text for row in reply_markup.inline_keyboard for btn in row)


@pytest.mark.asyncio
async def test_client_can_view_bids(mock_callback, mock_state):
    """Test that client can view bids on their order."""
    # Setup
    mock_callback.data = "order_bids:1"
    
    client_user = User(id=1, tg_id=123456, name="Test Client", role="client")
    order = Order(
        id=1, 
        client_id=1,
        category="Test Category",
        zone="Test Zone",
        status="new"
    )
    master1 = User(id=2, tg_id=654321, name="Master 1", role="master")
    master2 = User(id=3, tg_id=789012, name="Master 2", role="master")
    bid1 = Bid(id=1, order_id=1, master_id=2, price=5000, status="active")
    bid2 = Bid(id=2, order_id=1, master_id=3, price=6000, status="active")
    
    # Mock database query results
    with patch("app.bot.handlers.client.SessionFactory") as mock_session_factory:
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock user query
        mock_user_result = AsyncMock()
        mock_user_result.scalars.return_value.first.return_value = client_user
        mock_session.execute.side_effect = [mock_user_result]
        
        # Mock order query
        mock_order_result = AsyncMock()
        mock_order_result.scalars.return_value.first.return_value = order
        mock_session.execute.side_effect = [mock_user_result, mock_order_result]
        
        # Mock bids query
        mock_bids_result = AsyncMock()
        mock_bids_result.all.return_value = [(bid1, master1), (bid2, master2)]
        mock_session.execute.side_effect = [mock_user_result, mock_order_result, mock_bids_result]
        
        # Execute
        await order_bids_list(mock_callback, mock_state)
        
        # Assert
        mock_callback.message.edit_text.assert_called_once()
        # Verify bids are shown
        call_args = mock_callback.message.edit_text.call_args[0][0]
        assert f"Заказ #{order.id}" in call_args
        assert "Предложения мастеров:" in call_args
        assert master1.name in call_args
        assert master2.name in call_args
        assert str(bid1.price) in call_args
        assert str(bid2.price) in call_args
        # Verify select buttons are present
        reply_markup = mock_callback.message.edit_text.call_args[1]["reply_markup"]
        assert any(f"Выбрать: {master1.name}" in btn.text for row in reply_markup.inline_keyboard for btn in row)
        assert any(f"Выбрать: {master2.name}" in btn.text for row in reply_markup.inline_keyboard for btn in row)


@pytest.mark.asyncio
async def test_client_can_select_bid(mock_callback):
    """Test that client can select a bid."""
    # Setup
    mock_callback.data = "select_bid:1"
    
    client_user = User(id=1, tg_id=123456, name="Test Client", role="client")
    master = User(id=2, tg_id=654321, name="Test Master", role="master")
    order = Order(
        id=1, 
        client_id=1,
        category="Test Category",
        zone="Test Zone",
        status="new"
    )
    bid = Bid(id=1, order_id=1, master_id=2, price=5000, status="active")
    
    # Import function locally to avoid circular imports
    with patch("app.bot.handlers.client.SessionFactory") as mock_session_factory:
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock user query
        mock_user_result = AsyncMock()
        mock_user_result.scalars.return_value.first.return_value = client_user
        mock_session.execute.side_effect = [mock_user_result]
        
        # Mock bid, order, master query
        mock_bid_order_result = AsyncMock()
        mock_bid_order_result.first.return_value = (bid, order, master)
        mock_session.execute.side_effect = [mock_user_result, mock_bid_order_result]
        
        # Mock other bids query
        mock_other_bids_result = AsyncMock()
        mock_other_bids_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [mock_user_result, mock_bid_order_result, mock_other_bids_result]
        
        # Import function locally
        from app.bot.handlers.client import select_bid
        
        # Execute
        await select_bid(mock_callback, None)
        
        # Assert
        mock_callback.message.edit_text.assert_called_once()
        # Verify confirmation message
        call_args = mock_callback.message.edit_text.call_args[0][0]
        assert f"Вы выбрали мастера {master.name}" in call_args
        assert f"заказа #{order.id}" in call_args
        assert str(bid.price) in call_args
        # Verify order and bid status updates
        assert order.status == "assigned"
        assert order.master_id == master.id
        assert bid.status == "selected"
        # Verify master notification
        mock_callback.bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_master_can_view_nearby_orders(mock_message, mock_state):
    """Test that master can view orders in their zones."""
    # Setup
    master_user = User(id=2, tg_id=123456, name="Test Master", role="master", zones=["Zone1", "Zone2"])
    order1 = Order(
        id=1, 
        client_id=1,
        category="Category1",
        zone="Zone1",
        status="new",
        created_at=MagicMock()
    )
    order1.created_at.strftime.return_value = "01.01.2023 12:00"
    
    order2 = Order(
        id=2, 
        client_id=1,
        category="Category2",
        zone="Zone2",
        status="new",
        created_at=MagicMock()
    )
    order2.created_at.strftime.return_value = "02.01.2023 12:00"
    
    # Mock database query results
    with patch("app.bot.handlers.master.SessionFactory") as mock_session_factory:
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock user query
        mock_user_result = AsyncMock()
        mock_user_result.scalars.return_value.first.return_value = master_user
        mock_session.execute.side_effect = [mock_user_result]
        
        # Mock new orders query
        mock_new_orders_result = AsyncMock()
        mock_new_orders_result.scalars.return_value.all.return_value = [order1, order2]
        mock_session.execute.side_effect = [mock_user_result, mock_new_orders_result]
        
        # Mock assigned orders query
        mock_assigned_orders_result = AsyncMock()
        mock_assigned_orders_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [mock_user_result, mock_new_orders_result, mock_assigned_orders_result]
        
        # Mock bids query
        mock_bids_result = AsyncMock()
        mock_bids_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [
            mock_user_result, 
            mock_new_orders_result, 
            mock_assigned_orders_result,
            mock_bids_result
        ]
        
        # Execute
        await nearby_orders_button(mock_message, mock_state)
        
        # Assert
        assert mock_message.answer.call_count >= 3  # Header + 2 orders
        # Verify orders are shown
        calls = mock_message.answer.call_args_list
        assert any("Новые заказы в ваших районах" in call[0][0] for call in calls)
        assert any(f"Заказ #{order1.id}" in call[0][0] for call in calls)
        assert any(f"Заказ #{order2.id}" in call[0][0] for call in calls)
        assert any(order1.category in call[0][0] for call in calls)
        assert any(order2.category in call[0][0] for call in calls)
        assert any(order1.zone in call[0][0] for call in calls)
        assert any(order2.zone in call[0][0] for call in calls)


@pytest.mark.asyncio
async def test_master_can_view_order_details(mock_callback, mock_state):
    """Test that master can view order details."""
    # Setup
    mock_callback.data = "view_order:1"
    
    master_user = User(id=2, tg_id=123456, name="Test Master", role="master", zones=["Zone1"])
    order = Order(
        id=1, 
        client_id=1,
        category="Test Category",
        zone="Zone1",
        address="Test Address",
        description="Test Description",
        status="new",
        created_at=MagicMock()
    )
    order.created_at.strftime.return_value = "01.01.2023 12:00"
    
    # Mock database query results
    with patch("app.bot.handlers.master.SessionFactory") as mock_session_factory:
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock order query
        mock_order_result = AsyncMock()
        mock_order_result.scalars.return_value.first.return_value = order
        mock_session.execute.side_effect = [mock_order_result]
        
        # Execute
        await view_order_details(mock_callback, mock_state)
        
        # Assert
        mock_callback.message.edit_text.assert_called_once()
        # Verify order details are shown
        call_args = mock_callback.message.edit_text.call_args[0][0]
        assert f"Заказ #{order.id}" in call_args
        assert order.category in call_args
        assert order.zone in call_args
        assert order.address in call_args
        assert order.description in call_args
        # Verify bid button is present
        reply_markup = mock_callback.message.edit_text.call_args[1]["reply_markup"]
        assert any("Сделать ставку" in btn.text for row in reply_markup.inline_keyboard for btn in row)