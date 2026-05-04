# PawPal+ - Smart Pet Care Scheduler

PawPal+ is an intelligent daily planner for pet owners. Add pets, assign care tasks with priorities and schedules, detect conflicts, and use AI Smart Scheduling to turn natural-language reminders into scheduled tasks.

---

## Base Project

This project extends the **AI110 Module 2 Streamlit pet scheduler starter shell**. The starter provided the app shell; PawPal+ adds backend scheduling logic, a complete Streamlit workflow, automated tests, and an AI Smart Scheduling layer.

Implemented additions include:

- Core scheduling system in `pawpal_system.py`: `Task`, `Pet`, `Owner`, and `Scheduler`
- Streamlit UI for pets, tasks, conflict banners, and schedule generation
- AI Smart Scheduling in `agent.py` using Mistral for natural-language task entry
- A 45-test automated test suite in `tests/test_pawpal.py`
- Documentation in `README.md`, `model_card.md`, and `reflection.md`

---

## Project Summary

PawPal+ manages pet care tasks, schedules them by completion state, priority, category, and time, detects overlapping tasks for the same pet, and allows natural-language scheduling through AI.

---

## Key Features

### Smart Sorting and Conflict-Aware Scheduling

The scheduler orders the day using:

1. Completion status: pending tasks appear before completed ones
2. Priority: high-priority tasks appear first
3. Category importance: Health, Food, Exercise, then Other
4. Time: tasks with the same priority and category are sorted chronologically

After sorting, PawPal+ creates a conflict-free display plan per pet. If a lower-ranked task overlaps a higher-ranked task, the displayed start time is shifted to begin when the higher-ranked task ends. The original stored task time is not silently mutated.

Example:

| Task | Original Time | Duration | Priority | Category | Displayed Time |
|---|---:|---:|---:|---|---:|
| Get flu shot | 13:00 | 20 min | 1 | Health | 13:00 |
| Run | 13:00 | 20 min | 2 | Exercise | 13:20 |

### Conflict Detection

The scheduler scans each pet's tasks for overlaps using start time plus duration. Conflicts are shown as warnings at the top of the dashboard.

### Recurring Task Cloning

Tasks can be marked `Once`, `Daily`, or `Weekly`. When a recurring task is completed, the system creates the next pending copy automatically.

### Pending / Completed Toggle

A sidebar control switches the dashboard between pending and completed task views.

### Smart Scheduling (AI)

`PawPalAgent` lets owners type scheduling requests in plain English, such as `Walk Buddy at 5 PM`.

The agent sends the request to Mistral (`mistral-small-latest`) with a strict JSON-extraction prompt. Mistral returns a JSON object with:

| Field | Example |
|---|---|
| `pet_name` | `"Buddy"` |
| `task_description` | `"Walk"` |
| `time` | `"17:00"` |
| `priority` | `1` |
| `category` | `"Exercise"` |

`app.py` uses those fields to find the matching pet, create a `Task` with the parsed priority/category and default duration/frequency values, and add it through the existing scheduler path. If the pet is not found, the app shows a warning asking the user to add the pet first.

Priority is mapped as `1 = high/urgent/super important/medicine/critical`, `2 = normal/default/medium`, and `3 = low/not urgent/optional`.

Category is normalized using these keyword groups:

| Category | Keywords |
|---|---|
| Health | medicine, medication, pill, vet, vaccine, flu shot, bath, grooming, clean, shower |
| Food | feed, food, meal, breakfast, lunch, dinner, water |
| Exercise | walk, run, exercise, play, training |
| Other | fallback |

### Rejected AI Approaches

**RAG** was not used because PawPal+ does not have an external document corpus or knowledge base to retrieve from.

**A full agentic workflow** was not used because the task only needs single-step structured extraction from user text into scheduler fields.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| UI Framework | Streamlit |
| Testing | pytest |
| Core Logic | Python `dataclasses`, `datetime`, `timedelta` |
| AI Agent | Mistral AI - `mistral-small-latest` via `mistralai` |

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

```env
MISTRAL_API_KEY=your_api_key_here
```

The `.env` file is listed in `.gitignore`; never commit your API key.

**5. Run the app**

```bash
streamlit run app.py
```

---

## Testing

Run the automated test suite:

```bash
python -m pytest tests/ -v
```

---

## Reliability & Evaluation

The project includes automated tests for both the core scheduler logic and the AI Smart Scheduling guardrails.

Current test result:

```text
45 passed in 1.93s
```

