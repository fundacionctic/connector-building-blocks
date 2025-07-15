"""
Test module for SSE endpoints.

This module tests the Server-Sent Events endpoints for pull and push transfers,
verifying that they properly stream messages and handle authentication.
"""

import json
import os
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from edcpy.backend import app


@pytest.fixture
def api_key():
    """API key for testing."""

    return "test-api-key-123"


@pytest.fixture
def client_with_api_key(api_key):
    """Test client with API key environment variable set."""

    with patch.dict(os.environ, {"API_AUTH_KEY": api_key}):
        yield TestClient(app)


@pytest.fixture
def auth_headers(api_key):
    """Authorization headers for API key authentication."""

    return {"Authorization": f"Bearer {api_key}"}


class TestSSEPullEndpoint:
    """Test cases for the pull SSE endpoint."""

    def test_missing_api_key_env(self):
        """Test that endpoint returns 403 when API_AUTH_KEY is not set."""

        with patch.dict(os.environ, {}, clear=True):
            client = TestClient(app)
            response = client.get("/pull/stream/test-transfer-123")
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_invalid_api_key(self, client_with_api_key):
        """Test that endpoint returns 401 with invalid API key."""

        headers = {"Authorization": "Bearer invalid-key"}

        response = client_with_api_key.get(
            "/pull/stream/test-transfer-123", headers=headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_auth_header(self, client_with_api_key):
        """Test that endpoint returns 403 when Authorization header is missing."""

        response = client_with_api_key.get("/pull/stream/test-transfer-123")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("edcpy.backend._stream_pull_messages")
    def test_pull_sse_success(
        self, mock_stream_function, client_with_api_key, auth_headers
    ):
        """Test successful pull SSE streaming."""

        # Mock the streaming function to return a successful SSE message
        mock_pull_message_data = {
            "type": "pull_message",
            "transfer_process_id": "test-transfer-123",
            "request_args": {"method": "GET", "url": "http://provider.com/data"},
            "auth_code": "jwt-token",
            "auth_key": "Authorization",
            "endpoint": "http://provider.com/data",
            "properties": {"key": "value"},
            "contract_id": "contract-123",
        }

        async def mock_stream_generator():
            yield f"data: {json.dumps(mock_pull_message_data)}\n\n"

        mock_stream_function.return_value = mock_stream_generator()

        # Make the SSE request
        response = client_with_api_key.get(
            "/pull/stream/test-transfer-123?timeout=5", headers=auth_headers
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert "Cache-Control" in response.headers
        assert response.headers["Cache-Control"] == "no-cache"

        # Verify the SSE data format
        content = response.text
        assert "data: " in content

        # Parse the JSON data from the SSE event
        sse_data = content.split("data: ")[1].split("\n\n")[0]
        event_data = json.loads(sse_data)

        assert event_data["type"] == "pull_message"
        assert event_data["transfer_process_id"] == "test-transfer-123"
        assert event_data["request_args"] == {
            "method": "GET",
            "url": "http://provider.com/data",
        }
        assert event_data["auth_code"] == "jwt-token"
        assert event_data["auth_key"] == "Authorization"
        assert event_data["endpoint"] == "http://provider.com/data"
        assert event_data["properties"] == {"key": "value"}
        assert event_data["contract_id"] == "contract-123"

    @patch("edcpy.backend._stream_pull_messages")
    def test_pull_sse_error_handling(
        self, mock_stream_function, client_with_api_key, auth_headers
    ):
        """Test error handling in pull SSE streaming."""

        # Mock the streaming function to return an error message
        mock_error_data = {
            "type": "error",
            "message": "Connection failed",
            "transfer_process_id": "test-transfer-123",
            "routing_path": None,
        }

        async def mock_stream_generator():
            yield f"data: {json.dumps(mock_error_data)}\n\n"

        mock_stream_function.return_value = mock_stream_generator()

        # Make the SSE request
        response = client_with_api_key.get(
            "/pull/stream/test-transfer-123", headers=auth_headers
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK

        # Verify error message in SSE format
        content = response.text
        assert "data: " in content

        sse_data = content.split("data: ")[1].split("\n\n")[0]
        event_data = json.loads(sse_data)

        assert event_data["type"] == "error"
        assert event_data["message"] == "Connection failed"
        assert event_data["transfer_process_id"] == "test-transfer-123"
        assert event_data["routing_path"] is None


class TestSSEPushEndpoint:
    """Test cases for the push SSE endpoint."""

    def test_missing_api_key_env(self):
        """Test that endpoint returns 403 when API_AUTH_KEY is not set."""

        with patch.dict(os.environ, {}, clear=True):
            client = TestClient(app)
            response = client.get("/push/stream/test/routing/path")
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_invalid_api_key(self, client_with_api_key):
        """Test that endpoint returns 401 with invalid API key."""

        headers = {"Authorization": "Bearer invalid-key"}

        response = client_with_api_key.get(
            "/push/stream/test/routing/path", headers=headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("edcpy.backend._stream_push_messages")
    def test_push_sse_success(
        self, mock_stream_function, client_with_api_key, auth_headers
    ):
        """Test successful push SSE streaming."""

        # Mock the streaming function to return a successful SSE message
        mock_push_message_data = {
            "type": "push_message",
            "routing_path": "test/routing/path",
            "body": {"data": "test data", "timestamp": "2023-01-01T00:00:00Z"},
        }

        async def mock_stream_generator():
            yield f"data: {json.dumps(mock_push_message_data)}\n\n"

        mock_stream_function.return_value = mock_stream_generator()

        # Make the SSE request
        response = client_with_api_key.get(
            "/push/stream/test/routing/path?timeout=5", headers=auth_headers
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert response.headers["Cache-Control"] == "no-cache"

        # Verify the SSE data format
        content = response.text
        assert "data: " in content

        # Parse the JSON data from the SSE event
        sse_data = content.split("data: ")[1].split("\n\n")[0]
        event_data = json.loads(sse_data)

        assert event_data["type"] == "push_message"
        assert event_data["routing_path"] == "test/routing/path"
        assert event_data["body"] == {
            "data": "test data",
            "timestamp": "2023-01-01T00:00:00Z",
        }

    @patch("edcpy.backend._stream_push_messages")
    def test_push_sse_error_handling(
        self, mock_stream_function, client_with_api_key, auth_headers
    ):
        """Test error handling in push SSE streaming."""

        # Mock the streaming function to return an error message
        mock_error_data = {
            "type": "error",
            "message": "Queue not found",
            "transfer_process_id": None,
            "routing_path": "test/routing/path",
        }

        async def mock_stream_generator():
            yield f"data: {json.dumps(mock_error_data)}\n\n"

        mock_stream_function.return_value = mock_stream_generator()

        # Make the SSE request
        response = client_with_api_key.get(
            "/push/stream/test/routing/path", headers=auth_headers
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK

        # Verify error message in SSE format
        content = response.text
        assert "data: " in content

        sse_data = content.split("data: ")[1].split("\n\n")[0]
        event_data = json.loads(sse_data)

        assert event_data["type"] == "error"
        assert event_data["message"] == "Queue not found"
        assert event_data["routing_path"] == "test/routing/path"
        assert event_data["transfer_process_id"] is None


class TestSSEParameterValidation:
    """Test cases for SSE parameter validation."""

    def test_timeout_validation(self, client_with_api_key, auth_headers):
        """Test timeout parameter validation."""

        # Test timeout too low
        response = client_with_api_key.get(
            "/pull/stream/test-transfer-123?timeout=0", headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test timeout too high
        response = client_with_api_key.get(
            "/pull/stream/test-transfer-123?timeout=3601", headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test valid timeout
        with patch("edcpy.backend._stream_pull_messages") as mock_stream_function:

            async def mock_stream_generator():
                yield 'data: {"type": "error", "message": "Test exception"}\n\n'

            mock_stream_function.return_value = mock_stream_generator()

            response = client_with_api_key.get(
                "/pull/stream/test-transfer-123?timeout=60", headers=auth_headers
            )
            assert response.status_code == status.HTTP_200_OK

            # Verify timeout was passed correctly
            mock_stream_function.assert_called_once_with(
                transfer_process_id="test-transfer-123", timeout=60, provider_host=None
            )

    def test_default_timeout(self, client_with_api_key, auth_headers):
        """Test that default timeout is applied correctly."""

        with patch("edcpy.backend._stream_pull_messages") as mock_stream_function:

            async def mock_stream_generator():
                yield 'data: {"type": "error", "message": "Test exception"}\n\n'

            mock_stream_function.return_value = mock_stream_generator()

            response = client_with_api_key.get(
                "/pull/stream/test-transfer-123", headers=auth_headers
            )
            assert response.status_code == status.HTTP_200_OK

            # Verify default timeout was used (60 seconds) and no provider_host
            mock_stream_function.assert_called_once_with(
                transfer_process_id="test-transfer-123", timeout=60, provider_host=None
            )

    def test_provider_host_parameter(self, client_with_api_key, auth_headers):
        """Test provider_host parameter is passed correctly."""

        with patch("edcpy.backend._stream_pull_messages") as mock_stream_function:

            async def mock_stream_generator():
                yield 'data: {"type": "error", "message": "Test exception"}\\n\\n'

            mock_stream_function.return_value = mock_stream_generator()

            response = client_with_api_key.get(
                "/pull/stream/test-transfer-123?provider_host=provider.example.com",
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK

            # Verify provider_host was passed correctly
            mock_stream_function.assert_called_once_with(
                transfer_process_id="test-transfer-123",
                timeout=60,
                provider_host="provider.example.com",
            )
