import pytest
import httpx
from unittest.mock import Mock, patch
from app.router_agent import RouterAgent, LimitedContextGetSessionService
from google.adk.sessions.session import Session
from google.adk.sessions.base_session_service import GetSessionConfig


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing."""
    return Mock(spec=httpx.AsyncClient)


@pytest.fixture
def router_agent(mock_http_client):
    """Create a RouterAgent instance for testing."""
    return RouterAgent(
        mock_http_client, 
        ["http://agent1.test", "http://agent2.test"]
    )


class TestLimitedContextGetSessionService:
    """Test the LimitedContextGetSessionService class."""

    def test_initialization(self):
        """Test service initialization with default max events."""
        service = LimitedContextGetSessionService()
        assert service.max_recent_events_for_llm == 10

    def test_initialization_with_custom_limit(self):
        """Test service initialization with custom max events."""
        service = LimitedContextGetSessionService(
            max_recent_events_for_llm=5
        )
        assert service.max_recent_events_for_llm == 5

    def test_get_session_with_no_config(self):
        """Test get_session with no config applies default limit."""
        service = LimitedContextGetSessionService(
            max_recent_events_for_llm=3
        )
        
        # Mock the parent's get_session method
        with patch.object(
            service.__class__.__bases__[0], 'get_session'
        ) as mock_parent:
            mock_parent.return_value = Mock(spec=Session)
            
            service.get_session(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session"
            )
            
            # Verify that the parent method was called with our limit
            mock_parent.assert_called_once()
            args, kwargs = mock_parent.call_args
            assert kwargs['config'].num_recent_events == 3

    def test_get_session_with_config_no_limit(self):
        """Test get_session with config but no num_recent_events."""
        service = LimitedContextGetSessionService(
            max_recent_events_for_llm=3
        )
        config = GetSessionConfig()
        
        with patch.object(
            service.__class__.__bases__[0], 'get_session'
        ) as mock_parent:
            mock_parent.return_value = Mock(spec=Session)
            
            service.get_session(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                config=config
            )
            
            # Verify that the parent method was called with our limit
            mock_parent.assert_called_once()
            args, kwargs = mock_parent.call_args
            assert kwargs['config'].num_recent_events == 3

    def test_get_session_with_config_high_limit(self):
        """Test get_session with config requesting more events than our cap."""
        service = LimitedContextGetSessionService(
            max_recent_events_for_llm=3
        )
        config = GetSessionConfig(num_recent_events=10)
        
        with patch.object(
            service.__class__.__bases__[0], 'get_session'
        ) as mock_parent:
            mock_parent.return_value = Mock(spec=Session)
            
            service.get_session(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                config=config
            )
            
            # Verify that the parent method was called with our limit (capped)
            mock_parent.assert_called_once()
            args, kwargs = mock_parent.call_args
            assert kwargs['config'].num_recent_events == 3

    def test_get_session_with_config_low_limit(self):
        """Test get_session with config requesting fewer events than our cap."""
        service = LimitedContextGetSessionService(
            max_recent_events_for_llm=10
        )
        config = GetSessionConfig(num_recent_events=5)
        
        with patch.object(
            service.__class__.__bases__[0], 'get_session'
        ) as mock_parent:
            mock_parent.return_value = Mock(spec=Session)
            
            service.get_session(
                app_name="test_app",
                user_id="test_user",
                session_id="test_session",
                config=config
            )
            
            # Verify parent method was called with original limit (not capped)
            mock_parent.assert_called_once()
            args, kwargs = mock_parent.call_args
            assert kwargs['config'].num_recent_events == 5


class TestRouterAgent:
    """Test the RouterAgent class."""

    def test_initialization(self, mock_http_client):
        """Test RouterAgent initialization."""
        agent = RouterAgent(mock_http_client, ["http://agent1.test"])
        assert agent._user_id == 'remote_agent'
        assert agent._agent is not None
        assert agent._runner is not None

    def test_get_processing_message(self, router_agent):
        """Test get_processing_message returns expected message."""
        message = router_agent.get_processing_message()
        assert message == 'Processing the reimbursement request...'

    def test_supported_content_types(self):
        """Test that supported content types are defined correctly."""
        assert RouterAgent.SUPPORTED_CONTENT_TYPES == ['text', 'text/plain']

    @patch('app.router_agent.HostAgent')
    def test_build_agent(self, mock_host_agent_class, mock_http_client):
        """Test _build_agent method creates HostAgent correctly."""
        mock_host_agent = Mock()
        mock_host_agent.create_agent.return_value = Mock()
        mock_host_agent_class.return_value = mock_host_agent
        
        agent = RouterAgent(mock_http_client, ["http://agent1.test"])
        
        # Verify HostAgent was created with correct parameters
        mock_host_agent_class.assert_called_once_with(
            ["http://agent1.test"], 
            mock_http_client
        )
        mock_host_agent.create_agent.assert_called_once()
        
        # Use the agent variable to avoid linter warning
        assert agent._user_id == 'remote_agent' 