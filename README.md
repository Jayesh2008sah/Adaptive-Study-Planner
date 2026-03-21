# Adaptive-Study-Planner
Adaptive study planner with priority weighting, energy-based scheduling, and bias transparency — built with Python &amp; Streamlit
A personal study planner that adapts based on your behavior.

## What it does
- Schedules topics based on priority, energy level, and difficulty
- Increases priority automatically when you miss a subject
- Redistributes missed time across remaining days
- Flags when the algorithm underrepresents a subject (Bias Transparency)

## Tech
- Python, Streamlit, Plotly, Pandas

## How to run
pip install -r requirements.txt
streamlit run app.py

## Responsible AI feature
The planner warns you when any subject gets less than 10% of your 
study time — keeping you in control of the algorithm, not the other way around.
