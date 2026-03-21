import copy

ENERGY_ORDER = {"high": 0, "medium": 1, "low": 2}
DIFFICULTY_TIME = {"easy": 45, "medium": 60, "hard": 90}


def build_weighted_pool(subjects):
    pool = []
    for subject in subjects:
        weight = max(1, round(subject.get("priority", 1)))
        for _ in range(weight):
            pool.append(subject["name"])
    return pool


def build_topic_list(subjects):
    topics = []
    for subject in subjects:
        weight = max(1, round(subject.get("priority", 1)))
        for topic in subject["topics"]:
            difficulty = topic.get("difficulty", "medium")
            time_mins = DIFFICULTY_TIME[difficulty]
            energy = topic.get("energy", "medium")
            topics.append({
                "subject": subject["name"],
                "topic": topic["name"],
                "difficulty": difficulty,
                "energy": energy,
                "time": time_mins,
                "weight": weight
            })
    return topics


def generate_plan(subjects, day_types):
    all_topics = build_topic_list(subjects)

    all_topics.sort(key=lambda x: (
        ENERGY_ORDER[x["energy"]],
        -DIFFICULTY_TIME[x["difficulty"]],
        -x["weight"]
    ))

    plan = {}

    for i, day_type in enumerate(day_types):
        remaining_work = [t for t in all_topics if t["time"] > 0]
        if not remaining_work:
            break

        day_label = f"Day {i + 1} ({day_type})"
        day_plan = []

        if day_type == "weekday":
            bands = [
                {
                    "label": "Evening",
                    "minutes": 120,
                    "allowed_energy": ["high", "medium", "low"],
                    "allowed_difficulty": ["easy", "medium", "hard"]
                }
            ]
        else:
            bands = [
                {
                    "label": "Afternoon",
                    "minutes": 120,
                    "allowed_energy": ["high", "medium"],
                    "allowed_difficulty": ["medium", "hard"]
                },
                {
                    "label": "Evening",
                    "minutes": 120,
                    "allowed_energy": ["medium", "low"],
                    "allowed_difficulty": ["easy", "medium"]
                }
            ]

        for band in bands:
            remaining = band["minutes"]
            for task in all_topics:
                if remaining <= 0:
                    break
                if task["time"] <= 0:
                    continue
                if task["energy"] not in band["allowed_energy"]:
                    continue
                if task["difficulty"] not in band["allowed_difficulty"]:
                    continue

                used = min(task["time"], remaining)
                day_plan.append({
                    "subject": task["subject"],
                    "topic": task["topic"],
                    "difficulty": task["difficulty"],
                    "energy": task["energy"],
                    "time": used,
                    "band": band["label"]
                })
                task["time"] -= used
                remaining -= used

        plan[day_label] = day_plan

    return plan


def auto_adjust_plan(plan, missed_subjects, subjects):
    if not missed_subjects:
        return plan

    days = list(plan.keys())
    days_left = len(days)

    missed_minutes = 0
    for subject in subjects:
        if subject["name"] in missed_subjects:
            for topic in subject["topics"]:
                difficulty = topic.get("difficulty", "medium")
                missed_minutes += DIFFICULTY_TIME[difficulty]

    if missed_minutes <= 0:
        return plan

    extra_per_day = missed_minutes // days_left

    for day in days:
        plan[day].append({
            "subject": "Recovery",
            "topic": f"Make up: {', '.join(missed_subjects)}",
            "difficulty": "mixed",
            "energy": "medium",
            "time": extra_per_day,
            "band": "Evening"
        })

    return plan


def update_priorities(subjects, missed_subjects):
    for subject in subjects:
        base = subject.get("base_priority", 1)
        current = subject.get("priority", base)

        if subject["name"] in missed_subjects:
            subject["priority"] = current + 2.5
            subject["missed"] = subject.get("missed", 0) + 1
        else:
            subject["priority"] = max(base, current - 0.3)
            subject["missed"] = subject.get("missed", 0)

    return subjects


