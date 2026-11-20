"""Tools agents can use (PR 3.5).

* **Read** tools look things up, with the permissions of the person who started the run.
* **Propose** tools stage a change (create a document, tasks or a decision). Nothing is written until a
  person approves the run's review; then every proposed change is applied, or none (D57).

There is deliberately no tool that edits, deletes, archives, assigns people, publishes, or reaches outside
Booski (D-P3-6). ``registry.FORBIDDEN_ACTIONS`` lists what no tool may be named for, and a test checks it.
"""
