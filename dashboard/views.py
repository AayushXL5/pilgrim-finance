import json
import os
from decimal import Decimal
from django.conf import settings
from django.db.models import Sum, Count
from django.http import FileResponse, Http404
from django.shortcuts import render
from finance.models import Ledger, BankTransaction, InternalLedgerEntry, ReconciliationResult


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def dashboard_view(request):
    """Main dashboard page with all chart data pre-loaded."""
    ledger = Ledger.objects.all()
    has_data = ledger.exists()

    # ── KPI Cards ──
    credits = ledger.filter(type='credit').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    debits = ledger.filter(type='debit').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    net = credits - debits
    total = ledger.count()
    matched = ledger.filter(reconciliation_status='matched').count()
    probable = ledger.filter(reconciliation_status='probable').count()
    unmatched = ledger.filter(reconciliation_status='unmatched').count()
    match_rate = round((matched + probable) / max(total, 1) * 100, 1)
    anomaly_count = ledger.filter(anomaly_flag=True).count()
    unmatched_amount = ledger.filter(reconciliation_status='unmatched').aggregate(t=Sum('amount'))['t'] or Decimal('0')

    # ── Category Breakdown (for pie chart) ──
    cat_data = (
        ledger.filter(type='debit')
        .values('category')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )
    cat_labels = [c['category'] for c in cat_data]
    cat_values = [float(c['total']) for c in cat_data]

    # ── Daily Cashflow (for area chart) ──
    daily_credits = dict(
        ledger.filter(type='credit')
        .values('date')
        .annotate(total=Sum('amount'))
        .values_list('date', 'total')
    )
    daily_debits = dict(
        ledger.filter(type='debit')
        .values('date')
        .annotate(total=Sum('amount'))
        .values_list('date', 'total')
    )
    all_dates = sorted(set(list(daily_credits.keys()) + list(daily_debits.keys())))
    cashflow_labels = [d.strftime('%d %b') for d in all_dates]
    cashflow_credits = [float(daily_credits.get(d, 0)) for d in all_dates]
    cashflow_debits = [float(daily_debits.get(d, 0)) for d in all_dates]

    # ── Reconciliation Status (for bar chart) ──
    recon_data = {
        'Matched': ReconciliationResult.objects.filter(status='matched').count(),
        'Probable': ReconciliationResult.objects.filter(status='probable').count(),
        'Unmatched (Bank)': ReconciliationResult.objects.filter(status='unmatched_bank').count(),
        'Unmatched (Internal)': ReconciliationResult.objects.filter(status='unmatched_internal').count(),
    }

    # ── Top Unmatched Transactions ──
    top_unmatched = ledger.filter(reconciliation_status='unmatched').order_by('-amount')[:10]

    # ── Anomalies ──
    anomalies = ledger.filter(anomaly_flag=True).order_by('-amount')[:10]

    # ── Data Counts ──
    bank_count = BankTransaction.objects.count()
    internal_count = InternalLedgerEntry.objects.count()

    context = {
        'has_data': has_data,
        'credits': credits,
        'debits': debits,
        'net': net,
        'total': total,
        'matched': matched,
        'probable': probable,
        'unmatched': unmatched,
        'match_rate': match_rate,
        'anomaly_count': anomaly_count,
        'unmatched_amount': unmatched_amount,
        'bank_count': bank_count,
        'internal_count': internal_count,
        # Chart data as JSON
        'cat_labels': json.dumps(cat_labels),
        'cat_values': json.dumps(cat_values),
        'cashflow_labels': json.dumps(cashflow_labels),
        'cashflow_credits': json.dumps(cashflow_credits),
        'cashflow_debits': json.dumps(cashflow_debits),
        'recon_labels': json.dumps(list(recon_data.keys())),
        'recon_values': json.dumps(list(recon_data.values())),
        'top_unmatched': top_unmatched,
        'anomalies': anomalies,
    }
    return render(request, 'dashboard/index.html', context)


def download_sample(request, filename):
    """Serve sample CSV files for download."""
    allowed = {
        'bank_statement_v2.csv', 'internal_ledger_v2.csv',
        'bank_statement.csv', 'internal_ledger.csv',
    }
    if filename not in allowed:
        raise Http404
    path = os.path.join(settings.BASE_DIR, 'sample_data', filename)
    if not os.path.exists(path):
        raise Http404
    return FileResponse(open(path, 'rb'), as_attachment=True, filename=filename)
