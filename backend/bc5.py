from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel
import pandas as pd
import uvicorn
import os
import json
import time
import csv
import re

# For query scraping using Selenium and BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# For topic modeling
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer

# For Gemini API calls (query endpoint)
# Note: This assumes you have installed and configured the "google" package for Gemini.
# If not, ensure you install it and update accordingly.
from google import genai  

# CSV file names
TWEETS_CSV = "tweets.csv"
USERS_CSV = "users.csv"

app = FastAPI(
    title="Twitter Data Analysis API",
    description="API endpoints to display analyzed tweets data, query Twitter, and perform semantic visualization via topic modeling."
)

#########################################
# ---------- Helper Functions --------- #
#########################################

def init_csv():
    """Initialize CSV files if they do not exist."""
    if not os.path.exists(TWEETS_CSV):
        with open(TWEETS_CSV, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "username", "text", "timestamp", "url", "likes",
                "retweets", "replies", "extracted_urls", "extracted_hashtags"
            ])
    if not os.path.exists(USERS_CSV):
        with open(USERS_CSV, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "username", "display_name", "bio", "location",
                "followers", "profile_url"
            ])

def load_cookies(driver, cookies_file="x.com.json"):
    """Load cookies from a JSON file into the Selenium driver."""
    if os.path.exists(cookies_file):
        with open(cookies_file, "r") as file:
            cookies = json.load(file)
        for cookie in cookies:
            if "sameSite" in cookie and cookie["sameSite"] not in ["Strict", "Lax", "None"]:
                del cookie["sameSite"]
            driver.add_cookie(cookie)

def init_driver(headless=True):
    """Initialize Selenium Chrome driver."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://twitter.com")
    time.sleep(3)
    load_cookies(driver)
    driver.refresh()
    time.sleep(3)
    return driver

def extract_urls_and_hashtags_gemini(text):
    """
    Extract core URLs and hashtags from text using Google's Gemini model.
    """
    client = genai.Client(api_key="AIzaSyBQjwl1U4208zTqqoOvAhjo98ypbCs8Pk4")
    prompt = f"""
Extract only the core URLs (without query parameters, fragments, or extra paths) and hashtags from the following text.

### Example:
- **Input URL:** https://aapsonline.org/bidens-bounty-on-your-life-hospitals-incentive-payments-for-covid-19/
- **Extracted Core URL:** https://aapsonline.org/

### Input Text:
"{text}"

