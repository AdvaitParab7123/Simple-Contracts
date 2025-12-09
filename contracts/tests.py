"""
Tests for Contract Management module.
"""

from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import (
    Contract, ContractFile, ContractVersion, ContractShare,
    AdditionalApproval, Clause, ClausePlaybookEntry, Deviation,
    RiskItem, SignatureRecord, AuditLog, Department, ContractType, Tag
)
from .permissions import (
    can_view_contract, can_edit_contract, can_delete_contract,
    can_manage_approvals, can_admin_contracts, can_create_contract,
    is_legal_admin, is_legal_user, get_user_role, Roles
)
from .services import DashboardService, ContractQueryService, ContractOperationsService

User = get_user_model()


class DepartmentModelTest(TestCase):
    """Tests for Department model"""
    
    def test_create_department(self):
        dept = Department.objects.create(name='Legal')
        self.assertEqual(str(dept), 'Legal')
        self.assertIsNotNone(dept.created_at)


class ContractTypeModelTest(TestCase):
    """Tests for ContractType model"""
    
    def test_create_contract_type(self):
        ct = ContractType.objects.create(
            name='Service Agreement',
            description='Standard service agreement'
        )
        self.assertEqual(str(ct), 'Service Agreement')
        self.assertTrue(ct.active)


class TagModelTest(TestCase):
    """Tests for Tag model"""
    
    def test_create_tag(self):
        tag = Tag.objects.create(name='High Priority', color='#ff0000')
        self.assertEqual(str(tag), 'High Priority')
        self.assertEqual(tag.color, '#ff0000')


class ContractModelTest(TestCase):
    """Tests for Contract model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.department = Department.objects.create(name='Legal')
        self.contract_type = ContractType.objects.create(name='NDA')
    
    def test_create_contract(self):
        contract = Contract.objects.create(
            title='Test Contract',
            customer_or_vendor_name='Test Company',
            owner=self.user,
            created_by=self.user,
            bu_team=self.department,
            contract_type=self.contract_type,
            effective_date=date.today(),
            value_amount=Decimal('10000.00'),
            currency='INR'
        )
        
        self.assertIsNotNone(contract.id)
        self.assertIn('CNT-', contract.contract_number)
        self.assertEqual(contract.status, Contract.Status.DRAFT)
        self.assertEqual(str(contract), f"{contract.contract_number} - Test Contract")
    
    def test_contract_expiring_soon(self):
        contract = Contract.objects.create(
            title='Expiring Contract',
            customer_or_vendor_name='Test Company',
            owner=self.user,
            status=Contract.Status.ACTIVE,
            end_date=date.today() + timedelta(days=15)
        )
        
        self.assertTrue(contract.is_expiring_soon)
    
    def test_contract_not_expiring_soon(self):
        contract = Contract.objects.create(
            title='Long Term Contract',
            customer_or_vendor_name='Test Company',
            owner=self.user,
            status=Contract.Status.ACTIVE,
            end_date=date.today() + timedelta(days=60)
        )
        
        self.assertFalse(contract.is_expiring_soon)
    
    def test_contract_expired(self):
        contract = Contract.objects.create(
            title='Old Contract',
            customer_or_vendor_name='Test Company',
            owner=self.user,
            end_date=date.today() - timedelta(days=10)
        )
        
        self.assertTrue(contract.is_expired)


class ContractFileModelTest(TestCase):
    """Tests for ContractFile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.contract = Contract.objects.create(
            title='Test Contract',
            customer_or_vendor_name='Test Company',
            owner=self.user
        )
    
    def test_only_one_primary_file(self):
        file1 = ContractFile.objects.create(
            contract=self.contract,
            file=SimpleUploadedFile('test1.pdf', b'content'),
            original_filename='test1.pdf',
            is_primary=True,
            uploaded_by=self.user
        )
        
        file2 = ContractFile.objects.create(
            contract=self.contract,
            file=SimpleUploadedFile('test2.pdf', b'content'),
            original_filename='test2.pdf',
            is_primary=True,
            uploaded_by=self.user
        )
        
        file1.refresh_from_db()
        self.assertFalse(file1.is_primary)
        self.assertTrue(file2.is_primary)


