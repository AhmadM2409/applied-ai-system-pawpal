# PawPal+ — Smart Pet Care Scheduler

PawPal+ is an intelligent daily planner for pet owners. Add your pets, assign care tasks with priorities and schedules, and let the built-in scheduler build an optimized, conflict-free day — automatically rescheduling recurring tasks so nothing gets missed.

---

## Base Project

This project extends the **AI110 Module 2 Streamlit starter shell** provided as part of the lab assignment. The starter supplied a thin `app.py` with placeholder text describing what needed to be built. On top of that, this project implements:

- The complete backend scheduling system (`pawpal_system.py`) — `Task`, `Pet`, `Owner`, and `Scheduler` classes
- The full Streamlit UI with all forms, task views, conflict banners, and schedule generation
- An AI Smart Scheduling layer (`agent.py`) using Gemini 2.5 Flash for natural-language task entry
- A 10-test automated test suite (`tests/test_pawpal.py`)
- Full documentation (`model_card.md`, `reflection.md`, this README)

---

## Key Features

### Three-Key Smart Sorting
The scheduler orders your day using a three-level priority system:

1. **Completion status** — pending tasks always surface above completed ones
2. **Priority (1–3)** — high-priority items lead the list
3. **Chronological time** — ties broken by start time for a clean daily flow

### Conflict Detection
The scheduler scans every pet's task list for time overlaps using interval arithmetic (`start_time + duration`). Conflicts are flagged as persistent warnings at the top of the dashboard — visible at a glance without needing to generate a plan first.

### Recurring Task Cloning
Tasks can be marked `Once`, `Daily`, or `Weekly`. When a recurring task is completed, the system automatically clones it with the next scheduled date and re-adds it to the pet's list — keeping the schedule perpetually up to date without manual re-entry.

### Pending / Completed Toggle
A sidebar radio switch filters the entire dashboard — task tables, expander counts, and the generated plan — between **Pending** and **Completed** views instantly.

### Smart Scheduling (AI)
A natural-language input field powered by `PawPalAgent` lets owners type scheduling requests in plain English — for example, *"Walk Buddy at 5 PM"* or *"Give Luna her medication at 8 AM."*

The agent sends the request to `gemini-2.5-flash` with a strict JSON-extraction system prompt and extracts three fields:

| Field | Example |
|---|---|
| `pet_name` | `"Buddy"` |
| `task_description` | `"Evening walk"` |
| `time` | `"17:00"` |

The matching pet is located automatically and a task is added to their schedule — no manual form entry required. If the pet is not found, a warning is shown asking the user to add the pet first. See [`model_card.md`](model_card.md) for full agent documentation.

### Rejected AI Approaches

**RAG (Retrieval-Augmented Generation)** was not used. The system operates on user-supplied data entered at runtime. There is no external document corpus or knowledge base to retrieve from.

**Full agentic workflow** (multi-step reasoning loop with tool use) was not used. The scheduling task requires only a single structured extraction — the input maps directly to three fields. Adding a reasoning loop would introduce latency and complexity with no benefit to the user.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| UI Framework | Streamlit |
| Testing | pytest |
| Core Logic | Python `dataclasses`, `datetime`, `timedelta` |
| AI Agent | Google Generative AI — `gemini-2.5-flash` (`google-generativeai`) |

---

## Setup & Installation

**1. Clone the repository**
```bash
git clone https://github.com/AhmadM2409/applied-ai-system-project
cd applied-ai-system-project
```

**2. Create and activate a virtual environment**
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure your API key**

Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_api_key_here
```
The `.env` file is listed in `.gitignore` — never commit your API key.

**5. Run the app**
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## Testing

The automated test suite covers task completion, pet–task wiring, conflict detection, and boundary conditions (sequential tasks, cross-pet overlaps).

```bash
python -m pytest tests/ -v
```

Expected output:
```
10 passed in 0.03s
```

---

## Demo

**Example 1 — AI adds a task successfully**
1. Add a pet: name `Buddy`, species `Dog`
2. In the Smart Scheduling section, type: `Walk Buddy at 5 PM`
3. Expected: success message — *Task added to Buddy's schedule: 'Walk' at 17:00*

**Example 2 — Pet not found warning**
1. In the Smart Scheduling section, type: `Feed Luna at noon`
2. Expected: warning — *No pet named Luna found. Please add that pet first.*

**Example 3 — Conflict detection**
1. With Buddy registered and the 5 PM walk already added, type: `Give Buddy medication at 5:10 PM`
2. Expected: task added, then conflict banner fires at the top of the page — the new task overlaps with the walk still in progress

---

## Project Structure

```
applied-ai-system-project/
├── app.py               # Streamlit UI — all pages, forms, and AI scheduling section
├── pawpal_system.py     # Core logic — Task, Pet, Owner, Scheduler dataclasses
├── agent.py             # AI agent — natural-language task parsing via Gemini
├── requirements.txt     # All dependencies
├── README.md            # This file
├── model_card.md        # AI model documentation for the Gemini agent
├── reflection.md        # Design decisions, tradeoffs, and AI collaboration notes
└── tests/
    └── test_pawpal.py   # 10 pytest tests covering core backend logic
```

---

## Architecture & Data Flow

```
Manual entry path:
  User fills form → Task() → Pet.add_task() → Scheduler

AI Smart Scheduling path:
  User types text → PawPalAgent → Gemini 2.5 Flash
                 → JSON {pet_name, task_description, time}
                 → Task() with defaults → Pet.add_task() → Scheduler

Scheduler operations (both paths):
  Scheduler.generate_daily_plan()     →  sort by (is_completed, priority, time)
  Scheduler.detect_conflicts()        →  interval overlap, per-pet grouping

Data model:
  Owner
   └── Pet (1 or more)
        └── Task (1 or more)
             ├── mark_complete(pet)  →  clones self if Daily/Weekly
             └── pet_name            →  stamped by Pet.add_task()
```

---

## Limitations

- The AI agent extracts only `pet_name`, `task_description`, and `time`. Fields such as `duration`, `priority`, `category`, and `frequency` are not extracted and default to fixed values (20 min, priority 2, "Other", "Once").
- The AI has no awareness of the existing schedule before a task is submitted; it cannot warn about conflicts in advance.
- Pet name matching uses case-insensitive comparison, but the model may paraphrase or misspell the pet name, causing a no-match warning.
- All data is stored in `st.session_state`. Refreshing the browser clears all pets and tasks — there is no persistent storage.
- No quantitative accuracy benchmark exists for the AI extraction step.

---

## Design Tradeoffs

**Conflict detection uses exact overlap** — a task is flagged if it starts before another ends. Buffer time between tasks is not modelled, which is a deliberate simplification: for a single-home domestic scenario, travel time is negligible and the added complexity would not benefit the target user.

**In-memory storage via `st.session_state`** — appropriate for a lab prototype but would require SQLite or a similar persistence layer for a production app.

---

*Built for AI110 — Module 2 Lab Assignment*
