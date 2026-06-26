import streamlit as st
import urllib.parse
import json
import pandas as pd
import requests
import random  
from groq import Groq

# ==========================================
# 1. INITIALIZATION & API SETUP
# ==========================================
api_token = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_token)
N8N_WEBHOOK_URL = "https://your-n8n-webhook-url-here" 

st.set_page_config(page_title="AI Quiz Generator", page_icon="🎯", layout="wide")

def reset_quiz():
    """Instantly clears the board if a user changes the subject or topic."""
    st.session_state.current_q_data = None
    st.session_state.answered = False

# ==========================================
# 2. MEMORY & SESSION STATES
# ==========================================
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

# ==========================================
# 3. SECURE LOGIN GATE
# ==========================================
if not st.session_state.logged_in:
    st.title("🎯 Welcome to AI Quiz Generator")
    st.markdown("### Please create your session profile to begin.")
    
    with st.container():
        name_input = st.text_input("Enter your Full Name:", key="login_name")
        email_input = st.text_input("Enter your Email Address:", key="login_email")
        
        if st.button("Save & Start Quiz 🚀", type="primary"):
            if name_input.strip() and email_input.strip():
                st.session_state.student_name = name_input
                st.session_state.student_email = email_input
                st.session_state.logged_in = True
                st.rerun()  
            else:
                st.error("Please fill out both your name and email to continue.")
    st.stop()  # Stops the rest of the app from loading until logged in

# ==========================================
# 4. DASHBOARD & CONFIGURATION
# ==========================================
st.title(f"👋 Welcome, {st.session_state.student_name}!")
st.markdown("---")
st.subheader("📚 Configure Your Study Session")

col_a, col_b, col_c = st.columns(3)
grade_level = col_a.selectbox("Target Grade:", ["Grade 9", "Grade 10", "AS Level", "A Level"], on_change=reset_quiz)
subject = col_b.text_input("Academic Subject:", placeholder="e.g., Physics", on_change=reset_quiz)
topic = col_c.text_input("Topic Area:", placeholder="e.g., Kinematics", on_change=reset_quiz)

study_mode = st.radio("Select Study Mode:", ["Multiple Choice (MCQ)", "Theory"], on_change=reset_quiz)
question_length = "short"
if study_mode == "Theory":
    question_length = st.selectbox("Select Theory Length:", ["Short Question", "Long Question"], on_change=reset_quiz)

# ==========================================
# 5. QUESTION GENERATION ENGINE
# ==========================================
if st.session_state.current_q_data is None:
    if st.button("Generate Question 🧠", type="primary"):
        if subject.strip() == "" or topic.strip() == "":
            st.error("Please fill in both Subject and Topic before generating.")
        else:
            with st.spinner("Analyzing curriculum and generating a unique problem..."):
                random_seed = random.randint(1, 100000) 
                
                if study_mode == "Multiple Choice (MCQ)":
                    prompt = f"""
                    You are a professor. Create ONE highly unique multiple choice question for {grade_level} {subject} about {topic}.
                    Randomization Seed: {random_seed}. Make it unpredictable.
                    You MUST output ONLY valid JSON format.
                    Format exactly like this: {{"question": "The question text", "A": "Option A text", "B": "Option B text", "C": "Option C text", "D": "Option D text", "correct": "A"}}
                    """
                else:
                    length_inst = "maximum 2 sentences." if question_length == "Short Question" else "a complex, multi-part scenario."
                    prompt = f"""
                    You are a professor. Create ONE highly unique {question_length} for {grade_level} {subject} about {topic}. 
                    Randomization Seed: {random_seed}. Make it unpredictable. It must be {length_inst}
                    You MUST output ONLY valid JSON format.
                    Format exactly like this: {{"question": "The question text"}}
                    """

                try:
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.9,
                        response_format={"type": "json_object"} 
                    )
                    
                    raw_text = response.choices[0].message.content.strip()
                    start_idx = raw_text.find('{')
                    end_idx = raw_text.rfind('}')
                    clean_json = raw_text[start_idx:end_idx+1] if start_idx != -1 else raw_text
                        
                    st.session_state.current_q_data = json.loads(clean_json)
                    st.session_state.current_q_data['type'] = study_mode
                    st.session_state.answered = False
                    st.rerun() 
                except Exception as e:
                    st.error(f"Network error while generating question: {e}")

# ==========================================
# 6. ACTIVE QUIZ & GRADING LOOP
# ==========================================
else:
    st.markdown("---")
    st.subheader("📋 Question:")
    st.info(st.session_state.current_q_data["question"])
    
    q_data = st.session_state.current_q_data
    search_query = urllib.parse.quote(f"{subject} {topic} answer explanation")
    study_link = f"https://www.google.com/search?q={search_query}"

    # --- STATE A: WAITING FOR STUDENT TO ANSWER ---
    if not st.session_state.answered:
        
        if q_data['type'] == "Multiple Choice (MCQ)":
            # Added a unique 'key' so Streamlit never forgets the choice
            user_choice = st.radio("Select your answer:", ["A", "B", "C", "D"], format_func=lambda x: f"{x}) {q_data[x]}", key="mcq_radio")
            
            if st.button("Submit Answer ✔️"):
                correct_ans = q_data["correct"]
                score = 100 if user_choice == correct_ans else 0
                st.session_state.progress_data.append({"Subject": subject, "Topic": topic, "Score": score})
                st.session_state.user_choice = user_choice 
                st.session_state.answered = True
                st.rerun() 
                
        else: # Theory Mode
            # Added a unique 'key' so Streamlit never forgets the text
            student_answer = st.text_area("Type your answer below:", key="theory_text")
            
            if st.button("Submit Answer ✔️"):
                if student_answer.strip() == "":
                    st.
