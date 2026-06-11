# AETHON — Documentation

> Self-hosted, provider-agnostic personal AI assistant — multi-channel, multi-agent, full control. Bring your own model provider.

---

## Document Structure

### Product Documents (`product/`)

| Document | Description |
|----------|-------------|
| [PRODUCT.md](product/PRODUCT.md) | Product overview, features, architecture |
| [GETTING-STARTED.md](product/GETTING-STARTED.md) | Installation and quick start guide |
| [CONFIGURATION.md](product/CONFIGURATION.md) | Complete configuration reference |
| [CAPABILITIES.md](CAPABILITIES.md) | 0.2.0 capabilities — tools, macOS, LSP, dynamic tools, ambient, recording, MCP server |
| [API-REFERENCE.md](product/API-REFERENCE.md) | HTTP endpoints, WebSocket, webhook, tool reference |
| [ARCHITECTURE.md](product/ARCHITECTURE.md) | Technical architecture, data flows, component relationships |

### Development Documents (`development/`)

| Document | Description |
|----------|-------------|
| [PHASE-1-CORE.md](development/PHASE-1-CORE.md) | Phase 1 — Core infrastructure design document |
| [PHASE-2-CHANNELS.md](development/PHASE-2-CHANNELS.md) | Phase 2 — Channel integrations design |
| [PHASE-3-MULTIAGENT.md](development/PHASE-3-MULTIAGENT.md) | Phase 3 — Multi-agent orchestration design |
| [PHASE-4-POLISH.md](development/PHASE-4-POLISH.md) | Phase 4 — Polish and advanced features design |
| [PHASE-5-DASHBOARD.md](development/PHASE-5-DASHBOARD.md) | Phase 5 — Dashboard & UX Revolution design |
| [PHASE-6-INFRASTRUCTURE.md](development/PHASE-6-INFRASTRUCTURE.md) | Phase 6 — Infrastructure Strengthening design |
| [PHASE-7-INTELLIGENCE.md](development/PHASE-7-INTELLIGENCE.md) | Phase 7 — AI Capabilities Expansion design |
| [PHASE-8-RELIABILITY.md](development/PHASE-8-RELIABILITY.md) | Phase 8 — Reliability Hardening (autonomous-engineer trustworthiness; from the hermes-strands audit) |
| [ROADMAP.md](development/ROADMAP.md) | Project roadmap (Phase 1-7) |
| [SECURITY.md](development/SECURITY.md) | Security model and threat analysis |

### Checklists (`checklists/`)

| Document | Description |
|----------|-------------|
| [PHASE-1-CHECKLIST.md](checklists/PHASE-1-CHECKLIST.md) | Phase 1 completion checklist |
| [PHASE-2-CHECKLIST.md](checklists/PHASE-2-CHECKLIST.md) | Phase 2 completion checklist |
| [PHASE-3-CHECKLIST.md](checklists/PHASE-3-CHECKLIST.md) | Phase 3 completion checklist |
| [PHASE-4-CHECKLIST.md](checklists/PHASE-4-CHECKLIST.md) | Phase 4 completion checklist |
| [PHASE-5-CHECKLIST.md](checklists/PHASE-5-CHECKLIST.md) | Phase 5 completion checklist (76 items) |
| [PHASE-6-CHECKLIST.md](checklists/PHASE-6-CHECKLIST.md) | Phase 6 completion checklist (54 items) |
| [PHASE-7-CHECKLIST.md](checklists/PHASE-7-CHECKLIST.md) | Phase 7 completion checklist (53 items) |
| [PHASE-8-CHECKLIST.md](checklists/PHASE-8-CHECKLIST.md) | Phase 8 reliability checklist (R1-R18, 4 sprints) |

### References (`references/`)

| Document | Description |
|----------|-------------|
| [strands-agents-reference.md](references/strands-agents-reference.md) | Strands Agents SDK API reference |

---

## Quick Access

**New users:** Start with the [Getting Started Guide](product/GETTING-STARTED.md).

**Configuration:** All settings are documented in the [Configuration Reference](product/CONFIGURATION.md).

**API integration:** All endpoints, webhooks, and tools are documented in the [API Reference](product/API-REFERENCE.md).

**Technical details:** The [Architecture Document](product/ARCHITECTURE.md) describes the layered architecture, data flows, and component relationships.

---

## Project Status

| Phase | Status | Tests | Checklist |
|-------|--------|-------|-----------|
| Phase 1 — Core Runtime | ✅ Completed | 64 tests | 37 items |
| Phase 2 — Channels + Memory | ✅ Completed | 120 tests | 42 items |
| Phase 3 — Multi-Agent + SOP | ✅ Completed | 178 tests | 38 items |
| Phase 4 — Polish + Advanced | ✅ Completed | 294 tests | 48 items |
| Phase 5 — Dashboard & UX | ✅ Completed | 348 tests | 76 items |
| Phase 6 — Infrastructure | ✅ v1 slice (Docker + CI + packaging + dashboard auth) | 421 tests | 54 items |
| Phase 7 — AI Capabilities | ✅ Shipped in 0.2.0 (see [CAPABILITIES.md](CAPABILITIES.md)) | 421 tests | 53 items |
| Phase 8 — Reliability Hardening | ✅ Implemented ([PHASE-8](development/PHASE-8-RELIABILITY.md)) | 616 tests | R1-R18 + 2 review rounds |

**Completed:** 616 tests, all passing.

**0.2.0** added the capability tools, macOS integration, LSP, dynamic tool loading,
ambient mode, session recording/replay, the MCP server, and system-prompt awareness —
see [CAPABILITIES.md](CAPABILITIES.md).

**Still deferred:** response streaming, team/pipeline (Swarm/Graph) orchestration wired
into the runtime, per-specialist multi-model config, and real-time voice.
