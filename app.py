import json
import os
from groq import Groq
import random
import string
from datetime import datetime
import uuid
import requests
# No 're' or 'time' needed anymore
from datetime import timedelta
from flask import Flask, jsonify, request, render_template, session, Response# Keep Response
from flask_cors import CORS # Import CORS
from supabase import create_client, Client
import dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# --- Imports for NEP 2020 AI Analyst (MODIFIED) ---
import google.generativeai as genai # <<< FIX 1: Import the main 'genai' module
from google.generativeai.types import HarmCategory, HarmBlockThreshold # <<< FIX 1: Removed incorrect 'as genai' alias

# --- NEW IMPORTS FOR OCR ---
from PIL import Image
import io
# --- END NEW IMPORTS ---


dotenv.load_dotenv()

app = Flask(__name__)
CORS(app) 

# --- FIX for Session Errors ---
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or 'temporary-secret-key-for-testing-only-12345'

app.permanent_session_lifetime = timedelta(days=7)

# Supabase creds (User's original values)
SUPABASE_URL = ""
SUPABASE_KEY = ""
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ----------------------------------------------------------------------
# --- NEP 2020 AI ANALYST (SYSTEM PROMPT) CONFIGURATION ---
# ----------------------------------------------------------------------

# --- (FIX 1: SECURE API KEY) ---
# Load the API key from an environment variable. DO NOT paste it here.
api_key = "" # <<< FIX 2: Load key from environment
if not api_key:
    print("CRITICAL ERROR: 'GEMINI_API_KEY' environment variable not set.")
    print("Please set it before running the app:")
    print("   (Mac/Linux)     export GEMINI_API_KEY='your_key_here'")
    print("   (Windows CMD) set GEMINI_API_KEY=your_key_here")
else:
    genai.configure(api_key=api_key) # This will now work

# We only need the generation model now
# Note: 'gemini-2.5-flash' is not a standard public model name. 
# You may mean 'gemini-1.5-flash'. We will use the '-latest' suffix
# to ensure the API finds the most recent stable version.
GENERATION_MODEL = 'gemini-2.5-flash' # <<< FIX 3: Use a valid model name
VISION_MODEL = 'gemini-2.5-flash' # <<< FIX 3: Use a valid model name

groq_client = Groq(
    api_key=''  # or api_key="your_key_here"
)


# ----------------------------------------------------------------------
# --- NEW OCR HELPER FUNCTION ---
# ----------------------------------------------------------------------

