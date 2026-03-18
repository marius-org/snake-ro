from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, constr
from typing import Optional
import os
import asyncpg
import asyncio
from datetime import datetime

app = FastAPI(title="Șarpele Român API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Database ──────────────────────────────────────────────
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://snake:snakepass@localhost:5432/snakedb"
)

db_pool = None

async def get_pool():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10)
    return db_pool

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id          SERIAL PRIMARY KEY,
                player_name VARCHAR(50)  NOT NULL,
                score       INTEGER      NOT NULL,
                created_at  TIMESTAMPTZ  DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scores_score
            ON scores (score DESC)
        """)

@app.on_event("startup")
async def startup():
    retries = 5
    for i in range(retries):
        try:
            await init_db()
            print("✅ Database connected and initialized")
            return
        except Exception as e:
            print(f"⏳ DB not ready ({i+1}/{retries}): {e}")
            await asyncio.sleep(3)
    print("❌ Could not connect to database — running without persistence")

@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        await db_pool.close()

# ── Models ────────────────────────────────────────────────
class ScoreSubmit(BaseModel):
    player_name: str
    score: int

class ScoreResponse(BaseModel):
    id: int
    player_name: str
    score: int
    created_at: datetime

# ── Routes ────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "snake-ro"}

@app.post("/api/scores", response_model=ScoreResponse)
async def submit_score(data: ScoreSubmit):
    if not data.player_name.strip():
        raise HTTPException(400, "Numele nu poate fi gol")
    if data.score < 0:
        raise HTTPException(400, "Scorul nu poate fi negativ")
    if data.score > 99999:
        raise HTTPException(400, "Scor prea mare — ești sigur că nu trișezi?")

    name = data.player_name.strip()[:50]

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO scores (player_name, score)
                VALUES ($1, $2)
                RETURNING id, player_name, score, created_at
            """, name, data.score)
        return dict(row)
    except Exception as e:
        raise HTTPException(500, f"Eroare bază de date: {str(e)}")

@app.get("/api/scores")
async def get_scores(limit: int = 10, player: Optional[str] = None):
    limit = min(max(1, limit), 100)
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            if player:
                rows = await conn.fetch("""
                    SELECT id, player_name, score, created_at
                    FROM scores
                    WHERE LOWER(player_name) = LOWER($1)
                    ORDER BY score DESC
                    LIMIT $2
                """, player, limit)
            else:
                rows = await conn.fetch("""
                    SELECT DISTINCT ON (player_name)
                        id, player_name, score, created_at
                    FROM scores
                    ORDER BY player_name, score DESC
                    LIMIT $1
                """, limit * 3)

                # Re-sort by score and take top N
                rows = sorted(rows, key=lambda r: r['score'], reverse=True)[:limit]

        return [dict(r) for r in rows]
    except Exception as e:
        # Return empty if DB not available
        return []

@app.get("/api/scores/stats")
async def get_stats():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*)           AS total_games,
                    COUNT(DISTINCT player_name) AS unique_players,
                    MAX(score)         AS high_score,
                    AVG(score)::INT    AS avg_score
                FROM scores
            """)
        return dict(stats)
    except Exception as e:
        return {"error": str(e)}

# Serve frontend static files
if os.path.exists("/app/static"):
    app.mount("/", StaticFiles(directory="/app/static", html=True), name="static")
