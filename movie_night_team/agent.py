"""Movie Night Planner team: Host orchestrates Scout and Referee."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

try:
    from google.adk.models.lite_llm import LiteLlm
except Exception:  # pragma: no cover - keeps Gemini fallback easy in older ADK installs
    LiteLlm = None

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TMDB_SERVER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../tmdb_server.py"))
USE_CLAUDE_HOST = os.getenv("USE_CLAUDE_HOST", "true").lower() in {"1", "true", "yes"}
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "anthropic/claude-sonnet-4-6")


def _mcp(server_path: str = TMDB_SERVER_PATH) -> McpToolset:
    """Create one fresh MCP subprocess connection per agent that uses tools."""
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
1. Extract genre/vibe, time budget, youngest viewer age, and any named title.
2. Use discover_movies for open-ended genre/vibe discovery.
3. Use search_movies when a title is named or user says "something like <movie>".
4. For each candidate, call get_movie_details.
5. Return 5-8 candidates with title, year, id, runtime, US certification, genres, and audience score.
"""

REFEREE_PROMPT = """\
You are Referee, the constraint checker.
Your ONLY job is to check candidates against hard constraints. Do not recommend or rank.

Check every candidate for:
1. Runtime within the time budget.
2. Certification appropriate for the youngest viewer:
   - under 7: G only
   - 7-12: G or PG
   - 13-16: G, PG, or PG-13
   - 17+: any rating except NC-17 unless explicitly allowed
   - unknown certification: DOESN'T FIT unless all other choices fail; mark unknown clearly
3. Genre/vibe matches the preference.

Return exactly:
MOVIE: Title (Year)
VERDICT: FITS | DOESN'T FIT
REASON: one line
"""

HOST_PROMPT = """\
You are Host, the orchestrator of a multi-agent Movie Night Planner.

For every movie-night request, follow this pipeline IN ORDER:
1. Delegate to Scout. Pass the complete user request. Scout must retrieve candidates and details from TMDB.
2. Delegate to Referee. Pass the user constraints and Scout's complete candidate list.
3. Recommend a ranked shortlist using only movies marked FITS.

Final answer format:
## Recommended Shortlist
1. Title (Year) — runtime min, rating — short reason.
2. Title (Year) — runtime min, rating — short reason.
3. Title (Year) — runtime min, rating — short reason.

## Why These Fit
One short paragraph connecting the picks to the group's age, time, and mood.

If nothing fits, do not invent recommendations. Say what constraint to relax, e.g. allow 15 more minutes, allow PG-13, or broaden the genre.
Never answer from your own movie knowledge without delegating to Scout first.
"""

scout = LlmAgent(
    name="scout",
    model="gemini-2.5-flash",
    description=(
        "Finds candidate movies on TMDB and fetches details. Retrieval only. Use FIRST."
    ),
    instruction=SCOUT_PROMPT,
    tools=[_mcp()],
)

referee = LlmAgent(
    name="referee",
    model="gemini-2.5-flash",
    description=(
        "Checks Scout's candidates against runtime, age rating, and genre constraints. "
        "Returns FITS or DOESN'T FIT. Use AFTER Scout."
    ),
    instruction=REFEREE_PROMPT,
)

host_model = (
    LiteLlm(model=CLAUDE_MODEL)
    if USE_CLAUDE_HOST and LiteLlm is not None
    else "gemini-2.5-flash"
)

root_agent = LlmAgent(
    name="host",
    model=host_model,
    description="Orchestrates Scout and Referee to recommend a ranked movie-night shortlist.",
    instruction=HOST_PROMPT,
    sub_agents=[scout, referee],
)
