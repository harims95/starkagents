# StarkAgents — Swarm Intelligence on StarkNet

> Throw your startup at 500 AI agents. One brutal verdict. Sealed on-chain. Forever.

**Live →** [starkagents.vercel.app](https://starkagents.vercel.app)

---

## What It Does

You submit your startup pitch. A swarm of AI agents — each with a distinct role, bias, and codename — tears it apart across 4 pillars and 2 debate rounds. The final verdict is cryptographically published to StarkNet Sepolia. No spin. No fluff. Verifiable by anyone, forever.

---

## The Agents

| Codename | Role | Specialty |
|----------|------|-----------|
| **VEGA** | Market Demand Analyst | Timing windows, saturation signals |
| **KIRA** | Unit Economics Analyst | CAC, LTV, payback period |
| **BLADE** | Competitor Simulator | Plays your top 3 competitors |
| **WARD** | Regulatory Risk Analyst | GDPR, sector rules, licensing traps |
| **FLUX** | Growth Hacker | Viral loops, k-factor, channel fit |
| **FANG** | VC Devil's Advocate | Series A partner stress-test |

6 active agents in demo. 400+ defined in the roster.

---

## The Flow

```
Connect Wallet (Argent X)
       ↓
Submit Pitch (name, problem, solution, market, model)
       ↓
War Room — Live Bubblemaps-style agent network
  • RPM gauge tracks swarm intensity
  • Agents debate in real-time (2 rounds, 4 pillars)
  • Speech pops show live reasoning
  • Stance flips visible on-screen
       ↓
Verdict — Score /100 with pillar breakdown
  • RPM gauge locked at final score
  • God View: 3 what-if re-simulations
       ↓
StarkNet — Verdict published on-chain
  • Transaction hash linked via Starkscan
```

---

## Debate Pillars

- **Market Demand & Timing** — Is the market ready?
- **Revenue & Business Model** — Does the money math work?
- **User Adoption & Retention** — Will users come back?
- **Competitive Survival** — Can you survive 90 days vs. incumbents?

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Single HTML file — DM Sans + JetBrains Mono, no framework |
| Backend | FastAPI + OpenAI `gpt-4o-mini`, WebSocket streaming |
| Contract | Cairo 1.0 — `VerdictRegistry` on StarkNet Sepolia |
| Wallet | Argent X via `starknet.js` injected provider |
| Deploy | Vercel (frontend) + Railway (backend) |

---

## Smart Contract

- **Network:** StarkNet Sepolia
- **Address:** `0x028c860e92e39b86ca995d56b30615c357274790204deeae7598c887d455754c`
- **Class Hash:** `0x048703d1102acd53868c7e757ccc71e15bf99563d7af5ebb386d46c4a5ed4e51`
- **Explorer:** [Starkscan](https://sepolia.starkscan.co/contract/0x028c860e92e39b86ca995d56b30615c357274790204deeae7598c887d455754c)

---

## Live URLs

| Service | URL |
|---------|-----|
| Frontend | https://starkagents.vercel.app |
| Backend API | https://starkagents-production.up.railway.app |
| WebSocket | wss://starkagents-production.up.railway.app |

---

## Local Dev

```bash
# Frontend — just open the file
open frontend/index.html

# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Set `OPENAI_API_KEY` in your backend environment.

---

## God View

After receiving a verdict, you get **3 re-simulation slots**. Inject a scenario — *"Amazon enters your market"*, *"You pivot to B2B"* — and the full swarm re-evaluates from scratch under those conditions. Delta score shown vs. original.

---

## Built at

ETHGlobal Hackathon → continuing as a real product.

*Swarm intelligence. Immutable verdicts. No mercy.*
