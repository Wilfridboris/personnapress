"""Tests for the Alembic autogenerate filter (Story: fix-scheduled-publish-catchup-reconciler).

Ensures the ``include_name`` predicate excludes only ``apscheduler_jobs`` (as a table)
and passes everything else through — preventing future ``alembic revision --autogenerate``
runs from emitting ``op.drop_table('apscheduler_jobs')``.
"""

from app.db.alembic_filters import include_name


def test_apscheduler_jobs_table_excluded():
    """The apscheduler_jobs table must be excluded from autogenerate."""
    assert include_name("apscheduler_jobs", "table", []) is False


def test_regular_table_included():
    """Ordinary tables (e.g. campaigns) must pass through."""
    assert include_name("campaigns", "table", []) is True


def test_users_table_included():
    """Another ordinary table (users) must pass through."""
    assert include_name("users", "table", []) is True


def test_non_table_apscheduler_index_included():
    """An index named apscheduler_* is NOT filtered — only tables are."""
    assert include_name("apscheduler_jobs_next_run_time", "index", []) is True


def test_non_table_schema_included():
    """Schema-type objects must pass through."""
    assert include_name("public", "schema", []) is True


def test_non_table_sequence_included():
    """Sequence-type objects must pass through."""
    assert include_name("apscheduler_jobs_seq", "sequence", []) is True
