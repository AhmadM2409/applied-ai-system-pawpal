# Model Card — PawPal+ AI Scheduling Agent

---

## Model Overview

| Field | Value |
|---|---|
| Model name | Gemini 2.5 Flash |
| Model ID | `gemini-2.5-flash` |
| Provider | Google |
| Library | `google-generativeai` (Python, v0.8.6+) |
| Access method | `genai.GenerativeModel.generate_content()` |
| Role in system | Natural-language task parser |

---

## What the Agent Does

`PawPalAgent` (defined in `agent.py`) accepts a free-text scheduling request from the user and returns a structured Python dictionary containing exactly three fields:

| Output key | Type | Example |
|---|---|---|
| `pet_name` | string | `"Buddy"` |
| `task_description` | string | `"Evening walk"` |
| `time` | string (HH:MM, 24-hour) | `"17:00"` |

The dictionary is then used by `app.py` to locate the matching pet and automatically add a `Task` to their schedule — eliminating the need to fill out the manual task form.

---

## System Prompt

The agent uses a single, fixed system prompt prepended to every user request:

> *"You are a smart pet care assistant. When given a user's message, extract scheduling information and return ONLY a valid JSON string with exactly these keys: `pet_name`, `task_description`, and `time` (in HH:MM 24-hour format). If a piece of information is missing, guess logically based on context or leave it as an empty string. Do not include any explanation, markdown, or extra text — only the raw JSON string."*

**Design intent:** The prompt constrains the model to produce machine-parseable output only. No conversational preamble, no markdown fences, no explanation — just the raw JSON object. This avoids the need for a complex parser and keeps the integration surface minimal.

The system prompt and user message are concatenated into a single string before being passed to `generate_content()`, because `google-generativeai` does not expose a dedicated `system` parameter at the `GenerativeModel` level.

---

## Response Processing

1. The raw response text is stripped of leading and trailing whitespace.
2. Two regular expressions remove markdown code fences if present (```` ```json ```` or ```` ``` ````).
3. The cleaned string is passed to `json.loads()`.
4. On any exception (parse error, network error, unexpected model output), the method returns a safe fallback dictionary:
   ```python
   {"pet_name": "Unknown", "task_description": "Unknown task", "time": "12:00"}
   ```

---

## Intended Use

| Use case | Supported |
|---|---|
| Parsing simple natural-language pet care reminders | Yes |
| Inferring reasonable defaults for missing fields | Yes (model's best-guess) |
| Replacing the manual task form for quick entry | Yes |
| Multi-turn conversation or follow-up questions | No |
| Persistent memory across browser sessions | No |
| Medical or veterinary advice | No |

This agent is a convenience layer for a single-user domestic pet scheduling app. It is a lab prototype and is not designed for clinical, commercial, or safety-critical use.

---

## Limitations

### Parsing reliability
The model is instructed to return only raw JSON, but it may occasionally wrap output in markdown fences or include a brief preamble. The fence-stripping logic handles common cases; however, unexpected output formats will trigger the fallback and result in an "Unknown" task being created rather than an error.

### Fallback silently adds a task
When parsing fails, the fallback dictionary (`pet_name: "Unknown"`, `time: "12:00"`) is returned and `app.py` will attempt to find a pet named "Unknown." If no such pet exists, the UI shows a warning. If a pet happens to be named "Unknown," a task will be added silently with incorrect data.

### Case-sensitive pet name matching
`app.py` matches the returned `pet_name` to existing pets using a case-insensitive comparison (`.lower()`). However, the model may abbreviate, misspell, or paraphrase the pet name (e.g., "Buddy Boy" instead of "Buddy"), causing a no-match warning even when the intent is clear.

### No context about existing pets or tasks
The model receives only the user's single text request. It has no knowledge of which pets are registered in the system, what tasks already exist, or whether a time slot is already occupied. It cannot warn the user about conflicts before a task is added.

### No persistent storage
All data (pets, tasks, and AI-generated tasks) lives in `st.session_state`. Closing or refreshing the browser destroys all data. The AI agent does not have its own memory between requests.

### API key required
The agent requires a valid `GEMINI_API_KEY` in a `.env` file. If the key is missing, invalid, or the quota is exceeded, the agent raises an exception at instantiation time and the Smart Scheduling section will fail at runtime.

### Rate limits and latency
Each Smart Scheduling request makes a live API call to Google's Gemini service. Response time depends on network conditions and API availability. The current implementation does not cache results or retry on transient failures.

---

## Risks

| Risk | Severity | Notes |
|---|---|---|
| Incorrect field extraction (wrong pet, time, or task) | Low | User can verify before submitting manually |
| Fallback task silently added to wrong pet | Medium | Only occurs if a pet named "Unknown" exists |
| API key exposed in `.env` | Medium | `.env` must be in `.gitignore`; never commit it |
| Model generates plausible but wrong time (e.g., AM/PM swap) | Low | User sees the result in the success message |
| Quota exhaustion during a demo | Low | Free tier limits apply; no retry logic |

---

## Out of Scope

- This model card does not cover the core scheduling logic in `pawpal_system.py` (pure Python, no ML).
- No fine-tuning, prompt optimization, or evaluation dataset was produced for this integration.
- No bias or fairness evaluation has been conducted; the task domain (domestic pet care scheduling) is considered low-risk.

---

*Built for AI110 — Module 2 Lab Assignment*
