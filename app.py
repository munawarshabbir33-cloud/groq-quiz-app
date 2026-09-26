import streamlit as st
import urllib.parse
import json
import pandas as pd
import requests
import random
from groq import Groq

# ==========================================
# 1. PAGE SETUP & APPLE DESIGN SYSTEM (CSS)
# ==========================================
st.set_page_config(
    page_title="AI Quiz Generator | Pro", 
    page_icon="🎯", 
    layout="wide"
)

apple_theme_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* 1. Global Background with Ambient Apple Gradients */
.stApp {
    background-color: #000000 !important;
    background-image: 
        radial-gradient(at 10% 10%, rgba(0, 113, 227, 0.22) 0px, transparent 55%),
        radial-gradient(at 90% 10%, rgba(191, 90, 242, 0.18) 0px, transparent 55%),
        radial-gradient(at 50% 90%, rgba(48, 209, 88, 0.15) 0px, transparent 55%) !important;
    background-attachment: fixed !important;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", sans-serif !important;
    color: #f5f5f7 !important;
}

/* 2. Hide standard Streamlit chrome */
header[data-testid="stHeader"] { display: none !important; }
footer { display: none !important; }

/* 3. Central Glassmorphic Container */
.block-container {
    max-width: 950px !important;
    padding-top: 3rem !important;
    padding-bottom: 4rem !important;
}

/* Smooth Fade-In Animation */
div[data-testid="stVerticalBlock"] > div {
    animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) ease-out;
}

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

