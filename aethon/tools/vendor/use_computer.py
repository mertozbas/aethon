"""🖥️ Computer control tool.

Control mouse, keyboard, take screenshots, scroll, drag, switch apps.
Uses pyautogui for cross-platform automation.

Dependencies: pip install pyautogui

Examples:
    use_computer(action="screenshot")
    use_computer(action="click", x=500, y=300)
    use_computer(action="type", text="Hello world")
    use_computer(action="hotkey", keys=["cmd", "c"])
    use_computer(action="scroll", direction="down", clicks=5)
    use_computer(action="drag", x=100, y=100, to_x=500, to_y=500)
"""

import os
import platform
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from strands import tool

# Lazy import pyautogui
_pyautogui = None


def _get_pyautogui():
    global _pyautogui
    if _pyautogui is None:
        import pyautogui

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        _pyautogui = pyautogui
    return _pyautogui


def _normalize_key(key: str) -> str:
    """Normalize key names across platforms."""
    system = platform.system().lower()
    if system == "darwin":
        mapping = {
            "cmd": "command",
            "ctrl": "ctrl",
            "opt": "option",
            "alt": "option",
            "super": "command",
        }
    else:
        mapping = {
            "cmd": "winleft",
            "ctrl": "ctrl",
            "opt": "alt",
            "alt": "alt",
            "super": "winleft",
        }
    return mapping.get(key.lower(), key.lower())