def extract_school_data_from_image(image_bytes: bytes):
    """
    Uses Gemini Vision to extract school data from an image and return structured JSON.
    """
    print("DEBUG: Starting OCR extraction...")
    
    # --- The Master Prompt for the Vision Model ---
    system_prompt = """
    You are an expert OCR and data extraction AI. Your task is to analyze the provided image
    of a handwritten or printed school data form. Find, extract, and structure the data 
    for the 21 fields listed below.

    **CRITICAL INSTRUCTIONS:**
    1.  Return ONLY a single, valid JSON object.
    2.  Do NOT include '```json' or '```' or any other text before or after the JSON.
    3.  If a value for a field cannot be found, use `null` (not "N/A" or "missing").
    4.  Carefully follow the data type (string, number, object, list) for each field.

    **FIELDS TO EXTRACT:**

    1.  "school_name": (string) The name of the school.
    2.  "school_type": (string) Must be one of: "gov", "private", "trust".
    3.  "location": (string) The full address or city.
    4.  "year_establishment": (number) The 4-digit year.
    5.  "num_students": (number) **CALCULATE THIS**: Sum all values from "total_students_per_grade". If you cannot find per-grade data, try to find a "total students" field.
    6.  "total_students_per_grade": (object) A JSON object of grade-to-student counts. Example: {"Grade 1": 50, "Grade 2": 55, "Std 10": 120}
    7.  "num_grades": (number) The total number of grades (e.g., 12).
    8.  "avg_attendance_rate": (number) The percentage (e.g., 92.5).
    9.  "enrollment_trends_of_past_3_years": (list) A list of 3 numbers. Example: [250, 275, 300]
    10. "gender_ratio": (string) The M:F ratio. Example: "55:45" or "1.2:1".
    11. "students_special_needs": (number) The total count of students with special needs.
    12. "num_teachers": (number) The total count of teachers.
    13. "teacher_qualifications": (string) The average or most common qualification (e.g., "B.Ed", "M.Sc").
    14. "teacher_to_student_ratio": (string) **CALCULATE THIS**: Divide 'num_students' by 'num_teachers'. Return as "1:X". Example: 500 students / 25 teachers = "1:20". Return `null` if data is missing.
    15. "avg_teacher_experience": (number) Average years of experience (e.g., 8.5).
    16. "professional_dept": (string) Any listed professional development programs.
    17. "infra_availability": (object) An object for infrastructure status. Example: {"classrooms": "Available", "labs": "Partial", "toilets": "Available", "electricity": "Available", "water": "Available"}
    18. "digital_infra": (string) A description of digital tools (e.g., "Computers, Internet, 2 Smart Boards").
    19. "performance_scores": (object) An object for average subject scores. Example: {"math": 75.5, "science": 80.0, "hindi": 82.0, "mother_language": 88.0, "english": 79.0}
    20. "curriculum_completion": (number) The average completion rate (e.g., 95.0).
    21. "nep_participation": (string) Description of NEP-aligned activities.
    
    Start the JSON object now:
    {
    """
    
    try:
        # Load image with PIL
        img = Image.open(io.BytesIO(image_bytes))
        
        # Configure the model (genai is now correctly imported)
        model = genai.GenerativeModel(VISION_MODEL)
        
        # Generate content
        # Note: The prompt is a combination of text and the image
        response = model.generate_content([system_prompt, img])
        
        # Clean the response text to find the JSON
        raw_text = response.text
        print(f"DEBUG: Raw AI Response:\n{raw_text}")
        
        # Find the start and end of the JSON object
        json_start = raw_text.find('{')
        json_end = raw_text.rfind('}')
        
        if json_start == -1 or json_end == -1:
            print("ERROR: No JSON object found in AI response.")
            raise Exception("AI did not return a valid JSON object.")
            
        json_string = raw_text[json_start:json_end+1]
        
        # Parse and return the dictionary
        extracted_data = json.loads(json_string)
        return extracted_data

    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to decode JSON from AI. Response was:\n{json_string}")
        raise Exception(f"AI returned malformed JSON. {e}")
    except Exception as e:
        print(f"ERROR: Error in Gemini Vision call: {e}")
        raise e


# ----------------------------------------------------------------------
# --- NEP 2020 AI ANALYST (SYSTEM PROMPT) FUNCTIONS ---
# ----------------------------------------------------------------------

# <<< MODIFIED/RENAMED FUNCTION >>>
def get_context_aware_answer(user_query: str, user_name: str, school_context: str):
    """
    Calls Groq (Llama) with a dynamic system prompt that includes user and school data.
    """
    
    print(f"DEBUG: Getting context-aware answer for: '{user_name}'")
    print(f"DEBUG: Query: {user_query}")

    # --- SYSTEM PROMPT ---
    system_instruction = (
        f"You are a highly advanced AI analyst, specializing in India's National Education Policy 2020 (NEP 2020). "
        f"You are speaking directly to {user_name}.\n\n"
        
        "Your primary role is to be a helpful, context-aware assistant. You must follow these rules:\n"
        "1. **Acknowledge the User:** If appropriate, greet the user by their name.\n"
        "2. **Use the Data:** When the user asks about their school, answer directly using the school data provided in the context.\n"
        "3. **Analyze & Suggest:** Analyze the provided school data and give specific, actionable suggestions on how the school can improve its alignment with NEP 2020.\n"
        "4. **Answer General NEP Questions:** If the user asks a general question about NEP 2020, answer it accurately.\n"
        "5. **Combine Knowledge:** When possible, relate NEP answers back to the school's data.\n"
        "6. **Guardrails:** If the user asks something completely unrelated to education, NEP, or school data, politely decline.\n"
        "7. **Format:** Use clear Markdown formatting (bold headings with **, bullet points with -, etc.) to make responses easy to read.\n"
        "8. **Style of Speech:** when the school data is provided i want you to talk in the language of the school that is located in but also if the user asks to be in anyother language you can"
    )

    try:
        # Build the user message with context
        user_message = f"{school_context}\n\n---\n\nUser Question: {user_query}"
        
        print("DEBUG: Calling Groq API...")
        
        # Call Groq API
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_instruction
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            model="llama-3.3-70b-versatile",  # Best model for reasoning tasks
            temperature=0.7,
            max_tokens=1024,
            top_p=0.9,
            stream=False
        )
        
        print("DEBUG: Response received successfully!")
        
        # Extract the response
        if chat_completion.choices and len(chat_completion.choices) > 0:
            response_text = chat_completion.choices[0].message.content
            
            # Check if response was complete
            finish_reason = chat_completion.choices[0].finish_reason
            print(f"DEBUG: Finish reason: {finish_reason}")
            
            if finish_reason == "stop":
                return response_text
            elif finish_reason == "length":
                return response_text + "\n\n*(Response was cut off due to length limit)*"
            else:
                return response_text
        
        return "No response generated. Please try again."
            
    except Exception as e:
        print(f"ERROR calling Groq API: {e}")
        import traceback
        traceback.print_exc()
        
        error_str = str(e).lower()
        if "api" in error_str and "key" in error_str:
            return "Sorry, there's an issue with the API key. Please contact the administrator."
        elif "rate" in error_str or "limit" in error_str:
            return "Sorry, we've hit our rate limit. Please try again in a moment."
        
        return f"Sorry, I encountered an error: {str(e)}"


