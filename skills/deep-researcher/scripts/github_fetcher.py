import sys
import requests
import re

def normalize_github_url(url):
    """
    Converts a standard GitHub URL (blob/main) to its Raw equivalent.
    """
    if 'raw.githubusercontent.com' in url:
        return url
    
    # https://github.com/USER/REPO/blob/BRANCH/PATH -> https://raw.githubusercontent.com/USER/REPO/BRANCH/PATH
    pattern = r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)"
    match = re.match(pattern, url)
    if match:
        user, repo, branch, path = match.groups()
        return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"
    
    # Handle tree URLs (best effort, maybe it should be handled differently)
    return url

def fetch_raw(url):
    try:
        raw_url = normalize_github_url(url)
        print(f"📡 Fetching from: {raw_url}...", file=sys.stderr)
        resp = requests.get(raw_url, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return f"Error: Failed to fetch {url}. Reason: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python github_fetcher.py <github_url>")
        sys.exit(1)
        
    url = sys.argv[1]
    content = fetch_raw(url)
    print(content)
