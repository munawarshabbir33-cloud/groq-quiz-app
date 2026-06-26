import streamlit as st
import urllib.parse
import json
import pandas as pd
import requests
import random  # Added to fix duplicate questions
from groq import Groq

# 1. Initialization & Keys
api_token = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_token)
N8N_WEBHOOK_URL = "https://your-n8n-webhook-url-here" 

st.set_page_config(page_title="AI Quiz Generator", page_icon="🎯", layout="wide")

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
    
    # Simple, locked form layout
    name_input = st.text_input("Enter your Full Name:")
    email_input = st.text_input("Enter your Email Address:")
    
    if st.button("Save & Start Quiz 🚀"):
        if name_input.strip() and email_input.strip():
            # Save data and unlock the app
            st.session_state.student_name = name_input
            st.session_state.student_email = email_input
            st.session_state.logged_in = True
            st.rerun()  # Instantly refreshes the screen to hide login
        else:
            st.error("Please fill out both your name and email to continue.")
            
    st.stop()  # Completely stops the rest of the app from loading until logged in!

# ---------------------------------------------------------
# EVERYTHING BELOW THIS LINE ONLY SHOWS AFTER LOGGING IN
# ---------------------------------------------------------

# 4. Top Bar & Configuration Controls
st.title(f"👋 Welcome, {st.session_state.student_name}!")
st.markdown("---")
st.subheader("📚 Configure Your Study Session")

col_a, col_b, col_c = st.columns(3)
grade_level = col_a.selectbox("Target Grade:", ["Grade 9", "Grade 10", "AS Level", "A Level"])
subject = col_b.text_input("Academic Subject:", placeholder="e.g., Physics")
topic = col_c.text_input("Topic Area:", placeholder="e.g., Kinematics")

study_mode = st.radio("Select Study Mode:", ["Multiple Choice (MCQ)", "Theory"])
question_length = "short"
if study_mode == "Theory":
    question_length = st.selectbox("Select Theory Length:", ["Short Question", "Long Question"])

# 5. The Core Loop: Generating vs Answering
if st.session_state.current_q_data is None:
    # State A: No question currently active. Show the Generate button.
    if st.button("Generate Question 🧠"):
        if subject.strip() == "" or topic.strip() == "":
            st.error("Please fill in both Subject and Topic.")
        else:
            with st.spinner("Generating a unique problem..."):
                # We inject a random number to force the AI to write a completely new question every time
                random_seed = random.randint(1, 100000) 
                
                if study_mode == "Multiple Choice (MCQ)":
                    prompt = f"""
                    You are a professor. Create ONE highly unique multiple choice question for {grade_level} {subject} about {topic}.
                    Randomization Seed: {random_seed}. Do NOT use standard textbook examples. Make it unpredictable.
                    You MUST output ONLY valid JSON in this exact format, nothing else:
                    {{"question": "The question text", "A": "Option A text", "B": "Option B text", "C": "Option C text", "D": "Option D text", "correct": "A"}}
                    """
                else:
                    length_inst = "maximum 2 sentences." if question_length == "Short Question" else "a complex, multi-part scenario."
                    prompt = f"""
                    You are a professor. Create ONE highly unique {question_length} for {grade_level} {subject} about {topic}. 
                    Randomization Seed: {random_seed}. Do NOT use standard textbook examples. Make it unpredictable.
                    It must be {length_inst}
                    You MUST output ONLY valid JSON in this exact format, nothing else:
                    {{"question": "The question text"}}
                    """

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.9 # Increased temperature for more creativity
                )
                
                try:
                    raw_text = response.choices[0].message.content.strip()
                    if raw_text.startswith("```json"):
                        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                    st.session_state.current_q_data = json.loads(raw_text)
                    st.session_state.current_q_data['type'] = study_mode
                    st.session_state.answered = False
                    st.rerun() # Refresh to show the question cleanly
                except:
                    st.error("Failed to format question. Please click generate again.")

