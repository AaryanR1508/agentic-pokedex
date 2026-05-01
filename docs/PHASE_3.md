# 💻 Phase 3: The Frontend UI — Implementation Plan

**Owner:** Frontend/UI Engineer  
**Goal:** Build a highly dynamic, visually stunning React SPA (Single Page Application) that serves as the user interface for the Agentic Pokédex. It must handle multi-modal inputs (text, image uploads, audio recording) and beautifully display the resulting conversational response alongside a dynamic "Pokédex Visor" data card.

> [!IMPORTANT]
> The design must not feel like a generic minimum viable product. It needs to look **premium**, utilizing vibrant Pokédex-inspired colors (classic red/glassmorphism), smooth micro-animations, and responsive layouts.

---

## 1. Environment & Tooling Setup

### 1.1 Project Initialization

- The frontend is located in the `frontend/` directory.
- Initialize the project using Vite: `npm create vite@latest . -- --template react` (if not already done).
- The `Dockerfile` for the frontend is already provided in the Phase 0 infrastructure plan and uses `node:20-alpine`.

### 1.2 Required Dependencies

Install the following via `npm install`:

| Package | Purpose |
|---|---|
| `react` & `react-dom` | Core framework |
| `tailwindcss` | Rapid utility-first styling for building premium layouts and animations |
| `axios` | Robust HTTP client for handling `multipart/form-data` requests |
| `lucide-react` | Sleek, modern SVG icons for UI buttons (mic, camera, send) |
| `framer-motion` | (Optional but highly recommended) For complex, smooth mount/unmount animations of the Visor card |
| `react-markdown` | To render the markdown-formatted responses coming from Gemini |

> [!NOTE]
> **Styling:** Use **TailwindCSS** for rapid, utility-first styling. Tailwind makes it extremely easy to implement the required glassmorphism effects (e.g., `backdrop-blur-md bg-white/10`) and responsive layouts without writing custom CSS files.

### 1.3 Environment Variables

Ensure Vite can access the backend URL:
- `.env` file in the `frontend/` directory: `VITE_API_URL=http://localhost:8000`
- Access in code via `import.meta.env.VITE_API_URL`

---

## 2. UI/UX Design System & Layout

The application should follow a split-pane layout on desktop, collapsing to a stacked view on mobile.

### 2.1 The Split Layout

1. **Left Pane (The Chat Interface):**
   - Takes up ~60% of the screen width on desktop.
   - A scrollable message history.
   - An input dock fixed at the bottom with standard text input, image upload button, and a hold-to-talk audio recording button.
2. **Right Pane (The Pokédex Visor):**
   - Takes up ~40% of the screen width.
   - A sticky, highly stylized card that updates dynamically whenever the backend returns `context_used`.
   - Acts as the visual "database readout" complementing the LLM's conversational text.

### 2.2 Design Aesthetics

- **Theme:** "Modern Retro" — glassmorphism (semi-transparent overlays with background blur) combined with classic Pokémon Red accents (`#ee1515`).
- **Typography:** Use a modern sans-serif font like `Inter` or `Outfit` from Google Fonts.
- **Animations:** 
  - Messages should slide up and fade in.
  - The Pokédex Visor should have a subtle "data loading" scanline effect or pulse when updating.
  - Hover states on buttons must feel responsive (scale up slightly, glow).

---

## 3. Component Architecture

Structure the `src/` directory logically:

```text
src/
├── assets/             # Global CSS, static images
├── components/
│   ├── layout/         # AppContainer, SplitPane
│   ├── chat/           # ChatWindow, MessageBubble, InputDock
│   ├── visor/          # PokedexVisor, StatRadar, TypeBadge, EvoChain
│   └── shared/         # LoadingSpinner, IconButton
├── hooks/              # Custom hooks (e.g., useAudioRecorder, usePokedexAPI)
├── services/           # Axios API configuration
└── App.jsx             # Main orchestrator
```

### 3.1 Core Components Breakdown

#### `InputDock.jsx`
The most complex interactive component. It needs:
- A text `<input>` or `<textarea>`.
- A hidden `<input type="file" accept="image/png, image/jpeg" />` triggered by a camera icon button.
- An audio recording button (microphone icon). Use the native browser `MediaRecorder` API to capture audio chunks and compile them into an `.ogg` or `.webm` Blob to send to the backend.

