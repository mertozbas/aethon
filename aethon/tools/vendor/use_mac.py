"""🍎 use_mac - Unified macOS system control via AppleScript & system APIs.

Like use_aws wraps the AWS CLI, this wraps the entire macOS ecosystem:
Calendar, Reminders, Mail, Contacts, Safari, Finder, System Events,
Shortcuts, Messages, Keychain, Music, and raw AppleScript execution.

One tool to control the whole Mac.
"""

import json
import logging
import os
import platform
import re
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

from strands import tool

logger = logging.getLogger(__name__)


# =============================================================================
# Core helpers
# =============================================================================


def _check_macos() -> Optional[str]:
    if platform.system() != "Darwin":
        return "use_mac is only available on macOS."
    return None


def _run_applescript(script: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _run_js(script: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run JavaScript for Automation (JXA) — more powerful for some APIs."""
    return subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _esc(text: str) -> str:
    """Escape for AppleScript double-quoted strings."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _ok(text: str) -> Dict[str, Any]:
    return {"status": "success", "content": [{"text": text}]}


def _err(text: str) -> Dict[str, Any]:
    return {"status": "error", "content": [{"text": text}]}


def _run_and_return(script: str, timeout: int = 30) -> Dict[str, Any]:
    """Run AppleScript and return result or error."""
    r = _run_applescript(script, timeout)
    if r.returncode == 0:
        return _ok(r.stdout.strip() if r.stdout.strip() else "Done.")
    return _err(f"AppleScript error: {r.stderr.strip()}")


# =============================================================================
# Calendar
# =============================================================================


def _calendar_list_events(calendar: str = None, days: int = 7) -> Dict:
    """List upcoming calendar events."""
    cal_filter = f'whose name is "{_esc(calendar)}"' if calendar else ""
    script = f"""
    set now to current date
    set endDate to now + ({days} * days)
    set output to ""
    tell application "Calendar"
        repeat with cal in (calendars {cal_filter})
            set calName to name of cal
            set evts to (every event of cal whose start date ≥ now and start date ≤ endDate)
            repeat with e in evts
                set eName to summary of e
                set eStart to start date of e
                set eEnd to end date of e
                set eLoc to location of e
                if eLoc is missing value then set eLoc to ""
                set output to output & calName & "|||" & eName & "|||" & (eStart as string) & "|||" & (eEnd as string) & "|||" & eLoc & linefeed
            end repeat
        end repeat
    end tell
    return output
    """
    r = _run_applescript(script, timeout=30)
    if r.returncode != 0:
        return _err(f"Calendar error: {r.stderr.strip()}")

    events = []
    for line in r.stdout.strip().split("\n"):
        if not line or "|||" not in line:
            continue
        parts = line.split("|||")
        if len(parts) >= 4:
            events.append(
                {
                    "calendar": parts[0].strip(),
                    "title": parts[1].strip(),
                    "start": parts[2].strip(),
                    "end": parts[3].strip(),
                    "location": parts[4].strip() if len(parts) > 4 else "",
                }
            )

    if not events:
        return _ok(f"No events in the next {days} days.")

    lines = [f"📅 **{len(events)} events** (next {days} days):\n"]
    for e in events:
        loc = f" 📍 {e['location']}" if e["location"] else ""
        lines.append(f"  • [{e['calendar']}] **{e['title']}**")
        lines.append(f"    {e['start']} → {e['end']}{loc}")
    return _ok("\n".join(lines))


def _calendar_create_event(
    title: str,
    start: str,
    end: str = None,
    calendar: str = None,
    location: str = None,
    notes: str = None,
    all_day: bool = False,
) -> Dict:
    """Create a calendar event."""
    cal_target = f'calendar "{_esc(calendar)}"' if calendar else "first calendar"
    props = [f'summary:"{_esc(title)}"']
    props.append(f'start date:date "{_esc(start)}"')
    if end:
        props.append(f'end date:date "{_esc(end)}"')
    if location:
        props.append(f'location:"{_esc(location)}"')
    if notes:
        props.append(f'description:"{_esc(notes)}"')
    if all_day:
        props.append("allday event:true")

    script = f"""
    tell application "Calendar"
        tell {cal_target}
            make new event with properties {{{", ".join(props)}}}
        end tell
    end tell
    """
    return _run_and_return(script)


def _calendar_list_calendars() -> Dict:
    script = """
    tell application "Calendar"
        set output to ""
        repeat with c in calendars
            set output to output & name of c & linefeed
        end repeat
        return output
    end tell
    """
    r = _run_applescript(script)
    if r.returncode != 0:
        return _err(f"Error: {r.stderr.strip()}")
    cals = [c.strip() for c in r.stdout.strip().split("\n") if c.strip()]
    return _ok("📅 Calendars:\n" + "\n".join(f"  • {c}" for c in cals))


# =============================================================================
# Reminders
# =============================================================================


def _reminders_list(list_name: str = None, show_completed: bool = False) -> Dict:
    completed_filter = "" if show_completed else "whose completed is false"
    if list_name:
        script = f"""
        tell application "Reminders"
            set output to ""
            set rl to list "{_esc(list_name)}"
            repeat with r in (reminders of rl {completed_filter})
                set rName to name of r
                set rDue to ""
                try
                    set rDue to due date of r as string
                end try
                set rPri to priority of r as string
                set output to output & rName & "|||" & rDue & "|||" & rPri & linefeed
            end repeat
            return output
        end tell
        """
    else:
        script = f"""
        tell application "Reminders"
            set output to ""
            repeat with rl in lists
                set listName to name of rl
                repeat with r in (reminders of rl {completed_filter})
                    set rName to name of r
                    set rDue to ""
                    try
                        set rDue to due date of r as string
                    end try
                    set output to output & listName & "|||" & rName & "|||" & rDue & linefeed
                end repeat
            end repeat
            return output
        end tell
        """
    r = _run_applescript(script, timeout=30)
    if r.returncode != 0:
        return _err(f"Reminders error: {r.stderr.strip()}")

    items = []
    for line in r.stdout.strip().split("\n"):
        if not line or "|||" not in line:
            continue
        parts = line.split("|||")
        items.append(parts)

    if not items:
        return _ok("No reminders found.")

    lines = [f"✅ **{len(items)} reminders**:\n"]
    for parts in items:
        due = (
            f" (due: {parts[-1].strip()})"
            if len(parts) > 2 and parts[-1].strip()
            else ""
        )
        name = parts[1].strip() if len(parts) > 2 else parts[0].strip()
        list_label = f"[{parts[0].strip()}] " if len(parts) > 2 else ""
        lines.append(f"  • {list_label}{name}{due}")
    return _ok("\n".join(lines))


def _reminders_create(
    title: str,
    list_name: str = None,
    due_date: str = None,
    notes: str = None,
    priority: int = 0,
) -> Dict:
    target = f'list "{_esc(list_name)}"' if list_name else "default list"
    props = [f'name:"{_esc(title)}"']
    if due_date:
        props.append(f'due date:date "{_esc(due_date)}"')
    if notes:
        props.append(f'body:"{_esc(notes)}"')
    if priority:
        props.append(f"priority:{priority}")

    script = f"""
    tell application "Reminders"
        tell {target}
            make new reminder with properties {{{", ".join(props)}}}
        end tell
    end tell
    """
    return _run_and_return(script)


def _reminders_lists() -> Dict:
    script = """
    tell application "Reminders"
        set output to ""
        repeat with rl in lists
            set output to output & name of rl & linefeed
        end repeat
        return output
    end tell
    """
    r = _run_applescript(script)
    if r.returncode != 0:
        return _err(f"Error: {r.stderr.strip()}")
    lists = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]
    return _ok("✅ Reminder Lists:\n" + "\n".join(f"  • {l}" for l in lists))


# =============================================================================
# Contacts
# =============================================================================


def _contacts_search(query: str) -> Dict:
    script = f"""
    tell application "Contacts"
        set output to ""
        set matches to (every person whose name contains "{_esc(query)}")
        repeat with p in matches
            set pName to name of p
            set pEmail to ""
            try
                set pEmail to value of first email of p
            end try
            set pPhone to ""
            try
                set pPhone to value of first phone of p
            end try
            set output to output & pName & "|||" & pEmail & "|||" & pPhone & linefeed
        end repeat
        return output
    end tell
    """
    r = _run_applescript(script, timeout=15)
    if r.returncode != 0:
        return _err(f"Contacts error: {r.stderr.strip()}")

    contacts = []
    for line in r.stdout.strip().split("\n"):
        if not line or "|||" not in line:
            continue
        parts = line.split("|||")
        contacts.append(
            {
                "name": parts[0].strip(),
                "email": parts[1].strip() if len(parts) > 1 else "",
                "phone": parts[2].strip() if len(parts) > 2 else "",
            }
        )

    if not contacts:
        return _ok(f"No contacts matching '{query}'.")

    lines = [f"👤 **{len(contacts)} contacts** matching '{query}':\n"]
    for c in contacts:
        details = []
        if c["email"]:
            details.append(f"📧 {c['email']}")
        if c["phone"]:
            details.append(f"📱 {c['phone']}")
        lines.append(f"  • **{c['name']}** {' | '.join(details)}")
    return _ok("\n".join(lines))


def _contacts_create(
    name: str, email: str = None, phone: str = None, company: str = None
) -> Dict:
    """Create a new contact."""
    # Split name into first/last
    name_parts = name.strip().split(" ", 1)
    first = name_parts[0]
    last = name_parts[1] if len(name_parts) > 1 else ""

    props = [f'first name:"{_esc(first)}"']
    if last:
        props.append(f'last name:"{_esc(last)}"')
    if company:
        props.append(f'organization:"{_esc(company)}"')

    email_line = ""
    if email:
        email_line = f'\n        make new email at end of emails of newPerson with properties {{label:"work", value:"{_esc(email)}"}}'

    phone_line = ""
    if phone:
        phone_line = f'\n        make new phone at end of phones of newPerson with properties {{label:"mobile", value:"{_esc(phone)}"}}'

    script = f"""
    tell application "Contacts"
        set newPerson to make new person with properties {{{", ".join(props)}}}{email_line}{phone_line}
        save
    end tell
    """
    return _run_and_return(script)


# =============================================================================
# Mail
# =============================================================================


def _mail_send(
    to: str, subject: str, body: str, cc: str = None, attachment: str = None
) -> Dict:
    cc_line = ""
    if cc:
        cc_recipients = [c.strip() for c in cc.split(",")]
        cc_lines = "\n".join(
            f'make new cc recipient at end of cc recipients with properties {{address:"{_esc(c)}"}}'
            for c in cc_recipients
        )
        cc_line = cc_lines

    attachment_line = ""
    if attachment:
        attachment_line = f'\n        make new attachment with properties {{file name:POSIX file "{_esc(attachment)}"}}'

    to_recipients = [t.strip() for t in to.split(",")]
    to_lines = "\n".join(
        f'make new to recipient at end of to recipients with properties {{address:"{_esc(t)}"}}'
        for t in to_recipients
    )

    script = f"""
    tell application "Mail"
        set newMessage to make new outgoing message with properties {{subject:"{_esc(subject)}", content:"{_esc(body)}", visible:true}}
        tell newMessage
            {to_lines}
            {cc_line}
            {attachment_line}
        end tell
        send newMessage
    end tell
    """
    return _run_and_return(script, timeout=30)


def _mail_check() -> Dict:
    script = """
    tell application "Mail"
        check for new mail
        set output to ""
        set inboxMsgs to messages of inbox
        set msgCount to count of inboxMsgs
        if msgCount > 10 then set msgCount to 10
        repeat with i from 1 to msgCount
            set m to item i of inboxMsgs
            set mSubject to subject of m
            set mSender to sender of m
            set mDate to date received of m as string
            set mRead to read status of m
            set readMark to "📩"
            if mRead then set readMark to "📧"
            set output to output & readMark & "|||" & mSender & "|||" & mSubject & "|||" & mDate & linefeed
        end repeat
        return output
    end tell
    """
    r = _run_applescript(script, timeout=30)
    if r.returncode != 0:
        return _err(f"Mail error: {r.stderr.strip()}")

    lines = ["📬 **Recent Inbox** (latest 10):\n"]
    for line in r.stdout.strip().split("\n"):
        if not line or "|||" not in line:
            continue
        parts = line.split("|||")
        if len(parts) >= 3:
            lines.append(f"  {parts[0].strip()} **{parts[2].strip()}**")
            lines.append(
                f"    From: {parts[1].strip()} | {parts[3].strip() if len(parts) > 3 else ''}"
            )
    return _ok("\n".join(lines))


def _mail_unread_count() -> Dict:
    script = """
    tell application "Mail"
        return unread count of inbox
    end tell
    """
    r = _run_applescript(script)
    if r.returncode == 0:
        return _ok(f"📬 Unread emails: **{r.stdout.strip()}**")
    return _err(f"Mail error: {r.stderr.strip()}")


# =============================================================================
# Safari / Browser
# =============================================================================


def _safari_tabs() -> Dict:
    script = """
    tell application "Safari"
        set output to ""
        repeat with w in windows
            set winIdx to index of w
            repeat with t in tabs of w
                set tName to name of t
                set tURL to URL of t
                set output to output & winIdx & "|||" & tName & "|||" & tURL & linefeed
            end repeat
        end repeat
        return output
    end tell
    """
    r = _run_applescript(script)
    if r.returncode != 0:
        return _err(f"Safari error: {r.stderr.strip()}")

    lines = ["🌐 **Safari Tabs**:\n"]
    for line in r.stdout.strip().split("\n"):
        if not line or "|||" not in line:
            continue
        parts = line.split("|||")
        if len(parts) >= 3:
            lines.append(f"  • [Win {parts[0].strip()}] {parts[1].strip()}")
            lines.append(f"    {parts[2].strip()}")
    return _ok("\n".join(lines))


def _safari_open(url: str) -> Dict:
    script = f"""
    tell application "Safari"
        activate
        open location "{_esc(url)}"
    end tell
    """
    return _run_and_return(script)


def _safari_read_page() -> Dict:
    """Read the text content of the current Safari page."""
    script = """
    tell application "Safari"
        set pageText to do JavaScript "document.body.innerText" in current tab of front window
        return pageText
    end tell
    """
    r = _run_applescript(script, timeout=15)
    if r.returncode != 0:
        return _err(f"Safari error: {r.stderr.strip()}")
    text = r.stdout.strip()
    # Truncate very long pages
    if len(text) > 10000:
        text = text[:10000] + "\n\n... [truncated, page too long]"
    return _ok(text)


def _safari_url() -> Dict:
    """Get the URL of the current Safari tab."""
    script = """
    tell application "Safari"
        return URL of current tab of front window
    end tell
    """
    r = _run_applescript(script)
    if r.returncode == 0:
        return _ok(r.stdout.strip())
    return _err(f"Safari error: {r.stderr.strip()}")


# =============================================================================
# Finder
# =============================================================================


def _finder_selection() -> Dict:
    """Get currently selected files in Finder."""
    script = """
    tell application "Finder"
        set sel to selection
        set output to ""
        repeat with f in sel
            set output to output & (POSIX path of (f as alias)) & linefeed
        end repeat
        return output
    end tell
    """
    r = _run_applescript(script)
    if r.returncode != 0:
        return _err(f"Finder error: {r.stderr.strip()}")
    files = [f.strip() for f in r.stdout.strip().split("\n") if f.strip()]
    if not files:
        return _ok("No files selected in Finder.")
    return _ok("📁 Selected files:\n" + "\n".join(f"  • {f}" for f in files))


def _finder_tag(path: str, tags: str) -> Dict:
    """Add Finder tags to a file."""
    tag_list = [t.strip() for t in tags.split(",")]
    tag_str = ", ".join(f'"{_esc(t)}"' for t in tag_list)
    # Use xattr for tagging (more reliable)
    import plistlib

    tag_data = plistlib.dumps(tag_list, fmt=plistlib.FMT_BINARY)
    hex_data = tag_data.hex()
    # Use shell xattr command
    r = subprocess.run(
        [
            "xattr",
            "-wx",
            "com.apple.metadata:_kMDItemUserTags",
            hex_data,
            os.path.expanduser(path),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if r.returncode == 0:
        return _ok(f"Tagged '{path}' with: {', '.join(tag_list)}")
    return _err(f"Tagging error: {r.stderr.strip()}")


def _finder_reveal(path: str) -> Dict:
    """Reveal a file in Finder."""
    script = f"""
    tell application "Finder"
        reveal POSIX file "{_esc(os.path.expanduser(path))}"
        activate
    end tell
    """
    return _run_and_return(script)


def _finder_get_tags(path: str) -> Dict:
    """Get Finder tags of a file."""
    r = subprocess.run(
        ["mdls", "-name", "kMDItemUserTags", os.path.expanduser(path)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if r.returncode == 0:
        return _ok(f"Tags for '{path}':\n{r.stdout.strip()}")
    return _err(f"Error: {r.stderr.strip()}")


# =============================================================================
# System Events (notifications, clipboard, apps, volume, dark mode, etc.)
# =============================================================================


def _system_notification(
    message: str, title: str = "AETHON", subtitle: str = None, sound: str = None
) -> Dict:
    subtitle_part = f' subtitle "{_esc(subtitle)}"' if subtitle else ""
    sound_part = f' sound name "{_esc(sound)}"' if sound else ""
    script = f'display notification "{_esc(message)}" with title "{_esc(title)}"{subtitle_part}{sound_part}'
    return _run_and_return(script)


def _system_clipboard_get() -> Dict:
    script = "return the clipboard"
    r = _run_applescript(script)
    if r.returncode == 0:
        return _ok(f"📋 Clipboard:\n{r.stdout.strip()}")
    return _err(f"Clipboard error: {r.stderr.strip()}")


def _system_clipboard_set(text: str) -> Dict:
    script = f'set the clipboard to "{_esc(text)}"'
    return _run_and_return(script)


def _system_volume(level: int = None) -> Dict:
    if level is not None:
        script = f"set volume output volume {level}"
        return _run_and_return(script)
    else:
        script = "return output volume of (get volume settings)"
        r = _run_applescript(script)
        if r.returncode == 0:
            return _ok(f"🔊 Volume: {r.stdout.strip()}%")
        return _err(f"Volume error: {r.stderr.strip()}")


def _system_dark_mode(enable: bool = None) -> Dict:
    if enable is not None:
        val = "true" if enable else "false"
        script = f"""
        tell application "System Events"
            tell appearance preferences
                set dark mode to {val}
            end tell
        end tell
        """
        return _run_and_return(script)
    else:
        script = """
        tell application "System Events"
            tell appearance preferences
                return dark mode
            end tell
        end tell
        """
        r = _run_applescript(script)
        if r.returncode == 0:
            mode = "Dark" if "true" in r.stdout.lower() else "Light"
            return _ok(f"🌗 Appearance: {mode} mode")
        return _err(f"Error: {r.stderr.strip()}")


def _system_frontmost_app() -> Dict:
    script = """
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
        return frontApp
    end tell
    """
    r = _run_applescript(script)
    if r.returncode == 0:
        return _ok(f"🖥️ Frontmost app: {r.stdout.strip()}")
    return _err(f"Error: {r.stderr.strip()}")


def _system_running_apps() -> Dict:
    script = """
    tell application "System Events"
        set appNames to name of every process whose background only is false
        set output to ""
        repeat with n in appNames
            set output to output & n & linefeed
        end repeat
        return output
    end tell
    """
    r = _run_applescript(script)
    if r.returncode != 0:
        return _err(f"Error: {r.stderr.strip()}")
    apps = [a.strip() for a in r.stdout.strip().split("\n") if a.strip()]
    return _ok(
        f"🖥️ **{len(apps)} running apps**:\n" + "\n".join(f"  • {a}" for a in apps)
    )


def _system_launch_app(app_name: str) -> Dict:
    script = f"""
    tell application "{_esc(app_name)}"
        activate
    end tell
    """
    return _run_and_return(script)


def _system_quit_app(app_name: str) -> Dict:
    script = f"""
    tell application "{_esc(app_name)}"
        quit
    end tell
    """
    return _run_and_return(script)


def _system_screen_brightness(level: float = None) -> Dict:
    """Get or set screen brightness (0.0 - 1.0)."""
    if level is not None:
        r = subprocess.run(
            ["brightness", str(level)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            return _ok(f"🔅 Brightness set to {level}")
        # Fallback: try with osascript
        return _err("brightness CLI not found. Install: brew install brightness")
    else:
        r = subprocess.run(
            ["brightness", "-l"], capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            return _ok(f"🔅 Brightness:\n{r.stdout.strip()}")
        return _err("brightness CLI not found.")


def _system_screenshot(path: str = None, area: bool = False) -> Dict:
    """Take a screenshot."""
    if not path:
        path = os.path.expanduser(
            f"~/Desktop/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
    cmd = ["screencapture"]
    if area:
        cmd.append("-i")  # interactive selection
    cmd.append(path)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        return _ok(f"📸 Screenshot saved: {path}")
    return _err(f"Screenshot error: {r.stderr.strip()}")


def _system_say(text: str, voice: str = None, rate: int = None) -> Dict:
    """Text-to-speech using macOS say command."""
    cmd = ["say"]
    if voice:
        cmd.extend(["-v", voice])
    if rate:
        cmd.extend(["-r", str(rate)])
    cmd.append(text)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        return _ok(f'🔊 Spoke: "{text[:50]}..."')
    return _err(f"Say error: {r.stderr.strip()}")


def _system_wifi() -> Dict:
    """Get current WiFi info."""
    r = subprocess.run(
        [
            "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport",
            "-I",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if r.returncode == 0:
        return _ok(f"📶 WiFi Info:\n{r.stdout.strip()}")
    # Fallback
    r2 = subprocess.run(
        ["networksetup", "-getairportnetwork", "en0"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if r2.returncode == 0:
        return _ok(f"📶 {r2.stdout.strip()}")
    return _err("Could not get WiFi info.")


def _system_battery() -> Dict:
    """Get battery status."""
    r = subprocess.run(
        ["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5
    )
    if r.returncode == 0:
        return _ok(f"🔋 Battery:\n{r.stdout.strip()}")
    return _err("Could not get battery info.")


def _system_do_not_disturb(enable: bool = None) -> Dict:
    """Toggle Focus/Do Not Disturb mode."""
    if enable is not None:
        # Use shortcuts to toggle DND
        action = "turn on" if enable else "turn off"
        script = f"""
        tell application "System Events"
            -- Toggle via Control Center
            tell application process "ControlCenter"
                -- Click Focus in menu bar
            end tell
        end tell
        """
        # More reliable: use shortcuts
        r = subprocess.run(
            (
                ["shortcuts", "run", "Toggle Focus"]
                if enable
                else ["shortcuts", "run", "Toggle Focus"]
            ),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return _ok(f"🔕 Do Not Disturb: {'ON' if enable else 'OFF'} (attempted)")
    return _ok("Use enable=true/false to toggle DND.")


# =============================================================================
# Shortcuts (Siri Shortcuts)
# =============================================================================


def _shortcuts_list() -> Dict:
    r = subprocess.run(
        ["shortcuts", "list"], capture_output=True, text=True, timeout=15
    )
    if r.returncode != 0:
        return _err(f"Shortcuts error: {r.stderr.strip()}")
    shortcuts = [s.strip() for s in r.stdout.strip().split("\n") if s.strip()]
    return _ok(
        f"⚡ **{len(shortcuts)} shortcuts**:\n"
        + "\n".join(f"  • {s}" for s in shortcuts[:50])
    )


def _shortcuts_run(name: str, input_text: str = None) -> Dict:
    cmd = ["shortcuts", "run", name]
    stdin_data = input_text if input_text else None
    r = subprocess.run(
        cmd, capture_output=True, text=True, timeout=60, input=stdin_data
    )
    if r.returncode == 0:
        output = r.stdout.strip() if r.stdout.strip() else "Shortcut completed."
        return _ok(f"⚡ '{name}' result:\n{output}")
    return _err(f"Shortcut error: {r.stderr.strip()}")


# =============================================================================
# Messages (iMessage)
# =============================================================================


def _messages_send(to: str, text: str) -> Dict:
    """Send an iMessage."""
    script = f"""
    tell application "Messages"
        set targetBuddy to buddy "{_esc(to)}" of (first account whose service type is iMessage)
        send "{_esc(text)}" to targetBuddy
    end tell
    """
    return _run_and_return(script)


def _messages_recent() -> Dict:
    """Get recent iMessage chats."""
    script = """
    tell application "Messages"
        set output to ""
        set chatList to chats
        set chatCount to count of chatList
        if chatCount > 15 then set chatCount to 15
        repeat with i from 1 to chatCount
            set c to item i of chatList
            set cName to name of c
            if cName is missing value then set cName to id of c
            set output to output & cName & linefeed
        end repeat
        return output
    end tell
    """
    r = _run_applescript(script)
    if r.returncode != 0:
        return _err(f"Messages error: {r.stderr.strip()}")
    chats = [c.strip() for c in r.stdout.strip().split("\n") if c.strip()]
    return _ok("💬 Recent chats:\n" + "\n".join(f"  • {c}" for c in chats))


# =============================================================================
# Music
# =============================================================================


def _music_now_playing() -> Dict:
    script = """
    tell application "Music"
        if player state is playing then
            set trackName to name of current track
            set artistName to artist of current track
            set albumName to album of current track
            return "🎵 " & trackName & " by " & artistName & " (" & albumName & ")"
        else
            return "⏸ Music is not playing."
        end if
    end tell
    """
    return _run_and_return(script)


def _music_control(action: str) -> Dict:
    action_map = {
        "play": "play",
        "pause": "pause",
        "next": "next track",
        "previous": "previous track",
        "stop": "stop",
    }
    cmd = action_map.get(action, action)
    script = f"""
    tell application "Music"
        {cmd}
    end tell
    """
    return _run_and_return(script)


# =============================================================================
# Keychain (secure credential storage)
# =============================================================================


def _keychain_get(service: str, account: str = None) -> Dict:
    """Get a password from Keychain."""
    cmd = ["security", "find-generic-password", "-s", service, "-w"]
    if account:
        cmd.extend(["-a", account])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if r.returncode == 0:
        return _ok(f"🔑 Password for '{service}': {r.stdout.strip()}")
    return _err(f"Keychain error: {r.stderr.strip()}")


def _keychain_set(service: str, account: str, password: str) -> Dict:
    """Store a password in Keychain."""
    cmd = [
        "security",
        "add-generic-password",
        "-s",
        service,
        "-a",
        account,
        "-w",
        password,
        "-U",
    ]  # -U = update if exists
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if r.returncode == 0:
        return _ok(f"🔑 Password stored for '{service}' ({account}).")
    return _err(f"Keychain error: {r.stderr.strip()}")


def _keychain_delete(service: str, account: str = None) -> Dict:
    """Delete a password from Keychain."""
    cmd = ["security", "delete-generic-password", "-s", service]
    if account:
        cmd.extend(["-a", account])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if r.returncode == 0:
        return _ok(f"🔑 Password deleted for '{service}'.")
    return _err(f"Keychain error: {r.stderr.strip()}")


# =============================================================================
# Raw AppleScript execution
# =============================================================================


def _run_raw_applescript(script: str, timeout: int = 30) -> Dict:
    """Execute arbitrary AppleScript."""
    return _run_and_return(script, timeout)


def _run_raw_jxa(script: str, timeout: int = 30) -> Dict:
    """Execute arbitrary JavaScript for Automation."""
    r = _run_js(script, timeout)
    if r.returncode == 0:
        return _ok(r.stdout.strip() if r.stdout.strip() else "Done.")
    return _err(f"JXA error: {r.stderr.strip()}")


# =============================================================================
# The unified tool
# =============================================================================


@tool
def use_mac(
    action: str,
    # Common params
    query: str = None,
    text: str = None,
    title: str = None,
    name: str = None,
    path: str = None,
    # Calendar
    calendar: str = None,
    start: str = None,
    end: str = None,
    days: int = 7,
    location: str = None,
    all_day: bool = False,
    # Reminders
    list_name: str = None,
    due_date: str = None,
    priority: int = 0,
    show_completed: bool = False,
    # Contacts
    email: str = None,
    phone: str = None,
    company: str = None,
    # Mail
    to: str = None,
    subject: str = None,
    body: str = None,
    cc: str = None,
    attachment: str = None,
    # Safari
    url: str = None,
    # System
    level: float = None,
    enable: bool = None,
    voice: str = None,
    rate: int = None,
    area: bool = False,
    sound: str = None,
    subtitle: str = None,
    tags: str = None,
    # Shortcuts
    input_text: str = None,
    # Keychain
    service: str = None,
    account: str = None,
    password: str = None,
    # Music
    music_action: str = None,
    # Raw
    script: str = None,
    timeout: int = 30,
    notes: str = None,
    app_name: str = None,
) -> Dict[str, Any]:
    """🍎 Unified macOS system control — Calendar, Reminders, Mail, Contacts, Safari,
    Finder, System Events, Shortcuts, Messages, Music, Keychain, and raw AppleScript.

    One tool to control the entire Mac. Like use_aws for AWS, but for macOS.

    Args:
        action: The action to perform. Format: "category.operation"

            **Calendar:**
            - "calendar.events" — List upcoming events (days=7, calendar=optional)
            - "calendar.create" — Create event (title, start, end, calendar, location, notes, all_day)
            - "calendar.list" — List all calendars

            **Reminders:**
            - "reminders.list" — List reminders (list_name=optional, show_completed=False)
            - "reminders.create" — Create reminder (title, list_name, due_date, notes, priority)
            - "reminders.lists" — List all reminder lists

            **Contacts:**
            - "contacts.search" — Search contacts (query)
            - "contacts.create" — Create contact (name, email, phone, company)

            **Mail:**
            - "mail.send" — Send email (to, subject, body, cc, attachment)
            - "mail.inbox" — Check recent inbox
            - "mail.unread" — Get unread count

            **Safari:**
            - "safari.tabs" — List open tabs
            - "safari.open" — Open URL (url)
            - "safari.read" — Read current page text
            - "safari.url" — Get current tab URL

            **Finder:**
            - "finder.selection" — Get selected files
            - "finder.tag" — Tag a file (path, tags="tag1,tag2")
            - "finder.tags" — Get tags of a file (path)
            - "finder.reveal" — Reveal file in Finder (path)

            **System:**
            - "system.notify" — Send notification (text, title, subtitle, sound)
            - "system.clipboard.get" — Get clipboard content
            - "system.clipboard.set" — Set clipboard (text)
            - "system.volume" — Get/set volume (level=0-100)
            - "system.dark_mode" — Get/toggle dark mode (enable=bool)
            - "system.frontmost" — Get frontmost app
            - "system.apps" — List running apps
            - "system.launch" — Launch app (app_name)
            - "system.quit" — Quit app (app_name)
            - "system.brightness" — Get/set brightness (level=0.0-1.0)
            - "system.screenshot" — Take screenshot (path, area=bool)
            - "system.say" — Text-to-speech (text, voice, rate)
            - "system.wifi" — Get WiFi info
            - "system.battery" — Get battery status
            - "system.dnd" — Toggle Do Not Disturb (enable=bool)

            **Shortcuts:**
            - "shortcuts.list" — List Siri Shortcuts
            - "shortcuts.run" — Run a shortcut (name, input_text)

            **Messages:**
            - "messages.send" — Send iMessage (to, text)
            - "messages.recent" — List recent chats

            **Music:**
            - "music.now_playing" — Current track info
            - "music.play" — Play
            - "music.pause" — Pause
            - "music.next" — Next track
            - "music.previous" — Previous track

            **Keychain:**
            - "keychain.get" — Get password (service, account)
            - "keychain.set" — Store password (service, account, password)
            - "keychain.delete" — Delete password (service, account)

            **Raw:**
            - "applescript" — Run raw AppleScript (script, timeout)
            - "jxa" — Run raw JXA (script, timeout)

    Returns:
        Dict with status and content
    """
    err = _check_macos()
    if err:
        return _err(err)

    try:
        # --- Calendar ---
        if action == "calendar.events":
            return _calendar_list_events(calendar=calendar, days=days)
        elif action == "calendar.create":
            if not title or not start:
                return _err("title and start required for calendar.create")
            return _calendar_create_event(
                title=title,
                start=start,
                end=end,
                calendar=calendar,
                location=location,
                notes=notes,
                all_day=all_day,
            )
        elif action == "calendar.list":
            return _calendar_list_calendars()

        # --- Reminders ---
        elif action == "reminders.list":
            return _reminders_list(list_name=list_name, show_completed=show_completed)
        elif action == "reminders.create":
            if not title:
                return _err("title required for reminders.create")
            return _reminders_create(
                title=title,
                list_name=list_name,
                due_date=due_date,
                notes=notes,
                priority=priority,
            )
        elif action == "reminders.lists":
            return _reminders_lists()

        # --- Contacts ---
        elif action == "contacts.search":
            if not query:
                return _err("query required for contacts.search")
            return _contacts_search(query)
        elif action == "contacts.create":
            if not name:
                return _err("name required for contacts.create")
            return _contacts_create(
                name=name, email=email, phone=phone, company=company
            )

        # --- Mail ---
        elif action == "mail.send":
            if not to or not subject or not body:
                return _err("to, subject, body required for mail.send")
            return _mail_send(
                to=to, subject=subject, body=body, cc=cc, attachment=attachment
            )
        elif action == "mail.inbox":
            return _mail_check()
        elif action == "mail.unread":
            return _mail_unread_count()

        # --- Safari ---
        elif action == "safari.tabs":
            return _safari_tabs()
        elif action == "safari.open":
            if not url:
                return _err("url required for safari.open")
            return _safari_open(url)
        elif action == "safari.read":
            return _safari_read_page()
        elif action == "safari.url":
            return _safari_url()

        # --- Finder ---
        elif action == "finder.selection":
            return _finder_selection()
        elif action == "finder.tag":
            if not path or not tags:
                return _err("path and tags required for finder.tag")
            return _finder_tag(path=path, tags=tags)
        elif action == "finder.tags":
            if not path:
                return _err("path required for finder.tags")
            return _finder_get_tags(path)
        elif action == "finder.reveal":
            if not path:
                return _err("path required for finder.reveal")
            return _finder_reveal(path)

        # --- System ---
        elif action == "system.notify":
            if not text:
                return _err("text required for system.notify")
            return _system_notification(
                message=text, title=title or "AETHON", subtitle=subtitle, sound=sound
            )
        elif action == "system.clipboard.get":
            return _system_clipboard_get()
        elif action == "system.clipboard.set":
            if not text:
                return _err("text required for system.clipboard.set")
            return _system_clipboard_set(text)
        elif action == "system.volume":
            return _system_volume(level=int(level) if level is not None else None)
        elif action == "system.dark_mode":
            return _system_dark_mode(enable=enable)
        elif action == "system.frontmost":
            return _system_frontmost_app()
        elif action == "system.apps":
            return _system_running_apps()
        elif action == "system.launch":
            if not app_name:
                return _err("app_name required for system.launch")
            return _system_launch_app(app_name)
        elif action == "system.quit":
            if not app_name:
                return _err("app_name required for system.quit")
            return _system_quit_app(app_name)
        elif action == "system.brightness":
            return _system_screen_brightness(level=level)
        elif action == "system.screenshot":
            return _system_screenshot(path=path, area=area)
        elif action == "system.say":
            if not text:
                return _err("text required for system.say")
            return _system_say(text=text, voice=voice, rate=rate)
        elif action == "system.wifi":
            return _system_wifi()
        elif action == "system.battery":
            return _system_battery()
        elif action == "system.dnd":
            return _system_do_not_disturb(enable=enable)

        # --- Shortcuts ---
        elif action == "shortcuts.list":
            return _shortcuts_list()
        elif action == "shortcuts.run":
            if not name:
                return _err("name required for shortcuts.run")
            return _shortcuts_run(name=name, input_text=input_text)

        # --- Messages ---
        elif action == "messages.send":
            if not to or not text:
                return _err("to and text required for messages.send")
            return _messages_send(to=to, text=text)
        elif action == "messages.recent":
            return _messages_recent()

        # --- Music ---
        elif action == "music.now_playing":
            return _music_now_playing()
        elif action in (
            "music.play",
            "music.pause",
            "music.next",
            "music.previous",
            "music.stop",
        ):
            return _music_control(action.split(".")[-1])

        # --- Keychain ---
        elif action == "keychain.get":
            if not service:
                return _err("service required for keychain.get")
            return _keychain_get(service=service, account=account)
        elif action == "keychain.set":
            if not service or not account or not password:
                return _err("service, account, password required for keychain.set")
            return _keychain_set(service=service, account=account, password=password)
        elif action == "keychain.delete":
            if not service:
                return _err("service required for keychain.delete")
            return _keychain_delete(service=service, account=account)

        # --- Raw execution ---
        elif action == "applescript":
            if not script:
                return _err("script required for applescript action")
            return _run_raw_applescript(script=script, timeout=timeout)
        elif action == "jxa":
            if not script:
                return _err("script required for jxa action")
            return _run_raw_jxa(script=script, timeout=timeout)

        else:
            return _err(
                f"Unknown action: {action}\n\n"
                "Valid actions: calendar.events, calendar.create, calendar.list, "
                "reminders.list, reminders.create, reminders.lists, "
                "contacts.search, contacts.create, "
                "mail.send, mail.inbox, mail.unread, "
                "safari.tabs, safari.open, safari.read, safari.url, "
                "finder.selection, finder.tag, finder.tags, finder.reveal, "
                "system.notify, system.clipboard.get, system.clipboard.set, "
                "system.volume, system.dark_mode, system.frontmost, system.apps, "
                "system.launch, system.quit, system.brightness, system.screenshot, "
                "system.say, system.wifi, system.battery, system.dnd, "
                "shortcuts.list, shortcuts.run, "
                "messages.send, messages.recent, "
                "music.now_playing, music.play, music.pause, music.next, music.previous, "
                "keychain.get, keychain.set, keychain.delete, "
                "applescript, jxa"
            )

    except subprocess.TimeoutExpired:
        return _err(f"Action '{action}' timed out after {timeout}s.")
    except Exception as e:
        logger.error(f"use_mac error: {e}")
        return _err(f"Error: {str(e)}")
