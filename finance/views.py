"""Finance API endpoints."""
import csv
import io
import hashlib
import uuid

from decimal import Decimal
from django.db.models import Sum, Count, Q, F
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from finance.models import (
    BankTransaction, InternalLedgerEntry,
    ReconciliationResult, Ledger, CategoryRule
)
from finance.serializers import (
    BankTransactionSerializer, InternalLedgerEntrySerializer,
    ReconciliationResultSerializer, LedgerSerializer,
    SummarySerializer, CategoryBreakdownSerializer, CategoryRuleSerializer
)
from finance.reconciliation import run_reconciliation
from finance.categorizer import categorize


# ── Upload Endpoints ──

@extend_schema(
    summary='Upload bank statement CSV',
    description='Upload a bank_statement.csv file. Columns: date, narration, amount, type (credit/debit). Duplicates are automatically skipped.',
    request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}},
)
@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def upload_bank_statement(request):
    """Upload and ingest a bank statement CSV."""
    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'No file provided. Send a CSV with key "file".'}, status=400)

    batch_id = uuid.uuid4().hex[:12]
    created, skipped, errors = 0, 0, []

    try:
        decoded = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))

        for i, row in enumerate(reader, start=2):
            try:
                date_str = row.get('date', '').strip()
                narration = row.get('narration', '').strip()
                amount = Decimal(row.get('amount', '0').strip().replace(',', ''))
                txn_type = row.get('type', '').strip().lower()

                if txn_type not in ('credit', 'debit'):
                    errors.append(f"Row {i}: Invalid type '{txn_type}'")
                    continue

                raw = f"{date_str}|{narration.lower()}|{amount}|{txn_type}"
                h = hashlib.sha256(raw.encode()).hexdigest()

                if BankTransaction.objects.filter(hash=h).exists():
                    skipped += 1
                    continue

                BankTransaction.objects.create(
                    date=date_str, narration=narration,
                    amount=amount, type=txn_type,
                    source_file=file.name, upload_batch=batch_id, hash=h
                )
                created += 1
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")

    except Exception as e:
        return Response({'error': f'Failed to parse CSV: {str(e)}'}, status=400)

    return Response({
        'message': f'Bank statement uploaded successfully.',
        'batch_id': batch_id,
        'created': created,
        'duplicates_skipped': skipped,
        'errors': errors,
    })


@extend_schema(
    summary='Upload internal ledger CSV',
    description='Upload an internal_ledger.csv file. Columns: date, description, amount, category. Duplicates are automatically skipped.',
    request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}},
)
@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def upload_internal_ledger(request):
    """Upload and ingest an internal ledger CSV."""
    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'No file provided. Send a CSV with key "file".'}, status=400)

    batch_id = uuid.uuid4().hex[:12]
    created, skipped, errors = 0, 0, []

    try:
        decoded = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))

        for i, row in enumerate(reader, start=2):
            try:
                date_str = row.get('date', '').strip()
                description = row.get('description', '').strip()
                amount = Decimal(row.get('amount', '0').strip().replace(',', ''))
                category = row.get('category', '').strip()

                # Auto-categorize if no category provided
                if not category:
                    category = categorize(description)

                raw = f"{date_str}|{description.lower()}|{amount}|{category}"
                h = hashlib.sha256(raw.encode()).hexdigest()

                if InternalLedgerEntry.objects.filter(hash=h).exists():
                    skipped += 1
                    continue

                InternalLedgerEntry.objects.create(
                    date=date_str, description=description,
                    amount=amount, category=category,
                    source_file=file.name, upload_batch=batch_id, hash=h
                )
                created += 1
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")

    except Exception as e:
        return Response({'error': f'Failed to parse CSV: {str(e)}'}, status=400)

    return Response({
        'message': f'Internal ledger uploaded successfully.',
        'batch_id': batch_id,
        'created': created,
        'duplicates_skipped': skipped,
        'errors': errors,
    })


