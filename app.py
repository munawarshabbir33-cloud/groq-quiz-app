import streamlit as st
import urllib.parse
import json
import pandas as pd
import requests
import random
from groq import Groq

# 1. Initialization
api_token = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_token)
N8N_WEBHOOK_URL = "https://hammad2026nustclasses.app.n8n.cloud/webhook/d8e699f0-59ab-4b77-9602-54f16e201939" 

st.set_page_config(page_title="AI Quiz Generator", page_icon="🎯", layout="wide")

def reset_quiz():
    st.session_state.current_q_data = None
    st.session_state.answered = False

# 2. Session States
if "progress_data" not in st.session_state: st.session_state.progress_data = []
if "current_q_data" not in st.session_state: st.session_state.current_q_data = None
if "answered" not in st.session_state: st.session_state.answered = False
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "student_name" not in st.session_state: st.session_state.student_name = ""
if "student_email" not in st.session_state: st.session_state.student_email = ""

# 3. Login Screen
if not st.session_state.logged_in:
    st.title("🎯 Welcome to AI Quiz Generator")
    name_input = st.text_input("Enter your Full Name:")
    email_input = st.text_input("Enter your Email Address:")
    if st.button("Save & Start Quiz 🚀"):
        if name_input.strip() and email_input.strip():
            st.session_state.student_name = name_input
            st.session_state.student_email = email_input
            st.session_state.logged_in = True
            st.rerun()
    st.stop()

# 4. Configuration
st.title(f"👋 Welcome, {st.session_state.student_name}!")
col_a, col_b, col_c = st.columns(3)
grade_level = col_a.selectbox("Target Grade:", ["Grade 9", "Grade 10", "AS Level", "A Level"], on_change=reset_quiz)
subject = col_b.text_input("Academic Subject:", on_change=reset_quiz)
topic = col_c.text_input("Topic Area:", on_change=reset_quiz)

study_mode = st.radio("Select Study Mode:", ["Multiple Choice (MCQ)", "Theory"], on_change=reset_quiz)

# 5. Question Generation
if st.session_state.current_q_data is None:
    if st.button("Generate Question 🧠"):
        if not subject or not topic: st.error("Please fill in Subject and Topic.")
        else:
            with st.spinner("Generating..."):
                seed = random.randint(1, 100000)
                prompt = f"Create a unique {study_mode} question for {grade_level} {subject} on {topic}. Seed: {seed}. Output ONLY valid JSON."
                try:
                    res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                    st.session_state.current_q_data = json.loads(res.choices[0].message.content)
                    st.session_state.current_q_data['type'] = study_mode
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# 6. Grading & MCQ Rendering
else:
    st.info(st.session_state.current_q_data.get("question", "No question text found."))
    
    # MCQ Rendering Logic
    if st.session_state.current_q_data['type'] == "Multiple Choice (MCQ)":
        if not st.session_state.answered:
            # Here are your options!
            choice = st.radio("Select your answer:", ["A", "B", "C", "D"], format_func=lambda x: f"{x}) {st.session_state.current_q_data.get(x, '')}")
            if st.button("Submit"):
                st.session_state.user_choice = choice
                st.session_state.answered = True
                score = 100 if choice == st.session_state.current_q_data.get("correct") else 0
                st.session_state.progress_data.append({"Subject": subject, "Topic": topic, "Score": score})
                st.rerun()
        else:
            # Display results
            st.write(f"Your choice: {st.session_state.user_choice}")
            if st.button("Next Question ⏭️"):
                st.session_state.current_q_data = None
                st.session_state.answered = False
                st.rerun()
    
    # Theory Logic
    else:
        if not st.session_state.answered:
            ans = st.text_area("Type answer:")
            if st.button("Submit"):
                st.session_state.answered = True
                st.session_state.progress_data.append({"Subject": subject, "Topic": topic, "Score": 100})
                st.rerun()
        else:
            if st.button("Next Question ⏭️"):
                st.session_state.current_q_data = None
                st.session_state.answered = False
                st.rerun()

# 7. Dashboard
if st.session_state.progress_data:
    st.markdown("---")
    st.header("📈 Progress")
    df = pd.DataFrame(st.session_state.progress_data)
    st.line_chart(df["Score"])
    if st.button("Email Report"):
        requests.post(N8N_WEBHOOK_URL, json={"name": st.session_state.student_name, "email": st.session_state.student_email, "data": df.to_dict()})
        st.success("Sent!")