#### `ChatWindow.jsx`
- Maps over a `messages` array in state.
- Distinct styles for user messages vs. AI responses.
- Render AI responses using `react-markdown` as Gemini often returns bold text, lists, or code blocks.

#### `PokedexVisor.jsx`
- A visually distinct panel that renders the `context_used` JSON from the backend.
- **Header:** Pokémon name (capitalized) and National Dex ID.
- **Hero Image:** Display the `sprite_url`. Give it a subtle glowing backdrop based on its primary type (e.g., red glow for Fire).
- **Types Section:** Render distinct colored pills for each type (e.g., Grass is green, Poison is purple).
- **Stats Section:** Render a bar chart or a small radar chart for HP, Atk, Def, SpA, SpD, Spe.
- **Relationships:** Show "Strong Against" and "Weak Against" based on the graph traversal data returned from the backend.

---

## 4. State Management & Data Flow

Since the app is relatively simple, React's built-in `useState` and `useRef` are sufficient at the top level (`App.jsx`), passing data down via props.

### 4.1 Application State

```javascript
const [messages, setMessages] = useState([]); // { role: 'user' | 'ai', content: str, type: 'text'|'audio'|'image', mediaUrl?: str }
const [isTyping, setIsTyping] = useState(false); // For loading state
const [activeVisorData, setActiveVisorData] = useState(null); // The latest context_used object
```

### 4.2 Handling API Requests

Create a service function to handle the `multipart/form-data` payload cleanly:

```javascript
// src/services/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000'
});

export const sendMultimodalQuery = async ({ text, imageFile, audioBlob }) => {
  const formData = new FormData();
  
  if (text) formData.append('text', text);
  if (imageFile) formData.append('image', imageFile);
  if (audioBlob) formData.append('audio', audioBlob, 'recording.ogg');

  const response = await api.post('/api/v1/query', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  
  return response.data; // { response: string, context_used: object, modality_routed: string }
};
```

---

## 5. Handling Multi-Modal Inputs

### 5.1 Image Upload Preview
When a user selects an image, immediately display a preview in the chat log (as a "User" message) and then fire the API request. You can create a temporary preview URL using `URL.createObjectURL(file)`.

### 5.2 Audio Recording (The `useAudioRecorder` hook)
To truly impress, don't just ask the user to upload an audio file. Build an in-browser recorder:
1. Request microphone permissions via `navigator.mediaDevices.getUserMedia({ audio: true })`.
2. Initialize a `MediaRecorder`.
3. When the user holds the mic button, start recording.
4. When released, stop recording, compile the Blob, display an "Audio Message" bubble in the chat, and fire the API request.

---

## 6. Error Handling & Edge Cases

| Scenario | UX Handling |
|---|---|
| Backend is down | Show a clear error message in the chat: "Connection to the Pokédex network failed." |
| No context returned | If `context_used` is null (e.g., general chit-chat), gracefully hide or fade out the Visor pane. |
| Large Image Upload | Client-side validation: if file > 5MB, show a toast error and block upload. |
| Audio Denied | If microphone permissions are denied, disable the mic button and show a tooltip explaining why. |

---

## 7. Deliverables Checklist

When Phase 3 is complete, the following must be true:

- [ ] `frontend/` project initialized with Vite and React.
- [ ] Split-pane layout implemented and responsive (stacks vertically on mobile screens).
- [ ] Premium CSS styling applied (glassmorphism, vibrant colors, custom typography).
- [ ] Text input successfully sends requests to the backend and renders the markdown response.
- [ ] Image upload functional, displaying a preview in the chat and correctly appending to `FormData`.
- [ ] In-browser audio recording implemented and successfully routing to the backend.
- [ ] "Pokédex Visor" card dynamically updates and correctly maps properties (sprite, types, stats, graph relationships) from the `context_used` payload.
- [ ] Loading states (spinners or typing indicators) are present while waiting for the FastAPI backend.
- [ ] Clean error handling for network issues or bad inputs.
