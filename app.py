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
N8N_WEBHOOK_URL = "https://hammad2026nustclasses.app.n8n.cloud/webhook/d8e699f0-59ab-4b77-9602-54f16e201939" 

# Set up the page layout
st.set_page_config(page_title="AI Quiz Generator", page_icon="🎯", layout="wide")

# ==========================================
# 2. CUSTOM BACKGROUND IMAGE (CSS)
# ==========================================
# A dynamic, quiz-themed background image (Question Marks)
background_image_url = "https://images.unsplash.com/photo-1606326608606-aa0b62935f2b?q=80&w=1920"

page_bg_img = f"""
<style>
/* 1. This anchors the background to the absolute root of the entire webpage */
.stApp {{
    background-image: url("{background_image_url}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    background-repeat: no-repeat;
}}

/* 2. Makes the top header bar transparent so it doesn't block the image */
header[data-testid="stHeader"] {{
    background: transparent !important;
}}

/* 3. The main content box: Slightly transparent white (85% opacity) so text is highly readable, but the background is always visible behind it */
.block-container {{
    background-color: rgba(255, 255, 255, 0.85); 
    padding: 3rem !important;
    border-radius: 15px;
    box-shadow: 0px 8px 20px rgba(0, 0, 0, 0.3);
    margin-top: 2rem;
    margin-bottom: 2rem;
}}
</style>
"""
st.markdown(page_bg_img, unsafe_allow_html=True)

# ==========================================
# 3. HELPER FUNCTIONS & SESSION STATES
# ==========================================
def reset_quiz():
    """Instantly clears the board if a user changes the subject or topic."""
    st.session_state.current_q_data = None
    st.session_state.answered = False

if "progress_data" not in st.session_state: st.session_state.progress_data = []  
if "current_q_data" not in st.session_state: st.session_state.current_q_data = None
if "answered" not in st.session_state: st.session_state.answered = False
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "student_name" not in st.session_state: st.session_state.student_name = ""
if "student_email" not in st.session_state: st.session_state.student_email = ""

# ==========================================
# 4. SECURE LOGIN GATE
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
    st.stop()

# ==========================================
# 5. DASHBOARD & CONFIGURATION
# ==========================================
st.title(f"👋 Welcome, {st.session_state.student_name}!")
st.markdown("---")
st.subheader("📚 Configure Your Study Session")

col_a, col_b, col_c = st.columns(3)
# Set AS Level as the default option by setting index=2
grade_level = col_a.selectbox("Target Grade:", ["Grade 9", "Grade 10", "AS Level", "A Level"], index=2, on_change=reset_quiz)
subject = col_b.text_input("Academic Subject:", placeholder="e.g., Physics", on_change=reset_quiz)
topic = col_c.text_input("Topic Area:", placeholder="e.g., Kinematics", on_change=reset_quiz)

study_mode = st.radio("Select Study Mode:", ["Multiple Choice (MCQ)", "Theory"], on_change=reset_quiz)
question_length = "short"
if study_mode == "Theory":
    question_length = st.selectbox("Select Theory Length:", ["Short Question", "Long Question"], on_change=reset_quiz)

