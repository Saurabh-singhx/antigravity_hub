# Antigravity Hub • Local Relay & Autonomous Multi-Agent Interview Prep Engine

An extensible, 100% local notification relay, remote-control bridge, and **autonomous multi-agent interview preparation engine** connecting **ANY Google Antigravity CLI workflow, coding agent, or job automation pipeline** to your mobile phone.

Pre-configured right out of the box for **Auto Job Apply (`auto_job_apply`)**.

---

## 🌟 Key Features

### 1. 🤖 Autonomous Multi-Agent Interview Prep (Trending & Verified Sources)
- **Zero Hallucinations Guarantee**: All questions and answers are extracted and verified against authentic sources (e.g. `yangshun/tech-interview-handbook`, `donnemartin/system-design-primer`, `Sudheerr/ReactJS-Interview-Questions`, LeetCode Discuss, Reddit `r/cscareerquestions`, Engineering Blogs).
- **Multi-Agent Pipeline**:
  1. `JobCollectorAgent`: Harvests recently applied jobs from `/home/saurabh/coding/auto_job_apply/data/job_applications.db` and extracts target tech stacks (Flutter, React, MERN, Python, System Design, QA).
  2. `SourceDiscoveryAgent`: Scans safe GitHub repositories and verified social media handles using the `SafetyGuardSkill` to prevent downloading from shady/malicious repos.
  3. `QnARetrieverAgent`: Fetches authentic candidate questions with exponential backoff retries.
  4. `VerificationAgent`: Verifies source grounding, difficulty rating, and technical completeness.
  5. `CuratorDispatchAgent`: Formats questions into interactive buttons, saves to SQLite, and dispatches to mobile via WebSockets and Expo Push.

### 2. ⏰ Intelligent 3-Times-A-Day Schedule & Skip Guarantee
Runs automatically when your computer boots up and follows a strict 3-slot daily schedule:
- **Slot 1 (Morning)**: `4:00 AM – 11:00 AM` ➔ *Core Fundamentals & Language Internals*
- **Slot 2 (Afternoon)**: `11:00 AM – 5:00 PM` ➔ *Architecture, Coding Patterns & System Design*
- **Slot 3 (Evening)**: `5:00 PM – 12:00 AM` ➔ *Real-World Scenarios, Company Specifics & Behavioral*
- **Quiet Period**: `12:00 AM – 4:00 AM` ➔ *No automated push notifications*

> **Intelligent Skip Logic**: If you didn't open your PC all day and boot it at night, **passed slots are automatically skipped**. You will only receive the current active slot (Evening), never a bulk dump of all 3 slots!

### 3. 🎨 Neomorphism Light Theme Mobile App
- **Interactive Question Buttons**: Questions are rendered as tactile neomorphic raised buttons. Tapping reveals the structured answer, verified source repo citation, tech badges, and master actions.
- **Daily View vs. Permanent Backend Archive**: Today's view automatically resets daily so your phone stays clean and focused on today's prep. All past questions remain permanently stored in SQLite and can be browsed in the **Archive** tab with search and pagination!
- **Complete Neomorphic Restyling**: Dual-tone soft bevels, tactile buttons, and light slate styling across all screens.

### 4. 🚀 Automatic Startup on PC Boot
- Seamlessly configured as a `systemd --user` background service (`antigravity-hub.service`) with lingering enabled.
- Starts automatically as soon as your computer boots up!
- Includes XDG autostart desktop entry fallback.

### 5. 🔌 Universal Notification & Remote Control SDK (`client_sdk/`)
- Remote actions from bed: SMS / 2FA OTP prompt entry, and screenshot inspection with Approve/Skip buttons.

---

## 🚀 Quick Start

### 1. Start the Local Backend Relay
```bash
cd /home/saurabh/coding/antigravity_hub/backend
./run_backend.sh
```
*The local relay runs at `http://0.0.0.0:8765`.*
- Swagger Docs: `http://localhost:8765/docs`
- WebSocket: `ws://localhost:8765/ws/notifications`

### 2. Install Background Service (Auto-Boot on PC Startup)
```bash
cd /home/saurabh/coding/antigravity_hub/backend
./install_service.sh
```
- Status check: `systemctl --user status antigravity-hub.service`
- Live logs: `journalctl --user -u antigravity-hub.service -f`

### 3. Start the Mobile App
```bash
cd /home/saurabh/coding/antigravity_hub/mobile
npx expo start
```
- Scan the QR code using the **Expo Go** app on Android or iOS.
- Tap **⚙️ IP** to set your computer's local Wi-Fi IP (e.g. `http://192.168.31.210:8765`).

---

## 📂 Scalable Architecture & File Structure

