# Généré automatiquement par refactor_finances_flat.py
# Les fragments sont placés directement à la racine pour faciliter l'upload GitHub.
from __future__ import annotations

from pathlib import Path as _Path

_BASE = _Path(__file__).parent
_PARTS = sorted(_BASE.glob("finances_data_part_*.pyfrag"))

if not _PARTS:
    raise RuntimeError(
        "Fragments Finances introuvables pour finances_data.py"
    )

_source = "".join(
    part.read_text(encoding="utf-8")
    for part in _PARTS
)

exec(
    compile(
        _source,
        str(_BASE / "finances_data.py"),
        "exec",
    ),
    globals(),
    globals(),
)

del _source, _PARTS, _BASE, _Path


# Extraction progressive des lectures de transactions.
# Le bloc historique reste compilé dans les fragments pour cette petite étape,
# mais les appels publics passent désormais par le module dédié ci-dessous.
import finances_transactions_data as _transactions_data


def list_transactions(
    user_id,
    start_date=None,
    end_date=None,
    transaction_type=None,
    category_id=None,
    tag_id=None,
    status=None,
    payment_method_id=None,
    reconciliation_status=None,
    query=None,
    transaction_id=None,
    include_linked_transfer_destinations=True,
    amount_exact=None,
    amount_min=None,
    amount_max=None,
    limit=1000,
):
    return _transactions_data.list_transactions(
        user_id,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type,
        category_id=category_id,
        tag_id=tag_id,
        status=status,
        payment_method_id=payment_method_id,
        reconciliation_status=reconciliation_status,
        query=query,
        transaction_id=transaction_id,
        include_linked_transfer_destinations=(
            include_linked_transfer_destinations
        ),
        amount_exact=amount_exact,
        amount_min=amount_min,
        amount_max=amount_max,
        limit=limit,
        get_connection=get_connection,
    )


def get_transaction(user_id, transaction_id):
    return _transactions_data.get_transaction(
        user_id,
        transaction_id,
        list_transactions=list_transactions,
    )