Test coverage includes:

* Task completion behavior
* Recurring daily task cloning
* Pet task assignment
* Same-pet conflict detection
* Cross-pet conflict avoidance
* Sequential non-overlapping task handling
* Conflict-free display-time adjustment
* Scheduler ordering by priority, category, and time
* Mistral JSON parsing
* Priority normalization from model output and user wording
* Category normalization and keyword inference
* AI time validation
* Extra-key filtering from model output
* Invalid JSON fallback behavior

### AI Smart Scheduling Evaluation

The Mistral agent was tested with mocked model responses to verify that the app remains safe even when model output varies.

| Scenario | Expected Behavior | Result |
| --- | --- | --- |
| Valid JSON response | Extract `pet_name`, `task_description`, `time`, `priority`, and `category` | Passed |
| Priority/category normalization | Convert and infer safe priority/category values | Passed |
| Extra model keys | Ignore extra keys and return only the five allowed fields | Passed |
| Invalid JSON | Return empty fallback fields instead of crashing | Passed |

A live smoke test also confirmed the real Mistral API can parse natural-language scheduling requests:

| Input | Output |
| --- | --- |
| `Walk Buddy at 5 PM` | `{"pet_name": "Buddy", "task_description": "Walk", "time": "17:00", "priority": 2, "category": "Exercise"}` |
| `Feed Luna at noon` | `{"pet_name": "Luna", "task_description": "Feed", "time": "12:00", "priority": 2, "category": "Food"}` |
| `Give Max medicine at 8:30 AM` | `{"pet_name": "Max", "task_description": "Give medicine", "time": "08:30", "priority": 1, "category": "Health"}` |

The Streamlit app was also tested end-to-end with:

* successful AI task creation
* missing-pet warning
* conflict warning after AI-added overlapping tasks
* conflict-free display adjustment for overlapping same-pet tasks

---

## Demo

**Example 1 - AI adds a task successfully**

1. Add pet: `Buddy`, `Dog`
2. Smart Scheduling input: `Walk Buddy at 5 PM`
3. Expected: task added to Buddy around `17:00`, priority `2`, category `Exercise`

**Example 2 - Pet not found warning**

1. Smart Scheduling input: `Feed Luna at noon`
2. Expected: warning because Luna has not been added

**Example 3 - Conflict-aware scheduling**

1. With Buddy registered and a 5 PM task already added, enter: `Give Buddy medication at 5:10 PM`
2. Expected: task added with priority `1` and category `Health`; overlapping lower-ranked display times are shifted later in the task table

---

## Project Structure

```text
applied-ai-system-project/
├── app.py
├── pawpal_system.py
├── agent.py
├── requirements.txt
├── README.md
├── model_card.md
├── reflection.md
├── assets/
│   └── architecture.md
└── tests/
    └── test_pawpal.py
```

---

## Architecture & Data Flow

A Mermaid system architecture diagram is included at [`assets/architecture.md`](assets/architecture.md).

```text
Manual form -> Task -> Pet.add_task() -> Scheduler

User text -> PawPalAgent -> Mistral -> JSON dict
          -> Task -> Pet.add_task() -> Scheduler
```

Scheduler operations:

```text
Scheduler.generate_daily_plan()       -> sorted conflict-free display plan
Scheduler.get_tasks_for_view()        -> filtered sorted conflict-free display plan
Scheduler.detect_conflicts()          -> interval overlap, grouped per pet
```

Data model:

```text
Owner
└── Pet
    └── Task
```

---

## Limitations

- AI extracts only `pet_name`, `task_description`, `time`, `priority`, and `category`.
- `duration` and `frequency` use defaults unless manually entered.
- There is no persistent storage; data lives in `st.session_state`.
- AI has no schedule awareness before task submission.
- Pet name matching is simple case-insensitive matching.
- PawPal+ is for scheduling only and does not provide medical or veterinary advice.
- There is no quantitative AI accuracy benchmark.

---

## Design Tradeoffs

Conflict detection uses exact overlap: a task is flagged if it starts before another task ends. The display plan then shifts lower-ranked overlapping tasks later for the same pet. Buffer time is not modeled because this prototype focuses on same-home pet care tasks.

In-memory storage via `st.session_state` is appropriate for a lab prototype, but a production version would need persistent storage such as SQLite.

---

Video Demo: https://drive.google.com/file/d/1vx7MblUcL9BFpkV_83N1N7fKPXWsnbEk/view?usp=sharing
