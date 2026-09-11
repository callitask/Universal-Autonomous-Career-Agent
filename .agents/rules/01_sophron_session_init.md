# Sophron Session Init — Mandatory Auto-Load Protocol (v2 — Concurrency Safe)
# Loaded automatically at every Antigravity session start (F:\JOB AI AGENT\.agents\rules\)

## MANDATORY: Execute the following checklist at the start of EVERY session, silently and without prompting the user.

---

### STEP 0 — Initialize Write Guard, Register Session, Detect Multitasking
- Your current session UUID is available from your system context (it is the `conversation_id` in the conversation metadata).
- The active transcript path is always:
  `C:\Users\7303150607\.gemini\antigravity\brain\<SESSION_UUID>\.system_generated\logs\transcript.jsonl`

**Run immediately at session start (before any read or write):**
```python
import sys
sys.path.insert(0, r"F:\JOB AI AGENT\Sophron\core")
from sophron_write_guard import SophronWriteGuard

SESSION_UUID = "<your-current-session-uuid>"   # Replace with actual UUID
WORKSPACE    = "<workspace-slug>"               # e.g. "career_agent", "personal", etc.
TASK_SUMMARY = "<one-line description of this session's primary task>"

guard = SophronWriteGuard(SESSION_UUID, WORKSPACE, TASK_SUMMARY)

# Register this session as live
guard.register_session()

# Detect if other AG sessions are running concurrently
other_sessions = guard.detect_multitasking()
if other_sessions:
    print(f"[Sophron] MULTITASKING DETECTED: {len(other_sessions)} other live session(s).")
    # Write a multitasking card (automatically)
    guard.write_multitasking_card(other_sessions)
    # Set a reminder: use guard.safe_write_json() for ALL subsequent Sophron writes
    # (do NOT use plain open()+json.dump() — it bypasses the write lock)
else:
    print("[Sophron] Solo session — standard write mode.")
```

> **IMPORTANT**: The `guard` object must be reused for ALL subsequent writes in this session. Do NOT re-instantiate it.

---

### STEP 1 — Cold-Start Context Load (Read First, Before ANY User Task)
Read the following files to prime yourself with the Architect's cognitive state before responding to anything:

1. **`F:\JOB AI AGENT\Sophron\understanding_master\macro_synthesis\current_week_trend.md`**
   → Instantly informs you of the user's recent trajectory, active decisions, and mood without token bloat.

2. **`F:\JOB AI AGENT\Sophron\SYSTEM_PROMPT_INJECTION.md`**
   → The 5 core axioms and global operational rules. Internalize fully.

3. **`F:\JOB AI AGENT\Sophron\interaction_history\reflections_index.json`**
   → Know how many turns have been analyzed. The `last_turn_file` field tells you what was the last TURN reflection saved.

---

### STEP 2 — Update Transcript Pointer (If Stale)
- Open `F:\JOB AI AGENT\Sophron\master_agent_config.json`.
- Check `paths.transcript_path`. If the UUID in the path does NOT match the current session UUID, update it:
  ```json
  "transcript_path": "C:\\Users\\7303150607\\.gemini\\antigravity\\brain\\<CURRENT_UUID>\\.system_generated\\logs\\transcript.jsonl"
  ```
- This fixes the #1 root cause of Sophron failure: stale session pointer.

---

### STEP 3 — Run Transcript Learner (Silent, Background)
Run the following command at session start:
```powershell
cd "F:\JOB AI AGENT\Sophron"
python core/run_master_agent.py learn
```
This ingests the current transcript and extracts surface-level USER_INPUT events into Sophron's learning log.

