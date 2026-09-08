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


# Extraction progressive des écritures de transactions.
# Les fonctions originales restent encore présentes dans les fragments;
# ces façades tardives conservent les signatures publiques actuelles.
import finances_transactions_writes as _transactions_writes


def save_transaction(
    user_id,
    transaction_date,
    transaction_type,
    amount,
    description,
    category_id=None,
    tag_ids=None,
    note=None,
    status="confirmed",
    payment_method_id=None,
    reconciliation_status="unreconciled",
    reconciliation_date=None,
    budget_excluded=False,
    bank_programmed=False,
    reminder_enabled=False,
    reminder_time=None,
    transaction_id=None,
):
    return _transactions_writes.save_transaction(
        user_id,
        transaction_date,
        transaction_type,
        amount,
        description,
        category_id=category_id,
        tag_ids=tag_ids,
        note=note,
        status=status,
        payment_method_id=payment_method_id,
        reconciliation_status=reconciliation_status,
        reconciliation_date=reconciliation_date,
        budget_excluded=budget_excluded,
        bank_programmed=bank_programmed,
        reminder_enabled=reminder_enabled,
        reminder_time=reminder_time,
        transaction_id=transaction_id,
        TRANSACTION_TYPES=TRANSACTION_TYPES,
        TRANSACTION_STATUSES=TRANSACTION_STATUSES,
        RECONCILIATION_STATUSES=RECONCILIATION_STATUSES,
        normalize_reminder_time=_normalize_reminder_time,
        money=_money,
        text=_text,
        get_connection=get_connection,
        validate_links=_validate_links,
        validate_payment_method=_validate_payment_method,
    )


def delete_transaction(user_id, transaction_id):
    return _transactions_writes.delete_transaction(
        user_id,
        transaction_id,
        get_connection=get_connection,
    )


def set_transaction_status(user_id, transaction_id, status):
    return _transactions_writes.set_transaction_status(
        user_id,
        transaction_id,
        status,
        TRANSACTION_STATUSES=TRANSACTION_STATUSES,
        get_connection=get_connection,
    )


# Extraction progressive des lectures des paiements de carte liés.
# Les signatures publiques restent inchangées.
import finances_card_payments_data as _card_payments_data


def get_card_payment_transfer(user_id, transfer_id):
    return _card_payments_data.get_card_payment_transfer(
        user_id,
        transfer_id,
        get_connection=get_connection,
    )


def list_card_payment_transfers(user_id, limit=10000):
    return _card_payments_data.list_card_payment_transfers(
        user_id,
        limit=limit,
        get_connection=get_connection,
    )


# Extraction progressive de l'écriture des paiements de carte liés.
# La signature publique reste inchangée.
import finances_card_payments_writes as _card_payments_writes


def save_card_payment_transfer(
    user_id,
    source_payment_method_id,
    destination_payment_method_id,
    amount,
    source_date,
    destination_date=None,
    description=None,
    note=None,
    status="planned",
    bank_programmed=False,
    reminder_enabled=False,
    reminder_time=None,
    transfer_id=None,
):
    return _card_payments_writes.save_card_payment_transfer(
        user_id,
        source_payment_method_id,
        destination_payment_method_id,
        amount,
        source_date,
        destination_date=destination_date,
        description=description,
        note=note,
        status=status,
        bank_programmed=bank_programmed,
        reminder_enabled=reminder_enabled,
        reminder_time=reminder_time,
        transfer_id=transfer_id,
        TRANSACTION_STATUSES=TRANSACTION_STATUSES,
        money=_money,
        text=_text,
        normalize_reminder_time=_normalize_reminder_time,
        get_connection=get_connection,
        validate_card_payment_methods=_validate_card_payment_methods,
    )


# Extraction progressive des contrôles de l'Historique.
import finances_history_analysis as _history_analysis


def find_potential_duplicate_transactions(
    user_id,
    *,
    start_date=None,
    end_date=None,
    same_type=True,
    window_days=2,
    limit=10000,
):
    return _history_analysis.find_potential_duplicate_transactions(
        user_id,
        start_date=start_date,
        end_date=end_date,
        same_type=same_type,
        window_days=window_days,
        limit=limit,
        list_transactions=list_transactions,
    )
