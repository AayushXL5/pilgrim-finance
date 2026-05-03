from django.urls import path
from finance import views

urlpatterns = [
    # Upload
    path('upload/bank/', views.upload_bank_statement, name='upload-bank'),
    path('upload/ledger/', views.upload_internal_ledger, name='upload-ledger'),
    path('clear/', views.clear_data, name='clear-data'),
    # Reconciliation
    path('reconcile/', views.trigger_reconciliation, name='reconcile'),
    path('reconciliation/', views.reconciliation_list, name='reconciliation-list'),
    # Analytics
    path('summary/', views.summary, name='summary'),
    path('category-breakdown/', views.category_breakdown, name='category-breakdown'),
    path('anomalies/', views.anomalies, name='anomalies'),
    # Export
    path('export/powerbi/', views.export_powerbi, name='export-powerbi'),
    # Ledger
    path('ledger/', views.ledger_list, name='ledger-list'),
]
