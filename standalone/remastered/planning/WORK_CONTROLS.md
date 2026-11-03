# Work controls that stay put

Status: integrated into canonical source and the fourth app; packaged Human startup/save/reload verification passed at03:24 Eastern.

The Work tab recreated all role and recipe buttons whenever settlement data changed. A worker changing from Mining to Delivering, a queue update, or a changed stockpile could remove a button between pointer press and release or drop keyboard focus. The before browser report reproduces the lost click at 320, 390 and 768 pixel widths.

The candidate keeps role and recipe buttons keyed by the original command plus the sorted selected-unit references. Ordinary status updates reuse the same elements; a changed selection replaces them so releasing a held tap does not issue an action to a different worker. Disabled or removed recipes move focus to the production heading. Empty selection disables role assignment with a visible reason, and the selected role is marked. The hint explicitly says assigning a role replaces current tasks. These changes do not alter game commands, costs, queues or server authority.

- Focused browser checks: 9/33 before, 33/33 after. Actual browser pointer down/update/up and keyboard input are used; captured request counts verify one dispatch for surviving clicks.
- Combined responsive HUD checks: 253/253 with the mining-filter predecessor included; no browser errors.
- Selection replacement protects held DOM interactions. No new request protocol or stronger network race guarantee is claimed. Native WebKit acceptance passes29 checks, including a real tree→Carpentry→bucket→spike→spade sequence. Its held-pointer diagnostics are synthetic DOM events; physical touch remains a separate scope.

Evidence is in `reference/work-controls/`. The increment includes the Mining supplies predecessor. The fourth combined source passes253 responsive HUD and33 held-control checks; exact current build status is in OVERNIGHT_2026-10-17.md.
