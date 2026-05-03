import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from datetime import time
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
from pawpal_system import Task, Pet, Owner, Scheduler, is_valid_time
from agent import PawPalAgent, EMPTY_RESULT


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_task(description="Feed", time_str="09:00", duration=30, priority=2, category="Feeding"):
    return Task(
        description=description,
        time=time_str,
        duration=duration,
        priority=priority,
        category=category,
    )


def make_mock_mistral_response(content: str):
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = content
    return response


@pytest.mark.parametrize("time_text", ["00:00", "09:30", "13:00", "23:59"])
def test_is_valid_time_accepts_hh_mm_24_hour_values(time_text):
    assert is_valid_time(time_text) is True


@pytest.mark.parametrize(
    "time_text",
    ["", "25:00", "13:99", "1pm", "tomorrow evening", None],
)
def test_is_valid_time_rejects_invalid_values(time_text):
    assert is_valid_time(time_text) is False


# ── Task tests ───────────────────────────────────────────────────────────────

class TestTask:

    def test_mark_complete_flips_status(self):
        task = make_task()
        assert task.is_completed is False
        task.mark_complete()
        assert task.is_completed is True

    def test_mark_complete_is_idempotent(self):
        task = make_task()
        task.mark_complete()
        task.mark_complete()   # calling twice should not raise or revert
        assert task.is_completed is True


# ── Pet tests ────────────────────────────────────────────────────────────────

def test_recurring_daily_task_creates_new_pending_copy():
    from pawpal_system import Pet, Task

    pet = Pet(name="Buddy", species="Dog")

    task = Task(
        description="Feed",
        time="09:00",
        duration=10,
        priority=1,
        category="Food",
        frequency="Daily",
    )

    pet.add_task(task)

    task.mark_complete(pet)

    assert task.is_completed is True
    assert len(pet.tasks) == 2

    new_task = pet.tasks[1]
    assert new_task.description == "Feed"
    assert new_task.time == "09:00"
    assert new_task.duration == 10
    assert new_task.priority == 1
    assert new_task.category == "Food"
    assert new_task.frequency == "Daily"
    assert new_task.is_completed is False
    assert new_task.pet_name == "Buddy"


class TestPet:

    def test_add_task_appends_to_list(self):
        pet = Pet(name="Buddy", species="Dog")
        task = make_task()
        pet.add_task(task)
        assert task in pet.tasks
        assert len(pet.tasks) == 1

    def test_add_task_stamps_pet_name(self):
        pet = Pet(name="Buddy", species="Dog")
        task = make_task()
        pet.add_task(task)
        assert task.pet_name == "Buddy"

    def test_add_multiple_tasks(self):
        pet = Pet(name="Misty", species="Cat")
        pet.add_task(make_task("Task A"))
        pet.add_task(make_task("Task B"))
        assert len(pet.tasks) == 2


# ── Scheduler conflict detection tests ───────────────────────────────────────

class TestSchedulerConflicts:

    def _build_owner_with_overlap(self):
        """Buddy has two overlapping tasks; Misty has none."""
        buddy = Pet(name="Buddy", species="Dog")
        buddy.add_task(make_task("Morning walk",  time_str="08:00", duration=30))
        buddy.add_task(make_task("Flea treatment", time_str="08:15", duration=20))

        misty = Pet(name="Misty", species="Cat")
        misty.add_task(make_task("Vet medication", time_str="09:00", duration=10))

        owner = Owner(name="Alex")
        owner.add_pet(buddy)
        owner.add_pet(misty)
        return owner

    def test_detects_exactly_one_conflict(self):
        owner = self._build_owner_with_overlap()
        scheduler = Scheduler()
        conflicts = scheduler.detect_conflicts(owner.get_all_tasks())
        assert len(conflicts) == 1

    def test_conflict_involves_correct_pet(self):
        owner = self._build_owner_with_overlap()
        scheduler = Scheduler()
        task_a, task_b = scheduler.detect_conflicts(owner.get_all_tasks())[0]
        assert task_a.pet_name == "Buddy"
        assert task_b.pet_name == "Buddy"

    def test_conflict_identifies_correct_tasks(self):
        owner = self._build_owner_with_overlap()
        scheduler = Scheduler()
        task_a, task_b = scheduler.detect_conflicts(owner.get_all_tasks())[0]
        descriptions = {task_a.description, task_b.description}
        assert descriptions == {"Morning walk", "Flea treatment"}

    def test_no_conflict_when_tasks_are_sequential(self):
        pet = Pet(name="Buddy", species="Dog")
        pet.add_task(make_task("Walk",    time_str="08:00", duration=30))
        pet.add_task(make_task("Feeding", time_str="08:30", duration=15))  # starts exactly when walk ends

        owner = Owner(name="Alex")
        owner.add_pet(pet)
        scheduler = Scheduler()
        conflicts = scheduler.detect_conflicts(owner.get_all_tasks())
        assert len(conflicts) == 0

    def test_cross_pet_tasks_never_conflict(self):
        buddy = Pet(name="Buddy", species="Dog")
        misty = Pet(name="Misty", species="Cat")
        buddy.add_task(make_task("Walk",     time_str="09:00", duration=60))
        misty.add_task(make_task("Grooming", time_str="09:15", duration=30))  # same slot, different pet

        owner = Owner(name="Alex")
        owner.add_pet(buddy)
        owner.add_pet(misty)
        scheduler = Scheduler()
        conflicts = scheduler.detect_conflicts(owner.get_all_tasks())
        assert len(conflicts) == 0

    def test_identical_same_pet_tasks_conflict(self):
        pet = Pet(name="Kat", species="Dog")
        pet.add_task(make_task("Run", time_str="13:00", duration=20))
        pet.add_task(make_task("Run", time_str="13:00", duration=20))

        owner = Owner(name="Alex")
        owner.add_pet(pet)
        scheduler = Scheduler()
        conflicts = scheduler.detect_conflicts(owner.get_all_tasks())
        assert len(conflicts) == 1


