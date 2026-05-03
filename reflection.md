# PawPal+ Project Reflection

## 1. System Design

**Core User Actions:**
1. **Profile Management**: Entering and storing basic owner and pet profiles.
2. **Task Entry & Customization**: Adding or editing pet care tasks with specific durations, categories, and priority levels.
3. **Daily Plan Generation**: Producing an optimized daily schedule that respects time constraints and priorities.

**a. Initial design**

My initial design uses a modular, object-oriented approach with four primary classes:
* **Task (Dataclass)**: The base unit of data, holding description, time, duration, priority, and category.
* **Pet (Dataclass)**: A container for specific animal info and a list of its assigned tasks.
* **Owner**: Manages the high-level profile and coordinates multiple Pet objects.
* **Scheduler**: The logic engine that processes the Owner's tasks to handle sorting and conflict detection.

**b. Design changes**

Based on the AI architectural review, I made two key refinements to the design:
1. **Time Parsing**: `Task.time` stores time as a string (e.g., `"09:00"`). A `_parse_time()` helper converts it to a `datetime` object only when needed for arithmetic comparisons in conflict detection and sorting — keeping the data model simple while still supporting robust comparisons.
2. **Task Context**: Added a `pet_name` field to the `Task` dataclass so that the Scheduler can identify which pet a task belongs to when tasks are flattened into a single list.
3. **Display-Time Adjustment**: Added a conflict-free display plan that shifts lower-ranked overlapping tasks later without silently changing the original stored task time.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers four primary constraints in a hierarchical sort:
* **Completion Status**: Completed tasks are automatically pushed to the bottom of the list to keep the "To-Do" items front and center.
* **Priority (1-3)**: Among pending tasks, high-priority items (Priority 1) are moved to the top.
* **Category**: Health tasks rank above Food, Food above Exercise, and Exercise above Other.
* **Time**: Tasks with the same priority and category are sorted chronologically.

I decided that **Completion Status** was the most important constraint for user experience, as it prevents a cluttered "finished" list from burying urgent, upcoming tasks.

**b. Tradeoffs**

A key tradeoff in this design is the **"Exact Overlap"** detection. The scheduler flags a conflict if one task starts before another ends and creates a conflict-free display plan by shifting lower-ranked overlapping tasks later. It does *not* account for "buffer time" or travel time between tasks.

This is reasonable for a domestic pet care scenario where most tasks (feeding, meds) happen in the same location. Adding complex buffer logic would have increased the system's complexity without providing significant value for a single-home user.

---

## 3. AI Collaboration

**a. How you used AI**

I used AI as a "Co-Architect" throughout the project:
* **Design Brainstorming**: Using Claude to refine the initial class structures and identify data bottlenecks.
* **Refactoring**: Leveraging AI to design the `_parse_time()` helper that converts string times to `datetime` objects for arithmetic comparisons, keeping the data model simple while supporting robust conflict detection.
* **Logic Implementation**: Providing high-level pseudo-code prompts to have the AI "flesh out" method bodies for the Scheduler and recurring task logic.

**b. Judgment and verification**

During the Phase 1 review, the AI suggested using a dedicated `Conflict` dataclass instead of raw tuples for the conflict detection output. After evaluating the tradeoff, I kept raw tuples — the UI destructures the pair with a single `for _a, _b in _conflicts:` loop, which is readable enough without the overhead of an additional class. The simpler approach was the right call for a two-field result.

---

## 4. Testing and Verification

**a. What you tested**

I implemented a suite of 45 automated tests using `pytest` covering:
* **State Management**: Ensuring `mark_complete()` toggles correctly and clones recurring tasks.
* **Logic Integrity**: Verifying that `add_task()` correctly stamps the pet's name onto the task.
* **Boundary Conditions**: Testing sequential tasks (one ending exactly when another starts) to ensure they do *not* trigger a false conflict.
* **Scheduler Reliability**: Verifying priority/category sorting, invalid time handling, and conflict-free display-time adjustment.
* **AI Guardrails**: Testing Mistral JSON parsing, extra-key filtering, invalid JSON fallback, priority/category normalization, and invalid AI time rejection.

**b. Confidence**

I am highly confident in the core scheduler logic because the automated test suite passes 100% of the time and covers both backend scheduling behavior and the Streamlit display path.

If I had more time, I would test **cross-day scheduling** (e.g., a task starting at 11:30 PM and ending at 12:30 AM) and **timezone transitions**, which are common edge cases for mobile users who travel with their pets.

---

## 5. Reflection

**a. What went well**

I am most satisfied with the **Recurring Task Logic**. Being able to mark a "Daily Feed" as complete and having the system automatically generate a fresh, pending version for the next day makes the app feel proactive rather than just a passive list.

**b. What you would improve**

If I had another iteration, I would redesign the **Task Storage**. Currently, everything lives in memory via `st.session_state`. Integrating a local SQLite database would allow users to close their browser without losing their entire pet history.

**c. Key takeaway**

The most important thing I learned is the value of **"CLI-First" development**. By building and testing the core logic in a simple terminal environment before touching the Streamlit UI, I avoided hours of debugging browser-refresh issues and could focus entirely on the "brain" of the application.

---

## 6. AI Feature — Smart Scheduling

**a. What was implemented**

The final extension to the project is a Smart Scheduling feature powered by `PawPalAgent` in `agent.py`. The agent sends the user's plain-English text to Mistral (`mistral-small-latest`) with a constrained system prompt and JSON mode so the response can be parsed into `{pet_name, task_description, time, priority, category}` and wired directly into the existing scheduler backend.

**b. Helpful AI behavior**

The most effective design decision was the **constrained JSON extraction prompt**. By explicitly forbidding markdown, explanations, and extra keys, the model reliably returns machine-parseable output on the first call, avoiding the need for a more complex parsing pipeline.

**c. Flawed / limited AI behavior**

The model can produce imperfect output: task descriptions that are vague, pet names that are paraphrased (breaking the lookup match), or invalid time/category/priority values. Guardrails normalize priority and category, reject invalid AI times before task creation, and let the scheduler handle conflicts after a task is submitted.

**d. Future improvement**

The most impactful next step would be to extend the extraction prompt to infer `duration` and `frequency`, or to add a confirmation step that lets the user review and adjust parsed values before the task is committed.
