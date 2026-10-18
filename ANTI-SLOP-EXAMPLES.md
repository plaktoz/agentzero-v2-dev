# Anti-Slop Examples from PRDs

## Issue #184: CAVEMAN AND UNSLOP

This document shows specific slop patterns found in both PRDs with before/after examples.

---

## Examples from Development PRD

### Example 1: Executive Summary Opening

**BEFORE (Slop):**
```markdown
This PRD defines a unified multi-agent development system designed to address 
the fundamental challenges of AI-assisted software development at scale. The 
system combines distributed coordination, structured workflows, radical 
minimalism, and engineering fundamentals into a cohesive platform.
```

**AFTER (Anti-Slop):**
```markdown
This multi-agent system coordinates 20-30+ AI agents for software development. 
Reduces code by 53%, cost by 26%, time by 41%. Persists context across crashes. 
Works with Anthropic, OpenAI, Google.
```

**Changes:**
- Removed "designed to address the fundamental challenges"
- Replaced vague "at scale" with concrete "20-30+ agents"
- Added specific metrics (53%, 26%, 41%)
- Removed "cohesive platform" (generic)
- Added concrete capabilities

---

### Example 2: Problem Statement

**BEFORE (Slop):**
```markdown
Current AI-assisted development faces several challenges:
- **Context Loss**: Agents lose state on restart, making multi-agent workflows fragile
- **Over-Engineering**: Agents write more code than necessary, increasing maintenance burden
```

**AFTER (Anti-Slop):**
```markdown
Current AI-assisted development problems:
- **Context Loss**: Agent crashes lose hours of work
- **Over-Engineering**: Agents write 2-3x more code than needed
```

**Changes:**
- "faces several challenges" → "problems" (direct)
- "making multi-agent workflows fragile" → "lose hours of work" (concrete impact)
- "write more code than necessary" → "write 2-3x more code" (specific metric)
- "increasing maintenance burden" → removed (implied by 2-3x)

---

### Example 3: Vision Statement

**BEFORE (Slop):**
```markdown
**Build a multi-agent development system that:**
- Scales reliably to 20-30+ concurrent agents
- Persists context across crashes and restarts
- Produces minimal, high-quality code through systematic verification
- Keeps humans in control at critical decision points
- Works across multiple AI runtimes and platforms
- Measures and optimizes for real impact: code size, cost, time, and quality
```

**AFTER (Anti-Slop):**
```markdown
**System Goals:**
- 20-30+ concurrent agents
- Context survives crashes
- Minimal code via systematic verification
- Human approval at critical points
- Multi-runtime support (Anthropic, OpenAI, Google)
- Track: code size, cost, time, quality
```

**Changes:**
- "Build a multi-agent development system that:" → "System Goals:" (direct)
- "Scales reliably to" → removed (implied)
- "Persists context across crashes and restarts" → "Context survives crashes" (concise)
- "Produces minimal, high-quality code through" → "Minimal code via" (shorter)
- "Keeps humans in control at" → "Human approval at" (direct)
- "Works across multiple AI runtimes and platforms" → "Multi-runtime support" + examples
- "Measures and optimizes for real impact:" → "Track:" (direct)

---

### Example 4: "Why This Matters" Sections

**BEFORE (Slop):**
```markdown
**Why This Matters:**
Traditional AI agents lose all context when they crash or restart. This makes 
multi-agent workflows fragile - a single crash can lose hours of work. Version 
control worktrees solve this by treating agent state as version-controlled data.
```

**AFTER (Anti-Slop):**
```markdown
**Problem:**
Agent crashes lose hours of work.

**Solution:**
Version control worktrees persist agent state. Crashes recover from last commit.
```

**Changes:**
- "Why This Matters:" → "Problem:" / "Solution:" (clearer structure)
- Removed "Traditional AI agents" (obvious context)
- "This makes multi-agent workflows fragile" → removed (redundant)
- Split into problem/solution format (clearer)
- "treating agent state as version-controlled data" → "persist agent state" (simpler)

---

### Example 5: "How It Works" Sections

**BEFORE (Slop):**
```markdown
**How It Works:**
An agent's "hook" is a version control worktree - a separate working directory 
linked to the main repository. When an agent works, it commits state changes to 
its hook. If the agent crashes, a new session can resume from the last committed 
state. The hook IS the assignment - if work is hooked, it executes immediately 
without confirmation.
```

**AFTER (Anti-Slop):**
```markdown
**Implementation:**
Hook = version control worktree (separate directory linked to main repo)

Agent workflow:
1. Work on task
2. Commit state to hook
3. If crash → new session resumes from last commit

Rule: Hooked work executes immediately (no confirmation)
```

**Changes:**
- "How It Works:" → "Implementation:" (more precise)
- Converted paragraph to structured list
- "The hook IS the assignment" → "Rule:" (clearer emphasis)
- Removed redundant explanations

---

## Examples from Non-Development PRD

### Example 6: Executive Summary

**BEFORE (Slop):**
```markdown
This PRD defines a unified multi-agent system for **non-development work** - 
content creation, research, data analysis, operations, and other knowledge work. 
While the companion development PRD focuses on code, this system addresses the 
broader challenge of coordinating AI agents for general knowledge work at scale.
```