@tool
def use_computer(
    action: str,
    x: Optional[int] = None,
    y: Optional[int] = None,
    to_x: Optional[int] = None,
    to_y: Optional[int] = None,
    text: Optional[str] = None,
    key: Optional[str] = None,
    keys: Optional[List[str]] = None,
    clicks: int = 3,
    direction: str = "down",
    button: str = "left",
    duration: float = 0.5,
    interval: float = 0.0,
    region: Optional[List[int]] = None,
    app_name: Optional[str] = None,
    screen_number: int = 1,
) -> Dict[str, Any]:
    """🖥️ Computer control - mouse, keyboard, screenshots, scrolling.

    Args:
        action: Action to perform:
            Mouse: mouse_position, click, double_click, right_click, middle_click, move_mouse, drag, scroll
            Keyboard: type, key_press, hotkey
            Screen: screenshot, screen_size
            Window: switch_app, minimize_all, show_desktop, mission_control
            Info: get_system_info
        x: X coordinate for mouse actions
        y: Y coordinate for mouse actions
        to_x: Destination X for drag
        to_y: Destination Y for drag
        text: Text to type
        key: Key to press (enter, tab, space, escape, etc.)
        keys: Key combination (e.g., ["cmd", "c"])
        clicks: Scroll amount (default: 3)
        direction: Scroll direction (up, down, left, right)
        button: Mouse button (left, right, middle)
        duration: Mouse movement duration in seconds
        interval: Interval between keystrokes when typing
        region: Screenshot region [left, top, width, height]
        app_name: Application name for switch_app
        screen_number: Screen number for switch_screen

    Returns:
        Dict with status, content (and image for screenshots)
    """
    try:
        pag = _get_pyautogui()

        if action == "mouse_position":
            mx, my = pag.position()
            return {"status": "success", "content": [{"text": f"Mouse: ({mx}, {my})"}]}

        elif action == "screenshot":
            screenshots_dir = os.path.expanduser("~/.aethon/screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(screenshots_dir, f"screenshot_{ts}.png")

            screenshot = (
                pag.screenshot(region=tuple(region)) if region else pag.screenshot()
            )
            screenshot.save(filepath)

            with open(filepath, "rb") as f:
                file_bytes = f.read()

            return {
                "status": "success",
                "content": [
                    {"text": f"Screenshot saved: {filepath}"},
                    {"image": {"format": "png", "source": {"bytes": file_bytes}}},
                ],
            }

        elif action == "click":
            if x is None or y is None:
                return {
                    "status": "error",
                    "content": [{"text": "x and y required for click"}],
                }
            pag.moveTo(x, y, duration=duration)
            pag.click(button=button)
            return {
                "status": "success",
                "content": [{"text": f"Clicked ({x}, {y}) [{button}]"}],
            }

        elif action == "double_click":
            if x is None or y is None:
                return {"status": "error", "content": [{"text": "x and y required"}]}
            pag.moveTo(x, y, duration=duration)
            pag.doubleClick()
            return {
                "status": "success",
                "content": [{"text": f"Double-clicked ({x}, {y})"}],
            }

        elif action == "right_click":
            if x is None or y is None:
                return {"status": "error", "content": [{"text": "x and y required"}]}
            pag.moveTo(x, y, duration=duration)
            pag.rightClick()
            return {
                "status": "success",
                "content": [{"text": f"Right-clicked ({x}, {y})"}],
            }

        elif action == "middle_click":
            if x is None or y is None:
                return {"status": "error", "content": [{"text": "x and y required"}]}
            pag.moveTo(x, y, duration=duration)
            pag.middleClick()
            return {
                "status": "success",
                "content": [{"text": f"Middle-clicked ({x}, {y})"}],
            }

        elif action == "move_mouse":
            if x is None or y is None:
                return {"status": "error", "content": [{"text": "x and y required"}]}
            pag.moveTo(x, y, duration=duration)
            return {"status": "success", "content": [{"text": f"Moved to ({x}, {y})"}]}

        elif action == "drag":
            if any(v is None for v in [x, y, to_x, to_y]):
                return {
                    "status": "error",
                    "content": [{"text": "x, y, to_x, to_y required for drag"}],
                }
            pag.moveTo(x, y, duration=0.3)
            pag.dragTo(to_x, to_y, duration=max(duration, 0.5), button=button)
            return {
                "status": "success",
                "content": [{"text": f"Dragged ({x},{y}) → ({to_x},{to_y})"}],
            }

        elif action == "scroll":
            if x is not None and y is not None:
                pag.moveTo(x, y, duration=0.2)

            if direction in ("up", "down"):
                amt = clicks if direction == "up" else -clicks
                pag.scroll(amt)
            else:
                # Horizontal scroll - use hscroll if available (pyautogui 0.9.54+)
                amt = clicks if direction == "right" else -clicks
                if hasattr(pag, "hscroll"):
                    pag.hscroll(amt)
                else:
                    # Fallback: AppleScript for macOS horizontal scroll
                    import platform as _pf

                    if _pf.system() == "Darwin":
                        import subprocess

                        # Use cliclick or osascript for horizontal scroll
                        try:
                            subprocess.run(
                                [
                                    "osascript",
                                    "-e",
                                    f'tell application "System Events" to scroll area 1 of front window of front application to {{0, 0, {amt * 50}, 0}}',
                                ],
                                capture_output=True,
                                timeout=3,
                            )
                        except Exception:
                            pass  # Best effort
                    else:
                        # Linux/Windows: shift+scroll works
                        pag.keyDown("shift")
                        pag.scroll(amt)
                        pag.keyUp("shift")
            return {
                "status": "success",
                "content": [{"text": f"Scrolled {direction} {clicks}"}],
            }

        elif action == "type":
            if not text:
                return {
                    "status": "error",
                    "content": [{"text": "text required for type"}],
                }
            pag.typewrite(text, interval=interval)
            return {"status": "success", "content": [{"text": f"Typed: {text[:100]}"}]}

        elif action == "key_press":
            if not key:
                return {"status": "error", "content": [{"text": "key required"}]}
            pag.press(key)
            return {"status": "success", "content": [{"text": f"Pressed: {key}"}]}

        elif action == "hotkey":
            if not keys:
                return {
                    "status": "error",
                    "content": [{"text": "keys required for hotkey"}],
                }
            normalized = [_normalize_key(k) for k in keys]
            pag.hotkey(*normalized)
            return {
                "status": "success",
                "content": [{"text": f"Hotkey: {' + '.join(keys)}"}],
            }

        elif action == "screen_size":
            w, h = pag.size()
            return {"status": "success", "content": [{"text": f"Screen: {w}x{h}"}]}

        elif action == "switch_app":
            if not app_name:
                return {"status": "error", "content": [{"text": "app_name required"}]}
            system = platform.system().lower()
            if system == "darwin":
                pag.hotkey("command", "space")
                time.sleep(0.5)
                pag.typewrite(app_name)
                time.sleep(0.5)
                pag.press("enter")
            elif system == "windows":
                pag.press("win")
                time.sleep(0.5)
                pag.typewrite(app_name)
                time.sleep(0.5)
                pag.press("enter")
            else:
                pag.hotkey("alt", "f2")
                time.sleep(0.5)
                pag.typewrite(app_name)
                time.sleep(0.5)
                pag.press("enter")
            return {
                "status": "success",
                "content": [{"text": f"Switched to {app_name}"}],
            }

        elif action == "minimize_all":
            system = platform.system().lower()
            if system == "darwin":
                pag.hotkey("command", "option", "h", "m")
            else:
                pag.hotkey("winleft" if system == "windows" else "super", "d")
            return {"status": "success", "content": [{"text": "Minimized all windows"}]}

        elif action == "show_desktop":
            system = platform.system().lower()
            if system == "darwin":
                pag.hotkey("fn", "f11")
            else:
                pag.hotkey("winleft" if system == "windows" else "super", "d")
            return {"status": "success", "content": [{"text": "Showing desktop"}]}

        elif action == "mission_control":
            system = platform.system().lower()
            if system == "darwin":
                pag.hotkey("ctrl", "up")
            elif system == "windows":
                pag.hotkey("win", "tab")
            else:
                pag.hotkey("super")
            return {
                "status": "success",
                "content": [{"text": "Opened mission control"}],
            }

        elif action == "get_system_info":
            info = {
                "platform": platform.system(),
                "screen": list(pag.size()),
                "mouse": list(pag.position()),
            }
            return {"status": "success", "content": [{"text": f"System: {info}"}]}

        else:
            return {
                "status": "error",
                "content": [{"text": f"Unknown action: {action}"}],
            }

    except ImportError:
        return {
            "status": "error",
            "content": [{"text": "pyautogui not installed. pip install pyautogui"}],
        }
    except Exception as e:
        return {"status": "error", "content": [{"text": f"Error: {e}"}]}
