"""
AgentCore Memory client for the procurement agent.

Uses the bedrock-agentcore data plane APIs:
- list-memory-records: List records by namespace
- retrieve-memory-records: Semantic search across memories
- batch-create-memory-records: Store new memories
- list-sessions: List agent sessions

Control plane (bedrock-agentcore-control):
- get-memory: Get memory resource details
"""

import os
import json
from typing import Dict, Any, List, Optional

import boto3
import structlog

logger = structlog.get_logger()

MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


class AgentCoreMemoryClient:
    """Client for AgentCore Memory data plane operations."""

    def __init__(self, memory_id: Optional[str] = None, region: Optional[str] = None):
        self._memory_id = memory_id or MEMORY_ID
        self._region = region or AWS_REGION
        self._data_client = boto3.client(
            "bedrock-agentcore",
            region_name=self._region,
        )
        self._control_client = boto3.client(
            "bedrock-agentcore-control",
            region_name=self._region,
        )

    # ── Control Plane ───────────────────────────────────────────────

    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory resource details (status, strategies, etc.)."""
        response = self._control_client.get_memory(
            memoryId=self._memory_id,
        )
        memory = response.get("memory", {})
        logger.info("memory_info_retrieved", memory_id=self._memory_id, status=memory.get("status"))
        return memory

    # ── Data Plane: List & Retrieve ─────────────────────────────────

    def list_records(
        self,
        namespace: str,
        strategy_id: Optional[str] = None,
        max_items: int = 50,
    ) -> List[Dict[str, Any]]:
        """List memory records in a namespace."""
        kwargs: Dict[str, Any] = {
            "memoryId": self._memory_id,
            "namespace": namespace,
            "maxItems": max_items,
        }
        if strategy_id:
            kwargs["memoryStrategyId"] = strategy_id

        response = self._data_client.list_memory_records(**kwargs)
        records = response.get("memoryRecordSummaries", [])
        logger.info("memory_records_listed", namespace=namespace, count=len(records))
        return records

    def retrieve_records(
        self,
        namespace: str,
        query: str,
        strategy_id: Optional[str] = None,
        max_items: int = 10,
    ) -> List[Dict[str, Any]]:
        """Semantic search for memory records."""
        search_criteria: Dict[str, Any] = {
            "query": query,
        }
        if strategy_id:
            search_criteria["memoryStrategyId"] = strategy_id

        response = self._data_client.retrieve_memory_records(
            memoryId=self._memory_id,
            namespace=namespace,
            searchCriteria=search_criteria,
            maxItems=max_items,
        )
        records = response.get("memoryRecordSummaries", [])
        logger.info("memory_records_retrieved", namespace=namespace, query=query, count=len(records))
        return records

    def get_record(self, memory_record_id: str) -> Dict[str, Any]:
        """Get a specific memory record by ID."""
        response = self._data_client.get_memory_record(
            memoryId=self._memory_id,
            memoryRecordId=memory_record_id,
        )
        return response

    # ── Data Plane: Sessions ────────────────────────────────────────

    def list_sessions(self, max_items: int = 20) -> List[Dict[str, Any]]:
        """List agent sessions."""
        response = self._data_client.list_sessions(
            memoryId=self._memory_id,
            maxItems=max_items,
        )
        sessions = response.get("sessions", response.get("items", []))
        logger.info("sessions_listed", count=len(sessions))
        return sessions

    # ── Data Plane: Create Records ──────────────────────────────────

    def create_records(
        self,
        namespace: str,
        records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Batch create memory records.

        Each record should have:
        - content: str (the memory content)
        - memoryStrategyId: str (optional, strategy to associate with)
        """
        response = self._data_client.batch_create_memory_records(
            memoryId=self._memory_id,
            namespace=namespace,
            memoryRecords=records,
        )
        logger.info("memory_records_created", namespace=namespace, count=len(records))
        return response

    def delete_record(self, memory_record_id: str) -> None:
        """Delete a memory record."""
        self._data_client.delete_memory_record(
            memoryId=self._memory_id,
            memoryRecordId=memory_record_id,
        )
        logger.info("memory_record_deleted", record_id=memory_record_id)
