# telegram-bridge

A Telegram bot that turns a chat into a remote control for AI coding CLIs on a Windows machine.
It drives two engines behind one interface:

- **OpenCode** — via the local OpenCode HTTP server (`opencode serve`): projects, sessions, agents, models, live streaming, permission requests.
- **Qoder** — via its CLI (`qoder run`): single working directory, session list, live streaming.

Messages are converted from Markdown to Telegram-safe HTML, with special handling for tables
(rendered as monospace grids) and long messages (split into chunks).

## Requirements

- Python 3.10+ (stdlib only, no third-party packages)
- [OpenCode CLI](https://opencode.ai) with a running server, and/or Qoder CLI
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## Setup

1. Copy the config template and fill in your values:

```bash
cp .env.example .env
```

2. Edit `.env`:

| Key | Meaning |
|---|---|
| `BOT_TOKEN` | Telegram bot token |
| `ALLOWED_ID` | Numeric Telegram user id allowed to use the bot (owner) |
| `QODER_DIR` | Default working directory |
| `QODER_BIN` | Path/filename of the Qoder executable |
| `QODER_PERMISSION_MODE` | Qoder permission mode (default `accept_edits`) |
| `QODER_TIMEOUT` | Qoder run timeout in seconds (default `900`) |
| `OPENCODE_BIN` | Path to the OpenCode executable |
| `OPENCODE_PROVIDER` / `OPENCODE_MODEL` | Default provider/model |
| `OPENCODE_TIMEOUT` | Response timeout in seconds (default `600`) |
| `STREAM_INTERVAL` | Minimum seconds between streamed edits (default `1.6`) |

3. Run:

```powershell
python bot.py
```

Or use the helper script (writes `bridge.log`, tracks the PID):

```powershell
.\start-bridge.ps1 start
.\start-bridge.ps1 status
.\start-bridge.ps1 stop
```

## Commands

| Command | Action |
|---|---|
| `/start`, `/help`, `/menu` | Main menu |
| `/src [qoder\|opencode]` | Switch engine (each engine keeps its own dir/session) |
| `/projects` | List OpenCode projects |
| `/sessions` | List sessions/chat history for the current engine |
| `/open <n>` | Open session by index or id prefix |
| `/new` | Start a new session/conversation |
| `/cd [path]` | Change working directory (browse if no path) |
| `/model [query]` | Pick a model |
| `/agent` | Pick an agent (OpenCode) |
| `/history [n]` | Show last messages |
| `/stop` | Interrupt the running task |
| `/status` | Engine, workdir, busy state |
| any other text | Sent to the active engine as a prompt |

## Structure

```
bot.py              entry point: Telegram polling loop, routing, streaming, menu
config.py           .env loader and defaults
telegram.py         raw Bot API client (sendMessage, edit, keyboards) + live Streamer
formatting.py       Markdown -> Telegram HTML, table/grid rendering, chunking
state.py            per-chat state in state.json (engine, workdir, session, model)
opencode_api.py     small helper around the OpenCode REST API
bridge/
  core/errors.py        BridgeError hierarchy (safe user message + technical detail)
  shared/logging_setup.py  logging configuration (stdout, start-bridge.ps1 compatible)
  shared/error_boundary.py single error boundary: logs, notifies owner, never crashes a thread
backends/
  opencode.py       OpenCode backend: sessions, models, agents, permission replies, streaming
  qoder.py          Qoder CLI backend: subprocess streaming, session list, local history log
engine/
  registry.py       short callback keys -> payloads with TTL
  projects.py       project/session listing for OpenCode
  lifecycle.py      create/open/switch session helpers
  screens.py        message rendering for projects, sessions, cards, history
  actions.py        callback_data router (buttons)
tests/              unit tests (unittest; mypy --strict config in pyproject.toml)
```

## Notes

- Only `ALLOWED_ID` can talk to the bot; other chats are ignored.
- `state.json`, `bridge.log`, `bridge.pid` and `.env` are runtime/secret files and are git-ignored.
- Table rendering assumes a monospace font on the client (Telegram uses one inside `pre` blocks).
