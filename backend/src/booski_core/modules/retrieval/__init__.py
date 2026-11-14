"""Permission-aware retrieval (PR 3.3): full-text search across memory entries, knowledge documents and the
Decision Log, and assembly of AI context within a token budget.

PostgreSQL full-text search only (D-P3-5): no embeddings, vector database or extra service. Every query is
scoped exactly like the records' own endpoints, so nobody can retrieve what they couldn't open.
"""
