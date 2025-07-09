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
    start_messaging_app,
    with_messaging_app,
)


class TestMessagingAppCreation:
    """Test suite for messaging app creation and configuration."""

    @pytest.mark.asyncio
    async def test_start_messaging_app_success(self, mock_config):
        """Test successful creation of messaging app."""

        mock_broker = AsyncMock()
        mock_exchange = MagicMock()

        with patch("edcpy.messaging.RabbitBroker", return_value=mock_broker), patch(
            "edcpy.messaging.FastStream"
        ) as mock_faststream, patch(
            "edcpy.messaging.RabbitExchange", return_value=mock_exchange
        ), patch(
            "edcpy.messaging.get_config", return_value=mock_config
        ):

            messaging_app = await start_messaging_app()

            # Verify messaging app structure
            assert isinstance(messaging_app, MessagingApp)
            assert messaging_app.broker == mock_broker
            assert messaging_app.exchange == mock_exchange

            # Verify broker was started
            mock_broker.start.assert_called_once()
            mock_broker.declare_exchange.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_messaging_app_no_rabbit_url(self):
        """Test that messaging app creation fails without RabbitMQ URL."""

        mock_config = MagicMock(spec=AppConfig)
        mock_config.rabbit_url = None

        with patch("edcpy.messaging.get_config", return_value=mock_config):
            with pytest.raises(ValueError, match="RabbitMQ URL is not set"):
                await start_messaging_app()

    @pytest.mark.asyncio
    async def test_start_messaging_app_with_handlers(self, mock_config):
        """Test messaging app creation with custom handlers."""

        mock_broker = AsyncMock()
        mock_exchange = MagicMock()

        # Create proper mock handlers that are callable
        async def mock_pull_handler(message):
            pass

        async def mock_push_handler(message):
            pass

        # Mock the subscriber method to return a decorator function
        mock_subscriber_decorator = MagicMock()
        mock_subscriber_decorator.return_value = lambda handler: handler
        mock_broker.subscriber = MagicMock(return_value=mock_subscriber_decorator)

        with patch("edcpy.messaging.RabbitBroker", return_value=mock_broker), patch(
            "edcpy.messaging.FastStream"
        ) as mock_faststream, patch(
            "edcpy.messaging.RabbitExchange", return_value=mock_exchange
        ), patch(
            "edcpy.messaging.get_config", return_value=mock_config
        ), patch(
            "edcpy.messaging.RabbitQueue"
        ) as mock_queue:

            messaging_app = await start_messaging_app(
                http_pull_handler=mock_pull_handler, http_push_handler=mock_push_handler
            )

            # Verify handlers were registered
            assert mock_queue.call_count == 2  # One for pull, one for push
            assert mock_broker.subscriber.call_count == 2  # Called for both handlers

    @pytest.mark.asyncio
    async def test_with_messaging_app_context_manager(self, mock_config):
        """Test the messaging app context manager."""

        mock_broker = AsyncMock()
        mock_exchange = MagicMock()

        with patch("edcpy.messaging.RabbitBroker", return_value=mock_broker), patch(
            "edcpy.messaging.FastStream"
        ) as mock_faststream, patch(
            "edcpy.messaging.RabbitExchange", return_value=mock_exchange
        ), patch(
            "edcpy.messaging.get_config", return_value=mock_config
        ):

            async with with_messaging_app() as messaging_app:
                assert isinstance(messaging_app, MessagingApp)
                assert messaging_app.broker == mock_broker

            # Verify broker was closed after context exit
            mock_broker.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_messaging_app_exception_handling(self, mock_config):
        """Test that context manager handles broker close exceptions."""

        mock_broker = AsyncMock()
        mock_broker.close.side_effect = Exception("Close error")
        mock_exchange = MagicMock()

        with patch("edcpy.messaging.RabbitBroker", return_value=mock_broker), patch(
            "edcpy.messaging.FastStream"
        ) as mock_faststream, patch(
            "edcpy.messaging.RabbitExchange", return_value=mock_exchange
        ), patch(
            "edcpy.messaging.get_config", return_value=mock_config
        ):

            # Should not raise an exception
            async with with_messaging_app() as messaging_app:
                assert messaging_app is not None

            # Verify close was attempted
            mock_broker.close.assert_called_once()


