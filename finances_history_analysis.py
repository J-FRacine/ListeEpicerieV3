from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal


def find_potential_duplicate_transactions(
    user_id,
    *,
    start_date=None,
    end_date=None,
    same_type=True,
    window_days=2,
    limit=10000,
    list_transactions,
):
    """Retourne des groupes de doublons potentiels: montant exact + dates proches."""

    rows = list_transactions(
        user_id,
        start_date=start_date,
        end_date=end_date,
        include_linked_transfer_destinations=False,
        limit=limit,
    )
    buckets = defaultdict(list)
    for row in rows:
        key = (
            Decimal(row["amount"]).copy_abs().quantize(Decimal("0.01")),
            row["transaction_type"] if same_type else "*",
        )
        buckets[key].append(dict(row))

    groups = []
    delta_days = max(0, int(window_days))
    for (amount, tx_type), bucket in buckets.items():
        bucket.sort(
            key=lambda item: (
                item["transaction_date"],
                int(item["id"]),
            )
        )
        cluster = []
        for row in bucket:
            if not cluster:
                cluster = [row]
                continue
            if (
                row["transaction_date"]
                - cluster[0]["transaction_date"]
            ).days <= delta_days:
                cluster.append(row)
            else:
                if len(cluster) >= 2:
                    groups.append(
                        {
                            "amount": amount,
                            "transaction_type": tx_type,
                            "transactions": cluster,
                        }
                    )
                cluster = [row]
        if len(cluster) >= 2:
            groups.append(
                {
                    "amount": amount,
                    "transaction_type": tx_type,
                    "transactions": cluster,
                }
            )

    groups.sort(
        key=lambda group: (
            group["transactions"][-1]["transaction_date"],
            group["amount"],
        ),
        reverse=True,
    )
    return groups


def list_month_unreconciled_transactions(
    user_id,
    month_value,
    *,
    month_start,
    add_months,
    list_transactions,
):
    month = month_start(month_value)
    month_end = add_months(month, 1) - timedelta(days=1)
    return list_transactions(
        user_id,
        start_date=month,
        end_date=month_end,
        status="confirmed",
        reconciliation_status="unreconciled",
        include_linked_transfer_destinations=True,
        limit=10000,
    )
