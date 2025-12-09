"""
URL Configuration for Contract Management module.

Include this in your main urls.py:
    path('contracts/', include('contracts.urls')),
"""

from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Contract List
    path('list/', views.ContractListView.as_view(), name='list'),
    
    # Contract CRUD
    path('new/', views.ContractCreateWizardView.as_view(), name='create'),
    path('<uuid:pk>/', views.ContractDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.ContractUpdateView.as_view(), name='edit'),
    
    # Contract Actions
    path('<uuid:pk>/status/', views.ContractStatusChangeView.as_view(), name='status_change'),
    path('<uuid:pk>/share/', views.ContractShareCreateView.as_view(), name='share'),
    
    # File Operations
    path('<uuid:pk>/files/upload/', views.ContractFileUploadView.as_view(), name='file_upload'),
    path('<uuid:pk>/files/<int:file_id>/download/', views.ContractFileDownloadView.as_view(), name='file_download'),
    path('<uuid:pk>/versions/add/', views.ContractVersionCreateView.as_view(), name='version_create'),
    
    # Contract Components
    path('<uuid:pk>/approvals/request/', views.ApprovalRequestCreateView.as_view(), name='approval_request'),
    path('<uuid:pk>/clauses/add/', views.ClauseCreateView.as_view(), name='clause_create'),
    path('<uuid:pk>/deviations/add/', views.DeviationCreateView.as_view(), name='deviation_create'),
    path('<uuid:pk>/risks/add/', views.RiskItemCreateView.as_view(), name='risk_create'),
    path('<uuid:pk>/signatures/add/', views.SignatureRecordCreateView.as_view(), name='signature_create'),
    
    # Approvals
    path('approvals/', views.ApprovalListView.as_view(), name='approvals'),
    path('approvals/<int:pk>/', views.ApprovalDetailView.as_view(), name='approval_detail'),
    
    # Configurations
    path('configurations/', views.ConfigurationsView.as_view(), name='configurations'),
    path('configurations/type/create/', views.ConfigTypeCreateView.as_view(), name='config_type_create'),
    path('configurations/type/<int:pk>/delete/', views.ConfigTypeDeleteView.as_view(), name='config_type_delete'),
    path('configurations/tag/create/', views.ConfigTagCreateView.as_view(), name='config_tag_create'),
    path('configurations/tag/<int:pk>/delete/', views.ConfigTagDeleteView.as_view(), name='config_tag_delete'),
    path('configurations/dept/create/', views.ConfigDeptCreateView.as_view(), name='config_dept_create'),
    path('configurations/dept/<int:pk>/delete/', views.ConfigDeptDeleteView.as_view(), name='config_dept_delete'),
    path('configurations/clause/create/', views.ConfigClauseCreateView.as_view(), name='config_clause_create'),
    path('configurations/clause/<int:pk>/delete/', views.ConfigClauseDeleteView.as_view(), name='config_clause_delete'),
]