```
antigravity_hub/
├── backend/
│   ├── app.py                      # FastAPI entry point & WebSocket relay
│   ├── run_backend.sh              # One-click startup script
│   ├── install_service.sh          # Systemd auto-boot installer
│   ├── requirements.txt            # Python dependencies
│   ├── config/
│   │   └── settings.py             # Slot definitions, paths, thresholds, trusted repos
│   ├── core/
│   │   ├── time_slots.py           # 3-slot daily logic (Morning, Afternoon, Evening, Quiet)
│   │   └── scheduler.py            # Boot detector, skip logic & 5-minute background loop
│   ├── database/
│   │   ├── schema.py               # SQLite schemas (notifications, qna, slots, devices)
│   │   └── manager.py              # SQLite store with pagination & slot tracking
│   ├── models/
│   │   ├── notifications.py        # Notification & action Pydantic models
│   │   ├── qna.py                  # QnAItem, QnASource, Daily & Paginated schemas
│   │   └── devices.py              # Mobile device registration models
│   ├── services/
│   │   ├── notification_engine.py  # WebSocket & Expo Push dispatch
│   │   └── qna_service.py          # Daily feed & history queries
│   ├── agents/
│   │   ├── job_collector.py        # Reads recent applied jobs from auto_job_apply db
│   │   ├── source_discovery.py     # Discovers safe GitHub repos & tech handles
│   │   ├── qna_retriever.py        # Fetches authentic Q&A pairs with retries
│   │   ├── verifier.py             # Strict source-grounding & anti-hallucination check
│   │   ├── curator_dispatch.py     # Saves to SQLite & broadcasts to mobile
│   │   ├── orchestrator.py         # Multi-agent master pipeline orchestrator
│   │   └── skills/
│   │       ├── safety_guard.py     # Vets against shady repos and unsafe file types
│   │       ├── github_scanner.py   # GitHub repository search and indexer
│   │       ├── social_scanner.py   # Reliable social handles (LeetCode, r/cscareerquestions)
│   │       ├── qna_extractor.py    # Parses Q&A pairs and citation quotes
│   │       └── answer_verifier.py  # Groundedness verification engine
│   └── api/
│       ├── routes_system.py        # Health check, status, APK download
│       ├── routes_notifications.py # Send notifications, request actions, responses
│       └── routes_qna.py           # Daily feed, paginated archive, slot trigger
│
├── mobile/
│   ├── App.js                      # Root container & navigation
│   ├── src/
│   │   ├── theme/
│   │   │   └── neomorphism.js      # Neomorphic light theme design tokens
│   │   ├── components/
│   │   │   ├── NeoCard.js          # Neomorphic card container
│   │   │   ├── NeoButton.js        # Tactile neomorphic button
│   │   │   ├── NeoPill.js          # Pill badges for slots and difficulty
│   │   │   ├── QuestionButtonCard.js# Question buttons with expandable answers
│   │   │   ├── SlotProgressHeader.js# Visual 3-slot daily progress tracker
│   │   │   ├── PaginationControls.js# Paginated archive controls
│   │   │   ├── OtpModal.js         # In-app OTP dialog
│   │   │   ├── ScreenshotModal.js  # Fullscreen screenshot inspector
│   │   │   └── HubSettingsModal.js # IP settings modal
│   │   └── screens/
│   │       ├── TodayPrepScreen.js  # Today's daily prep view (resets daily)
│   │       ├── ArchiveScreen.js    # Permanent paginated Q&A history
│   │       ├── AlertsScreen.js     # Live CLI workflow alerts & actions
│   │       └── StatusScreen.js     # PC connection diagnostics & schedule rules
│
└── client_sdk/
    ├── __init__.py
    └── antigravity_notify.py       # Universal Python notifier & prep query SDK
```

---

## 🔌 Using the Universal Python Client SDK

In **ANY** Python script across `/home/saurabh/coding/`, import `notify`:

```python
import sys
sys.path.append("/home/saurabh/coding/antigravity_hub")
from client_sdk.antigravity_notify import notify

# 1. Send Application Alert
notify.send(
    workflow="auto_job_apply",
    title="🎯 Applied to Full Stack Engineer (+Flutter)",
    message="Submitted tailored resume via Wellfound.",
    level="success",
    category="job_applied",
)

# 2. Two-Way Remote Action (Wait for Phone Response!)
otp_code = notify.request_action(
    workflow="auto_job_apply",
    title="🔑 Portal OTP Verification",
    prompt="Enter the 6-digit code sent to your phone",
    action_type="input",
    timeout_seconds=120,
)

# 3. Query Today's Daily Prep from Python CLI
prep = notify.get_daily_prep()
print(f"Today's Questions: {len(prep['items'])}")
```
