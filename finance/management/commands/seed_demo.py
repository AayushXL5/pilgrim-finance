"""Seeds demo data from sample CSVs if the database is empty."""
import csv
import hashlib
import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from finance.models import BankTransaction, InternalLedgerEntry
from finance.categorizer import categorize
from finance.reconciliation import run_reconciliation


class Command(BaseCommand):
    help = 'Load sample CSVs and run reconciliation (skips if data exists)'

    def handle(self, *args, **options):
        if BankTransaction.objects.exists():
            self.stdout.write('Data already loaded, skipping seed.')
            return

        base = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'sample_data')

        # Bank statement
        bank_path = os.path.join(base, 'bank_statement.csv')
        if os.path.exists(bank_path):
            with open(bank_path, encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    date_str = row.get('date', '').strip()
                    narration = row.get('narration', '').strip()
                    amount = Decimal(row.get('amount', '0').strip().replace(',', ''))
                    txn_type = row.get('type', '').strip().lower()
                    raw = f"{date_str}|{narration.lower()}|{amount}|{txn_type}"
                    h = hashlib.sha256(raw.encode()).hexdigest()
                    if not BankTransaction.objects.filter(hash=h).exists():
                        BankTransaction.objects.create(
                            date=date_str, narration=narration,
                            amount=amount, type=txn_type,
                            source_file='bank_statement.csv', upload_batch='seed', hash=h
                        )
                        count += 1
                self.stdout.write(f'Bank: {count} entries loaded')

        # Internal ledger
        ledger_path = os.path.join(base, 'internal_ledger.csv')
        if os.path.exists(ledger_path):
            with open(ledger_path, encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    date_str = row.get('date', '').strip()
                    description = row.get('description', '').strip()
                    amount = Decimal(row.get('amount', '0').strip().replace(',', ''))
                    category = row.get('category', '').strip()
                    if not category:
                        category = categorize(description)
                    raw = f"{date_str}|{description.lower()}|{amount}|{category}"
                    h = hashlib.sha256(raw.encode()).hexdigest()
                    if not InternalLedgerEntry.objects.filter(hash=h).exists():
                        InternalLedgerEntry.objects.create(
                            date=date_str, description=description,
                            amount=amount, category=category,
                            source_file='internal_ledger.csv', upload_batch='seed', hash=h
                        )
                        count += 1
                self.stdout.write(f'Ledger: {count} entries loaded')

        # Reconcile
        result = run_reconciliation()
        self.stdout.write(f'Reconciliation: {result}')
        self.stdout.write('Demo data seeded.')
