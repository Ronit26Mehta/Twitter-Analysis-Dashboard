from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
import pandas as pd
import networkx as nx
import google.generativeai as genai
from pyvis.network import Network
import json
import re
from collections import Counter
import os

# Configure the Google Generative AI API key and model
genai.configure(api_key="AIzaSyBQjwl1U4208zTqqoOvAhjo98ypbCs8Pk4")
model = genai.GenerativeModel("gemini-2.0-flash-exp")

app = FastAPI(
    title="Tweet Term Co-occurrence Analysis API",
    description="API to analyze tweet term co-occurrence networks and return AI analysis along with visualization."
)

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
    # Extract key terms
    key_terms = extract_key_terms(df, min_count=min_term_count, max_terms=max_terms)
    
    # Create a graph
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
    
    # Remove edges below threshold and isolated nodes
    edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if d['weight'] < min_edge_weight]
    G.remove_edges_from(edges_to_remove)
    isolated_nodes = list(nx.isolates(G))
    G.remove_nodes_from(isolated_nodes)
    
    if len(G.nodes()) == 0:
        raise HTTPException(status_code=404, detail="No significant co-occurrences found with current parameters.")
    
    # Identify main node
    main_node, main_degree = max(G.degree(), key=lambda x: x[1])
    
    nodes_count_json = json.dumps({node: data.get('count', 0) for node, data in G.nodes(data=True)}, indent=4)
    loose_threshold = 2
    loosely_linked = [n for n in G.neighbors(main_node) if G.degree(n) <= loose_threshold]
    loosely_linked_json = json.dumps({node: G.degree(node) for node in loosely_linked}, indent=4)
    
    # Create Pyvis network visualization
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
    
    # Generate AI analysis of the network
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
async def get_visualization(file: str = "term_cooccurrence_graph.html"):
    """
    Serve the generated HTML visualization.
    """
    if not os.path.exists(file):
        raise HTTPException(status_code=404, detail=f"{file} not found.")
    return FileResponse(file, media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
