from fastapi import FastAPI
import tldextract
import whois
from datetime import datetime

app = FastAPI(
    title="News Reliability Checker API",
    description="API to fetch WHOIS data and check reliability.",
    version="1.0.0"
)

def extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    try:
        extracted = tldextract.extract(url)
        return f"{extracted.domain}.{extracted.suffix}".lower()
    except Exception:
        return ""

@app.get("/whois", summary="Fetch WHOIS data for a domain")
async def get_whois(url: str):
    """Endpoint to fetch WHOIS data for a given URL."""
    domain = extract_domain(url)
    if not domain:
        return {"error": "Invalid URL format"}
    
    try:
        w = whois.whois(url)
        creation_date = w.creation_date
        expiration_date = w.expiration_date
        registrar = w.registrar
        
        # Handle lists in dates
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        if isinstance(expiration_date, list):
            expiration_date = expiration_date[0]
        
        # Calculate domain age
        domain_age = None
        if creation_date and isinstance(creation_date, datetime):
            domain_age = (datetime.now() - creation_date).days / 365.25
        
        return {
            "domain": domain,
            "creation_date": str(creation_date) if creation_date else "Unknown",
            "expiration_date": str(expiration_date) if expiration_date else "Unknown",
            "registrar": registrar if registrar else "Unknown",
            "domain_age_years": round(domain_age, 2) if domain_age else "Unknown"
        }
    except Exception as e:
        return {"error": f"WHOIS lookup failed: {str(e)}"}