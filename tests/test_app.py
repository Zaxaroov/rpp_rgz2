import pytest
from unittest.mock import patch, MagicMock
from app import app

# Создаем тестовый клиент Flask
@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

# Тест генерации короткой ссылки (POST /shorten)
@patch("app.get_db_connections")
def test_shorten(mock_db, client):
    # Мокаем соединение и курсор
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    response = client.post("/shorten", data={"url": "https://example.com"})
    
    # Проверка редиректа
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    
    # Проверка что был выполнен INSERT
    mock_cursor.execute.assert_called()
    mock_conn.commit.assert_called()

# Тест редиректа по короткой ссылке (GET /<short_code>)
@patch("app.get_db_connections")
def test_redirect_short(mock_db, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Мокаем результат запроса SELECT
    mock_cursor.fetchone.return_value = {"id": 1, "original_url": "https://example.com"}
    
    response = client.get("/abcdef12")
    
    # Проверка редиректа на оригинальный URL
    assert response.status_code == 302
    assert response.headers["Location"] == "https://example.com"
    
    # Проверка обновления кликов
    assert mock_cursor.execute.call_count >= 2
    mock_conn.commit.assert_called()

# Тест получения статистики (GET /stats/<short_code>)
@patch("app.get_db_connections")
def test_stats(mock_db, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Мокаем результаты SELECT
    mock_cursor.fetchone.side_effect = [
        {"id": 1, "clicks": 10},  # результат запроса url_row
    ]
    mock_cursor.fetchall.return_value = [
        {"ip_address": "127.0.0.1"},
        {"ip_address": "192.168.1.1"}
    ]
    
    response = client.get("/stats/abcdef12")
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["clicks"] == 10
    assert "127.0.0.1" in data["unique_ips"]
    assert "192.168.1.1" in data["unique_ips"]
