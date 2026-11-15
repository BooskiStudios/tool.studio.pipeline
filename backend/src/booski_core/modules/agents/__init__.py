"""Agents (PR 3.4): agent definitions as per-workspace configurations, and agent runs executed by the
``booski agent-worker`` process.

Agents are configurations on shared orchestration, not separate AI systems (D-P3-3). In PR 3.4 they can
plan, review and draft, but they have no tools: they never change studio records. Every finished run
raises an "AI output" approval, and people apply what they approve (D49).
"""