class TestSchedulerSorting:

    def _descriptions(self, tasks):
        return [task.description for task in Scheduler().sort_tasks_by_priority(tasks)]

    def test_higher_priority_comes_first_even_if_later(self):
        tasks = [
            make_task("Medium morning food", time_str="08:00", priority=2, category="Food"),
            make_task("High afternoon exercise", time_str="15:00", priority=1, category="Exercise"),
        ]

        assert self._descriptions(tasks) == ["High afternoon exercise", "Medium morning food"]

    def test_category_breaks_priority_and_time_ties(self):
        tasks = [
            make_task("Other task", time_str="13:00", priority=1, category="Other"),
            make_task("Exercise task", time_str="13:00", priority=1, category="Exercise"),
            make_task("Health task", time_str="13:00", priority=1, category="Health"),
            make_task("Food task", time_str="13:00", priority=1, category="Food"),
        ]

        assert self._descriptions(tasks) == [
            "Health task",
            "Food task",
            "Exercise task",
            "Other task",
        ]

    def test_category_ranking_is_case_insensitive(self):
        tasks = [
            make_task("Exercise task", time_str="13:00", priority=1, category="exercise"),
            make_task("Health task", time_str="13:00", priority=1, category="HEALTH"),
        ]

        assert self._descriptions(tasks) == ["Health task", "Exercise task"]

    def test_time_breaks_ties_after_priority_and_category(self):
        tasks = [
            make_task("Later health", time_str="14:00", priority=1, category="Health"),
            make_task("Earlier health", time_str="09:00", priority=1, category="Health"),
        ]

        assert self._descriptions(tasks) == ["Earlier health", "Later health"]

    def test_completed_tasks_appear_after_pending_tasks(self):
        completed = make_task("Completed urgent health", time_str="08:00", priority=1, category="Health")
        completed.is_completed = True
        pending = make_task("Pending low other", time_str="20:00", priority=3, category="Other")

        assert self._descriptions([completed, pending]) == [
            "Pending low other",
            "Completed urgent health",
        ]

    def test_invalid_category_defaults_to_other_ranking(self):
        tasks = [
            make_task("Unknown category", time_str="13:00", priority=1, category="Mystery"),
            make_task("Exercise category", time_str="13:00", priority=1, category="Exercise"),
        ]

        assert self._descriptions(tasks) == ["Exercise category", "Unknown category"]

    def test_invalid_time_sorts_last_without_crashing(self):
        tasks = [
            make_task("Invalid time", time_str="tomorrow evening", priority=1, category="Health"),
            make_task("Valid time", time_str="13:00", priority=1, category="Health"),
        ]

        assert self._descriptions(tasks) == ["Valid time", "Invalid time"]

    def test_get_tasks_for_view_preserves_toggle_and_sorting(self):
        pending_exercise = make_task("Run", time_str="13:00", priority=1, category="Exercise")
        pending_health = make_task("Get flu shot", time_str="13:00", priority=1, category="Health")
        completed_health = make_task("Completed shot", time_str="08:00", priority=1, category="Health")
        completed_health.is_completed = True

        scheduler = Scheduler()
        tasks = [pending_exercise, completed_health, pending_health]

        pending_view = scheduler.get_tasks_for_view(tasks, show_completed=False)
        completed_view = scheduler.get_tasks_for_view(tasks, show_completed=True)

        assert [task.description for task in pending_view] == ["Get flu shot", "Run"]
        assert [task.description for task in completed_view] == ["Completed shot"]