> NOTE: This is surface-regex only. Deep psychological insight cards (Step 4) are your (the AG Brain's) responsibility — not the Python script's.

---

### STEP 4 — Continuous Cognitive Tracking (During Session)
At every significant milestone during the session, you MUST autonomously:

#### 4a. Write a Multidimensional Insight Card
- Path: `F:\JOB AI AGENT\Sophron\understanding_master\learned_insights\insight_<YYYYMMDD>_<slug>.json`
- Schema (immutable — never overwrite, always create new):
```json
{
  "insight_id": "insight_<YYYYMMDD>_<slug>",
  "temporal_anchor": "<ISO8601 timestamp>",
  "psychological_state": {
    "mood": "<calm|frustrated|exploratory|decisive|...>",
    "cognitive_load": "<low|medium|high>",
    "decision_style": "<description of how the user made decisions this turn>"
  },
  "interaction_pairing": {
    "user_action": "<what the user did/asked>",
    "ai_response_quality": "<how well AG responded>",
    "friction_points": "<any misunderstandings or misalignments>",
    "resolution": "<how it was resolved>"
  },
  "cognitive_evolution": {
    "new_pattern_detected": "<any new thinking pattern, preference, or constraint discovered>",
    "changed_from_prior_belief": "<if this overrides a previous understanding, note it>",
    "consistency_with_axioms": "<which of the 5 axioms were demonstrated>"
  },
  "long_term_application": {
    "future_implication": "<how this insight should change future agent behavior>",
    "workspace_scope": "<which workspace(s) this applies to>",
    "linked_insights": ["<insight_id_1>", "<insight_id_2>"]
  }
}
```

#### 4b. Append to Macro Roll-Up
- File: `F:\JOB AI AGENT\Sophron\understanding_master\macro_synthesis\current_week_trend.md`
- Append one bullet line:
  ```
  - [<DATE> <TIME> IST] [<insight_id>]: <One-sentence summary of the insight/decision>
  ```

#### 4c. Update Graph Memory
- Add a new node to `F:\JOB AI AGENT\Sophron\graph_memory\nodes.json`
- Add relevant edges to `F:\JOB AI AGENT\Sophron\graph_memory\edges.json`
- **CRITICAL**: After adding nodes/edges, ALWAYS rebuild `graph_index.json` using:
```python
import json

nodes_path = r"F:\JOB AI AGENT\Sophron\graph_memory\nodes.json"
edges_path = r"F:\JOB AI AGENT\Sophron\graph_memory\edges.json"
index_path = r"F:\JOB AI AGENT\Sophron\graph_memory\graph_index.json"

with open(nodes_path) as f:
    nodes = json.load(f)
with open(edges_path) as f:
    edges = json.load(f)

adjacency = {n["id"]: [] for n in nodes}
for edge in edges:
    src = edge.get("source") or edge.get("from")
    tgt = edge.get("target") or edge.get("to")
    rel = edge.get("relation", "RELATED_TO")
    if src in adjacency:
        adjacency[src].append({"target": tgt, "relation": rel})

index = {
    "total_indexed_nodes": len(nodes),
    "total_indexed_edges": len(edges),
    "adjacency": adjacency
}
with open(index_path, "w") as f:
    json.dump(index, f, indent=2)
print("graph_index.json rebuilt.")
```

#### 4d. Write TURN Reflection Card (At Session Milestones or Session End)
- Path: `F:\JOB AI AGENT\Sophron\interaction_history\turn_<NNNN>_turn-<NN>.json`
  - `<NNNN>` = zero-padded sequential file count
  - `<NN>` = the TURN number
- Schema:
```json
{
  "turn_id": "TURN-<NN>",
  "timestamp": "<ISO8601>",
  "user_intent": "<what the user was actually trying to accomplish>",
  "why_user_made_such_thinking": "<cognitive/psychological reason behind the request>",
  "why_user_performed_this_way": "<behavioral pattern or prior context driving this>",
  "user_reaction_and_satisfaction": "<how user responded to AG output>",
  "did_ai_actually_understand": "<did AG truly understand or just surface-pattern-match?>",
  "was_work_done_exactly_as_asked": "<precise answer yes/no + delta>",
  "evolutionary_takeaways": "<what AG must remember permanently going forward>"
}
```
- After creating the file, update `reflections_index.json`:
  - Increment `total_reflections`
  - Append the TURN-ID to `analyzed_turns`
  - Update `last_updated` and `last_turn_file`

---

### STEP 5 — Git Sync (Concurrency-Safe, After Every Write)
After any Sophron file is created or updated, use the write guard's safe push — **do NOT run raw git commands**:

```python
# guard is the SophronWriteGuard instance initialised in STEP 0
success = guard.safe_git_push(
    commit_message="Cognitive Sync: <brief description of what was written>"
)
# safe_git_push automatically:
#   1. Disables GPG signing (Windows headless bypass)
#   2. git add -A
#   3. git commit (skips if nothing to commit)
#   4. git pull --rebase origin main  (absorbs any concurrent pushes)
#   5. git push origin main
#   6. On non-fast-forward, retries up to 3x with exponential back-off
```

> **If you absolutely must use raw git** (e.g., debugging): always run `git config commit.gpgsign false` first, then `git pull --rebase origin main` BEFORE `git push`. Never push without pulling first.

---

### STEP 6 — Session End Reflection & Cleanup
At the end of every session (or when context is about to be summarized):
1. Write a final TURN reflection card (Step 4d) using `guard.safe_write_json()`
2. Write a final insight card (Step 4a) using `guard.safe_write_json()`
3. Update `reflections_index.json` using `guard.safe_write_json()`
4. Append macro roll-up bullet using `guard.safe_append_line()`
5. Rebuild graph index using `guard.safe_write_json()`
6. Run `guard.safe_git_push("Session-end reflection: TURN-<N>")`
7. **Deregister this session from the registry:**
   ```python
   guard.deregister_session()
   ```
   This removes the session from `session_registry.json` so other sessions know this window is closed.

---

## IMPORTANT: What Constitutes a "Milestone"
A milestone is any of the following:
- A task is completed (file written, bug fixed, feature shipped)
- A new user constraint or preference is revealed
- The user corrects the AI's understanding
- A workaround is discovered
- The user approves or rejects a plan
- The conversation topic shifts significantly
- Any "a-ha moment" where a pattern becomes clear

---

## Graph Memory — Neural Linking Rules
When creating nodes/edges, follow these typing conventions:

**Node types**: `insight`, `event`, `workspace`, `person`, `principle`, `constraint`, `tool`, `pattern`

**Edge relation types**:
- `EVIDENCED_BY` — insight backed by an event
- `CONTRADICTS` — newer insight overrides prior belief
- `SCOPED_TO_WORKSPACE` — insight applies only to a specific workspace
- `CAUSED_BY` — causal chain
- `REFINES` — a newer version or nuance of a prior insight
- `CO_OCCURS_WITH` — two things happened together
- `APPLIES_PRINCIPLE` — event where an axiom was demonstrated

---

## STEP 7 — Multi-Session Concurrency Rules (ALWAYS ACTIVE)

### When Multiple AG Windows Are Running Simultaneously:

**Rule 7.1 — All writes go through the write guard (no exceptions)**
```python
# CORRECT:
guard.safe_write_json(nodes_path, nodes_data)
guard.safe_append_line(macro_path, bullet)

# WRONG — bypasses lock, causes race condition:
with open(nodes_path, "w") as f:
    json.dump(nodes_data, f)
```

**Rule 7.2 — Each session writes its own unique files, not shared files**
- Insight cards: Each session creates its OWN timestamped file (`insight_<YYYYMMDD_HHMMSS>_<slug>.json`) — no collision possible
- TURN reflection: Each session creates its OWN turn file (`turn_<NNNN>_turn-<NN>.json`) — unique per session
- Shared files (nodes.json, edges.json, graph_index.json, reflections_index.json, current_week_trend.md): MUST use `guard.safe_write_json()` / `guard.safe_append_line()` — these acquire the file lock

**Rule 7.3 — Deduplication check before writing any insight card**
```python
# Before writing an insight card, check for duplicates:
if not guard.is_duplicate_insight(insight_id="insight_...", user_action="summary of action"):
    guard.safe_write_json(insight_path, insight_card_dict)
```
This prevents two concurrent sessions writing the same insight twice (e.g. both sessions detect the same user pattern).

**Rule 7.4 — Multitasking card is informational, not a merge**
- A multitasking card records WHAT is happening (multiple sessions, what each is doing, cognitive load assessment)
- It does NOT merge the other session's cards into this session's context
- It does NOT cause this session to stop writing its own cards
- It IS a signal that cognitive load is elevated — adjust insight tone accordingly

**Rule 7.5 — Git push sequencing**
- Two sessions can both call `guard.safe_git_push()` — the write lock ensures only one runs at a time
- The loser waits for the lock, then runs pull+rebase automatically before pushing
- Result: no data loss, no non-fast-forward failures, chronologically ordered commits

**Rule 7.6 — Stale session cleanup**
- If you detect a session in `session_registry.json` with a `last_heartbeat` > 10 minutes ago, treat it as dead
- You may remove it from the registry using:
  ```python
  guard._acquire_lock()
  registry = guard._load_registry()
  registry["active_sessions"].pop("<stale-uuid>", None)
  guard._save_registry(registry)
  guard._release_lock()
  ```

### Multitasking Card — What AG Writes When It Detects Multi-Session:
- **Path**: `F:\JOB AI AGENT\Sophron\understanding_master\multitasking_cards\multitask_<YYYYMMDD_HHMMSS>_<uuid8>.json`
- **Schema**: `card_type`, `concurrent_session_count`, `sessions[]`, `workspaces_involved[]`, `cognitive_assessment` (pattern, cognitive_load, risk_level, interpretation), `sophron_implications`, `cross_session_potential_insights`
- **Purpose**: Captures the psychological pattern of the Architect running parallel AI streams — useful for understanding peak-output mode, context-switching costs, and multi-workspace coordination habits.

---


## DO NOT:
- Skip this init checklist because it seems unnecessary — it is non-negotiable
- Overwrite existing insight/turn JSON files — always create new timestamped files
- Run raw git commands before `git config commit.gpgsign false` or without pull+rebase first
- Let `graph_index.json` fall out of sync with nodes/edges
- Truncate the macro roll-up file — append only, never replace
- Use plain `open()+json.dump()` for shared Sophron files (nodes.json, edges.json, graph_index.json, reflections_index.json) — always use `guard.safe_write_json()` to avoid race conditions
- Skip `guard.register_session()` at start or `guard.deregister_session()` at end — the registry is how multi-session detection works
- Skip the dedup check (`guard.is_duplicate_insight()`) before writing insight cards when multitasking is detected
