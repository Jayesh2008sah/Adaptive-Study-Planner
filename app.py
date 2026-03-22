import json
import os
import copy
import streamlit as st
import plotly.express as px
import pandas as pd
from planner import (
    generate_plan, auto_adjust_plan, update_priorities,
    generate_weekly_summary, reset_completed_topics, add_topics_to_subject,
    check_bias
)

STATE_FILE = "state.json"
STREAK_FILE = "streak.json"

st.set_page_config(
    page_title="Adaptive Study Planner",
    page_icon="📚",
    layout="wide"
)

# ── CUSTOM CSS ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* dark sidebar */
section[data-testid="stSidebar"] {
    background: #0f0f0f;
    border-right: 1px solid #222;
}
section[data-testid="stSidebar"] * {
    color: #e0e0e0 !important;
}

/* main background */
.stApp {
    background: #111318;
    color: #f0f0f0;
}

/* cards */
.task-card {
    background: #1c1f26;
    border: 1px solid #2a2d35;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    transition: border-color 0.2s;
}
.task-card:hover {
    border-color: #4f46e5;
}
.task-card.done {
    opacity: 0.5;
    border-color: #22c55e;
}
.task-card.missed {
    border-color: #ef4444;
    background: #1f1515;
}

/* day card */
.day-card {
    background: #16191f;
    border: 1px solid #2a2d35;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
}
.day-title {
    font-size: 16px;
    font-weight: 600;
    color: #a0aec0;
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* stat cards */
.stat-card {
    background: #1c1f26;
    border: 1px solid #2a2d35;
    border-radius: 14px;
    padding: 20px 24px;
    text-align: center;
}
.stat-value {
    font-size: 32px;
    font-weight: 700;
    color: #f0f0f0;
    line-height: 1.1;
}
.stat-label {
    font-size: 13px;
    color: #6b7280;
    margin-top: 4px;
    font-weight: 500;
}

/* badges */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.03em;
}
.badge-hard   { background: #3b1212; color: #f87171; border: 1px solid #7f1d1d; }
.badge-medium { background: #2d1f00; color: #fbbf24; border: 1px solid #78350f; }
.badge-easy   { background: #0f2d1a; color: #4ade80; border: 1px solid #14532d; }
.badge-mixed  { background: #1e1b4b; color: #a5b4fc; border: 1px solid #3730a3; }

/* timer */
.timer-display {
    font-size: 28px;
    font-weight: 700;
    color: #f0f0f0;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.05em;
}

/* progress bar override */
.stProgress > div > div {
    background: #4f46e5;
    border-radius: 99px;
}

/* headings */
h1, h2, h3 { color: #f0f0f0 !important; }
p, span, label { color: #c0c0c0; }

/* buttons */
.stButton > button {
    background: #1c1f26;
    border: 1px solid #2a2d35;
    color: #f0f0f0;
    border-radius: 8px;
    font-weight: 500;
}
.stButton > button:hover {
    border-color: #4f46e5;
    color: #a5b4fc;
}

/* tab styling */
.stTabs [data-baseweb="tab"] {
    color: #6b7280;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    color: #a5b4fc !important;
    border-bottom-color: #4f46e5 !important;
}

/* metric */
[data-testid="metric-container"] {
    background: #1c1f26;
    border: 1px solid #2a2d35;
    border-radius: 12px;
    padding: 16px;
}

/* expander */
details {
    background: #16191f;
    border: 1px solid #2a2d35 !important;
    border-radius: 12px;
    padding: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── HELPERS ────────────────────────────────────────────────
DIFF_COLORS = {"hard": "hard", "medium": "medium", "easy": "easy", "mixed": "mixed"}

def badge(diff):
    cls = DIFF_COLORS.get(diff, "mixed")
    return f'<span class="badge badge-{cls}">{diff.upper()}</span>'

def save_state(subjects):
    with open(STATE_FILE, "w") as f:
        json.dump(subjects, f, indent=2)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return None

def reset_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

def load_streak():
    if os.path.exists(STREAK_FILE):
        with open(STREAK_FILE, "r") as f:
            return json.load(f)
    return {"current": 0, "best": 0}

def save_streak(streak):
    with open(STREAK_FILE, "w") as f:
        json.dump(streak, f, indent=2)

def update_streak(missed_any):
    streak = load_streak()
    if not missed_any:
        streak["current"] += 1
        if streak["current"] > streak["best"]:
            streak["best"] = streak["current"]
    else:
        streak["current"] = 0
    save_streak(streak)
    return streak

# ── SESSION INIT ───────────────────────────────────────────
if "subjects" not in st.session_state:
    saved = load_state()
    st.session_state.subjects = saved if saved else []
if "plan" not in st.session_state:
    st.session_state.plan = None
if "summary" not in st.session_state:
    st.session_state.summary = None
if "missed" not in st.session_state:
    st.session_state.missed = []
if "task_status" not in st.session_state:
    st.session_state.task_status = {}
if "form_key" not in st.session_state:
    st.session_state.form_key = 0
if "active_timer" not in st.session_state:
    st.session_state.active_timer = None

streak = load_streak()

# ── SIDEBAR ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Controls")
    if st.button("🔄 Reset Everything", use_container_width=True):
        reset_state()
        st.session_state.subjects = []
        st.session_state.plan = None
        st.session_state.summary = None
        st.session_state.missed = []
        st.session_state.task_status = {}
        st.session_state.form_key = 0
        st.session_state.active_timer = None
        st.rerun()
    if st.button("📅 Start New Week", use_container_width=True):
        if st.session_state.subjects:
            update_streak(len(st.session_state.missed) > 0)
            st.session_state.subjects = reset_completed_topics(st.session_state.subjects)
            st.session_state.plan = None
            st.session_state.summary = None
            st.session_state.missed = []
            st.session_state.task_status = {}
            st.session_state.active_timer = None
            save_state(st.session_state.subjects)
            st.success("New week started!")
            st.rerun()
    st.divider()
    st.markdown(f"**🔥 Streak**")
    st.markdown(f"Current: **{streak['current']} weeks**")
    st.markdown(f"Best: **{streak['best']} weeks**")
    st.divider()
    st.caption("Data saved in state.json")

# ── HEADER + STATS DASHBOARD ───────────────────────────────
st.markdown("# 📚 Adaptive Study Planner")
st.caption("Priority-weighted · Energy-aware · Missed day recovery · Responsible AI")
st.divider()

# stats dashboard always visible at top
total_tasks = sum(len(tasks) for tasks in st.session_state.plan.values()) if st.session_state.plan else 0
done_count  = sum(1 for v in st.session_state.task_status.values() if v == "done")
missed_count = sum(1 for v in st.session_state.task_status.values() if v == "missed")
completion_pct = int((done_count / total_tasks) * 100) if total_tasks > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📋 Total Tasks", total_tasks)
c2.metric("✅ Done", done_count)
c3.metric("❌ Missed", missed_count)
c4.metric("📈 Completion", f"{completion_pct}%")
c5.metric("🔥 Streak", f"{streak['current']} wks", f"Best: {streak['best']}")

if total_tasks > 0:
    st.progress(completion_pct / 100)

st.divider()

# ── TABS ───────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Subjects", "📅 Plan", "📊 Summary", "🎯 Missed Tracker"
])

# ══════════════════════════════════════════════════════════
# TAB 1 — SUBJECTS
# ══════════════════════════════════════════════════════════
with tab1:
    st.subheader("Build Your Subjects")
    fk = st.session_state.form_key

    with st.expander("➕ Add a new subject", expanded=len(st.session_state.subjects) == 0):
        col1, col2 = st.columns(2)
        with col1:
            new_subject_name = st.text_input("Subject name", placeholder="e.g. Math", key=f"subj_name_{fk}")
        with col2:
            new_subject_priority = st.slider("Base priority", 1, 5, 3, key=f"subj_pri_{fk}")

        st.markdown("**Topics**")
        num_topics = st.number_input("How many topics?", 1, 20, 2, key=f"num_topics_{fk}")
        topics_input = []
        for i in range(int(num_topics)):
            st.markdown(f"*Topic {i+1}*")
            c1, c2, c3 = st.columns(3)
            with c1:
                tname = st.text_input("Name", key=f"tname_{fk}_{i}", placeholder="e.g. Algebra")
            with c2:
                tdiff = st.selectbox("Difficulty", ["easy", "medium", "hard"], key=f"tdiff_{fk}_{i}")
            with c3:
                tenergy = st.selectbox("Energy", ["low", "medium", "high"], key=f"tenergy_{fk}_{i}")
            topics_input.append({"name": tname, "difficulty": tdiff, "energy": tenergy, "completed": False})

        if st.button("Add Subject", type="primary", key=f"add_subj_{fk}"):
            if not new_subject_name.strip():
                st.error("Enter a subject name")
            elif any(t["name"].strip() == "" for t in topics_input):
                st.error("Fill in all topic names")
            else:
                st.session_state.subjects.append({
                    "name": new_subject_name.strip(),
                    "base_priority": new_subject_priority,
                    "priority": new_subject_priority,
                    "missed": 0,
                    "topics": topics_input
                })
                save_state(st.session_state.subjects)
                st.session_state.form_key += 1
                st.success(f"Added {new_subject_name.strip()}")
                st.rerun()

    if st.session_state.subjects:
        st.divider()
        st.subheader("Your Subjects")
        for i, subj in enumerate(st.session_state.subjects):
            with st.expander(f"**{subj['name']}** — priority {round(subj['priority'],1)} | missed {subj['missed']} times"):
                rows = [{"Topic": t["name"], "Difficulty": t["difficulty"], "Energy": t["energy"]} for t in subj["topics"]]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                if st.button(f"Remove {subj['name']}", key=f"remove_{i}"):
                    st.session_state.subjects.pop(i)
                    save_state(st.session_state.subjects)
                    st.rerun()
    else:
        st.info("No subjects yet — add one above")

# ══════════════════════════════════════════════════════════
# TAB 2 — PLAN
# ══════════════════════════════════════════════════════════
with tab2:
    st.subheader("Weekly Plan")

    if not st.session_state.subjects:
        st.warning("Add subjects first")
    else:
        week_type = st.radio("Week structure", ["Default (Mon-Sat 2h, Sun 4h)", "Custom"])
        if week_type.startswith("Default"):
            day_types = ["weekday"] * 6 + ["sunday"]
        else:
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_types = []
            cols = st.columns(7)
            for j, (col, name) in enumerate(zip(cols, day_names)):
                with col:
                    choice = st.selectbox(name, ["weekday", "sunday"], key=f"day_{j}")
                    day_types.append(choice)

        if st.button("🗓️ Generate Plan", type="primary", use_container_width=True):
            subjects_copy = copy.deepcopy(st.session_state.subjects)
            plan = generate_plan(subjects_copy, day_types)

            total_topics_time = sum(
                sum(45 if t.get("difficulty")=="easy" else 60 if t.get("difficulty")=="medium" else 90 for t in s["topics"])
                for s in st.session_state.subjects
            )
            total_available = sum(120 if d == "weekday" else 240 for d in day_types)

            if total_topics_time > total_available:
                overflow_mins = total_topics_time - total_available
                st.warning(f"⚠️ Responsible AI: {overflow_mins//60}h {overflow_mins%60}m of work won't fit this week. Consider carrying topics to next week.")

            st.session_state.plan = plan
            st.session_state.task_status = {}
            st.session_state.active_timer = None
            st.session_state.summary = generate_weekly_summary(st.session_state.subjects, plan, st.session_state.missed)
            st.success("Plan generated")

        if st.session_state.plan:
            st.divider()

            # timer widget
            st.markdown("### ⏱️ Focus Timer")
            timer_col1, timer_col2, timer_col3 = st.columns([2, 1, 1])
            with timer_col1:
                timer_mins = st.number_input("Minutes", 1, 120, 25, key="timer_input")
            with timer_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("▶ Start Timer"):
                    st.session_state.active_timer = timer_mins * 60
            with timer_col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("⏹ Stop"):
                    st.session_state.active_timer = None

            if st.session_state.active_timer is not None:
                mins = st.session_state.active_timer // 60
                secs = st.session_state.active_timer % 60
                st.markdown(
                    f'<div class="timer-display">{mins:02d}:{secs:02d}</div>',
                    unsafe_allow_html=True
                )
                st.caption("Timer runs while page is open. Use browser tab to track.")

            st.divider()

            for day, tasks in st.session_state.plan.items():
                if not tasks:
                    continue

                day_keys = [f"{day}_{i}" for i in range(len(tasks))]
                done_in_day = sum(1 for k in day_keys if st.session_state.task_status.get(k) == "done")
                total_in_day = len(tasks)
                progress = done_in_day / total_in_day if total_in_day > 0 else 0

                with st.expander(f"📅 {day}  —  {done_in_day}/{total_in_day} done", expanded=True):
                    st.progress(progress)
                    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                    for t_idx, t in enumerate(tasks):
                        task_key = f"{day}_{t_idx}"
                        status = st.session_state.task_status.get(task_key, "pending")

                        col1, col2, col3 = st.columns([5, 1, 1])
                        with col1:
                            b = badge(t.get("difficulty", "medium"))
                            energy_icon = "⚡" if t.get("energy") == "high" else "〰️" if t.get("energy") == "medium" else "🌙"
                            if status == "done":
                                st.markdown(
                                    f'<div style="opacity:0.45;text-decoration:line-through;color:#9ca3af">'
                                    f'{energy_icon} <b>{t["subject"]}</b> — {t["topic"]} &nbsp;{b}&nbsp; <span style="color:#6b7280">{t["time"]} mins</span></div>',
                                    unsafe_allow_html=True
                                )
                            elif status == "missed":
                                st.markdown(
                                    f'<div style="color:#f87171">'
                                    f'{energy_icon} <b>{t["subject"]}</b> — {t["topic"]} &nbsp;{b}&nbsp; <span style="color:#6b7280">{t["time"]} mins</span> ❌</div>',
                                    unsafe_allow_html=True
                                )
                            else:
                                st.markdown(
                                    f'<div style="color:#e2e8f0">'
                                    f'{energy_icon} <b>{t["subject"]}</b> — {t["topic"]} &nbsp;{b}&nbsp; <span style="color:#6b7280">{t["time"]} mins</span></div>',
                                    unsafe_allow_html=True
                                )
                        with col2:
                            if st.button("✅", key=f"done_{task_key}"):
                                st.session_state.task_status[task_key] = "done"
                                st.rerun()
                        with col3:
                            if st.button("❌", key=f"miss_{task_key}"):
                                st.session_state.task_status[task_key] = "missed"
                                st.session_state.subjects = update_priorities(st.session_state.subjects, [t["subject"]])
                                if t["subject"] not in st.session_state.missed and t["subject"] != "Recovery":
                                    st.session_state.missed.append(t["subject"])
                                save_state(st.session_state.subjects)
                                st.rerun()

            if st.session_state.missed:
                st.divider()
                st.subheader("🔁 Adjusted Plan (with Recovery)")
                adjusted = auto_adjust_plan(copy.deepcopy(st.session_state.plan), st.session_state.missed, st.session_state.subjects)
                for adj_idx, (day, tasks) in enumerate(adjusted.items()):
                    if not tasks:
                        continue
                    with st.expander(f"📅 Day {adj_idx+1} (adjusted)", expanded=True):
                        rows = [{"Band": t.get("band",""), "Subject": t["subject"], "Topic": t["topic"], "Difficulty": t.get("difficulty",""), "Time (mins)": t["time"]} for t in tasks]
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════
# TAB 3 — SUMMARY
# ══════════════════════════════════════════════════════════
with tab3:
    st.subheader("Weekly Summary")

    if not st.session_state.summary:
        st.info("Generate a plan first to see your summary")
    else:
        summary = st.session_state.summary
        total_mins = summary["total_minutes"]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Study Time", f"{total_mins//60}h {total_mins%60}m")
        col2.metric("Tasks Done", f"{done_count}/{total_tasks}")
        col3.metric("Missed", missed_count)
        col4.metric("Streak", f"{streak['current']} 🔥")

        st.divider()

        if summary["by_subject"]:
            st.markdown("**Time per subject**")
            chart_data = pd.DataFrame([
                {"Subject": k, "Minutes": v}
                for k, v in summary["by_subject"].items() if k != "Recovery"
            ])
            fig = px.bar(chart_data, x="Subject", y="Minutes", color="Subject", text="Minutes",
                        color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                             font_color="#c0c0c0")
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.markdown("**Priority trends**")
        trend_data = [{"Subject": t["subject"], "Priority": t["priority"], "Missed Total": t["missed_total"], "Trend": t["trend"]} for t in summary["priority_trends"]]
        st.dataframe(pd.DataFrame(trend_data), use_container_width=True, hide_index=True)

        fig2 = px.bar(pd.DataFrame(trend_data), x="Subject", y="Priority", color="Trend", text="Priority",
                     color_discrete_map={"↑ rising (missed)": "#ef4444", "↓ decaying (consistent)": "#22c55e", "→ stable": "#3b82f6"})
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#c0c0c0")
        fig2.update_traces(textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

        st.divider()
        if st.session_state.plan and st.session_state.subjects:
            bias_warnings = check_bias(st.session_state.subjects, st.session_state.plan)
            if bias_warnings:
                st.subheader("⚠️ Bias Check")
                for w in bias_warnings:
                    st.warning(w["message"])
                st.info("💡 Responsible AI: Flagging subjects getting less than 10% of study time.")
            else:
                st.success("✅ Bias Check passed — all subjects getting fair time.")

# ══════════════════════════════════════════════════════════
# TAB 4 — MISSED TRACKER
# ══════════════════════════════════════════════════════════
with tab4:
    st.subheader("Missed Subject Tracker")

    if not st.session_state.subjects:
        st.warning("Add subjects first")
    else:
        st.markdown("Which subjects did you miss this week?")
        missed_selections = []
        for idx, subj in enumerate(st.session_state.subjects):
            if st.checkbox(f"{subj['name']} (missed {subj['missed']} times total)", key=f"missed_{idx}"):
                missed_selections.append(subj["name"])

        if st.button("✅ Update Missed & Adjust Priorities", type="primary"):
            st.session_state.missed = missed_selections
            st.session_state.subjects = update_priorities(st.session_state.subjects, missed_selections)
            save_state(st.session_state.subjects)
            if missed_selections:
                st.error(f"Marked as missed: {', '.join(missed_selections)}")
                st.info("Priorities updated — regenerate your plan to see changes")
            else:
                st.success("No subjects missed — great week!")

        st.divider()
        st.markdown("**Missed history**")
        history_data = [{"Subject": s["name"], "Times Missed": s["missed"], "Current Priority": round(s["priority"],1), "Base Priority": s["base_priority"]} for s in st.session_state.subjects]
        st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)

        if any(s["missed"] > 0 for s in st.session_state.subjects):
            fig3 = px.bar(pd.DataFrame(history_data), x="Subject", y="Times Missed", color="Subject", text="Times Missed",
                         color_discrete_sequence=px.colors.qualitative.Set1)
            fig3.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#c0c0c0")
            fig3.update_traces(textposition="outside")
            st.plotly_chart(fig3, use_container_width=True)