### Output Format (Respond with JSON only, no explanations):
{{
    "urls": ["core URLs only"],
    "hashtags": ["hashtags only"]
}}
"""
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    generated_text = ""
    if response.candidates:
        generated_text = response.candidates[0].content.parts[0].text
    cleaned_text = generated_text.strip().strip("```json").strip("```").strip()
    if not cleaned_text:
        return "None", "None"
    try:
        extracted_data = json.loads(cleaned_text)
        urls = extracted_data.get("urls", [])
        hashtags = extracted_data.get("hashtags", [])
    except json.JSONDecodeError as e:
        return "None", "None"
    urls_text = ", ".join(urls) if urls else "None"
    hashtags_text = ", ".join(hashtags) if hashtags else "None"
    return urls_text, hashtags_text

def convert_to_number(text):
    """Convert text like '1.2K' or '3M' to a number."""
    text = text.replace(",", "").strip()
    if text.endswith("M"):
        return int(float(text[:-1]) * 1_000_000)
    if text.endswith("K"):
        return int(float(text[:-1]) * 1_000)
    return int(text) if text.isdigit() else 0

def check_user_exists(username):
    username = username.strip().lower()
    if not os.path.exists(USERS_CSV):
        return False
    try:
        df = pd.read_csv(USERS_CSV, usecols=["username"], dtype=str)
        if df.empty or "username" not in df.columns:
            return False
        existing_usernames = df["username"].str.strip().str.lower()
        return username in existing_usernames.values
    except Exception as e:
        return False

def fetch_user_info(username, driver):
    profile_url = f"https://twitter.com/{username}"
    driver.get(profile_url)
    time.sleep(5)
    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        display_name_element = soup.find("div", {"data-testid": "UserName"})
        display_name = "Unknown"
        if display_name_element:
            name_span = display_name_element.find("span")
            display_name = name_span.text.strip() if name_span else "Unknown"
        bio_element = soup.find("div", {"data-testid": "UserDescription"})
        bio = bio_element.text.strip() if bio_element else "No bio"
        location_element = soup.find("span", {"data-testid": "UserLocation"})
        location = "Not provided"
        if location_element:
            location_span = location_element.find("span")
            location = location_span.text.strip() if location_span else "Not provided"
        followers_count = 0
        followers_element = soup.find("a", href=lambda href: href and "verified_followers" in href)
        if followers_element:
            followers_span = followers_element.find("span")
            if followers_span:
                followers_text = followers_span.text.strip()
                followers_count = convert_to_number(followers_text)
        with open(USERS_CSV, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([username, display_name, bio, location, followers_count, profile_url])
    except Exception as e:
        pass

def scrape_twitter(keyword, driver, max_scrolls=0):
    """Scrape Twitter for live tweets matching the keyword."""
    search_url = f"https://twitter.com/search?q={keyword.replace(' ', '%20')}&f=live"
    driver.get(search_url)
    time.sleep(5)
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    while scroll_count < max_scrolls:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scroll_count += 1
    soup = BeautifulSoup(driver.page_source, "html.parser")
    tweets_data = []
    tweets = soup.find_all("article")
    for tweet in tweets:
        try:
            user_element = tweet.find("a", href=True)
            username = user_element["href"] if user_element else "N/A"
            username = username.split("/")[1] if username else "N/A"
            text_element = tweet.find("div", {"lang": True})
            text = text_element.text.strip() if text_element else "N/A"
            time_element = tweet.find("time")
            timestamp = time_element["datetime"] if time_element else "N/A"
            link = "N/A"
            if time_element and time_element.parent and time_element.parent.name == "a":
                link = "https://twitter.com" + time_element.parent["href"]
            likes, retweets, replies = 0, 0, 0
            engagement_buttons = tweet.find_all("button", attrs={"aria-label": True})
            for button in engagement_buttons:
                label = button["aria-label"]
                match = re.search(r"(\d+)\s*(reply|replies)", label, re.IGNORECASE)
                if match:
                    replies = int(match.group(1))
                match = re.search(r"(\d+)\s*(repost|retweet|retweets)", label, re.IGNORECASE)
                if match:
                    retweets = int(match.group(1))
                match = re.search(r"(\d+)\s*(like|likes)", label, re.IGNORECASE)
                if match:
                    likes = int(match.group(1))
            extracted_urls, extracted_hashtags = extract_urls_and_hashtags_gemini(text)
            with open(TWEETS_CSV, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([
                    username, text, timestamp, link,
                    likes, retweets, replies, extracted_urls, extracted_hashtags
                ])
            tweet_info = {
                "username": username,
                "text": text,
                "timestamp": timestamp,
                "url": link,
                "likes": likes,
                "retweets": retweets,
                "replies": replies,
                "extracted_urls": extracted_urls,
                "extracted_hashtags": extracted_hashtags
            }
            tweets_data.append(tweet_info)
            if not check_user_exists(username):
                fetch_user_info(username, driver)
        except Exception as e:
            continue
    return tweets_data

#########################################
# ----------- Pydantic Models --------- #
#########################################

class QueryRequest(BaseModel):
    userquery: str
    mode: str  # Expected values: "hard" or "soft"

#########################################
# ----------- Endpoints  ------------- #
#########################################

@app.get("/")
async def root():
    """
    Root endpoint providing a welcome message.
    """
    return {"message": "Welcome to the Twitter Data Analysis API. Explore endpoints: /tweets, /report, /maps/{map_name}, /visualizations/{viz_name}, /query, and /semantic_visualization."}

@app.get("/tweets", response_class=JSONResponse)
async def get_tweets():
    """
    Return all the enriched tweet data as JSON.
    """
    try:
        df = pd.read_csv("analyzed_tweets.csv")
        data = df.to_dict(orient="records")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading CSV file: {str(e)}")

@app.get("/report", response_class=PlainTextResponse)
async def get_report():
    """
    Return the AI-generated analysis report (in Markdown).
    """
    try:
        with open("twitter_analysis_report.md", "r", encoding="utf-8") as f:
            report = f.read()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading report file: {str(e)}")

@app.get("/maps/{map_name}")
async def get_map(map_name: str):
    """
    Serve HTML maps. Valid map names: user_locations, tweet_timeseries.
    """
    if map_name == "user_locations":
        file_path = "user_locations_map.html"
    elif map_name == "tweet_timeseries":
        file_path = "tweet_time_series_map.html"
    else:
        raise HTTPException(status_code=404, detail="Map not found")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail=f"{file_path} does not exist.")
    
    return FileResponse(file_path, media_type="text/html")

@app.get("/visualizations/{viz_name}")
async def get_visualization(viz_name: str):
    """
    Serve visualization images.
    Valid viz_name values: wordcloud, cooccurrence_heatmap, sentiment_trend, daily_tweet_count_trend, top_languages, top_mentions, political_distribution, sentiment_vs_politics.
    """
    allowed = {
        "wordcloud": "wordcloud.png",
        "cooccurrence_heatmap": "cooccurrence_heatmap.png",
        "sentiment_trend": "sentiment_trend.png",
        "daily_tweet_count_trend": "daily_tweet_count_trend.png",
        "top_languages": "top_languages.png",
        "top_mentions": "top_mentions.png",
        "political_distribution": "political_distribution.png",
        "sentiment_vs_politics": "sentiment_vs_politics.png"
    }
    if viz_name not in allowed:
        raise HTTPException(status_code=404, detail="Visualization not found")
    
    file_path = allowed[viz_name]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail=f"{file_path} does not exist.")
    
    return FileResponse(file_path, media_type="image/png")

@app.get("/operations")
async def list_operations():
    """
    Returns a list of operations performed during analysis.
    """
    operations = {
        "1": "Sorted tweets by timestamp",
        "2": "Detected tweet language using langdetect",
        "3": "Translated non-English tweets using googletrans",
        "4": "Extracted keywords using TF-IDF",
        "5": "Computed sentiment scores (sentence and keywords)",
        "6": "Extracted geographic locations and geocoded them using spaCy and geopy",
        "7": "Extracted mentioned users via regex",
        "8": "Assessed political inclination based on keywords",
        "9": "Created wordcloud and co-occurrence heatmap",
        "10": "Plotted linear regression trend for tweet sentiment",
        "11": "Plotted daily tweet count trend with regression",
        "12": "Created maps for user locations and tweet geolocations",
        "13": "Performed topic modeling using LDA",
        "14": "Created additional visualizations for top entities"
    }
    return operations

@app.post("/query")
def query_endpoint(payload: QueryRequest):
    """
    Query endpoint to scrape Twitter based on a keyword.
    Mode:
      - "hard": Uses max_scrolls=5
      - "soft": Uses max_scrolls=200
    """
    init_csv()  # Ensure CSV files are initialized
    driver = init_driver(headless=True)
    
    mode = payload.mode.lower()
    if mode == "hard":
        results = scrape_twitter(payload.userquery, driver, max_scrolls=5)
        message = "Hard scraping completed and CSV files updated."
    elif mode == "soft":
        results = scrape_twitter(payload.userquery, driver, max_scrolls=200)
        message = "Soft scraping completed and CSV files updated."
    else:
        driver.quit()
        raise HTTPException(status_code=400, detail="Invalid mode. Please specify 'hard' or 'soft'.")
    
    driver.quit()
    return {
        "results": results,
        "message": message
    }

@app.get("/semantic_visualization", response_class=JSONResponse)
def semantic_visualization(keyword: str = Query(..., description="Keyword to filter tweets for semantic analysis."),
                           n_topics: int = Query(5, description="Number of topics to extract.")):
    """
    Perform topic modeling on tweets that contain the given keyword.
    This endpoint filters the tweets based on the keyword, applies LDA topic modeling,
    and returns the top words for each topic.
    """
    try:
        df = pd.read_csv("analyzed_tweets.csv")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading tweets file: {str(e)}")
    
    if df.empty or "text" not in df.columns:
        raise HTTPException(status_code=400, detail="Tweets data is empty or missing 'text' column.")
    
    # Filter tweets containing the keyword (case-insensitive)
    filtered_df = df[df['text'].str.contains(keyword, case=False, na=False)]
    if filtered_df.empty:
        return {"message": f"No tweets found containing keyword: {keyword}", "topics": []}
    
    # Use CountVectorizer and LDA to extract topics
    vectorizer = CountVectorizer(stop_words='english', max_features=1000)
    dtm = vectorizer.fit_transform(filtered_df['text'])
    
    lda = LatentDirichletAllocation(n_components=n_topics, random_state=42)
    lda.fit(dtm)
    
    feature_names = vectorizer.get_feature_names_out()
    topics = {}
    for idx, topic in enumerate(lda.components_):
        top_indices = topic.argsort()[-10:][::-1]
        top_words = [feature_names[i] for i in top_indices]
        topics[f"Topic {idx+1}"] = top_words
    
    # Return the topics as JSON (for further visualization with external tools if desired)
    return {
        "keyword": keyword,
        "n_topics": n_topics,
        "num_tweets_analyzed": len(filtered_df),
        "topics": topics,
        "message": "Semantic visualization data generated. You can use these topics with visualization tools like TensorFlow Projector, Datamapplot, or Nomic."
    }

#########################################
# -------------- Main ----------------- #
#########################################

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
