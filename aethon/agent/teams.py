"""Team orchestrator for multi-agent execution.

Supports Swarm (collaborative handoff) and Graph (deterministic pipeline) modes.
"""

import logging

from strands import Agent
from strands.multiagent import Swarm, GraphBuilder

from aethon.agent.specialists import SpecialistFactory
from aethon.config import MultiAgentConfig


logger = logging.getLogger("aethon.teams")


class TeamOrchestrator:
    """Multi-agent team management with Swarm and Graph modes."""

    def __init__(
        self,
        specialist_factory: SpecialistFactory,
        orchestrator: Agent,
        config: MultiAgentConfig,
    ):
        self.factory = specialist_factory
        self.orchestrator = orchestrator
        self.config = config

    def collaborative_task(self, task: str) -> str:
        """Swarm mode — agents hand off tasks to each other."""
        specialists = self.factory.get_all()
        all_agents = [self.orchestrator] + list(specialists.values())

        swarm = Swarm(
            nodes=all_agents,
            entry_point=self.orchestrator,
            max_handoffs=self.config.max_handoffs,
            max_iterations=self.config.max_iterations,
            execution_timeout=self.config.execution_timeout,
            node_timeout=self.config.node_timeout,
        )

        logger.info(f"Swarm starting: {len(all_agents)} agents")
        result = swarm(task)
        return self._extract_result(result)

    def pipeline_task(self, task: str, pipeline: list[str] | None = None) -> str:
        """Graph mode — deterministic sequential pipeline."""
        if pipeline is None:
            pipeline = ["planner", "researcher", "coder"]

        builder = GraphBuilder()

        nodes = {}
        for spec_name in pipeline:
            agent = self.factory.get(spec_name)
            node = builder.add_node(agent, spec_name)
            nodes[spec_name] = node

        for i in range(len(pipeline) - 1):
            builder.add_edge(nodes[pipeline[i]], nodes[pipeline[i + 1]])

        builder.set_entry_point(pipeline[0])
        builder.set_execution_timeout(self.config.execution_timeout)
        builder.set_node_timeout(self.config.node_timeout)

        graph = builder.build()

        logger.info(f"Graph pipeline starting: {' -> '.join(pipeline)}")
        result = graph(task)
        return self._extract_result(result)

    @staticmethod
    def _extract_result(result) -> str:
        """Extract text from MultiAgentResult."""
        for node_result in reversed(list(result.results.values())):
            agent_results = node_result.get_agent_results()
            if agent_results:
                text = str(agent_results[-1]).strip()
                if text:
                    return text
        return "No result available."
