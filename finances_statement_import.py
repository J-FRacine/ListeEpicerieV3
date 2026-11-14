"""Analyse prudente d'un relevé de carte de crédit PDF.

Le module extrait le texte avec pypdf, repère des lignes transactionnelles
génériques et propose des correspondances avec les transactions Finances.
Il ne concilie et ne modifie jamais une transaction lui-même.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
import io
import re
import unicodedata


_DATE_FULL_RE = re.compile(
    r"(?P<day>\d{1,2})[/-](?P<month>\d{1,2})[/-](?P<year>\d{2,4})"
)
_DATE_ISO_RE = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"
)
_DATE_SHORT_RE = re.compile(
    r"(?P<day>\d{1,2})[/-](?P<month>\d{1,2})(?![/-]\d)"
)
_AMOUNT_RE = re.compile(
    r"(?<!\d)(?P<sign>[-+−]?)\s*"
    r"(?P<amount>\d{1,3}(?:[ \u00a0.,]\d{3})*[.,]\d{2}|\d+[.,]\d{2})"
    r"\s*(?P<currency>\$|CAD|CA\$)?",
    re.IGNORECASE,
)

_STATEMENT_DATE_LABELS = (
    "date du relevé",
    "date du releve",
    "statement date",
    "date de clôture",
    "date de cloture",
    "closing date",
)
_BALANCE_LABELS = (
    "nouveau solde",
    "solde du relevé",
    "solde du releve",
    "new balance",
    "statement balance",
    "balance due",
    "solde à payer",
    "solde a payer",
)

_CREDIT_HINTS = (
    "paiement",
    "payment",
    "remboursement",
    "refund",
    "credit",
    "crédit",
    "retour",
)


def _normalize_text(value):
    text = unicodedata.normalize(
        "NFKD",
        str(value or "").strip().casefold(),
    )
    return " ".join(
        "".join(
            char
            for char in text
            if not unicodedata.combining(char)
        ).split()
    )


def _parse_amount_token(token):
    clean = str(token or "").strip().replace("\u00a0", " ")
    sign = Decimal("-1") if clean.startswith(("-", "−")) else Decimal("1")
    clean = clean.lstrip("+-−").strip().replace(" ", "")
    if "," in clean and "." in clean:
        if clean.rfind(",") > clean.rfind("."):
            clean = clean.replace(".", "").replace(",", ".")
        else:
            clean = clean.replace(",", "")
    elif "," in clean:
        clean = clean.replace(",", ".")
    try:
        return (Decimal(clean) * sign).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _coerce_date(match, *, statement_date=None):
    groups = match.groupdict()
    try:
        day = int(groups["day"])
        month = int(groups["month"])
        year_value = groups.get("year")
        if year_value:
            year = int(year_value)
            if year < 100:
                year += 2000 if year < 70 else 1900
        else:
            reference = statement_date or date.today()
            year = reference.year
            # Un relevé de janvier peut contenir des opérations de décembre.
            if reference.month <= 2 and month >= 11:
                year -= 1
        return date(year, month, day)
    except (TypeError, ValueError):
        return None


def _find_date_in_text(text, *, statement_date=None):
    for pattern in (_DATE_ISO_RE, _DATE_FULL_RE, _DATE_SHORT_RE):
        match = pattern.search(text)
        if match:
            parsed = _coerce_date(
                match,
                statement_date=statement_date,
            )
            if parsed:
                return parsed, match.span()
    return None, None


def _extract_labeled_date(text):
    normalized = _normalize_text(text)
    for label in _STATEMENT_DATE_LABELS:
        pos = normalized.find(_normalize_text(label))
        if pos < 0:
            continue
        # On recherche dans une fenêtre raisonnable autour du libellé dans
        # le texte original; les dates complètes sont privilégiées.
        window = text[max(0, pos - 40): pos + 120]
        for pattern in (_DATE_ISO_RE, _DATE_FULL_RE):
            match = pattern.search(window)
            if match:
                parsed = _coerce_date(match)
                if parsed:
                    return parsed
    return None


def _extract_labeled_balance(lines):
    for line in lines:
        normalized = _normalize_text(line)
        if not any(
            _normalize_text(label) in normalized
            for label in _BALANCE_LABELS
        ):
            continue
        matches = list(_AMOUNT_RE.finditer(line))
        if not matches:
            continue
        value = _parse_amount_token(
            (matches[-1].group("sign") or "")
            + matches[-1].group("amount")
        )
        if value is not None:
            return abs(value)
    return None


def extract_pdf_text(pdf_bytes, *, max_pages=60, max_bytes=12_000_000):
    if not isinstance(pdf_bytes, (bytes, bytearray)):
        raise ValueError("Le contenu PDF est invalide.")
    if not pdf_bytes:
        raise ValueError("Le fichier PDF est vide.")
    if len(pdf_bytes) > int(max_bytes):
        raise ValueError("Le relevé PDF dépasse la taille maximale de 12 Mo.")

    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError(
            "La dépendance pypdf n’est pas installée sur le serveur."
        ) from error

    try:
        reader = PdfReader(io.BytesIO(bytes(pdf_bytes)))
    except Exception as error:
        raise ValueError(
            "Le fichier ne semble pas être un PDF lisible."
        ) from error

    if len(reader.pages) > int(max_pages):
        raise ValueError(
            f"Le relevé contient plus de {int(max_pages)} pages."
        )

    texts = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            texts.append("")

    text = "\n".join(texts).strip()
    if not text:
        raise ValueError(
            "Aucun texte n’a pu être extrait du PDF. "
            "Le relevé est peut-être une image numérisée."
        )
    return text


def parse_statement_text(text):
    """Transforme le texte extrait en lignes transactionnelles candidates."""
    raw_text = str(text or "")
    if not raw_text.strip():
        raise ValueError("Le relevé ne contient aucun texte.")

    lines = [
        " ".join(line.split())
        for line in raw_text.splitlines()
        if line.strip()
    ]
    statement_date = _extract_labeled_date(raw_text)
    statement_balance = _extract_labeled_balance(lines)

    rows = []
    seen = set()
    for line_number, line in enumerate(lines, start=1):
        tx_date, date_span = _find_date_in_text(
            line,
            statement_date=statement_date,
        )
        if tx_date is None:
            continue

        amount_matches = list(_AMOUNT_RE.finditer(line))
        if not amount_matches:
            continue

        amount_match = amount_matches[-1]
        amount = _parse_amount_token(
            (amount_match.group("sign") or "")
            + amount_match.group("amount")
        )
        if amount is None or amount == 0:
            continue

        start_desc = date_span[1] if date_span else 0
        end_desc = amount_match.start()
        description = line[start_desc:end_desc].strip(" -–—:;|")
        if not description:
            description = "Transaction du relevé"

        normalized_description = _normalize_text(description)
        kind_hint = (
            "income"
            if any(
                hint in normalized_description
                for hint in (
                    _normalize_text(value)
                    for value in _CREDIT_HINTS
                )
            )
            else None
        )

        key = (
            tx_date,
            abs(amount),
            normalized_description,
        )
        if key in seen:
            continue
        seen.add(key)

        rows.append(
            {
                "line_number": line_number,
                "transaction_date": tx_date,
                "description": description[:240],
                "amount": abs(amount),
                "kind_hint": kind_hint,
                "source_line": line[:500],
            }
        )

    return {
        "statement_date": statement_date,
        "statement_balance": statement_balance,
        "rows": rows,
        "line_count": len(lines),
    }


def prepare_statement_import(pdf_bytes):
    text = extract_pdf_text(pdf_bytes)
    result = parse_statement_text(text)
    result["text_length"] = len(text)
    return result


def _description_similarity(left, right):
    left_norm = _normalize_text(left)
    right_norm = _normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm in right_norm or right_norm in left_norm:
        return 0.92
    return SequenceMatcher(
        None,
        left_norm,
        right_norm,
    ).ratio()


def match_statement_rows(
    statement_rows,
    finance_rows,
    *,
    date_window_days=3,
):
    """Propose des correspondances prudentes avec les transactions Finances.

    Une correspondance est dite certaine seulement si:
    - le montant est exactement le même;
    - la date est à +/- 3 jours;
    - le meilleur candidat est unique sans ambiguïté rapprochée.
    """
    candidates = [dict(row) for row in finance_rows or ()]
    results = []

    for source in statement_rows or ():
        source = dict(source)
        source_date = source["transaction_date"]
        source_amount = Decimal(source["amount"]).quantize(
            Decimal("0.01")
        )
        scored = []

        for candidate in candidates:
            candidate_amount = Decimal(
                candidate.get("amount") or 0
            ).copy_abs().quantize(Decimal("0.01"))
            if candidate_amount != source_amount:
                continue

            candidate_date = candidate.get("transaction_date")
            if not isinstance(candidate_date, date):
                try:
                    candidate_date = date.fromisoformat(
                        str(candidate_date)[:10]
                    )
                except (TypeError, ValueError):
                    continue

            days = abs((candidate_date - source_date).days)
            if days > int(date_window_days):
                continue

            hint = source.get("kind_hint")
            if (
                hint
                and candidate.get("transaction_type")
                and candidate.get("transaction_type") != hint
            ):
                continue

            similarity = _description_similarity(
                source.get("description"),
                candidate.get("description"),
            )
            score = (
                100
                - (days * 12)
                + int(similarity * 20)
            )
            scored.append(
                {
                    "transaction_id": int(candidate["id"]),
                    "transaction_date": candidate_date,
                    "description": candidate.get("description") or "",
                    "amount": candidate_amount,
                    "score": score,
                    "date_difference_days": days,
                    "description_similarity": similarity,
                }
            )

        scored.sort(
            key=lambda row: (
                -row["score"],
                row["date_difference_days"],
                row["transaction_id"],
            )
        )

        best = scored[0] if scored else None
        second = scored[1] if len(scored) > 1 else None
        certain = bool(
            best
            and best["score"] >= 76
            and (
                second is None
                or best["score"] - second["score"] >= 10
            )
        )

        results.append(
            {
                **source,
                "match": best,
                "certain": certain,
                "candidate_count": len(scored),
            }
        )

    certain_ids = []
    seen_ids = set()
    for row in results:
        if not row["certain"] or not row["match"]:
            continue
        transaction_id = int(row["match"]["transaction_id"])
        if transaction_id in seen_ids:
            # Deux lignes du relevé ne doivent jamais sélectionner silencieusement
            # la même transaction Finances.
            row["certain"] = False
            continue
        seen_ids.add(transaction_id)
        certain_ids.append(transaction_id)

    return {
        "rows": results,
        "certain_transaction_ids": certain_ids,
        "certain_count": len(certain_ids),
        "ambiguous_count": sum(
            1
            for row in results
            if row["match"] and not row["certain"]
        ),
        "unmatched_count": sum(
            1
            for row in results
            if not row["match"]
        ),
    }
