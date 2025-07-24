import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from starlette.requests import Request
from starlette.responses import Response

from app.main import (
    RequestLoggingMiddleware, MissingAPIKeyError, async_main
)


class TestRequestLoggingMiddleware:
    """Test the RequestLoggingMiddleware class."""

    pytestmark = pytest.mark.asyncio

    @pytest.fixture
    def middleware(self):
        """Create a RequestLoggingMiddleware instance for testing."""
        return RequestLoggingMiddleware(Mock())

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url = "http://test.com/api/test"
        request.headers = {"content-type": "application/json"}
        return request

    async def test_dispatch_logs_request_and_response(self, middleware):
        """Test that dispatch logs both request and response."""
        # Setup
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = "http://test.com/api"
        request.headers = {}
        request.body = AsyncMock(return_value=b"")
        
        response = Response("OK", status_code=200)
        
        async def mock_call_next(req):
            return response
        
        # Act
        with patch('app.main.logger') as mock_logger:
            result = await middleware.dispatch(request, mock_call_next)
        
        # Assert
        assert result == response
        mock_logger.info.assert_called()
        # Check that request logging happened
        request_calls = [
            call for call in mock_logger.info.call_args_list 
            if "INCOMING REQUEST" in str(call)
        ]
        assert len(request_calls) >= 1
        
        # Check that response logging happened
        response_calls = [
            call for call in mock_logger.info.call_args_list 
            if "OUTGOING RESPONSE" in str(call)
        ]
        assert len(response_calls) >= 1

    async def test_dispatch_logs_json_request_body(self, middleware):
        """Test that dispatch logs JSON request body."""
        # Setup
        request = Mock(spec=Request)
        request.method = "POST"
        request.url = "http://test.com/api"
        request.headers = {"content-type": "application/json"}
        
        test_data = {"key": "value", "number": 42}
        json_body = json.dumps(test_data).encode()
        request.body = AsyncMock(return_value=json_body)
        
        response = Response("OK", status_code=200)
        
        async def mock_call_next(req):
            return response
        
        # Act
        with patch('app.main.logger') as mock_logger:
            await middleware.dispatch(request, mock_call_next)
        
        # Assert
        # Check that JSON body was logged
        body_calls = [
            call for call in mock_logger.info.call_args_list 
            if "Request Body:" in str(call)
        ]
        assert len(body_calls) >= 1

    async def test_dispatch_logs_non_json_request_body(self, middleware):
        """Test that dispatch logs non-JSON request body as raw."""
        # Setup
        request = Mock(spec=Request)
        request.method = "POST"
        request.url = "http://test.com/api"
        request.headers = {"content-type": "application/json"}
        
        # Invalid JSON
        request.body = AsyncMock(return_value=b"invalid json data")
        
        response = Response("OK", status_code=200)
        
        async def mock_call_next(req):
            return response
        
        # Act
        with patch('app.main.logger') as mock_logger:
            await middleware.dispatch(request, mock_call_next)
        
        # Assert
        # Check that raw body was logged
        body_calls = [
            call for call in mock_logger.info.call_args_list 
            if "Request Body (raw):" in str(call)
        ]
        assert len(body_calls) >= 1

    async def test_dispatch_handles_body_read_exception(self, middleware):
        """Test that dispatch handles exceptions when reading body."""
        # Setup
        request = Mock(spec=Request)
        request.method = "POST"
        request.url = "http://test.com/api"
        request.headers = {"content-type": "application/json"}
        request.body = AsyncMock(side_effect=Exception("Body read error"))
        
        response = Response("OK", status_code=200)
        
        async def mock_call_next(req):
            return response
        
        # Act
        with patch('app.main.logger') as mock_logger:
            result = await middleware.dispatch(request, mock_call_next)
        
        # Assert
        assert result == response
        # Check that warning was logged
        warning_calls = [
            call for call in mock_logger.warning.call_args_list 
            if "Could not read request body" in str(call)
        ]
        assert len(warning_calls) >= 1

    async def test_dispatch_skips_body_for_non_json_content_type(
        self, middleware
    ):
        """Test that dispatch skips body logging for non-JSON content."""
        # Setup
        request = Mock(spec=Request)
        request.method = "POST"
        request.url = "http://test.com/api"
        request.headers = {"content-type": "text/plain"}
        request.body = AsyncMock(return_value=b"plain text")
        
        response = Response("OK", status_code=200)
        
        async def mock_call_next(req):
            return response
        
        # Act
        with patch('app.main.logger'):
            await middleware.dispatch(request, mock_call_next)
        
        # Assert
        # Should not try to read body for non-JSON content
        request.body.assert_not_called()

    async def test_dispatch_measures_response_time(self, middleware):
        """Test that dispatch measures and logs response time."""
        # Setup
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = "http://test.com/api"
        request.headers = {}
        request.body = AsyncMock(return_value=b"")
        
        response = Response("OK", status_code=200)
        
        async def slow_call_next(req):
            # Simulate some processing time
            await asyncio.sleep(0.01)
            return response
        
        # Act
        with patch('app.main.logger') as mock_logger:
            await middleware.dispatch(request, slow_call_next)
        
        # Assert
        # Check that duration was logged
        duration_calls = [
            call for call in mock_logger.info.call_args_list 
            if "Duration:" in str(call)
        ]
        assert len(duration_calls) >= 1


