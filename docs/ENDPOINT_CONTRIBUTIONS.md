# Endpoint Contributions Tracking

This feature allows you to track which developers contributed to creating and maintaining each API endpoint in the SAT-Annotator project.

## Overview

The system analyzes git history to associate API endpoints with their contributors, providing detailed information about:

- Who created each endpoint
- When endpoints were first introduced
- File locations and commit history
- Contribution statistics and rankings

## API Endpoints

### 1. Get All Contributions
```http
GET /api/contributions/
```
Returns detailed information about all endpoint contributions, including authors, commit history, and modification dates.

### 2. Get My Contributions
```http
GET /api/contributions/my/
```
Returns endpoints contributed to by the current git user (based on git config).

### 3. Get Contributions Summary
```http
GET /api/contributions/summary/
```
Returns aggregated statistics including:
- Total endpoints count
- Endpoints grouped by HTTP method
- List of all contributors
- Sample endpoint information

### 4. Get Contributions by Author
```http
GET /api/contributions/by-author/{author_name}
```
Returns all endpoints contributed to by a specific author.

**Example:**
```bash
curl "http://localhost:8000/api/contributions/by-author/Ahmed%20Fadel"
```

### 5. List All Endpoints
```http
GET /api/contributions/endpoints/
```
Returns a list of all available endpoints with optional filtering.

**Query Parameters:**
- `method` (optional): Filter by HTTP method (GET, POST, PUT, DELETE)
- `file_path` (optional): Filter by file path

**Examples:**
```bash
# Get all POST endpoints
curl "http://localhost:8000/api/contributions/endpoints/?method=POST"

# Get endpoints from session_images.py
curl "http://localhost:8000/api/contributions/endpoints/?file_path=session_images"
```

### 6. Get Contribution Statistics
```http
GET /api/contributions/stats/
```
Returns detailed statistics including:
- Overview with counts and breakdowns
- Contributor rankings by endpoint count
- File distribution showing endpoints per file
- Recent activity list

## Features

### Git History Analysis
- Analyzes git blame and commit history
- Associates endpoints with their authors
- Tracks modification dates and commit messages
- Handles multiple contributors per endpoint

### Endpoint Detection
- Automatically detects FastAPI endpoints using decorators
- Supports both `@router` and `@app` decorators
- Finds endpoints in multiple files and directories
- Extracts HTTP methods and URL paths

### Contributor Tracking
- Maps git authors to endpoint contributions
- Counts commits per contributor per endpoint
- Tracks first and last contribution dates
- Provides email and name information

## Usage Examples

### Find Your Contributions
To see what endpoints you've contributed to:

```bash
curl http://localhost:8000/api/contributions/my/
```

### Get Project Overview
To see overall project statistics:

```bash
curl http://localhost:8000/api/contributions/summary/
```

### Find Specific Author's Work
To see what a specific developer contributed:

```bash
curl "http://localhost:8000/api/contributions/by-author/Ahmed%20Fadel"
```

### Filter Endpoints
To see only POST endpoints:

```bash
curl "http://localhost:8000/api/contributions/endpoints/?method=POST"
```

## Sample Response

Here's an example response from `/api/contributions/by-author/Ahmed%20Fadel`:

```json
{
  "author": "Ahmed Fadel",
  "total_endpoints": 20,
  "contributions": {
    "POST /upload-image/": {
      "method": "POST",
      "path": "/upload-image/",
      "file_path": "app/routers/session_images.py",
      "contribution": {
        "name": "Ahmed Fadel",
        "email": "125441479+justFadel19@users.noreply.github.com",
        "commits": 1,
        "first_commit_date": "Fri Jul 18 16:58:09 2025 +0300",
        "last_commit_date": "Fri Jul 18 16:58:09 2025 +0300"
      },
      "last_modified": {
        "hash": "74f921c...",
        "author_name": "Ahmed Fadel",
        "date": "Fri Jul 18 16:58:09 2025 +0300",
        "message": "Merge pull request #45 from justFadel19/feature/csv-export-format"
      }
    }
  }
}
```

## Testing

You can test the system using the provided test script:

```bash
python test_contributions.py
```

Or run the standalone contributions server:

```bash
python contributions_server.py
```

Then access the API at `http://localhost:8001`

## Implementation Details

### Files Added/Modified

1. **`app/utils/git_analyzer.py`** - Core git analysis functionality
2. **`app/routers/contributions.py`** - FastAPI router with endpoints
3. **`app/main.py`** - Updated to include contributions router
4. **`test_contributions.py`** - Test script for functionality verification
5. **`contributions_server.py`** - Standalone server for testing

### Dependencies

The system uses standard Python libraries and existing project dependencies:
- `subprocess` for git commands
- `re` for regex pattern matching
- `pathlib` for file operations
- `fastapi` and `pydantic` for API endpoints

No additional dependencies are required.

## Benefits

This feature helps teams:

1. **Track Contributions**: Easily see who worked on which endpoints
2. **Code Ownership**: Identify experts for specific API areas
3. **Documentation**: Understand the evolution of the API
4. **Onboarding**: Help new team members understand code structure
5. **Recognition**: Acknowledge individual contributions to the project