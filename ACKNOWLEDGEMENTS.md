# Acknowledgements

## Claude Code Game Studios

Booski's AI workforce design draws on ideas from [Claude Code Game Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) by Donchitos, released under the MIT licence (Copyright (c) 2026 Donchitos). The PR3.1 audit ([docs/audits/PR3.1-CCGS-AUDIT.md](docs/audits/PR3.1-CCGS-AUDIT.md)) records what was reviewed, pinned to commit `abc0de7`.

Ideas used so far, rewritten in Booski's own words and code:

| Booski feature | Milestone | Idea from Claude Code Game Studios |
|---|---|---|
| AI model tiers (`routine`, `standard`, `deep`) chosen by the kind of task | PR3.2 | Assigning model tiers by task complexity: the cheapest adequate model for routine work, the most capable for multi-document synthesis and high-stakes review |
| Agents as configurations with responsibilities, "must not" rules and delegation maps; the starter roles (Producer, Technical Director, Game Designer, QA Lead) | PR3.4 | The agent roster, its tiered hierarchy and each agent's delegation map and limits; the collaboration protocol (agents propose, people decide) |

No Claude Code Game Studios text or code has been copied into this repository. If any is reused in future, it will be listed in a `THIRD_PARTY_NOTICES.md` file with the full MIT licence text, its source path and the pinned commit (D28).
