"""Scout agent: retrieval-only movie candidate finder."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TMDB_SERVER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../tmdb_server.py"))


def _mcp(server_path: str = TMDB_SERVER_PATH) -> McpToolset:
    """Create a fresh MCP connection for this agent."""
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command=sys.executable, args=[server_path])
        )
    )


SCOUT_PROMPT = """\
You are Scout, the retrieval specialist for a Movie Night Planner.

Your ONLY job is to find movie candidates from TMDB and report clean details.
Do not recommend, rank, approve, reject, or judge the movies.

For every request:
1. Understand the movie-night details: preferred genre or vibe, time budget, age of youngest viewer, and any named movie/title.
2. Use discover_movies when the user asks to find something by genre/vibe.
3. Use search_movies when a title is named or the request says "something like <movie>".
4. For every promising candidate, call get_movie_details.
5. Return only a structured candidate list with title, year, id, runtime, US certification, genres, and audience score.

Keep the list to 5-8 candidates. Retrieval only — no final shortlist.
"""

root_agent = LlmAgent(
    name="scout",
    model="gemini-2.5-flash",
    description=(
        "Finds movie candidates on TMDB and fetches runtime, US certification, "
        "genres, and audience score. Retrieval only. Use FIRST."
    ),
    instruction=SCOUT_PROMPT,
    tools=[_mcp()],
)
