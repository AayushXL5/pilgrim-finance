"""
Generate realistic sample CSVs for testing the reconciliation engine.
Creates bank_statement.csv and internal_ledger.csv with deliberate
edge cases: fuzzy narrations, date offsets, duplicates, unmatched entries.
"""
import csv
import os
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand


# ── Transaction templates ──
MATCHED_TRANSACTIONS = [
    # (bank_narration, internal_description, category, amount, type)
    ('SWIGGY ORDER #4521', 'Swiggy Order', 'Food & Dining', 456.00, 'debit'),
    ('ZOMATO 8827162', 'Zomato food delivery', 'Food & Dining', 892.00, 'debit'),
    ('UBER TRIP MUMBAI', 'Uber cab ride', 'Transport', 347.00, 'debit'),
    ('OLA RIDE 29APR', 'Ola auto fare', 'Transport', 189.00, 'debit'),
    ('AMAZON PAY INV/2026/04', 'Amazon purchase - headphones', 'Shopping', 2499.00, 'debit'),
    ('FLIPKART SELLER HUB', 'Flipkart order #FK882716', 'Shopping', 1299.00, 'debit'),
    ('AIRTEL PREPAID RCHG', 'Airtel mobile recharge', 'Utilities', 599.00, 'debit'),
    ('JIO FIBER BILL APR', 'Jio broadband monthly', 'Utilities', 999.00, 'debit'),
    ('TATA POWER BILL', 'Electricity bill - Apr 2026', 'Utilities', 2340.00, 'debit'),
    ('NETFLIX.COM', 'Netflix subscription', 'Subscriptions', 649.00, 'debit'),
    ('SPOTIFY PREMIUM', 'Spotify monthly', 'Subscriptions', 119.00, 'debit'),
    ('HDFC BANK EMI', 'Car loan EMI - HDFC', 'Loan & EMI', 15800.00, 'debit'),
    ('BAJAJ FINSERV EMI', 'Bajaj Finance laptop EMI', 'Loan & EMI', 3200.00, 'debit'),
    ('SOCIETY MAINTENANCE', 'Society maintenance Q1', 'Rent & Housing', 4500.00, 'debit'),
    ('RENT TRANSFER APR', 'Monthly rent payment', 'Rent & Housing', 18000.00, 'debit'),
    ('PETROL HPCL STATION', 'HP petrol pump fuel', 'Transport', 3200.00, 'debit'),
    ('CULT.FIT MEMBERSHIP', 'Cult.fit gym monthly', 'Fitness', 1499.00, 'debit'),
    ('APOLLO PHARMACY', 'Apollo pharmacy medicines', 'Healthcare', 780.00, 'debit'),
    ('DMart GROCERY', 'DMart monthly grocery', 'Shopping', 4560.00, 'debit'),
    ('MYNTRA FASHION', 'Myntra clothing order', 'Shopping', 2890.00, 'debit'),
    ('DOMINOS PIZZA ORDER', 'Dominos Friday dinner', 'Food & Dining', 756.00, 'debit'),
    ('CAFE COFFEE DAY', 'CCD coffee meeting', 'Food & Dining', 380.00, 'debit'),
    ('DECATHLON SPORTS', 'Decathlon sports gear', 'Shopping', 3450.00, 'debit'),
    ('ZERODHA FUND TRANSFER', 'Zerodha trading deposit', 'Investments', 10000.00, 'debit'),
    ('GROWW MF SIP', 'Groww mutual fund SIP', 'Investments', 5000.00, 'debit'),
    ('UDEMY COURSE PURCHASE', 'Udemy Python course', 'Education', 449.00, 'debit'),
    ('STAR HEALTH PREMIUM', 'Star Health insurance annual', 'Insurance', 12000.00, 'debit'),
    ('RAPIDO BIKE TAXI', 'Rapido bike ride', 'Transport', 89.00, 'debit'),
    ('MEESHO ORDER 44521', 'Meesho home decor order', 'Shopping', 1120.00, 'debit'),
    ('NYKAA BEAUTY ORDER', 'Nykaa cosmetics purchase', 'Shopping', 1850.00, 'debit'),
    # Credits
    ('SALARY CREDIT APR26', 'April salary credited', 'Salary', 65000.00, 'credit'),
    ('SALARY CREDIT MAR26', 'March salary', 'Salary', 65000.00, 'credit'),
    ('FREELANCE PAYMENT', 'Freelance design project', 'Salary', 15000.00, 'credit'),
    ('CASHBACK AMAZON', 'Amazon cashback reward', 'Shopping', 250.00, 'credit'),
    ('UPI REFUND SWIGGY', 'Swiggy refund for cancelled order', 'Food & Dining', 340.00, 'credit'),
    ('DIVIDEND HDFC BANK', 'HDFC Bank dividend Q4', 'Investments', 1200.00, 'credit'),
    ('FD INTEREST SBI', 'SBI FD interest payout', 'Investments', 3400.00, 'credit'),
]

