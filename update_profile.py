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
    """Update README.md or profile.md with top starred repositories."""
    if not repos:
        print("No repositories to update")
        return False
    
    # Try to find file with markers - check README.md first, then profile.md
    target_file = None
    for candidate_file in [readme_file, 'profile.md']:
        try:
            with open(candidate_file, 'r', encoding='utf-8') as f:
                test_content = f.read()
                # Check if file has at least one REPO marker
                if '<!-- REPO_1_START -->' in test_content:
                    target_file = candidate_file
                    content = test_content
                    print(f"Found markers in {candidate_file}")
                    break
        except FileNotFoundError:
            continue
    
    if not target_file:
        print(f"Error: Neither {readme_file} nor profile.md contains REPO markers")
        return False
    
    # Extract username from first repo
    username = repos[0].get('owner', {}).get('login', 'YOUR_USERNAME')
    if not username or username == 'YOUR_USERNAME':
        print(f"Error: Invalid username extracted from repos")
        return False
    
    # Get current date for cache busting (changes daily to force refresh)
    cache_date = datetime.now().strftime('%Y%m%d')  # Format: YYYYMMDD
    
    # Update each repository placeholder
    updated = False
    for i, repo in enumerate(repos[:6], 1):
        repo_name = repo.get('name', '')
        repo_url = repo.get('html_url', '')
        
        if not repo_name or not repo_url:
            print(f"Warning: Skipping REPO_{i} - missing name or URL")
            continue
        
        # GitHub Stats API expects unencoded usernames and repo names
        # Only encode if there are special characters that need it (spaces, etc.)
        # Most GitHub usernames/repos are safe without encoding
        # Create GitHub Stats API card URL
        # Using show_owner=false to show repo name instead of username/repo format
        stats_url = f'https://github-readme-stats.vercel.app/api/pin/?username={username}&repo={repo_name}&theme=dark&hide_border=true'
        
        # Create the markdown card with proper alt text (escape special chars in alt text)
        alt_text = repo_name.replace('[', '\\[').replace(']', '\\]')
        card = f'[![{alt_text}]({stats_url})]({repo_url})'
        
        # Use regex to find and replace between the comment markers
        # Pattern matches: START marker, whitespace/newlines, markdown card, whitespace/newlines, END marker
        # Uses [\s\S] to match any character including newlines (more reliable than . with DOTALL)
        pattern = rf'(<!-- REPO_{i}_START -->)[\s\S]*?\[!\[.*?\]\(.*?\)\]\(.*?\)[\s\S]*?(<!-- REPO_{i}_END -->)'
        replacement = rf'\1\n{card}\n\2'
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            content = new_content
            updated = True
            print(f"✅ Updated REPO_{i}: {repo_name}")
        else:
            print(f"⚠️  No match found for REPO_{i} markers in {target_file}")
    
    # Write updated content
    if updated:
        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Successfully updated {target_file}")
            return True
        except Exception as e:
            print(f"Error writing to {target_file}: {e}")
            return False
    else:
        print(f"No changes detected in {target_file}")
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

