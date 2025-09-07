"""
Git Analysis Utility for tracking endpoint contributions.

This module provides functionality to analyze git history and identify
which developers contributed to creating/modifying API endpoints.
"""

import subprocess
import re
import os
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GitEndpointAnalyzer:
    """Analyzes git history to track endpoint contributions."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize the analyzer with repository path."""
        self.repo_path = Path(repo_path).resolve()
        self.endpoint_patterns = [
            r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            r'@app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
        ]
    
    def _run_git_command(self, cmd: List[str]) -> str:
        """Run a git command and return the output."""
        try:
            result = subprocess.run(
                ["git"] + cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(cmd)}, Error: {e.stderr}")
            return ""
    
    def _extract_endpoints_from_content(self, content: str) -> Set[Tuple[str, str]]:
        """Extract endpoints from file content."""
        endpoints = set()
        for pattern in self.endpoint_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                method = match.group(1).upper()
                path = match.group(2)
                endpoints.add((method, path))
        return endpoints
    
    def _get_file_endpoints(self, file_path: str) -> Set[Tuple[str, str]]:
        """Get current endpoints from a file."""
        try:
            full_path = self.repo_path / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return self._extract_endpoints_from_content(content)
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")
        return set()
    
    def _get_commit_info(self, commit_hash: str) -> Dict[str, str]:
        """Get commit information."""
        format_str = "%H|%an|%ae|%ad|%s"
        output = self._run_git_command([
            "show", "--no-patch", f"--format={format_str}", commit_hash
        ])
        
        if output:
            parts = output.split('|', 4)
            if len(parts) >= 5:
                return {
                    'hash': parts[0],
                    'author_name': parts[1],
                    'author_email': parts[2],
                    'date': parts[3],
                    'message': parts[4]
                }
        return {}
    
    def get_file_history(self, file_path: str) -> List[Dict]:
        """Get commit history for a specific file."""
        commits = []
        
        # Check if file exists in git history
        file_exists = self._run_git_command(["ls-files", file_path])
        if not file_exists:
            logger.info(f"File {file_path} not yet committed to git")
            return []
        
        output = self._run_git_command([
            "log", "--follow", "--oneline", "--", file_path
        ])
        
        if output:
            for line in output.split('\n'):
                if line.strip():
                    commit_hash = line.split()[0]
                    commit_info = self._get_commit_info(commit_hash)
                    if commit_info:
                        commits.append(commit_info)
        
        return commits
    
    def analyze_endpoint_contributions(self) -> Dict[str, Dict]:
        """Analyze all endpoint contributions across the repository."""
        # Find all router files
        router_files = []
        
        # Check common locations for API endpoints
        patterns = [
            "app/main.py",
            "app/routers/*.py",
            "main.py",
            "routers/*.py",
        ]
        
        for pattern in patterns:
            if "*" in pattern:
                # Handle glob patterns
                import glob
                files = glob.glob(str(self.repo_path / pattern))
                router_files.extend([os.path.relpath(f, self.repo_path) for f in files])
            else:
                file_path = self.repo_path / pattern
                if file_path.exists():
                    router_files.append(pattern)
        
        # Remove duplicates
        router_files = list(set(router_files))
        
        contributions = {}
        
        for file_path in router_files:
            logger.info(f"Analyzing file: {file_path}")
            
            # Get current endpoints in the file
            current_endpoints = self._get_file_endpoints(file_path)
            
            if not current_endpoints:
                continue
            
            # Get file history
            file_history = self.get_file_history(file_path)
            
            # For each endpoint, try to find when it was introduced
            for method, path in current_endpoints:
                endpoint_key = f"{method} {path}"
                
                # Use git blame to find who last modified each line containing the endpoint
                blame_info = self._get_endpoint_blame(file_path, method, path)
                
                if endpoint_key not in contributions:
                    contributions[endpoint_key] = {
                        'method': method,
                        'path': path,
                        'file_path': file_path,
                        'contributors': [],
                        'first_commit': None,
                        'last_modified': None,
                        'blame_info': blame_info
                    }
                
                # Add file history to determine original author
                if file_history:
                    # The last commit in history is usually the first one (oldest)
                    first_commit = file_history[-1] if file_history else None
                    last_commit = file_history[0] if file_history else None
                    
                    contributions[endpoint_key]['first_commit'] = first_commit
                    contributions[endpoint_key]['last_modified'] = last_commit
                    
                    # Extract unique contributors
                    contributors = {}
                    for commit in file_history:
                        author = commit.get('author_name', 'Unknown')
                        email = commit.get('author_email', '')
                        if author not in contributors:
                            contributors[author] = {
                                'name': author,
                                'email': email,
                                'commits': 0,
                                'first_commit_date': commit.get('date'),
                                'last_commit_date': commit.get('date')
                            }
                        contributors[author]['commits'] += 1
                        # Update dates (assuming commits are in chronological order, newest first)
                        contributors[author]['last_commit_date'] = commit.get('date')
                    
                    contributions[endpoint_key]['contributors'] = list(contributors.values())
        
        return contributions
    
    def _get_endpoint_blame(self, file_path: str, method: str, path: str) -> Dict:
        """Get git blame information for a specific endpoint."""
        try:
            # Check if file exists in git history
            file_exists = self._run_git_command(["ls-files", file_path])
            if not file_exists:
                logger.info(f"File {file_path} not yet committed to git")
                return {'note': 'File not yet committed'}
            
            # Run git blame on the file
            blame_output = self._run_git_command(["blame", "--line-porcelain", file_path])
            
            if not blame_output:
                return {}
            
            # Look for lines containing the endpoint definition
            endpoint_pattern = rf'@(?:router|app)\.{method.lower()}\s*\(\s*["\']({re.escape(path)})["\']'
            
            lines = blame_output.split('\n')
            for i, line in enumerate(lines):
                if re.search(endpoint_pattern, line, re.IGNORECASE):
                    # Find the corresponding blame info (usually a few lines before)
                    for j in range(max(0, i-10), i+1):
                        if lines[j].startswith('author '):
                            author = lines[j][7:]  # Remove 'author ' prefix
                            # Look for more commit info
                            commit_info = {}
                            for k in range(max(0, j-5), j+10):
                                if k < len(lines):
                                    if lines[k].startswith('author '):
                                        commit_info['author'] = lines[k][7:]
                                    elif lines[k].startswith('author-mail '):
                                        commit_info['author_email'] = lines[k][12:].strip('<>')
                                    elif lines[k].startswith('author-time '):
                                        try:
                                            timestamp = int(lines[k][12:])
                                            commit_info['author_time'] = datetime.fromtimestamp(timestamp).isoformat()
                                        except:
                                            pass
                                    elif lines[k].startswith('summary '):
                                        commit_info['summary'] = lines[k][8:]
                            return commit_info
            
        except Exception as e:
            logger.warning(f"Could not get blame info for {method} {path} in {file_path}: {e}")
        
        return {}
    
    def get_current_user_contributions(self) -> Dict:
        """Get contributions for the current git user."""
        # Get current git user info
        user_name = self._run_git_command(["config", "user.name"])
        user_email = self._run_git_command(["config", "user.email"])
        
        all_contributions = self.analyze_endpoint_contributions()
        
        user_contributions = {}
        
        for endpoint_key, endpoint_data in all_contributions.items():
            # Check if current user contributed to this endpoint
            for contributor in endpoint_data.get('contributors', []):
                if (contributor.get('name') == user_name or 
                    contributor.get('email') == user_email):
                    user_contributions[endpoint_key] = {
                        **endpoint_data,
                        'my_contribution': contributor
                    }
                    break
        
        return {
            'user_info': {
                'name': user_name,
                'email': user_email
            },
            'contributions': user_contributions,
            'total_endpoints': len(user_contributions)
        }
    
    def get_endpoint_summary(self) -> Dict:
        """Get a summary of all endpoints and their contributors."""
        contributions = self.analyze_endpoint_contributions()
        
        summary = {
            'total_endpoints': len(contributions),
            'endpoints_by_method': {},
            'contributors': {},
            'endpoints': []
        }
        
        for endpoint_key, endpoint_data in contributions.items():
            method = endpoint_data['method']
            
            # Count by method
            if method not in summary['endpoints_by_method']:
                summary['endpoints_by_method'][method] = 0
            summary['endpoints_by_method'][method] += 1
            
            # Track contributors
            for contributor in endpoint_data.get('contributors', []):
                name = contributor.get('name', 'Unknown')
                if name not in summary['contributors']:
                    summary['contributors'][name] = {
                        'name': name,
                        'email': contributor.get('email', ''),
                        'endpoints': []
                    }
                summary['contributors'][name]['endpoints'].append({
                    'method': method,
                    'path': endpoint_data['path'],
                    'commits': contributor.get('commits', 0)
                })
            
            # Add to endpoints list
            last_modified_data = endpoint_data.get('last_modified')
            first_commit_data = endpoint_data.get('first_commit')
            
            summary['endpoints'].append({
                'method': method,
                'path': endpoint_data['path'],
                'file_path': endpoint_data['file_path'],
                'contributors': [c.get('name', 'Unknown') for c in endpoint_data.get('contributors', [])],
                'last_modified': last_modified_data.get('date') if last_modified_data else None,
                'first_commit': first_commit_data.get('date') if first_commit_data else None
            })
        
        return summary