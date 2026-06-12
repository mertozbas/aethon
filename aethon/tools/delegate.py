"""Delegate tools for multi-agent orchestration.

Each tool delegates a task to a specialist agent via SpecialistFactory.
"""

import logging

from strands import tool

logger = logging.getLogger("aethon.delegate")

_specialist_factory = None
# Phase 10 C2: the planner persists its structured plan straight into the ledger.
_plan_ledger = None
_plan_approval = False


def set_specialist_factory(factory):
    """Set the global specialist factory reference."""
    global _specialist_factory
    _specialist_factory = factory


def set_plan_ledger(ledger, plan_approval: bool = False):
    """Wire the planner's plan→ledger pipeline (Phase 10 C2). When set,
    ask_planner writes its structured plan into this ledger as a project tree."""
    global _plan_ledger, _plan_approval
    _plan_ledger = ledger
    _plan_approval = plan_approval


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
def ask_scout(query: str) -> str:
    """Delegate a "read many, return little" investigation to the scout.

    The scout reads the sources you point it at (files, code, logs) and returns
    a CONCISE conclusion — keeping the raw dumps out of your context. Use it for
    "read these files and tell me X" / "where is Y handled?": the bulk stays with
    the scout, and only the answer enters your turn.

    Args:
        query: What to find out, and which sources/paths to look at
    """
    if not _specialist_factory:
        return "Error: Specialist factory not started."
    scout = _specialist_factory.get("scout")
    result = scout(query)
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


def plan_into_ledger(
    planning_task: str, *, origin_channel: str = "", origin_recipient: str = ""
) -> dict | None:
    """Run the planner for a task and persist a STRUCTURED plan into the ledger.

    Returns the ``persist_plan`` result (``{project_id, task_ids, summary}``) or
    ``None`` when the pipeline isn't wired or the planner produced no structured
    tasks (a provider that can't force structured output). Shared by the
    ask_planner tool and the C1 intake branch so both open a project the same way
    (no double-creation — persist_plan owns the parent task). ``origin_*`` are
    stamped on the project so the C3 executor can deliver pulses/receipt back.
    """
    if not _specialist_factory or _plan_ledger is None:
        return None
    try:
        from aethon.agent.planning import PlanSchema, persist_plan

        planner = _specialist_factory.get("planner")
        # Non-deprecated structured-output path: force the planner's reply into
        # PlanSchema via the agent invocation, then read the validated model off
        # the result.
        outcome = planner(planning_task, structured_output_model=PlanSchema)
        plan = getattr(outcome, "structured_output", None)
        if plan and plan.tasks:
            return persist_plan(
                _plan_ledger, plan, plan_approval=_plan_approval,
                origin_channel=origin_channel, origin_recipient=origin_recipient,
            )
    except Exception as e:
        logger.warning(
            f"plan_into_ledger failed ({type(e).__name__}: {e})."
        )
    return None


@tool
def ask_planner(planning_task: str) -> str:
    """Delegate a planning task to the planner specialist.
    The planner breaks complex tasks into step-by-step plans and prioritizes them.

    When the task ledger is wired (Phase 10), the plan is written straight into
    the ledger as a dependency-ordered project tree and a summary is returned.

    Args:
        planning_task: Description of the task to plan
    """
    if not _specialist_factory:
        return "Error: Specialist factory not started."

    # Phase 10 C2: structured plan → ledger, with a free-text fallback so a
    # provider that can't force structured output still returns a usable plan.
    result = plan_into_ledger(planning_task)
    if result:
        return result["summary"]
    logger.info("ask_planner: no structured plan persisted; using free-text plan.")
    planner = _specialist_factory.get("planner")
    return _extract_text(planner(planning_task))
