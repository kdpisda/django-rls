"""Pytest configuration and fixtures."""

import pytest
from django.test import TestCase, TransactionTestCase
from django.db import connection


@pytest.fixture(scope='session')
def django_db_setup():
    """Setup test database with RLS support."""
    with connection.cursor() as cursor:
        # Ensure we're using PostgreSQL
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        if not version.startswith('PostgreSQL'):
            pytest.skip("RLS tests require PostgreSQL")


@pytest.fixture
def rls_test_case():
    """Fixture for RLS test cases."""
    class RLSTestCase(TransactionTestCase):
        def setUp(self):
            super().setUp()
            # Setup test data
            
        def tearDown(self):
            # Clean up RLS policies
            super().tearDown()
    
    return RLSTestCase


@pytest.fixture
def mock_request():
    """Mock Django request object."""
    class MockRequest:
        def __init__(self):
            self.user = None
            self.session = {}
    
    return MockRequest()