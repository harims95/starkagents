"""
StarkAgents Backend
FastAPI + OpenAI gpt-4o-mini — Swarm Intelligence Engine
Architecture: Knowledge Graph → Env Config → 2-Round Parallel Debate → Verdict
"""

import os
import json
import asyncio
import hashlib
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# ============================================================
# CONFIG
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = "gpt-4o-mini"
MAX_TOKENS = 200

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ============================================================
# PILLARS (4)
# ============================================================

PILLARS = [
    {
        "key": "market",
        "label": "Market Demand & Timing",
        "icon": "🌊",
        "color": "#00FFD4",
        "criteria": "Is there real, growing demand? Is the timing right? Are macro trends supporting this?"
    },
    {
        "key": "revenue",
        "label": "Revenue & Business Model",
        "icon": "💰",
        "color": "#FBBF24",
        "criteria": "Is the monetization clear? Are unit economics sustainable? Can the model scale?"
    },
    {
        "key": "adoption",
        "label": "User Adoption & Retention",
        "icon": "🎯",
        "color": "#38BDF8",
        "criteria": "Will users adopt this? Is the value prop clear in <10 seconds? Will they retain?"
    },
    {
        "key": "competition",
        "label": "Competitive Survival",
        "icon": "⚔️",
        "color": "#F472B6",
        "criteria": "Can this survive competitive attacks? Is the moat real? How fast can incumbents copy this?"
    },
]

# ============================================================
# AGENT ROSTER (12 defined, 6 active for demo)
# ============================================================

