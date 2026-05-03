import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, date
from typing import List, Optional


def is_valid_time(time_text: str) -> bool:
    """Return True only for valid HH:MM 24-hour time strings."""
    if not isinstance(time_text, str):
        return False
    if not re.fullmatch(r"\d{2}:\d{2}", time_text):
        return False

    hour_text, minute_text = time_text.split(":")
    hour = int(hour_text)
    minute = int(minute_text)
    return 0 <= hour <= 23 and 0 <= minute <= 59


def _parse_time(time_str: str) -> datetime:
    """Parse a time string into a datetime object for arithmetic comparisons."""
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized time format: {time_str!r}")


def _priority_rank(priority) -> int:
    try:
        parsed = int(priority)
    except (TypeError, ValueError):
        return 2
    return parsed if parsed in (1, 2, 3) else 2


def _category_rank(category: str) -> int:
    ranks = {
        "health": 0,
        "food": 1,
        "exercise": 2,
        "other": 3,
    }
    return ranks.get(str(category or "").strip().lower(), 3)


def _time_rank(time_text: str) -> datetime:
    try:
        return _parse_time(time_text)
    except (TypeError, ValueError):
        return datetime.max


@dataclass
class Task:
    description: str
    time: str           # Expected format: "HH:MM" e.g. "09:00"
    duration: int       # In minutes
    priority: int       # 1 = highest, 3 = lowest
    category: str
    is_completed: bool = False
    pet_name: str = ""      # Stamped automatically by Pet.add_task()
    frequency: str = "Once" # "Once", "Daily", "Weekly"
    date: str = ""          # "YYYY-MM-DD"; empty means today

    def mark_complete(self, pet: Optional["Pet"] = None) -> None:
        """Mark this task done; if recurring, schedule the next occurrence on the pet."""
        self.is_completed = True
        if self.frequency in ("Daily", "Weekly") and pet is not None:
            base = date.fromisoformat(self.date) if self.date else date.today()
            delta = timedelta(days=1) if self.frequency == "Daily" else timedelta(weeks=1)
            next_task = replace(self, date=(base + delta).isoformat(), is_completed=False)
            pet.add_task(next_task)


@dataclass
class Pet:
    name: str
    species: str
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Stamp the task with this pet's name and append it to the task list."""
        task.pet_name = self.name
        self.tasks.append(task)


@dataclass
class Owner:
    name: str
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's roster."""
        self.pets.append(pet)

    def get_all_tasks(self) -> List[Task]:
        """Return a flat list of every task across all owned pets."""
        return [task for pet in self.pets for task in pet.tasks]


class Scheduler:

    def generate_daily_plan(self, owner: Owner, include_completed: bool = True) -> List[Task]:
        """Return the owner's tasks sorted; pass include_completed=False for a pending-only view."""
        tasks = owner.get_all_tasks()
        if not include_completed:
            tasks = self.filter_tasks(tasks, show_completed=False)
        return self.generate_conflict_free_plan(tasks)

    def sort_tasks_by_priority(self, tasks: List[Task]) -> List[Task]:
        """Sort by completion, priority, category importance, time, then description."""
        return sorted(
            tasks,
            key=lambda t: (
                1 if t.is_completed else 0,
                _priority_rank(t.priority),
                _category_rank(t.category),
                _time_rank(t.time),
                t.description.lower(),
            ),
        )

    def filter_tasks(self, tasks: List[Task], show_completed: bool = False) -> List[Task]:
        """Return only tasks whose completed status matches show_completed."""
        return [t for t in tasks if t.is_completed == show_completed]

    def get_tasks_for_view(self, tasks: List[Task], show_completed: bool = False) -> List[Task]:
        """Return filtered tasks in the same sorted order used by the UI."""
        return self.generate_conflict_free_plan(
            self.filter_tasks(tasks, show_completed=show_completed)
        )

    def generate_conflict_free_plan(self, tasks: List[Task]) -> List[Task]:
        """Return sorted task copies with overlapping same-pet display times shifted later."""
        pet_tasks: dict = {}
        pet_order: List[str] = []
        for task in tasks:
            pet_key = task.pet_name
            if pet_key not in pet_tasks:
                pet_order.append(pet_key)
                pet_tasks[pet_key] = []
            pet_tasks[pet_key].append(task)

        adjusted_plan: List[Task] = []
        for pet_key in pet_order:
            previous_end = None
            for task in self.sort_tasks_by_priority(pet_tasks[pet_key]):
                try:
                    scheduled_start = _parse_time(task.time)
                except (TypeError, ValueError):
                    adjusted_plan.append(replace(task))
                    continue

                if previous_end is not None and scheduled_start < previous_end:
                    scheduled_start = previous_end

                adjusted_task = replace(task, time=scheduled_start.strftime("%H:%M"))
                adjusted_plan.append(adjusted_task)
                previous_end = scheduled_start + timedelta(minutes=task.duration)

        return adjusted_plan

    def detect_conflicts(self, tasks: List[Task]) -> List[tuple]:
        """Return pairs of tasks that overlap in time for the same pet."""
        # Group tasks by pet so we only check overlaps within the same pet's schedule
        pet_tasks: dict = {}
        for task in tasks:
            pet_tasks.setdefault(task.pet_name, []).append(task)

        conflicts: List[tuple] = []
        for pet_task_list in pet_tasks.values():
            sorted_tasks = sorted(pet_task_list, key=lambda t: _parse_time(t.time))
            for i in range(len(sorted_tasks)):
                for j in range(i + 1, len(sorted_tasks)):
                    a = sorted_tasks[i]
                    b = sorted_tasks[j]
                    a_start = _parse_time(a.time)
                    a_end = a_start + timedelta(minutes=a.duration)
                    b_start = _parse_time(b.time)
                    if b_start < a_end:   # b starts before a finishes → overlap
                        conflicts.append((a, b))
        return conflicts