class AdditionalApprovalModelTest(TestCase):
    """Tests for AdditionalApproval model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='requester',
            email='requester@example.com',
            password='testpass123'
        )
        self.approver = User.objects.create_user(
            username='approver',
            email='approver@example.com',
            password='testpass123'
        )
        self.contract = Contract.objects.create(
            title='Test Contract',
            customer_or_vendor_name='Test Company',
            owner=self.user
        )
    
    def test_create_approval(self):
        approval = AdditionalApproval.objects.create(
            contract=self.contract,
            requested_by=self.user,
            approver=self.approver,
            reason='Need legal review'
        )
        
        self.assertEqual(approval.status, AdditionalApproval.Status.PENDING)
        self.assertIsNone(approval.decided_at)


class PermissionsTest(TestCase):
    """Tests for permission helper functions"""
    
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass'
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass'
        )
        self.other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='otherpass'
        )
        
        self.contract = Contract.objects.create(
            title='Test Contract',
            customer_or_vendor_name='Test Company',
            owner=self.regular_user,
            created_by=self.regular_user
        )
    
    def test_admin_can_view_any_contract(self):
        self.assertTrue(can_view_contract(self.admin_user, self.contract))
    
    def test_owner_can_view_contract(self):
        self.assertTrue(can_view_contract(self.regular_user, self.contract))
    
    def test_other_user_cannot_view_unshared_contract(self):
        self.assertFalse(can_view_contract(self.other_user, self.contract))
    
    def test_admin_can_edit_any_contract(self):
        self.assertTrue(can_edit_contract(self.admin_user, self.contract))
    
    def test_owner_can_edit_contract(self):
        self.assertTrue(can_edit_contract(self.regular_user, self.contract))
    
    def test_other_user_cannot_edit_unshared_contract(self):
        self.assertFalse(can_edit_contract(self.other_user, self.contract))
    
    def test_shared_user_can_view_contract(self):
        ContractShare.objects.create(
            contract=self.contract,
            shared_with_user=self.other_user,
            access_level='VIEW'
        )
        self.assertTrue(can_view_contract(self.other_user, self.contract))
    
    def test_shared_user_with_edit_can_edit_contract(self):
        ContractShare.objects.create(
            contract=self.contract,
            shared_with_user=self.other_user,
            access_level='EDIT'
        )
        self.assertTrue(can_edit_contract(self.other_user, self.contract))
    
    def test_admin_can_delete_any_contract(self):
        self.assertTrue(can_delete_contract(self.admin_user, self.contract))
    
    def test_owner_can_delete_draft_contract(self):
        self.assertTrue(can_delete_contract(self.regular_user, self.contract))
    
    def test_owner_cannot_delete_active_contract(self):
        self.contract.status = Contract.Status.ACTIVE
        self.contract.save()
        self.assertFalse(can_delete_contract(self.regular_user, self.contract))
    
    def test_get_user_role_superuser(self):
        self.assertEqual(get_user_role(self.admin_user), Roles.LEGAL_ADMIN)
    
    def test_is_legal_admin(self):
        self.assertTrue(is_legal_admin(self.admin_user))
        self.assertFalse(is_legal_admin(self.regular_user))


class DashboardServiceTest(TestCase):
    """Tests for DashboardService"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create some test contracts
        self.draft_contract = Contract.objects.create(
            title='Draft Contract',
            customer_or_vendor_name='Company A',
            owner=self.user,
            status=Contract.Status.DRAFT
        )
        
        self.pending_contract = Contract.objects.create(
            title='Pending Contract',
            customer_or_vendor_name='Company B',
            owner=self.user,
            status=Contract.Status.PENDING
        )
        
        self.active_contract = Contract.objects.create(
            title='Active Contract',
            customer_or_vendor_name='Company C',
            owner=self.user,
            status=Contract.Status.ACTIVE,
            end_date=date.today() + timedelta(days=20)
        )
    
    def test_get_pending_action_contracts(self):
        service = DashboardService(self.user)
        result = service.get_pending_action_contracts()
        
        self.assertEqual(result['count'], 2)  # Draft + Pending
    
    def test_get_expiring_contracts(self):
        service = DashboardService(self.user)
        result = service.get_expiring_contracts(days=30)
        
        self.assertEqual(result['count'], 1)  # Only active_contract
    
    def test_get_contract_stats(self):
        service = DashboardService(self.user)
        stats = service.get_contract_stats()
        
        self.assertEqual(stats['draft'], 1)
        self.assertEqual(stats['pending'], 1)
        self.assertEqual(stats['active'], 1)
        self.assertEqual(stats['total'], 3)


