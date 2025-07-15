"""
Pytest configuration and fixtures for edcpy tests.
"""

import asyncio
import os
import tempfile
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from faststream.rabbit import RabbitBroker, RabbitExchange

from edcpy.config import AppConfig
from edcpy.messaging import MessagingApp


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_cert_file() -> Generator[str, None, None]:
    """Create a temporary certificate file for testing."""

    cert_content = """-----BEGIN CERTIFICATE-----
MIIBkTCB+wIJANVqXjqUvJxzMA0GCSqGSIb3DQEBCwUAMBQxEjAQBgNVBAMMCWxv
Y2FsaG9zdDAeFw0yMzEwMDEwMDAwMDBaFw0yNDEwMDEwMDAwMDBaMBQxEjAQBgNV
BAMMCWxvY2FsaG9zdDBcMA0GCSqGSIb3DQEBAQUAA0sAMEgCQQC8Q2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2J2
-----END CERTIFICATE-----"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
        f.write(cert_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    try:
        os.unlink(temp_path)
    except OSError:
        pass


@pytest.fixture
def mock_config(mock_cert_file) -> AppConfig:
    """Create a mock configuration for testing."""

    config = AppConfig()
    config.cert_path = mock_cert_file
    config.rabbit_url = "amqp://test:test@localhost:5672/test"
    config.http_api_port = 8000
    return config


@pytest.fixture
def mock_messaging_app() -> MessagingApp:
    """Create a mock messaging app for testing."""

    mock_broker = AsyncMock(spec=RabbitBroker)
    mock_exchange = MagicMock(spec=RabbitExchange)
    mock_app = MagicMock()

    # Configure mock broker methods
    mock_broker.start = AsyncMock()
    mock_broker.close = AsyncMock()
    mock_broker.publish = AsyncMock()
    mock_broker.declare_exchange = AsyncMock()

    messaging_app = MessagingApp(
        broker=mock_broker, app=mock_app, exchange=mock_exchange
    )

    return messaging_app


@pytest.fixture
def mock_start_publisher_messaging_app(mock_messaging_app):
    """Mock the start_publisher_messaging_app function."""

    async def async_mock_start_publisher_messaging_app(*args, **kwargs):
        return mock_messaging_app

    with patch(
        "edcpy.backend.start_publisher_messaging_app",
        side_effect=async_mock_start_publisher_messaging_app,
    ):
        yield


@pytest.fixture
def mock_get_config(mock_config):
    """Mock the get_config function."""

    with patch("edcpy.backend.get_config", return_value=mock_config):
        yield mock_config


@pytest.fixture
def test_client(mock_start_publisher_messaging_app, mock_get_config):
    """Create a test client for the FastAPI app."""

    from edcpy.backend import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_endpoint_data_reference():
    """Sample EndpointDataReference data for testing."""

    return {
        "id": "test-transfer-id",
        "endpoint": "https://provider.example.com/api/data",
        "authKey": "Authorization",
        "authCode": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJkYWQiOiJ7XCJwcm9wZXJ0aWVzXCI6e1wibWV0aG9kXCI6XCJHRVRcIn19IiwiZXhwIjoxNzAwMDAwMDAwLCJpYXQiOjE2OTk5OTk5OTl9.mock_signature",
        "properties": {"key": "value"},
        "contractId": "contract-123",
    }


@pytest.fixture
def sample_push_data():
    """Sample push data for testing."""

    return {"message": "test data", "timestamp": "2023-01-01T00:00:00Z"}
