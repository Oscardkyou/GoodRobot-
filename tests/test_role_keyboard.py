from app.bot.keyboards import role_keyboard


def test_role_keyboard_has_only_client_and_master():
    kb = role_keyboard()
    rows = kb.inline_keyboard
    # Expect exactly one row with two buttons
    assert len(rows) == 1
    assert len(rows[0]) == 2
    texts = [btn.text for btn in rows[0]]
    assert "Я клиент" in texts
    assert "Я мастер" in texts
    assert all("Партн" not in t for t in texts)
