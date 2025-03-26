# backend/main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import re
from urllib.parse import urlparse, parse_qs
from typing import Optional

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
INSTAGRAM_DOMAIN = "www.instagram.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

def extract_shortcode(url: str) -> Optional[str]:
    """Extract the shortcode from an Instagram Reel URL"""
    parsed = urlparse(url)
    if parsed.netloc != INSTAGRAM_DOMAIN and parsed.netloc != f"www.{INSTAGRAM_DOMAIN}":
        return None
    
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) < 2 or path_parts[0] != "reel":
        return None
    
    return path_parts[1]

async def fetch_reel_data(shortcode: str) -> Optional[str]:
    """Fetch reel data from Instagram"""
    api_url = f"https://{INSTAGRAM_DOMAIN}/reel/{shortcode}/?__a=1&__d=dis"
    
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://{INSTAGRAM_DOMAIN}/",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            
            data = response.json()
            video_url = data.get("items", [{}])[0].get("video_versions", [{}])[0].get("url")
            
            return video_url
    except Exception as e:
        print(f"Error fetching reel data: {e}")
        return None

@app.post("/download")
async def download_reel(request: Request):
    data = await request.json()
    url = data.get("url", "").strip()
    
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    shortcode = extract_shortcode(url)
    if not shortcode:
        raise HTTPException(status_code=400, detail="Invalid Instagram Reel URL")
    
    video_url = await fetch_reel_data(shortcode)
    if not video_url:
        raise HTTPException(status_code=404, detail="Could not fetch video. The reel may be private or unavailable.")
    
    return JSONResponse({
        "success": True,
        "video_url": video_url,
        "message": "Video fetched successfully"
    })

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Instagram Reels Downloader API"}

# For local testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)