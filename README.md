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
python -m bridge.main
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
config.py           .env loader and defaults
start-bridge.ps1    start / stop / status / restart wrapper (runs `python -m bridge.main`)
bridge/
  main.py               entry point: logging, context, routers, start the poller
  container.py          composition root: builds Context (state, guard, brokers, services)
  core/errors.py        BridgeError hierarchy (safe user message + technical detail)
  core/models.py        shared models (SessionInfo, StreamResult, ...)
  core/ports/agent_engine.py  AgentEngine protocol every engine implements
  core/ports/state_repository.py  StateRepository protocol
  application/
    command_router.py       slash commands -> handlers table (fallback = prompt)
    callback_router.py      inline-button data -> handlers table
    session_service.py      SessionService / ProjectService over OpenCode
    commands/               one file per command (help, status, projects, sessions, ...)
    services/prompt_runner.py   run a prompt on the active engine + stream the reply
    services/busy_guard.py      atomic per-chat "task running" lock
    services/permission_broker.py tool permission requests with TTL
  infrastructure/
    telegram/transport.py   HTTP to api.telegram.org, incl. IP fallback when DNS is blocked
    telegram/client.py      Bot API calls: send / edit / action / answer
    telegram/poller.py      getUpdates loop; each update runs in a guarded thread
    telegram/streamer.py    live message editing of streamed replies
    telegram/typing_indicator.py  periodic "typing" action, stoppable via Event
    engines/registry.py     engine kind -> AgentEngine instance
    engines/opencode/...    OpenCodeEngine: sessions, projects, models, permissions
    engines/qoder/...       QoderEngine: stream-json process, history, interrupt
    persistence/json_state_repository.py  JSON state file, atomic writes
  presentation/
    messenger.py      send text: escape + chunk + attach keyboard
    screens.py        message rendering for projects, sessions, cards, history
    html_escape.py    the only place text is escaped for Telegram HTML
    markdown_to_html.py  Markdown -> Telegram HTML
    table_renderer.py    Markdown tables: monospace grid or per-row cards
    chunker.py        split long replies, keep code blocks/tables intact
    keyboards.py      inline keyboard builders
  shared/
    logging_setup.py  logging configuration (stdout, start-bridge.ps1 compatible)
    error_boundary.py single error boundary: logs, notifies owner, never crashes a thread
    callback_registry.py  short callback keys -> payloads with TTL
tests/              unit tests (unittest; mypy --strict config in pyproject.toml)
```

## Notes

- Only `ALLOWED_ID` can talk to the bot; other chats are ignored.
- `state.json`, `bridge.log`, `bridge.pid` and `.env` are runtime/secret files and are git-ignored.
- Table rendering assumes a monospace font on the client (Telegram uses one inside `pre` blocks).
