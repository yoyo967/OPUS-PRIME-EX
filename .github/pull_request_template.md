# Pull Request

## Summary
What does this change and why?

## Type
- [ ] feat
- [ ] fix
- [ ] docs
- [ ] spec (changes frozen specification — see below)
- [ ] test / chore

## Checklist
- [ ] `ruff check .` passes
- [ ] `mypy` passes (strict)
- [ ] `pytest -q` passes
- [ ] `python scripts/spec_lint.py` passes
- [ ] Added/updated tests for new behaviour
- [ ] No secrets committed (`.env` stays local)

## Legal / determinism (if applicable)
- [ ] Legal parameters live in versioned tables, not hardcoded
- [ ] The LLM does not compute or invent citations in this change
- [ ] Filing/reserved-service actions remain blocked
- [ ] I verified any new legal source/parameter against the primary source (name it):

## Spec impact (if this is a `spec` change)
- Section(s) touched:
- Version bump + gatekeeper note in `review/gate_report.md`:
- Prompt hash updated in `spec/spec_hashes.json` (if the prompt changed):
