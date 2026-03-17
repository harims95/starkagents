---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments: ['brainstorming-session-2026-03-17']
workflowType: 'architecture'
project_name: 'StarkAgents'
user_name: 'Asus'
date: '2026-03-17'
---

# StarkAgents — Architecture Decision Document

_Synthesized from brainstorming session 2026-03-17. All decisions locked._

---

## 1. System Overview

StarkAgents is a swarm intelligence engine that predicts startup viability using multi-agent AI debate, with verdicts published permanently on StarkNet.

**Core loop:**
```
Pitch Input → Knowledge Graph Builder → Environment Config Agent
→ War Room (2-round debate, parallel agent calls)
→ Verdict Scoring → On-Chain Publish (StarkZap)
→ God View (optional delta re-simulation, max 3)
```

**Speed target:** 8–10 seconds end-to-end
**AI model:** gpt-4o-mini (OpenAI), async parallel calls
**Chain:** StarkNet Sepolia (hackathon) → Mainnet (production)
**Auth:** StarkZap social login (Google/email), no seed phrases

---

## 2. Frontend Architecture

### Stack
- Single HTML file (`frontend/index.html`) — no build step
- CSS animations for bubble war room (no canvas, no D3)
- Vanilla JS for WebSocket + StarkZap SDK integration
- StarkZap via CDN or minimal Node.js proxy if CDN unavailable

### Screens
1. **Home** — headline, agent category groups, "Drop Your Pitch" CTA
2. **Input Form** — name, problem, solution, market, business model + visibility toggle (public/private)
3. **War Room** — CSS bubble swarm (live debate visualization)
4. **Verdict** — score (0–100), pillar breakdown, on-chain tx link (Starkscan)
5. **God View** — what-if scenario injection, delta score, max 3 re-runs

### Bubble UI Spec (30-min CSS implementation)
```css
/* Bubble = floating div, border-radius: 50% */
/* SIZE → agent confidence (px = confidence value) */
/* COLOR → bullish (cyan #00ff88) | bearish (red #ff4466) | neutral (purple #8844ff) */
/* ANIMATION → float keyframe, 4s ease-in-out infinite */
/* TRANSITION → background 0.8s on stance flip */
/* ARGUMENT LINE → SVG line between disagreeing agents, pulses during debate */
```

**Faction mechanics (JS):**
- Agents that agree drift toward same quadrant via `transform: translate()`
- Agents that disagree get `nudge` applied (small random offset)
- Stance flip triggers color transition + argument line disappears

**Dramatic events:**
- 3+ agents go bearish → red alert pulse on war room border
- Consensus achieved → all bubbles glow same color
- Contested verdict (split 3-2) → "CONTESTED" badge, score ceiling capped at 65

---

## 3. Backend Architecture

### Stack
- FastAPI + Uvicorn
- OpenAI AsyncOpenAI (gpt-4o-mini)
- WebSocket for streaming war room events to frontend
- Python-dotenv for env vars

### File: `backend/main.py`

**Endpoints:**
```
GET  /api/health
POST /api/analyze          → triggers full simulation pipeline
WS   /ws/warroom/{session} → streams agent events in real-time
```

**Pipeline (sequential steps, each streamed via WS):**

```
1. KnowledgeGraphAgent.build(pitch)     → graph JSON
2. EnvironmentConfigAgent.configure(graph) → simulation config
3. Round 1: all agents in parallel      → stances + reasoning
4. Round 2: all agents in parallel      → updated stances (see R1 outputs)
5. ScoringAgent.compute(r1, r2)         → verdict object
6. Return verdict → frontend publishes on-chain
```

**WebSocket event types:**
```python
{ "event": "graph_built",     "data": graph }
{ "event": "config_ready",    "data": config }
{ "event": "agent_result",    "data": { agent_id, round, stance, confidence, reasoning } }
{ "event": "agent_flip",      "data": { agent_id, old_stance, new_stance, reason } }
{ "event": "verdict_ready",   "data": verdict }
```

