# Knowledge-scope study data

Original fiction written for this project, used by `research/cs3235_paper/experiments/knowledge_scope.py`. Two worlds, three roles each. Every role has one knowledge file holding only what that role could plausibly know.

`study.json` fixes personas, marker phrases and queries before any run. A role's topic marker is the phrase showing that its own answer reached the prompt. A role's `restricted_markers` belong to higher-standing roles and must never reach its prompt. Labels are author-assigned, not independently adjudicated.