# --- YOUR /ask ROUTE ---
@app.route('/ask', methods=['POST'])
def ask_policy_question():
    """Endpoint for receiving user questions for the AI analyst (non-streaming)."""
    data = request.get_json()
    user_query = data.get('query')
    
    if not user_query:
        return jsonify({"error": "Missing 'query' in request body."}), 400

    if 'username' not in session:
        return jsonify({"error": "You must be logged in to use the AI analyst."}), 401
        
    current_username = session['username']
    
    # 1. Get User's Name
    user_name = current_username
    try:
        user_info_response = supabase.table("User").select('firstname', 'lastname').eq('username', current_username).execute()
        if user_info_response.data:
            user = user_info_response.data[0]
            full_name = f"{user.get('firstname', '')} {user.get('lastname', '')}".strip()
            if full_name:
                user_name = full_name
    except Exception as e:
        print(f"Warning: Could not fetch user's full name. {e}")

    # 2. Get School Data - SIMPLIFIED FORMATTING
    school_data_context = "No school data has been submitted yet."
    try:
        school_data_response = supabase.table("schooldata").select('*').eq('submitted_by_username', current_username).limit(1).execute()
        
        if school_data_response.data:
            school_data = school_data_response.data[0]
            
            # Format in a cleaner, more readable way
            school_data_context = "School Data:\n"
            for key, value in school_data.items():
                # Skip internal fields
                if key not in ['id', 'created_at', 'submitted_by_username']:
                    school_data_context += f"- {key}: {value}\n"
                    
    except Exception as e:
        print(f"ERROR: CRITICAL error fetching school data: {e}")
        return jsonify({"error": f"Failed to fetch context data from database: {e}"}), 500
    
    answer = get_context_aware_answer(user_query, user_name, school_data_context)
    
    return jsonify({
        "query": user_query,
        "answer": answer
    })

# ----------------------------------------------------------------------
# --- NEW OCR/IMAGE ROUTES ---
# ----------------------------------------------------------------------

@app.route('/ocr')
def ocr_page():
    """Serves the new OCR upload page."""
    if 'logged_in' not in session or not session['logged_in']:
        return """
            <script>
                alert("You must be logged in to use this feature.");
                window.location.href = "/login";
            </script>
        """
    # We will create 'ocr.html' in the next step
    return render_template('ocr.html')


@app.route('/extract-from-image', methods=['POST'])
def extract_from_image():
    """
    Receives an image, sends it to the Gemini Vision model for extraction,
    and returns the structured JSON data.
    """
    if 'username' not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401
    
    if 'image' not in request.files:
        return jsonify({"error": "No image file found in request."}), 400
        
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({"error": "No selected file."}), 400
        
    try:
        image_bytes = file.read()
        
        # Call the helper function to get data from Gemini
        extracted_data = extract_school_data_from_image(image_bytes)
        
        # Return the dictionary as JSON
        return jsonify(extracted_data), 200
        
    except Exception as e:
        print(f"Error during image extraction: {e}")
        # Send a generic error message to the client
        return jsonify({"error": f"An error occurred during extraction: {str(e)}"}), 500


