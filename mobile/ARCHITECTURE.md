# Antigravity Hub • Mobile Client Architecture & Design System

**Version:** 2.2.0  
**Framework:** React Native 0.86.3 • React 19.2.3 • Expo SDK 57 • Kotlin • Android Room SQLite • Expo Notifications  
**Repository Path:** [`mobile/`](file:///home/saurabh/coding/antigravity_hub/mobile)  
**Master Architecture & Evolution Blueprint:** [`../ARCHITECTURE.md`](file:///home/saurabh/coding/antigravity_hub/ARCHITECTURE.md)

---

## 📱 Mobile Architecture Overview

The **Antigravity Hub Mobile App** is a tactile, high-performance cross-platform application designed for daily interview preparation, system observability, and zero-latency human-in-the-loop remote control.

```mermaid
flowchart TD
    subgraph UI ["Neomorphism UI Layer (Light Theme)"]
        Nav["Navigation Header & Tab Bar"]
        Tab1["TodayPrepScreen (3-Slot Active Feed)"]
        Tab2["ArchiveScreen (SQLite Paginated History)"]
        Tab3["AlertsScreen (Live Feed & Actions)"]
        Tab4["StatusScreen (Health & Diagnostics)"]
        
        Nav --> Tab1
        Nav --> Tab2
        Nav --> Tab3
        Nav --> Tab4
    end

    subgraph Modals ["Security & Interaction Modals"]
        SettingsModal["HubSettingsModal (IP & Token Auth)"]
        ScreenshotModal["ScreenshotModal (Protected Images)"]
        OtpModal["OtpModal (2FA / OTP Prompts)"]
    end

    subgraph StateAndStorage ["Local State & Storage Layer"]
        AsyncStore[("@react-native-async-storage")]
        URLState["Hub URL State"]
        TokenState["Hub Token State (X-Hub-Token)"]
        AsyncStore --> URLState
        AsyncStore --> TokenState
    end

    subgraph NetworkEngine ["Zero-Trust Networking Engine"]
        HTTPClient["Authenticated fetch() (Headers: X-Hub-Token)"]
        WSClient["WebSocket Client (/ws/notifications?token=...)"]
        PushEngine["Expo Notifications Engine (Android Bar Banners)"]
    end

    StateAndStorage --> NetworkEngine
    NetworkEngine --> HubBackend["Antigravity Hub Backend (FastAPI :8765)"]
```

---

## 🎨 Neomorphism Design System Tokens ([`neomorphism.js`](file:///home/saurabh/coding/antigravity_hub/mobile/src/theme/neomorphism.js))

The user interface follows a modern, dual-tone **Neomorphism Light Theme** optimized for focus and tactile satisfaction.

### 1. Color Palette
| Token | Value | Role |
| :--- | :--- | :--- |
| `background` | `#e6eef8` | Soft blue-gray ambient canvas |
| `cardBg` | `#ebf1f8` | Raised surface tone |
| `primary` | `#2563eb` | Vibrant brand accent |
| `primaryDark` | `#1d4ed8` | Pressed / active state |
| `textPrimary` | `#0f172a` | High-contrast slate header typography |
| `textSecondary`| `#475569` | Body & meta text |
| `shadowLight` | `#ffffff` | Top-left specular bevel reflection |
| `shadowDark` | `#b8c9dc` | Bottom-right ambient occlusion shadow |

### 2. Neomorphic Component Library
- [`NeoCard`](file:///home/saurabh/coding/antigravity_hub/mobile/src/components/NeoCard.js): Elevated card wrapper featuring soft top-left white bevel and bottom-right blue-gray ambient drop shadow.
- [`NeoButton`](file:///home/saurabh/coding/antigravity_hub/mobile/src/components/NeoButton.js): Tactile action button with dynamic active press compression.
- [`NeoPill`](file:///home/saurabh/coding/antigravity_hub/mobile/src/components/NeoPill.js): Category and tech-stack badge indicator with subtle border relief.
- [`QuestionButtonCard`](file:///home/saurabh/coding/antigravity_hub/mobile/src/components/QuestionButtonCard.js): Primary learning card rendering questions as tactile buttons; tapping unfolds verified answers, authentic source links, difficulty badges, and review toggles.

---

## 🔐 Security & Network Architecture

### 1. Token-Based Authentication (`X-Hub-Token`)
- **Credential Storage**: The pre-shared hub token is saved locally in encrypted app storage via `@react-native-async-storage/async-storage` under the key `antigravity_hub_token`.
- **Request Ingestion**: Every API request (`TodayPrepScreen`, `ArchiveScreen`, `StatusScreen`, `AlertsScreen`) automatically attaches:
  ```javascript
  headers: {
    'Content-Type': 'application/json',
    'X-Hub-Token': hubToken,
    'Authorization': `Bearer ${hubToken}`
  }
  ```
- **Connection Diagnostics**: The [`HubSettingsModal`](file:///home/saurabh/coding/antigravity_hub/mobile/src/components/HubSettingsModal.js) includes a **"🔍 Test Auth"** tool that executes an authenticated probe to `/api/auth/verify`, giving instant feedback (`✅ Verified!`, `❌ 401 Unauthorized`, or `❌ Unreachable`).

### 2. Authenticated Real-Time WebSocket Streaming
- Connection URL: `ws://<ip>:<port>/ws/notifications?token=<encoded_token>`
- **Live Re-keying**: If the user updates their token in settings, the WebSocket automatically teardowns the existing socket and reconnects with the new token.
- **Resilient Auto-Reconnection**: Reconnects automatically on network drops (exponential backoff 3.5s – 4.0s) and syncs immediately when the app returns from background to active via `AppState`.

### 3. Ephemeral Action Nonces & Verification
- When an OTP prompt or human approval is triggered, the notification includes a cryptographically secure `action_secret`.
- When the user types the OTP or presses "Approve", the payload submits:
  ```json
  {
    "action_id": "act_12345",
    "response_value": "592014",
    "action_secret": "v8k9La..."
  }
  ```
  preventing replay or unauthorized resolution by third parties.

### 4. Protected Screenshot Streaming
- Screenshots sent from automation pipelines are served through the authenticated backend route.
- The mobile app appends the active session token:
  `${screenshotUrl}?token=${hubToken}`
  enabling `<Image source={{ uri: finalUrl }} />` to render the protected asset while denying public access.

---

## 📑 Screen Breakdown & User Flows

```mermaid
graph LR
    App[App.js] --> Prep[TodayPrepScreen]
    App --> Archive[ArchiveScreen]
    App --> Alerts[AlertsScreen]
    App --> Status[StatusScreen]

    Prep --> Card[QuestionButtonCard]
    Prep --> Progress[SlotProgressHeader]
    
    Archive --> Filters[Category Pills]
    Archive --> Search[Keyword Search]
    Archive --> Pagination[PaginationControls]

    Alerts --> Actions[OTP / Approval Prompts]
    Alerts --> Preview[ScreenshotModal]

    Status --> Diagnostic[Relay Ping & Security Badge]
    Status --> Settings[HubSettingsModal]
```

### 1. Today's Prep (`TodayPrepScreen`)
- **Daily Refresh Policy**: Questions are scoped to `today` (`YYYY-MM-DD`). Yesterday's questions automatically move to the permanent Archive, ensuring the daily view is clean, focused, and free of overwhelm.
- **Slot Progress Header**: Tracks completion for the 3 daily slots:
  - 🌅 Morning Fundamentals
  - ☀️ Afternoon Architecture
  - 🌙 Evening Scenarios
- **Mastered Toggles**: Mark questions as mastered or flag them for review.

### 2. Archive & History (`ArchiveScreen`)
- **Permanent SQLite Archive**: All questions from all past days are permanently preserved on the backend.
- **Search & Filter**: Real-time keyword search across questions and answers with category filters (`Fundamentals`, `Architecture`, `System Design`, `Real-World`, `Behavioral`).
- **Paginated Scrolling**: Efficient pagination controls with 8 items per page to prevent memory overhead.

### 3. Alerts & Remote Control (`AlertsScreen`)
- Displays real-time CLI activity feeds (e.g. applications submitted, test results).
- **Interactive Action Triggers**:
  - `input`: Pops up [`OtpModal`](file:///home/saurabh/coding/antigravity_hub/mobile/src/components/OtpModal.js) for SMS / 2FA OTP codes.
  - `confirm`: Approve / Reject buttons for autonomous actions.
  - `screenshot`: Opens fullscreen [`ScreenshotModal`](file:///home/saurabh/coding/antigravity_hub/mobile/src/components/ScreenshotModal.js) to inspect portal pages before approving.

### 4. Relay Status & Security Diagnostics (`StatusScreen`)
- Displays live backend connection status, server URL, and security state (`🔒 Authenticated (X-Hub-Token set)`).
- Quick manual slot triggers to run the multi-agent pipeline on-demand.
- Test alert dispatcher to verify end-to-end push notification delivery.

---

## 🔔 Native Push & System Banner System

Configured via `expo-notifications`:
- **Android 13+ Runtime Permissions**: Automatically requests `POST_NOTIFICATIONS` permission on boot.
- **High-Priority Channel**: Configured with `importance: MAX`, custom vibration rhythm (`[0, 250, 250, 250]`), and bypass-DND flags.
- **Zero-Latency WebSocket Banners**: Incoming WebSocket payloads trigger native Android notification drawer banners so you receive alerts even when glancing away from the screen.

---

## 🚀 Native Android Background Architecture (`mobile/android/`)

To guarantee real-time alert delivery even when the app is completely swiped away or closed:

### 1. `HubForegroundService.kt`
- Implements an Android native `Service` configured with `FOREGROUND_SERVICE_TYPE_DATA_SYNC`.
- Maintains an ongoing, low-profile notification (*"Antigravity Hub Active"*).
- Establishes a background OkHttp WebSocket connection directly to the backend relay with 20s ping heartbeats and 5s exponential reconnection.

### 2. Native Kotlin to React Native AsyncStorage Bridge (`RKStorage` Room DB)
- **The Problem**: In modern React Native versions, `@react-native-async-storage/async-storage` does not store keys in `SharedPreferences`. Instead, it writes to an internal SQLite database managed by Android Room (`RKStorage` / `catalystLocalStorage`).
- **The Solution**: `HubForegroundService.kt` directly queries the SQLite database on disk:
  ```kotlin
  val db = SQLiteDatabase.openDatabase(dbFile.path, null, SQLiteDatabase.OPEN_READONLY)
  val cursor = db.rawQuery("SELECT value FROM catalystLocalStorage WHERE key = ?", arrayOf("antigravity_hub_token"))
  ```
  This enables the background Kotlin service to authenticate WebSocket connections seamlessly without needing the React Native JavaScript engine to be awake!

### 3. `BootReceiver.kt`
- Listens for `Intent.ACTION_BOOT_COMPLETED` and starts `HubForegroundService` automatically when the phone turns on.

