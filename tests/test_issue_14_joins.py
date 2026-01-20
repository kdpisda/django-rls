import pytest
from django.db import connection, models
from django.db.models import Q

from django_rls.models import RLSModel
from django_rls.policies import ModelPolicy


@pytest.mark.django_db(transaction=True)
def test_joined_field_reference_error():
    """
    Reproduces Issue #14: Defining a policy that references a joined field
    (e.g., company__name) causes a FieldError or compilation error
    because standard CREATE POLICY syntax does not support JOINs.
    """

    class Company(models.Model):
        name = models.CharField(max_length=100)

        class Meta:
            app_label = "tests"
            db_table = "issue14_company"

    class Employee(RLSModel):
        name = models.CharField(max_length=100)
        company = models.ForeignKey(Company, on_delete=models.CASCADE)

        class Meta:
            app_label = "tests"
            db_table = "issue14_employee"
            rls_policies = [
                # This policy implies a JOIN: Employee -> Company
                ModelPolicy("company_name_policy", filters=Q(company__name="Acme"))
            ]

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(Company)
        schema_editor.create_model(Employee)

    try:
        # This triggers policy creation which compiles the Q object
        # With the fix (Subquery conversion), this should now SUCCEED.
        Employee.enable_rls()

        # Verify it works
        # Create Companies
        acme = Company.objects.create(name="Acme")
        other = Company.objects.create(name="Other")

        # Create Employees (Need to bypass RLS or use superuser for insertion if
        # strictly enforced)
        # Owner bypass applies if we had an owner field. We don't.
        # So we need to use FORCE RLS to test filtering or just normal?
        # Default policy is PERMISSIVE.
        # If no policy matches (and RLS on), default is DENY.
        # Our policy is "company__name='Acme'".

        # Insert Data - RLS is now FORCED, so only Acme employees can be created
        # since the policy is: company__name='Acme'
        Employee.objects.create(name="Alice", company=acme)

        # Bob at "Other" company would violate RLS policy WITH CHECK clause
        # This is expected behavior with FORCE ROW LEVEL SECURITY
        from django.db import ProgrammingError

        with pytest.raises(ProgrammingError):
            Employee.objects.create(name="Bob", company=other)

        # Let's ensure the policy exists in postgres
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_policy WHERE polname='company_name_policy'"
            )
            assert cursor.fetchone()[0] == 1

    except Exception as e:
        pytest.fail(f"Failed to enable RLS with joined field: {e}")

    finally:
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(Employee)
            schema_editor.delete_model(Company)