else:
    # State B: A question is currently active.
    st.markdown("---")
    st.subheader("📋 Question:")
    st.info(st.session_state.current_q_data["question"])
    
    q_data = st.session_state.current_q_data
    search_query = urllib.parse.quote(f"{subject} {topic} answer explanation")
    study_link = f"[https://www.google.com/search?q=](https://www.google.com/search?q=){search_query}"

    # If the user HAS NOT submitted an answer yet
    if not st.session_state.answered:
        if q_data['type'] == "Multiple Choice (MCQ)":
            user_choice = st.radio("Select your answer:", ["A", "B", "C", "D"], format_func=lambda x: f"{x}) {q_data[x]}")
            
            if st.button("Submit Answer"):
                correct_ans = q_data["correct"]
                score = 100 if user_choice == correct_ans else 0
                st.session_state.progress_data.append({"Subject": subject, "Topic": topic, "Score": score})
                st.session_state.user_choice = user_choice # Save their choice to memory
                st.session_state.answered = True
                st.rerun() # Refresh to show the results
                
        else: # Theory Mode
            student_answer = st.text_area("Type your answer:")
            if st.button("Submit Answer"):
                if student_answer.strip() == "":
                    st.error("Please type an answer.")
                else:
                    with st.spinner("Grading..."):
                        eval_prompt = f"""Evaluate this answer for correctness. Question: {q_data['question']}. Answer: {student_answer}.
                        Output ONLY valid JSON: {{"verdict": "CORRECT" or "INCORRECT", "explanation": "1 sentence explanation"}}"""
                        
                        eval_resp = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": eval_prompt}],
                            temperature=0.1
                        )
                        try:
                            eval_text = eval_resp.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                            eval_json = json.loads(eval_text)
                            
                            score = 100 if eval_json["verdict"] == "CORRECT" else 0
                            st.session_state.progress_data.append({"Subject": subject, "Topic": topic, "Score": score})
                            st.session_state.theory_eval = eval_json # Save evaluation to memory
                            st.session_state.answered = True
                            st.rerun()
                        except:
                            st.error("Grading system encountered a formatting error.")

    # If the user HAS submitted an answer, show results and the NEXT button
    if st.session_state.answered:
        score = st.session_state.progress_data[-1]["Score"] # Look at the most recent score
        
        if score == 100:
            st.balloons()
            st.markdown("<h1 style='text-align: center;'>😊 Excellent Work!</h1>", unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='text-align: center;'>😢 Keep Trying!</h1>", unsafe_allow_html=True)
            
        if q_data['type'] == "Multiple Choice (MCQ)":
            correct_ans = q_data["correct"]
            user_choice = st.session_state.user_choice
            for opt in ["A", "B", "C", "D"]:
                text = f"{opt}) {q_data[opt]}"
                if opt == correct_ans:
                    st.markdown(f"<div style='background-color:#d4edda; padding:10px; border-radius:5px; color:#155724; margin:5px 0;'>✅ <b>{text}</b> (Correct)</div>", unsafe_allow_html=True)
                elif opt == user_choice and user_choice != correct_ans:
                    st.markdown(f"<div style='background-color:#f8d7da; padding:10px; border-radius:5px; color:#721c24; margin:5px 0;'>❌ <b>{text}</b> (Your Answer)</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='padding:10px; margin:5px 0;'>{text}</div>", unsafe_allow_html=True)
        else:
            eval_json = st.session_state.theory_eval
            if score == 100:
                st.success(f"{eval_json['explanation']}")
            else:
                st.error(f"{eval_json['explanation']}")
                
        st.markdown(f"**📚 Study Link:** [Click here to review {topic}]({study_link})")
        st.markdown("---")
        
        # EXACTLY ONE Next Question Button
        if st.button("Next Question ⏭️", type="primary"):
            st.session_state.current_q_data = None
            st.session_state.answered = False
            st.rerun() # Wipes the slate clean instantly!

# 6. Student Progress Tracker & Graph
if len(st.session_state.progress_data) > 0:
    st.markdown("---")
    st.header("📈 Your Progress Dashboard")
    
    df = pd.DataFrame(st.session_state.progress_data)
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Grade Trajectory")
        st.line_chart(df["Score"]) 
        
    with col_right:
        st.subheader("Subject Averages")
        avg_df = df.groupby('Subject')['Score'].mean().reset_index()
        st.dataframe(avg_df, use_container_width=True)
    
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download My Progress Spreadsheet (CSV)",
        data=csv_data,
        file_name=f"{st.session_state.student_name}_progress_report.csv",
        mime="text/csv"
    )
    
    if st.button("📧 Email My Progress Report & Graph Data"):
        raw_spreadsheet_text = df.to_csv(index=False)
        payload = {
            "name": st.session_state.student_name,
            "email": st.session_state.student_email,
            "averages": avg_df.to_dict('records'),
            "spreadsheet_content": raw_spreadsheet_text,
            "scores_for_graph": df["Score"].tolist()
        }
        try:
            requests.post(N8N_WEBHOOK_URL, json=payload)
            st.success(f"All data successfully transmitted to your automated mail server!")
        except Exception as e:
            st.error("Could not reach n8n webhook. Check your URL.")
