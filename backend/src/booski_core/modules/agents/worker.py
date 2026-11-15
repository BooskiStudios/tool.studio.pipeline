"""The agent worker (``booski agent-worker``): claims queued runs from PostgreSQL and runs them (D46).

Claiming uses ``FOR UPDATE SKIP LOCKED`` and a time-limited lease, so several workers can run side by side
and a run whose worker crashed is picked up again once its lease expires; it continues from its last
completed step. No message broker is needed (D-P3-2, as D15 planned for the Local Worker).
"""

import logging
import socket
import time
import uuid
from collections.abc import Mapping

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from booski_core.modules.agents.models import AgentRun
from booski_core.modules.agents.orchestrator import LEASE, Orchestrator, Sleep, add_event
from booski_core.modules.ai.providers.base import AiProvider

logger = logging.getLogger("booski_core.agents")

MAX_ATTEMPTS = 3  # claims per run: a run that keeps crashing its worker is failed, not retried forever

_CLAIM = text(
    """
    UPDATE agent_runs
    SET status = 'running',
        lease_owner = :worker,
        lease_expires_at = now() + make_interval(secs => :lease_seconds),
        attempts = attempts + 1,
        started_at = coalesce(started_at, now()),
        updated_at = now(),
        version = version + 1
    WHERE id = (
        SELECT id FROM agent_runs
        WHERE status = 'queued' OR (status = 'running' AND lease_expires_at < now())
        ORDER BY created_at
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    RETURNING id, attempts
    """
)


def worker_name() -> str:
    return f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"


def claim(session_factory: sessionmaker[Session], worker: str) -> uuid.UUID | None:
    """Claims the oldest queued run (or one whose worker's lease expired). None if there is nothing to do."""
    with session_factory() as db:
        row = db.execute(_CLAIM, {"worker": worker, "lease_seconds": LEASE.total_seconds()}).one_or_none()
        if row is None:
            db.commit()
            return None
        run_id, attempts = row
        run = db.get(AgentRun, run_id)
        if run is None:  # pragma: no cover - claimed just now in the same transaction
            return None
        if attempts > MAX_ATTEMPTS:
            run.status = "failed"
            run.error_code = "too_many_attempts"
            run.error_detail = f"The run was interrupted {MAX_ATTEMPTS} times and has been stopped."
            run.lease_owner = None
            run.lease_expires_at = None
            add_event(db, run, "failed", data={"code": "too_many_attempts"})
            db.commit()
            return None
        add_event(db, run, "claimed", data={"worker": worker, "attempt": attempts, "resumed": attempts > 1})
        db.commit()
        return uuid.UUID(str(run_id))


def run_once(
    session_factory: sessionmaker[Session],
    providers: Mapping[str, AiProvider],
    *,
    worker: str,
    sleep: Sleep = time.sleep,
) -> uuid.UUID | None:
    """Claims and runs one run. Returns its id, or None if nothing was waiting."""
    run_id = claim(session_factory, worker)
    if run_id is not None:
        logger.info("Running agent run %s", run_id)
        Orchestrator(session_factory, providers, worker=worker, sleep=sleep).run(run_id)
    return run_id


def serve(
    session_factory: sessionmaker[Session],
    providers: Mapping[str, AiProvider],
    *,
    poll_seconds: float,
    once: bool = False,
) -> None:
    """Runs agent runs until stopped (Ctrl+C / SIGTERM). With ``once``, works through the queue and exits."""
    worker = worker_name()
    logger.info("Agent worker %s started", worker)
    while True:
        try:
            did_work = run_once(session_factory, providers, worker=worker) is not None
        except Exception:  # a broken run must not take the worker down; its lease expires and it's retried
            logger.exception("Agent run failed unexpectedly")
            did_work = True
        if not did_work:
            if once:
                return
            time.sleep(poll_seconds)