ALL_AGENTS = {
    "MarketPulse": {
        "id": "psi-2041",
        "name": "Agent Ψ-2041",
        "handle": "MarketPulse",
        "role": "Market Demand Analyst",
        "category": "MARKET INTELLIGENCE",
        "avatar": "🌊",
        "color": "#00FFD4",
        "never_flips_on": "market_size",
        "system": """You are Agent Ψ-2041 "Market Pulse", a Market Demand Analyst in a startup prediction swarm.
You evaluate market size, timing, demand signals, and macro trends. You are data-driven.
When market data is strong, you say so clearly. When it's weak, you don't sugarcoat it.
You NEVER change your assessment of raw market size — only interpretation.
You must respond ONLY with valid JSON, no markdown, no backticks."""
    },
    "TrendSeeker": {
        "id": "omega-trend",
        "name": "Agent Ω-8873",
        "handle": "TrendSeeker",
        "role": "Trend & Timing Specialist",
        "category": "MARKET INTELLIGENCE",
        "avatar": "📈",
        "color": "#34D399",
        "system": """You are Agent Ω-8873 "Trend Seeker", a Trend & Timing Specialist in a startup prediction swarm.
You analyze adoption curves, technology readiness, and cultural shifts. You think in S-curves.
You are bullish on well-timed ideas, bearish on ideas that are too early or too late.
You must respond ONLY with valid JSON, no markdown, no backticks."""
    },
    "UnitEcon": {
        "id": "delta-1159",
        "name": "Agent Δ-1159",
        "handle": "UnitEcon",
        "role": "Unit Economics Analyst",
        "category": "FINANCIAL ANALYSIS",
        "avatar": "💰",
        "color": "#FBBF24",
        "system": """You are Agent Δ-1159 "Unit Econ", a Unit Economics Analyst in a startup prediction swarm.
You stress-test revenue models, CAC/LTV ratios, and burn rate sustainability.
You are brutally honest about financial viability. Numbers don't lie.
You must respond ONLY with valid JSON, no markdown, no backticks."""
    },
    "RevenueScout": {
        "id": "sigma-rev",
        "name": "Agent Σ-4420",
        "handle": "RevenueScout",
        "role": "Business Model Evaluator",
        "category": "FINANCIAL ANALYSIS",
        "avatar": "💎",
        "color": "#F59E0B",
        "system": """You are Agent Σ-4420 "Revenue Scout", a Business Model Evaluator in a startup prediction swarm.
You evaluate pricing strategy, monetization paths, and scalability of the model.
You look for sustainable revenue engines, not just growth hacks.
You must respond ONLY with valid JSON, no markdown, no backticks."""
    },
    "FirstClick": {
        "id": "lambda-7766",
        "name": "Agent Λ-7766",
        "handle": "FirstClick",
        "role": "Early Adopter Simulator",
        "category": "USER PSYCHOLOGY",
        "avatar": "🎯",
        "color": "#38BDF8",
        "system": """You are Agent Λ-7766 "First Click", an Early Adopter Simulator in a startup prediction swarm.
You simulate the first-time user experience. You test whether the value prop is clear in under 10 seconds.
You are enthusiastic about products that nail the first impression.
You must respond ONLY with valid JSON, no markdown, no backticks."""
    },
    "StickyLoop": {
        "id": "phi-3302",
        "name": "Agent Φ-3302",
        "handle": "StickyLoop",
        "role": "Retention & Habit Analyst",
        "category": "USER PSYCHOLOGY",
        "avatar": "🔄",
        "color": "#818CF8",
        "system": """You are Agent Φ-3302 "Sticky Loop", a Retention & Habit Analyst in a startup prediction swarm.
You evaluate habit loops, switching costs, and D1/D7/D30 retention predictions.
You know that acquisition is cheap — retention is everything.
You must respond ONLY with valid JSON, no markdown, no backticks."""
    },
    "RedTeam": {
        "id": "theta-9915",
        "name": "Agent Θ-9915",
        "handle": "RedTeam",
        "role": "Competitor Simulator",
        "category": "COMPETITIVE WARFARE",
        "avatar": "⚔️",
        "color": "#F87171",
        "aggression_if_bullish_consensus": True,
        "system": """You are Agent Θ-9915 "Red Team", a Competitor Simulator in a startup prediction swarm.
You think like the #1 competitor. How fast can they copy this? What would Google, Amazon, or a well-funded rival do?
You get MORE aggressive when other agents are too bullish — someone has to stress-test the defenses.
You must respond ONLY with valid JSON, no markdown, no backticks."""
    },
    "MoatInspector": {
        "id": "xi-5508",
        "name": "Agent Ξ-5508",
        "handle": "MoatInspector",
        "role": "Defensibility Analyst",
        "category": "COMPETITIVE WARFARE",
        "avatar": "🛡️",
        "color": "#FB923C",
        "system": """You are Agent Ξ-5508 "Moat Inspector", a Defensibility Analyst in a startup prediction swarm.
You evaluate network effects, data moats, technical barriers, and regulatory moats.
You respect real moats. You are bearish on superficial differentiation.
You must respond ONLY with valid JSON, no markdown, no backticks."""
    },
    "BuildCheck": {
        "id": "pi-6641",
        "name": "Agent Π-6641",
        "handle": "BuildCheck",
        "role": "Technical Architect",
        "category": "TECHNICAL FEASIBILITY",
        "avatar": "⚙️",
        "color": "#94A3B8",
        "system": """You are Agent Π-6641 "Build Check", a Technical Architect in a startup prediction swarm.
You assess if the solution is technically buildable, scalable, and maintainable with a small team.
You think about infrastructure costs, technical debt, and engineering complexity.
You must respond ONLY with valid JSON, no markdown, no backticks."""
    },
    "PolicyScan": {
        "id": "zeta-1287",
        "name": "Agent Ζ-1287",
        "handle": "PolicyScan",
        "role": "Regulatory Risk Analyst",
        "category": "REGULATORY & COMPLIANCE",
        "avatar": "📋",
        "color": "#C084FC",
        "is_blocker": True,
        "block_threshold": 80,
        "system": """You are Agent Ζ-1287 "Policy Scan", a Regulatory Risk Analyst in a startup prediction swarm.
You flag legal risks, compliance requirements, and regulatory exposure.
If regulatory risk is severe (>80% confidence of bearish), you can effectively block the verdict.
You must respond ONLY with valid JSON, no markdown, no backticks."""
    },
    "ViralEngine": {
        "id": "kappa-3394",
        "name": "Agent Κ-3394",
        "handle": "ViralEngine",
        "role": "Growth Hacker",
        "category": "GROWTH & DISTRIBUTION",
        "avatar": "🚀",
        "color": "#4ADE80",
        "system": """You are Agent Κ-3394 "Viral Engine", a Growth Hacker in a startup prediction swarm.
You evaluate distribution channels, viral mechanics, and content-led growth potential.
You are optimistic about clever distribution but skeptical of products that require paid acquisition to survive.
You must respond ONLY with valid JSON, no markdown, no backticks."""
    },
    "SkepticalVC": {
        "id": "rho-5571",
        "name": "Agent Ρ-5571",
        "handle": "SkepticalVC",
        "role": "VC Devil's Advocate",
        "category": "INVESTOR PERSPECTIVE",
        "avatar": "🦈",
        "color": "#FF6B8A",
        "always_probes_bullish": True,
        "system": """You are Agent Ρ-5571 "Skeptical Check", a VC Devil's Advocate in a startup prediction swarm.
You've reviewed 3000+ pitches and funded less than 2%. You look for unrealistic assumptions, unclear monetization, weak moats, and bad timing.
You are tough but fair — when something is genuinely strong, you say so. But you ALWAYS find at least one serious hole.
You must respond ONLY with valid JSON, no markdown, no backticks."""
    },
}