### Agent Call Format
```python
# System prompt = agent persona (detailed, graph-injected)
# User prompt = evaluation task for this pillar
# Response format: {"type": "json_object"}
# Response schema: {stance: "bullish"|"bearish", confidence: 40-95, reasoning: "2-3 sentences"}
# max_tokens: 200

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def call_agent(agent_id, system_prompt, user_prompt):
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        max_tokens=200,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return json.loads(response.choices[0].message.content)
```

---

## 4. Agent System Design

### Agent Roster (Cairo enum + Python mapping)

| ID | Name | Category | Persona Bias |
|---|---|---|---|
| MarketPulse | Market Pulse | Market Intelligence | Market size & demand signals |
| TrendSeeker | Trend Seeker | Market Intelligence | Timing & adoption curves |
| UnitEcon | Unit Econ | Financial Analysis | CAC/LTV, burn sustainability |
| RevenueScout | Revenue Scout | Financial Analysis | Pricing & monetization paths |
| FirstClick | First Click | User Psychology | <10 sec value prop clarity |
| StickyLoop | Sticky Loop | User Psychology | D1/D7/D30 retention |
| RedTeam | Red Team | Competitive Warfare | Thinks like #1 competitor |
| MoatInspector | Moat Inspector | Competitive Warfare | Network effects & defensibility |
| BuildCheck | Build Check | Technical Feasibility | Buildability & scalability |
| PolicyScan | Policy Scan | Regulatory & Compliance | Legal risks, can block verdict |
| ViralEngine | Viral Engine | Growth & Distribution | Distribution & viral mechanics |
| SkepticalVC | Skeptical VC | Investor Perspective | Tough VC, pokes holes |

**Hackathon demo:** 5–6 agents across 4 pillars
**Production:** All 12

### Behavioral Logic Per Agent

```python
AGENT_BEHAVIORS = {
    "RedTeam":     { "aggression_if_bullish_consensus": True },
    "PolicyScan":  { "can_block_verdict_if_risk_gt": 80 },
    "SkepticalVC": { "always_probes_bullish_agents": True },
    "MarketPulse": { "never_flips_on_market_size": True },
}
```

### Knowledge Graph Builder

One LLM call before agents run. Extracts:
```json
{
  "domain": "fintech|b2b_saas|consumer|healthtech|...",
  "market_stage": "emerging|growing|mature|declining",
  "business_model": "subscription|marketplace|transactional|...",
  "key_risks": ["regulation", "competition", "adoption"],
  "key_strengths": ["network_effect", "data_moat", "timing"],
  "comparable_startups": ["Stripe", "Robinhood"],
  "enemy_archetype": "Big Tech|incumbents|other_startups",
  "buyer_persona": "enterprise|smb|consumer",
  "geography": "global|us|emerging_markets"
}
```

### Environment Config Agent

Reads graph → outputs simulation config:
```json
{
  "agents_to_spawn": ["MarketPulse", "UnitEcon", "RedTeam", "PolicyScan", "SkepticalVC"],
  "agent_biases": {
    "RedTeam": { "aggression": 0.9, "thinks_like": "Stripe" },
    "PolicyScan": { "weight": 1.4, "is_blocker": true }
  },
  "debate_rounds": 2,
  "consensus_threshold": 0.65
}
```

### Round 2 Memory Injection

```python
# Each agent's Round 2 system prompt appends:
f"""
In Round 1 you said: '{agent_r1_reasoning}' with {agent_r1_confidence}% confidence.

Other agents said:
{other_agents_r1_summary}

Based on new information from your peers, do you maintain or revise your position?
If you change stance, explain which argument convinced you.
"""
```

---

## 5. Scoring Algorithm