class TestMessageModels:
    """Test suite for message model functionality."""

    def test_http_pull_message_creation(self):
        """Test HttpPullMessage creation and properties."""

        auth_code_decoded = {"dad": {"properties": {"method": "GET"}}}

        message = HttpPullMessage(
            auth_code_decoded=auth_code_decoded,
            auth_code="test_auth_code",
            auth_key="Authorization",
            endpoint="https://provider.example.com/api/data",
            id="test-id",
            properties={"key": "value"},
            contract_id="contract-123",
        )

        assert message.http_method == "GET"
        assert message.transfer_process_id == "test-id"
        assert message.provider_host == "provider.example.com"

        request_args = message.request_args
        assert request_args["method"] == "GET"
        assert request_args["url"] == "https://provider.example.com/api/data"
        assert request_args["headers"]["Authorization"] == "test_auth_code"
        assert request_args["params"]["contractId"] == "contract-123"

    def test_http_pull_message_missing_method(self):
        """Test HttpPullMessage with missing HTTP method."""

        auth_code_decoded = {"dad": {"properties": {}}}

        message = HttpPullMessage(
            auth_code_decoded=auth_code_decoded,
            auth_code="test_auth_code",
            auth_key="Authorization",
            endpoint="https://provider.example.com/api/data",
            id="test-id",
            properties={"key": "value"},
            contract_id="contract-123",
        )

        with pytest.raises(ValueError, match="Could not find HTTP method in auth code"):
            _ = message.http_method

    def test_http_push_message_creation(self):
        """Test HttpPushMessage creation."""

        test_body = {"message": "test data", "timestamp": "2023-01-01T00:00:00Z"}

        message = HttpPushMessage(body=test_body)

        assert message.body == test_body

    def test_http_pull_message_provider_host_with_port(self):
        """Test provider host extraction with port."""

        auth_code_decoded = {"dad": {"properties": {"method": "POST"}}}

        message = HttpPullMessage(
            auth_code_decoded=auth_code_decoded,
            auth_code="test_auth_code",
            auth_key="Authorization",
            endpoint="https://provider.example.com:8443/api/data",
            id="test-id",
            properties={"key": "value"},
            contract_id="contract-123",
        )

        assert message.provider_host == "provider.example.com"


class TestMessagePublishing:
    """Test suite for message publishing functionality."""

    @pytest.mark.asyncio
    async def test_publish_message_success(self, mock_messaging_app):
        """Test successful message publishing."""

        test_message = HttpPushMessage(body={"test": "data"})
        test_routing_key = "test.routing.key"

        await mock_messaging_app.broker.publish(
            message=test_message,
            routing_key=test_routing_key,
            exchange=mock_messaging_app.exchange,
        )

        # Verify publish was called with correct parameters
        mock_messaging_app.broker.publish.assert_called_once_with(
            message=test_message,
            routing_key=test_routing_key,
            exchange=mock_messaging_app.exchange,
        )

    @pytest.mark.asyncio
    async def test_publish_multiple_messages(self, mock_messaging_app):
        """Test publishing multiple messages."""

        messages = [HttpPushMessage(body={"message": f"test_{i}"}) for i in range(3)]

        for i, message in enumerate(messages):
            await mock_messaging_app.broker.publish(
                message=message,
                routing_key=f"test.{i}",
                exchange=mock_messaging_app.exchange,
            )

        # Verify all messages were published
        assert mock_messaging_app.broker.publish.call_count == 3

    @pytest.mark.asyncio
    async def test_publish_with_different_routing_keys(self, mock_messaging_app):
        """Test publishing with different routing key patterns."""

        test_cases = [
            (BASE_HTTP_PULL_QUEUE_ROUTING_KEY, "pull message"),
            (BASE_HTTP_PUSH_QUEUE_ROUTING_KEY, "push message"),
            (f"{BASE_HTTP_PULL_QUEUE_ROUTING_KEY}.provider-host", "pull with provider"),
            (
                f"{BASE_HTTP_PUSH_QUEUE_ROUTING_KEY}.custom.path",
                "push with custom path",
            ),
        ]

        for routing_key, body in test_cases:
            message = HttpPushMessage(body={"type": body})
            await mock_messaging_app.broker.publish(
                message=message,
                routing_key=routing_key,
                exchange=mock_messaging_app.exchange,
            )

        # Verify all routing keys were used
        assert mock_messaging_app.broker.publish.call_count == len(test_cases)

        # Verify the calls were made with correct routing keys
        call_args_list = mock_messaging_app.broker.publish.call_args_list
        used_routing_keys = [call.kwargs["routing_key"] for call in call_args_list]

        expected_routing_keys = [routing_key for routing_key, _ in test_cases]
        assert used_routing_keys == expected_routing_keys
