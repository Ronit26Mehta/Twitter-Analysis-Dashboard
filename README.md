

# Rakshak: Twitter Analysis Dashboard

Rakshak is a multi-platform social media analytics project, and this module focuses on the in-depth analysis of Twitter data. The objective is to process, visualize, and extract actionable insights from tweets, including sentiment analysis, trend detection, political bias examination, and network/term co-occurrence analysis. This dashboard integrates data from additional sources such as Reddit and other social media to provide a holistic view of the online discourse.

## Table of Contents

- [Project Overview](#project-overview)
- [File and Directory Structure](#file-and-directory-structure)
- [Installation and Setup](#installation-and-setup)
- [Data Processing Pipeline](#data-processing-pipeline)
- [Visualizations and Reporting](#visualizations-and-reporting)
- [Dashboard Functionality](#dashboard-functionality)
- [Usage and Customization](#usage-and-customization)
- [Future Work and Extensions](#future-work-and-extensions)
- [License and Acknowledgments](#license-and-acknowledgments)

---
## video  overiview:
https://drive.google.com/drive/folders/1-MxTBKAqpKGU_-CItFsLAs-h8wKpYVMC

## Project Overview

Rakshak’s Twitter Analysis module is designed to help users:
- **Monitor Trends:** Track daily tweet counts, sentiment trends, and term co-occurrence.
- **Understand Sentiment:** Analyze tweet sentiments over time and in relation to political affiliations.
- **Explore Networks:** Visualize tweet interactions, term co-occurrence graphs, and user location maps.
- **Integrate Multi-Source Data:** Complement Twitter data with Reddit and other social media platforms to enrich the analysis.

This module is built with both backend and frontend components, ensuring robust data processing along with an interactive, user-friendly dashboard.

---

## File and Directory Structure

```
user4/
├── analyzed_tweets.csv            # Processed tweets with analysis outputs.
├── tweets.csv                     # Raw tweet data.
├── users.csv                      # User information for tweet authors.
├── reddit_data.csv                # Data collected from Reddit.
├── social_media_data.csv          # Additional social media dataset.
├── filtered_mbfc_fact_1.csv       # Filtered data from an external source.
├── x.com.json                     # Data from the x.com platform.
│
├── backend.py                     # Server-side processing and API endpoints.
├── frontend.py                    # Frontend dashboard interface code.
├── bc1.py ... bc6.py              # Backend modules for various analysis tasks.
├── fn.py ... fn6.py               # Functional scripts for data processing and visualizations.
├── main.ipynb                     # Interactive notebook for prototyping and analysis.
├── twitter_analysis_report.md     # Detailed report of analysis methodology and findings.
├── requirements.txt               # Python dependencies for the project.
│
├── cooccurrence_heatmap.png       # Visual heatmap of term co-occurrences.
├── daily_tweet_count_trend.png    # Trend chart of tweet counts over time.
├── political_distribution.png     # Analysis of political bias in tweets.
├── sentiment_time_series.png      # Time series of tweet sentiment scores.
├── sentiment_trend.png            # Overall sentiment trends over time.
├── sentiment_vs_politics.png      # Comparative analysis of sentiment and political leaning.
├── top_languages.png              # Language distribution among tweets.
├── wordcloud.png                  # Word cloud visualization of tweet content.
│
├── term_cooccurrence_graph.html   # Interactive term co-occurrence graph.
├── tweet_locations.html           # Interactive map showing tweet locations.
├── tweet_time_series.html         # Interactive time series visualization of tweet activity.
├── tweet_time_series_map.html     # Map-based time series visualization.
├── user_locations_map.html        # Interactive map of user locations.
│
└── lib/                           # Frontend libraries and assets.
    ├── bindings/
    │   └── utils.js               # Utility functions for frontend interactions.
    ├── tom-select/
    │   ├── tom-select.complete.min.js  # Enhances HTML select elements.
    │   └── tom-select.css          # Styling for Tom Select.
    └── vis-9.1.2/
        ├── vis-network.min.js      # JavaScript library for network visualizations.
        └── vis-network.css         # CSS styling for network graphs.
```

### Key Components

- **Data Files:**  
  CSV and JSON files that store raw and processed data from Twitter, Reddit, and other sources.

- **Processing Scripts:**  
  Python scripts (`backend.py`, `bc*.py`, and `fn*.py`) handle data ingestion, cleaning, analysis, and API endpoints for the dashboard.

- **Visual Outputs:**  
  PNG images and interactive HTML reports visualize trends, networks, sentiments, and geographic distributions.

- **Frontend Assets:**  
  The `lib` directory includes third-party libraries that enhance interactivity and visualization capabilities.

---

## Installation and Setup

### Prerequisites
- Python 3.7 or above
- pip (Python package installer)
- A modern web browser for dashboard visualization

### Setup Instructions

1. **Clone the Repository:**
   ```bash
   git clone https://your-repository-link.git
   cd your-repository-folder
   ```

2. **Install Dependencies:**
   Use the provided `requirements.txt` to install necessary Python packages:
   ```bash
   pip install -r user4/requirements.txt
   ```

3. **Run the Backend Server:**
   Launch the server which handles data processing:
   ```bash
   python user4/backend.py
   ```

4. **Open the Dashboard:**
   Open the `frontend.py` or directly open the HTML files (e.g., `tweet_time_series.html`) in your browser to interact with the dashboard.

5. **Interactive Analysis:**
   You can also launch the Jupyter Notebook for exploratory analysis:
   ```bash
   jupyter notebook user4/main.ipynb
   ```

---

## Data Processing Pipeline

The Twitter Analysis module processes data through the following steps:

1. **Data Collection:**
   - **Twitter Data:** Tweets are collected in `tweets.csv`.
   - **Multi-Platform Integration:** Data from Reddit (`reddit_data.csv`), social media (`social_media_data.csv`), and other external sources (`x.com.json`) are also incorporated.

2. **Data Cleaning and Preprocessing:**
   - Scripts in `fn.py` and subsequent functional modules perform cleaning, deduplication, and filtering.
   - `filtered_mbfc_fact_1.csv` contains curated data for quality analysis.

3. **Analysis Modules:**
   - **Sentiment Analysis:** Using `bc*` scripts, tweets are analyzed for sentiment over time (visualized in `sentiment_time_series.png` and `sentiment_trend.png`).
   - **Political Bias:** Analysis of political leanings is visualized in `political_distribution.png` and `sentiment_vs_politics.png`.
   - **Network and Co-occurrence:** Term co-occurrence and network analysis generate heatmaps and interactive graphs (`cooccurrence_heatmap.png` and `term_cooccurrence_graph.html`).

4. **Visualization and Reporting:**
   - Visual outputs such as line charts, heatmaps, and word clouds are generated.
   - The detailed analysis report is documented in `twitter_analysis_report.md`.

---

## Visualizations and Reporting

### Key Visuals

- **Co-occurrence Heatmap:**  
  Visualizes the frequency with which key terms appear together in tweets.

- **Daily Tweet Count Trend:**  
  Displays how tweet volume changes over time, highlighting peak activity periods.

- **Sentiment Analysis:**
  - **Time Series:** Shows sentiment fluctuations.
  - **Trend Comparison:** Links sentiment scores with political leanings.

- **Network Graphs:**  
  Interactive HTML-based graphs present term co-occurrences and user interaction networks.

- **Geographic Maps:**  
  Maps (e.g., `tweet_locations.html`, `user_locations_map.html`) provide spatial context for tweet origins and user locations.

---

## Dashboard Functionality

The interactive dashboard offers:
- **Real-Time Updates:**  
  Dynamic visualizations reflect current trends and analysis results.
- **Interactive Elements:**  
  Clickable elements and filters allow users to explore specific time periods, languages, or topics.
- **API Endpoints:**  
  The backend exposes data endpoints that the frontend dashboard uses to refresh content and maintain interactivity.

---

## Usage and Customization

### Running the Analysis

- **Automated Data Processing:**  
  The backend scripts run periodic data ingestion and analysis tasks, ensuring up-to-date results.
- **Custom Queries:**  
  Users can adjust parameters (e.g., time frames, keywords) directly from the dashboard to tailor the analysis.

### Customization Tips

- **Extending Analysis Modules:**  
  Developers can add new Python scripts (e.g., additional `bc*` or `fn*` files) to incorporate new analytical methods.
- **Dashboard Styling:**  
  Modify the assets in the `lib` folder (e.g., CSS files) to adjust the look and feel of the interface.
- **Data Integration:**  
  Easily integrate new data sources by adding corresponding CSV or JSON files and updating the data processing pipeline.

---

## Future Work and Extensions

### Scalability Enhancements
- **Big Data Integration:**  
  Plan to integrate scalable solutions (e.g., Apache Spark) for handling larger datasets.
- **Real-Time Streaming:**  
  Implement real-time data streams for immediate trend analysis.

### Additional Data Sources
- **Expanded Social Media:**  
  Integrate more platforms to offer a broader analysis.
- **Deep Learning Enhancements:**  
  Explore advanced machine learning models for more nuanced sentiment and network analysis.

### Community and Feedback
- **Open Source Contributions:**  
  Contributions, improvements, and feature requests are welcome.
- **Documentation Updates:**  
  Continuous updates will be made as new analysis methods are integrated.

---

## License and Acknowledgments

