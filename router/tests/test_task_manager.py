import pytest
from unittest.mock import Mock
from app.task_manager import AgentWithTaskManager


pytestmark = pytest.mark.asyncio


class ConcreteAgentWithTaskManager(AgentWithTaskManager):
    """Concrete implementation of AgentWithTaskManager for testing."""
    
    def __init__(self):
        self._user_id = "test_user"
        self._runner = Mock()
        self._agent = Mock()
        self._agent.name = "test_agent"
    
    def get_processing_message(self) -> str:
        return "Processing test task..."


class TestAgentWithTaskManager:
    """Test the AgentWithTaskManager class."""

    @pytest.fixture
    def agent_manager(self):
        """Create a concrete instance for testing."""
        return ConcreteAgentWithTaskManager()

    def test_invoke_creates_new_session_when_none_exists(self, agent_manager):
        """Test invoke creates new session when none exists."""
        # Setup
        query = "Test query"
        session_id = "test_session_123"
        
        # Mock session service
        mock_session_service = Mock()
        mock_session_service.get_session.return_value = None
        mock_session_service.create_session.return_value = Mock(id=session_id)
        agent_manager._runner.session_service = mock_session_service
        
        # Mock runner.run to return events
        mock_event = Mock()
        mock_event.content = Mock()
        mock_event.content.parts = [Mock()]
        mock_event.content.parts[0].text = "Test response"
        agent_manager._runner.run.return_value = [mock_event]
        
        # Act
        result = agent_manager.invoke(query, session_id)
        
        # Assert
        mock_session_service.get_session.assert_called_once_with(
            app_name="test_agent",
            user_id="test_user",
            session_id=session_id
        )
        mock_session_service.create_session.assert_called_once()
        assert result == "Test response"

    def test_invoke_uses_existing_session(self, agent_manager):
        """Test invoke uses existing session when available."""
        # Setup
        query = "Test query"
        session_id = "test_session_123"
        
        # Mock session service with existing session
        mock_session = Mock(id=session_id)
        mock_session_service = Mock()
        mock_session_service.get_session.return_value = mock_session
        agent_manager._runner.session_service = mock_session_service
        
        # Mock runner.run to return events
        mock_event = Mock()
        mock_event.content = Mock()
        mock_event.content.parts = [Mock()]
        mock_event.content.parts[0].text = "Test response"
        agent_manager._runner.run.return_value = [mock_event]
        
        # Act
        result = agent_manager.invoke(query, session_id)
        
        # Assert
        mock_session_service.get_session.assert_called_once()
        mock_session_service.create_session.assert_not_called()
        assert result == "Test response"

    def test_invoke_handles_empty_events(self, agent_manager):
        """Test invoke handles empty events list."""
        # Setup
        query = "Test query"
        session_id = "test_session_123"
        
        # Mock session service
        mock_session = Mock(id=session_id)
        mock_session_service = Mock()
        mock_session_service.get_session.return_value = mock_session
        agent_manager._runner.session_service = mock_session_service
        
        # Mock runner.run to return empty events
        agent_manager._runner.run.return_value = []
        
        # Act
        result = agent_manager.invoke(query, session_id)
        
        # Assert
        assert result == ""

    def test_invoke_handles_no_content_in_last_event(self, agent_manager):
        """Test invoke handles event with no content."""
        # Setup
        query = "Test query"
        session_id = "test_session_123"
        
        # Mock session service
        mock_session = Mock(id=session_id)
        mock_session_service = Mock()
        mock_session_service.get_session.return_value = mock_session
        agent_manager._runner.session_service = mock_session_service
        
        # Mock runner.run to return event with no content
        mock_event = Mock()
        mock_event.content = None
        agent_manager._runner.run.return_value = [mock_event]
        
        # Act
        result = agent_manager.invoke(query, session_id)
        
        # Assert
        assert result == ""

    def test_invoke_handles_multiple_text_parts(self, agent_manager):
        """Test invoke handles multiple text parts in response."""
        # Setup
        query = "Test query"
        session_id = "test_session_123"
        
        # Mock session service
        mock_session = Mock(id=session_id)
        mock_session_service = Mock()
        mock_session_service.get_session.return_value = mock_session
        agent_manager._runner.session_service = mock_session_service
        
        # Mock runner.run to return event with multiple text parts
        mock_event = Mock()
        mock_event.content = Mock()
        mock_event.content.parts = [Mock(), Mock(), Mock()]
        mock_event.content.parts[0].text = "Part 1"
        mock_event.content.parts[1].text = "Part 2"
        mock_event.content.parts[2].text = None  # Test filtering
        agent_manager._runner.run.return_value = [mock_event]
        
        # Act
        result = agent_manager.invoke(query, session_id)
        
        # Assert
        assert result == "Part 1\nPart 2"

    async def test_stream_creates_new_session_when_none_exists(
        self, agent_manager
    ):
        """Test stream creates new session when none exists."""
        # Setup
        query = "Test query"
        session_id = "test_session_123"
        
        # Mock session service
        mock_session_service = Mock()
        mock_session_service.get_session.return_value = None
        created_session = Mock(id=session_id)
        mock_session_service.create_session.return_value = created_session
        agent_manager._runner.session_service = mock_session_service
        
        # Mock runner.run_async to return events
        async def mock_run_async(*args, **kwargs):
            mock_event = Mock()
            mock_event.is_final_response.return_value = True
            mock_event.content = Mock()
            mock_event.content.parts = [Mock()]
            mock_event.content.parts[0].text = "Final response"
            yield mock_event
        
        agent_manager._runner.run_async = mock_run_async
        
        # Act
        results = []
        async for result in agent_manager.stream(query, session_id):
            results.append(result)
        
        # Assert
        mock_session_service.create_session.assert_called_once()
        assert len(results) == 1
        assert results[0]['is_task_complete'] is True
        assert results[0]['content'] == "Final response"

    async def test_stream_handles_non_final_response(self, agent_manager):
        """Test stream handles non-final response."""
        # Setup
        query = "Test query"
        session_id = "test_session_123"
        
        # Mock session service
        mock_session = Mock(id=session_id)
        mock_session_service = Mock()
        mock_session_service.get_session.return_value = mock_session
        agent_manager._runner.session_service = mock_session_service
        
        # Mock runner.run_async to return non-final event
        async def mock_run_async(*args, **kwargs):
            mock_event = Mock()
            mock_event.is_final_response.return_value = False
            yield mock_event
        
        agent_manager._runner.run_async = mock_run_async
        
        # Act
        results = []
        async for result in agent_manager.stream(query, session_id):
            results.append(result)
        
        # Assert
        assert len(results) == 1
        assert results[0]['is_task_complete'] is False
        assert results[0]['updates'] == "Processing test task..."

    async def test_stream_handles_function_response(self, agent_manager):
        """Test stream handles function response in final event."""
        # Setup
        query = "Test query"
        session_id = "test_session_123"
        
        # Mock session service
        mock_session = Mock(id=session_id)
        mock_session_service = Mock()
        mock_session_service.get_session.return_value = mock_session
        agent_manager._runner.session_service = mock_session_service
        
        # Mock runner.run_async to return final event with function response
        async def mock_run_async(*args, **kwargs):
            mock_event = Mock()
            mock_event.is_final_response.return_value = True
            mock_event.content = Mock()
            mock_event.content.parts = [Mock()]
            mock_event.content.parts[0].text = None
            mock_event.content.parts[0].function_response = Mock()
            resp = {"result": "function_result"}
            func_resp = mock_event.content.parts[0].function_response
            func_resp.model_dump.return_value = resp
            yield mock_event
        
        agent_manager._runner.run_async = mock_run_async
        
        # Act
        results = []
        async for result in agent_manager.stream(query, session_id):
            results.append(result)
        
        # Assert
        assert len(results) == 1
        assert results[0]['is_task_complete'] is True
        assert results[0]['content'] == {"result": "function_result"} 