# Unmatched bank-only transactions
UNMATCHED_BANK = [
    ('ATM CASH WDL SBI ANDHERI', 5000.00, 'debit'),
    ('UPI/P2P/RAHUL SHARMA', 2000.00, 'debit'),
    ('NEFT TO SAVINGS 2', 25000.00, 'debit'),
    ('INTEREST CREDIT SB', 142.00, 'credit'),
    ('ATM CASH WDL ICICI MG ROAD', 10000.00, 'debit'),
    ('UPI/P2P/PRIYA SINGH', 1500.00, 'debit'),
    ('CASHBACK PAYTM', 47.00, 'credit'),
]

# Unmatched internal-only transactions
UNMATCHED_INTERNAL = [
    ('Office supplies from local market', 'Shopping', 890.00),
    ('Team lunch cash payment', 'Food & Dining', 2400.00),
    ('Parking charges monthly', 'Transport', 1500.00),
    ('Provisions for depreciation', 'Uncategorized', 5000.00),
    ('Stationery reimbursement', 'Shopping', 650.00),
    ('Water purifier AMC', 'Utilities', 1200.00),
]


class Command(BaseCommand):
    help = 'Generate realistic sample CSV files for testing'

    def add_arguments(self, parser):
        parser.add_argument('--output-dir', type=str, default='sample_data',
                            help='Output directory for CSV files')

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        os.makedirs(output_dir, exist_ok=True)

        base_date = date(2026, 4, 1)
        bank_rows = []
        internal_rows = []

        # ── Matched transactions (with deliberate fuzzy edges) ──
        for i, (bank_narr, int_desc, category, amount, txn_type) in enumerate(MATCHED_TRANSACTIONS):
            day_offset = random.randint(0, 27)
            txn_date = base_date + timedelta(days=day_offset)

            # Bank entry
            bank_rows.append({
                'date': txn_date.strftime('%Y-%m-%d'),
                'narration': bank_narr,
                'amount': f'{amount:.2f}',
                'type': txn_type,
            })

            # Internal entry — with date offset (0-2 days) for testing
            date_drift = random.choice([0, 0, 0, 1, 1, 2])  # mostly same day
            int_date = txn_date + timedelta(days=date_drift)

            internal_rows.append({
                'date': int_date.strftime('%Y-%m-%d'),
                'description': int_desc,
                'amount': f'{amount:.2f}',
                'category': category,
            })

        # ── Unmatched bank transactions ──
        for narr, amount, txn_type in UNMATCHED_BANK:
            day_offset = random.randint(0, 27)
            txn_date = base_date + timedelta(days=day_offset)
            bank_rows.append({
                'date': txn_date.strftime('%Y-%m-%d'),
                'narration': narr,
                'amount': f'{amount:.2f}',
                'type': txn_type,
            })

        # ── Unmatched internal transactions ──
        for desc, category, amount in UNMATCHED_INTERNAL:
            day_offset = random.randint(0, 27)
            txn_date = base_date + timedelta(days=day_offset)
            internal_rows.append({
                'date': txn_date.strftime('%Y-%m-%d'),
                'description': desc,
                'amount': f'{amount:.2f}',
                'category': category,
            })

        # ── Duplicate entry (edge case) ──
        if bank_rows:
            bank_rows.append(bank_rows[0].copy())  # exact duplicate
            self.stdout.write(self.style.WARNING('  Added 1 duplicate bank entry for dedup testing'))

        # Shuffle for realism
        random.shuffle(bank_rows)
        random.shuffle(internal_rows)

        # ── Write CSVs ──
        bank_path = os.path.join(output_dir, 'bank_statement.csv')
        with open(bank_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'narration', 'amount', 'type'])
            writer.writeheader()
            writer.writerows(bank_rows)

        internal_path = os.path.join(output_dir, 'internal_ledger.csv')
        with open(internal_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'description', 'amount', 'category'])
            writer.writeheader()
            writer.writerows(internal_rows)

        self.stdout.write(self.style.SUCCESS(
            f'\nGenerated sample data:'
            f'\n   Bank statement:   {bank_path} ({len(bank_rows)} rows)'
            f'\n   Internal ledger:  {internal_path} ({len(internal_rows)} rows)'
            f'\n   Matched pairs:    {len(MATCHED_TRANSACTIONS)}'
            f'\n   Unmatched bank:   {len(UNMATCHED_BANK)}'
            f'\n   Unmatched internal: {len(UNMATCHED_INTERNAL)}'
        ))