def reset_completed_topics(subjects):
    """
    Resets topics that were completed last week so they
    can be scheduled again next week.
    """
    for subject in subjects:
        for topic in subject["topics"]:
            topic["completed"] = False
    return subjects


def add_topics_to_subject(subjects, subject_name, new_topics):
    """
    Adds new topics to an existing subject.
    new_topics: list of dicts with name, difficulty, energy
    """
    for subject in subjects:
        if subject["name"] == subject_name:
            for t in new_topics:
                t["completed"] = False
                subject["topics"].append(t)
            return subjects
    return subjects


def generate_weekly_summary(subjects, plan, missed_subjects):
    """
    Returns a summary dict with:
    - total hours studied
    - hours per subject
    - missed subjects and count
    - priority trends
    """
    summary = {
        "total_minutes": 0,
        "by_subject": {},
        "missed": missed_subjects,
        "priority_trends": []
    }

    for day, tasks in plan.items():
        for task in tasks:
            subj = task["subject"]
            mins = task["time"]
            summary["total_minutes"] += mins
            if subj not in summary["by_subject"]:
                summary["by_subject"][subj] = 0
            summary["by_subject"][subj] += mins

    for subject in subjects:
        name = subject["name"]
        base = subject.get("base_priority", 1)
        current = subject.get("priority", base)
        missed_count = subject.get("missed", 0)

        if current > base:
            trend = "↑ rising (missed)"
        elif current < base:
            trend = "↓ decaying (consistent)"
        else:
            trend = "→ stable"

        summary["priority_trends"].append({
            "subject": name,
            "priority": round(current, 1),
            "missed_total": missed_count,
            "trend": trend
        })

    return summary


def print_plan(plan):
    for day, tasks in plan.items():
        print(f"\n{day}")
        if not tasks:
            print("  No tasks scheduled")
            continue
        for t in tasks:
            diff = t.get("difficulty", "")
            band = t.get("band", "")
            print(f"  [{band}] [{diff}] {t['subject']} - {t['topic']} ({t['time']} mins)")


def print_summary(summary):
    print("\n========================================")
    print("   WEEKLY SUMMARY")
    print("========================================")

    total_hours = summary["total_minutes"] // 60
    total_mins = summary["total_minutes"] % 60
    print(f"\n  Total study time: {total_hours}h {total_mins}m")

    print("\n  Time per subject:")
    for subj, mins in sorted(summary["by_subject"].items(), key=lambda x: -x[1]):
        hours = mins // 60
        rem = mins % 60
        print(f"    {subj}: {hours}h {rem}m")

    if summary["missed"]:
        print(f"\n  Missed this week: {', '.join(summary['missed'])}")
    else:
        print("\n  No subjects missed this week ✓")

    print("\n  Priority trends:")
    for t in summary["priority_trends"]:
        print(f"    {t['subject']}: {t['priority']} — {t['trend']} (total missed: {t['missed_total']})")
def check_bias(subjects, plan):
    """
    Checks if any subject is getting less than 10% of total study time.
    Returns a list of warnings for underscheduled subjects.
    """
    time_per_subject = {}
    total_time = 0

    for day, tasks in plan.items():
        for task in tasks:
            subj = task["subject"]
            mins = task["time"]
            if subj == "Recovery":
                continue
            time_per_subject[subj] = time_per_subject.get(subj, 0) + mins
            total_time += mins

    warnings = []
    if total_time == 0:
        return warnings

    for subject in subjects:
        name = subject["name"]
        mins = time_per_subject.get(name, 0)
        percentage = (mins / total_time) * 100

        if percentage < 10:
            warnings.append({
                "subject": name,
                "percentage": round(percentage, 1),
                "minutes": mins,
                "message": f"{name} is only getting {round(percentage, 1)}% of your study time this week ({mins} mins). Is that intentional?"
            })

    return warnings        