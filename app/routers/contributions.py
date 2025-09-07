"""
API Contributions Router

This module provides endpoints to track and display API endpoint contributions
by analyzing git history and associating endpoints with their contributors.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path

from app.utils.git_analyzer import GitEndpointAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize the git analyzer
analyzer = GitEndpointAnalyzer()


class ContributorInfo(BaseModel):
    """Information about a contributor."""
    name: str
    email: str
    commits: int
    first_commit_date: Optional[str] = None
    last_commit_date: Optional[str] = None


class EndpointContribution(BaseModel):
    """Information about an endpoint contribution."""
    method: str
    path: str
    file_path: str
    contributors: List[ContributorInfo]
    first_commit: Optional[Dict[str, Any]] = None
    last_modified: Optional[Dict[str, Any]] = None
    blame_info: Optional[Dict[str, Any]] = None


class UserContributions(BaseModel):
    """User's endpoint contributions."""
    user_info: Dict[str, str]
    contributions: Dict[str, Any]
    total_endpoints: int


class EndpointSummary(BaseModel):
    """Summary of all endpoints and contributors."""
    total_endpoints: int
    endpoints_by_method: Dict[str, int]
    contributors: Dict[str, Any]
    endpoints: List[Dict[str, Any]]


@router.get("/contributions/", response_model=Dict[str, EndpointContribution])
async def get_all_contributions():
    """
    Get contributions for all API endpoints.
    
    Returns detailed information about who contributed to each endpoint,
    including commit history, authors, and modification dates.
    """
    try:
        contributions = analyzer.analyze_endpoint_contributions()
        
        # Convert to Pydantic models for proper serialization
        result = {}
        for endpoint_key, data in contributions.items():
            # Convert contributors to proper format
            contributors = []
            for contrib in data.get('contributors', []):
                contributors.append(ContributorInfo(
                    name=contrib.get('name', 'Unknown'),
                    email=contrib.get('email', ''),
                    commits=contrib.get('commits', 0),
                    first_commit_date=contrib.get('first_commit_date'),
                    last_commit_date=contrib.get('last_commit_date')
                ))
            
            result[endpoint_key] = EndpointContribution(
                method=data['method'],
                path=data['path'],
                file_path=data['file_path'],
                contributors=contributors,
                first_commit=data.get('first_commit'),
                last_modified=data.get('last_modified'),
                blame_info=data.get('blame_info')
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing contributions: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to analyze endpoint contributions: {str(e)}"
        )


@router.get("/contributions/my/", response_model=UserContributions)
async def get_my_contributions():
    """
    Get the current user's endpoint contributions.
    
    Returns only the endpoints that the current git user has contributed to,
    based on git authorship information.
    """
    try:
        user_contributions = analyzer.get_current_user_contributions()
        return UserContributions(**user_contributions)
        
    except Exception as e:
        logger.error(f"Error getting user contributions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user contributions: {str(e)}"
        )


@router.get("/contributions/summary/", response_model=EndpointSummary)
async def get_contributions_summary():
    """
    Get a summary of all endpoints and their contributors.
    
    Returns aggregated statistics about endpoints, methods used,
    and contributor information.
    """
    try:
        summary = analyzer.get_endpoint_summary()
        return EndpointSummary(**summary)
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate contributions summary: {str(e)}"
        )


