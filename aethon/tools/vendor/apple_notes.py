"""📝 Apple Notes tool — manage Apple Notes via AppleScript.

Provides non-interactive, programmatic access to Apple Notes.
"""

import logging
import os
import platform
import shutil
import subprocess
from typing import Any, Dict, Optional

from strands import tool

logger = logging.getLogger(__name__)

# Folders to skip (Recently Deleted in all languages)
_DELETED_FOLDERS = {
    "Recently Deleted",
    "Nylig slettet",
    "Senast raderade",
    "Senest slettet",
    "Zuletzt gelöscht",
    "Supprimés récemment",
    "Eliminados recientemente",
    "Eliminati di recente",
    "Recent verwijderd",
    "Ostatnio usunięte",
    "Недавно удалённые",
    "Apagados recentemente",
    "Apagadas recentemente",
    "最近删除",
    "最近刪除",
    "最近削除した項目",
    "최근 삭제된 항목",
    "Son Silinenler",
    "Äskettäin poistetut",
    "Nedávno smazané",
    "Πρόσφατα διαγραμμένα",
    "Nemrég töröltek",
    "Șterse recent",
    "Nedávno vymazané",
    "เพิ่งลบ",
    "Đã xóa gần đây",
    "Нещодавно видалені",
}


def _check_macos() -> Optional[str]:
    """Return error string if not macOS, else None."""
    if platform.system() != "Darwin":
        return "Apple Notes is only available on macOS."
    return None


