from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from pydantic import BaseModel
import pandas as pd
import uvicorn
import os
import json
import time
import csv
import re
import networkx as nx
from collections import Counter
from pyvis.network import Network
# For query scraping using Selenium and BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# For topic modeling
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer

# For Gemini API calls (query and analysis)
import google.generativeai as genai

# Configure the Google Generative AI API key and model
genai.configure(api_key="AIzaSyBQjwl1U4208zTqqoOvAhjo98ypbCs8Pk4")
model = genai.GenerativeModel("gemini-2.0-flash-exp")

# CSV file names
TWEETS_CSV = "tweets.csv"
USERS_CSV = "users.csv"

app = FastAPI(
    title="Twitter Data Analysis API",
    description=("API endpoints to display analyzed tweets data, query Twitter, " 
                 "perform semantic visualization via topic modeling, and analyze term co-occurrence networks.")
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
    except json.JSONDecodeError:
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
    except Exception:
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
    except Exception:
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
        except Exception:
            continue
    return tweets_data

def preprocess_text(text: str):
    """
    Preprocess tweet text to extract meaningful terms.
    """
    if not isinstance(text, str):
        return []
    text = text.lower()
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    tokens = text.split()
    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'if', 'in', 'on', 'at', 'to', 'for', 'with',
                  'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
                  'does', 'did', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'this', 'that', 'of',
                  'from', 'by', 'my', 'your', 'his', 'her', 'its', 'our', 'their'}
    tokens = [token for token in tokens if token not in stop_words and len(token) > 2]
    return tokens

def extract_key_terms(tweets_df: pd.DataFrame, min_count: int = 2, max_terms: int = 500):
    """
    Extract key terms from all tweets based on frequency.
    """
    all_terms = []
    for text in tweets_df['text']:
        all_terms.extend(preprocess_text(text))
    term_counts = Counter(all_terms)
    key_terms = {term: count for term, count in term_counts.items() if count >= min_count}
    if len(key_terms) > max_terms:
        key_terms = dict(sorted(key_terms.items(), key=lambda x: x[1], reverse=True)[:max_terms])
    return key_terms

def visualize_term_cooccurrence(
    df: pd.DataFrame,
    min_term_count: int = 2,
    max_terms: int = 200,
    min_edge_weight: int = 2,
    output_file: str = "term_cooccurrence_graph.html"
):
    """
    Creates and visualizes a term co-occurrence network from tweets.
    """
    key_terms = extract_key_terms(df, min_count=min_term_count, max_terms=max_terms)
    G = nx.Graph()
    for _, row in df.iterrows():
        if not isinstance(row['text'], str):
            continue
        tweet_terms = preprocess_text(row['text'])
        tweet_terms = [term for term in tweet_terms if term in key_terms]
        for i in range(len(tweet_terms)):
            for j in range(i+1, len(tweet_terms)):
                term1, term2 = tweet_terms[i], tweet_terms[j]
                if not G.has_node(term1):
                    G.add_node(term1, count=key_terms[term1])
                if not G.has_node(term2):
                    G.add_node(term2, count=key_terms[term2])
                if G.has_edge(term1, term2):
                    G[term1][term2]['weight'] += 1
                else:
                    G.add_edge(term1, term2, weight=1)
    edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if d['weight'] < min_edge_weight]
    G.remove_edges_from(edges_to_remove)
    isolated_nodes = list(nx.isolates(G))
    G.remove_nodes_from(isolated_nodes)
    if len(G.nodes()) == 0:
        raise HTTPException(status_code=404, detail="No significant co-occurrences found with current parameters.")
    main_node, main_degree = max(G.degree(), key=lambda x: x[1])
    nodes_count_json = json.dumps({node: data.get('count', 0) for node, data in G.nodes(data=True)}, indent=4)
    loose_threshold = 2
    loosely_linked = [n for n in G.neighbors(main_node) if G.degree(n) <= loose_threshold]
    loosely_linked_json = json.dumps({node: G.degree(node) for node in loosely_linked}, indent=4)
    net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="black", notebook=False, select_menu=True)
    net.barnes_hut(gravity=-20000, central_gravity=0.3, spring_length=250, spring_strength=0.001)
    for node, attr in G.nodes(data=True):
        count = attr.get('count', 0)
        net.add_node(node, title=f"Term: {node}<br>Frequency: {count}<br>Connections: {G.degree(node)}", value=count)
    for u, v, attr in G.edges(data=True):
        weight = attr.get('weight', 1)
        net.add_edge(u, v, value=weight, title=f"Co-occurrence: {weight}")
    max_count = max([data.get('count', 1) for _, data in G.nodes(data=True)])
    min_size, max_size = 10, 50
    for node in net.nodes:
        node_id = node.get('id')
        if node_id in G.nodes:
            count = G.nodes[node_id].get('count', 1)
            size = min_size + (count / max_count) * (max_size - min_size)
            node.update({"size": size})
    net.set_options("""
    var options = {
      "nodes": {
        "borderWidth": 2,
        "scaling": {"min": 10, "max": 50},
        "color": {"border": "#2B7CE9", "background": "#97C2FC"},
        "font": {"size": 16, "face": "arial", "color": "#343434", "align": "center"}
      },
      "edges": {
        "color": {"color": "#848484", "inherit": false},
        "smooth": {"enabled": true, "type": "dynamic"},
        "width": 0.5
      },
      "physics": {
        "barnesHut": {"gravitationalConstant": -20000, "centralGravity": 0.3, "springLength": 250, "springConstant": 0.001},
        "minVelocity": 0.75
      }
    }
    """)
    prompt = f'''
    I have created a graph showing how terms co-occur in tweets from Twitter data.
    The main term is '{main_node}' which has {main_degree} connections.
    
    These are my terms and their frequencies:
    {nodes_count_json}
    
    These are terms loosely linked to my main term:
    {loosely_linked_json}
    
    Give me an analysis of the key topics and themes in this conversation network.
    Identify any clusters of terms that might represent distinct narratives or topics.
    
    Output in JSON format with:
    - key_themes: list of main themes/topics identified
    - topic_clusters: object with cluster names as keys and relevant terms as values
    - interesting_insights: list of 3-5 observations about the data
    - summary_report: brief analysis of what this term network reveals
    '''
    try:
        response = model.generate_content(prompt)
        analysis_text = response.text
        if '```json' in analysis_text:
            analysis_text = analysis_text.split('```json')[1].split('```')[0].strip()
        elif '```' in analysis_text:
            analysis_text = analysis_text.split('```')[1].split('```')[0].strip()
        analysis_json = json.loads(analysis_text)
    except Exception as e:
        analysis_json = {
            "key_themes": ["Analysis not available"],
            "summary_report": "Could not generate analysis due to an error.",
            "error": str(e)
        }
    net.write_html(output_file)
    return G, analysis_json, output_file

