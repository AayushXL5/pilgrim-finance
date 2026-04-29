from rest_framework import serializers
from finance.models import BankTransaction, InternalLedgerEntry, ReconciliationResult, Ledger, CategoryRule


class BankTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankTransaction
        fields = ['id', 'date', 'narration', 'amount', 'type', 'source_file', 'upload_batch', 'created_at']


class InternalLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalLedgerEntry
        fields = ['id', 'date', 'description', 'amount', 'category', 'source_file', 'upload_batch', 'created_at']


class ReconciliationResultSerializer(serializers.ModelSerializer):
    bank_transaction = BankTransactionSerializer(read_only=True)
    internal_entry = InternalLedgerEntrySerializer(read_only=True)

    class Meta:
        model = ReconciliationResult
        fields = [
            'id', 'bank_transaction', 'internal_entry',
            'amount_match', 'date_diff', 'narration_similarity',
            'overall_confidence', 'status', 'created_at'
        ]


class LedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ledger
        fields = [
            'id', 'date', 'amount', 'category', 'source', 'type',
            'narration', 'reconciliation_status', 'confidence_score',
            'anomaly_flag', 'anomaly_reason', 'created_at'
        ]


class CategoryRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryRule
        fields = ['id', 'pattern', 'category', 'priority', 'created_at']


class SummarySerializer(serializers.Serializer):
    total_credits = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_debits = serializers.DecimalField(max_digits=14, decimal_places=2)
    net_position = serializers.DecimalField(max_digits=14, decimal_places=2)
    unmatched_amount_bank = serializers.DecimalField(max_digits=14, decimal_places=2)
    unmatched_amount_internal = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_transactions = serializers.IntegerField()
    matched_count = serializers.IntegerField()
    probable_count = serializers.IntegerField()
    unmatched_count = serializers.IntegerField()
    match_rate = serializers.FloatField()
    anomaly_count = serializers.IntegerField()


class CategoryBreakdownSerializer(serializers.Serializer):
    category = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    transaction_count = serializers.IntegerField()
    percentage = serializers.FloatField()
