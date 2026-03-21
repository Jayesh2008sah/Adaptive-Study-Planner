import json
import os
import copy
import streamlit as st
import plotly.express as px
import pandas as pd
from planner import (
    generate_plan, auto_adjust_plan, update_priorities,
    generate_weekly_summary, reset_completed_topics, add_topics_to_subject
)

STATE_FILE = "state.json"

st.set_page_config(
    page_title="Adaptive Study Planner",
    page_icon="📚",
    layout="wide"
)

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

if "subjects" not in st.session_state:
    saved = load_state()
    st.session_state.subjects = saved if saved else []
if "plan" not in st.session_state:
    st.session_state.plan = None
if "summary" not in st.session_state:
    st.session_state.summary = None
if "missed" not in st.session_state:
    st.session_state.missed = []

st.title("📚 Adaptive Study Planner")
st.caption("Priority-weighted · Energy-aware · Missed day recovery")
st.divider()

with st.sidebar:
    st.header("⚙️ Controls")
    if st.button("🔄 Reset Everything", use_container_width=True):
        reset_state()
        st.session_state.subjects = []
        st.session_state.plan = None
        st.session_state.summary = None
        st.session_state.missed = []
        st.rerun()
    if st.button("📅 Start New Week", use_container_width=True):
        if st.session_state.subjects:
            st.session_state.subjects = reset_completed_topics(st.session_state.subjects)
            st.session_state.plan = None
            st.session_state.summary = None
            st.session_state.missed = []
            save_state(st.session_state.subjects)
            st.success("New week started — topics reset")
    st.divider()
    st.caption("Your data is saved locally in state.json")

tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Subjects", "📅 Plan", "📊 Summary", "🎯 Missed Tracker"
])

