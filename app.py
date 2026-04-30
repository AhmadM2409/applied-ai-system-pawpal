from datetime import time
from pawpal_system import Owner, Pet, Task, Scheduler
from agent import PawPalAgent

import streamlit as st

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ── Session state initialisation ─────────────────────────────────────────────
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Alex")
    st.session_state.scheduler = Scheduler()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.write(f"Logged in as: {st.session_state.owner.name}")
    st.divider()
    task_view = st.radio("View tasks", ["Pending", "Completed"], key="task_view")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

# ── Conflict banner (always visible) ─────────────────────────────────────────
_all_tasks = st.session_state.owner.get_all_tasks()
if _all_tasks:
    _conflicts = st.session_state.scheduler.detect_conflicts(_all_tasks)
    if _conflicts:
        st.warning(f"{len(_conflicts)} scheduling conflict(s) detected:")
        for _a, _b in _conflicts:
            st.warning(
                f"**{_a.pet_name}**: '{_a.description}' ({_a.time}, {_a.duration} min) "
                f"overlaps with '{_b.description}' ({_b.time}, {_b.duration} min)"
            )

st.divider()

# ── Add a Pet ─────────────────────────────────────────────────────────────────
st.subheader("Add a Pet")
col1, col2 = st.columns(2)
with col1:
    new_pet_name = st.text_input("Pet name", key="new_pet_name")
with col2:
    new_pet_species = st.selectbox("Species", ["Dog", "Cat", "Bird", "Other"], key="new_pet_species")

if st.button("Add Pet"):
    if new_pet_name.strip():
        new_pet = Pet(name=new_pet_name.strip(), species=new_pet_species)
        st.session_state.owner.add_pet(new_pet)
        st.success(f"Added {new_pet.name} ({new_pet.species})")
        st.rerun()
    else:
        st.warning("Please enter a pet name.")

st.divider()

# ── Add a Task ────────────────────────────────────────────────────────────────
st.subheader("Add a Task")

pets = st.session_state.owner.pets
if not pets:
    st.info("Add a pet first before adding tasks.")
else:
    selected_pet_name = st.selectbox(
        "Assign to pet", [p.name for p in pets], key="task_pet"
    )

    col1, col2 = st.columns(2)
    with col1:
        task_desc = st.text_input("Description", value="Morning walk", key="task_desc")
        task_time = st.time_input("Time", value=time(9, 0), key="task_time")
    with col2:
        task_duration = st.number_input(
            "Duration (minutes)", min_value=1, max_value=240, value=20, key="task_duration"
        )
        task_priority = st.selectbox(
            "Priority",
            [1, 2, 3],
            format_func=lambda x: {1: "1 - High", 2: "2 - Medium", 3: "3 - Low"}[x],
            key="task_priority",
        )

    col1, col2 = st.columns(2)
    with col1:
        task_category = st.selectbox(
            "Category", ["Feeding", "Exercise", "Health", "Grooming", "Other"], key="task_category"
        )
    with col2:
        task_frequency = st.selectbox(
            "Frequency", ["Once", "Daily", "Weekly"], key="task_frequency"
        )

    if st.button("Add Task"):
        new_task = Task(
            description=task_desc.strip(),
            time=task_time.strftime("%H:%M"),
            duration=int(task_duration),
            priority=task_priority,
            category=task_category,
            frequency=task_frequency,
        )
        target_pet = next(p for p in pets if p.name == selected_pet_name)
        target_pet.add_task(new_task)
        st.success(f"Added '{new_task.description}' to {target_pet.name}'s schedule.")
        st.rerun()

st.divider()

# ── Smart Scheduling (AI) ─────────────────────────────────────────────────────
st.subheader("✨ Smart Scheduling (AI)")

ai_input = st.text_input(
    "Type your scheduling request naturally (e.g., Schedule a walk for Buddy at 5 PM)",
    key="ai_input",
)

if st.button("Schedule with AI"):
    if not ai_input.strip():
        st.warning("Please enter a scheduling request.")
    else:
        with st.spinner("Parsing your request..."):
            try:
                agent = PawPalAgent()
                parsed = agent.parse_user_request(ai_input.strip())
            except Exception as e:
                st.error(f"AI parsing failed: {e}")
                parsed = None

        if parsed:
            ai_pet_name = parsed.get("pet_name", "").strip()
            ai_task_desc = parsed.get("task_description", "").strip()
            ai_time = parsed.get("time", "").strip()

            matched_pet = next(
                (p for p in st.session_state.owner.pets if p.name.lower() == ai_pet_name.lower()),
                None,
            )

            if not matched_pet:
                st.warning(
                    f"No pet named **{ai_pet_name}** found. "
                    "Please add that pet first using the 'Add a Pet' section above."
                )
            else:
                ai_task = Task(
                    description=ai_task_desc or "Task",
                    time=ai_time or "09:00",
                    duration=20,
                    priority=2,
                    category="Other",
                    frequency="Once",
                )
                matched_pet.add_task(ai_task)
                st.success(
                    f"Task added to **{matched_pet.name}**'s schedule: "
                    f"'{ai_task.description}' at {ai_task.time}"
                )
                st.rerun()

st.divider()

# ── Current Pets & Tasks ──────────────────────────────────────────────────────
show_completed = task_view == "Completed"
st.subheader(f"Current Pets & Tasks — {task_view}")
if not st.session_state.owner.pets:
    st.info("No pets added yet.")
else:
    for pet in st.session_state.owner.pets:
        visible = st.session_state.scheduler.filter_tasks(pet.tasks, show_completed=show_completed)
        with st.expander(f"{pet.name} ({pet.species}) — {len(visible)} {task_view.lower()} task(s)"):
            if visible:
                st.table([
                    {
                        "Time": t.time,
                        "Description": t.description,
                        "Duration": f"{t.duration} min",
                        "Priority": t.priority,
                        "Category": t.category,
                        "Frequency": t.frequency,
                        "Done": t.is_completed,
                    }
                    for t in visible
                ])
            else:
                st.caption(f"No {task_view.lower()} tasks.")

st.divider()

# ── Generate Schedule ─────────────────────────────────────────────────────────
st.subheader("Build Schedule")

if st.button("Generate schedule"):
    all_tasks = st.session_state.owner.get_all_tasks()
    if not all_tasks:
        st.warning("No tasks to schedule. Add some tasks first.")
    else:
        plan = st.session_state.scheduler.generate_daily_plan(
            st.session_state.owner, include_completed=show_completed
        )
        st.markdown(f"### Today's Plan — {task_view}")
        st.table([
            {
                "Pet": t.pet_name,
                "Time": t.time,
                "Task": t.description,
                "Duration": f"{t.duration} min",
                "Priority": t.priority,
                "Category": t.category,
                "Frequency": t.frequency,
            }
            for t in plan
        ])
        st.success("Conflicts are shown at the top of the page if any exist.")