class TestConflictFreePlan:

    def _pet_with_tasks(self, name="Kat", species="Dog", tasks=None):
        pet = Pet(name=name, species=species)
        for task in tasks or []:
            pet.add_task(task)
        return pet

    def test_lower_priority_same_time_task_shifts_after_higher_priority_task(self):
        flu_shot = make_task("Get flu shot", time_str="13:00", duration=20, priority=1, category="Health")
        run = make_task("Run", time_str="13:00", duration=20, priority=2, category="Exercise")
        pet = self._pet_with_tasks(tasks=[run, flu_shot])

        plan = Scheduler().generate_conflict_free_plan(pet.tasks)

        assert [(task.description, task.time) for task in plan] == [
            ("Get flu shot", "13:00"),
            ("Run", "13:20"),
        ]
        assert run.time == "13:00"

    def test_same_priority_health_stays_before_exercise_and_exercise_shifts(self):
        run = make_task("Run", time_str="13:00", duration=20, priority=1, category="Exercise")
        flu_shot = make_task("Get flu shot", time_str="13:00", duration=20, priority=1, category="Health")
        pet = self._pet_with_tasks(tasks=[run, flu_shot])

        plan = Scheduler().generate_conflict_free_plan(pet.tasks)

        assert [(task.description, task.time) for task in plan] == [
            ("Get flu shot", "13:00"),
            ("Run", "13:20"),
        ]

    def test_non_conflicting_tasks_keep_original_times(self):
        walk = make_task("Walk", time_str="09:00", duration=20, priority=2, category="Exercise")
        run = make_task("Run", time_str="10:00", duration=20, priority=2, category="Exercise")
        pet = self._pet_with_tasks(tasks=[walk, run])

        plan = Scheduler().generate_conflict_free_plan(pet.tasks)

        assert [(task.description, task.time) for task in plan] == [
            ("Walk", "09:00"),
            ("Run", "10:00"),
        ]
        assert walk.time == "09:00"
        assert run.time == "10:00"

    def test_cross_pet_tasks_do_not_shift_each_other(self):
        kat = self._pet_with_tasks(
            name="Kat",
            tasks=[make_task("Run", time_str="13:00", duration=20, priority=1, category="Exercise")],
        )
        buddy = self._pet_with_tasks(
            name="Buddy",
            tasks=[make_task("Walk", time_str="13:00", duration=20, priority=1, category="Exercise")],
        )

        plan = Scheduler().generate_conflict_free_plan(kat.tasks + buddy.tasks)

        assert [(task.pet_name, task.description, task.time) for task in plan] == [
            ("Kat", "Run", "13:00"),
            ("Buddy", "Walk", "13:00"),
        ]

    def test_chain_conflicts_shift_correctly(self):
        first = make_task("First", time_str="13:00", duration=20, priority=1, category="Health")
        second = make_task("Second", time_str="13:10", duration=20, priority=1, category="Health")
        third = make_task("Third", time_str="13:15", duration=20, priority=1, category="Health")
        pet = self._pet_with_tasks(tasks=[first, second, third])

        plan = Scheduler().generate_conflict_free_plan(pet.tasks)

        assert [(task.description, task.time) for task in plan] == [
            ("First", "13:00"),
            ("Second", "13:20"),
            ("Third", "13:40"),
        ]


