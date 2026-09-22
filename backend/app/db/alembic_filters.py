"""Alembic autogenerate filters.

Exportable predicates for ``context.configure(include_name=...)`` so future
autogenerate runs never emit a ``drop_table('apscheduler_jobs')`` diff.
APScheduler owns that table at runtime; it must never be touched by migrations.
"""


def include_name(name: str, type_: str, parent_names: object) -> bool:
    """Return False only for the ``apscheduler_jobs`` table; pass everything else.

    Wired into both ``run_migrations_offline`` and ``do_run_migrations`` in
    ``alembic/env.py`` via ``include_name=include_name``.
    """
    if type_ == "table" and name == "apscheduler_jobs":
        return False
    return True
