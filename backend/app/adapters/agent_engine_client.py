"""
Vertex AI Agent Engine Client Adapter.
Supports hybrid execution:
1. When `AGENT_ENGINE_RESOURCE_NAME` is configured, queries are delegated to the hosted Vertex AI Reasoning Engine on GCP.
2. Otherwise, gracefully executes the official ADK in-process multi-agent tree.
"""

import os
import logging
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class AgentEngineClient:
    def __init__(self, resource_name: Optional[str] = None):
        self.resource_name = resource_name or os.getenv("AGENT_ENGINE_RESOURCE_NAME")
        self._remote_engine = None
        if self.resource_name:
            try:
                import vertexai
                from vertexai.preview import reasoning_engines
                project = os.getenv("GCP_PROJECT_ID", "agentic-cinema-prod")
                location = os.getenv("GCP_REGION", "us-central1")
                vertexai.init(project=project, location=location)
                self._remote_engine = reasoning_engines.ReasoningEngine(self.resource_name)
                logger.info(f"Connected to remote Vertex AI Agent Engine: {self.resource_name}")
            except Exception as e:
                logger.warning(f"Failed to connect to remote Agent Engine ({e}); running in-process ADK fallback.")
                self._remote_engine = None

    def execute_story_generation(self, topic: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes multi-agent story generation, either remotely via Agent Engine or locally via ADK.
        """
        if self._remote_engine is not None:
            try:
                logger.info(f"Delegating story generation to remote Agent Engine: {self.resource_name}")
                response = self._remote_engine.query(topic=topic, context=context or {})
                return {
                    "execution_mode": "remote_agent_engine",
                    "resource_name": self.resource_name,
                    "result": response
                }
            except Exception as e:
                logger.error(f"Remote Agent Engine query failed ({e}); switching to local ADK fallback.")

        # In-process ADK execution fallback
        from app.agents.orchestrator_agent import orchestrator_agent
        result = orchestrator_agent.orchestrate_scene_generation(
            project_id="agent-engine-local",
            topic=topic,
            scene_number=1,
            total_scenes=3
        )
        return {
            "execution_mode": "in_process_adk",
            "resource_name": None,
            "result": result
        }


agent_engine_client = AgentEngineClient()
