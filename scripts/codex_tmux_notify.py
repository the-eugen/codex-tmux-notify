#!/usr/bin/env python3
"""Quiet tmux status-line notifications for Codex lifecycle hooks."""

import hashlib
import json
import os
import subprocess
import sys


OPTION_PREFIX = "@codex_attention_"
WINDOW_ATTENTION = "@codex_attention"
STATUS_MARKER = "#{?@codex_attention_count,#[fg=colour214]◆ Codex #{@codex_attention_count},}"
FORMAT_SAVES = {
    "window-status-format": "@codex_notify_saved_window_status_format",
    "window-status-current-format": "@codex_notify_saved_window_status_current_format",
}
FORMAT_REFERENCE = {
    "window-status-format": "#{E:@codex_notify_saved_window_status_format}",
    "window-status-current-format": "#{E:@codex_notify_saved_window_status_current_format}",
}


def tmux(*args, input_text=None):
    try:
        return subprocess.run(
            ["tmux", *args],
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None


def pane_context():
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return None
    result = tmux("display-message", "-p", "-t", pane, "#{window_id}:#{window_active}")
    if result is None or result.returncode != 0:
        return None
    try:
        window_id, active = result.stdout.strip().rsplit(":", 1)
    except ValueError:
        return None
    return pane, window_id, active == "1"


def session_option(session_id):
    digest = hashlib.sha256(session_id.encode("utf-8", "replace")).hexdigest()[:24]
    return OPTION_PREFIX + digest


def set_session_attention(window_id, session_id, pending):
    option = session_option(session_id)
    if pending:
        tmux("set-option", "-w", "-t", window_id, option, "1")
    else:
        tmux("set-option", "-wu", "-t", window_id, option)


def clear_window(window_id):
    result = tmux("show-options", "-w", "-t", window_id)
    if result is None or result.returncode != 0:
        return
    for line in result.stdout.splitlines():
        name = line.split(None, 1)[0] if line.split(None, 1) else ""
        if name.startswith(OPTION_PREFIX):
            tmux("set-option", "-wu", "-t", window_id, name)


def option_value(name):
    result = tmux("show-options", "-gv", name)
    if result is None or result.returncode != 0:
        return None
    return result.stdout.rstrip("\n")


def refresh_attention_state():
    result = tmux("list-windows", "-a", "-F", "#{window_id}")
    if result is None or result.returncode != 0:
        return
    window_ids = sorted(set(line.strip() for line in result.stdout.splitlines() if line.strip()))
    for window_id in window_ids:
        options = tmux("show-options", "-w", "-t", window_id)
        if options is None or options.returncode != 0:
            continue
        pending = any(
            line.split(None, 1)[0].startswith(OPTION_PREFIX)
            for line in options.stdout.splitlines()
            if line.split(None, 1)
        )
        if pending:
            tmux("set-option", "-w", "-t", window_id, WINDOW_ATTENTION, "1")
        else:
            tmux("set-option", "-wu", "-t", window_id, WINDOW_ATTENTION)
    tmux("refresh-client", "-S")


def highlight_window_formats():
    for option, saved_option in FORMAT_SAVES.items():
        current = option_value(option)
        if current is None:
            continue
        reference = FORMAT_REFERENCE[option]
        saved = option_value(saved_option)
        if reference in current:
            if saved is None:
                continue
        else:
            tmux("set-option", "-g", saved_option, current)
        prefix = (
            "#{?@codex_attention,#[#{E:window-status-activity-style}],}"
            "#{?@codex_attention,#[bold],} "
        )
        suffix = "#{?@codex_attention, #[default],}"
        wrapped = f"{prefix}{reference}{suffix}"
        if current != wrapped:
            tmux("set-option", "-g", option, wrapped)


def install(plugin_dir):
    current = tmux("show-options", "-gv", "status-right")
    if current is not None and current.returncode == 0:
        status_right = current.stdout.rstrip("\n")
        if STATUS_MARKER in status_right:
            tmux("set-option", "-g", "status-right", status_right.replace(STATUS_MARKER, "").strip())
    tmux("set-option", "-gu", "@codex_attention_count")
    highlight_window_formats()

    script = os.path.join(plugin_dir, "scripts", "codex_tmux_notify.py")
    hook_command = f"run-shell -b '{script} clear-window #{{window_id}}'"
    hooks = tmux("show-hooks", "-g")
    existing = hooks.stdout if hooks is not None and hooks.returncode == 0 else ""
    if hook_command not in existing:
        tmux("set-hook", "-ag", "after-select-window", hook_command)
    refresh_attention_state()


def handle_hook():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return
    context = pane_context()
    if context is None:
        return
    _, window_id, active = context
    event = payload.get("hook_event_name", "")
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return

    if event in {"Stop", "PermissionRequest", "Interrupt"}:
        if active:
            # The user is already looking at this window; clear all its agents.
            clear_window(window_id)
        else:
            set_session_attention(window_id, session_id, True)
    elif event in {"UserPromptSubmit", "SessionEnd"}:
        set_session_attention(window_id, session_id, False)
    refresh_attention_state()


def main(argv):
    if argv and argv[0] == "install":
        install(argv[1] if len(argv) > 1 else os.path.dirname(os.path.dirname(__file__)))
    elif argv and argv[0] == "clear-window":
        window_id = argv[1] if len(argv) > 1 else None
        if window_id is None:
            context = pane_context()
            window_id = context[1] if context is not None else None
        if window_id is not None:
            clear_window(window_id)
            refresh_attention_state()
    else:
        handle_hook()


if __name__ == "__main__":
    main(sys.argv[1:])
