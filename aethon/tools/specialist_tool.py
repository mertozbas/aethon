"""Dynamic specialist management tool (Phase 10 C5).

Provides the manage_specialists tool bound to a SpecialistFactory. Lets the agent
define, list, and remove custom specialists that persist across sessions
(workspace/specialists/*.json). Uses the closure pattern (like task_tool.py).
"""

from strands import tool

from aethon.agent.specialists import DYNAMIC_TOOL_ALLOWLIST, SAFE_DYNAMIC_TOOLS


def create_manage_specialists_tool(factory, *, allow_powerful: bool = False):
    """Create a manage_specialists tool bound to a SpecialistFactory.

    ``allow_powerful`` gates whether a custom specialist may be granted a powerful
    tool (shell/python_repl/file_write/editor/http_request — anything that can run
    code, mutate files, or reach the network); off by default. The factory also
    enforces this at tool resolution, so this is the clear-error UX layer.
    """

    @tool
    def manage_specialists(
        action: str,
        name: str = "",
        system_prompt: str = "",
        tools: str = "",
    ) -> str:
        """Define, list, or remove custom specialists (persisted across sessions).

        Raise a soldier for a need no built-in specialist covers, then delegate to
        it with ask_specialist(name, task).

        Args:
            action: "create" | "list" | "remove"
            name: The specialist's name (lower-cased + slugged into its key)
            system_prompt: What the specialist is and how it should work (create)
            tools: Comma-separated tool names from the allowlist (file_read,
                file_write, editor, shell, think, current_time, python_repl,
                http_request, calculator) — e.g. "file_read, think"
        """
        if action == "list":
            listing = factory.list_specialists()
            if not listing:
                return "No specialists."
            return "\n".join(f"- {k} ({kind})" for k, kind in sorted(listing.items()))

        if action == "remove":
            if not name:
                return "Error: 'name' is required."
            return (
                f"Specialist removed: {name}"
                if factory.remove_specialist(name)
                else f"No such custom specialist: {name}"
            )

        if action == "create":
            if not name:
                return "Error: 'name' is required."
            requested = [t.strip() for t in (tools or "").split(",") if t.strip()]
            unknown = [t for t in requested if t not in DYNAMIC_TOOL_ALLOWLIST]
            if unknown:
                return (
                    f"Error: tool(s) not allowed: {', '.join(unknown)}. "
                    f"Allowed: {', '.join(sorted(DYNAMIC_TOOL_ALLOWLIST))}"
                )
            powerful = [t for t in requested if t not in SAFE_DYNAMIC_TOOLS]
            if powerful and not allow_powerful:
                return (
                    f"Error: powerful tool(s) {', '.join(powerful)} are disabled "
                    f"(set core_loop.allow_powerful_specialists to enable). Safe "
                    f"tools: {', '.join(sorted(SAFE_DYNAMIC_TOOLS))}."
                )
            key = factory.add_specialist(name, system_prompt, requested)
            return f"Specialist created: {key} (tools: {', '.join(requested) or 'think'})"

        return f"Unknown action: {action}. Supported: create, list, remove"

    return manage_specialists