# Active agents for hackathon demo (6 agents)
DEMO_AGENT_KEYS = ["MarketPulse", "UnitEcon", "RedTeam", "PolicyScan", "ViralEngine", "SkepticalVC"]
DEMO_AGENTS = [ALL_AGENTS[k] for k in DEMO_AGENT_KEYS]

# ============================================================
# MODELS
# ============================================================

class StartupIdea(BaseModel):
    name: str
    problem: str
    solution: str
    market: str
    model: str
    scenario: Optional[str] = None
    is_public: bool = True

# ============================================================
# KNOWLEDGE GRAPH BUILDER
# ============================================================

async def build_knowledge_graph(idea: StartupIdea) -> dict:
    """Extract structured knowledge graph from startup pitch — one fast LLM call."""

    prompt = f"""Analyze this startup idea and extract a structured knowledge graph.

STARTUP:
- Name: {idea.name}
- Problem: {idea.problem}
- Solution: {idea.solution}
- Market: {idea.market}
- Business Model: {idea.model}

Respond ONLY with this JSON (no markdown, no backticks):
{{
  "domain": "fintech|b2b_saas|consumer|healthtech|edtech|marketplace|infrastructure|other",
  "market_stage": "emerging|growing|mature|declining",
  "business_model": "subscription|marketplace|transactional|advertising|freemium|other",
  "key_risks": ["<risk1>", "<risk2>", "<risk3>"],
  "key_strengths": ["<strength1>", "<strength2>"],
  "comparable_startups": ["<company1>", "<company2>"],
  "enemy_archetype": "<who would kill this startup>",
  "buyer_persona": "enterprise|smb|consumer|developer",
  "geography": "global|us|emerging_markets|regional"
}}"""

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=300,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a startup analyst. Extract structured data from startup pitches. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
    )
    return json.loads(response.choices[0].message.content)


# ============================================================
# ENVIRONMENT CONFIG AGENT
# ============================================================

async def configure_environment(graph: dict, available_agents: list) -> dict:
    """Decide which agents to activate and with what biases — based on knowledge graph."""

    agent_names = [a["handle"] for a in available_agents]

    prompt = f"""You are an Environment Configuration Agent for a startup prediction swarm.
Based on this knowledge graph, select and configure the best agents for this simulation.

KNOWLEDGE GRAPH:
{json.dumps(graph, indent=2)}

AVAILABLE AGENTS: {agent_names}

Rules:
- Always include SkepticalVC and at least one market agent
- If domain is fintech/healthtech/legaltech → boost PolicyScan weight
- If market_stage is mature → set RedTeam aggression high
- If business_model is marketplace → focus UnitEcon on liquidity bootstrap

Respond ONLY with this JSON (no markdown, no backticks):
{{
  "agents_to_activate": ["<handle1>", "<handle2>", ...],
  "agent_notes": {{
    "<handle>": "<one sentence on what to focus on for this specific startup>"
  }},
  "dominant_risk": "<the single biggest risk for this startup>",
  "dominant_strength": "<the single biggest strength>",
  "consensus_threshold": 0.65
}}"""

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=300,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are an environment configuration agent. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
    )
    config = json.loads(response.choices[0].message.content)

    # Validate: ensure agents_to_activate only contains known handles
    valid_handles = {a["handle"] for a in available_agents}
    config["agents_to_activate"] = [
        h for h in config.get("agents_to_activate", agent_names)
        if h in valid_handles
    ]
    if not config["agents_to_activate"]:
        config["agents_to_activate"] = agent_names

    return config


# ============================================================
# AGENT ENGINE
# ============================================================

