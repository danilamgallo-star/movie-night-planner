# Movie Night Planner

A small multi-agent movie recommender built with Google ADK, MCP, and TMDB.

You describe the movie night, for example the age of the youngest viewer, how much time you have, and the kind of movie you want. The app looks up real movie data, filters out bad fits, and returns a short recommendation list.

Example request:

```text
Family movie night: 4 people, youngest is 8, 2 hours, adventure and animation.
```

## How It Works

The app uses three agents in order:

1. **Scout** finds candidate movies from TMDB.
2. **Referee** checks runtime, age rating, and genre fit.
3. **Host** writes the final shortlist.

The flow is fixed with a `SequentialAgent`:

```text
Scout -> Referee -> Host
```

TMDB access is handled through the local MCP server in `tmdb_server.py`.

## Setup

Use Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
TMDB_API_KEY=your_tmdb_api_key_here
USE_CLAUDE_HOST=true
CLAUDE_MODEL=anthropic/claude-sonnet-4-6
```

For ADK Web, each agent folder also needs an `.env`. The easiest way is:

```bash
cp .env scout_agent/.env
cp .env referee_agent/.env
cp .env movie_night_team/.env
```

## Run From Terminal

```bash
source .venv/bin/activate
python movie_night_planner.py "Family movie night: 4 people, youngest is 8, 2 hours, adventure and animation."
```

To see the agent events:

```bash
python movie_night_planner.py --verbose "2 adults and a 10-year-old, 90 minutes, comedy"
```

## Run With ADK Web

```bash
source .venv/bin/activate
adk web
```

Open the URL from the terminal, usually:

```text
http://127.0.0.1:8000
```

Use `movie_night_team` for the full flow. The other agents are useful for testing pieces separately:

- `scout_agent`: movie lookup only
- `referee_agent`: constraint checking only
- `movie_night_team`: full recommendation flow

## Project Structure

```text
movie_night_planner/
├── movie_night_planner.py      # CLI runner
├── tmdb_server.py              # MCP server for TMDB tools
├── requirements.txt
├── .env.example
├── scout_agent/
│   └── agent.py
├── referee_agent/
│   └── agent.py
├── movie_night_team/
│   └── agent.py
└── sample_runs/
    └── family_animation_sample.txt
```

## MCP Tools

`tmdb_server.py` exposes three tools:

- `discover_movies(genre, max_runtime, age_rating)`
- `search_movies(query)`
- `get_movie_details(movie_id)`

The returned movie data is trimmed to the fields the agents need:

```text
title, year, id, runtime, certification, genres, score
```

## Models

Scout and Referee use Gemini.

Host uses Claude through LiteLLM by default:

```env
USE_CLAUDE_HOST=true
CLAUDE_MODEL=anthropic/claude-sonnet-4-6
```

To use Gemini for Host too:

```env
USE_CLAUDE_HOST=false
```

## Notes

Do not commit real `.env` files. Keep secrets in `.env` and use `.env.example` only as a template.

Movie metadata comes from [The Movie Database (TMDB)](https://www.themoviedb.org/). This project uses the TMDB API but is not endorsed or certified by TMDB.
