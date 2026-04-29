from django.contrib import admin
from finance.models import BankTransaction, InternalLedgerEntry, ReconciliationResult, Ledger, CategoryRule


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'narration', 'amount', 'type', 'upload_batch', 'created_at']
    list_filter = ['type', 'upload_batch', 'date']
    search_fields = ['narration']
    readonly_fields = ['hash', 'created_at']


@admin.register(InternalLedgerEntry)
class InternalLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ['date', 'description', 'amount', 'category', 'upload_batch', 'created_at']
    list_filter = ['category', 'upload_batch', 'date']
    search_fields = ['description']
    readonly_fields = ['hash', 'created_at']


@admin.register(ReconciliationResult)
class ReconciliationResultAdmin(admin.ModelAdmin):
    list_display = ['status', 'overall_confidence', 'amount_match', 'date_diff', 'narration_similarity', 'created_at']
    list_filter = ['status']
    readonly_fields = ['created_at']


@admin.register(Ledger)
class LedgerAdmin(admin.ModelAdmin):
    list_display = ['date', 'amount', 'category', 'source', 'type', 'reconciliation_status', 'anomaly_flag']
    list_filter = ['source', 'type', 'reconciliation_status', 'anomaly_flag', 'category']
    search_fields = ['narration', 'category']


@admin.register(CategoryRule)
class CategoryRuleAdmin(admin.ModelAdmin):
    list_display = ['pattern', 'category', 'priority', 'created_at']
    list_filter = ['category']