```python
def compute_verdict(agents, r1_results, r2_results, config):
    pillar_scores = {}
    for pillar in ["market", "revenue", "adoption", "competition"]:
        pillar_agents = [a for a in agents if a.pillar == pillar]
        scores = [r2_results[a.id].confidence for a in pillar_agents]
        stances = [r2_results[a.id].stance for a in pillar_agents]

        # Bearish agents invert their score
        weighted = [(s if stance == "bullish" else 100-s) for s, stance in zip(scores, stances)]
        pillar_scores[pillar] = mean(weighted)

    # Policy blocker: hard cap at 40 if triggered
    if is_blocked(agents, r2_results, config):
        return cap(mean(pillar_scores.values()), max=40)

    # Contested: cap at 65 if split
    if is_contested(r2_results):
        return cap(mean(pillar_scores.values()), max=65)

    final_score = mean(pillar_scores.values())
    stance_flips = count_flips(r1_results, r2_results)
    consensus_level = compute_consensus(r2_results)

    return {
        "final_score": round(final_score),
        "pillar_scores": pillar_scores,
        "stance_flips": stance_flips,
        "consensus_level": round(consensus_level),
        "contested": is_contested(r2_results),
        "blocked": is_blocked(agents, r2_results, config)
    }
```

---

## 6. God View Architecture

**Mechanism:** Delta injection — original graph stays intact, override layer applied on top.

```python
def apply_god_view(original_graph, scenario_text):
    # One LLM call to extract delta from scenario
    delta = extract_delta(scenario_text, original_graph)

    # Merge: override only changed fields
    updated_graph = {**original_graph, **delta}

    # Inject into all agent prompts:
    god_view_prefix = f"""
    REALITY OVERRIDE ACTIVE: {scenario_text}

    Previous reality assumed: {summarize(original_graph)}
    This has now changed: {delta}

    Re-evaluate with this new information from scratch.
    """
    return updated_graph, god_view_prefix
```

**Preset scenarios (UI buttons):**
- "Amazon enters your market"
- "Recession hits — budgets cut 40%"
- "Competitor raises $50M Series B"
- "Regulation bans your core feature"
- "You pivot to B2B"
- "OpenAI builds this natively"
- "You go viral on TikTok overnight"

**Limit:** Max 3 God View runs per verdict (enforced on frontend + Cairo contract)

---

## 7. Smart Contract Architecture

### File: `contracts/verdict_registry.cairo`

```cairo
#[derive(Drop, Serde, starknet::Store)]
struct Verdict {
    // Identity
    founder: ContractAddress,
    idea_hash: felt252,
    timestamp: u64,

    // Knowledge graph (compressed)
    domain: felt252,
    market_stage: felt252,
    business_model: felt252,
    key_risks_hash: felt252,

    // Agent roster
    agents_spawned: Array<AgentId>,
    agent_count: u8,

    // Round scores
    r1_stances: Array<bool>,
    r1_scores: Array<u8>,
    r2_stances: Array<bool>,
    r2_scores: Array<u8>,
    stance_flips: u8,

    // Final verdict
    final_score: u8,
    pillar_scores: Array<u8>,     // [market, revenue, adoption, competition]
    consensus_level: u8,
    contested: bool,
    blocked: bool,

    // God View
    god_view_count: u8,           // max 3 — contract rejects > 3
    god_view_hashes: Array<felt252>,

    // Visibility
    is_public: bool,

    // Integrity
    proof_hash: felt252,
}

#[derive(Drop, Serde, starknet::Store)]
enum AgentId {
    MarketPulse,
    TrendSeeker,
    UnitEcon,
    RevenueScout,
    FirstClick,
    StickyLoop,
    RedTeam,
    MoatInspector,
    BuildCheck,
    PolicyScan,
    ViralEngine,
    SkepticalVC,
}
```

**Functions:**
```cairo
fn submit_verdict(ref self, verdict: Verdict)    // stores verdict, emits event
fn get_verdict(self, idea_hash: felt252) -> Verdict  // view, respects is_public
fn get_public_verdicts(self) -> Array<felt252>   // returns public idea_hashes
fn add_god_view(ref self, idea_hash: felt252, scenario_hash: felt252)  // max 3
```

