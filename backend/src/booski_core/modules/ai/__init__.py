"""AI Core foundation (PR 3.2): providers, the model catalogue, task routing, the AI gateway, usage and
cost tracking, and per-workspace AI settings.

Every AI request goes through ``gateway.complete``. Nothing in this package runs agents, stores memory or
executes tools; those are later milestones.
"""
