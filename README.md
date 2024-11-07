# CodeReviewer

This project is a backend solution for reviewing coding assignments from GitHub repositories using the Google Gemini AI. The tool analyzes the code and provides feedback, including comments, ratings, and conclusions, based on the developer's level (Junior, Middle, Senior).

## Features

- Fetches code from a GitHub repository.
- Uses Google Gemini AI to analyze the code.
- Returns a detailed review with comments, ratings, and conclusions.

## Prerequisites

- **Python 3.10+**
- **GitHub API Token** (for accessing GitHub repositories).
- **Google API Key** (for interacting with Google Gemini AI).

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/NikitaVishnyak/CodeReviewer.git
    cd CodeReviewer
    ```

2. Install dependencies with **Poetry**.

    ```bash
    poetry install
    ```

3. Create a `.env` file in the project root and add your environment variables:

    ```ini
    GOOGLE_API_KEY=your-google-api-key
    GITHUB_API_KEY=your-github-api-key
    ```

## Running the Application

To start the FastAPI server, use the following command:

```bash
poetry run uvicorn app.main:app --reload