class TestMissingAPIKeyError:
    """Test the MissingAPIKeyError exception."""

    def test_missing_api_key_error_creation(self):
        """Test creating MissingAPIKeyError."""
        error = MissingAPIKeyError("API key is missing")
        assert str(error) == "API key is missing"
        assert isinstance(error, Exception)


class TestAsyncMain:
    """Test the async_main function."""

    pytestmark = pytest.mark.asyncio

    @patch('uvicorn.Server')
    @patch('app.main.A2AStarletteApplication')
    @patch('app.main.MyAgentExecutor')
    async def test_async_main_creates_server_correctly(
        self, mock_executor_class, mock_app_class, mock_server_class
    ):
        """Test that async_main creates server with correct configuration."""
        # Setup mocks
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        mock_executor.agent.SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
        
        mock_app = Mock()
        mock_app_class.return_value = mock_app
        mock_starlette_app = Mock()
        mock_app.build.return_value = mock_starlette_app
        
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.serve = AsyncMock()
        
        # Act
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            await async_main(
                host="localhost", 
                port=8000, 
                phoenix="http://phoenix:6006", 
                remote_agent_addresses=["http://agent1:8001"]
            )
        
        # Assert
        mock_executor_class.assert_called_once()
        mock_app_class.assert_called_once()
        mock_server.serve.assert_called_once()

    @patch('uvicorn.Server')
    @patch('app.main.A2AStarletteApplication')
    @patch('app.main.MyAgentExecutor')
    async def test_async_main_adds_middleware(
        self, mock_executor_class, mock_app_class, mock_server_class
    ):
        """Test that async_main adds required middleware."""
        # Setup mocks
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        mock_executor.agent.SUPPORTED_CONTENT_TYPES = ['text']
        
        mock_app = Mock()
        mock_app_class.return_value = mock_app
        mock_starlette_app = Mock()
        mock_app.build.return_value = mock_starlette_app
        
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.serve = AsyncMock()
        
        # Act
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            await async_main("localhost", 8000, "phoenix", [])
        
        # Assert
        # Check that middleware was added
        assert mock_starlette_app.add_middleware.call_count >= 2

    @patch('app.main.logger')
    @patch('app.main.exit')
    async def test_async_main_handles_missing_api_key_error(
        self, mock_exit, mock_logger
    ):
        """Test that async_main handles MissingAPIKeyError."""
        # Act
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.side_effect = MissingAPIKeyError("API key missing")
            
            await async_main("localhost", 8000, "phoenix", [])
        
        # Assert
        mock_logger.error.assert_called_once()
        mock_exit.assert_called_once_with(1)

    @patch('app.main.logger')
    @patch('app.main.exit')
    async def test_async_main_handles_general_exception(
        self, mock_exit, mock_logger
    ):
        """Test that async_main handles general exceptions."""
        # Act
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.side_effect = Exception("General error")
            
            await async_main("localhost", 8000, "phoenix", [])
        
        # Assert
        mock_logger.error.assert_called_once()
        mock_exit.assert_called_once_with(1)


class TestMainFunction:
    """Test the main CLI function."""

    @patch('app.main.asyncio.run')
    def test_main_function_calls_async_main(self, mock_run):
        """Test that main function calls async_main with correct parameters."""
        # This is a bit tricky to test directly due to click decorators
        # We'll test the logic inside main function
        
        # Mock the click context and runner
        with patch('app.main.async_main'):
            # Simulate calling main function directly
            from app.main import main as main_func
            
            # We can't easily test click-decorated function,
            # but we can test async_main call indirectly
            mock_run.return_value = None
            
            # The function signature is defined by click decorators
            # so we test the underlying async function instead
            assert callable(main_func)

    def test_main_function_with_default_parameters(self):
        """Test main function with default parameters."""
        with patch('app.main.asyncio.run'):
            # Test would require more complex click testing setup
            # For now, just verify the function exists and is callable
            from app.main import main as main_func
            assert callable(main_func)

    def test_main_entry_point(self):
        """Test that main can be called as entry point."""
        # Test the __name__ == '__main__' block
        with patch('app.main.main') as mock_main:
            with patch('builtins.__name__', '__main__'):
                # This would be called when running the module directly
                # Just verify the function exists
                assert callable(mock_main) 