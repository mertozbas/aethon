"""Delegate tools for multi-agent orchestration.

Each tool delegates a task to a specialist agent via SpecialistFactory.
"""

from strands import tool


_specialist_factory = None


def set_specialist_factory(factory):
    """Set the global specialist factory reference."""
    global _specialist_factory
    _specialist_factory = factory


def _extract_text(result) -> str:
    """Extract text from agent result."""
    return str(result).strip() or "No result returned."


@tool
def ask_coder(task: str) -> str:
    """Delegate a coding task to the coder specialist.
    The coder writes code, runs tests, debugs, and refactors.

    Args:
        task: Description of the coding task
    """
    if not _specialist_factory:
        return "Error: Specialist factory not started."
    coder = _specialist_factory.get("coder")
    result = coder(task)
    return _extract_text(result)


@tool
def ask_researcher(query: str) -> str:
    """Delegate a research task to the researcher specialist.
    The researcher performs web research, reads documentation, and gathers information.

    Args:
        query: Topic or question to research
    """
    if not _specialist_factory:
        return "Error: Specialist factory not started."
    researcher = _specialist_factory.get("researcher")
    result = researcher(query)
    return _extract_text(result)


@tool
def ask_analyst(data_task: str) -> str:
    """Delegate a data analysis task to the analyst specialist.
    The analyst performs data analysis, computation, chart generation, and report writing.

    Args:
        data_task: Description of the analysis task
    """
    if not _specialist_factory:
        return "Error: Specialist factory not started."
    analyst = _specialist_factory.get("analyst")
    result = analyst(data_task)
    return _extract_text(result)


@tool
def ask_planner(planning_task: str) -> str:
    """Delegate a planning task to the planner specialist.
    The planner breaks complex tasks into step-by-step plans and prioritizes them.

    Args:
        planning_task: Description of the task to plan
    """
    if not _specialist_factory:
        return "Error: Specialist factory not started."
    planner = _specialist_factory.get("planner")
    result = planner(planning_task)
    return _extract_text(result)