async def run_agent(
    agent: dict,
    idea: StartupIdea,
    pillar: dict,
    graph: dict,
    env_config: dict,
    round_num: int,
    r1_results: list = None,
    god_view_prefix: str = ""
) -> dict:
    """Run a single agent evaluation — Round 1 or Round 2."""

    # Graph context injected into every agent
    graph_context = f"""
STARTUP KNOWLEDGE GRAPH:
- Domain: {graph.get('domain')}
- Market Stage: {graph.get('market_stage')}
- Business Model: {graph.get('business_model')}
- Key Risks: {', '.join(graph.get('key_risks', []))}
- Key Strengths: {', '.join(graph.get('key_strengths', []))}
- Comparable Startups: {', '.join(graph.get('comparable_startups', []))}
- Biggest Threat: {graph.get('enemy_archetype')}
- Buyer Persona: {graph.get('buyer_persona')}"""

    # Agent-specific focus note from env config
    focus_note = env_config.get("agent_notes", {}).get(agent["handle"], "")
    focus_line = f"\nYOUR FOCUS FOR THIS STARTUP: {focus_note}" if focus_note else ""

    # Round 2: inject memory of R1 + other agents' positions
    memory_injection = ""
    if round_num == 2 and r1_results:
        my_r1 = next((r for r in r1_results if r["agent_id"] == agent["id"]), None)
        others = [r for r in r1_results if r["agent_id"] != agent["id"]]

        if my_r1:
            memory_injection = f"""
ROUND 1 MEMORY — YOUR PREVIOUS STANCE:
You said: "{my_r1['reasoning']}" with {my_r1['confidence']}% confidence ({my_r1['stance']}).

OTHER AGENTS' ROUND 1 POSITIONS:
{chr(10).join([f"- {r['agent_name']} ({r['agent_role']}): {r['stance']} ({r['confidence']}%) — {r['reasoning']}" for r in others])}

Based on your peers' arguments, do you MAINTAIN or REVISE your position?
If you change stance, explicitly state which argument convinced you."""

    # God View prefix
    god_line = f"\n{god_view_prefix}" if god_view_prefix else ""

    user_prompt = f"""Evaluate this startup on: **{pillar['label']}**

Consider: {pillar['criteria']}
{graph_context}
{focus_line}
{god_line}
STARTUP:
- Name: {idea.name}
- Problem: {idea.problem}
- Solution: {idea.solution}
- Market: {idea.market}
- Business Model: {idea.model}
{memory_injection}

Respond ONLY with this JSON (no markdown, no backticks):
{{"stance": "bullish" or "bearish", "confidence": <40-95>, "reasoning": "<2-3 sentences>"}}"""

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": agent["system"]},
                {"role": "user", "content": user_prompt}
            ]
        )
        result = json.loads(response.choices[0].message.content)

        return {
            "agent_id": agent["id"],
            "agent_name": agent["name"],
            "agent_handle": agent["handle"],
            "agent_role": agent["role"],
            "agent_category": agent["category"],
            "agent_avatar": agent["avatar"],
            "agent_color": agent["color"],
            "pillar": pillar["key"],
            "round": round_num,
            "stance": result.get("stance", "bearish"),
            "confidence": min(95, max(40, int(result.get("confidence", 60)))),
            "reasoning": result.get("reasoning", "Analysis inconclusive."),
        }

    except Exception:
        return {
            "agent_id": agent["id"],
            "agent_name": agent["name"],
            "agent_handle": agent["handle"],
            "agent_role": agent["role"],
            "agent_category": agent["category"],
            "agent_avatar": agent["avatar"],
            "agent_color": agent["color"],
            "pillar": pillar["key"],
            "round": round_num,
            "stance": "bearish",
            "confidence": 45,
            "reasoning": "Agent encountered an error. Defaulting to cautious assessment.",
        }


# ============================================================
# SCORING
# ============================================================

def compute_pillar_score(votes: list) -> int:
    bullish = [v for v in votes if v["stance"] == "bullish"]
    bearish = [v for v in votes if v["stance"] == "bearish"]
    bull_w = sum(v["confidence"] for v in bullish)
    bear_w = sum(v["confidence"] for v in bearish)
    if bull_w + bear_w == 0:
        return 50
    return round((bull_w / (bull_w + bear_w)) * 100)


def is_contested(r2_by_pillar: dict) -> bool:
    """True if any pillar has a 50/50 or close split."""
    for votes in r2_by_pillar.values():
        bullish = sum(1 for v in votes if v["stance"] == "bullish")
        bearish = sum(1 for v in votes if v["stance"] == "bearish")
        total = bullish + bearish
        if total > 0 and abs(bullish - bearish) <= 1:
            return True
    return False


