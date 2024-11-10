import os
import json
import logging
import typing_extensions
from typing import Dict, Any, Tuple, List

import google.generativeai as genai
from dotenv import load_dotenv
from slowapi import Limiter
from fastapi import FastAPI, HTTPException, Request
from github import Github, GithubException, Auth
from pydantic import BaseModel, HttpUrl, Field
from slowapi.util import get_remote_address

from cache.caching import generate_repo_cache_key, get_cached_github_repo, set_cached_github_repo


load_dotenv()

app = FastAPI(title='CodeReviewer')
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
logging.basicConfig(level=logging.INFO)

limiter = Limiter(
    key_func=get_remote_address,
    strategy='fixed-window',
    storage_uri=os.getenv('REDIS_URL'),
    enabled=bool(os.getenv('RATE_LIMITING_ENABLED')),
)


class ReviewRequest(BaseModel):
    assignment_description: str
    github_repo_url: HttpUrl
    candidate_level: str = Field(..., pattern='^(Junior|Middle|Senior)$')


class Review(typing_extensions.TypedDict):
    downsides_and_comments: list[str]
    conclusion: str
    rating: str


@app.post('/review')
@limiter.limit('5/5minute', per_method=True)
async def review_code(request: Request, review_request: ReviewRequest) -> Dict[str, Any]:
    """
    Review code from a GitHub repository using Gemini AI.

    :param request: The incoming HTTP request object, used by rate limiter.
    :param review_request: The review request containing assignment description, GitHub repository URL, and candidate level.
    :return: A dictionary with files found, downsides/comments, rating, and conclusion.
    """
    repo_key = generate_repo_cache_key(review_request.github_repo_url, review_request.candidate_level)
    cached_repo = await get_cached_github_repo(repo_key)
    if cached_repo:
        repo_content = cached_repo
    else:
        logging.info("Fetching github repository...")
        repo_content = await fetch_github_repo(review_request.github_repo_url)
        if not repo_content:
            raise HTTPException(status_code=500, detail="No files found in the repository or unable to fetch content.")

        await set_cached_github_repo(repo_key, repo_content)

    logging.info("Analyzing code with Gemini...")
    review = await analyze_code_with_gemini(repo_content, review_request.assignment_description,
                                            review_request.candidate_level)
    if not review:
        raise HTTPException(status_code=500, detail="Could not analyze code with Gemini.")

    downsides_or_comments, rating, conclusion = parse_review(review)

    return {
        'files_found': list(repo_content.keys()),
        'downsides or comments': downsides_or_comments,
        'rating': rating,
        'conclusion': conclusion
    }


async def fetch_github_repo(repo_url: str) -> Dict[str, str]:
    """
    Fetch the contents of a GitHub repository.

    :param repo_url: The URL of the GitHub repository.
    :return: A dictionary with file names as keys and file content as values.
    """
    github_api_key = os.getenv('GITHUB_API_KEY')
    g = Github(auth=Auth.Token(github_api_key))
    repo_name = repo_url.path.strip('/')

    try:
        repo = g.get_repo(repo_name)
    except GithubException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="Repository not found.")
        else:
            raise HTTPException(status_code=500, detail="An error occurred while fetching the repository.")

    contents = repo.get_contents('')
    files_content = {}

    while contents:
        file_content = contents.pop(0)

        if file_content.type == 'dir':
            contents.extend(repo.get_contents(file_content.path))
        else:
            try:
                decoded_content = file_content.decoded_content.decode('utf-8')
                logging.info(f"Processing file: {file_content.path}")
                files_content[file_content.path] = decoded_content
            except UnicodeDecodeError:
                logging.warning(f"Skipping non-text file: {file_content.path}")

    return files_content


async def analyze_code_with_gemini(files: Dict[str, str], description: str, level: str) -> str:
    """
    Analyze code using Gemini AI.

    :param files: A dictionary containing the code files to analyze.
    :param description: The assignment description for context.
    :param level: The candidate level for which the code is being reviewed.
    :return: The analysis response text from Gemini AI.
    """
    prompt = create_prompt(files, description, level)
    try:
        response = genai.GenerativeModel('gemini-1.5-flash').generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type='application/json', response_schema=Review
            )
        )
        return response.text
    except Exception as e:
        logging.error(f"Error with Gemini API: {e}")
        raise HTTPException(status_code=500, detail=f"Gemini API error: {e}")


def create_prompt(files: Dict[str, str], description: str, level: str) -> str:
    """
    Create a prompt for the Gemini AI model.

    :param files: A dictionary containing the code files to analyze.
    :param description: The assignment description for context.
    :param level: The candidate level for which the code is being reviewed.
    :return: A formatted prompt string for Gemini AI.
    """
    prompt = f"You are reviewing code for a '{level}' level developer.\n\nCode files:\n"
    for filename, content in files.items():
        prompt += f"File: {filename}\n{content}\n\n"
    prompt += (
        f"""Assignment: {description}\n
        Based on the level of the developer and his Assignment, review the code in the following format:
        1. Downsides and Comments: List specific issues or areas for improvement.
        2. Conclusion: Summarize your overall assessment.
        3. Rating: Give a rating out of 10.
        You have to give me only these three paragraphs (Downsides and Comments, Conclusion, Rating).
        Follow this structure:
        "downsides_and_comments": [
            "Comment 1",
            "Comment 2",
            ...
        ],
        "conclusion": "Overall conclusion",
        "rating": "Rating/10"
        """
    )
    return prompt


def parse_review(review: str) -> Tuple[List[str], str, str]:
    """
    Parse the review response from Gemini AI.

    :param review: response from Gemini AI.
    :return: A tuple containing: list of downsides and comments, rating, conclusion.
    """
    try:
        parsed_data = json.loads(review)
        downsides_and_comments = parsed_data.get('downsides_and_comments', [])
        rating = parsed_data.get('rating', 'N/A')
        conclusion = parsed_data.get('conclusion', '')
        return downsides_and_comments, rating, conclusion
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON: {e}")
        return [], 'N/A', 'Error parsing review'