class ContractOperationsServiceTest(TestCase):
    """Tests for ContractOperationsService"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_contract(self):
        service = ContractOperationsService(self.user)
        
        contract = service.create_contract({
            'title': 'New Contract',
            'customer_or_vendor_name': 'Test Company',
            'category': Contract.Category.SALES,
            'effective_date': date.today()
        })
        
        self.assertIsNotNone(contract.id)
        self.assertEqual(contract.owner, self.user)
        self.assertEqual(contract.created_by, self.user)
        
        # Check audit log was created
        log = AuditLog.objects.filter(
            contract=contract,
            action=AuditLog.Action.CREATE_CONTRACT
        ).first()
        self.assertIsNotNone(log)
    
    def test_change_status(self):
        service = ContractOperationsService(self.user)
        
        contract = Contract.objects.create(
            title='Test Contract',
            customer_or_vendor_name='Company',
            owner=self.user,
            status=Contract.Status.DRAFT
        )
        
        service.change_status(contract, Contract.Status.PENDING, 'Ready for review')
        
        contract.refresh_from_db()
        self.assertEqual(contract.status, Contract.Status.PENDING)
        
        # Check audit log
        log = AuditLog.objects.filter(
            contract=contract,
            action=AuditLog.Action.CHANGE_STATUS
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.metadata['new_status'], Contract.Status.PENDING)


class ContractViewsTest(TestCase):
    """Tests for contract views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass'
        )
        
        self.contract = Contract.objects.create(
            title='Test Contract',
            customer_or_vendor_name='Test Company',
            owner=self.user,
            created_by=self.user
        )
    
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('contracts:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_dashboard_accessible_when_logged_in(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('contracts:dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_contract_list_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('contracts:list'))
        self.assertEqual(response.status_code, 200)
    
    def test_contract_detail_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('contracts:detail', kwargs={'pk': self.contract.pk})
        )
        self.assertEqual(response.status_code, 200)
    
    def test_contract_detail_view_forbidden_for_non_owner(self):
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='otherpass'
        )
        self.client.login(username='other', password='otherpass')
        response = self.client.get(
            reverse('contracts:detail', kwargs={'pk': self.contract.pk})
        )
        # Should redirect since user doesn't have access
        self.assertEqual(response.status_code, 302)
    
    def test_configurations_require_admin_role(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('contracts:configurations'))
        self.assertEqual(response.status_code, 302)  # Redirect - not admin
        
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(reverse('contracts:configurations'))
        self.assertEqual(response.status_code, 200)


class ApprovalServiceTest(TestCase):
    """Tests for ApprovalService"""
    
    def setUp(self):
        self.requester = User.objects.create_user(
            username='requester',
            email='requester@example.com',
            password='testpass123'
        )
        self.approver = User.objects.create_user(
            username='approver',
            email='approver@example.com',
            password='testpass123'
        )
        self.contract = Contract.objects.create(
            title='Test Contract',
            customer_or_vendor_name='Test Company',
            owner=self.requester
        )
    
    def test_create_approval_request(self):
        from .services import ApprovalService
        
        service = ApprovalService(self.requester)
        approval = service.create_approval_request(
            self.contract,
            self.approver,
            reason='Need legal sign-off'
        )
        
        self.assertEqual(approval.status, AdditionalApproval.Status.PENDING)
        self.assertEqual(approval.approver, self.approver)
        self.assertEqual(approval.requested_by, self.requester)
    
    def test_process_approval_decision(self):
        from .services import ApprovalService
        
        approval = AdditionalApproval.objects.create(
            contract=self.contract,
            requested_by=self.requester,
            approver=self.approver
        )
        
        service = ApprovalService(self.approver)
        service.process_decision(approval, 'APPROVED', 'Looks good')
        
        approval.refresh_from_db()
        self.assertEqual(approval.status, AdditionalApproval.Status.APPROVED)
        self.assertIsNotNone(approval.decided_at)
        self.assertEqual(approval.decision_comment, 'Looks good')

