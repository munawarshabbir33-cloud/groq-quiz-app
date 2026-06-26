import streamlit as st
import urllib.parse  # Used to safely create web links
from groq import Groq

# 1. Grab the secret token from Streamlit's cloud encrypted vault
api_token = st.secrets["GROQ_API_KEY"]

# 2. Instantiate the Groq communication client
client = Groq(api_key=api_token)

# 3. Application User Interface Design (Streamlit Frontend)
st.set_page_config(page_title="AI Quiz Generator", page_icon="🎯", layout="centered")

st.title("🎯 Free AI Quiz Generator")
st.write("Generate short, engaging academic questions instantly.")

# Data capture block for inputs
with st.container():
    grade_level = st.selectbox("Target Grade Level:", ["Grade 9", "Grade 10", "AS Level", "A Level"])
    subject = st.text_input("Academic Subject:", placeholder="e.g., Physics, Computer Science")
    topic = st.text_input("Curriculum Topic Area:", placeholder="e.g., Newtons Law, Arrays")

# Initialize persistent session states
if "generated_question" not in st.session_state:
    st.session_state.generated_question = None
if "evaluation_results" not in st.session_state:
    st.session_state.evaluation_results = None

# 4. Question Generation Pipeline (UPDATED FOR SHORTER QUESTIONS)
if st.button("Generate Original Question"):
    if subject.strip() == "" or topic.strip() == "":
        st.warning("Please fill in both the Subject and Topic boxes before proceeding.")
    else:
        st.write("Communicating with Groq AI network... generating problem.")
        
        # We added a strict rule for brevity here
        generation_prompt = f"""
        You are an elite academic professor constructing test items for {grade_level} {subject}.
        Generate exactly ONE short-answer question testing knowledge on: {topic}.
        CRITICAL RULE: The question must be extremely short, direct, and punchy (maximum 1 to 2 sentences, under 20 words).
        Do not make it multiple choice. Output ONLY the raw question text. No introductory filler text.
        """
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": generation_prompt}],
            temperature=0.7
        )
        
        st.session_state.generated_question = response.choices[0].message.content
        st.session_state.evaluation_results = None  # Clear past grading values

# 5. Student Interaction & Automated Evaluation Loop
if st.session_state.generated_question:
    st.markdown("---")
    st.subheader("📋 Assessment Problem:")
    st.info(st.session_state.generated_question)
    
    student_answer = st.text_input("Type your formal answer submission below:", key="student_input_box")
    
    if st.button("Submit Assessment Answer"):
        if student_answer.strip() == "":
            st.error("Please enter text into the answer space before submitting.")
        else:
            st.write("Evaluating submission metrics...")
            
            grading_prompt = f"""
            You are a rigorous exam evaluator. Review the problem context and evaluate the student response.
            Question: {st.session_state.generated_question}
            Student Response: {student_answer}
            
            You must output your reply strictly in this identical format structure:
            VERDICT: [CORRECT or INCORRECT]
            EXPLANATION: [Provide a precise 1-sentence analytical review of the concept.]
            """
            
            grading_call = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": grading_prompt}],
                temperature=0.1
            )
            
            st.session_state.evaluation_results = grading_call.choices[0].message.content

# 6. Dynamic Results Display & Study Link Logic (UPDATED)
if st.session_state.evaluation_results:
    st.markdown("---")
    st.subheader("📊 Performance Diagnostics Feedback:")
    
    # If they got it right, just show the success message
    if "VERDICT: CORRECT" in st.session_state.evaluation_results:
        st.success(st.session_state.evaluation_results)
        
    # If they got it wrong, show the error AND generate a study link
    else:
        st.error(st.session_state.evaluation_results)
        
        # Create a safe, clickable Google Search link for the specific topic
        search_query = urllib.parse.quote(f"{subject} {topic} lesson explanation")
        study_link = f"https://www.google.com/search?q={search_query}"
        
        # Display the link clearly to the student
        st.markdown(f"**📚 Needs review?** [Click here to study more about **{topic}**]({study_link})")