with tab1:
    st.subheader("Build Your Subjects")
    with st.expander("➕ Add a new subject", expanded=len(st.session_state.subjects) == 0):
        col1, col2 = st.columns(2)
        with col1:
            new_subject_name = st.text_input("Subject name", placeholder="e.g. Math")
        with col2:
            new_subject_priority = st.slider("Base priority", 1, 5, 3)
        st.markdown("**Topics**")
        num_topics = st.number_input("How many topics?", 1, 20, 2)
        topics_input = []
        for i in range(int(num_topics)):
            st.markdown(f"*Topic {i+1}*")
            c1, c2, c3 = st.columns(3)
            with c1:
                tname = st.text_input("Name", key=f"tname_{i}", placeholder="e.g. Algebra")
            with c2:
                tdiff = st.selectbox("Difficulty", ["easy", "medium", "hard"], key=f"tdiff_{i}")
            with c3:
                tenergy = st.selectbox("Energy", ["low", "medium", "high"], key=f"tenergy_{i}")
            topics_input.append({
                "name": tname,
                "difficulty": tdiff,
                "energy": tenergy,
                "completed": False
            })
        if st.button("Add Subject", type="primary"):
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
                st.success(f"Added {new_subject_name}")
                st.rerun()

    if st.session_state.subjects:
        st.divider()
        st.subheader("Your Subjects")
        for i, subj in enumerate(st.session_state.subjects):
            with st.expander(
                f"**{subj['name']}** — priority {round(subj['priority'], 1)} | missed {subj['missed']} times"
            ):
                rows = []
                for t in subj["topics"]:
                    rows.append({
                        "Topic": t["name"],
                        "Difficulty": t["difficulty"],
                        "Energy": t["energy"]
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                if st.button(f"Remove {subj['name']}", key=f"remove_{i}"):
                    st.session_state.subjects.pop(i)
                    save_state(st.session_state.subjects)
                    st.rerun()
    else:
        st.info("No subjects yet — add one above")

with tab2:
    st.subheader("Generate Your Weekly Plan")
    if not st.session_state.subjects:
        st.warning("Add subjects first in the Subjects tab")
    else:
        week_type = st.radio("Week structure", ["Default (Mon-Sat 2h, Sun 4h)", "Custom"])
        if week_type.startswith("Default"):
            day_types = ["weekday"] * 6 + ["sunday"]
        else:
            st.markdown("**Set each day**")
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
            st.session_state.plan = plan
            st.session_state.summary = generate_weekly_summary(
                st.session_state.subjects, plan, st.session_state.missed
            )
            st.success("Plan generated")

        if st.session_state.plan:
            st.divider()
            for day, tasks in st.session_state.plan.items():
                if not tasks:
                    continue
                with st.expander(f"📅 {day}", expanded=True):
                    rows = []
                    for t in tasks:
                        rows.append({
                            "Band": t.get("band", ""),
                            "Subject": t["subject"],
                            "Topic": t["topic"],
                            "Difficulty": t.get("difficulty", ""),
                            "Energy": t.get("energy", ""),
                            "Time (mins)": t["time"]
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            if st.session_state.missed:
                st.divider()
                st.subheader("🔁 Adjusted Plan (with Recovery)")
                adjusted = auto_adjust_plan(
                    copy.deepcopy(st.session_state.plan),
                    st.session_state.missed,
                    st.session_state.subjects
                )
                for day, tasks in adjusted.items():
                    if not tasks:
                        continue
                    with st.expander(f"📅 {day} (adjusted)"):
                        rows = []
                        for t in tasks:
                            rows.append({
                                "Band": t.get("band", ""),
                                "Subject": t["subject"],
                                "Topic": t["topic"],
                                "Difficulty": t.get("difficulty", ""),
                                "Time (mins)": t["time"]
                            })
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Weekly Summary")
    if not st.session_state.summary:
        st.info("Generate a plan first to see your summary")
    else:
        summary = st.session_state.summary
        total_mins = summary["total_minutes"]
        total_hours = total_mins // 60
        total_rem = total_mins % 60
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Study Time", f"{total_hours}h {total_rem}m")
        col2.metric("Subjects", len(st.session_state.subjects))
        col3.metric("Missed This Week", len(summary["missed"]))
        st.divider()
        if summary["by_subject"]:
            st.markdown("**Time per subject**")
            chart_data = pd.DataFrame([
                {"Subject": k, "Minutes": v}
                for k, v in summary["by_subject"].items()
                if k != "Recovery"
            ])
            fig = px.bar(
                chart_data, x="Subject", y="Minutes",
                color="Subject", text="Minutes",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
        st.divider()
        st.markdown("**Priority trends**")
        trend_data = []
        for t in summary["priority_trends"]:
            trend_data.append({
                "Subject": t["subject"],
                "Priority": t["priority"],
                "Missed Total": t["missed_total"],
                "Trend": t["trend"]
            })
        st.dataframe(pd.DataFrame(trend_data), use_container_width=True, hide_index=True)
        fig2 = px.bar(
            pd.DataFrame(trend_data),
            x="Subject", y="Priority",
            color="Trend", text="Priority",
            color_discrete_map={
                "↑ rising (missed)": "#ef4444",
                "↓ decaying (consistent)": "#22c55e",
                "→ stable": "#3b82f6"
            }
        )
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        fig2.update_traces(textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

with tab4:
    st.subheader("Missed Subject Tracker")
    if not st.session_state.subjects:
        st.warning("Add subjects first")
    else:
        st.markdown("Which subjects did you miss this week?")
        missed_selections = []
        for idx, subj in enumerate(st.session_state.subjects):
            checked = st.checkbox(
                f"{subj['name']} (missed {subj['missed']} times total)",
                key=f"missed_{idx}"
            )
            if checked:
                missed_selections.append(subj["name"])

        if st.button("✅ Update Missed & Adjust Priorities", type="primary"):
            st.session_state.missed = missed_selections
            st.session_state.subjects = update_priorities(
                st.session_state.subjects, missed_selections
            )
            save_state(st.session_state.subjects)
            if missed_selections:
                st.error(f"Marked as missed: {', '.join(missed_selections)}")
                st.info("Priorities updated — regenerate your plan to see changes")
            else:
                st.success("No subjects missed — great week!")

        st.divider()
        st.markdown("**Missed history**")
        history_data = []
        for subj in st.session_state.subjects:
            history_data.append({
                "Subject": subj["name"],
                "Times Missed": subj["missed"],
                "Current Priority": round(subj["priority"], 1),
                "Base Priority": subj["base_priority"]
            })
        st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)
        if any(s["missed"] > 0 for s in st.session_state.subjects):
            fig3 = px.bar(
                pd.DataFrame(history_data),
                x="Subject", y="Times Missed",
                color="Subject", text="Times Missed",
                color_discrete_sequence=px.colors.qualitative.Set1
            )
            fig3.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
            fig3.update_traces(textposition="outside")
            st.plotly_chart(fig3, use_container_width=True)
