import pytest
import httpx
from unittest.mock import Mock, patch
from uuid import uuid4

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    Task, TaskState, TextPart
)

from app.agent_executor import MyAgentExecutor


pytestmark = pytest.mark.asyncio


async def async_list_iterator(items):
    """Helper to create async iterator from list."""
    for item in items:
        yield item


class TestMyAgentExecutor:
    """Test the MyAgentExecutor class."""

    @pytest.fixture
    def mock_http_client(self):
        """Mock HTTP client for testing."""
        return Mock(spec=httpx.AsyncClient)

    @pytest.fixture
    def agent_executor(self, mock_http_client):
        """Create a MyAgentExecutor instance for testing."""
        return MyAgentExecutor(mock_http_client, ["http://agent1.test"])

    @pytest.fixture
    def mock_context(self):
        """Create a mock RequestContext."""
        context = Mock(spec=RequestContext)
        context.get_user_input.return_value = "Test query"
        context.current_task = None
        context.contextId = str(uuid4())
        
        # Mock message
        mock_message = Mock()
        mock_message.parts = [Mock()]
        mock_message.parts[0].root = TextPart(text="Test message")
        context.message = mock_message
        
        return context

    @pytest.fixture
    def mock_context_with_task(self):
        """Create a mock RequestContext with existing task."""
        context = Mock(spec=RequestContext)
        context.get_user_input.return_value = "Test query"
        
        # Create mock task
        mock_task = Mock(spec=Task)
        mock_task.id = str(uuid4())
        mock_task.contextId = str(uuid4())
        context.current_task = mock_task
        context.contextId = mock_task.contextId
        
        # Mock message
        mock_message = Mock()
        mock_message.parts = [Mock()]
        mock_message.parts[0].root = TextPart(text="Test message")
        context.message = mock_message
        
        return context

    @pytest.fixture
    def mock_event_queue(self):
        """Create a mock EventQueue."""
        return Mock(spec=EventQueue)

    def test_initialization(self, mock_http_client):
        """Test MyAgentExecutor initialization."""
        executor = MyAgentExecutor(mock_http_client, ["http://agent1.test"])
        assert executor.agent is not None

    @patch('app.agent_executor.new_task')
    @patch('app.agent_executor.TaskUpdater')
    async def test_execute_creates_new_task_when_none_exists(
        self, mock_task_updater_class, mock_new_task, 
        agent_executor, mock_context, mock_event_queue
    ):
        """Test execute creates new task when none exists."""
        # Setup
        mock_new_task.return_value = Mock()
        mock_new_task.return_value.id = str(uuid4())
        mock_new_task.return_value.contextId = str(uuid4())
        
        mock_task_updater = Mock()
        mock_task_updater_class.return_value = mock_task_updater
        
        # Mock agent stream to return complete task
        async def mock_stream(query, context_id):
            items = [
                {
                    'is_task_complete': True,
                    'content': 'Task completed successfully'
                }
            ]
            for item in items:
                yield item
        
        agent_executor.agent.stream = mock_stream

        # Act
        await agent_executor.execute(mock_context, mock_event_queue)

        # Assert
        mock_new_task.assert_called_once_with(mock_context.message)
        mock_event_queue.enqueue_event.assert_called_once()
        mock_task_updater.complete.assert_called_once()

    @patch('app.agent_executor.TaskUpdater')
    async def test_execute_uses_existing_task(
        self, mock_task_updater_class, 
        agent_executor, mock_context_with_task, mock_event_queue
    ):
        """Test execute uses existing task when one exists."""
        # Setup
        mock_task_updater = Mock()
        mock_task_updater_class.return_value = mock_task_updater
        
        # Mock agent stream to return complete task
        async def mock_stream(query, context_id):
            items = [
                {
                    'is_task_complete': True,
                    'content': 'Task completed successfully'
                }
            ]
            for item in items:
                yield item
        
        agent_executor.agent.stream = mock_stream

        # Act
        await agent_executor.execute(mock_context_with_task, mock_event_queue)

        # Assert
        # Should not enqueue new event since task already exists
        mock_event_queue.enqueue_event.assert_not_called()
        mock_task_updater.complete.assert_called_once()

    @patch('app.agent_executor.TaskUpdater')
    async def test_execute_handles_incomplete_task(
        self, mock_task_updater_class,
        agent_executor, mock_context, mock_event_queue
    ):
        """Test execute handles incomplete task updates."""
        # Setup
        mock_task_updater = Mock()
        mock_task_updater_class.return_value = mock_task_updater
        
        with patch('app.agent_executor.new_task') as mock_new_task:
            mock_new_task.return_value = Mock()
            mock_new_task.return_value.id = str(uuid4())
            mock_new_task.return_value.contextId = str(uuid4())
            
            # Mock agent stream to return incomplete then complete task
            async def mock_stream(query, context_id):
                items = [
                    {
                        'is_task_complete': False,
                        'updates': 'Processing...'
                    },
                    {
                        'is_task_complete': True,
                        'content': 'Task completed successfully'
                    }
                ]
                for item in items:
                    yield item
            
            agent_executor.agent.stream = mock_stream

            # Act
            await agent_executor.execute(mock_context, mock_event_queue)

            # Assert
            mock_task_updater.update_status.assert_called()
            mock_task_updater.complete.assert_called_once()

    @patch('app.agent_executor.TaskUpdater')
    async def test_execute_handles_dict_response_with_valid_form(
        self, mock_task_updater_class,
        agent_executor, mock_context, mock_event_queue
    ):
        """Test execute handles dictionary response with valid form."""
        # Setup
        mock_task_updater = Mock()
        mock_task_updater_class.return_value = mock_task_updater
        
        with patch('app.agent_executor.new_task') as mock_new_task:
            mock_new_task.return_value = Mock()
            mock_new_task.return_value.id = str(uuid4())
            mock_new_task.return_value.contextId = str(uuid4())
            
            # Mock agent stream to return dict response
            async def mock_stream(query, context_id):
                items = [
                    {
                        'is_task_complete': True,
                        'content': {
                            'response': {
                                'result': [{'form_data': 'test_value'}]
                            }
                        }
                    }
                ]
                for item in items:
                    yield item
            
            agent_executor.agent.stream = mock_stream

            # Act
            await agent_executor.execute(mock_context, mock_event_queue)

            # Assert
            mock_task_updater.update_status.assert_called()
            # Should call update_status with input_required state
            call_args = mock_task_updater.update_status.call_args
            assert call_args[0][0] == TaskState.input_required

    @patch('app.agent_executor.TaskUpdater')
    async def test_execute_handles_dict_response_with_invalid_form(
        self, mock_task_updater_class,
        agent_executor, mock_context, mock_event_queue
    ):
        """Test execute handles dictionary response with invalid form."""
        # Setup
        mock_task_updater = Mock()
        mock_task_updater_class.return_value = mock_task_updater
        
        with patch('app.agent_executor.new_task') as mock_new_task:
            mock_new_task.return_value = Mock()
            mock_new_task.return_value.id = str(uuid4())
            mock_new_task.return_value.contextId = str(uuid4())
            
            # Mock agent stream to return invalid dict response
            async def mock_stream(query, context_id):
                items = [
                    {
                        'is_task_complete': True,
                        'content': {
                            'invalid': 'structure'
                        }
                    }
                ]
                for item in items:
                    yield item
            
            agent_executor.agent.stream = mock_stream

            # Act
            await agent_executor.execute(mock_context, mock_event_queue)

            # Assert
            mock_task_updater.update_status.assert_called()
            # Should call update_status with failed state
            call_args = mock_task_updater.update_status.call_args
            assert call_args[0][0] == TaskState.failed

    async def test_cancel_raises_unsupported_operation(
        self, agent_executor, mock_context, mock_event_queue
    ):
        """Test cancel method raises UnsupportedOperationError."""
        # ServerError wraps UnsupportedOperationError
        with pytest.raises(Exception):
            await agent_executor.cancel(mock_context, mock_event_queue) 