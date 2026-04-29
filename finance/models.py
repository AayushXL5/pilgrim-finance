import hashlib
from django.db import models


class BankTransaction(models.Model):
    """Raw bank statement transactions, ingested from CSV."""
    TYPE_CHOICES = [('credit', 'Credit'), ('debit', 'Debit')]

    date = models.DateField(db_index=True)
    narration = models.TextField()
    amount = models.DecimalField(max_digits=14, decimal_places=2, db_index=True)
    type = models.CharField(max_length=6, choices=TYPE_CHOICES)
    source_file = models.CharField(max_length=255, blank=True)
    upload_batch = models.CharField(max_length=64, blank=True, db_index=True)
    hash = models.CharField(max_length=64, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Bank Transaction'

    def save(self, *args, **kwargs):
        if not self.hash:
            raw = f"{self.date}|{self.narration.strip().lower()}|{self.amount}|{self.type}"
            self.hash = hashlib.sha256(raw.encode()).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.type.upper()}] {self.date} | ₹{self.amount:,.2f} | {self.narration[:50]}"


class InternalLedgerEntry(models.Model):
    """Internal ledger entries, ingested from CSV."""
    date = models.DateField(db_index=True)
    description = models.TextField()
    amount = models.DecimalField(max_digits=14, decimal_places=2, db_index=True)
    category = models.CharField(max_length=100, blank=True, db_index=True)
    source_file = models.CharField(max_length=255, blank=True)
    upload_batch = models.CharField(max_length=64, blank=True, db_index=True)
    hash = models.CharField(max_length=64, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Internal Ledger Entry'
        verbose_name_plural = 'Internal Ledger Entries'

    def save(self, *args, **kwargs):
        if not self.hash:
            raw = f"{self.date}|{self.description.strip().lower()}|{self.amount}|{self.category}"
            self.hash = hashlib.sha256(raw.encode()).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date} | ₹{self.amount:,.2f} | {self.description[:50]}"


class ReconciliationResult(models.Model):
    """Stores the result of matching a bank txn with an internal entry."""
    STATUS_CHOICES = [
        ('matched', 'Matched'),
        ('probable', 'Probable Match'),
        ('unmatched_bank', 'Unmatched (Bank)'),
        ('unmatched_internal', 'Unmatched (Internal)'),
    ]

    bank_transaction = models.ForeignKey(
        BankTransaction, on_delete=models.CASCADE,
        null=True, blank=True, related_name='reconciliation_results'
    )
    internal_entry = models.ForeignKey(
        InternalLedgerEntry, on_delete=models.CASCADE,
        null=True, blank=True, related_name='reconciliation_results'
    )
    amount_match = models.BooleanField(default=False)
    date_diff = models.IntegerField(default=0, help_text='Absolute difference in days')
    narration_similarity = models.FloatField(default=0, help_text='0-100 fuzzy score')
    overall_confidence = models.FloatField(default=0, help_text='0-100 weighted confidence')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-overall_confidence']
        verbose_name = 'Reconciliation Result'

    def __str__(self):
        return f"{self.status} | Confidence: {self.overall_confidence:.0f}%"


class Ledger(models.Model):
    """Normalized, unified ledger combining both sources."""
    SOURCE_CHOICES = [('bank', 'Bank'), ('internal', 'Internal')]
    TYPE_CHOICES = [('credit', 'Credit'), ('debit', 'Debit')]
    RECON_CHOICES = [
        ('matched', 'Matched'),
        ('probable', 'Probable'),
        ('unmatched', 'Unmatched'),
    ]

    date = models.DateField(db_index=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    category = models.CharField(max_length=100, db_index=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    type = models.CharField(max_length=6, choices=TYPE_CHOICES)
    narration = models.TextField()
    reconciliation_status = models.CharField(max_length=10, choices=RECON_CHOICES, db_index=True)
    confidence_score = models.FloatField(default=0)
    matched_with = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Linked entry from the other source'
    )
    anomaly_flag = models.BooleanField(default=False, db_index=True)
    anomaly_reason = models.CharField(max_length=255, blank=True)
    bank_transaction = models.ForeignKey(
        BankTransaction, on_delete=models.SET_NULL, null=True, blank=True
    )
    internal_entry = models.ForeignKey(
        InternalLedgerEntry, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Ledger Entry'
        verbose_name_plural = 'Ledger Entries'

    def __str__(self):
        flag = '🚨' if self.anomaly_flag else ''
        return f"{flag} {self.date} | {self.source} | ₹{self.amount:,.2f} | {self.category}"


class CategoryRule(models.Model):
    """Extensible rules for auto-categorizing transactions."""
    pattern = models.CharField(max_length=255, help_text='Regex pattern to match narration/description')
    category = models.CharField(max_length=100)
    priority = models.IntegerField(default=0, help_text='Higher priority rules are checked first')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-priority']
        verbose_name = 'Category Rule'

    def __str__(self):
        return f"{self.pattern} → {self.category} (priority: {self.priority})"
