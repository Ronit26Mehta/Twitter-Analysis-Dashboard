
# Twitter Data Analysis Report

## Overview
- Total Tweets Analyzed: 33
- Unique Users: 32
- Average Sentiment Score: 0.08

## Political Distribution
political_inclination
neutral          30
right-leaning     3

## Top Topics
- Topic 1: ww2, churchill, did, military, white, winston, don, people, generation, order
- Topic 2: europe, ww2, right, ww3, need, nazis, ussr, america, don, going
- Topic 3: ww3, wants, fighting, won, weapons, going, ukraine, people, nation, hasn
- Topic 4: ww2, world, like, think, need, europe, war, america, saved, don
- Topic 5: ww2, war, start, world, won, allied, grandfather, allies, order, ussr

## Key Findings
- Non-English tweets are detected using langdetect and translated to English via googletrans.
- Two maps are generated: one showing user locations and one (time-series) showing tweet-extracted geolocations.
- Linear regression on tweet index provides a trend line for sentiment, and daily tweet counts are analyzed.
- Topic modeling (LDA) identifies distinct themes within the tweets.

## Generated Visualizations
- Wordcloud of keywords
- Keyword co-occurrence heatmap
- User locations map
- Time-series map of tweet-extracted locations
- Sentiment trend line (with linear regression)
- Daily tweet count trend
- Political inclination distribution and sentiment vs. politics scatter plot
