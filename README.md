# Antigravity Hub • Local Mobile Notification & Remote Control System

An extensible, 100% local notification relay and remote-control bridge connecting **ANY Google Antigravity CLI workflow, coding agent, or automation pipeline** to your mobile phone.

Pre-configured right out of the box for **Auto Job Apply (`auto_job_apply`)**.

---

## 🌟 Key Features

1. **Universal Notification SDK (`client_sdk/`)**:
   - Any Python script, Antigravity subagent, or autonomous tool can publish alerts with a single line of code.
2. **Interactive Remote Actions (Human-in-the-Loop from Bed)**:
   - **SMS / 2FA OTP Prompt**: When portals (Naukri, LinkedIn) trigger an OTP verification, the CLI pauses, your phone vibrates, you type the 6 digits on your phone, and the CLI inputs it into the browser!
   - **Approval Before Submit**: Push a screenshot of the filled application to mobile and wait for your manual **"Approve & Submit"** or **"Skip"** tap.
3. **100% Local Backend (FastAPI + WebSockets + SQLite)**:
   - Zero cloud database lock-in. No Supabase needed. All candidate data, CTC details, and cookies remain on your machine.
   - Real-time WebSockets for instant 0ms LAN updates.
   - Expo Push Notifications gateway for native lock-screen push alerts on Android & iOS.
4. **React Native / Expo Mobile App (`mobile/`)**:
   - Sleek dark-mode interface with live status badge.
   - Filter tabs: `All`, `Job Apply`, `Actions Required`, `Errors`.
   - Fullscreen browser screenshot inspection (view CAPTCHA puzzles or blocked pages).
   - In-app action resolution.

---

## 🚀 Quick Start

### 1. Start the Local Backend Relay
```bash
cd /home/saurabh/coding/antigravity_hub/backend
./run_backend.sh
```
*The local relay starts at `http://0.0.0.0:8765`.*
- Swagger Docs: `http://localhost:8765/docs`
- WebSocket: `ws://localhost:8765/ws/notifications`

---

### 2. Start the Mobile App
```bash
cd /home/saurabh/coding/antigravity_hub/mobile
npx expo start
```
- Open the **Expo Go** app on your Android or iPhone and scan the QR code displayed in the terminal.
- Tap **⚙️ IP** in the top bar of the mobile app to set your computer's local IP (e.g. `http://192.168.1.15:8765`).

---

## 🔌 Connecting ANY Antigravity Workflow

In **ANY** Python script or agent across `/home/saurabh/coding/`, import the universal notifier:

```python
import sys
sys.path.append("/home/saurabh/coding/antigravity_hub")
from client_sdk.antigravity_notify import notify

# 1. Informational / Success Alert
notify.send(
    workflow="coding_agent",
    title="🚀 Build Succeeded",
    message="Compiled 48 modules in 12.4s. All unit tests passed.",
    level="success",
)

# 2. Critical Alert with Browser Screenshot
notify.send(
    workflow="auto_job_apply",
    title="⚠️ Turnstile CAPTCHA Blocked",
    message="Indeed triggered verification on card #8.",
    level="critical",
    category="captcha",
    screenshot_path="data/screenshots/captcha.png",
)

# 3. Two-Way Remote Action (Wait for Phone Response!)
otp_code = notify.request_action(
    workflow="auto_job_apply",
    title="🔑 Naukri OTP Required",
    prompt="Enter the 6-digit SMS code sent to +91 98765*****",
    action_type="input",
    timeout_seconds=120,
)
if otp_code:
    print(f"Received OTP from mobile: {otp_code}")
    page.fill("#otp_input", otp_code)
```

---

## 📂 Project Structure

```
antigravity_hub/
├── backend/
│   ├── app.py                 # FastAPI REST & WebSocket Server
│   ├── db.py                  # Local SQLite manager (hub.db)
│   ├── models.py              # Pydantic data schemas
│   ├── notification_engine.py # WebSocket + Expo Push Engine
│   ├── run_backend.sh         # One-click startup script
│   └── data/                  # SQLite store & captured screenshots
│
├── mobile/
│   ├── App.js                 # React Native Mobile App
│   ├── app.json               # Expo configuration
│   └── package.json           # Dependencies
│
└── client_sdk/
    ├── __init__.py
    └── antigravity_notify.py  # Universal Python notifier
```
