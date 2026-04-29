"""
Reconciliation engine — matches bank transactions against internal ledger entries.

Scoring: amount (40 pts) + date proximity (30 pts) + narration similarity (30 pts)
>= 80 = matched, 60-79 = probable, < 60 = unmatched
"""
from decimal import Decimal
from difflib import SequenceMatcher

from finance.models import (
    BankTransaction, InternalLedgerEntry,
    ReconciliationResult, Ledger
)
from finance.categorizer import categorize


def _amount_score(bank_amt: Decimal, internal_amt: Decimal) -> tuple[float, bool]:
    """Score amount similarity. Returns (score, is_exact_match)."""
    if bank_amt == internal_amt:
        return 40.0, True
    diff_pct = abs(bank_amt - internal_amt) / max(bank_amt, internal_amt, Decimal('0.01')) * 100
    if diff_pct <= 1:
        return 20.0, False
    return 0.0, False


def _date_score(bank_date, internal_date) -> tuple[float, int]:
    """Score date proximity. Returns (score, abs_day_diff)."""
    diff = abs((bank_date - internal_date).days)
    if diff == 0:
        return 30.0, diff
    elif diff == 1:
        return 20.0, diff
    elif diff == 2:
        return 10.0, diff
    return 0.0, diff


def _narration_score(bank_narr: str, internal_desc: str) -> float:
    """Score narration similarity using SequenceMatcher."""
    a = bank_narr.strip().lower()
    b = internal_desc.strip().lower()
    ratio = SequenceMatcher(None, a, b).ratio()
    return round(ratio * 30, 2)


def run_reconciliation():
    """
    Core reconciliation logic.
    1. Clear previous results
    2. For each bank txn, find the best matching internal entry
    3. Create ReconciliationResult records
    4. Build the normalized Ledger
    """
    # Clear previous runs
    ReconciliationResult.objects.all().delete()
    Ledger.objects.all().delete()

    bank_txns = list(BankTransaction.objects.all())
    internal_entries = list(InternalLedgerEntry.objects.all())

    matched_bank_ids = set()
    matched_internal_ids = set()
    probable_bank_ids = set()
    probable_internal_ids = set()
    results = []

    # ── Phase 1: Find best matches ──
    for bt in bank_txns:
        best_match = None
        best_confidence = 0

        for ie in internal_entries:
            if ie.id in matched_internal_ids:
                continue

            # Date must be within 2 days
            date_s, date_diff = _date_score(bt.date, ie.date)
            if date_diff > 2:
                continue

            amt_s, amt_exact = _amount_score(bt.amount, ie.amount)
            if amt_s == 0:
                continue  # Amount doesn't match at all

            narr_s = _narration_score(bt.narration, ie.description)
            confidence = amt_s + date_s + narr_s

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = {
                    'internal_entry': ie,
                    'amount_match': amt_exact,
                    'date_diff': date_diff,
                    'narration_similarity': round(narr_s / 0.3, 2) if narr_s > 0 else 0,
                    'overall_confidence': round(confidence, 2),
                }

        if best_match and best_confidence >= 60:
            ie = best_match['internal_entry']
            status = 'matched' if best_confidence >= 80 else 'probable'
            results.append(ReconciliationResult(
                bank_transaction=bt,
                internal_entry=ie,
                amount_match=best_match['amount_match'],
                date_diff=best_match['date_diff'],
                narration_similarity=best_match['narration_similarity'],
                overall_confidence=best_match['overall_confidence'],
                status=status,
            ))
            if status == 'matched':
                matched_bank_ids.add(bt.id)
                matched_internal_ids.add(ie.id)
            else:
                probable_bank_ids.add(bt.id)
                probable_internal_ids.add(ie.id)
        else:
            results.append(ReconciliationResult(
                bank_transaction=bt,
                internal_entry=None,
                amount_match=False,
                date_diff=0,
                narration_similarity=0,
                overall_confidence=best_confidence if best_match else 0,
                status='unmatched_bank',
            ))

    # ── Phase 2: Mark unmatched internal entries ──
    for ie in internal_entries:
        if ie.id not in matched_internal_ids:
            results.append(ReconciliationResult(
                bank_transaction=None,
                internal_entry=ie,
                amount_match=False,
                date_diff=0,
                narration_similarity=0,
                overall_confidence=0,
                status='unmatched_internal',
            ))

    ReconciliationResult.objects.bulk_create(results)

    # -- Phase 3: Build normalized ledger --
    _build_ledger(bank_txns, internal_entries, matched_bank_ids, matched_internal_ids, probable_bank_ids, probable_internal_ids)

    return {
        'total_bank': len(bank_txns),
        'total_internal': len(internal_entries),
        'matched': sum(1 for r in results if r.status == 'matched'),
        'probable': sum(1 for r in results if r.status == 'probable'),
        'unmatched_bank': sum(1 for r in results if r.status == 'unmatched_bank'),
        'unmatched_internal': sum(1 for r in results if r.status == 'unmatched_internal'),
    }


