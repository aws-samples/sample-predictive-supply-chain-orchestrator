"""
Integration tests for Bedrock agent.

Uses moto for AWS service mocking.
Follows CDE standards: 70%+ coverage target.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from aws.bedrock.agent import BedrockAgent, BedrockConversation


class TestBedrockAgent:
    """Test suite for BedrockAgent class."""
    
    def test_init_with_agent_id(self):
        """Test agent initialization with explicit agent ID."""
        agent = BedrockAgent(agent_id="test-agent-123", region="us-east-1")
        
        assert agent.agent_id == "test-agent-123"
        assert agent.region == "us-east-1"
    
    def test_init_without_agent_id_raises_error(self):
        """Test that missing agent ID raises ValueError."""
        with patch("aws.bedrock.agent.settings") as mock_settings:
            mock_settings.bedrock_agent_id = ""
            mock_settings.aws_region = "us-east-1"
            
            with pytest.raises(ValueError, match="BEDROCK_AGENT_ID must be set"):
                BedrockAgent()
    
    @patch("aws.bedrock.agent.boto3.client")
    def test_invoke_success(self, mock_boto_client):
        """Test successful agent invocation."""
        # Setup mock
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock streaming response
        mock_response = {
            "completion": [
                {"chunk": {"bytes": b"Hello "}},
                {"chunk": {"bytes": b"World"}}
            ]
        }
        mock_client.invoke_agent.return_value = mock_response
        
        # Test
        agent = BedrockAgent(agent_id="test-agent", region="us-east-1")
        result = agent.invoke("Test input")
        
        # Verify
        assert "session_id" in result
        assert result["completion"] == "Hello World"
        assert isinstance(result["trace"], list)
        mock_client.invoke_agent.assert_called_once()
    
    @patch("aws.bedrock.agent.boto3.client")
    def test_invoke_empty_input_raises_error(self, mock_boto_client):
        """Test that empty input raises ValueError."""
        agent = BedrockAgent(agent_id="test-agent", region="us-east-1")
        
        with pytest.raises(ValueError, match="input_text cannot be empty"):
            agent.invoke("")
    
    @patch("aws.bedrock.agent.boto3.client")
    def test_invoke_throttling_error(self, mock_boto_client):
        """Test handling of throttling errors."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock throttling error
        error_response = {"Error": {"Code": "ThrottlingException"}}
        mock_client.invoke_agent.side_effect = ClientError(
            error_response,
            "InvokeAgent"
        )
        
        agent = BedrockAgent(agent_id="test-agent", region="us-east-1")
        
        with pytest.raises(ClientError):
            agent.invoke("Test input")
    
    @patch("aws.bedrock.agent.boto3.client")
    def test_invoke_validation_error(self, mock_boto_client):
        """Test handling of validation errors."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock validation error
        error_response = {"Error": {"Code": "ValidationException"}}
        mock_client.invoke_agent.side_effect = ClientError(
            error_response,
            "InvokeAgent"
        )
        
        agent = BedrockAgent(agent_id="test-agent", region="us-east-1")
        
        with pytest.raises(ValueError, match="Invalid agent input"):
            agent.invoke("Test input")
    
    @patch("aws.bedrock.agent.boto3.client")
    def test_invoke_resource_not_found(self, mock_boto_client):
        """Test handling of resource not found errors."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock resource not found error
        error_response = {"Error": {"Code": "ResourceNotFoundException"}}
        mock_client.invoke_agent.side_effect = ClientError(
            error_response,
            "InvokeAgent"
        )
        
        agent = BedrockAgent(agent_id="test-agent", region="us-east-1")
        
        with pytest.raises(ValueError, match="Agent not found"):
            agent.invoke("Test input")
    
    @patch("aws.bedrock.agent.boto3.client")
    def test_parse_streaming_response_with_trace(self, mock_boto_client):
        """Test parsing streaming response with trace events."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock response with trace
        mock_response = {
            "completion": [
                {"chunk": {"bytes": b"Response"}},
                {"trace": {"type": "orchestration", "data": "test"}}
            ]
        }
        mock_client.invoke_agent.return_value = mock_response
        
        agent = BedrockAgent(agent_id="test-agent", region="us-east-1")
        result = agent.invoke("Test")
        
        assert result["completion"] == "Response"
        assert len(result["trace"]) == 1
    
    def test_generate_session_id(self):
        """Test session ID generation."""
        agent = BedrockAgent(agent_id="test-agent", region="us-east-1")
        session_id = agent._generate_session_id()
        
        assert isinstance(session_id, str)
        assert len(session_id) > 0


class TestBedrockConversation:
    """Test suite for BedrockConversation class."""
    
    @patch("aws.bedrock.agent.boto3.client")
    def test_init(self, mock_boto_client):
        """Test conversation initialization."""
        agent = BedrockAgent(agent_id="test-agent", region="us-east-1")
        conversation = BedrockConversation(agent)
        
        assert conversation.agent == agent
        assert isinstance(conversation.session_id, str)
        assert len(conversation.history) == 0
        assert isinstance(conversation.session_attributes, dict)
    
    @patch("aws.bedrock.agent.boto3.client")
    def test_send_message(self, mock_boto_client):
        """Test sending message in conversation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock response
        mock_response = {
            "completion": [
                {"chunk": {"bytes": b"Agent response"}}
            ]
        }
        mock_client.invoke_agent.return_value = mock_response
        
        agent = BedrockAgent(agent_id="test-agent", region="us-east-1")
        conversation = BedrockConversation(agent)
        
        response = conversation.send_message("Hello")
        
        assert response == "Agent response"
        assert len(conversation.history) == 2
        assert conversation.history[0]["role"] == "user"
        assert conversation.history[0]["content"] == "Hello"
        assert conversation.history[1]["role"] == "assistant"
    
    @patch("aws.bedrock.agent.boto3.client")
    def test_send_message_with_attributes(self, mock_boto_client):
        """Test sending message with session attributes."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_response = {
            "completion": [
                {"chunk": {"bytes": b"Response"}}
            ]
        }
        mock_client.invoke_agent.return_value = mock_response
        
        agent = BedrockAgent(agent_id="test-agent", region="us-east-1")
        conversation = BedrockConversation(agent)
        
        conversation.send_message("Test", attributes={"key": "value"})
        
        assert conversation.session_attributes["key"] == "value"
    
    @patch("aws.bedrock.agent.boto3.client")
    def test_get_history(self, mock_boto_client):
        """Test getting conversation history."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_response = {
            "completion": [
                {"chunk": {"bytes": b"Response"}}
            ]
        }
        mock_client.invoke_agent.return_value = mock_response
        
        agent = BedrockAgent(agent_id="test-agent", region="us-east-1")
        conversation = BedrockConversation(agent)
        
        conversation.send_message("Message 1")
        conversation.send_message("Message 2")
        
        history = conversation.get_history()
        
        assert len(history) == 4  # 2 user + 2 assistant
        assert history[0]["content"] == "Message 1"
        assert history[2]["content"] == "Message 2"
    
    @patch("aws.bedrock.agent.boto3.client")
    def test_clear_history(self, mock_boto_client):
        """Test clearing conversation history."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_response = {
            "completion": [
                {"chunk": {"bytes": b"Response"}}
            ]
        }
        mock_client.invoke_agent.return_value = mock_response
        
        agent = BedrockAgent(agent_id="test-agent", region="us-east-1")
        conversation = BedrockConversation(agent)
        
        old_session_id = conversation.session_id
        conversation.send_message("Test")
        conversation.clear_history()
        
        assert len(conversation.history) == 0
        assert conversation.session_id != old_session_id
        assert len(conversation.session_attributes) == 0
