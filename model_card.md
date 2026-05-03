# Model Card - PawPal+ AI Scheduling Agent

---

## Model Overview

| Field | Value |
|---|---|
| Model name | Mistral Small Latest |
| Model ID | `mistral-small-latest` |
| Provider | Mistral AI |
| Library | `mistralai` |
| Access method | `client.chat.complete()` |
| Purpose | Natural-language scheduling extraction |

---

## What the Agent Does

`PawPalAgent` in `agent.py` accepts a free-text pet care scheduling request and returns a Python dictionary with exactly five scheduling fields:

| Output key | Type | Example |
|---|---|---|
| `pet_name` | string | `"Buddy"` |
| `task_description` | string | `"Walk"` |
| `time` | string in HH:MM 24-hour format | `"17:00"` |
| `priority` | integer from 1 to 3 | `1` |
| `category` | one of `Exercise`, `Food`, `Health`, `Other` | `"Exercise"` |

`app.py` uses the dictionary to locate the matching pet, create a `Task`, and add that task through `Pet.add_task()`.

---

## Input / Output Format

Example input:

```text
Walk Buddy at 5 PM
```

Expected model output:

```json
{"pet_name": "Buddy", "task_description": "Walk", "time": "17:00", "priority": 2, "category": "Exercise"}
```

---

## Prompt Behavior

The agent sends a system message instructing the model to act as a pet care scheduling assistant and return only a valid JSON object with:

* `pet_name`
* `task_description`
* `time`
* `priority`
* `category`

The call also enables Mistral JSON mode:

```python
response_format={"type": "json_object"}
```

Priority is mapped as `1 = high/urgent/super important/medicine/critical`, `2 = normal/default/medium`, and `3 = low/not urgent/optional`.

Category is normalized using these keyword groups:

| Category | Keywords |
|---|---|
| Health | medicine, medication, pill, vet, vaccine, flu shot, bath, grooming, clean, shower |
| Food | feed, food, meal, breakfast, lunch, dinner, water |
| Exercise | walk, run, exercise, play, training |
| Other | fallback |

The code still normalizes the parsed result so only the five allowed keys are returned, even if the model includes extra fields.

---

## Response Parsing Logic

1. The raw response content is read from `response.choices[0].message.content`.
2. Leading and trailing whitespace are stripped.
3. Markdown code fences are removed if present.
4. The cleaned string is parsed with `json.loads()`.
5. The final result is normalized to exactly five keys.
6. If parsing fails, the agent returns:

```python
{"pet_name": "", "task_description": "", "time": "", "priority": 2, "category": "Other"}
```

API and network errors are not swallowed inside the agent. They propagate to `app.py`, where the Streamlit UI shows an error message and logs the exception.

---

## Intended Use

| Use case                                           | Supported |
| -------------------------------------------------- | --------- |
| Parsing simple natural-language pet care reminders | Yes       |
| Converting common time phrases into 24-hour time   | Yes       |
| Replacing the manual task form for quick entry     | Yes       |
| Multi-turn planning                                | No        |
| Persistent memory                                  | No        |
| Veterinary or medical advice                       | No        |

This model use is intended only as a convenience layer for a lab prototype pet scheduling app.

---

## Reliability Testing

The project includes automated tests for both the scheduler and the AI guardrails.

Current result:

```text
45 passed
```

AI-specific reliability checks include:

| Test                | Purpose                                                               | Result |
| ------------------- | --------------------------------------------------------------------- | ------ |
| Valid JSON response | Confirms normal model output is parsed correctly                      | Passed |
| Priority handling   | Confirms priority values are normalized to integers from 1 to 3       | Passed |
| Category handling   | Confirms category values are normalized or inferred from task wording | Passed |
| Invalid time handling | Confirms invalid AI times are rejected before task creation         | Passed |
| Conflict-free display scheduling | Confirms lower-ranked overlapping same-pet tasks are shifted later | Passed |
| Extra model keys    | Confirms only `pet_name`, `task_description`, `time`, `priority`, and `category` are returned | Passed |
| Invalid JSON        | Confirms malformed model output returns safe empty fallback fields    | Passed |

