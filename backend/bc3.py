from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
import pandas as pd
import uvicorn
import os

app = FastAPI(title="Twitter Data Analysis API", description="API endpoints to display analyzed tweets data, visualizations, and maps.")

@app.get("/")
async def root():
    """
    Root endpoint providing a welcome message.
    """
    return {"message": "Welcome to the Twitter Data Analysis API. Explore endpoints /tweets, /report, /maps/{map_name}, and /visualizations/{viz_name}"}

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
    Endpoint to serve HTML maps.
    Valid map names:
      - user_locations (user_locations_map.html)
      - tweet_timeseries (tweet_time_series_map.html)
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
    Endpoint to serve visualization images.
    Valid viz_name values:
      - wordcloud
      - cooccurrence_heatmap
      - sentiment_trend
      - daily_tweet_count_trend
      - top_languages
      - top_mentions
      - political_distribution
      - sentiment_vs_politics
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

if __name__ == "__main__":
   import uvicorn
   uvicorn.run(app, host="0.0.0.0", port=8000)
