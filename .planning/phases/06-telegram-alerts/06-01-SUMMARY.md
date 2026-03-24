---
phase: 06-telegram-alerts
plan: 01
subsystem: alerts, api
tags: [telegram, python-telegram-bot, bot, async, background-thread]

dependency-graph:
  requires: []
  provides:
    - "src/alerts/bot.py — Telegram bot with /start and /status commands"
    - "src/alerts/__init__.py — alerts package"
    - "SUBSCRIBED_CHATS set for chat_id registration"
    - "start_bot() / stop_bot() lifecycle functions"
    - "_format_signal_message() for signal display formatting"
    - "telegram_bot_token config field in Settings"
  affects: [06-telegram-alerts-02, 06-telegram-alerts-03]

tech-stack:
  added: [python-telegram-bot]
  patterns:
    - "Bot runs in daemon thread via threading.Thread"
    - "Module-level state: SUBSCRIBED_CHATS, _application, _thread, _db_path"
    - "asyncio.to_thread for sync compute_signal in async handler"

key-files:
  created:
    - src/alerts/__init__.py
    - src/alerts/bot.py
    - tests/test_bot.py
  modified:
    - src/config.py
    - pyproject.toml

key-decisions:
  - "Bot runs in daemon thread, not asyncio — simpler lifecycle with APScheduler"
  - "Empty token = bot disabled with warning log, not crash"
  - "Module-level SUBSCRIBED_CHATS set shared between bot and dispatcher"
  - "Emoji badges: BUY=🟢, HOLD=🟡, SELL=🔴 for visual signal clarity"

patterns-established:
  - "Alert formatting: Vietnamese + English bilingual messages"
  - "Disclaimer footer: 'Đây là thông tin thị trường, không phải tư vấn đầu tư'"

requirements-completed: []

metrics:
  duration: 4min
  completed: 2026-03-25T20:05:00Z
---

# Phase 6 Plan 01: Telegram Bot Setup Summary

**Telegram bot with /start (chat_id registration) and /status (signal display) commands, running in background thread via python-telegram-bot 22.x**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-25T20:01:03Z
- **Completed:** 2026-03-25T20:05:00Z
- **Tasks:** 1
- **Files modified:** 5

## Accomplishments
- Telegram bot module with /start and /status command handlers
- Bot lifecycle management (start/stop) via daemon thread
- Signal formatting with emoji badges, gap info, and bilingual disclaimer
- Graceful handling of missing bot token
- 13 unit tests covering handlers, formatting, and lifecycle

## Task Commits

1. **Task 1: Telegram bot module (TDD RED)** - `97d9621` (test)
2. **Task 1: Telegram bot module (TDD GREEN)** - `ff239f8` (feat)

## Files Created/Modified
- `src/alerts/__init__.py` - Alerts package init
- `src/alerts/bot.py` - Bot with /start, /status, lifecycle management, signal formatting
- `src/config.py` - Added telegram_bot_token setting
- `tests/test_bot.py` - 13 unit tests for bot handlers, formatting, lifecycle
- `pyproject.toml` - Added python-telegram-bot>=22.0 dependency

## Decisions Made
- Bot runs in daemon thread (not asyncio) — simpler lifecycle management alongside APScheduler
- Empty token disables bot with log warning rather than crashing the application
- Module-level SUBSCRIBED_CHATS set for sharing between bot and dispatcher (Plan 02)
- Bilingual messages (Vietnamese primary + English) for accessibility

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed missing compute_signal import in bot module**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** bot.py used compute_signal without importing it
- **Fix:** Added `from src.engine.pipeline import compute_signal` import
- **Files modified:** src/alerts/bot.py
- **Verification:** All 13 tests pass
- **Committed in:** `ff239f8`

**2. [Rule 1 - Bug] Fixed test async mock for update.message.reply_text**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Test used MagicMock for update.message but handler awaits reply_text
- **Fix:** Set update.message.reply_text = AsyncMock() in all test cases
- **Files modified:** tests/test_bot.py
- **Verification:** All 13 tests pass
- **Committed in:** `ff239f8`

**3. [Rule 1 - Bug] Fixed test _db_path initialization**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** status_handler checks _db_path and returns early if empty; tests didn't set it
- **Fix:** Set bot_module._db_path = "/tmp/test.db" before status tests
- **Files modified:** tests/test_bot.py
- **Verification:** All 13 tests pass
- **Committed in:** `ff239f8`

---

**Total deviations:** 3 auto-fixed (3 bugs)
**Impact on plan:** All fixes were test corrections during GREEN phase. No scope creep.

## Issues Encountered
None — straightforward implementation.

## Known Stubs
None.

## User Setup Required

To enable Telegram alerts, set the environment variable:
```bash
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
```
Without this, the bot is disabled (no crash, just a warning log).

## Next Phase Readiness
- Bot module ready for Plan 02 dispatcher integration
- SUBSCRIBED_CHATS set available for dispatcher to read
- _application reference available for dispatcher to send messages
- start_bot/stop_bot ready for Plan 03 lifespan wiring

---
*Phase: 06-telegram-alerts*
*Completed: 2026-03-25*

## Self-Check: PASSED
