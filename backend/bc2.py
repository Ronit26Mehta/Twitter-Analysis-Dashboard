from fastapi import FastAPI
from pydantic import BaseModel
import json
import time
import csv
import os
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Import the Gemini API client (from your urls_hashtag.py functionality)
from google import genai  # Ensure this package is installed and configured

app = FastAPI()

# CSV file names for storage
TWEETS_CSV = "tweets.csv"
USERS_CSV = "users.csv"

def init_csv():
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
    with open(cookies_file, "r") as file:
        cookies = json.load(file)
    for cookie in cookies:
        if "sameSite" in cookie and cookie["sameSite"] not in ["Strict", "Lax", "None"]:
            del cookie["sameSite"]
        driver.add_cookie(cookie)

def init_driver(headless=True):
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
    load_cookies(driver)  # Load session cookies from x.com.json
    driver.refresh()
    time.sleep(3)
    return driver

def extract_urls_and_hashtags_gemini(text):
    """
    Extract URLs and hashtags from text using Google's Gemini model.
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
    generated_text = response.candidates[0].content.parts[0].text if response.candidates else ""
    print("Raw API Response:", generated_text)
    cleaned_text = generated_text.strip().strip("```json").strip("```").strip()
    if not cleaned_text:
        print("❌ Error: Empty response received from Gemini API.")
        return "None", "None"
    try:
        extracted_data = json.loads(cleaned_text)
        urls = extracted_data.get("urls", [])
        hashtags = extracted_data.get("hashtags", [])
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")
        return "None", "None"
    urls_text = ", ".join(urls) if urls else "None"
    hashtags_text = ", ".join(hashtags) if hashtags else "None"
    return urls_text, hashtags_text

def scrape_twitter(keyword, driver, max_scrolls=0):
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
            print(f"Error extracting tweet: {e}")
            continue
    return tweets_data

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
        print(f"Error checking user existence: {e}")
        return False

def convert_to_number(text):
    text = text.replace(",", "").strip()
    if text.endswith("M"):
        return int(float(text[:-1]) * 1_000_000)
    if text.endswith("K"):
        return int(float(text[:-1]) * 1_000)
    return int(text) if text.isdigit() else 0

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
        print(f"✅ User info saved for: {username}")
    except Exception as e:
        print(f"❌ Error fetching user info for {username}: {e}")

# Updated Pydantic model now includes a "mode" field.
class QueryRequest(BaseModel):
    userquery: str
    mode: str  # Expected values: "hard" or "soft"

@app.post("/query")
def query_endpoint(payload: QueryRequest):
    init_csv()  # Ensure CSV files are initialized
    driver = init_driver(headless=True)
    
    mode = payload.mode.lower()
    if mode == "hard":
        # Hard mode uses a fixed scroll count of 5
        results = scrape_twitter(payload.userquery, driver, max_scrolls=5)
        message = "Hard scraping completed and CSV files updated."
    elif mode == "soft":
        # Soft mode uses a fixed scroll count of 200
        results = scrape_twitter(payload.userquery, driver, max_scrolls=200)
        message = "Soft scraping completed and CSV files updated."
    else:
        driver.quit()
        return {"error": "Invalid mode. Please specify 'hard' or 'soft'."}
    
    driver.quit()
    
    return {
        "results": results,
        "message": message
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