@router.get("/contributions/by-author/{author_name}")
async def get_contributions_by_author(author_name: str):
    """
    Get endpoint contributions by a specific author.
    
    Args:
        author_name: The name of the author to search for
    
    Returns:
        Dictionary of endpoints contributed to by the specified author
    """
    try:
        all_contributions = analyzer.analyze_endpoint_contributions()
        
        author_contributions = {}
        for endpoint_key, endpoint_data in all_contributions.items():
            for contributor in endpoint_data.get('contributors', []):
                if contributor.get('name', '').lower() == author_name.lower():
                    author_contributions[endpoint_key] = {
                        'method': endpoint_data['method'],
                        'path': endpoint_data['path'],
                        'file_path': endpoint_data['file_path'],
                        'contribution': contributor,
                        'last_modified': endpoint_data.get('last_modified'),
                        'first_commit': endpoint_data.get('first_commit')
                    }
                    break
        
        if not author_contributions:
            raise HTTPException(
                status_code=404,
                detail=f"No contributions found for author: {author_name}"
            )
        
        return {
            'author': author_name,
            'total_endpoints': len(author_contributions),
            'contributions': author_contributions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting contributions for author {author_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get contributions for author: {str(e)}"
        )


@router.get("/contributions/endpoints/")
async def list_all_endpoints(
    method: Optional[str] = Query(None, description="Filter by HTTP method (GET, POST, etc.)"),
    file_path: Optional[str] = Query(None, description="Filter by file path")
):
    """
    List all available API endpoints with optional filtering.
    
    Args:
        method: Optional HTTP method filter (GET, POST, PUT, DELETE, etc.)
        file_path: Optional file path filter
    
    Returns:
        List of endpoints with basic information
    """
    try:
        contributions = analyzer.analyze_endpoint_contributions()
        
        endpoints = []
        for endpoint_key, data in contributions.items():
            # Apply filters
            if method and data['method'].upper() != method.upper():
                continue
            if file_path and file_path not in data['file_path']:
                continue
            
            endpoint_info = {
                'endpoint': endpoint_key,
                'method': data['method'],
                'path': data['path'],
                'file_path': data['file_path'],
                'contributors_count': len(data.get('contributors', [])),
                'contributor_names': [c.get('name', 'Unknown') for c in data.get('contributors', [])],
                'last_modified': data.get('last_modified', {}).get('date') if data.get('last_modified') else None
            }
            endpoints.append(endpoint_info)
        
        # Sort by method and path for consistent ordering
        endpoints.sort(key=lambda x: (x['method'], x['path']))
        
        return {
            'total_endpoints': len(endpoints),
            'filters_applied': {
                'method': method,
                'file_path': file_path
            },
            'endpoints': endpoints
        }
        
    except Exception as e:
        logger.error(f"Error listing endpoints: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list endpoints: {str(e)}"
        )


@router.get("/contributions/stats/")
async def get_contribution_stats():
    """
    Get statistical information about endpoint contributions.
    
    Returns:
        Various statistics about the API endpoints and their contributors
    """
    try:
        summary = analyzer.get_endpoint_summary()
        
        # Calculate additional statistics
        stats = {
            'overview': {
                'total_endpoints': summary['total_endpoints'],
                'total_contributors': len(summary['contributors']),
                'methods_used': list(summary['endpoints_by_method'].keys()),
                'endpoints_by_method': summary['endpoints_by_method']
            },
            'contributor_rankings': [],
            'file_distribution': {},
            'recent_activity': []
        }
        
        # Rank contributors by number of endpoints
        for name, contributor_data in summary['contributors'].items():
            stats['contributor_rankings'].append({
                'name': name,
                'email': contributor_data.get('email', ''),
                'endpoint_count': len(contributor_data.get('endpoints', [])),
                'endpoints': contributor_data.get('endpoints', [])
            })
        
        # Sort by endpoint count (descending)
        stats['contributor_rankings'].sort(key=lambda x: x['endpoint_count'], reverse=True)
        
        # Calculate file distribution
        for endpoint in summary['endpoints']:
            file_path = endpoint.get('file_path', 'unknown')
            if file_path not in stats['file_distribution']:
                stats['file_distribution'][file_path] = 0
            stats['file_distribution'][file_path] += 1
        
        # Get recent activity (endpoints with recent modifications)
        recent_endpoints = []
        for endpoint in summary['endpoints']:
            if endpoint.get('last_modified'):
                recent_endpoints.append({
                    'method': endpoint['method'],
                    'path': endpoint['path'],
                    'last_modified': endpoint['last_modified'],
                    'contributors': endpoint['contributors']
                })
        
        # Sort by last modified date (most recent first)
        recent_endpoints.sort(
            key=lambda x: x.get('last_modified', ''), 
            reverse=True
        )
        stats['recent_activity'] = recent_endpoints[:10]  # Top 10 recent
        
        return stats
        
    except Exception as e:
        logger.error(f"Error generating contribution stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate contribution statistics: {str(e)}"
        )