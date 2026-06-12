"""
Bedrock AgentCore integration for Procurement Optimization Agent.

Provides natural language interface to optimization engine using Amazon Nova Pro.
Follows CDE standards:
- Type hints on all functions
- Error handling for AWS API calls
- Structured logging
- No hardcoded secrets
"""

import json
import uuid
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError
import structlog

from config.settings import settings

logger = structlog.get_logger()


class BedrockAgent:
    """
    Bedrock AgentCore wrapper for procurement optimization.
    
    Manages conversation state, tool orchestration, and natural language
    interface to the optimization engine.
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        region: Optional[str] = None
    ):
        """
        Initialize Bedrock agent client.
        
        Args:
            agent_id: Bedrock agent ID (defaults to settings)
            region: AWS region (defaults to settings)
        """
        self.agent_id = agent_id or settings.bedrock_agent_id
        self.region = region or settings.aws_region
        
        if not self.agent_id:
            raise ValueError("BEDROCK_AGENT_ID must be set in environment")
        
        self.client = boto3.client(
            "bedrock-agent-runtime",
            region_name=self.region
        )
        
        logger.info(
            "bedrock_agent_initialized",
            agent_id=self.agent_id,
            region=self.region
        )
    
    def invoke(
        self,
        input_text: str,
        session_id: Optional[str] = None,
        session_attributes: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Invoke Bedrock agent with natural language input.
        
        Args:
            input_text: User's natural language query
            session_id: Session ID for conversation continuity
            session_attributes: Additional session context
        
        Returns:
            Agent response with completion text and trace
        
        Raises:
            ValueError: If input is invalid
            ClientError: If AWS API call fails
        """
        if not input_text or not input_text.strip():
            raise ValueError("input_text cannot be empty")
        
        session_id = session_id or self._generate_session_id()
        
        logger.info(
            "invoking_bedrock_agent",
            agent_id=self.agent_id,
            session_id=session_id,
            input_length=len(input_text)
        )
        
        try:
            response = self.client.invoke_agent(
                agentId=self.agent_id,
                agentAliasId="TSTALIASID",  # Use test alias for development
                sessionId=session_id,
                inputText=input_text,
                sessionState={
                    "sessionAttributes": session_attributes or {}
                }
            )
            
            # Parse streaming response
            completion = self._parse_streaming_response(response)
            
            logger.info(
                "bedrock_agent_invoked",
                agent_id=self.agent_id,
                session_id=session_id,
                completion_length=len(completion.get("completion", ""))
            )
            
            return {
                "session_id": session_id,
                "completion": completion.get("completion", ""),
                "trace": completion.get("trace", []),
                "citations": completion.get("citations", [])
            }
        
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            
            if error_code == "ThrottlingException":
                logger.warning(
                    "bedrock_throttled",
                    agent_id=self.agent_id,
                    session_id=session_id
                )
                raise
            
            elif error_code == "ValidationException":
                logger.error(
                    "bedrock_validation_error",
                    agent_id=self.agent_id,
                    error=str(e)
                )
                raise ValueError(f"Invalid agent input: {e}")
            
            elif error_code == "ResourceNotFoundException":
                logger.error(
                    "bedrock_agent_not_found",
                    agent_id=self.agent_id
                )
                raise ValueError(f"Agent not found: {self.agent_id}")
            
            else:
                logger.error(
                    "bedrock_agent_error",
                    agent_id=self.agent_id,
                    error_code=error_code,
                    error=str(e)
                )
                raise
        
        except Exception as e:
            logger.error(
                "bedrock_agent_unexpected_error",
                agent_id=self.agent_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    def _parse_streaming_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse streaming response from Bedrock agent.
        
        Args:
            response: Streaming response from invoke_agent
        
        Returns:
            Parsed completion with text, trace, and citations
        """
        completion_text = ""
        trace_events = []
        citations = []
        
        try:
            event_stream = response.get("completion", [])
            
            for event in event_stream:
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        completion_text += chunk["bytes"].decode("utf-8")
                
                elif "trace" in event:
                    trace_events.append(event["trace"])
                
                elif "returnControl" in event:
                    # Handle return control for tool use
                    trace_events.append({
                        "type": "returnControl",
                        "data": event["returnControl"]
                    })
                
                elif "citation" in event:
                    citations.append(event["citation"])
            
            return {
                "completion": completion_text,
                "trace": trace_events,
                "citations": citations
            }
        
        except Exception as e:
            logger.error(
                "failed_to_parse_streaming_response",
                error=str(e)
            )
            return {
                "completion": "",
                "trace": [],
                "citations": []
            }
    
    def _generate_session_id(self) -> str:
        """
        Generate unique session ID.
        
        Returns:
            UUID-based session ID
        """
        return str(uuid.uuid4())


class BedrockConversation:
    """
    Manages multi-turn conversation with Bedrock agent.
    
    Maintains session state and conversation history.
    """
    
    def __init__(self, agent: BedrockAgent):
        """
        Initialize conversation manager.
        
        Args:
            agent: BedrockAgent instance
        """
        self.agent = agent
        self.session_id = str(uuid.uuid4())
        self.history: List[Dict[str, str]] = []
        self.session_attributes: Dict[str, str] = {}
        
        logger.info(
            "conversation_started",
            session_id=self.session_id
        )
    
    def send_message(
        self,
        message: str,
        attributes: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Send message in conversation context.
        
        Args:
            message: User message
            attributes: Additional session attributes
        
        Returns:
            Agent's response text
        """
        # Update session attributes
        if attributes:
            self.session_attributes.update(attributes)
        
        # Invoke agent
        response = self.agent.invoke(
            input_text=message,
            session_id=self.session_id,
            session_attributes=self.session_attributes
        )
        
        # Update history
        self.history.append({
            "role": "user",
            "content": message
        })
        self.history.append({
            "role": "assistant",
            "content": response["completion"]
        })
        
        return response["completion"]
    
    def get_history(self) -> List[Dict[str, str]]:
        """
        Get conversation history.
        
        Returns:
            List of message dictionaries
        """
        return self.history.copy()
    
    def clear_history(self) -> None:
        """Clear conversation history and start new session."""
        self.session_id = str(uuid.uuid4())
        self.history = []
        self.session_attributes = {}
        
        logger.info(
            "conversation_cleared",
            new_session_id=self.session_id
        )
