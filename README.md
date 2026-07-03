# Multi-Agent Movie Night Planner

Capstone project for **Claude and Google ADK — Building Agentic Systems with MCP**.

This repo follows the Module 4 structure: specialist agents plus a root orchestrator. The movie data layer is an MCP server backed by TMDB.

## What it does

Given a free-text movie night request like:

```bash
python movie_night_planner.py "4 people, youngest is 8, 2 hours, we like animation and adventure"
```

The team runs this pipeline:

1. **Scout** retrieves candidate movies from TMDB and fetches runtime, US certification, genres, and audience score.
2. **Referee** checks each candidate against the hard constraints: time budget, youngest viewer, and genre/vibe.
3. **Host** recommends a ranked shortlist of movies that fit.

## Project structure

```text
movie_night_planner/
├── tmdb_server.py              # FastMCP server exposing TMDB tools
├── movie_night_planner.py      # CLI Runner
├── requirements.txt
├── .env.example
├── scout_agent/
│   ├── __init__.py
│   ├── agent.py
│   └── .env.example
├── referee_agent/
│   ├── __init__.py
│   ├── agent.py
│   └── .env.example
├── movie_night_team/
│   ├── __init__.py
│   ├── agent.py              # Root Host with sub_agents=[scout, referee]
│   └── .env.example
└── sample_runs/
    └── family_animation_sample.txt
```

## Setup

Use Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

```env
TMDB_API_KEY=your_tmdb_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
USE_CLAUDE_HOST=true
CLAUDE_MODEL=anthropic/claude-sonnet-4-6
```

For `adk web`, also copy `.env.example` into each agent folder and fill the keys, or copy your root `.env` into those folders:

```bash
cp .env scout_agent/.env
cp .env referee_agent/.env
cp .env movie_night_team/.env
```

## Run the MCP server by itself

```bash
python tmdb_server.py
```

It will wait silently for an MCP client. Stop it with `Ctrl+C`.

## Run agents in ADK Web

From the repo root:

```bash
adk web
```

Pick:

- `scout_agent` to test retrieval only.
- `referee_agent` to test constraint checking by pasting candidate data.
- `movie_night_team` to run the full Host → Scout → Referee workflow.

## Run the CLI

```bash
python movie_night_planner.py "Family movie night: 4 people, youngest is 8, 2 hours, everyone loves adventure and animation."
```

Verbose event tracing:

```bash
python movie_night_planner.py --verbose "2 adults and a 10-year-old, 90 minutes, comedy"
```

## Model swap

The Host uses Claude through LiteLlm by default:

```python
LiteLlm(model="anthropic/claude-sonnet-4-6")
```

To use Gemini for the Host instead:

```env
USE_CLAUDE_HOST=false
```

Scout and Referee use `gemini-2.5-flash`.

## MCP tools

`tmdb_server.py` exposes:

- `discover_movies(genre, max_runtime, age_rating)`
- `search_movies(query)`
- `get_movie_details(movie_id)`

The server trims TMDB responses to keep agent context small:

```text
title, year, id, runtime, certification, genres, score
```

## TMDB attribution

This product uses the TMDB API but is not endorsed or certified by TMDB.

Movie metadata is provided by [The Movie Database (TMDB)](https://www.themoviedb.org/).