**Events:**
```cairo
#[event]
enum Event {
    VerdictSubmitted: VerdictSubmitted,
    GodViewAdded: GodViewAdded,
}

struct VerdictSubmitted { founder: ContractAddress, idea_hash: felt252, final_score: u8, is_public: bool }
struct GodViewAdded { idea_hash: felt252, scenario_hash: felt252, god_view_count: u8 }
```

### On-Chain Publish Flow (frontend JS)
```javascript
// 1. Hash the pitch inputs
const idea_hash = starknet.hash.pedersen([name, problem, solution, market, model]);

// 2. Submit verdict via StarkZap wallet
const tx = await wallet.execute({
    contractAddress: VERDICT_REGISTRY_ADDRESS,
    entrypoint: "submit_verdict",
    calldata: [
        idea_hash, final_score,
        market_score, revenue_score, adoption_score, competition_score,
        agent_count, stance_flips, consensus_level,
        god_view_count, proof_hash,
        is_public ? 1 : 0
    ]
});
await tx.wait();

// 3. Display tx link
const starkscanUrl = `https://sepolia.starkscan.co/tx/${tx.transaction_hash}`;
```

---

## 8. StarkZap Integration

```javascript
// CDN approach (preferred)
import { StarkZap, OnboardStrategy } from "starkzap";

const sdk = new StarkZap({ network: "sepolia" });

// Social login
const { wallet } = await sdk.onboard({
    strategy: OnboardStrategy.Privy  // Google, email
});

// Fallback if CDN unavailable: minimal Express proxy
// POST /api/starkzap/onboard → returns wallet address
// POST /api/starkzap/execute → signs and submits tx
```

**Fallback chain:**
1. StarkZap CDN → social login
2. StarkZap Node.js proxy → social login
3. Simulated wallet → show "Powered by StarkZap" branding, tx is mocked

---

## 9. File Structure

```
starkagents/
├── frontend/
│   └── index.html          # single file dApp
├── backend/
│   ├── main.py             # FastAPI + WebSocket + OpenAI
│   ├── agents.py           # agent personas, behavioral logic
│   ├── graph_builder.py    # knowledge graph extraction
│   ├── env_config.py       # environment config agent
│   ├── scoring.py          # verdict computation
│   └── requirements.txt
├── contracts/
│   ├── src/
│   │   └── verdict_registry.cairo
│   └── Scarb.toml
├── docs/
│   └── architecture.md     # this file
└── .env                    # OPENAI_API_KEY
```

---

## 10. Implementation Slices

| Slice | What | Target |
|---|---|---|
| 1 | Switch backend to OpenAI (gpt-4o-mini), async parallel calls | 15 min |
| 2 | Knowledge Graph Builder + Environment Config Agent | 20 min |
| 3 | 2-round debate with R2 memory injection | 20 min |
| 4 | CSS bubble war room UI | 30 min |
| 5 | StarkZap social login + wallet | 30 min |
| 6 | Cairo contract deploy (Sepolia) | 20 min |
| 7 | On-chain verdict publish + Starkscan link | 20 min |
| 8 | God View delta injection (6 preset scenarios) | 20 min |
| 9 | Agent categories UI (home + war room) | 15 min |
| **Total** | | **~3.5 hrs** |

---

## 11. Budget

| Item | Cost |
|---|---|
| Graph Builder (1 call/simulation) | ~$0.0001 |
| Env Config Agent (1 call) | ~$0.0001 |
| Round 1: 5 agents × 1 call | ~$0.0007 |
| Round 2: 5 agents × 1 call | ~$0.0007 |
| God View (up to 3 × 5 agents × 1 call) | ~$0.002 |
| **Total per simulation (no God View)** | ~$0.002 |
| **Total per simulation (with 3 God Views)** | ~$0.004 |
| **$5 budget supports** | ~1,250–2,500 simulations |
