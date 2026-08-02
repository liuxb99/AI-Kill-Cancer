"""Allow one public evidence record to support multiple gene assertions.

Revision ID: 029_ptc_evidence_unique
Revises: 028_ptc_integrated_research
"""

from alembic import op

revision = "029_ptc_evidence_unique"
down_revision = "028_ptc_integrated_research"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Use evidence_key as the canonical assertion identity.

    The same PMID or external evidence identifier may legitimately produce
    several gene/variant assertions. The previous source-level unique
    constraint incorrectly collapsed or rejected those assertions.
    """
    with op.batch_alter_table("domain_ptc_evidence_records") as batch_op:
        batch_op.drop_constraint("uq_ptc_evidence_source", type_="unique")


def downgrade() -> None:
    """Restore the legacy source-level uniqueness after removing duplicates.

    A direct downgrade is intentionally rejected when multi-assertion source
    records exist because silently deleting evidence would corrupt provenance.
    """
    connection = op.get_bind()
    duplicate = connection.exec_driver_sql(
        """
        SELECT source_name, source_record_id, COUNT(*)
        FROM domain_ptc_evidence_records
        GROUP BY source_name, source_record_id
        HAVING COUNT(*) > 1
        LIMIT 1
        """
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot downgrade 029: multiple gene assertions share the same evidence source record"
        )
    with op.batch_alter_table("domain_ptc_evidence_records") as batch_op:
        batch_op.create_unique_constraint(
            "uq_ptc_evidence_source",
            ["source_name", "source_record_id"],
        )