# ----------------------------------------------------------------------
# --- ALL YOUR ORIGINAL ROUTES (UNCHANGED) ---
# ----------------------------------------------------------------------

@app.route('/dashboard-data', methods=['GET'])
def get_dashboard_data():
    if 'username' not in session:
        return jsonify({"message": "Unauthorized. Please log in."}), 401
    current_username = session['username']
    role = supabase.table("User").select('role').eq('username', current_username).execute().data[0]['role']
    code = supabase.table("User").select('mode').eq('username', current_username).execute().data[0]['mode']
    print(code)
    print(role)
    try:
        if role != "Admin":
            if role == "faculty":
                response = supabase.table("schooldata").select('*').eq('facultycode', code).execute()
                if response.data:
                    return jsonify(response.data), 200 #error encountered
                else:
                    return jsonify({"message": "No school data found for this user."}), 404
            elif role == "student":
                response = supabase.table("schooldata").select('*').eq('studentcode', code).execute()
                if response.data:
                    return jsonify(response.data), 200
                else:
                    return jsonify({"message": "No school data found for this user."}), 404
            
        response = supabase.table("schooldata").select('*').eq('submitted_by_username', current_username).execute()
        if response.data:
            return jsonify(response.data), 200
        else:
            return jsonify({"message": "No school data found for this user."}), 404
    except Exception as e:
        print(f"Supabase retrieval error: {e}")
        return jsonify({"message": "Failed to retrieve data from database."}), 500

@app.route('/dashboard')
def dashboard_page():
    if 'logged_in' not in session or not session['logged_in']:
        return """
            <script>
                alert("You must be logged in to view the dashboard.");
                window.location.href = "/login";
            </script>
        """
    return render_template('dashboard.html')

@app.route('/submit-school-data', methods=['POST'])
def submit_school_data():
    if 'username' not in session:
        return """
            <script>
                alert("You must be logged in to submit school data.");
                window.location.href = "/login";
            </script>
        """
    current_username = session['username']
    try:
        form_data = request.form.to_dict()
        grade_enrollment_json = form_data.get('grade_enrollment_data', '{}')
        enrollment_trends_list = [
            int(n.strip()) 
            for n in form_data.get('enrollment_trends', '0,0,0').split(',') 
            if n.strip().isdigit()
        ]
        payload = {
            "submitted_by_username": current_username, 
            "school_name": form_data.get('school_name'),
            "school_type": form_data.get('school_type'),
            "location": form_data.get('location'),
            "year_establishment": int(form_data.get('year_establishment')),
            "num_students": int(form_data.get('num_students')),
            "num_grades": int(form_data.get('num_grades')),
            "avg_attendance_rate": float(form_data.get('avg_attendance_rate')),
            "gender_ratio": form_data.get('gender_ratio'),
            "students_special_needs": int(form_data.get('students_special_needs')),
            "num_teachers": int(form_data.get('num_teachers')),
            "teacher_qualifications": form_data.get('teacher_qualifications'),
            "avg_teacher_experience": float(form_data.get('avg_teacher_experience')),
            "professional_dept": form_data.get('professional_dept'),
            "curriculum_completion": float(form_data.get('curriculum_completion')),
            "nep_participation": form_data.get('nep_participation'),
            "grade_enrollment_data": json.loads(grade_enrollment_json), 
            "enrollment_trends": enrollment_trends_list, 
            "teacher_student_ratio": form_data.get('teacher_student_ratio'), 
            "infra_availability": {
                "classrooms": form_data.get('classrooms_avail'),
                "labs": form_data.get('labs_avail'),
                "toilets": form_data.get('toilets_avail'),
                "electricity": form_data.get('electricity_avail'),
                "water": form_data.get('water_avail'),
            }, 
            "digital_infra": form_data.get('digital_infra'),
            "performance_scores": {
                "math": float(form_data.get('perf_math')),
                "science": float(form_data.get('perf_science')),
                "hindi": float(form_data.get('perf_hindi')),
                "mother_language": float(form_data.get('perf_mother_lang')),
                "english": float(form_data.get('perf_english')),
            },
            "facultycode": generate_random_code(5),
            "studentcode": generate_random_code(5)
        }
    except Exception as e:
        print(f"Error processing form data: {e}") 
        return """
            <script>
                alert("Error: Invalid form data format.");
                window.location.href = "/sch_reg"; 
            </script>
        """, 400
    try:
        response = supabase.table("schooldata").insert(payload).execute()
        if response.data:
            return """
                <script>
                    alert("School data successfully saved and linked to your account!");
                    window.location.href = "/sch_reg"; 
                </script>
            """
        else:
            raise Exception("Insertion failed unexpectedly (no data returned).")
    except Exception as e:
        print(f"Supabase insertion error: {e}")
        return f"""
                <script>
                    alert("Error: Failed to save data. Details: {str(e)[:50]}");
                    window.location.href = "/sch_reg"; 
                </script>
                """