def test_agent_parses_valid_json_response(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    agent = PawPalAgent()
    agent.client.chat.complete = Mock(
        return_value=make_mock_mistral_response(
            '{"pet_name": "Kat", "task_description": "Take bath", "time": "13:00", "priority": 2, "category": "Health"}'
        )
    )

    result = agent.parse_schedule_request("Kat must take bath at 1pm, medium priority.")

    assert result == {
        "pet_name": "Kat",
        "task_description": "Take bath",
        "time": "13:00",
        "priority": 2,
        "category": "Health",
    }


def test_agent_converts_priority_string_to_integer(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    agent = PawPalAgent()
    agent.client.chat.complete = Mock(
        return_value=make_mock_mistral_response(
            '{"pet_name": "Kat", "task_description": "Run", "time": "13:00", "priority": "1", "category": "Exercise"}'
        )
    )

    result = agent.parse_schedule_request("Kat must run at 1 PM")

    assert result == {
        "pet_name": "Kat",
        "task_description": "Run",
        "time": "13:00",
        "priority": 1,
        "category": "Exercise",
    }


def test_agent_defaults_invalid_or_missing_priority(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    agent = PawPalAgent()
    agent.client.chat.complete = Mock(
        return_value=make_mock_mistral_response(
            '{"pet_name": "Kat", "task_description": "Run", "time": "13:00", "priority": "soon", "category": "Exercise"}'
        )
    )
    invalid_result = agent.parse_schedule_request("Kat must run at 1 PM")

    agent.client.chat.complete = Mock(
        return_value=make_mock_mistral_response(
            '{"pet_name": "Kat", "task_description": "Run", "time": "13:00"}'
        )
    )
    missing_result = agent.parse_schedule_request("Kat must run at 1 PM")

    assert invalid_result["priority"] == 2
    assert missing_result["priority"] == 2


def test_agent_infers_invalid_or_missing_category(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    agent = PawPalAgent()
    agent.client.chat.complete = Mock(
        return_value=make_mock_mistral_response(
            '{"pet_name": "Kat", "task_description": "Take bath", "time": "13:00", "priority": 2, "category": "Spa"}'
        )
    )
    invalid_result = agent.parse_schedule_request("Kat must take bath at 1pm, medium priority.")

    agent.client.chat.complete = Mock(
        return_value=make_mock_mistral_response(
            '{"pet_name": "Kat", "task_description": "Take bath", "time": "13:00", "priority": 2}'
        )
    )
    missing_result = agent.parse_schedule_request("Kat must take bath at 1pm, medium priority.")

    assert invalid_result["category"] == "Health"
    assert missing_result["category"] == "Health"


def test_agent_infers_exercise_category(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    agent = PawPalAgent()
    agent.client.chat.complete = Mock(
        return_value=make_mock_mistral_response(
            '{"pet_name": "Kat", "task_description": "Run", "time": "13:00", "priority": 2}'
        )
    )

    result = agent.parse_schedule_request("Kat must run at 1pm")

    assert result["category"] == "Exercise"


def test_agent_infers_food_category(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    agent = PawPalAgent()
    agent.client.chat.complete = Mock(
        return_value=make_mock_mistral_response(
            '{"pet_name": "Kat", "task_description": "Feed", "time": "12:00", "priority": 2}'
        )
    )

    result = agent.parse_schedule_request("Feed Kat at noon")

    assert result["category"] == "Food"


def test_agent_maps_priority_keywords_from_user_text(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    agent = PawPalAgent()
    agent.client.chat.complete = Mock(
        return_value=make_mock_mistral_response(
            '{"pet_name": "Kat", "task_description": "Run", "time": "13:00", "priority": 2, "category": "Exercise"}'
        )
    )

    result = agent.parse_schedule_request("Kat must run tomorrow at 1pm, super important priority")

    assert result["priority"] == 1


def test_agent_filters_extra_model_keys(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    agent = PawPalAgent()
    agent.client.chat.complete = Mock(
        return_value=make_mock_mistral_response(
            json.dumps(
                {
                    "pet_name": "Luna",
                    "task_description": "Feed",
                    "time": "12:00",
                    "priority": 3,
                    "category": "food",
                    "extra_key": "should not appear",
                }
            )
        )
    )

    result = agent.parse_schedule_request("Feed Luna at noon")

    assert result == {
        "pet_name": "Luna",
        "task_description": "Feed",
        "time": "12:00",
        "priority": 3,
        "category": "Food",
    }
    assert set(result.keys()) == {
        "pet_name",
        "task_description",
        "time",
        "priority",
        "category",
    }


def test_agent_returns_empty_result_for_invalid_json(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    agent = PawPalAgent()
    agent.client.chat.complete = Mock(
        return_value=make_mock_mistral_response("not valid json")
    )

    result = agent.parse_schedule_request("Walk Buddy at 5 PM")

    assert result == EMPTY_RESULT


def test_streamlit_current_tasks_table_uses_scheduler_sorting():
    app = AppTest.from_file("app.py", default_timeout=30)
    app.run()

    app.text_input(key="new_pet_name").set_value("Kat")
    app.selectbox(key="new_pet_species").set_value("Dog")
    app.button[0].click()
    app.run()

    app.text_input(key="task_desc").set_value("Run")
    app.time_input(key="task_time").set_value(time(13, 0))
    app.number_input(key="task_duration").set_value(20)
    app.selectbox(key="task_priority").set_value(1)
    app.selectbox(key="task_category").set_value("Exercise")
    app.selectbox(key="task_frequency").set_value("Once")
    app.button[1].click()
    app.run()

    app.text_input(key="task_desc").set_value("Get flu shot")
    app.time_input(key="task_time").set_value(time(13, 0))
    app.number_input(key="task_duration").set_value(20)
    app.selectbox(key="task_priority").set_value(1)
    app.selectbox(key="task_category").set_value("Health")
    app.selectbox(key="task_frequency").set_value("Once")
    app.button[1].click()
    app.run()

    table = app.table[0].value
    assert table["Description"].tolist()[:2] == ["Get flu shot", "Run"]
    assert table["Category"].tolist()[:2] == ["Health", "Exercise"]
    assert table["Time"].tolist()[:2] == ["13:00", "13:20"]
