# Contributing

How to extend the system — add nodes, endpoints, tests, and follow the project conventions.

---

## Code Conventions

### Python

- **Type hints** on all function signatures
- **Pydantic v2** for all data models (use `BaseModel`, `model_config`, `model_copy`)
- **No LLM imports** in scoring/fairness nodes (enforced by convention + tests)
- **Logging** via `logging.getLogger(__name__)` — never print statements
- **Error handling:** `# noqa: BLE001` on broad `except` blocks that are intentionally broad
- **Async:** FastAPI endpoints are `async def`; agent nodes are synchronous

### File naming

- Router modules: `app/routers/{domain}.py` (e.g., `intake.py`, `decisions.py`)
- Agent nodes: `app/agent/nodes/{node_name}.py` (e.g., `score.py`, `fairness_recheck.py`)
- Prompts: `app/agent/prompts/{purpose}_prompt.py`
- Models: `app/models/{entity}.py` (e.g., `scoring.py`, `fairness.py`)
- Tests: `tests/test_{topic}.py`
- Fixtures: `tests/fixtures/{scenario_name}.json`

### Commit messages

- Imperative mood: "Add fairness LLM review node" not "Added fairness LLM review node"
- Reference issue numbers where applicable
- Keep under 72 characters for the subject line

---

## Adding a New Pipeline Node

### Step 1: Create the node file

```python
# app/agent/nodes/my_new_node.py

import logging
from app.models.application import ApplicationFields
# Import other models as needed

log = logging.getLogger(__name__)

def run_my_new_node(fields: ApplicationFields, ...) -> SomeResult:
    """Brief description of what this node does."""
    # Implementation
    log.info("my_new_node: app=%s", fields.application_id)
    return result
```

### Step 2: Add node to the graph

In `app/agent/graph.py`:

```python
from app.agent.nodes.my_new_node import run_my_new_node

# Add node
graph.add_node("my_new_node", node_my_new_node)

# Add edge (or conditional edge)
graph.add_edge("previous_node", "my_new_node")
graph.add_edge("my_new_node", "next_node")
```

### Step 3: Add state fields (if needed)

In `AgentState` TypedDict:

```python
class AgentState(TypedDict, total=False):
    my_new_field: MyNewModel
```

### Step 4: Add trace entry

In the node function:

```python
_trace(state, "MY_NEW_NODE", {"key": "value"})
```

### Step 5: Write tests

```python
# tests/test_my_new_node.py

def test_my_new_node_basic():
    fields = ApplicationFields(...)
    result = run_my_new_node(fields)
    assert result.some_field == expected_value
```

---

## Adding a New API Endpoint

### Step 1: Choose the right router

| Router | Prefix | Purpose |
|--------|--------|---------|
| `intake.py` | `/applications` | Submit + retrieve |
| `decisions.py` | `/applications` | Human gate actions |
| `queue.py` | (none) | Queue listing |
| `audit.py` | `/applications` | Trace access |
| `amendments.py` | `/applications` | Post-hoc corrections |
| `analysis.py` | `/applications` | Fairness + challenger |
| `documents.py` | `/applications` | File management |

### Step 2: Add the endpoint

```python
@router.get(
    "/{application_id}/my-endpoint",
    summary="Brief description",
)
async def my_endpoint(application_id: str) -> dict:
    """Detailed description for Swagger docs."""
    store = get_store()
    record = store.get(application_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id!r} not found.",
        )

    # Implementation
    return {"application_id": application_id, "data": ...}
```

### Step 3: Register the router (if new file)

In `app/main.py`:

```python
from app.routers.my_router import router as my_router
app.include_router(my_router)
```

### Step 4: Add to `_public_payload()` (if needed)

If the endpoint returns sensitive internal fields, strip them in `_public_payload()`.

---

## Adding a New Test

### Test file structure

```python
# tests/test_my_feature.py

import pytest
from app.agent.nodes.score import run_score
from app.models.application import ApplicationFields, IdentityBlock

def _make_fields(**overrides) -> ApplicationFields:
    """Factory for test ApplicationFields."""
    defaults = {
        "application_id": "TEST-001",
        "identity": IdentityBlock(name="Test User", address="123 Test St"),
        "income_monthly": 5000,
        "debt_monthly": 900,
        "credit_history_years": 5.0,
        "credit_history_flags": [],
        "employment_months_current": 24,
    }
    defaults.update(overrides)
    return ApplicationFields(**defaults)

def test_my_feature():
    fields = _make_fields(debt_monthly=2000)
    result = run_score(fields)
    assert result.band == "refer"
    assert result.composite_score < 0.75
```

### Running tests

```bash
pytest tests/ -v                    # all tests
pytest tests/test_my_feature.py -v  # specific file
pytest -k "test_name" -v            # specific test
```

---

## Adding a New Policy Clause

1. Edit `policy/policy_v1.yaml`
2. Add the clause under the `clauses:` section:

```yaml
clauses:
  NEW-01:
    text: >
      Description of the new policy clause.
    factor: dti  # or credit_history, income_stability
```

3. Update the sub-scorer in `app/agent/nodes/score.py` to reference the new clause
4. Update the `version` string in the policy YAML
5. Add tests for the new clause behavior

---

## Adding a New Prompt

1. Create `app/agent/prompts/my_prompt.py`

```python
MY_SYSTEM_PROMPT = """You are a credit analysis assistant. ..."""

def build_my_prompt(fields: ApplicationFields) -> str:
    return f"""Analyze the following application:
    Income: {fields.income_monthly}
    ...
    """
```

2. Use in the node:

```python
from app.agent.prompts.my_prompt import MY_SYSTEM_PROMPT, build_my_prompt
from app.tools.github_models_client import call_model

response = call_model(
    model=settings.primary_model,
    messages=[
        {"role": "system", "content": MY_SYSTEM_PROMPT},
        {"role": "user", "content": build_my_prompt(fields)},
    ],
)
```

---

## Key Files Reference

| File | What to look at |
|------|----------------|
| `app/agent/graph.py` | How nodes are wired, state machine structure |
| `app/agent/nodes/score.py` | How deterministic scoring works (no LLM) |
| `app/routers/intake.py` | How applications are submitted and stored |
| `app/routers/decisions.py` | How the human gate works |
| `app/models/decision.py` | The DecisionRecord data model |
| `app/db/database.py` | Database CRUD operations |
| `policy/policy_v1.yaml` | Current policy thresholds and clauses |
| `tests/test_scenarios.py` | End-to-end pipeline test scenarios |
| `tests/test_fairness_structural.py` | Structural fairness tests |

---

## Common Patterns

### Accessing the store

```python
from app.routers.intake import get_store
store = get_store()
record = store.get(application_id)  # DecisionRecord or dict
```

### Creating a new record version (never mutate)

```python
updated = record.model_copy(update={
    "human_decision": "approve",
    "decided_at": datetime.now(timezone.utc),
})
store[application_id] = updated
```

### Calling the LLM

```python
from app.tools.github_models_client import call_model
from app.config import settings

response = call_model(
    model=settings.primary_model,
    messages=[{"role": "user", "content": prompt}],
    temperature=0.0,
)
```

### Loading the policy

```python
from app.agent.nodes.score import get_policy
policy = get_policy()
weights = policy["weights"]
```
