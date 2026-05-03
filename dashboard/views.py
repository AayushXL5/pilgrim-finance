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
    """Main dashboard page - Data is fetched via API and rendered client-side."""
    ledger = Ledger.objects.all()
    has_data = ledger.exists()
    
    # Only pass basic flags. The frontend will fetch all data from /api/ledger/
    context = {
        'has_data': has_data,
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
