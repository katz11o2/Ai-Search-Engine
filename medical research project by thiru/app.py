from flask import Flask, render_template, request, jsonify
from transformers import pipeline
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import keyboard  

app = Flask(__name__)

# Load the model for generating search terms from abstracts
search_model = pipeline("text2text-generation", model="google/flan-t5-small")

# SerpAPI key for Google Scholar search
SERPAPI_KEY = "238d90f4c012cb3cdafa4af07989f9d94c765aa45ae70ac4263d8c7764e787c2"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract_search_terms', methods=['POST'])
def extract_search_terms():
    data = request.json
    abstract = data.get('abstract')

    if not abstract:
        return jsonify({"error": "Abstract is required"}), 400

    query = f"Extract the key search terms from this research abstract: {abstract}"
    response = search_model(query)

    return jsonify({"search_terms": response[0]['generated_text']}), 200

@app.route('/search_papers', methods=['POST'])
def search_papers():
    data = request.json
    search_terms = data.get('search_terms')

    if not search_terms:
        return jsonify({"error": "Search terms are required"}), 400

    params = {
        "q": search_terms,
        "api_key": SERPAPI_KEY,
        "engine": "google_scholar",
        "num": 5  
    }
    response = requests.get("https://serpapi.com/search.json", params=params)

    if response.status_code != 200:
        return jsonify({"error": "Error fetching papers from Google Scholar"}), 500

    result = response.json()

    papers = []
    for paper in result.get('organic_results', []):
        papers.append({
            "title": paper.get('title'),
            "link": paper.get('link')
        })

    return jsonify({"papers": papers}), 200

def download_paper_from_scihub(paper_url):
    options = webdriver.ChromeOptions()
   
    driver = webdriver.Chrome(options=options)

    try:
        print("Loading Sci-Hub page...")
        driver.get("https://sci-hub.se")
        
        time.sleep(2)

        input_field = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "request"))
        )

        input_field.clear()
        
        print(f"Pasting the URL: {paper_url}")
        driver.execute_script("arguments[0].value = arguments[1];", input_field, paper_url)

        input_field.click()

        input_field.send_keys(Keys.RETURN)  

        print("Submitted the URL. Waiting for the paper to process...")
        time.sleep(5)  
        
        print("Looking for the download icon...")
        download_button = WebDriverWait(driver, 50).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[onclick^="location.href="]'))
        )
        
        print("Download icon found! Clicking to start the download.")
        download_button.click()
        
        print("Press 'Q' to close the browser window.")
        
        while True:
            if keyboard.is_pressed('q'):
                print("Q key pressed, closing the browser window.")
                break
            time.sleep(0.1) 

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit() 

@app.route('/download_paper', methods=['POST'])
def download_paper():
    data = request.json
    paper_url = data.get('paper_url')

    if not paper_url:
        return jsonify({"error": "Paper URL is required"}), 400

    download_paper_from_scihub(paper_url)

    return jsonify({"message": "Sci-Hub download process initiated."}), 200

if __name__ == '__main__':
    app.run(debug=True)