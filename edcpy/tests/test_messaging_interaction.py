"""
Tests for messaging interaction functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from edcpy.config import AppConfig
from edcpy.messaging import (
    BASE_HTTP_PULL_QUEUE_ROUTING_KEY,
    BASE_HTTP_PUSH_QUEUE_ROUTING_KEY,
    HttpPullMessage,
    HttpPushMessage,
    MessagingApp,
    start_publisher_messaging_app,
)


class TestPublisherMessagingApp:
    """Test suite for publisher-only messaging app creation and configuration."""

    @pytest.mark.asyncio
    async def test_start_publisher_messaging_app_success(self, mock_config):
        """Test successful creation of publisher-only messaging app."""
        mock_broker = AsyncMock()
        mock_exchange = MagicMock()

        with patch("edcpy.messaging.RabbitBroker", return_value=mock_broker), patch(
            "edcpy.messaging.FastStream"
        ) as mock_faststream, patch(
            "edcpy.messaging.RabbitExchange", return_value=mock_exchange
        ), patch(
            "edcpy.messaging.get_config", return_value=mock_config
        ):

            messaging_app = await start_publisher_messaging_app()

            # Verify messaging app structure
            assert isinstance(messaging_app, MessagingApp)
            assert messaging_app.broker == mock_broker
            assert messaging_app.exchange == mock_exchange
            assert messaging_app.consumer_queues == []  # No queues should be created

            # Verify broker was started
            mock_broker.start.assert_called_once()
            mock_broker.declare_exchange.assert_called_once()

            # Verify NO queues were declared (unlike the legacy function)
            mock_broker.declare_queue.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_publisher_messaging_app_no_rabbit_url(self):
        """Test that ValueError is raised when rabbit_url is not set."""
        mock_config = MagicMock(spec=AppConfig)
        mock_config.rabbit_url = None

        with patch("edcpy.messaging.get_config", return_value=mock_config):
            with pytest.raises(ValueError, match="RabbitMQ URL is not set"):
                await start_publisher_messaging_app()

    @pytest.mark.asyncio
    async def test_start_publisher_messaging_app_minimal_setup(self, mock_config):
        """Test publisher messaging app with minimal configuration."""
        mock_broker = AsyncMock()
        mock_exchange = MagicMock()

        with patch("edcpy.messaging.RabbitBroker", return_value=mock_broker), patch(
            "edcpy.messaging.FastStream"
        ), patch(
            "edcpy.messaging.RabbitExchange", return_value=mock_exchange
        ), patch(
            "edcpy.messaging.get_config", return_value=mock_config
        ):

            messaging_app = await start_publisher_messaging_app(
                exchange_name="test-exchange"
            )

            # Verify that custom exchange name was used
            assert messaging_app.exchange == mock_exchange

            # Verify broker operations
            mock_broker.start.assert_called_once()
            mock_broker.declare_exchange.assert_called_once_with(mock_exchange)

            # Verify no queues were created for publisher-only app
            mock_broker.declare_queue.assert_not_called()
            mock_broker.subscriber.assert_not_called()


class TestMessageModels:
    """Test suite for message model validation and property extraction."""

    def test_http_pull_message_creation(self):
        """Test creation of HttpPullMessage with all required fields."""
        message_data = {
            "auth_code_decoded": {
                "dad": {"properties": {"method": "GET"}},
                "other": "data",
            },
            "auth_code": "test_auth_code",
            "auth_key": "test_auth_key",
            "endpoint": "https://example.com:8080/api/data",
            "id": "test_id",
            "properties": {"key": "value"},
            "contract_id": "test_contract",
        }

        message = HttpPullMessage(**message_data)

        assert message.auth_code == "test_auth_code"
        assert message.auth_key == "test_auth_key"
        assert message.endpoint == "https://example.com:8080/api/data"
        assert message.id == "test_id"
        assert message.properties == {"key": "value"}
        assert message.contract_id == "test_contract"
        assert message.http_method == "GET"
        assert message.transfer_process_id == "test_id"
        assert message.provider_host == "example.com"

    def test_http_pull_message_missing_method(self):
        """Test that ValueError is raised when HTTP method is missing."""
        message_data = {
            "auth_code_decoded": {"dad": {"properties": {}}},  # Missing method
            "auth_code": "test_auth_code",
            "auth_key": "test_auth_key",
            "endpoint": "https://example.com/api/data",
            "id": "test_id",
            "properties": {},
            "contract_id": "test_contract",
        }

        message = HttpPullMessage(**message_data)

        with pytest.raises(ValueError, match="Could not find HTTP method in auth code"):
            _ = message.http_method

    def test_http_push_message_creation(self):
        """Test creation of HttpPushMessage."""
        message_data = {"body": {"test": "data", "number": 42}}

        message = HttpPushMessage(**message_data)
        assert message.body == {"test": "data", "number": 42}

    def test_http_pull_message_provider_host_with_port(self):
        """Test provider_host extraction handles ports correctly."""
        message_data = {
            "auth_code_decoded": {"dad": {"properties": {"method": "POST"}}},
            "auth_code": "test_auth_code",
            "auth_key": "test_auth_key",
            "endpoint": "https://provider.example.com:9443/api/endpoint",
            "id": "test_id",
            "properties": {},
            "contract_id": "test_contract",
        }

        message = HttpPullMessage(**message_data)
        assert message.provider_host == "provider.example.com"


class TestMessagePublishing:
    """Test suite for message publishing functionality."""

    @pytest.mark.asyncio
    async def test_publish_message_success(self, mock_messaging_app):
        """Test successful message publishing."""
        test_message = {"test": "data"}
        test_routing_key = "test.routing.key"

        await mock_messaging_app.broker.publish(
            message=test_message,
            routing_key=test_routing_key,
            exchange=mock_messaging_app.exchange,
        )

        mock_messaging_app.broker.publish.assert_called_once_with(
            message=test_message,
            routing_key=test_routing_key,
            exchange=mock_messaging_app.exchange,
        )

    @pytest.mark.asyncio
    async def test_publish_multiple_messages(self, mock_messaging_app):
        """Test publishing multiple messages."""
        messages = [
            {"id": 1, "data": "first"},
            {"id": 2, "data": "second"},
        ]

        for i, message in enumerate(messages):
            await mock_messaging_app.broker.publish(
                message=message,
                routing_key=f"test.message.{i}",
                exchange=mock_messaging_app.exchange,
            )

        assert mock_messaging_app.broker.publish.call_count == 2

    @pytest.mark.asyncio
    async def test_publish_with_different_routing_keys(self, mock_messaging_app):
        """Test publishing messages with different routing keys."""
        pull_message = HttpPullMessage(
            auth_code_decoded={"dad": {"properties": {"method": "GET"}}},
            auth_code="test_code",
            auth_key="test_key",
            endpoint="https://example.com/api",
            id="test_id",
            properties={},
            contract_id="test_contract",
        )

        push_message = HttpPushMessage(body={"test": "data"})

        # Test pull message routing
        pull_routing_key = f"{BASE_HTTP_PULL_QUEUE_ROUTING_KEY}.example.com.test_id"
        await mock_messaging_app.broker.publish(
            message=pull_message,
            routing_key=pull_routing_key,
            exchange=mock_messaging_app.exchange,
        )

        # Test push message routing
        push_routing_key = f"{BASE_HTTP_PUSH_QUEUE_ROUTING_KEY}.test.path"
        await mock_messaging_app.broker.publish(
            message=push_message,
            routing_key=push_routing_key,
            exchange=mock_messaging_app.exchange,
        )

        assert mock_messaging_app.broker.publish.call_count == 2