def is_policy_blocked(agents: list, r2_results: list) -> bool:
    """PolicyScan blocks verdict if bearish with >80 confidence."""
    policy_agent = next((a for a in agents if a.get("is_blocker")), None)
    if not policy_agent:
        return False
    policy_votes = [r for r in r2_results if r["agent_id"] == policy_agent["id"] and r["stance"] == "bearish"]
    return any(v["confidence"] >= policy_agent.get("block_threshold", 80) for v in policy_votes)


def count_stance_flips(r1: list, r2: list) -> int:
    flips = 0
    r1_map = {(r["agent_id"], r["pillar"]): r["stance"] for r in r1}
    for r in r2:
        key = (r["agent_id"], r["pillar"])
        if key in r1_map and r1_map[key] != r["stance"]:
            flips += 1
    return flips


def compute_verdict(pillar_scores: dict, agents: list, r1: list, r2: list, r2_by_pillar: dict):
    avg = sum(pillar_scores.values()) / len(pillar_scores)
    score = round(avg)
    flips = count_stance_flips(r1, r2)
    contested = is_contested(r2_by_pillar)
    blocked = is_policy_blocked(agents, r2)

    if blocked:
        score = min(score, 40)
        label = "BLOCKED — REGULATORY RISK"
    elif contested:
        score = min(score, 65)
        label = "CONTESTED — DIVIDED SWARM"
    elif score >= 65:
        label = "LIKELY SUCCESS"
    elif score >= 45:
        label = "UNCERTAIN — PIVOT ADVISED"
    else:
        label = "HIGH RISK — RETHINK"

    consensus = round(100 - (flips / max(len(r2), 1)) * 100)

    return {
        "final_score": score,
        "verdict": label,
        "stance_flips": flips,
        "consensus_level": consensus,
        "contested": contested,
        "blocked": blocked,
    }


def compute_idea_hash(idea: StartupIdea) -> str:
    content = f"{idea.name}|{idea.problem}|{idea.solution}|{idea.market}|{idea.model}"
    return "0x" + hashlib.sha256(content.encode()).hexdigest()[:64]


# ============================================================
# GOD VIEW DELTA
# ============================================================

async def build_god_view_prefix(scenario: str, original_graph: dict) -> str:
    """Extract delta from scenario and return prompt prefix for all agents."""

    prompt = f"""A "what-if" scenario has been injected into a startup simulation.

ORIGINAL CONTEXT:
{json.dumps(original_graph, indent=2)}

NEW SCENARIO: "{scenario}"

Extract what changed. Respond ONLY with this JSON:
{{
  "changed_factors": ["<factor1>", "<factor2>"],
  "new_risks": ["<risk1>"],
  "impact_summary": "<one sentence on how this changes the startup's outlook>"
}}"""

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=200,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Extract simulation deltas. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
    )
    delta = json.loads(response.choices[0].message.content)

    return f"""REALITY OVERRIDE ACTIVE: "{scenario}"
What changed: {', '.join(delta.get('changed_factors', []))}
New risks: {', '.join(delta.get('new_risks', []))}
Impact: {delta.get('impact_summary', '')}
Re-evaluate everything with this new reality in mind."""


# ============================================================
# FASTAPI APP
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("StarkAgents Backend Starting...")
    if not OPENAI_API_KEY:
        print("WARNING: OPENAI_API_KEY not set!")
    else:
        print("OpenAI API key loaded OK")
    yield
    print("StarkAgents Backend Shutting Down...")

