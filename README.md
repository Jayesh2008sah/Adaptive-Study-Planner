# 📚 Adaptive Study Planner

> A personal study planner that adapts to your behavior — not just your schedule.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red?style=flat-square)
![Responsible AI](https://img.shields.io/badge/Responsible-AI-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## 🧠 What Makes This Different

Most planners just show you a timetable. This one **adapts**.

- Miss a subject? Its priority increases automatically next week.
- Hard topics? Scheduled when your energy is highest.
- One subject dominating your week? The system warns you.

This isn't a to-do app. It's a **dynamic execution system**.

---

## ✨ Features

| Feature | Description |
|---|---|
| ⚡ Priority Weighting | Subjects with higher priority get more time slots automatically |
| 🌙 Energy-Based Scheduling | Hard topics in peak hours, easy topics in low-energy slots |
| 🎯 Difficulty-Aware Timing | Hard = 90 mins, Medium = 60 mins, Easy = 45 mins |
| 🔁 Missed Day Recovery | Miss a subject → time redistributed across remaining days |
| ⚠️ Bias Transparency | Warns when any subject gets less than 10% of study time |
| 🔥 Streak Tracker | Tracks consecutive weeks without missing a subject |
| ⏱️ Focus Timer | Built-in timer for each study session |
| 💾 State Persistence | Priorities and history saved between weeks |
| 🌲 Dark UI | Deep forest dark theme for long study sessions |

---

## 🤖 Responsible AI Features

This project was built with Responsible AI as a core design principle, not an afterthought.

**Bias Transparency** — The planner flags when the scheduling algorithm underrepresents any subject (below 10% of total study time). You stay in control of the algorithm, not the other way around.

**Explainable Decisions** — Priority changes are shown clearly. When a subject's priority increases, you can see exactly why (missed count, base vs current priority).

**Overflow Warning** — If your workload exceeds the week's available hours, the system warns you before generating the plan rather than silently dropping tasks.

---

## 🏗️ Architecture

```
planner.py          → The adaptive engine (core logic)
app.py              → Streamlit web interface
Test.py             → CLI version for terminal use
state.json          → Persisted subject state
streak.json         → Streak tracking data
requirements.txt    → Dependencies
```

### How the engine works

```
Input (subjects + topics + priorities)
    ↓
Priority Weighting → builds weighted pool
    ↓
Energy Sorting → hard topics first, easy last
    ↓
Day Band Assignment → weekday (2h) or sunday (4h)
    ↓
Plan Generated
    ↓
Mark Done / Missed
    ↓
Priorities Updated → missed subjects get +2.5 priority (capped at 10)
    ↓
Next week → system remembers everything
```
---

## 🚀 How to Run

**1. Clone the repo**
```bash
git clone https://github.com/Jayesh2008sah/Adaptive-Study-Planner.git
cd Adaptive-Study-Planner
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Run the web app**
```bash
streamlit run app.py
```

**4. Or run the CLI version**
```bash
python Test.py

---

## 🗺️ Roadmap

- [x] Priority weighting
- [x] Energy-based scheduling
- [x] Difficulty-aware time allocation
- [x] Missed day recovery
- [x] Bias transparency (Responsible AI)
- [x] Streak tracking
- [x] Focus timer
- [x] Dark UI
- [ ] Daily execution loop with done/missed per task
- [ ] Deploy on Streamlit Cloud
- [ ] AI-powered suggestions (pattern recognition after 3+ weeks of data)
- [ ] Mobile app (React Native)

---

## 💡 What I Learned Building This

- Adaptive systems are harder than they look
- Bugs at this level aren't syntax errors — they're flow issues and wrong assumptions
- Product thinking matters more than syntax knowledge
- Responsible AI isn't a feature you bolt on — it's a design decision you make from the start

---

## 📄 License

MIT — free to use, modify, and build on.

---

## 👤 Author

**Jayesh Kumar Sahu**
BCA Student | Python & AI | Interested in Responsible AI

[LinkedIn](www.linkedin.com/in/jayesh-kumar-sahu-370b08380) · [GitHub](https://github.com/Jayesh2008sah)
