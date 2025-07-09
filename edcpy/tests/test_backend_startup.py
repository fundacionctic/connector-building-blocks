"""
Tests for backend API startup and shutdown functionality.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from edcpy.backend import app, lifespan


class TestBackendStartup:
    """Test suite for backend startup functionality."""

    def test_app_creation(self):
        """Test that the FastAPI app can be created successfully."""

        assert app is not None
        assert hasattr(app.router, "lifespan_context")

    @pytest.mark.asyncio
    async def test_lifespan_startup_success(self, mock_messaging_app):
        """Test successful startup of the messaging app during lifespan."""

        mock_app = AsyncMock()

        with patch(
            "edcpy.backend.start_messaging_app", return_value=mock_messaging_app
        ):
            async with lifespan(mock_app):
                # Verify that the messaging app was set on the app state
                assert mock_app.state.messaging_app == mock_messaging_app

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_success(self, mock_messaging_app):
        """Test successful shutdown of the messaging app during lifespan."""

        mock_app = AsyncMock()

        with patch(
            "edcpy.backend.start_messaging_app", return_value=mock_messaging_app
        ):
            async with lifespan(mock_app):
                pass

            # Verify that the broker was closed
            mock_messaging_app.broker.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_with_exception(self, mock_messaging_app):
        """Test that shutdown handles exceptions gracefully."""

        mock_app = AsyncMock()
        mock_messaging_app.broker.close.side_effect = Exception("Close error")

        with patch(
            "edcpy.backend.start_messaging_app", return_value=mock_messaging_app
        ):
            # Should not raise an exception even if broker close fails
            async with lifespan(mock_app):
                pass

            # Verify that the broker close was attempted
            mock_messaging_app.broker.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_startup_failure(self):
        """Test that startup failure is handled properly."""

        mock_app = AsyncMock()

        with patch(
            "edcpy.backend.start_messaging_app", side_effect=Exception("Startup error")
        ):
            # Should raise the exception from start_messaging_app
            with pytest.raises(Exception, match="Startup error"):
                async with lifespan(mock_app):
                    pass

    def test_test_client_creation(self, test_client):
        """Test that the test client can be created successfully."""

        assert test_client is not None
        assert isinstance(test_client, TestClient)

    def test_app_state_access(self, test_client, mock_messaging_app):
        """Test that the messaging app can be accessed from app state."""

        # The test_client fixture should have set up the messaging app
        assert hasattr(test_client.app, "state")

        # Since we're using mocked startup, we need to verify the mock is working
        with patch(
            "edcpy.backend.start_messaging_app", return_value=mock_messaging_app
        ):
            # Create a new test client to trigger the lifespan
            with TestClient(app) as client:
                # The app should be accessible during the lifespan
                assert client.app is not None


class TestBackendConfiguration:
    """Test suite for backend configuration handling."""

    def test_get_messaging_app_dependency(self, test_client, mock_messaging_app):
        """Test that the messaging app dependency can be resolved."""

        from edcpy.backend import get_messaging_app

        # Create a mock request with app state
        mock_request = AsyncMock()
        mock_request.app.state.messaging_app = mock_messaging_app

        result = get_messaging_app(mock_request)
        assert result == mock_messaging_app

    def test_messaging_app_annotation(self):
        """Test that the MessagingAppDep annotation is properly defined."""

        from edcpy.backend import MessagingAppDep

        assert MessagingAppDep is not None
        # The annotation should be a type annotation
        assert hasattr(MessagingAppDep, "__origin__")


class TestBackendHealthCheck:
    """Test suite for basic backend health checks."""

    def test_app_routes_exist(self):
        """Test that the expected routes are registered."""

        routes = [
            getattr(route, "path", None)
            for route in app.routes
            if hasattr(route, "path")
        ]

        # Check that our main endpoints are registered
        assert "/pull" in routes
        assert "/push" in routes
        assert "/push/{routing_key_parts:path}" in routes

    def test_app_lifespan_configured(self):
        """Test that the app has lifespan configured."""

        assert app.router.lifespan_context is not None
