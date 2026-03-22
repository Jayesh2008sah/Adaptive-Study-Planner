import copy
import json
import os
from planner import generate_plan, auto_adjust_plan, update_priorities, print_plan

STATE_FILE = "state.json"

# ── STATE: SAVE & LOAD ─────────────────────────────────────

def save_state(subjects):
    with open(STATE_FILE, "w") as f:
        json.dump(subjects, f, indent=2)
    print("\n  [state saved to state.json]")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            subjects = json.load(f)
        print("  [loaded previous state from state.json]")
        return subjects
    return None


def reset_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print("  [state reset — starting fresh]")


# ── CLI: INPUT HELPERS ─────────────────────────────────────

def ask(prompt):
    return input(f"\n{prompt} > ").strip()


def ask_int(prompt, min_val=1, max_val=100):
    while True:
        try:
            val = int(ask(prompt))
            if min_val <= val <= max_val:
                return val
            print(f"  Enter a number between {min_val} and {max_val}")
        except ValueError:
            print("  Enter a valid number")


def ask_choice(prompt, options):
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        try:
            val = int(ask("Choose")) 
            if 1 <= val <= len(options):
                return options[val - 1]
            print(f"  Enter a number between 1 and {len(options)}")
        except ValueError:
            print("  Enter a valid number")


def ask_multi(prompt, options):
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    print("  Enter numbers separated by commas (e.g. 1,3)")
    while True:
        raw = ask("Choose").split(",")
        try:
            chosen = [options[int(x.strip()) - 1] for x in raw if x.strip()]
            if chosen:
                return chosen
            print("  Pick at least one")
        except (ValueError, IndexError):
            print("  Invalid input, try again")


# ── CLI: BUILD SUBJECTS ────────────────────────────────────

def build_subjects_from_cli():
    subjects = []
    num = ask_int("How many subjects do you want to add?", 1, 10)

    for i in range(num):
        print(f"\n--- Subject {i + 1} ---")
        name = ask("Subject name")
        priority = ask_int("Base priority (1=low, 5=high)", 1, 5)

        topics = []
        num_topics = ask_int("How many topics?", 1, 20)

        for j in range(num_topics):
            print(f"  -- Topic {j + 1} --")
            topic_name = ask("  Topic name")
            difficulty = ask_choice("  Difficulty", ["easy", "medium", "hard"])
            energy = ask_choice("  Energy required", ["low", "medium", "high"])
            topics.append({
                "name": topic_name,
                "difficulty": difficulty,
                "energy": energy
            })

        subjects.append({
            "name": name,
            "base_priority": priority,
            "priority": priority,
            "missed": 0,
            "topics": topics
        })

    return subjects


# ── CLI: WEEK SETUP ────────────────────────────────────────

def build_day_types():
    print("\nWeek setup — for each day enter:")
    print("  1 = weekday (2h evening)")
    print("  2 = sunday  (4h: afternoon + evening)")
    day_types = []
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for name in day_names:
        choice = ask_choice(f"{name}", ["weekday", "sunday"])
        day_types.append(choice)
    return day_types


# ── CLI: MISSED SUBJECTS ───────────────────────────────────

def ask_missed(subjects):
    names = [s["name"] for s in subjects]
    print("\nWhich subjects did you miss this week?")
    print("  0. None")
    for i, name in enumerate(names, 1):
        print(f"  {i}. {name}")
    raw = ask("Enter numbers separated by commas, or 0 for none").split(",")
    missed = []
    for x in raw:
        x = x.strip()
        if x == "0":
            return []
        try:
            idx = int(x) - 1
            if 0 <= idx < len(names):
                missed.append(names[idx])
        except ValueError:
            pass
    return missed


# ── MAIN ───────────────────────────────────────────────────

def main():
    print("\n========================================")
    print("   ADAPTIVE STUDY PLANNER")
    print("========================================")

    # load or build subjects
    saved = load_state()
    if saved:
        use_saved = ask_choice(
            "Previous state found. Use it?",
            ["Yes — continue from last week", "No — start fresh"]
        )
        if use_saved.startswith("Yes"):
            subjects = saved
            print("\nLoaded subjects:")
            for s in subjects:
                print(f"  {s['name']}: priority={s['priority']}, missed={s['missed']}")
        else:
            reset_state()
            subjects = build_subjects_from_cli()
    else:
        subjects = build_subjects_from_cli()

    # week setup
    use_default_week = ask_choice(
        "\nWeek structure",
        ["Default (Mon-Sat weekday, Sun sunday)", "Custom"]
    )
    if use_default_week.startswith("Default"):
        day_types = ["weekday", "weekday", "weekday", "weekday", "weekday", "weekday", "sunday"]
    else:
        day_types = build_day_types()

    # missed subjects
    missed = ask_missed(subjects)

    # update priorities
    subjects = update_priorities(subjects, missed)

    print("\n====== PRIORITIES ======")
    for s in subjects:
        print(f"  {s['name']}: priority={round(s['priority'], 1)}, missed={s['missed']}")

    # generate plan
    plan = generate_plan(subjects, day_types)

    print("\n====== WEEKLY PLAN ======")
    print_plan(plan)

    # recovery if missed
    if missed:
        adjusted = auto_adjust_plan(copy.deepcopy(plan), missed, subjects)
        print("\n====== ADJUSTED PLAN (with recovery) ======")
        print_plan(adjusted)

    # save state
    save_state(subjects)

    print("\n========================================")
    print("   DONE. Run again next week.")
    print("========================================\n")


if __name__ == "__main__":
    main()