def _build_ledger(bank_txns, internal_entries, matched_bank_ids, matched_internal_ids, probable_bank_ids, probable_internal_ids):
    """Build the normalized ledger from both sources + reconciliation data."""
    ledger_entries = []

    for bt in bank_txns:
        if bt.id in matched_bank_ids:
            recon_status = 'matched'
        elif bt.id in probable_bank_ids:
            recon_status = 'probable'
        else:
            recon_status = 'unmatched'

        confidence = 0
        recon = ReconciliationResult.objects.filter(
            bank_transaction=bt, status__in=['matched', 'probable']
        ).first()
        if recon:
            confidence = recon.overall_confidence

        category = categorize(bt.narration)
        is_anomaly, anomaly_reason = _detect_anomaly(bt.amount, bt.type, category)

        ledger_entries.append(Ledger(
            date=bt.date,
            amount=bt.amount,
            category=category,
            source='bank',
            type=bt.type,
            narration=bt.narration,
            reconciliation_status=recon_status,
            confidence_score=confidence,
            anomaly_flag=is_anomaly,
            anomaly_reason=anomaly_reason,
            bank_transaction=bt,
        ))

    for ie in internal_entries:
        if ie.id in matched_internal_ids:
            recon_status = 'matched'
        elif ie.id in probable_internal_ids:
            recon_status = 'probable'
        else:
            recon_status = 'unmatched'

        confidence = 0
        recon = ReconciliationResult.objects.filter(
            internal_entry=ie, status__in=['matched', 'probable']
        ).first()
        if recon:
            confidence = recon.overall_confidence

        category = ie.category or categorize(ie.description)
        txn_type = 'debit' if ie.amount > 0 else 'credit'
        is_anomaly, anomaly_reason = _detect_anomaly(ie.amount, txn_type, category)

        ledger_entries.append(Ledger(
            date=ie.date,
            amount=abs(ie.amount),
            category=category,
            source='internal',
            type=txn_type,
            narration=ie.description,
            reconciliation_status=recon_status,
            confidence_score=confidence,
            anomaly_flag=is_anomaly,
            anomaly_reason=anomaly_reason,
            internal_entry=ie,
        ))

    Ledger.objects.bulk_create(ledger_entries)


def _detect_anomaly(amount, txn_type, category) -> tuple[bool, str]:
    """Flag unusual transactions based on amount thresholds per category."""
    thresholds = {
        'Food & Dining': 2000,
        'Transport': 5000,
        'Utilities': 5000,
        'Shopping': 4000,
        'Subscriptions': 1000,
        'Uncategorized': 5000,
        'Fitness': 2000,
        'Healthcare': 3000,
        'Education': 2000,
    }
    limit = thresholds.get(category, 20000)
    if amount > limit:
        return True, f'Amount exceeds typical {category} threshold of {limit:,.0f}'
    return False, ''
