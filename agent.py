import json
import os
import re

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = (
    "You are a smart pet care assistant. "
    "When given a user's message, extract scheduling information and return "
    "ONLY a valid JSON string with exactly these keys: "
    '"pet_name", "task_description", and "time" (in HH:MM 24-hour format). '
    "If a piece of information is missing, guess logically based on context "
    "or leave it as an empty string. "
    "Do not include any explanation, markdown, or extra text — only the raw JSON string."
)


class PawPalAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def parse_user_request(self, user_text: str) -> dict:
        prompt = f"{SYSTEM_PROMPT}\n\nUser request: {user_text}"

        try:
            response = self.model.generate_content(prompt)
            raw = response.text.strip()

            # Strip markdown code fences if present (e.g. ```json ... ```)
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            return json.loads(raw.strip())
        except Exception:
            return {
                "pet_name": "Unknown",
                "task_description": "Unknown task",
                "time": "12:00",
            }