# ==========================================
# 6. QUESTION GENERATION ENGINE
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
                    You are an expert academic professor. Create ONE unique, challenging, and factually accurate multiple choice question for {grade_level} {subject} on {topic}.
                    Seed: {random_seed}.
                    CRITICAL RULES:
                    1. The correct answer MUST be absolutely factually correct.
                    2. The other 3 options MUST be plausible distractors related to the topic, but factually incorrect.
                    3. Randomly assign the correct answer to A, B, C, or D. DO NOT constantly make the answer A or B. It must be randomized.
                    4. EVERY option must have descriptive text content. No blank options.
                    You MUST output ONLY valid JSON format exactly like this:
                    {{"question": "Question text here?", "A": "First option text", "B": "Second option text", "C": "Third option text", "D": "Fourth option text", "correct": "C"}}
                    """
                else:
                    length_inst = "maximum 2 sentences." if question_length == "Short Question" else "a complex, multi-part scenario."
                    prompt = f"""
                    You are an expert academic professor. Create ONE factually accurate {question_length} for {grade_level} {subject} about {topic}. 
                    Seed: {random_seed}. It must be {length_inst}
                    You MUST output ONLY valid JSON format exactly like this: 
                    {{"question": "The question text"}}
                    """

                try:
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.8,
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
# 7. ACTIVE QUIZ & GRADING LOOP
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
            user_choice = st.radio(
                "Select your answer:", 
                ["A", "B", "C", "D"], 
                format_func=lambda x: f"{x}) {q_data.get(x, 'Error: Option text missing')}", 
                key="mcq_radio"
            )
            
            if st.button("Submit Answer ✔️", type="primary"):
                correct_ans = q_data.get("correct", "A") # Fallback to A if missing
                score = 100 if user_choice == correct_ans else 0
                st.session_state.progress_data.append({"Subject": subject, "Topic": topic, "Score": score})
                st.session_state.user_choice = user_choice 
                st.session_state.answered = True
                st.rerun() 
                
        else: # Theory Mode
            student_answer = st.text_area("Type your answer below:", key="theory_text")
            
            if st.button("Submit Answer ✔️", type="primary"):
                if student_answer.strip() == "":
                    st.error("⚠️ Please type an answer before submitting.")
                else:
                    with st.spinner("AI Professor is grading your answer..."):
                        eval_prompt = f"""
                        Evaluate this answer for correctness. 
                        Question: {q_data['question']}
                        Student Answer: {student_answer}
                        You MUST output ONLY valid JSON format exactly like this:
                        {{"verdict": "CORRECT", "explanation": "1 sentence explanation."}}
                        Or if wrong: {{"verdict": "INCORRECT", "explanation": "1 sentence explanation of the right answer."}}
                        """
                        try:
                            eval_resp = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{"role": "user", "content": eval_prompt}],
                                temperature=0.1,
                                response_format={"type": "json_object"}
                            )
                            
                            eval_text = eval_resp.choices[0].message.content
                            start_idx = eval_text.find('{')
                            end_idx = eval_text.rfind('}')
                            clean_eval = eval_text[start_idx:end_idx+1] if start_idx != -1 else eval_text
                            
                            eval_json = json.loads(clean_eval)
                            score = 100 if eval_json.get("verdict", "") == "CORRECT" else 0
                            
                            st.session_state.progress_data.append({"Subject": subject, "Topic": topic, "Score": score})
                            st.session_state.theory_eval = eval_json 
                            st.session_state.answered = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Grading system crashed. Reason: {e}")

    # --- STATE B: SHOWING RESULTS ---
    if st.session_state.answered:
        score = st.session_state.progress_data[-1]["Score"] 
        
        if score == 100:
            st.balloons()
            st.markdown("<h1 style='text-align: center;'>😊 Excellent Work!</h1>", unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='text-align: center;'>😢 Keep Trying!</h1>", unsafe_allow_html=True)
            
        if q_data['type'] == "Multiple Choice (MCQ)":
            correct_ans = q_data.get("correct", "A")
            user_choice = st.session_state.user_choice
            
            # Draw the colored boxes
            for opt in ["A", "B", "C", "D"]:
                text = f"{opt}) {q_data.get(opt, '')}"
                if opt == correct_ans:
                    st.markdown(f"<div style='background-color:#d4edda; padding:10px; border-radius:5px; color:#155724; border: 1px solid #c3e6cb; margin:5px 0;'>✅ <b>{text}</b> (Correct Answer)</div>", unsafe_allow_html=True)
                elif opt == user_choice and user_choice != correct_ans:
                    st.markdown(f"<div style='background-color:#f8d7da; padding:10px; border-radius:5px; color:#721c24; border: 1px solid #f5c6cb; margin:5px 0;'>❌ <b>{text}</b> (Your Answer)</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='background-color:#f8f9fa; padding:10px; border-radius:5px; color:#383d41; border: 1px solid #e2e3e5; margin:5px 0;'>{text}</div>", unsafe_allow_html=True)
        else:
            eval_json = st.session_state.theory_eval
            if score == 100:
                st.success(f"{eval_json.get('explanation', 'Correct!')}")
            else:
                st.error(f"{eval_json.get('explanation', 'Incorrect.')}")
                
        st.markdown(f"**📚 Study Link:** [Click here to review {topic}]({study_link})")
        st.markdown("---")
        
        if st.button("Next Question ⏭️", type="primary"):
            st.session_state.current_q_data = None
            st.session_state.answered = False
            st.rerun() 

# ==========================================
# 8. PROGRESS GRAPH & EXPORT DASHBOARD
# ==========================================
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
