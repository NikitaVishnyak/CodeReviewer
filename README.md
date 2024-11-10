# CodeReviewer

This project is a backend solution for reviewing coding assignments from GitHub repositories using the Google Gemini AI. The tool analyzes the code and provides feedback, including comments, ratings, and conclusions, based on the developer's level (Junior, Middle, Senior).

## Features

- Fetches code from a GitHub repository.
- Uses Google Gemini AI to analyze the code.
- Returns a detailed review with comments, ratings, and conclusions.

## Prerequisites

- **Python 3.10+** (optional if using Docker)
- **Docker** (recommended for running the project)
- **GitHub API Token** (for accessing GitHub repositories)
- **Google API Key** (for interacting with Google Gemini AI)

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/NikitaVishnyak/CodeReviewer.git
cd CodeReviewer
```
### 2. Install dependencies

- **Without Docker**:
    You can install the dependencies using **Poetry**:

    ```bash
    poetry install
    ```

### 3. Set up environment variables
Create a `.env` file in the project root and add your environment variables:
```ini
GOOGLE_API_KEY="your-google-api-key"
GITHUB_API_KEY="your-github-api-key"
REDIS_URL="redis://redis:6379"
RATE_LIMITING_ENABLED=set to `True` to enable rate limiting for requests.
```

### 4. Running the application

- **With Docker**:
```bash
docker-compose up --build
```

- **Without Docker**:
```bash
poetry run uvicorn app.main:app --reload
```