def generate_random_code(length=5):
            """
            Generates a random alphanumeric code.

            Args:
                length (int): The desired length of the code. Defaults to 12.

            Returns:
                str: A random code consisting of uppercase letters and digits.
            """
            # Define the set of characters to choose from: 
            # uppercase letters (A-Z) and digits (0-9)
            characters = string.ascii_uppercase + string.digits
            
            # Use random.choice() to select characters 'length' times
            # and ''.join() to combine them into a single string
            random_code = ''.join(random.choice(characters) for i in range(length))
            
            return random_code

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/land')
def land():
    return render_template('land.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')
    
@app.route('/info')
def info():
    if 'username' not in session:
        return jsonify({"message": "User not logged in"}), 401
    username = session['username']
    userinfo = (supabase.table("User").select('*').eq('username', username).execute())
    if userinfo and userinfo.data:
        user_dictionary = userinfo.data[0]
    else:
        user_dictionary = None
    uname = user_dictionary['username'] if user_dictionary else None
    email = user_dictionary['email'] if user_dictionary else None
    fname = user_dictionary['firstname'] if user_dictionary else None
    lname = user_dictionary['lastname'] if user_dictionary else None
    role = user_dictionary['role'] if user_dictionary else None
    code = user_dictionary['mode'] if user_dictionary else None
    pack = {
        'username': uname,
        'email': email,
        'firstname': fname,
        'lastname': lname,
        'role': role,
        'code': code
    }
    return jsonify(pack)

@app.route('/index')
def index():
    if 'logged_in' in session and session['logged_in']:
        return render_template('index.html')
    else:
        return render_template('register.html')

