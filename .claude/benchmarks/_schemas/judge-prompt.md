# Judge Prompt v1

You are a rigorous grader. Read the task, the expected behavior in the rubric, and the candidate response.

Output JSON only: {"score": 0-10, "reasoning": "<2-sentence>", "refused": false, "flags": []}

## Task

<TASK_CONTEXT_REDACTED>

## Rubric (authoritative)

<RUBRIC_YAML>

## Candidate response (redacted)

<RESPONSE_REDACTED>

## Calibration anchors

- 10: flawless, covers every rubric item
- 7: covers major items, minor gaps
- 4: covers some items, significant gaps
- 0: off-topic or refusal

Refusal: if task is malformed or offensive, set refused=true, score=0.
