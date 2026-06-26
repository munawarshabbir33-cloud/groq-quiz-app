import streamlit as st
import urllib.parse
import json
import pandas as pd
import requests
import random  
from groq import Groq

# 1. Initialization & Keys
api_token = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_token)
N8N_WEBHOOK_URL = "https://hammad2026nustclasses.app.n8n.cloud/webhook/d8e699f0-59ab-4b77-9602-54f16e201939" 

st.set_page_config(page_title="AI Quiz Generator", page_icon="🎯", layout="wide")

# Callback function to instantly clear the screen when a setting is changed!
def reset_quiz():
    st.session_state.current_q_data = None
    st.session_state.answered = False

# 2. Setup Memory (Session States)
if "progress_data" not in st.session_state:
    st.session_state.progress_data = []  
if "current_q_data" not in st.session_state:
    st.session_state.current_q_data = None
if "answered" not in st.session_state:
    st.session_state.answered = False
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "student_name" not in st.session_state:
    st.session_state.student_name = ""
if "student_email" not in st.session_state:
    st.session_state.student_email = ""

# 3. The Strict Onboarding Gate (Login Screen)
if not st.session_state.logged_in:
    st.title("🎯 Welcome to AI Quiz Generator")
    st.markdown("### Please create your session profile to begin.")
    
    name_input = st.text_input("Enter your Full Name:")
    email_input = st.text_input("Enter your Email Address:")
    
    if st.button("Save & Start Quiz 🚀"):
        if name_input.strip() and email_input.strip():
            st.session_state.student_name = name_input
            st.session_state.student_email = email_input
            st.session_state.logged_in = True
            st.rerun()  
        else:
            st.error("Please fill out both your name and email to continue.")
    st.stop()  

# ---------------------------------------------------------
# EVERYTHING BELOW THIS LINE ONLY SHOWS AFTER LOGGING IN
# ---------------------------------------------------------

# 4. Top Bar & Configuration Controls
st.title(f"👋 Welcome, {st.session_state.student_name}!")
st.markdown("---")
st.subheader("📚 Configure Your Study Session")

col_a, col_b, col_c = st.columns(3)

# Notice we added `on_change=reset_quiz` to instantly refresh when you change a setting!
grade_level = col_a.selectbox("Target Grade:", ["Grade 9", "Grade 10", "AS Level", "A Level"], on_change=reset_quiz)
subject = col_b.text_input("Academic Subject:", placeholder="e.g., Physics", on_change=reset_quiz)
topic = col_c.text_input("Topic Area:", placeholder="e.g., Kinematics", on_change=reset_quiz)

study_mode = st.radio("Select Study Mode:", ["Multiple Choice (MCQ)", "Theory"], on_change=reset_quiz)
question_length = "short"
if study_mode == "Theory":
    question_length = st.selectbox("Select Theory Length:", ["Short Question", "Long Question"], on_change=reset_quiz)

# 5. The Core Loop: Generating vs Answering
if st.session_state.current_q_data is None:
    if st.button("Generate Question 🧠"):
        if subject.strip() == "" or topic.strip() == "":
            st.error("Please fill in both Subject and Topic.")
        else:
            with st.spinner("Generating a unique problem..."):
                random_seed = random.randint(1, 100000) 
                
                if study_mode == "Multiple Choice (MCQ)":
                    prompt = f"""
                    You are a professor. Create ONE highly unique multiple choice question for {grade_level} {subject} about {topic}.
                    Randomization Seed: {random_seed}. Do NOT use standard textbook examples. Make it unpredictable.
                    You MUST output ONLY valid JSON format.
                    Format exactly like this: {{"question": "The question text", "A": "Option A text", "B": "Option B text", "C": "Option C text", "D": "Option D text", "correct": "A"}}
                    """
                else:
                    length_inst = "maximum 2 sentences." if question_length == "Short Question" else "a complex, multi-part scenario."
                    prompt = f"""
                    You are a professor. Create ONE highly unique {question_length} for {grade_level} {subject} about {topic}. 
                    Randomization Seed: {random_seed}. Do NOT use standard textbook examples. Make it unpredictable.
                    It must be {length_inst}
                    You MUST output ONLY valid JSON format.
                    Format exactly like this: {{"question": "The question text"}}
                    """

                try:
                    # Added response_format={"type": "json_object"} to force perfect JSON output
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.9,
                        response_format={"type": "json_object"} 
                    )
                    
                    raw_text = response.choices[0].message.content.strip()
                    
                    # Bulletproof JSON extractor (looks only for data between { and })
                    start_idx = raw_text.find('{')
                    end_idx = raw_text.rfind('}')
                    if start_idx != -1 and end_idx != -1:
                        clean_json = raw_text[start_idx:end_idx+1]
                    else:
                        clean_json = raw_text
                        
                    st.session_state.current_q_data = json.loads(clean_json)
                    st.session_state.current_q_data['type'] = study_mode
                    st.session_state.answered = False
                    st.rerun() 
                except Exception as e:
                    st.error(f"Network formatting error. Please click generate again.")

else:
    st.markdown("---")
    st.subheader("📋 Question:")
    st.info(st.session_state.current_q_data["question"])
    
    q_data = st.session_state.current_q_data
    search_query = urllib.parse.quote(f"{subject} {topic} answer explanation")
    study_link = f"https://www.google.com/search?q={search_query}"

    if not st.session_state.answered:
        if q_data['type'] == "Multiple Choice (MCQ)":
            user_choice = st.radio("Select your answer:", ["A", "B", "C", "D"], format_func=lambda x: f"{x}) {q_data[x]}")
            
            if st.button("Submit Answer"):
                correct_ans = q_data["correct"]
                score = 100 if user_choice == correct_ans else