A live Mistral smoke test also verified these examples:

| Input                          | Output                                                                      |
| ------------------------------ | --------------------------------------------------------------------------- |
| `Walk Buddy at 5 PM`           | `{"pet_name": "Buddy", "task_description": "Walk", "time": "17:00", "priority": 2, "category": "Exercise"}` |
| `Feed Luna at noon`            | `{"pet_name": "Luna", "task_description": "Feed", "time": "12:00", "priority": 2, "category": "Food"}` |
| `Give Max medicine at 8:30 AM` | `{"pet_name": "Max", "task_description": "Give medicine", "time": "08:30", "priority": 1, "category": "Health"}` |

The Streamlit app was also tested end-to-end for successful AI task creation, missing-pet warnings, conflict detection after AI-added overlapping tasks, and conflict-free display-time adjustment.

---

## Guardrails and Error Handling

| Guardrail         | Behavior                                                                                          |
| ----------------- | ------------------------------------------------------------------------------------------------- |
| Missing API key   | Raises a clear setup error                                                                        |
| Invalid JSON      | Returns empty fields instead of crashing                                                          |
| Extra model keys  | Filters output to only the five allowed fields                                                    |
| Invalid priority  | Defaults to priority `2`                                                                          |
| Invalid category  | Infers from task wording or falls back to `Other`                                                  |
| Invalid time      | App warns the user and does not add a task                                                        |
| Missing pet       | App warns the user and does not add a task                                                        |
| API/network error | App displays an error and logs the exception                                                      |
| Logs              | AI parse success, missing-pet warnings, task creation, and exceptions are written to `pawpal.log` |

---

## Limitations and Biases

* The model extracts only `pet_name`, `task_description`, `time`, `priority`, and `category`.
* It does not extract duration or recurrence.
* It does not know which pets already exist until `app.py` checks the parsed pet name.
* It does not see the full schedule before submitting a task, so conflict detection and display-time adjustment happen after task creation.
* It may misunderstand uncommon pet names, ambiguous wording, or AM/PM phrasing.
* It may perform better on simple English scheduling commands than on slang, multilingual input, or complex instructions.
* No large quantitative accuracy benchmark was created.

---

## Risks and Misuse Prevention

| Risk                               | Severity | Mitigation                                                       |
| ---------------------------------- | -------- | ---------------------------------------------------------------- |
| Wrong pet, task, or time extracted | Low      | User sees the resulting task and can manually correct it         |
| Missing pet name                   | Low      | App warns instead of adding a task                               |
| Invalid model output               | Low      | Agent returns empty fallback fields                              |
| Invalid time                       | Low      | App rejects it before task creation                              |
| API key exposure                   | Medium   | `.env` is ignored by git                                         |
| Over-reliance on AI output         | Low      | Manual task entry remains available                              |
| Veterinary misuse                  | Medium   | App is limited to scheduling and does not provide medical advice |

This system should not be used for medical, veterinary, emergency, or safety-critical decisions.

---

## Out-of-Scope Use

* Medical, veterinary, or safety-critical advice
* Autonomous multi-step planning
* Retrieval-augmented question answering
* Fine-tuning
* Persistent user profiling or memory
* Replacing professional care instructions

---

## AI Collaboration Reflection

AI assistance was used to plan the project structure, improve the scheduling logic, design tests, and refine the Mistral JSON extraction workflow.

One helpful AI suggestion was to keep the model output constrained to a small JSON object. This made the feature easier to test and safer to connect to the Streamlit app.

One flawed or incomplete AI suggestion was treating the project as if it had a broader agentic workflow. In practice, the system only needed single-step structured extraction, so the design was narrowed to a simpler and more reliable Mistral parsing agent.

---

Built for AI110.