/* 4. Typography Gradients */
h1 {
    background: linear-gradient(180deg, #FFFFFF 0%, #86868B 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
}

.apple-gradient-text {
    background: linear-gradient(135deg, #29d8ff 0%, #bf5af2 50%, #30d158 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
}

/* 5. Apple Form Inputs (Frosted Glass) */
.stTextInput > div > div > input, 
.stSelectbox > div > div > div, 
.stTextArea > div > div > textarea {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 14px !important;
    color: #f5f5f7 !important;
    backdrop-filter: blur(20px) !important;
    transition: all 0.3s ease !important;
}

.stTextInput > div > div > input:focus, 
.stSelectbox > div > div > div:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #0071e3 !important;
    box-shadow: 0 0 16px rgba(0, 113, 227, 0.4) !important;
    background: rgba(255, 255, 255, 0.08) !important;
}

/* 6. Apple Pill Buttons with Micro-Interactions */
.stButton > button {
    background: linear-gradient(135deg, #0071e3 0%, #4792f6 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 980px !important;
    padding: 0.75rem 2rem !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    box-shadow: 0 4px 15px rgba(0, 113, 227, 0.35) !important;
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
}

.stButton > button:hover {
    transform: scale(1.025) translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(0, 113, 227, 0.55) !important;
}

/* 7. Glass Radio Groups & Alerts */
div[role="radiogroup"] {
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    padding: 1.25rem !important;
    border-radius: 18px !important;
    backdrop-filter: blur(20px) !important;
}

.stAlert {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(20px) !important;
    color: #f5f5f7 !important;
}
</style>
"""
st.markdown(apple_theme_css, unsafe_allow_html=True)

# ==========================================
# 2. INITIALIZATION & API SETUP
# ==========================================
api_token = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_token)
N8N_WEBHOOK_URL = "https://your-n8n-webhook-url-here" 

def reset_quiz():
    st.session_state.current_q_data = None
    st.session_state.answered = False

if "progress_data" not in st.session_state: st.session_state.progress_data = []  
if "current_q_data" not in st.session_state: st.session_state.current_q_data = None
if "answered" not in st.session_state: st.session_state.answered = False
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "student_name" not in st.session_state: st.session_state.student_name = ""
if "student_email" not in st.session_state: st.session_state.student_email = ""

# ==========================================
# 3. SECURE APPLE LOGIN GATE
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1>AI Quiz Generator <span class='apple-gradient-text'>Pro</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #86868B; font-size: 1.1rem; margin-bottom: 2rem;'>Enter your credentials to access your testing suite.</p>", unsafe_allow_html=True)
    
    with st.container():
        name_input = st.text_input("Full Name", key="login_name", placeholder="e.g., Hammad")
        email_input = st.text_input("Email Address", key="login_email", placeholder="e.g., student@domain.com")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Start Assessment ➔", type="primary"):
            if name_input.strip() and email_input.strip():
                st.session_state.student_name = name_input
                st.session_state.student_email = email_input
                st.session_state.logged_in = True
                st.rerun()  
            else:
                st.error("Please provide both your name and email address.")
    st.stop()

# ==========================================
# 4. DASHBOARD & CONFIGURATION
# ==========================================
st.markdown(f"<h1>AI Quiz Generator <span class='apple-gradient-text'>Hub</span></h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color: #86868B;'>Logged in as <b>{st.session_state.student_name}</b></p>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

col_a, col_b, col_c = st.columns(3)
grade_level = col_a.selectbox("Target Grade", ["Grade 9", "Grade 10", "AS Level", "A Level"], index=2, on_change=reset_quiz)
subject = col_b.text_input("Subject", placeholder="e.g., Physics", on_change=reset_quiz)
topic = col_c.text_input("Curriculum Topic", placeholder="e.g., Kinematics", on_change=reset_quiz)

study_mode = st.radio("Assessment Mode", ["Multiple Choice (MCQ)", "Theory"], on_change=reset_quiz)
question_length = "short"
if study_mode == "Theory":
    question_length = st.selectbox("Theory Depth", ["Short Question", "Long Question"], on_change=reset_quiz)

# ==========================================
# 5. GENERATION ENGINE (UNBIASED SHUFFLE)
# ==========================================
if st.session_state.current_q_data is None:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Generate Quiz Question ✦", type="primary"):
        if subject.strip() == "" or topic.strip() == "":
            st.error("Please fill in both Subject and Topic fields.")
        else:
            with st.spinner("Synthesizing custom quiz question..."):
                random_seed = random.randint(1, 100000) 
                
                if study_mode == "Multiple Choice (MCQ)":
                    prompt = f"""
                    You are an expert academic professor. Create ONE unique, challenging, and factually accurate multiple choice question for {grade_level} {subject} on {topic}.
                    Seed: {random_seed}.
                    CRITICAL RULES:
                    1. The correct answer MUST be absolutely factually correct.
                    2. Provide exactly 3 plausible distractors that are factually incorrect.
                    You MUST output ONLY valid JSON format exactly like this:
                    {{"question": "Question text here?", "correct_answer": "The right answer text", "incorrect_answers": ["Wrong text 1", "Wrong text 2", "Wrong text 3"]}}
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
                    parsed_data = json.loads(clean_json)
                    
                    # Python Anti-Bias Shuffle Algorithm
                    if study_mode == "Multiple Choice (MCQ)":
                        options = [parsed_data["correct_answer"]] + parsed_data["incorrect_answers"]
                        random.shuffle(options) 
                        
                        parsed_data["A"] = options[0]
                        parsed_data["B"] = options[1]
                        parsed_data["C"] = options[2]
                        parsed_data["D"] = options[3]
                        
                        letters = ["A", "B", "C", "D"]
                        correct_index = options.index(parsed_data["correct_answer"])
                        parsed_data["correct"] = letters[correct_index]

                    st.session_state.current_q_data = parsed_data
                    st.session_state.current_q_data['type'] = study_mode
                    st.session_state.answered = False
                    st.rerun() 
                except Exception as e:
                    st.error(f"Generation error: {e}")

# ==========================================
# 6. ACTIVE QUIZ & GRADING LOOP
# ==========================================
else:
    st.markdown("<hr style='border: 1px solid rgba(255,255,255,0.1); margin: 2rem 0;'>", unsafe_allow_html=True)
    st.markdown("<h3>Generated Assessment Question</h3>", unsafe_allow_html=True)
    st.info(st.session_state.current_q_data["question"])
    
    q_data = st.session_state.current_q_data
    search_query = urllib.parse.quote(f"{subject} {topic} answer explanation")
    study_link = f"https://www.google.com/search?q={search_query}"

    if not st.session_state.answered:
        if q_data['type'] == "Multiple Choice (MCQ)":
            user_choice = st.radio(
                "Select Option:", 
                ["A", "B", "C", "D"], 
                format_func=lambda x: f"{x}) {q_data.get(x, '')}", 
                key="mcq_radio"
            )
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Submit Answer ➔", type="primary"):
                correct_ans = q_data.get("correct", "A") 
                score = 100 if user_choice == correct_ans else 0
                st.session_state.progress_data.append({"Subject": subject, "Topic": topic, "Score": score})
                st.session_state.user_choice = user_choice 
                st.session_state.answered = True
                st.rerun() 
                
        else: 
            student_answer = st.text_area("Type your response:", key="theory_text")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Submit Answer ➔", type="primary"):
                if student_answer.strip() == "":
                    st.error("Please enter your answer.")
                else:
                    with st.spinner("Grading response..."):
                        eval_prompt = f"""
                        Evaluate this answer for correctness. 
                        Question: {q_data['question']}
                        Student Answer: {student_answer}
                        You MUST output ONLY valid JSON format:
                        {{"verdict": "CORRECT", "explanation": "1 sentence explanation."}}
                        Or if wrong: {{"verdict": "INCORRECT", "explanation": "1 sentence explanation of right answer."}}
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
                            st.error(f"Grading error: {e}")

    # Results Display Screen
    if st.session_state.answered:
        score = st.session_state.progress_data[-1]["Score"] 
        
        if score == 100:
            st.balloons()
            st.markdown("<h2 style='text-align: center; color: #30d158;'>😊 Correct Answer! Great Job</h2>", unsafe_allow_html=True)
        else:
            st.markdown("<h2 style='text-align: center; color: #ff453a;'>😢 Incorrect. Review Recommended</h2>", unsafe_allow_html=True)
            
        if q_data['type'] == "Multiple Choice (MCQ)":
            correct_ans = q_data.get("correct", "A")
            user_choice = st.session_state.user_choice
            
            for opt in ["A", "B", "C", "D"]:
                text = f"{opt}) {q_data.get(opt, '')}"
                if opt == correct_ans:
                    st.markdown(f"<div style='background: rgba(48, 209, 88, 0.15); border: 1px solid #30d158; padding: 14px; border-radius: 12px; color: #30d158; margin: 8px 0;'>✅ <b>{text}</b> (Correct Answer)</div>", unsafe_allow_html=True)
                elif opt == user_choice and user_choice != correct_ans:
                    st.markdown(f"<div style='background: rgba(255, 69, 58, 0.15); border: 1px solid #ff453a; padding: 14px; border-radius: 12px; color: #ff453a; margin: 8px 0;'>❌ <b>{text}</b> (Your Selection)</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); padding: 14px; border-radius: 12px; color: #86868B; margin: 8px 0;'>{text}</div>", unsafe_allow_html=True)
        else:
            eval_json = st.session_state.theory_eval
            if score == 100:
                st.success(f"{eval_json.get('explanation', 'Correct!')}")
            else:
                st.error(f"{eval_json.get('explanation', 'Incorrect.')}")
                
        st.markdown(f"**📚 Study Material:** [Explore deeper context on {topic} ➔]({study_link})")
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("Next Quiz Question ⏭️", type="primary"):
            st.session_state.current_q_data = None
            st.session_state.answered = False
            st.rerun() 

# ==========================================
# 7. ANALYTICS & DASHBOARD
# ==========================================
if len(st.session_state.progress_data) > 0:
    st.markdown("<hr style='border: 1px solid rgba(255,255,255,0.1); margin: 3rem 0;'>", unsafe_allow_html=True)
    st.markdown("<h2>Performance Analytics</h2>", unsafe_allow_html=True)
    
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
        label="📥 Download CSV Report",
        data=csv_data,
        file_name=f"{st.session_state.student_name}_quiz_report.csv",
        mime="text/csv"
    )
    
    if st.button("📧 Email Progress Report (n8n Webhook)"):
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
            st.success("Report metrics successfully dispatched to n8n webhook.")
        except Exception as e:
            st.error(f"Webhook connection failure: {e}")
