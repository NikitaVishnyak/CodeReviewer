import os
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, Field
from github import Github, GithubException, Auth
import logging
import json
from dotenv import load_dotenv
from typing import Dict, Any, Tuple

load_dotenv()

genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
logging.basicConfig(level=logging.INFO)

app = FastAPI()


class ReviewRequest(BaseModel):
    assignment_description: str
    github_repo_url: HttpUrl
    candidate_level: str = Field(..., pattern="^(Junior|Middle|Senior)$")


@app.post("/review")
async def review_code(request: ReviewRequest) -> Dict[str, Any]:
    """
    Review code from a GitHub repository using Gemini AI.

    :param request: The review request containing assignment description, GitHub repository URL, and candidate level.
    :return: A dictionary with files found, downsides/comments, rating, and conclusion.
    """
    repo_content = await fetch_github_repo(request.github_repo_url)

    if not repo_content:
        raise HTTPException(status_code=500, detail="No files found in the repository or unable to fetch content.")

    review = await analyze_code_with_gemini(repo_content, request.assignment_description, request.candidate_level)

    if not review:
        raise HTTPException(status_code=500, detail="Could not analyze code with Gemini.")

    downsides_or_comments, rating, conclusion = parse_review(review)

    return {
        "files_found": list(repo_content.keys()),
        "downsides or comments": downsides_or_comments,
        "rating": rating,
        "conclusion": conclusion
    }


async def fetch_github_repo(repo_url: str) -> Dict[str, str]:
    """
    Fetch the contents of a GitHub repository.

    :param repo_url: The URL of the GitHub repository.
    :return: A dictionary with file names as keys and file content as values.
    """
    github_api_key = os.getenv('GITHUB_API_KEY')
    g = Github(auth=Auth.Token(github_api_key))
    repo_name = repo_url.path.strip("/")

    try:
        repo = g.get_repo(repo_name)
    except GithubException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="Repository not found.")
        else:
            raise HTTPException(status_code=500, detail="An error occurred while fetching the repository.")

    contents = repo.get_contents("")
    files_content = {}

    while contents:
        file_content = contents.pop(0)

        if file_content.type == "dir":
            contents.extend(repo.get_contents(file_content.path))
        else:
            try:
                decoded_content = file_content.decoded_content.decode("utf-8")
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
        response = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Error with Gemini API: {e}")
        raise HTTPException(status_code=500, detail=f"Gemini API error: {e}")


def create_prompt(files: Dict[str, str], description: str, level: str) -> str:
    """
    Create a prompt for the Gemini AI model based on the files, description, and candidate level.

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
        Please provide feedback in the following format: Downsides/Comments, Rating (?/10), Conclusion.
        Please use the following JSON schema:\n
        {{\n"Downsides/Comments": "<Your comments here>",\n"Rating": "<Your rating here>",\n"Conclusion": "<Your conclusion here>"\n}}""")
    return prompt


def parse_review(review: str) -> Tuple[str, str, str]:
    """
    Parse the review returned by Gemini AI into structured components.

    :param review: The raw comments string returned by the Gemini AI.
    :return: A tuple containing downsides/comments, rating, and conclusion.
    """
    try:
        json_part = review.strip().replace("```json", "").replace("```", "").strip()
        parsed_review = json.loads(json_part)

        rating = parsed_review.get("Rating", "N/A")
        conclusion = parsed_review.get("Conclusion", "")
        downsides_or_comments = format_downsides_and_comments(parsed_review.get("Downsides/Comments", ""))

    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON from comments: {e}")
        return review, "N/A", "The code review is complete based on the provided files."

    return downsides_or_comments, rating, conclusion


def format_downsides_and_comments(text: str) -> str:
    """
    Format the downsides/comments text by removing extra formatting.

    :param text: The raw downsides/comments text.
    :return: A cleaned-up version of the text with unwanted formatting removed.
    """
    return text.replace('\n\n', ' ').replace('**', '')