@app.route('/reg')
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def logged():
    if "logged_in" in session and session['logged_in']:
        return render_template('index.html')
    firstname = request.form.get("firstname")
    lastname = request.form.get("lastname")
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    cpassword = request.form.get("confirm_password")
    schoolname = request.form.get("school-name")
    mode = request.form.get("code-enter")
    if mode:
        fccheck = supabase.table("schooldata").select("facultycode").eq("school_name", schoolname).execute()
        print(fccheck)
        sccheck = supabase.table("schooldata").select("studentcode").eq("school_name", schoolname).execute()
        print(sccheck)
        if mode == fccheck.data[0]['facultycode']:
            role = "faculty"
        elif mode == sccheck.data[0]['studentcode']:
            role = "student"
        else:
            return """<script>alert("invalid code"); window.location.href = "/reg";</script>"""
    if password != cpassword:
        return """<script>alert("passwords do not match"); window.location.href = "/reg";</script>"""
    if len(password) < 8:
        return """<script>alert("password must be at least 8 characters long"); window.location.href = "/reg";</script>"""
    if not any(char.isdigit() for char in password):
        return """<script>alert("password must contain at least one digit"); window.location.href = "/reg";</script>"""
    if not any(char.isupper() for char in password):
        return """<script>alert("password must contain at least one uppercase letter"); window.location.href = "/reg";</script>"""
    username_check = supabase.table('User').select('username').eq('username', username).execute()
    if len(username_check.data) > 0:
        return """<script>alert("username already exists"); window.location.href = "/reg";</script>"""
    emailauth = supabase.table("User").select('email').eq('email', email).execute()
    if len(emailauth.data) > 0:
        return """<script>alert("email already exists"); window.location.href = "/reg";</script>"""
    try:
        hashed_password = generate_password_hash(password)
        if mode:
            supabase.table("User").insert({
                "firstname": firstname, "lastname": lastname, "username": username,
                "email": email, "password": hashed_password, "role":role, "mode":mode, 
            }).execute()
        else:
            supabase.table("User").insert({
                "firstname": firstname, "lastname": lastname, "username": username,
                "email": email, "password": hashed_password, "role":"Admin", "mode":"None",
            }).execute()
        if mode:
            session['logged_in'] = True
            session['username'] = username
            session['role'] = role
            session['mode'] = mode
        else:
            session['logged_in'] = True
            session['username'] = username
            session['role'] = "Admin"
            session['mode'] = "None"
        return """<script>alert("registration successful"); window.location.href = "/login";</script>"""
    except Exception as e:
        print(f"Supabase registration error: {e}")
        return jsonify({"message": "Registration failed due to a server error."}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session and session['logged_in']:
        return render_template('index.html')
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        role = supabase.table("User").select('role').eq('username', username).execute()
        user_response = supabase.table("User").select('username, password').eq('username', username).execute()
        if len(user_response.data) == 1:
            user = user_response.data[0]
            if check_password_hash(user['password'], password):
                session['logged_in'] = True
                session['username'] = username
                session['role'] = role.data[0]['role']
                return """<script>alert("login successful"); window.location.href = "/index";</script>"""
            else:
                return """<script>alert("incorrect password"); window.location.href = "/login";</script>"""
        else:
            return """<script>alert("username does not exist"); window.location.href = "/login";</script>"""
    else:
        return render_template('login.html')



@app.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')

@app.route('/Veiwpolicy')
def veiwpolicy():
    return render_template('NEP.html')

@app.route('/AI')
def AI():
    return render_template('AI.html')

@app.route('/logout')
def logout():
    session.clear()
    return render_template('land.html')

@app.route('/sch_reg')
def sch_reg():
    return render_template('sch_reg.html')

def get_tutor_response(user_query: str, chat_history: list, topic: str, user_name: str):
    """
    Calls Groq with a specific "Tutor" system prompt.
    """
    print(f"DEBUG: Getting AI Tutor response for {user_name} on topic: {topic}")

    # --- System Prompt for the AI Tutor ---
    system_instruction = (
        f"You are an expert AI tutor. Your student's name is {user_name}.\n"
        f"The student wants to learn about this specific topic: **{topic}**.\n\n"
        "YOUR RULES:\n"
        "1. **Be Patient & Encouraging:** Act as a supportive tutor, not just an answer machine.\n"
        "2. **Teach, Don't Just Answer:** When asked a question, explain the *concept* behind the answer.\n"
        "3. **Use Simple Examples:** Break down complex ideas into small, easy-to-understand parts with examples.\n"
        "4. **Ask Questions:** After explaining something, ask the student a question to check their understanding.\n"
        "5. **Stay on Topic:** Keep the conversation focused on the student's chosen topic.\n"
        "6. **Format Well:** Use Markdown (like **bold** and bullet points) to make your explanations clear."
    )
    
    # Build the message list
    messages = [{"role": "system", "content": system_instruction}]
    
    # Add the chat history
    for message in chat_history:
        messages.append({
            "role": message['role'],
            "content": message['content']
        })
    
    # Add the user's latest query
    messages.append({"role": "user", "content": user_query})

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile", # Using a strong model for tutoring
            temperature=0.7,
            max_tokens=2048,
            top_p=0.9,
            stream=False
        )
        
        if chat_completion.choices and len(chat_completion.choices) > 0:
            return chat_completion.choices[0].message.content
        return "Sorry, I'm having trouble thinking of a response right now."

    except Exception as e:
        print(f"ERROR calling Groq API for Tutor: {e}")
        return f"Sorry, an error occurred while connecting to the AI: {str(e)}"

# ----------------------------------------------------------------------
# --- AI TUTOR API ROUTES ---
# ----------------------------------------------------------------------

@app.route('/tutor')
def tutor_page():
    """Serves the new AI Tutor HTML page."""
    if 'logged_in' not in session or not session['logged_in']:
        return """
            <script>
                alert("You must be logged in to use the AI Tutor.");
                window.location.href = "/login";
            </script>
        """
    return render_template('tutor.html')


