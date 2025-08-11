import os
from flask import Flask, request, jsonify
import mysql.connector 
import openai 
import fitz #PyMuPDF for PDF text extraction
import docx #python-docx for DOCX
import json 

app = Flask(__name__)

#Seting up openAI API key (in  enviroment variables for security)
openai.api_key = os.getenv("OPENAI_API_KEY")


# MySQL sample database config
db_config = {
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD','Wande123'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'cas_db'),
}
#Extraction functions 
def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

#function to get jobs from sample database
def get_jobs_from_db():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, company, skills, description FROM jobs")
        rows = cursor.fetchall()
        jobs = []
        for row in rows:
            job = {
                'id': row[0],
                'title': row[1],
                'company': row[2],
                'skills': row[3].split(','),  
                'description': row[4]
            }
            jobs.append(job)
        return jobs
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


#Function to match skills to jobs
def match_jobs(cv_skills, jobs):
    matched = []
    cv_skills_set = set([skill.strip().lower() for skill in cv_skills])
    
    for job in jobs:
        job_skills = [s.strip().lower() for s in job['skills']]
        common_skills = cv_skills_set.intersection(job_skills)
        if common_skills:
            job_copy = job.copy()
            job_copy['matched_skills'] = list(common_skills)
            matched.append(job_copy)
    return matched

#Function to recommend courses
def suggest_courses(missing_skills):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    suggested_courses = []

    for skill in missing_skills:
        cursor.execute(
            "SELECT id, name, provider, link, skill FROM courses WHERE LOWER(skill) = %s", 
            (skill.lower(),)
        )
        rows = cursor.fetchall()
        for row in rows:
            course = {
                'id': row[0],
                'name': row[1],
                'provider': row[2],
                'link': row[3],
                'skill': row[4]
            }
            suggested_courses.append(course)
    
    cursor.close()
    conn.close()
    return suggested_courses


#Code for AI inclusion
def parse_cv_with_openai(cv_text):
    prompt = f"""
    Extract the skills, experience, and qualifications from the following CV text.
    Return the response as a JSON with keys: skills (list), experience (list of jobs with titles and dates), qualifications (list).

    CV TEXT:
    {cv_text}
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from CVs."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
        )
        extracted_json = response['choices'][0]['message']['content']
        return extracted_json
    except Exception as e:
        # You can log the error here if you want
        print(f"OpenAI API call failed: {e}")
        return None 

@app.route('/upload-cv', methods=['POST'])
def upload_cv():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Save file temporarily
    if not os.path.exists('./temp'):
        os.makedirs('./temp')
    file_path = f"./temp/{file.filename}"
    file.save(file_path)

    # Extract text based on file extension
    if file.filename.endswith('.pdf'):
        cv_text = extract_text_from_pdf(file_path)
    elif file.filename.endswith('.docx'):
        cv_text = extract_text_from_docx(file_path)
    else:
        return jsonify({"error": "Unsupported file format"}), 400
    
    try:
        # Parse CV using OpenAI
        parsed_data = parse_cv_with_openai(cv_text)
        if parsed_data is None:
            return jsonify({"error": "Failed to parse CV with OpenAI API"}), 500

        # Convert OpenAI JSON string to dict
        try:
            parsed_dict = json.loads(parsed_data)
        except json.JSONDecodeError:
            return jsonify({"error": "Failed to parse AI response"}), 500

        cv_skills = parsed_dict.get('skills', [])

        # Fetch jobs from database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, company, skills, description FROM jobs")
        rows = cursor.fetchall()
        jobs = []
        for row in rows:
            job = {
                'id': row[0],
                'title': row[1],
                'company': row[2],
                'skills': row[3].split(','),  
                'description': row[4]
            }
            jobs.append(job)
        cursor.close()
        conn.close()

        # Match jobs with CV skills
        matched_jobs = match_jobs(cv_skills, jobs)

        # Suggest courses based on missing skills
        all_missing_skills = set()
        for job in matched_jobs:
            job_skills_set = set([skill.strip().lower() for skill in job['skills']])
            cv_skills_set = set([skill.strip().lower() for skill in cv_skills])
            missing = job_skills_set - cv_skills_set
            all_missing_skills.update(missing)

        courses_suggested = suggest_courses(all_missing_skills)

        return jsonify({
            "parsed_cv": parsed_dict,
            "matched_jobs": matched_jobs,
            "suggested_courses": courses_suggested
        })
    finally:
        # Clean up: remove the temporarily saved file
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Failed to delete temp file: {e}")
    


@app.route("/")
def home():
    return jsonify({"message": "Welcome to the CAS Backend API!"})

#code to fetch jobs from the database
@app.route('/jobs')
def get_jobs():
    jobs = get_jobs_from_db()
    return jsonify(jobs)
    

#code to fetch the courses
@app.route('/courses')
def get_courses():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, provider, link, skill FROM courses")
    rows = cursor.fetchall()
    courses = []
    for row in rows:
        course = {
            'id': row[0],
            'name': row[1],
            'provider': row[2],
            'link': row[3],
            'skill': row[4]
        }
        courses.append(course)
    cursor.close()
    conn.close()
    return jsonify(courses)


if __name__ == "__main__":
    app.run(debug=True)