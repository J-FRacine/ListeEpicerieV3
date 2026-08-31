from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from db import get_connection
from finances_calculations import next_date, periods_per_year
from finances_validation import decimal_value, money, optional_date, text_value

SHARED_LOAN_ROLES = {
    "lender": "Prêteur",
    "borrower": "Emprunteur",
    "observer": "Consultation",
}
SHARED_LOAN_PERMISSIONS = {
    "view": "Lecture seulement",
    "edit": "Peut ajouter des versements",
}
VALID_FREQUENCY_UNITS = {"day", "week", "month", "year"}


def list_available_loan_participants(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, display_name, email
                FROM users
                WHERE is_active=TRUE AND id<>%s
                ORDER BY LOWER(display_name), LOWER(email), id;
                """,
                (user_id,),
            )
            return cur.fetchall()


def _require_shared_loan_access(cur, user_id, loan_id, *, edit=False):
    cur.execute(
        """
        SELECT loan.*,
               CASE WHEN loan.owner_user_id=%s THEN TRUE ELSE FALSE END AS is_owner,
               member.permission AS member_permission,
               member.role AS member_role
        FROM finance_shared_loans AS loan
        LEFT JOIN finance_shared_loan_members AS member
          ON member.loan_id=loan.id AND member.user_id=%s
        WHERE loan.id=%s
          AND (loan.owner_user_id=%s OR member.user_id=%s);
        """,
        (user_id, user_id, int(loan_id), user_id, user_id),
    )
    row = cur.fetchone()
    if not row:
        raise PermissionError("Vous n’avez pas accès à ce prêt.")
    if edit and not row["is_owner"] and row.get("member_permission") != "edit":
        raise PermissionError("Ce prêt est en lecture seulement pour votre compte.")
    return dict(row)


def save_shared_loan(
    user_id,
    *,
    title,
    original_balance,
    current_balance=None,
    annual_interest_rate=0,
    payment_amount=None,
    frequency_unit="month",
    frequency_interval=1,
    start_date=None,
    next_due_date=None,
    end_date=None,
    lender_name=None,
    borrower_name=None,
    note=None,
    status="active",
    members=None,
    loan_id=None,
):
    title = text_value(title, "Le nom du prêt", 160, required=True)
    original = money(original_balance, allow_zero=True)
    current = (
        original
        if current_balance in (None, "")
        else money(current_balance, allow_zero=True)
    )
    rate = (
        decimal_value(annual_interest_rate, "Le taux d’intérêt", allow_blank=True)
        or Decimal("0.00")
    )
    payment = money(payment_amount) if payment_amount not in (None, "") else None
    if frequency_unit not in VALID_FREQUENCY_UNITS:
        raise ValueError("La fréquence du prêt est invalide.")
    interval = int(frequency_interval or 1)
    if interval < 1:
        raise ValueError("L’intervalle de paiement doit être positif.")
    if status not in {"active", "paused", "completed"}:
        raise ValueError("Le statut du prêt est invalide.")

    normalized_members = []
    for member in members or []:
        member_id = int(member.get("user_id"))
        role = str(member.get("role") or "observer")
        permission = str(member.get("permission") or "view")
        if role not in SHARED_LOAN_ROLES or permission not in SHARED_LOAN_PERMISSIONS:
            raise ValueError("Les permissions du prêt sont invalides.")
        if member_id != int(user_id):
            normalized_members.append((member_id, role, permission))

    with get_connection() as conn:
        with conn.cursor() as cur:
            if loan_id:
                existing = _require_shared_loan_access(cur, user_id, loan_id, edit=True)
                if not existing["is_owner"]:
                    raise PermissionError(
                        "Seul le propriétaire peut modifier la fiche et le partage du prêt."
                    )
                cur.execute(
                    """
                    UPDATE finance_shared_loans
                    SET title=%s,lender_name=%s,borrower_name=%s,
                        original_balance=%s,current_balance=%s,
                        annual_interest_rate=%s,payment_amount=%s,
                        frequency_unit=%s,frequency_interval=%s,
                        start_date=%s,next_due_date=%s,end_date=%s,
                        note=%s,status=%s,updated_at=NOW()
                    WHERE id=%s AND owner_user_id=%s;
                    """,
                    (
                        title,
                        text_value(lender_name, "Le prêteur", 160),
                        text_value(borrower_name, "L’emprunteur", 160),
                        original,
                        current,
                        rate,
                        payment,
                        frequency_unit,
                        interval,
                        optional_date(start_date, "La date de début"),
                        optional_date(next_due_date, "La prochaine échéance"),
                        optional_date(end_date, "La date de fin"),
                        text_value(note, "La note", 2000),
                        status,
                        int(loan_id),
                        user_id,
                    ),
                )
                saved_id = int(loan_id)
            else:
                cur.execute(
                    """
                    INSERT INTO finance_shared_loans (
                        owner_user_id,title,lender_name,borrower_name,
                        original_balance,current_balance,annual_interest_rate,
                        payment_amount,frequency_unit,frequency_interval,
                        start_date,next_due_date,end_date,note,status
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id;
                    """,
                    (
                        user_id,
                        title,
                        text_value(lender_name, "Le prêteur", 160),
                        text_value(borrower_name, "L’emprunteur", 160),
                        original,
                        current,
                        rate,
                        payment,
                        frequency_unit,
                        interval,
                        optional_date(start_date, "La date de début"),
                        optional_date(next_due_date, "La prochaine échéance"),
                        optional_date(end_date, "La date de fin"),
                        text_value(note, "La note", 2000),
                        status,
                    ),
                )
                saved_id = int(cur.fetchone()["id"])

            cur.execute(
                "DELETE FROM finance_shared_loan_members WHERE loan_id=%s;",
                (saved_id,),
            )
            for member_id, role, permission in normalized_members:
                cur.execute(
                    """
                    INSERT INTO finance_shared_loan_members (loan_id,user_id,role,permission)
                    SELECT %s,id,%s,%s FROM users WHERE id=%s AND is_active=TRUE;
                    """,
                    (saved_id, role, permission, member_id),
                )
            conn.commit()
            return saved_id


def list_shared_loans(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT loan.*,
                       owner.display_name AS owner_name,
                       CASE WHEN loan.owner_user_id=%s THEN TRUE ELSE FALSE END AS is_owner,
                       member.permission AS my_permission,
                       member.role AS my_role,
                       COALESCE((
                           SELECT COUNT(*) FROM finance_shared_loan_members m
                           WHERE m.loan_id=loan.id
                       ),0)::INTEGER AS shared_count
                FROM finance_shared_loans AS loan
                JOIN users AS owner ON owner.id=loan.owner_user_id
                LEFT JOIN finance_shared_loan_members AS member
                  ON member.loan_id=loan.id AND member.user_id=%s
                WHERE loan.owner_user_id=%s OR member.user_id=%s
                ORDER BY CASE loan.status WHEN 'active' THEN 0 WHEN 'paused' THEN 1 ELSE 2 END,
                         LOWER(loan.title), loan.id;
                """,
                (user_id, user_id, user_id, user_id),
            )
            return [dict(row) for row in cur.fetchall()]


def get_shared_loan(user_id, loan_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            loan = _require_shared_loan_access(cur, user_id, loan_id)
            cur.execute(
                """
                SELECT member.user_id, member.role, member.permission,
                       account.display_name, account.email
                FROM finance_shared_loan_members AS member
                JOIN users AS account ON account.id=member.user_id
                WHERE member.loan_id=%s
                ORDER BY LOWER(account.display_name), member.user_id;
                """,
                (int(loan_id),),
            )
            loan["members"] = [dict(row) for row in cur.fetchall()]
            cur.execute(
                """
                SELECT event.*, account.display_name AS created_by_name
                FROM finance_shared_loan_events AS event
                JOIN users AS account ON account.id=event.created_by_user_id
                WHERE event.loan_id=%s
                ORDER BY event.event_date DESC, event.id DESC;
                """,
                (int(loan_id),),
            )
            loan["events"] = [dict(row) for row in cur.fetchall()]
            return loan


def add_shared_loan_event(
    user_id,
    loan_id,
    *,
    event_type,
    amount=0,
    event_date=None,
    note=None,
):
    if event_type not in {"payment", "principal_addition", "adjustment", "note"}:
        raise ValueError("Le type d’événement est invalide.")
    event_day = optional_date(event_date, "La date") or date.today()
    if event_type == "adjustment":
        try:
            value = Decimal(str(amount or 0)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError) as error:
            raise ValueError("Le montant est invalide.") from error
    else:
        value = money(amount, allow_zero=True)

    with get_connection() as conn:
        with conn.cursor() as cur:
            loan = _require_shared_loan_access(cur, user_id, loan_id, edit=True)
            balance = Decimal(loan["current_balance"])
            interest = Decimal("0.00")
            principal = Decimal("0.00")
            new_balance = balance
            if event_type == "payment":
                if value <= 0:
                    raise ValueError("Le versement doit être supérieur à 0.")
                periods = periods_per_year(
                    loan["frequency_unit"], int(loan["frequency_interval"] or 1)
                )
                periodic_rate = (
                    Decimal(loan["annual_interest_rate"] or 0)
                    / Decimal("100")
                    / periods
                )
                interest = (balance * periodic_rate).quantize(Decimal("0.01"))
                principal = max(Decimal("0.00"), value - interest)
                principal = min(balance, principal)
                new_balance = max(Decimal("0.00"), balance - principal)
            elif event_type == "principal_addition":
                principal = value
                new_balance = balance + value
            elif event_type == "adjustment":
                principal = value
                new_balance = max(Decimal("0.00"), balance + value)

            cur.execute(
                """
                INSERT INTO finance_shared_loan_events (
                    loan_id,created_by_user_id,event_date,event_type,amount,
                    interest_amount,principal_amount,balance_after,note
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);
                """,
                (
                    int(loan_id),
                    user_id,
                    event_day,
                    event_type,
                    value,
                    interest,
                    principal,
                    new_balance,
                    text_value(note, "La note", 1000),
                ),
            )
            new_status = "completed" if new_balance <= 0 else loan["status"]
            cur.execute(
                """
                UPDATE finance_shared_loans
                SET current_balance=%s,status=%s,updated_at=NOW()
                WHERE id=%s;
                """,
                (new_balance, new_status, int(loan_id)),
            )
            conn.commit()
            return {
                "balance_before": balance,
                "interest": interest,
                "principal": principal,
                "balance_after": new_balance,
            }


def shared_loan_amortization_preview(user_id, loan_id, max_rows=36):
    loan = get_shared_loan(user_id, loan_id)
    balance = Decimal(loan["current_balance"] or 0)
    payment = Decimal(loan.get("payment_amount") or 0)
    if payment <= 0 or balance <= 0:
        return []
    occurrence = loan.get("next_due_date") or date.today()
    periods = periods_per_year(
        loan["frequency_unit"], int(loan["frequency_interval"] or 1)
    )
    periodic_rate = (
        Decimal(loan["annual_interest_rate"] or 0) / Decimal("100") / periods
    )
    rows = []
    for number in range(1, max(1, min(int(max_rows), 120)) + 1):
        interest = (balance * periodic_rate).quantize(Decimal("0.01"))
        principal = max(Decimal("0.00"), payment - interest)
        if principal <= 0:
            break
        principal = min(balance, principal)
        actual_payment = principal + interest
        balance = max(Decimal("0.00"), balance - principal)
        rows.append(
            {
                "number": number,
                "date": occurrence,
                "payment": actual_payment,
                "interest": interest,
                "principal": principal,
                "remaining": balance,
            }
        )
        if balance <= 0:
            break
        occurrence = next_date(
            occurrence,
            loan["frequency_unit"],
            int(loan["frequency_interval"] or 1),
        )
    return rows
