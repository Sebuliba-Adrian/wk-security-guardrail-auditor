# /vision-check — Verify current work aligns with VISION.md

Read VISION.md and evaluate the current state of the project against every success criterion.

For each of the 7 success criteria, report:
- Status: DONE / IN PROGRESS / NOT STARTED
- Evidence: which files, tests, or endpoints satisfy it
- Gap: what remains if not fully done

Then check the 6 non-goals — confirm nothing in the current codebase violates them.

Finally, flag any architectural drift: does the current implementation match ARCHITECTURE.md?
Check the API surface, DB schema, and project structure.

Output a concise table. If drift is detected, recommend the corrective action.
Run this check every 5 turns to prevent scope creep and stay on course.