def analyze_tweets_cooccurrence(
    tweets_file: str,
    min_term_count: int = 2,
    max_terms: int = 200,
    min_edge_weight: int = 2
):
    """
    Loads tweets, performs co-occurrence analysis, and returns the graph and AI analysis.
    """
    try:
        df = pd.read_csv(tweets_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading tweets file: {str(e)}")
    if df.empty or 'text' not in df.columns:
        raise HTTPException(status_code=400, detail="Tweets data is empty or missing 'text' column.")
    graph, analysis, html_file = visualize_term_cooccurrence(
        df,
        min_term_count=min_term_count,
        max_terms=max_terms,
        min_edge_weight=min_edge_weight
    )
    return analysis, html_file

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
    return {"message": ("Welcome to the Twitter Data Analysis API. "
                        "Explore endpoints: /tweets, /report, /maps/{map_name}, /visualizations/{viz_name}, "
                        "/operations, /query, /semantic_visualization, /cooccurrence, and /visualization.")}

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
    Valid viz_name values: wordcloud, cooccurrence_heatmap, sentiment_trend, daily_tweet_count_trend, 
    top_languages, top_mentions, political_distribution, sentiment_vs_politics.
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
    return {"results": results, "message": message}

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
    filtered_df = df[df['text'].str.contains(keyword, case=False, na=False)]
    if filtered_df.empty:
        return {"message": f"No tweets found containing keyword: {keyword}", "topics": {}}
    try:
        vectorizer = CountVectorizer(stop_words='english', max_features=1000)
        dtm = vectorizer.fit_transform(filtered_df['text'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during vectorization: {str(e)}")
    try:
        lda = LatentDirichletAllocation(n_components=n_topics, random_state=42)
        lda.fit(dtm)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during topic modeling: {str(e)}")
    feature_names = vectorizer.get_feature_names_out()
    topics = {}
    for idx, topic in enumerate(lda.components_):
        top_indices = topic.argsort()[-10:][::-1]
        top_words = [feature_names[i] for i in top_indices]
        topics[f"Topic {idx+1}"] = top_words
    return {
        "keyword": keyword,
        "n_topics": n_topics,
        "num_tweets_analyzed": len(filtered_df),
        "topics": topics,
        "message": ("Semantic visualization data generated. "
                    "You can use these topics with visualization tools like TensorFlow Projector, Datamapplot, or Nomic.")
    }

@app.get("/cooccurrence", response_class=JSONResponse)
async def cooccurrence_analysis(
    tweets_file: str = "tweets.csv",
    min_term_count: int = Query(2, ge=1),
    max_terms: int = Query(200, ge=1),
    min_edge_weight: int = Query(2, ge=1)
):
    """
    Endpoint to run term co-occurrence analysis on tweets.
    Returns the AI-generated analysis JSON and path to the visualization HTML file.
    """
    analysis, html_file = analyze_tweets_cooccurrence(
        tweets_file,
        min_term_count=min_term_count,
        max_terms=max_terms,
        min_edge_weight=min_edge_weight
    )
    return {"analysis": analysis, "visualization_file": html_file}

@app.get("/visualization", response_class=FileResponse)
async def get_cooccurrence_visualization(file: str = "term_cooccurrence_graph.html"):
    """
    Serve the generated HTML visualization for term co-occurrence network.
    """
    if not os.path.exists(file):
        raise HTTPException(status_code=404, detail=f"{file} not found.")
    return FileResponse(file, media_type="text/html")

#########################################
# -------------- Main ----------------- #
#########################################

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
