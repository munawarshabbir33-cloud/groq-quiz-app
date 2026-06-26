import streamlit as st
import urllib.parse
import json
import pandas as pd
import requests
from groq import Groq

# 1. Initialization & Keys
api_token = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_token)

# Provide your n8n Webhook URL here to enable the email feature
N8N_WEBHOOK_URL = "https://hammad2026nustclasses.app.n8n.cloud/webhook/d8e699f0-59ab-4b77-9602-54f16e201939" 

st.set_page_config(page_title="AI Quiz Generator", page_icon="🎯", layout="wide")

# 2. Setup Memory (Session States)
if "progress_data" not in st.session_state:
    st.session_state.progress_data = []  # Stores the spreadsheet data
if "current_q_data" not in st.session_state:
    st.session_state.current_q_data = None
if "answered" not in st.session_state:
    st.session_state.answered = False

# 3. Student Onboarding (Top Bar)
st.title("🎯 Advanced AI LMS & Quiz Generator")
with st.expander("👤 Student Profile & Settings", expanded=True):
    col1, col2 = st.columns(2)
    student_name = col1.text_input("Enter your Full Name:")
    student_email = col2.text_input("Enter your Email Address:")

if not student_name or not student_email:
    st.warning("Please enter your name and email above to start tracking your progress.")
    st.stop()  # Pauses the app until the user logs in

# 4. Configuration Controls
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

# 5. Question Generation Logic
if st.button("Generate Question") or (st.session_state.answered and st.button("Next Question ⏭️")):
    if subject.strip() == "" or topic.strip() == "":
        st.error("Please fill in Subject and Topic.")
    else:
        st.session_state.answered = False # Reset answering state
        st.session_state.current_q_data = None # Clear old question
        
        with st.spinner("Generating problem..."):
            if study_mode == "Multiple Choice (MCQ)":
                prompt = f"""
                You are a professor. Create ONE multiple choice question for {grade_level} {subject} about {topic}.
                You MUST output ONLY valid JSON in this exact format, nothing else:
                {{"question": "The question text", "A": "Option A text", "B": "Option B text", "C": "Option C text", "D": "Option D text", "correct": "A"}}
                """
            else:
                length_instruction = "maximum 2 sentences." if question_length == "Short Question" else "a complex, multi-part paragraph scenario."
                prompt = f"""
                You are a professor. Create ONE {question_length} for {grade_level} {subject} about {topic}. 
                It must be {length_instruction}
                You MUST output ONLY valid JSON in this exact format, nothing else:
                {{"question": "The question text"}}
                """

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            # Parse the JSON response
            try:
                raw_text = response.choices[0].message.content.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                st.session_state.current_q_data = json.loads(raw_text)
                st.session_state.current_q_data['type'] = study_mode
            except:
                st.error("Failed to generate question perfectly. Please click generate again.")

# 6. Display Question & Grading Loop
if st.session_state.current_q_data and not st.session_state.answered:
    st.markdown("---")
    st.subheader("📋 Question:")
    st.info(st.session_state.current_q_data["question"])
    
    q_data = st.session_state.current_q_data
    search_query = urllib.parse.quote(f"{subject} {topic} answer explanation")
    study_link = f"[https://www.google.com/search?q=](https://www.google.com/search?q=){search_query}"

    # --- MCQ LOGIC ---
    if q_data['type'] == "Multiple Choice (MCQ)":
        user_choice = st.radio("Select your answer:", ["A", "B", "C", "D"], format_func=lambda x: f"{x}) {q_data[x]}")
        
        if st.button("Submit Answer"):
            st.session_state.answered = True
            correct_ans = q_data["correct"]
            
            # Save progress
            score = 100 if user_choice == correct_ans else 0
            st.session_state.progress_data.append({"Subject": subject, "Topic": topic, "Score": score})
            
            # Display colored boxes
            for opt in ["A", "B", "C", "D"]:
                text = f"{opt}) {q_data[opt]}"
                if opt == correct_ans:
                    st.markdown(f"<div style='background-color:#d4edda; padding:10px; border-radius:5px; color:#155724;'>✅ <b>{text}</b> (Correct)</div>", unsafe_allow_html=True)
                elif opt == user_choice and user_choice != correct_ans:
                    st.markdown(f"<div style='background-color:#f8d7da; padding:10px; border-radius:5px; color:#721c24;'>❌ <b>{text}</b> (Your Answer)</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='padding:10px;'>{text}</div>", unsafe_allow_html=True)
            
            st.markdown(f"**📚 Study Link:** [Click here to review {topic}]({study_link})")

    # --- THEORY LOGIC ---
    else:
        student_answer = st.text_area("Type your answer:")
        if st.button("Submit Answer"):
            if student_answer.strip() == "":
                st.error("Please type an answer.")
            else:
                st.session_state.answered = True
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
                        
                        if score == 100:
                            st.success(f"✅ CORRECT: {eval_json['explanation']}")
                            st.markdown(f"**📚 Explore More:** [Read about {topic}]({study_link})")
                        else:
                            st.error(f"❌ INCORRECT: {eval_json['explanation']}")
                            st.markdown(f"**📚 Needs review?** [Click here for the correct theory on {topic}]({study_link})")
                    except:
                        st.error("Grading system encountered a formatting error.")

# 7. Provide the "Next" Button after answering
if st.session_state.answered:
    st.button("Next Question ⏭️", key="next_btn")

# 8. Student Progress Tracker & Graph
if len(st.session_state.progress_data) > 0:
    st.markdown("---")
    st.header("📈 Your Progress Dashboard")
    
    df = pd.DataFrame(st.session_state.progress_data)
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Grade Trajectory")
        # Creates a line chart showing if scores are increasing or decreasing
        st.line_chart(df["Score"]) 
        
    with col_right:
        st.subheader("Subject Averages")
        avg_df = df.groupby('Subject')['Score'].mean().reset_index()
        st.dataframe(avg_df, use_container_width=True)
    
    # 9. Send to n8n to Email the Spreadsheet
    if st.button("📧 Email My Progress Report"):
        payload = {
            "name": student_name,
            "email": student_email,
            "averages": avg_df.to_dict('records'),
            "history": st.session_state.progress_data
        }
        try:
            # Sends the data to your n8n workflow
            requests.post(N8N_WEBHOOK_URL, json=payload)
            st.success(f"Spreadsheet data sent successfully to {student_email} via n8n!")
        except Exception as e:
            st.error("Could not reach n8n webhook. Make sure your URL is configured.")
