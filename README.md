# codex-tmux-notify

A quiet tmux status-line indicator for Codex sessions that finish a turn, request approval, or are interrupted while their window is in the background. It uses Codex lifecycle hooks and tmux window options; it never rings the terminal bell or opens a popup.

## Install

Create a symlink from the plugin checkout to tmux's plugin folder. Replace `/path/to/codex-tmux-notify` with the full path to this checkout:

```sh
mkdir -p "$HOME/.tmux/plugins"
ln -s /path/to/codex-tmux-notify "$HOME/.tmux/plugins/codex-tmux-notify"
```

Add this to `~/.tmux.conf` so the plugin loads automatically when the tmux server starts:

```tmux
run-shell -b 'exec "$HOME/.tmux/plugins/codex-tmux-notify/codex-tmux-notify.tmux"'
```

Load the plugin in the current server and on future starts by reloading the tmux config:

```sh
tmux source-file "$HOME/.tmux.conf"
```

Configure the Codex hooks in `~/.codex/hooks.json`. If that file does not exist yet, copy the provided configuration:

```sh
mkdir -p "$HOME/.codex"
cp "$HOME/.tmux/plugins/codex-tmux-notify/codex-hooks.json" "$HOME/.codex/hooks.json"
```

If `~/.codex/hooks.json` already exists, merge the provided event entries into its `hooks` object instead of replacing the file. Restart Codex or reload its hooks, then review and trust them with `/hooks` when prompted.

## Behavior

- `Stop`, `PermissionRequest`, and `Interrupt` mark the originating Codex session as needing attention.
- `UserPromptSubmit` clears only that Codex session's marker. Other agents in the same window remain pending.
- `SessionEnd` clears the ending session's marker.
- Notifications are suppressed if that agent's tmux window is active when the event occurs.
- Switching to a marked window clears all pending markers in that window.
- <img width="316" height="143" alt="Screenshot 2026-09-24 135434" src="https://github.com/user-attachments/assets/59f24e28-0e3c-4236-889e-7f1d35986c25" />
