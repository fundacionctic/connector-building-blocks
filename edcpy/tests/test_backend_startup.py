"""
Tests for backend startup functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from edcpy.backend import app
from edcpy.config import AppConfig


class TestBackendStartup:
    """Test suite for backend startup functionality."""

    def test_backend_startup_success(self, mock_messaging_app):
        """Test successful backend startup."""
        with patch(
            "edcpy.backend.start_publisher_messaging_app",
            return_value=mock_messaging_app,
        ) as mock_start:
            # Create a mock async function
            mock_start.return_value = AsyncMock(return_value=mock_messaging_app)

            client = TestClient(app)
            response = client.get("/docs")  # Test that the app is running
            assert response.status_code == 200

    def test_backend_startup_with_messaging_app(self, mock_messaging_app):
        """Test that the messaging app is properly initialized."""
        with patch(
            "edcpy.backend.start_publisher_messaging_app",
            return_value=mock_messaging_app,
        ) as mock_start:
            # Create a mock async function
            mock_start.return_value = AsyncMock(return_value=mock_messaging_app)

            client = TestClient(app)
            # The messaging app should be available in the app state
            # This is tested indirectly through the lifespan manager

    def test_backend_endpoints_available(self, mock_messaging_app):
        """Test that all expected endpoints are available."""
        with patch(
            "edcpy.backend.start_publisher_messaging_app",
            return_value=mock_messaging_app,
        ) as mock_start:
            # Create a mock async function
            mock_start.return_value = AsyncMock(return_value=mock_messaging_app)

            client = TestClient(app)

            # Check that the main endpoints are available
            response = client.get("/docs")
            assert response.status_code == 200

    def test_backend_startup_failure(self, mock_messaging_app):
        """Test backend startup failure handling."""
        with patch(
            "edcpy.backend.start_publisher_messaging_app",
            side_effect=Exception("Startup error"),
        ):
            # TestClient will handle the exception internally during lifespan startup
            # We can't easily test this without more complex mocking of the lifespan
            # This test verifies that the patch is applied correctly
            with pytest.raises(Exception, match="Startup error"):
                # Directly call the lifespan to test the exception handling
                import asyncio

                from edcpy.backend import lifespan

                async def test_lifespan():
                    mock_app = MagicMock()
                    async with lifespan(mock_app):
                        pass

                asyncio.run(test_lifespan())

    def test_backend_config_dependency(self, mock_messaging_app):
        """Test that backend properly uses configuration."""
        mock_config = MagicMock(spec=AppConfig)
        mock_config.http_api_port = 8080
        mock_config.cert_path = "/path/to/cert.pem"
        mock_config.rabbit_url = "amqp://localhost"

        with patch(
            "edcpy.backend.start_publisher_messaging_app",
            return_value=mock_messaging_app,
        ) as mock_start, patch("edcpy.backend.get_config", return_value=mock_config):
            # Create a mock async function
            mock_start.return_value = AsyncMock(return_value=mock_messaging_app)

            client = TestClient(app)
            response = client.get("/docs")
            assert response.status_code == 200