def _run_applescript(script: str) -> subprocess.CompletedProcess:
    """Run an AppleScript and return the result."""
    return subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _escape_for_applescript(text: str) -> str:
    """Escape a string for safe embedding inside AppleScript double quotes."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _list_notes(folder: str = None) -> list[dict]:
    """Get all notes as list of dicts with id, folder, title."""
    script = """
    set deletedTranslations to {"Recently Deleted", "Nylig slettet", "Senast raderade", "Senest slettet", "Zuletzt gelöscht", "Supprimés récemment", "Eliminados recientemente", "Eliminati di recente", "Recent verwijderd", "Ostatnio usunięte", "Недавно удалённые", "Apagados recentemente", "Apagadas recentemente", "最近删除", "最近刪除", "最近削除した項目", "최근 삭제된 항목", "Son Silinenler", "Äskettäin poistetut", "Nedávno smazané", "Πρόσφατα διαγραμμένα", "Nemrég töröltek", "Șterse recent", "Nedávno vymazané", "เพิ่งลบ", "Đã xóa gần đây", "Нещодавно видалені"}

    tell application "Notes"
        set output to ""
        repeat with eachFolder in folders
            set folderName to name of eachFolder
            if folderName is not in deletedTranslations then
                repeat with eachNote in notes of eachFolder
                    set noteName to name of eachNote
                    set noteID to id of eachNote
                    set output to output & noteID & "|||" & folderName & "|||" & noteName & linefeed
                end repeat
            end if
        end repeat
        return output
    end tell
    """
    result = _run_applescript(script)
    if result.returncode != 0:
        return []

    notes = []
    seen_ids = set()
    for line in result.stdout.strip().split("\n"):
        if not line or "|||" not in line:
            continue
        parts = line.split("|||", 2)
        if len(parts) != 3:
            continue
        note_id, note_folder, note_title = (
            parts[0].strip(),
            parts[1].strip(),
            parts[2].strip(),
        )
        if note_id in seen_ids:
            continue
        seen_ids.add(note_id)
        if folder and note_folder.lower() != folder.lower():
            continue
        notes.append({"id": note_id, "folder": note_folder, "title": note_title})

    return notes


def _get_note_body(note_id: str, as_markdown: bool = True) -> str:
    """Get the body of a note by ID. Returns markdown by default."""
    escaped_id = _escape_for_applescript(note_id)
    script = f"""
    tell application "Notes"
        set selectedNote to first note whose id is "{escaped_id}"
        return body of selectedNote
    end tell
    """
    result = _run_applescript(script)
    if result.returncode != 0:
        return f"Error reading note: {result.stderr.strip()}"

    html_body = result.stdout.strip()
    if not as_markdown:
        return html_body

    # Convert HTML to markdown
    try:
        import html2text

        h = html2text.HTML2Text()
        h.images_to_alt = True
        h.body_width = 0
        return h.handle(html_body).strip()
    except ImportError:
        # Fallback: strip tags naively
        import re

        clean = re.sub(r"<[^>]+>", "", html_body)
        return clean.strip()


def _create_note(title: str, body: str, folder: str = "Notes") -> dict:
    """Create a note in Apple Notes. Body can be plain text or markdown."""
    # Convert markdown body to HTML
    try:
        import mistune

        body_html = mistune.markdown(body)
    except ImportError:
        # Fallback: wrap in paragraph tags
        body_html = f"<p>{body}</p>"

    # Prepend title as H1 if not already in body
    if not body.strip().startswith(f"# {title}"):
        body_html = f"<h1>{title}</h1>{body_html}"

    escaped_html = _escape_for_applescript(body_html)
    escaped_folder = _escape_for_applescript(folder)

    script = f"""
    tell application "Notes"
        try
            set targetFolder to first folder whose name is "{escaped_folder}"
        on error
            set targetFolder to make new folder with properties {{name:"{escaped_folder}"}}
        end try
        tell targetFolder
            make new note with properties {{body:"{escaped_html}"}}
        end tell
    end tell
    """
    result = _run_applescript(script)
    if result.returncode == 0:
        return {
            "status": "success",
            "message": f"Note '{title}' created in '{folder}'.",
        }
    else:
        return {
            "status": "error",
            "message": f"Failed to create note: {result.stderr.strip()}",
        }


def _edit_note(note_id: str, new_body: str) -> dict:
    """Replace the body of an existing note."""
    try:
        import mistune

        body_html = mistune.markdown(new_body)
    except ImportError:
        body_html = f"<p>{new_body}</p>"

    escaped_html = _escape_for_applescript(body_html)
    escaped_id = _escape_for_applescript(note_id)

    script = f"""
    tell application "Notes"
        set selectedNote to first note whose id is "{escaped_id}"
        set body of selectedNote to "{escaped_html}"
    end tell
    """
    result = _run_applescript(script)
    if result.returncode == 0:
        return {"status": "success", "message": "Note updated."}
    else:
        return {
            "status": "error",
            "message": f"Failed to update note: {result.stderr.strip()}",
        }


def _append_to_note(note_id: str, text_to_append: str) -> dict:
    """Append text to an existing note without replacing content."""
    # First get current body
    escaped_id = _escape_for_applescript(note_id)
    get_script = f"""
    tell application "Notes"
        set selectedNote to first note whose id is "{escaped_id}"
        return body of selectedNote
    end tell
    """
    result = _run_applescript(get_script)
    if result.returncode != 0:
        return {
            "status": "error",
            "message": f"Failed to read note: {result.stderr.strip()}",
        }

    current_html = result.stdout.strip()

    # Convert append text to HTML
    try:
        import mistune

        append_html = mistune.markdown(text_to_append)
    except ImportError:
        append_html = f"<p>{text_to_append}</p>"

    new_html = current_html + append_html
    escaped_new = _escape_for_applescript(new_html)

    set_script = f"""
    tell application "Notes"
        set selectedNote to first note whose id is "{escaped_id}"
        set body of selectedNote to "{escaped_new}"
    end tell
    """
    result = _run_applescript(set_script)
    if result.returncode == 0:
        return {"status": "success", "message": "Text appended to note."}
    else:
        return {
            "status": "error",
            "message": f"Failed to append: {result.stderr.strip()}",
        }


def _delete_note(note_id: str) -> dict:
    """Delete a note by ID."""
    escaped_id = _escape_for_applescript(note_id)
    script = f"""
    tell application "Notes"
        set theNote to first note whose id is "{escaped_id}"
        delete theNote
    end tell
    """
    result = _run_applescript(script)
    if result.returncode == 0:
        return {"status": "success", "message": "Note deleted."}
    else:
        return {
            "status": "error",
            "message": f"Failed to delete: {result.stderr.strip()}",
        }


def _move_note(note_id: str, target_folder: str) -> dict:
    """Move a note to a different folder (creates folder if needed)."""
    escaped_id = _escape_for_applescript(note_id)
    escaped_folder = _escape_for_applescript(target_folder)

    script = f"""
    tell application "Notes"
        set noteToMove to missing value
        set noteName to ""
        set noteBody to ""
        set accToUse to missing value
        repeat with acc in accounts
            repeat with f in folders of acc
                try
                    set n to first note of f whose id is "{escaped_id}"
                    set noteToMove to n
                    set noteName to name of n
                    set noteBody to body of n
                    set accToUse to acc
                    exit repeat
                end try
            end repeat
            if noteToMove is not missing value then exit repeat
        end repeat
        if noteToMove is not missing value then
            set destinationFolder to missing value
            try
                set destinationFolder to folder "{escaped_folder}" of accToUse
            on error
                set destinationFolder to make new folder with properties {{name:"{escaped_folder}"}} at accToUse
            end try
            make new note at destinationFolder with properties {{name:noteName, body:noteBody}}
            delete noteToMove
        end if
    end tell
    """
    result = _run_applescript(script)
    if result.returncode == 0:
        return {"status": "success", "message": f"Note moved to '{target_folder}'."}
    else:
        return {
            "status": "error",
            "message": f"Failed to move: {result.stderr.strip()}",
        }


def _list_folders() -> list[str]:
    """List all note folders."""
    script = """
    tell application "Notes"
        set output to ""
        repeat with f in every folder
            set fName to name of f
            set output to output & fName & linefeed
        end repeat
        return output
    end tell
    """
    result = _run_applescript(script)
    if result.returncode != 0:
        return []
    folders = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    return [f for f in folders if f not in _DELETED_FOLDERS]


def _search_notes(query: str) -> list[dict]:
    """Search notes by title or content (case-insensitive substring match)."""
    all_notes = _list_notes()
    query_lower = query.lower()
    results = []
    for note in all_notes:
        if query_lower in note["title"].lower():
            results.append(note)
            continue
        # Also search body content
        body = _get_note_body(note["id"], as_markdown=False)
        if query_lower in body.lower():
            results.append(note)
    return results


def _export_notes(output_dir: str = None, as_markdown: bool = True) -> dict:
    """Export all notes to files."""
    if not output_dir:
        output_dir = os.path.expanduser("~/Desktop/notes_export")
    os.makedirs(output_dir, exist_ok=True)

    notes = _list_notes()
    exported = 0

    for note in notes:
        body = _get_note_body(note["id"], as_markdown=as_markdown)
        # Sanitize filename
        safe_title = (
            note["title"].replace("/", "-").replace("\\", "-").replace(":", "-")
        )
        if len(safe_title) > 200:
            safe_title = safe_title[:200]
        ext = ".md" if as_markdown else ".html"
        filepath = os.path.join(output_dir, f"{safe_title}{ext}")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(body)
        exported += 1

    return {
        "status": "success",
        "message": f"Exported {exported} notes to {output_dir}",
        "path": output_dir,
        "count": exported,
    }


@tool
def apple_notes(
    action: str,
    title: str = None,
    body: str = None,
    folder: str = None,
    note_id: str = None,
    query: str = None,
    note_number: int = None,
    target_folder: str = None,
    output_dir: str = None,
    as_markdown: bool = True,
) -> Dict[str, Any]:
    """📝 Manage Apple Notes on macOS - create, read, edit, delete, search, move, and export notes.

    Requires macOS. Uses AppleScript for direct, non-interactive access to Apple Notes.

    Args:
        action: Action to perform:
            - "list": List all notes (optional: folder filter)
            - "view": View a note's content (requires note_id or note_number)
            - "create": Create a new note (requires title + body, optional folder)
            - "edit": Replace note body (requires note_id + body)
            - "append": Append text to a note (requires note_id + body)
            - "delete": Delete a note (requires note_id)
            - "move": Move note to folder (requires note_id + target_folder)
            - "search": Search notes (requires query)
            - "folders": List all folders
            - "export": Export all notes to files (optional output_dir)
        title: Note title (for create)
        body: Note body in markdown or plain text (for create/edit/append)
        folder: Folder name to filter or create in (default: "Notes")
        note_id: Apple Notes internal ID (from list/search results)
        query: Search query string (for search)
        note_number: Note number from list output (1-based, alternative to note_id)
        target_folder: Destination folder (for move, created if doesn't exist)
        output_dir: Export directory path (default: ~/Desktop/notes_export)
        as_markdown: Return/export as markdown (default True, else raw HTML)

    Returns:
        Dict with status and content

    Examples:
        # List all notes
        apple_notes(action="list")

        # List notes in a specific folder
        apple_notes(action="list", folder="Work")

        # View note #3 from the list
        apple_notes(action="view", note_number=3)

        # Create a note
        apple_notes(action="create", title="Meeting Notes", body="## Agenda\\n- Review Q1\\n- Plan Q2")

        # Create in specific folder
        apple_notes(action="create", title="TODO", body="- Buy milk", folder="Personal")

        # Search notes
        apple_notes(action="search", query="meeting")

        # Edit a note (replaces body)
        apple_notes(action="edit", note_id="x-coredata://...", body="Updated content")

        # Append to a note
        apple_notes(action="append", note_id="x-coredata://...", body="\\n## New section")

        # Move note to folder
        apple_notes(action="move", note_id="x-coredata://...", target_folder="Archive")

        # Delete a note
        apple_notes(action="delete", note_id="x-coredata://...")

        # List folders
        apple_notes(action="folders")

        # Export all notes as markdown
        apple_notes(action="export", output_dir="/tmp/my_notes")
    """
    # Platform check
    err = _check_macos()
    if err:
        return {"status": "error", "content": [{"text": err}]}

    try:
        if action == "list":
            notes = _list_notes(folder=folder)
            if not notes:
                msg = f"No notes found{f' in folder {folder!r}' if folder else ''}."
                return {"status": "success", "content": [{"text": msg}]}
            lines = [
                f"📝 **{len(notes)} notes**{f' in {folder!r}' if folder else ''}:\n"
            ]
            for i, n in enumerate(notes, 1):
                lines.append(f"  {i}. [{n['folder']}] {n['title']}")
                lines.append(f"     ID: `{n['id']}`")
            return {"status": "success", "content": [{"text": "\n".join(lines)}]}

        elif action == "view":
            # Resolve note_id from note_number if needed
            if note_number and not note_id:
                notes = _list_notes(folder=folder)
                if note_number < 1 or note_number > len(notes):
                    return {
                        "status": "error",
                        "content": [
                            {
                                "text": f"Note #{note_number} not found. Only {len(notes)} notes available."
                            }
                        ],
                    }
                note_id = notes[note_number - 1]["id"]
                view_title = notes[note_number - 1]["title"]
            elif not note_id:
                return {
                    "status": "error",
                    "content": [
                        {"text": "Provide note_id or note_number to view a note."}
                    ],
                }
            else:
                view_title = None

            content = _get_note_body(note_id, as_markdown=as_markdown)
            header = f"📝 **{view_title}**\n\n" if view_title else ""
            return {"status": "success", "content": [{"text": f"{header}{content}"}]}

        elif action == "create":
            if not title:
                return {
                    "status": "error",
                    "content": [{"text": "title is required for create."}],
                }
            if not body:
                return {
                    "status": "error",
                    "content": [{"text": "body is required for create."}],
                }
            result = _create_note(title, body, folder=folder or "Notes")
            return {
                "status": result["status"],
                "content": [{"text": result["message"]}],
            }

        elif action == "edit":
            if not note_id:
                if note_number:
                    notes = _list_notes(folder=folder)
                    if note_number < 1 or note_number > len(notes):
                        return {
                            "status": "error",
                            "content": [{"text": f"Note #{note_number} not found."}],
                        }
                    note_id = notes[note_number - 1]["id"]
                else:
                    return {
                        "status": "error",
                        "content": [
                            {"text": "note_id or note_number required for edit."}
                        ],
                    }
            if not body:
                return {
                    "status": "error",
                    "content": [{"text": "body is required for edit."}],
                }
            result = _edit_note(note_id, body)
            return {
                "status": result["status"],
                "content": [{"text": result["message"]}],
            }

        elif action == "append":
            if not note_id:
                if note_number:
                    notes = _list_notes(folder=folder)
                    if note_number < 1 or note_number > len(notes):
                        return {
                            "status": "error",
                            "content": [{"text": f"Note #{note_number} not found."}],
                        }
                    note_id = notes[note_number - 1]["id"]
                else:
                    return {
                        "status": "error",
                        "content": [
                            {"text": "note_id or note_number required for append."}
                        ],
                    }
            if not body:
                return {
                    "status": "error",
                    "content": [{"text": "body is required for append."}],
                }
            result = _append_to_note(note_id, body)
            return {
                "status": result["status"],
                "content": [{"text": result["message"]}],
            }

        elif action == "delete":
            if not note_id:
                if note_number:
                    notes = _list_notes(folder=folder)
                    if note_number < 1 or note_number > len(notes):
                        return {
                            "status": "error",
                            "content": [{"text": f"Note #{note_number} not found."}],
                        }
                    note_id = notes[note_number - 1]["id"]
                else:
                    return {
                        "status": "error",
                        "content": [
                            {"text": "note_id or note_number required for delete."}
                        ],
                    }
            result = _delete_note(note_id)
            return {
                "status": result["status"],
                "content": [{"text": result["message"]}],
            }

        elif action == "move":
            if not note_id:
                if note_number:
                    notes = _list_notes(folder=folder)
                    if note_number < 1 or note_number > len(notes):
                        return {
                            "status": "error",
                            "content": [{"text": f"Note #{note_number} not found."}],
                        }
                    note_id = notes[note_number - 1]["id"]
                else:
                    return {
                        "status": "error",
                        "content": [
                            {"text": "note_id or note_number required for move."}
                        ],
                    }
            if not target_folder:
                return {
                    "status": "error",
                    "content": [{"text": "target_folder required for move."}],
                }
            result = _move_note(note_id, target_folder)
            return {
                "status": result["status"],
                "content": [{"text": result["message"]}],
            }

        elif action == "search":
            if not query:
                return {
                    "status": "error",
                    "content": [{"text": "query is required for search."}],
                }
            results = _search_notes(query)
            if not results:
                return {
                    "status": "success",
                    "content": [{"text": f"No notes matching '{query}'."}],
                }
            lines = [f"🔍 **{len(results)} notes** matching '{query}':\n"]
            for i, n in enumerate(results, 1):
                lines.append(f"  {i}. [{n['folder']}] {n['title']}")
                lines.append(f"     ID: `{n['id']}`")
            return {"status": "success", "content": [{"text": "\n".join(lines)}]}

        elif action == "folders":
            folders = _list_folders()
            if not folders:
                return {"status": "success", "content": [{"text": "No folders found."}]}
            lines = [f"📁 **{len(folders)} folders**:\n"]
            for f in folders:
                lines.append(f"  • {f}")
            return {"status": "success", "content": [{"text": "\n".join(lines)}]}

        elif action == "export":
            result = _export_notes(output_dir=output_dir, as_markdown=as_markdown)
            return {
                "status": result["status"],
                "content": [{"text": result["message"]}],
            }

        else:
            return {
                "status": "error",
                "content": [
                    {
                        "text": f"Unknown action: {action}. Valid: list, view, create, edit, append, delete, move, search, folders, export"
                    }
                ],
            }

    except Exception as e:
        logger.error(f"apple_notes error: {e}")
        return {"status": "error", "content": [{"text": f"Error: {str(e)}"}]}