@app.route('/tutor/start', methods=['POST'])
def start_tutor_session():
    """Creates a new chat session in the database."""
    # --- USE THIS CHECK ---
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({"error": "Unauthorized"}), 401
    
    current_username = session['username']
    # ... (rest of the function is the same) ...
    data = request.get_json()
    topic = data.get('topic')
    
    if not topic:
        return jsonify({"error": "No topic provided"}), 400
        
    try:
        response = supabase.table("chat_sessions").insert({
            "user_username": current_username,
            "topic": topic
        }).execute()
        
        if response.data:
            new_session_id = response.data[0]['id']
            return jsonify({"session_id": new_session_id, "topic": topic}), 201
        else:
            return jsonify({"error": "Failed to create session in database."}), 500
            
    except Exception as e:
        print(f"ERROR /tutor/start: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/tutor/history', methods=['GET'])
def get_tutor_history():
    """Fetches all past chat sessions for the logged-in user."""
    # --- USE THIS CHECK ---
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({"error": "Unauthorized"}), 401
    
    current_username = session['username']
    # ... (rest of the function is the same) ...
    try:
        response = supabase.table("chat_sessions").select("id, topic, created_at") \
                         .eq("user_username", current_username) \
                         .order("created_at", desc=True) \
                         .execute()
        
        return jsonify(response.data), 200
        
    except Exception as e:
        print(f"ERROR /tutor/history: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/tutor/messages', methods=['GET'])
def get_tutor_messages():
    """Fetches all messages for a specific session_id."""
    # --- USE THIS CHECK ---
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({"error": "Unauthorized"}), 401
        
    session_id = request.args.get('session_id')
    # ... (rest of the function is the same) ...
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400
        
    current_username = session['username']

    try:
        session_check = supabase.table("chat_sessions").select("id") \
                                .eq("id", session_id) \
                                .eq("user_username", current_username) \
                                .execute()
        
        if not session_check.data:
            return jsonify({"error": "Session not found or access denied."}), 404
            
        messages = supabase.table("chat_messages").select("role, content") \
                             .eq("session_id", session_id) \
                             .order("created_at", desc=False) \
                             .execute()
                             
        return jsonify(messages.data), 200

    except Exception as e:
        print(f"ERROR /tutor/messages: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/tutor/chat', methods=['POST'])
def handle_tutor_chat():
    """Handles sending a message and getting an AI response."""
    # --- USE THIS CHECK ---
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({"error": "Unauthorized"}), 401
        
    current_username = session['username']
    # ... (rest of the function is the same) ...
    data = request.get_json()
    session_id = data.get('session_id')
    user_message = data.get('user_message')
    
    if not session_id or not user_message:
        return jsonify({"error": "Missing session_id or user_message"}), 400

    try:
        session_data = supabase.table("chat_sessions").select("topic") \
                               .eq("id", session_id) \
                               .eq("user_username", current_username) \
                               .execute()
        
        if not session_data.data:
            return jsonify({"error": "Session not found or access denied."}), 404
        
        topic = session_data.data[0]['topic']

        supabase.table("chat_messages").insert({
            "session_id": session_id,
            "role": "user",
            "content": user_message
        }).execute()
        
        history_response = supabase.table("chat_messages").select("role, content") \
                                   .eq("session_id", session_id) \
                                   .order("created_at", desc=False) \
                                   .execute()
                                   
        chat_history = history_response.data[:-1] 

        user_name = current_username # this is takng the current username for the login
        try:
            user_info_response = supabase.table("User").select('firstname').eq('username', current_username).execute()
            if user_info_response.data and user_info_response.data[0].get('firstname'):
                user_name = user_info_response.data[0]['firstname']
        except Exception as e:
            print(f"Warning: Could not fetch user's first name. {e}")

        ai_response = get_tutor_response(user_message, chat_history, topic, user_name)
        
        supabase.table("chat_messages").insert({
            "session_id": session_id,
            "role": "assistant",
            "content": ai_response
        }).execute()
        
        return jsonify({"answer": ai_response})

    except Exception as e:
        print(f"ERROR /tutor/chat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/student-dashboard')
def student_dashboard_page():
    """Serves the new Student Dashboard page."""
    if 'logged_in' not in session or not session['logged_in']:
        return """
            <script>
                alert("You must be logged in to view your dashboard.");
                window.location.href = "/login";
            </script>
        """
    # This will find and render the 'student_dashboard.html' file
    # you created in your 'templates' folder.
    return render_template('student_dashboard.html')    

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"--- Starting Flask Server on port {port} ---")
    app.run(host='0.0.0.0', port=port, debug=False)
