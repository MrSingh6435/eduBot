from flask import Flask, render_template, request, jsonify
import requests
import google.generativeai as genai

app = Flask(__name__)

# Configure APIs
genai.configure(api_key="AIzaSyD3-j-C-QGdmVKTjB0JCVw3-Lh4TSs7zUo")
USAJOBS_API_KEY = "NlS/ZZPDgbwVtf/lqHKcTUySyAR4KAKEVlkpRvJYjT8="
GOOGLE_SEARCH_API_KEY = "AIzaSyC9Rm_X8qed7Vyt2g_GChYHXRks0pdh1Xk"
GOOGLE_CX = "b724f1dcc00c64c11"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    data = request.json
    user_query = data.get('query')
    user_skills = [skill.strip() for skill in data.get('skills', "").split(',') if skill.strip()]
    
    jobs, required_skills = fetch_jobs(user_query)
    skill_gap = analyze_skill_gap(user_skills, required_skills)
    learning_resources = fetch_learning_resources(", ".join(skill_gap) if skill_gap else user_query)
    
    response = generate_response(user_query, jobs, user_skills, skill_gap, learning_resources)
    
    return jsonify({
        'response': response,
        'jobs': jobs,
        'skill_gap': skill_gap,
        'learning_resources': learning_resources
    })

def fetch_jobs(job_title):
    """Fetch job listings from USA Jobs API."""
    url = "https://data.usajobs.gov/api/Search"
    headers = {"Authorization-Key": USAJOBS_API_KEY}
    params = {"Keyword": job_title, "ResultsPerPage": 5}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        jobs = response.json().get("SearchResult", {}).get("SearchResultItems", [])
        job_list = []
        required_skills = set()
        
        for job in jobs:
            position = job["MatchedObjectDescriptor"]["PositionTitle"]
            description = job["MatchedObjectDescriptor"].get("UserArea", {}).get("Details", {}).get("MajorDuties", "")
            
            job_list.append(position)
            required_skills.update(extract_skills(description))

        return job_list if job_list else ["No job listings found."], list(required_skills)
    
    except requests.exceptions.RequestException as e:
        print(f"USA Jobs API Error: {e}")
        return ["Could not fetch job data."], []

def extract_skills(description):
    """Extract skills from job description."""
    common_skills = {
        "Python", "C#", "Unity", "AI", "Machine Learning", "Deep Learning", "NLP",
        "Data Analysis", "Game Development", "Software Engineering", "Cybersecurity"
    }
    words = set(description.lower().split())
    return {skill for skill in common_skills if skill.lower() in words}

def fetch_learning_resources(query):
    """Fetch learning resources using Google Custom Search API."""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_SEARCH_API_KEY,
        "cx": GOOGLE_CX,
        "q": f"learning resources {query}",
        "num": 5
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        items = response.json().get("items", [])
        return [clean_resource_title(item["title"]) for item in items] if items else ["No courses found."]
    except requests.exceptions.RequestException as e:
        print(f"Google Search API Error: {e}")
        return ["Could not fetch learning resources."]

def clean_resource_title(title):
    """Clean up resource titles by removing site names."""
    return title.split(" - ")[0].split(" | ")[0]

def analyze_skill_gap(user_skills, required_skills):
    """Analyze the skill gap between user skills and job requirements."""
    return list(set(required_skills) - set(user_skills))

def generate_response(user_query, job_data, user_skills, skill_gap, learning_resources):
    """Generate a personalized career suggestion with formatted output."""
    prompt = f"""
    Provide career advice with this format:
    
    **Career Recommendation**
    *Brief overview*
    
    **Suggested Job Roles**
    *1. Role 1
    *2. Role 2
    
    **Your Current Skills**
    *Skill 1, Skill 2
    
    **Skills to Develop**
    *Skill 1, Skill 2
    
    **Recommended Learning Resources**
    *1. Resource 1
    *2. Resource 2
    
    Actual data to use:
    User Query: {user_query}
    Suggested Jobs: {', '.join(job_data[:3])}
    User Skills: {', '.join(user_skills)}
    Missing Skills: {', '.join(skill_gap) if skill_gap else 'None'}
    Learning Resources: {', '.join(learning_resources[:3])}
    """
    
    try:
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content(prompt)
        return format_response(response.text) if response else "No response generated."
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "Could not generate a response."

def format_response(text):
    """Convert * to <br> and ** to <strong> tags."""
    # First handle double asterisks for bold/headings
    parts = text.split('**')
    formatted = []
    for i, part in enumerate(parts):
        if i % 2 == 1:  # Odd indexes are between **
            formatted.append(f'<strong>{part.strip()}</strong>')
        else:
            formatted.append(part)
    formatted_text = ''.join(formatted)
    
    # Then handle single asterisks for line breaks
    formatted_text = formatted_text.replace('*', '<br>')
    
    # Clean up any empty tags
    formatted_text = formatted_text.replace('<strong></strong>', '')
    
    return formatted_text

if __name__ == '__main__':
    app.run(debug=True)