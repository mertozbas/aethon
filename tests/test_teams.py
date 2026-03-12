"""Tests for TeamOrchestrator."""

import pytest

from strands import Agent
from strands.models.ollama import OllamaModel

from aethon.agent.specialists import SpecialistFactory
from aethon.agent.teams import TeamOrchestrator
from aethon.config import MultiAgentConfig


@pytest.fixture
def model():
    return OllamaModel(
        host="http://localhost:11434",
        model_id="qwen3-coder-next",
    )


@pytest.fixture
def factory(model):
    return SpecialistFactory(model)


@pytest.fixture
def orchestrator_agent(model):
    return Agent(
        model=model,
        system_prompt="Sen AETHON orchestrator'sun. Gorevleri uygun uzmana yonlendir.",
        name="AETHON",
    )


@pytest.fixture
def team(factory, orchestrator_agent):
    config = MultiAgentConfig(
        execution_timeout=120.0,
        node_timeout=60.0,
        max_handoffs=5,
        max_iterations=5,
    )
    return TeamOrchestrator(factory, orchestrator_agent, config)


def test_team_creation(team):
    """TeamOrchestrator creates successfully."""
    assert team.factory is not None
    assert team.orchestrator is not None


def test_extract_result_empty():
    """_extract_result handles empty results."""

    class FakeResult:
        results = {}

    result = TeamOrchestrator._extract_result(FakeResult())
    assert result == "Sonuc alinamadi."


def test_pipeline_task(team):
    """Graph pipeline executes with real Ollama."""
    result = team.pipeline_task(
        "Merhaba de. Sadece 'Merhaba' yaz.",
        pipeline=["planner", "coder"],
    )
    assert isinstance(result, str)
    assert len(result) > 0
