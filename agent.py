import json
import os

from dotenv import load_dotenv
from mistralai.client import Mistral


SYSTEM_PROMPT = """
You are a smart pet care scheduling assistant.

Extract exactly five fields from the user's message:
- pet_name
- task_description
- time
- priority
- category

Return only a valid JSON object.
Do not include markdown.
Do not include explanations.
Do not include extra keys.

The time must be in 24-hour HH:MM format.
The priority must be an integer:
- 1 for urgent, very important, super important, high priority, medication, medicine, emergency, or critical tasks
- 2 for normal/default/medium priority
- 3 for low priority, not urgent, whenever, or optional tasks

The category must be one of: Exercise, Food, Health, Other.
- Exercise for walk, run, exercise, play, training
- Food for feed, food, meal, breakfast, lunch, dinner, water
- Health for medicine, medication, pill, vet, vaccine, vaccination, flu shot, bath, grooming, clean, shower
- Other when no category fits

Example:
User: Walk Buddy at 5 PM
Output: {"pet_name": "Buddy", "task_description": "Walk", "time": "17:00", "priority": 2, "category": "Exercise"}
"""


EMPTY_RESULT = {
    "pet_name": "",
    "task_description": "",
    "time": "",
    "priority": 2,
    "category": "Other",
}


HIGH_PRIORITY_TERMS = (
    "urgent",
    "very important",
    "super important",
    "high priority",
    "medication",
    "medicine",
    "emergency",
    "critical",
)

LOW_PRIORITY_TERMS = (
    "low priority",
    "not urgent",
    "whenever",
    "optional",
)

ALLOWED_CATEGORIES = ("Exercise", "Food", "Health", "Other")

CATEGORY_KEYWORDS = {
    "Exercise": ("walk", "run", "exercise", "play", "training"),
    "Food": ("feed", "food", "meal", "breakfast", "lunch", "dinner", "water"),
    "Health": (
        "medicine",
        "medication",
        "pill",
        "vet",
        "vaccine",
        "vaccination",
        "flu shot",
        "bath",
        "grooming",
        "clean",
        "shower",
    ),
}


def _priority_from_text(text: str) -> int | None:
    lowered = text.lower()
    if any(term in lowered for term in LOW_PRIORITY_TERMS):
        return 3
    if any(term in lowered for term in HIGH_PRIORITY_TERMS):
        return 1
    return None


def _normalize_priority(value, user_message: str, task_description: str) -> int:
    text_priority = _priority_from_text(f"{user_message} {task_description}")
    if text_priority is not None:
        return text_priority

    try:
        priority = int(value)
    except (TypeError, ValueError):
        return 2

    return priority if priority in (1, 2, 3) else 2


def _infer_category_from_text(text: str) -> str:
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "Other"


def _normalize_category(value, user_message: str, task_description: str) -> str:
    inferred = _infer_category_from_text(f"{task_description} {user_message}")
    if inferred != "Other":
        return inferred

    cleaned = str(value or "").strip().lower()
    for category in ALLOWED_CATEGORIES:
        if cleaned == category.lower():
            return category
    return "Other"


class PawPalAgent:
    def __init__(self, model: str = "mistral-small-latest"):
        load_dotenv()

        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY is missing. Add it to your .env file.")

        self.client = Mistral(api_key=api_key)
        self.model = model

    def parse_schedule_request(self, user_message: str) -> dict:
        response = self.client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content.strip()

        if raw_content.startswith("```"):
            raw_content = raw_content.replace("```json", "").replace("```", "").strip()

        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError:
            return EMPTY_RESULT.copy()

        return {
            "pet_name": str(parsed.get("pet_name", "")).strip(),
            "task_description": str(parsed.get("task_description", "")).strip(),
            "time": str(parsed.get("time", "")).strip(),
            "priority": _normalize_priority(
                parsed.get("priority"),
                user_message,
                str(parsed.get("task_description", "")),
            ),
            "category": _normalize_category(
                parsed.get("category"),
                user_message,
                str(parsed.get("task_description", "")),
            ),
        }

    def parse_user_request(self, user_text: str) -> dict:
        """
        Backward-compatible wrapper for older app.py code.
        Prefer parse_schedule_request() for new code.
        """
        return self.parse_schedule_request(user_text)
