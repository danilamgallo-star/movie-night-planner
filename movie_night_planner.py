"""CLI Runner for the Movie Night Planner capstone.

Usage:
    python movie_night_planner.py "4 people, youngest is 8, 2 hours, we like animation"
    python movie_night_planner.py --verbose "Family movie night, youngest 8, 2 hours, adventure and animation"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from typing import Sequence

from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters

try:
    from google.adk.models.lite_llm import LiteLlm
except Exception:  # pragma: no cover
    LiteLlm = None

TMDB_SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmdb_server.py")
USE_CLAUDE_HOST = os.getenv("USE_CLAUDE_HOST", "true").lower() in {"1", "true", "yes"}
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "anthropic/claude-sonnet-4-6")


def _mcp() -> McpToolset:
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command=sys.executable, args=[TMDB_SERVER_PATH])
        )
    )


def _host_model():
    if USE_CLAUDE_HOST and LiteLlm is not None:
        return LiteLlm(model=CLAUDE_MODEL)
    return "gemini-2.5-flash"


SCOUT_PROMPT = """\
You are Scout, the retrieval specialist for a Movie Night Planner.
Your ONLY job is to find movie candidates from TMDB and report clean details.
Use discover_movies for open-ended genre/vibe discovery and search_movies when a title is named.
For each candidate, call get_movie_details. Return 5-8 candidates with title, year, id, runtime, US certification, genres, and audience score. Do not recommend or rank.
"""

REFEREE_PROMPT = """\
You are Referee, the constraint checker. Check candidates against runtime, youngest-viewer rating, and genre/vibe.
Rating rule: under 7 = G; 7-12 = G/PG; 13-16 = G/PG/PG-13; 17+ = any except NC-17 unless explicitly allowed.
Return only:
MOVIE: Title (Year)
VERDICT: FITS | DOESN'T FIT
REASON: one line
"""

HOST_PROMPT = """\
You are Host, the final recommender for a Movie Night Planner.
Use the conversation history from Scout and Referee.
Recommend a ranked shortlist using only movies marked FITS by Referee.

Final answer format:
## Recommended Shortlist
1. Title (Year) — runtime min, rating — short reason.
2. Title (Year) — runtime min, rating — short reason.
3. Title (Year) — runtime min, rating — short reason.

## Why These Fit
One short paragraph.

If nothing fits, say which constraint to relax. Never use movies that Referee marked DOESN'T FIT.
"""


def make_team() -> tuple[SequentialAgent, list[McpToolset]]:
    scout_tools = _mcp()

    scout = LlmAgent(
        name="scout",
        model="gemini-2.5-flash",
        description="Finds movie candidates on TMDB and fetches details. Retrieval only. Use FIRST.",
        instruction=SCOUT_PROMPT,
        tools=[scout_tools],
    )

    referee = LlmAgent(
        name="referee",
        model="gemini-2.5-flash",
        description="Checks candidate movies against runtime, age rating, and genre constraints. Use AFTER Scout.",
        instruction=REFEREE_PROMPT,
    )

    host = LlmAgent(
        name="host",
        model=_host_model(),
        description="Writes the final ranked movie shortlist from Scout and Referee results.",
        instruction=HOST_PROMPT,
    )

    team = SequentialAgent(
        name="movie_night_team",
        description="Runs Scout, Referee, then Host in a fixed movie-planning pipeline.",
        sub_agents=[scout, referee, host],
    )

    return team, [scout_tools]


async def run_once(request: str, verbose: bool = False) -> str:
    host, toolsets = make_team()
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        state={}, app_name="movie_night_planner", user_id="user_1"
    )
    runner = Runner(agent=host, app_name="movie_night_planner", session_service=session_service)
    content = types.Content(role="user", parts=[types.Part(text=request)])
    final = ""
    started = time.time()

    try:
        async for event in runner.run_async(
            session_id=session.id, user_id="user_1", new_message=content
        ):
            if verbose:
                author = getattr(event, "author", "?")
                kind = "final" if event.is_final_response() else "event"
                print(f"[{time.time() - started:5.1f}s] {kind} from {author}", file=sys.stderr)
            if event.content and event.is_final_response() and event.content.parts:
                final = event.content.parts[0].text or final
        return final
    finally:
        for toolset in toolsets:
            try:
                await toolset.close()
            except Exception:
                pass


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-Agent Movie Night Planner")
    parser.add_argument("request", nargs="*", help="Movie night details as free text.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print event trace to stderr.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    request = " ".join(args.request).strip()
    if not request:
        request = input("Movie night details: ").strip()
    if not request:
        raise SystemExit("Please provide the movie night details.")
    print(asyncio.run(run_once(request, verbose=args.verbose)))


if __name__ == "__main__":
    main()