@extend_schema(
    summary='Clear all data',
    description='Deletes all uploaded CSVs and ledger data to reset the engine.',
)
@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def clear_data(request):
    """Clear all data from the database."""
    BankTransaction.objects.all().delete()
    InternalLedgerEntry.objects.all().delete()
    ReconciliationResult.objects.all().delete()
    Ledger.objects.all().delete()
    return Response({'message': 'All data successfully cleared.'})


# ── Reconciliation ──

@extend_schema(
    summary='Run reconciliation',
    description='Triggers the reconciliation engine. Matches bank transactions against internal ledger entries using confidence scoring (amount + date + narration similarity).',
)
@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def trigger_reconciliation(request):
    """Run the reconciliation engine."""
    bank_count = BankTransaction.objects.count()
    internal_count = InternalLedgerEntry.objects.count()

    if bank_count == 0 or internal_count == 0:
        return Response({
            'error': 'Upload both bank statement and internal ledger before reconciling.',
            'bank_transactions': bank_count,
            'internal_entries': internal_count,
        }, status=400)

    result = run_reconciliation()
    return Response({
        'message': 'Reconciliation complete.',
        **result,
    })


# ── Summary ──

@extend_schema(
    summary='Financial summary',
    description='Returns total credits, debits, net position, unmatched amounts, match rate, and anomaly count.',
    responses={200: SummarySerializer},
)
@api_view(['GET'])
def summary(request):
    """Financial summary with KPIs."""
    ledger = Ledger.objects.all()

    if not ledger.exists():
        return Response({'message': 'No data. Upload CSVs and run reconciliation first.'}, status=200)

    credits = ledger.filter(type='credit').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    debits = ledger.filter(type='debit').aggregate(t=Sum('amount'))['t'] or Decimal('0')

    matched = ledger.filter(reconciliation_status='matched').count()
    probable = ledger.filter(reconciliation_status='probable').count()
    unmatched = ledger.filter(reconciliation_status='unmatched').count()
    total = ledger.count()

    unmatched_bank = ledger.filter(
        source='bank', reconciliation_status='unmatched'
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    unmatched_internal = ledger.filter(
        source='internal', reconciliation_status='unmatched'
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    return Response({
        'total_credits': credits,
        'total_debits': debits,
        'net_position': credits - debits,
        'unmatched_amount_bank': unmatched_bank,
        'unmatched_amount_internal': unmatched_internal,
        'total_transactions': total,
        'matched_count': matched,
        'probable_count': probable,
        'unmatched_count': unmatched,
        'match_rate': round((matched + probable) / max(total, 1) * 100, 1),
        'anomaly_count': ledger.filter(anomaly_flag=True).count(),
    })


# ── Reconciliation Results ──

@extend_schema(
    summary='Reconciliation results',
    description='Returns all matched and unmatched entries with confidence scores. Filter by status: matched, probable, unmatched_bank, unmatched_internal.',
    parameters=[
        OpenApiParameter('status', str, description='Filter by status', required=False),
    ],
    responses={200: ReconciliationResultSerializer(many=True)},
)
@api_view(['GET'])
def reconciliation_list(request):
    """List reconciliation results with optional status filter."""
    qs = ReconciliationResult.objects.select_related('bank_transaction', 'internal_entry')
    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)

    serializer = ReconciliationResultSerializer(qs, many=True)
    return Response({
        'count': qs.count(),
        'results': serializer.data,
    })


# ── Category Breakdown ──

@extend_schema(
    summary='Category breakdown',
    description='Returns expenses grouped by category with totals and percentages.',
    responses={200: CategoryBreakdownSerializer(many=True)},
)
@api_view(['GET'])
def category_breakdown(request):
    """Expenses grouped by category."""
    breakdown = (
        Ledger.objects
        .filter(type='debit')
        .values('category')
        .annotate(total_amount=Sum('amount'), transaction_count=Count('id'))
        .order_by('-total_amount')
    )

    grand_total = sum(item['total_amount'] for item in breakdown) or Decimal('1')

    result = []
    for item in breakdown:
        result.append({
            'category': item['category'],
            'total_amount': item['total_amount'],
            'transaction_count': item['transaction_count'],
            'percentage': round(float(item['total_amount'] / grand_total * 100), 1),
        })

    return Response(result)


# ── Anomalies ──

@extend_schema(
    summary='Anomaly report',
    description='Returns transactions flagged as anomalous (unusually high amounts for their category).',
    responses={200: LedgerSerializer(many=True)},
)
@api_view(['GET'])
def anomalies(request):
    """List flagged anomalous transactions."""
    qs = Ledger.objects.filter(anomaly_flag=True)
    serializer = LedgerSerializer(qs, many=True)
    return Response({
        'count': qs.count(),
        'results': serializer.data,
    })


# ── Power BI Export ──

@extend_schema(
    summary='Export for Power BI',
    description='Returns the normalized ledger as a downloadable CSV file, ready for Power BI / Looker Studio import.',
)
@api_view(['GET'])
def export_powerbi(request):
    """Export ledger as CSV for Power BI / Looker Studio."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="pilgrim_ledger_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'date', 'amount', 'category', 'source', 'type',
        'narration', 'reconciliation_status', 'confidence_score',
        'anomaly_flag', 'anomaly_reason'
    ])

    for entry in Ledger.objects.all().iterator():
        writer.writerow([
            entry.date, entry.amount, entry.category, entry.source,
            entry.type, entry.narration, entry.reconciliation_status,
            entry.confidence_score, entry.anomaly_flag, entry.anomaly_reason
        ])

    return response


# ── Ledger ──

@extend_schema(
    summary='Full ledger',
    description='Returns the complete normalized ledger with all entries from both sources.',
    responses={200: LedgerSerializer(many=True)},
)
@api_view(['GET'])
def ledger_list(request):
    """Full normalized ledger."""
    qs = Ledger.objects.all()
    source = request.query_params.get('source')
    if source:
        qs = qs.filter(source=source)
    recon = request.query_params.get('reconciliation_status')
    if recon:
        qs = qs.filter(reconciliation_status=recon)

    serializer = LedgerSerializer(qs, many=True)
    return Response({
        'count': qs.count(),
        'results': serializer.data,
    })


# ── Sample Data ──

@extend_schema(exclude=True)
@api_view(['GET'])
def download_sample_bank(request):
    """Serve sample bank CSV directly."""
    content = (
        "date,narration,amount,type\n"
        "2026-04-10,Amazon Web Services,150.00,debit\n"
        "2026-04-12,Client Payment ACME Corp,5000.00,credit\n"
        "2026-04-15,Uber Rides,45.50,debit\n"
        "2026-04-18,WeWork Office Rent,1200.00,debit\n"
        "2026-04-20,Software Subscriptions,299.99,debit\n"
        "2026-04-22,Consulting Fee,2500.00,credit\n"
        "2026-04-25,Google Ads,850.00,debit\n"
    )
    response = HttpResponse(content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bank_statement.csv"'
    return response


@extend_schema(exclude=True)
@api_view(['GET'])
def download_sample_ledger(request):
    """Serve sample ledger CSV directly."""
    content = (
        "date,description,amount,category\n"
        "2026-04-10,AWS Cloud Hosting,-150.00,Software\n"
        "2026-04-12,Invoice 1042 - ACME,5000.00,Revenue\n"
        "2026-04-15,Uber ride to meeting,-45.50,Travel\n"
        "2026-04-18,WeWork Monthly Rent,-1200.00,Office\n"
        "2026-04-20,SaaS Subscriptions,-300.00,Software\n"
        "2026-04-22,Consulting - John Doe,2500.00,Revenue\n"
        "2026-04-26,Google Advertising,-850.00,Marketing\n"
    )
    response = HttpResponse(content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="internal_ledger.csv"'
    return response
