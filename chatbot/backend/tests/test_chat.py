import pytest
import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app


class MockLiteLLMService:
    """Mock LiteLLM service for testing"""
    
    @property
    def is_available(self) -> bool:
        return True
    
    async def get_completion(self, message: str, user_id: str = None, conversation_history = None) -> str:
        if not message.strip():
            return "I received an empty message. How can I help you?"
        return f"Mock LLM response to: {message}"
    
    async def get_streaming_completion(self, message: str, user_id: str = None, conversation_history = None):
        """Mock streaming completion"""
        if not message.strip():
            chunks = ["I received an empty message. ", "How can I help you?"]
        else:
            chunks = ["Mock ", "LLM ", "streaming ", f"response to: {message}"]
        
        for chunk in chunks:
            yield chunk


@pytest.fixture
def mock_litellm_service():
    """Fixture to provide mocked LiteLLM service"""
    return MockLiteLLMService()


def test_chat_completion_non_streaming(mock_litellm_service):
    """Test non-streaming chat completion endpoint with mocked LiteLLM"""
    client = TestClient(app)
    
    with patch('app.services.litellm_service.litellm_service', mock_litellm_service):
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "message": "Hello, test!",
                "stream": False
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "message" in data
    assert "usage" in data
    
    # Check message structure
    message = data["message"]
    assert "id" in message
    assert "text" in message
    assert "Mock LLM response to: Hello, test!" == message["text"]
    assert message["sender"] == "bot"
    assert "timestamp" in message
    
    # Check usage statistics
    usage = data["usage"]
    assert "prompt_tokens" in usage
    assert "completion_tokens" in usage
    assert "total_tokens" in usage


def test_chat_completion_streaming(mock_litellm_service):
    """Test streaming chat completion endpoint with mocked LiteLLM"""
    client = TestClient(app)
    
    with patch('app.services.litellm_service.litellm_service', mock_litellm_service):
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "message": "Hi there",
                "stream": True
            }
        )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert response.headers["cache-control"] == "no-cache"
    
    # Collect all events
    events = []
    content = ""
    
    # Parse SSE format
    for line in response.text.split('\n'):
        if line.startswith('data: '):
            try:
                event_data = json.loads(line[6:])
                events.append(event_data)
                if event_data.get("type") == "content":
                    content += event_data.get("content", "")
            except json.JSONDecodeError:
                pass
    
    # Check that we got events
    assert len(events) > 0
    
    # Check that we got content events
    content_events = [e for e in events if e.get("type") == "content"]
    assert len(content_events) > 0
    
    # Check that we got a done event
    done_events = [e for e in events if e.get("type") == "done"]
    assert len(done_events) == 1
    
    # Check the accumulated content contains expected response
    assert "Mock LLM streaming response to: Hi there" == content


def test_chat_completion_default_no_stream(mock_litellm_service):
    """Test that stream defaults to False when not provided"""
    client = TestClient(app)
    
    with patch('app.services.litellm_service.litellm_service', mock_litellm_service):
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "message": "Test default"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return non-streaming response
    assert "message" in data
    assert "Mock LLM response to: Test default" == data["message"]["text"]


def test_chat_completion_empty_message(mock_litellm_service):
    """Test handling of empty message"""
    client = TestClient(app)
    
    with patch('app.services.litellm_service.litellm_service', mock_litellm_service):
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "message": ""
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "I received an empty message. How can I help you?" == data["message"]["text"]


def test_chat_completion_with_user_id(mock_litellm_service):
    """Test chat completion with user_id"""
    client = TestClient(app)
    
    with patch('app.services.litellm_service.litellm_service', mock_litellm_service):
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "message": "Hello",
                "user_id": "test-user-123"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "Mock LLM response to: Hello" == data["message"]["text"]


def test_chat_completion_litellm_unavailable():
    """Test chat completion when LiteLLM service is unavailable"""
    
    class MockUnavailableLiteLLMService:
        @property
        def is_available(self) -> bool:
            return False
    
    client = TestClient(app)
    mock_service = MockUnavailableLiteLLMService()
    
    with patch('app.services.litellm_service.litellm_service', mock_service):
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "message": "Hello",
                "stream": False
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    # Should fallback to echo mode
    assert "Echo: Hello" in data["message"]["text"]
    assert "LLM service is not available" in data["message"]["text"]


def test_chat_completion_litellm_error(mock_litellm_service):
    """Test chat completion when Claude service throws an error"""
    
    class MockErrorLiteLLMService:
        @property
        def is_available(self) -> bool:
            return True
            
        async def get_completion(self, message: str, user_id: str = None, conversation_history = None) -> str:
            raise Exception("API rate limit exceeded")
    
    client = TestClient(app)
    mock_service = MockErrorLiteLLMService()
    
    with patch('app.services.litellm_service.litellm_service', mock_service):
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "message": "Hello",
                "stream": False
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    # Should fallback to echo mode with error message
    assert "Echo: Hello" in data["message"]["text"]
    assert "LLM encountered an error" in data["message"]["text"]
    assert "API rate limit exceeded" in data["message"]["text"]


def test_chat_completion_streaming_litellm_unavailable():
    """Test streaming chat completion when LiteLLM service is unavailable"""
    
    class MockUnavailableLiteLLMService:
        @property
        def is_available(self) -> bool:
            return False
    
    client = TestClient(app)
    mock_service = MockUnavailableLiteLLMService()
    
    with patch('app.services.litellm_service.litellm_service', mock_service):
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "message": "Hello",
                "stream": True
            }
        )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    # Parse response content
    content = ""
    for line in response.text.split('\n'):
        if line.startswith('data: '):
            try:
                event_data = json.loads(line[6:])
                if event_data.get("type") == "content":
                    content += event_data.get("content", "")
            except json.JSONDecodeError:
                pass
    
    assert "Echo: Hello" in content
    assert "LLM service is not available" in content