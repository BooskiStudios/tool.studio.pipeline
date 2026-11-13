"""The ``booski`` command: run the API, manage the database schema and provision accounts.

Later phases add ``seed-demo``, ``backup`` and ``restore-check`` here.
"""

import argparse
import getpass
import ipaddress
import logging
import sys
from pathlib import Path

from alembic import command

from booski_core.config import get_settings
from booski_core.migrations_config import alembic_config


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _serve(args: argparse.Namespace) -> int:
    # Until authentication exists (PR 2.2) the API must not be reachable from other machines.
    if not _is_loopback(args.host) and not args.allow_non_loopback:
        print(
            f"Refusing to listen on {args.host}: Booski Core has no authentication yet, so it only listens "
            "on this machine. Inside a container, pass --allow-non-loopback and publish the port to "
            "127.0.0.1 only (docker-compose.yml already does this).",
            file=sys.stderr,
        )
        return 2

    import uvicorn

    uvicorn.run(
        "booski_core.main:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
        reload_dirs=[str(Path(__file__).parent)] if args.reload else None,
        proxy_headers=False,
    )
    return 0


def _db(args: argparse.Namespace) -> int:
    # Show Alembic's progress ("Running upgrade  -> 0001, …") instead of finishing silently.
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = alembic_config(get_settings().sqlalchemy_url)
    if args.db_command == "upgrade":
        command.upgrade(config, args.revision)
    elif args.db_command == "downgrade":
        command.downgrade(config, args.revision)
    elif args.db_command == "current":
        command.current(config, verbose=True)
    elif args.db_command == "history":
        command.history(config)
    elif args.db_command == "revision":
        command.revision(config, message=args.message, autogenerate=True, rev_id=args.rev_id)
    return 0


def _read_password(args: argparse.Namespace) -> str:
    """From stdin with --password-stdin (automation), else a hidden prompt typed twice. Never from argv."""
    if args.password_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    first = getpass.getpass("Password (at least 12 characters): ")
    if getpass.getpass("Repeat password: ") != first:
        raise ValueError("The passwords don't match.")
    return first


def _accounts(args: argparse.Namespace) -> int:
    from sqlalchemy.orm import Session

    from booski_core import provisioning
    from booski_core.db import create_db_engine

    engine = create_db_engine(get_settings())
    try:
        with Session(engine) as db:
            if args.command == "create-owner":
                created = provisioning.create_owner(
                    db,
                    email=args.email,
                    display_name=args.name,
                    password=_read_password(args),
                    workspace_name=args.workspace_name,
                    workspace_slug=args.workspace_slug,
                )
                print(f"Created {args.email} as owner of workspace '{created.workspace_slug}'.")
            elif args.command == "set-password":
                revoked = provisioning.set_password(db, email=args.email, password=_read_password(args))
                print(f"Password updated for {args.email}. Signed out {revoked} session(s).")
            elif args.command in ("deactivate-user", "activate-user"):
                active = args.command == "activate-user"
                revoked = provisioning.set_active(db, email=args.email, active=active)
                state = "reactivated" if active else f"deactivated and signed out of {revoked} session(s)"
                print(f"{args.email} {state}.")
    except (provisioning.ProvisioningError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    return 0


def _devdb(args: argparse.Namespace) -> int:
    from booski_core import devdb

    try:
        paths = devdb.default_paths()
        if args.devdb_command == "setup":
            devdb.setup(paths, port=args.port, zip_path=args.zip)
        elif args.devdb_command == "start":
            devdb.start(paths)
        elif args.devdb_command == "stop":
            devdb.stop(paths)
        elif args.devdb_command == "status":
            print(devdb.status(paths))
    except devdb.DevDbError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="booski", description="Booski Core command-line tools.")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="Run the API server.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument(
        "--reload", action="store_true", help="Restart when source files change (development)."
    )
    serve.add_argument(
        "--allow-non-loopback",
        action="store_true",
        help="Allow a non-local --host. Only inside a container whose port is published to 127.0.0.1.",
    )
    serve.set_defaults(handler=_serve)

    db = commands.add_parser("db", help="Manage the database schema (Alembic).")
    db_commands = db.add_subparsers(dest="db_command", required=True)
    upgrade = db_commands.add_parser("upgrade", help="Apply migrations (default: to the latest).")
    upgrade.add_argument("revision", nargs="?", default="head")
    downgrade = db_commands.add_parser("downgrade", help="Revert migrations to a revision (e.g. -1, base).")
    downgrade.add_argument("revision")
    db_commands.add_parser("current", help="Show the revision applied to the database.")
    db_commands.add_parser("history", help="List all migrations.")
    revision = db_commands.add_parser("revision", help="Generate a new migration from model changes.")
    revision.add_argument("-m", "--message", required=True)
    revision.add_argument("--rev-id", help="Readable revision id, e.g. 0003 (default: random).")
    db.set_defaults(handler=_db)

    stdin_help = "Read the password from the first line of stdin instead of prompting."
    create_owner = commands.add_parser(
        "create-owner", help="Create the first owner account and their workspace (prompts for a password)."
    )
    create_owner.add_argument("--email", required=True)
    create_owner.add_argument("--name", required=True, help="Display name.")
    create_owner.add_argument("--workspace-name", required=True)
    create_owner.add_argument(
        "--workspace-slug", required=True, help="Workspace address, e.g. booski-studios."
    )
    create_owner.add_argument("--password-stdin", action="store_true", help=stdin_help)
    create_owner.set_defaults(handler=_accounts)

    set_password = commands.add_parser("set-password", help="Reset a user's password and sign them out.")
    set_password.add_argument("--email", required=True)
    set_password.add_argument("--password-stdin", action="store_true", help=stdin_help)
    set_password.set_defaults(handler=_accounts)

    for name, text in (
        ("deactivate-user", "Block a user from signing in and end their sessions."),
        ("activate-user", "Allow a deactivated user to sign in again."),
    ):
        account = commands.add_parser(name, help=text)
        account.add_argument("--email", required=True)
        account.set_defaults(handler=_accounts)

    devdb_parser = commands.add_parser("devdb", help="Run a private PostgreSQL 18 for local development.")
    devdb_commands = devdb_parser.add_subparsers(dest="devdb_command", required=True)
    setup = devdb_commands.add_parser(
        "setup", help="Download PostgreSQL, create the databases and backend/.env."
    )
    setup.add_argument("--port", type=int, default=55432)
    setup.add_argument(
        "--zip", type=Path, help="Use an already-downloaded PostgreSQL zip (checksum-verified)."
    )
    devdb_commands.add_parser("start", help="Start the local PostgreSQL.")
    devdb_commands.add_parser("stop", help="Stop the local PostgreSQL.")
    devdb_commands.add_parser("status", help="Show whether the local PostgreSQL is installed and running.")
    devdb_parser.set_defaults(handler=_devdb)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result: int = args.handler(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
