"""Update README.md with top starred repositories for GitHub profile."""
import requests
import os
import re
from typing import List, Dict
from datetime import datetime

# Get token from environment (GitHub Actions provides GITHUB_TOKEN automatically)
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_API_BASE = 'https://api.github.com'


def get_top_starred_repos(username: str = None, limit: int = 6) -> List[Dict]:
    """Fetch top starred repositories for a user."""
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'GitHub-Profile-Update'
    }
    
    # Add token if available (improves rate limits, but not required for public repos)
    if GITHUB_TOKEN:
        headers['Authorization'] = f'Bearer {GITHUB_TOKEN}'
    
    # If no username provided, get authenticated user's repos (requires token)
    if username:
        endpoint = f'/users/{username}/repos'
    else:
        if not GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN is required when username is not provided")
        endpoint = '/user/repos'
    
    # Get all repos, sorted by stars
    repos = []
    page = 1
    per_page = 100
    
    while True:
        url = f"{GITHUB_API_BASE}{endpoint}?sort=stars&direction=desc&per_page={per_page}&page={page}"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"Error fetching repos: {response.status_code} - {response.text[:200]}")
            break
            
        page_repos = response.json()
        if not page_repos:
            break
            
        repos.extend(page_repos)
        
        # If we got less than per_page, we're done
        if len(page_repos) < per_page:
            break
            
        page += 1
    
    # Sort by stars (descending) and return top repos
    repos.sort(key=lambda x: x.get('stargazers_count', 0), reverse=True)
    return repos[:limit]


def update_readme(repos: List[Dict], readme_file: str = 'README.md'):
    """Update README.md with top starred repositories."""
    if not repos:
        print("No repositories to update")
        return False
    
    # Read current README.md
    try:
        with open(readme_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: {readme_file} not found")
        return False
    
    # Extract username from first repo
    username = repos[0].get('owner', {}).get('login', 'YOUR_USERNAME')
    
    # Get current date for cache busting (changes daily to force refresh)
    cache_date = datetime.now().strftime('%Y%m%d')  # Format: YYYYMMDD
    
    # Update each repository placeholder
    updated = False
    for i, repo in enumerate(repos[:6], 1):
        repo_name = repo.get('name', '')
        repo_url = repo.get('html_url', '')
        
        # Create GitHub Stats API card with 1-day cache (86400 seconds)
        # v parameter forces refresh daily when date changes
        card = f'[![{repo_name}](https://github-readme-stats.vercel.app/api/pin/?username={username}&repo={repo_name}&theme=dark&hide_border=true&cache_seconds=86400&v={cache_date})]({repo_url})'
        
        # Use regex to find and replace between the comment markers
        pattern = rf'(<!-- REPO_{i}_START -->\s*)\[!\[.*?\]\(.*?\)\]\(.*?\)(\s*<!-- REPO_{i}_END -->)'
        new_content = re.sub(pattern, rf'\1{card}\2', content, flags=re.DOTALL)
        
        if new_content != content:
            content = new_content
            updated = True
    
    # Write updated content
    if updated:
        try:
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Successfully updated {readme_file}")
            return True
        except Exception as e:
            print(f"Error writing to {readme_file}: {e}")
            return False
    else:
        print("No changes detected in README.md")
        return False


def get_username() -> str:
    """Get authenticated user's username."""
    if not GITHUB_TOKEN:
        return ''
    
    headers = {
        'Authorization': f'Bearer {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'GitHub-Profile-Update'
    }
    
    response = requests.get(f"{GITHUB_API_BASE}/user", headers=headers, timeout=30)
    if response.status_code == 200:
        return response.json().get('login', '')
    return ''


if __name__ == '__main__':
    import sys
    
    print("Fetching top starred repositories...")
    
    # Try to get username from environment (GitHub Actions provides REPO_OWNER)
    # Otherwise try to get from authenticated user
    username = os.getenv('REPO_OWNER') or get_username()
    
    if not username:
        print("Error: Could not determine username")
        sys.exit(1)
    
    print(f"Fetching repos for: {username}")
    
    # Use public API endpoint with username
    repos = get_top_starred_repos(username=username, limit=6)
    print(f"Found {len(repos)} repositories")
    
    # Display top repos
    print("\n" + "="*60)
    print("Top Starred Repositories:")
    print("="*60)
    for i, repo in enumerate(repos, 1):
        name = repo.get('name', '')
        stars = repo.get('stargazers_count', 0)
        language = repo.get('language', 'N/A')
        print(f"{i}. {name} - ⭐ {stars} stars | {language}")
    
    # Update README.md
    print("\nUpdating README.md...")
    success = update_readme(repos, 'README.md')
    
    sys.exit(0 if success else 1)