app = FastAPI(title="StarkAgents API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

simulations = {}


@app.get("/api/health")
async def health():
    return {
        "status": "alive",
        "service": "starkagents",
        "agents_total": len(ALL_AGENTS),
        "agents_demo": len(DEMO_AGENTS),
        "pillars": len(PILLARS),
        "model": MODEL,
    }


@app.get("/api/agents")
async def list_agents():
    """Return full agent roster for UI display."""
    return [
        {
            "handle": k,
            "name": v["name"],
            "role": v["role"],
            "category": v["category"],
            "avatar": v["avatar"],
            "color": v["color"],
        }
        for k, v in ALL_AGENTS.items()
    ]


@app.websocket("/ws/simulate")
async def websocket_simulation(websocket: WebSocket):
    """Full simulation pipeline streamed via WebSocket."""
    await websocket.accept()

    try:
        data = await websocket.receive_json()
        idea = StartupIdea(**data)
        idea_hash = compute_idea_hash(idea)

        # Determine active agents
        agents = DEMO_AGENTS

        await websocket.send_json({
            "type": "start",
            "idea_hash": idea_hash,
            "total_pillars": len(PILLARS),
            "total_agents": len(agents),
        })

        # ── Step 1: Knowledge Graph ──────────────────────────────
        graph = await build_knowledge_graph(idea)
        await websocket.send_json({"type": "graph_built", "data": graph})

        # ── Step 2: Environment Config ───────────────────────────
        env_config = await configure_environment(graph, agents)

        # Filter agents to those selected by env config
        active_handles = set(env_config.get("agents_to_activate", [a["handle"] for a in agents]))
        active_agents = [a for a in agents if a["handle"] in active_handles]

        await websocket.send_json({
            "type": "config_ready",
            "data": env_config,
            "active_agents": [a["handle"] for a in active_agents],
        })

        # ── Step 3: God View prefix (if scenario) ────────────────
        god_view_prefix = ""
        if idea.scenario:
            god_view_prefix = await build_god_view_prefix(idea.scenario, graph)
            await websocket.send_json({"type": "god_view_active", "scenario": idea.scenario})

        # ── Step 4: Round 1 — all agents × all pillars, parallel ─
        all_r1 = []
        r1_by_pillar = {}

        for pillar in PILLARS:
            await websocket.send_json({
                "type": "pillar_start",
                "pillar": pillar["key"],
                "label": pillar["label"],
                "icon": pillar["icon"],
                "color": pillar["color"],
                "round": 1,
            })

            # All agents for this pillar run in parallel
            async def run_and_stream_r1(agent, pillar=pillar):
                result = await run_agent(agent, idea, pillar, graph, env_config, round_num=1, god_view_prefix=god_view_prefix)
                await websocket.send_json({"type": "agent_result", **result})
                return result

            pillar_r1 = await asyncio.gather(*[run_and_stream_r1(a) for a in active_agents])
            pillar_r1 = list(pillar_r1)
            r1_by_pillar[pillar["key"]] = pillar_r1
            all_r1.extend(pillar_r1)

        await websocket.send_json({"type": "round_complete", "round": 1})

        # ── Step 5: Round 2 — agents see R1 results, parallel ────
        all_r2 = []
        r2_by_pillar = {}

        for pillar in PILLARS:
            await websocket.send_json({
                "type": "pillar_start",
                "pillar": pillar["key"],
                "label": pillar["label"],
                "icon": pillar["icon"],
                "color": pillar["color"],
                "round": 2,
            })

            pillar_r1_results = r1_by_pillar[pillar["key"]]

            async def run_and_stream_r2(agent, pillar=pillar, pillar_r1=pillar_r1_results):
                result = await run_agent(
                    agent, idea, pillar, graph, env_config,
                    round_num=2,
                    r1_results=pillar_r1,
                    god_view_prefix=god_view_prefix
                )
                # Detect stance flip
                r1_match = next((r for r in pillar_r1 if r["agent_id"] == agent["id"]), None)
                if r1_match and r1_match["stance"] != result["stance"]:
                    result["flipped"] = True
                    result["previous_stance"] = r1_match["stance"]
                    await websocket.send_json({"type": "stance_flip", **result})
                else:
                    result["flipped"] = False
                await websocket.send_json({"type": "agent_result", **result})
                return result

            pillar_r2 = await asyncio.gather(*[run_and_stream_r2(a) for a in active_agents])
            pillar_r2 = list(pillar_r2)
            r2_by_pillar[pillar["key"]] = pillar_r2
            all_r2.extend(pillar_r2)

        await websocket.send_json({"type": "round_complete", "round": 2})

        # ── Step 6: Scoring ───────────────────────────────────────
        pillar_scores = {
            p["key"]: compute_pillar_score(r2_by_pillar[p["key"]])
            for p in PILLARS
        }

        verdict_data = compute_verdict(pillar_scores, active_agents, all_r1, all_r2, r2_by_pillar)

        final_payload = {
            "type": "verdict",
            "idea_hash": idea_hash,
            "pillar_scores": pillar_scores,
            "agent_count": len(active_agents),
            "is_public": idea.is_public,
            **verdict_data,
        }

        await websocket.send_json(final_payload)
        simulations[idea_hash] = {**final_payload, "votes_r1": all_r1, "votes_r2": all_r2, "graph": graph}

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@app.get("/api/simulation/{idea_hash}")
async def get_simulation(idea_hash: str):
    if idea_hash not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return simulations[idea_hash]


@app.get("/api/verdicts")
async def list_verdicts():
    return [
        {k: v for k, v in sim.items() if k not in ("votes_r1", "votes_r2")}
        for sim in simulations.values()
        if sim.get("is_public", True)
    ]


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