**AFTER (Anti-Slop):**
```markdown
This multi-agent system handles non-development work: content creation, research, 
data analysis, operations. Coordinates 20-30+ agents for knowledge work.

Companion to: Development PRD (focuses on code)
```

**Changes:**
- Removed "defines a unified multi-agent system for"
- "broader challenge of coordinating AI agents for general knowledge work at scale" → "Coordinates 20-30+ agents for knowledge work" (concrete)
- Split companion reference to separate line

---

### Example 7: Problem Statement

**BEFORE (Slop):**
```markdown
### What Problem Does This Solve?

Current AI-assisted knowledge work faces challenges:
- **Context Loss**: Agents lose research context on restart
- **Coordination Chaos**: Multiple agents working on related content without alignment
```

**AFTER (Anti-Slop):**
```markdown
### Problems Solved

Current AI knowledge work issues:
- **Context Loss**: Restart loses research
- **Coordination Chaos**: Agents duplicate work, conflict
```

**Changes:**
- "What Problem Does This Solve?" → "Problems Solved" (direct)
- "faces challenges:" → "issues:" (simpler)
- "Agents lose research context on restart" → "Restart loses research" (concise)
- "Multiple agents working on related content without alignment" → "Agents duplicate work, conflict" (specific)

---

### Example 8: Vision Statement

**BEFORE (Slop):**
```markdown
**Build a multi-agent system for knowledge work that:**
- Scales reliably to 20-30+ concurrent agents
- Persists research and context across crashes
- Produces high-quality content through systematic review
- Maintains consistent voice and style across agents
- Keeps humans in control at critical decision points
- Works across multiple content types and domains
```

**AFTER (Anti-Slop):**
```markdown
**System Goals:**
- 20-30+ concurrent agents
- Research survives crashes
- Quality via systematic review
- Consistent voice across agents
- Human approval at critical points
- Multi-domain: research, blog posts, docs, marketing, data analysis
```

**Changes:**
- Same pattern as dev PRD
- Added concrete examples of domains

---

## Caveman Approach Examples

### Example 9: Extreme Conciseness

**BEFORE (Standard Anti-Slop):**
```markdown
**Problem:**
Agent crashes lose hours of work.

**Solution:**
Version control worktrees persist agent state. Crashes recover from last commit.
```

**AFTER (Caveman):**
```markdown
**Problem:** Crash = lost work

**Solution:** Worktree persists state. Recover from last commit.
```

**Token Savings:** ~30%
**Readability Impact:** Still clear, but more terse

---

### Example 10: Requirements Section

**BEFORE (Standard Anti-Slop):**
```markdown
**Requirements:**
- Each agent gets a version control worktree (hook) for persistent state
- Work state survives crashes and restarts
- Version-controlled history with rollback capability
- Separation of agent identity (persistent) from sessions (ephemeral)
```

**AFTER (Caveman):**
```markdown
**Requirements:**
- Agent → worktree (hook) for state
- State survives crashes
- Version history + rollback
- Identity (persistent) ≠ sessions (ephemeral)
```

**Token Savings:** ~40%
**Readability Impact:** Requires more focus, but still understandable

---

## Recommendations

### Option 1: Anti-Slop Only (Recommended for PRDs)
- Remove AI patterns
- Keep clarity and readability
- ~20-30% token reduction
- **Best for human-readable documents**

### Option 2: Anti-Slop + Moderate Caveman
- Remove AI patterns
- Moderate conciseness (lists, shorter sentences)
- ~40-50% token reduction
- **Balance between tokens and readability**

### Option 3: Anti-Slop + Aggressive Caveman
- Remove AI patterns
- Maximum conciseness (symbols, abbreviations)
- ~60-70% token reduction
- **Best for token efficiency, harder to read**

---

## Specific Slop Patterns Found in PRDs

### Forbidden Phrases Found:
1. ❌ "designed to address the fundamental challenges"
2. ❌ "at scale" (without specific numbers)
3. ❌ "cohesive platform"
4. ❌ "faces several challenges"
5. ❌ "making workflows fragile"
6. ❌ "increasing maintenance burden"
7. ❌ "broader challenge of coordinating"
8. ❌ "general knowledge work at scale"

### Generic Patterns Found:
1. ❌ Long "Why This Matters" explanations
2. ❌ Verbose "How It Works" paragraphs
3. ❌ Vague problem statements without metrics
4. ❌ "Build a system that..." (could apply to any system)
5. ❌ Repetitive section structures

### What to Keep:
1. ✅ Concrete metrics (53%, 26%, 41%, 20-30+ agents)
2. ✅ Specific examples (FastAPI, JWT, bcrypt)
3. ✅ Code snippets and diagrams
4. ✅ Technical details and implementation notes
5. ✅ Decision rationale and trade-offs

---

## Next Steps

**Choose approach:**
1. Show more examples?
2. Apply Option 1 (Anti-Slop Only)?
3. Apply Option 2 (Anti-Slop + Moderate Caveman)?
4. Apply Option 3 (Anti-Slop + Aggressive Caveman)?
5. Create separate concise versions?
