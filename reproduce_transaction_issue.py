
import os
import django
from django.conf import settings
from django.db import connection

# Configure minimal Django settings
if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'postgres', # Assumes local postgres db
                'USER': 'postgres',
                'PASSWORD': 'password',
                'HOST': 'localhost',
                'PORT': '5432',
            }
        },
        INSTALLED_APPS=['django_rls'],
    )
    django.setup()

def test_transaction_scope():
    print("Testing set_config(is_local=True) behavior...")
    
    # Ensure we are in autocommit mode (default for Django outside transaction.atomic)
    connection.ensure_connection()
    original_autocommit = connection.autocommit
    print(f"Autocommit is: {original_autocommit}")
    
    with connection.cursor() as cursor:
        # 1. Set the variable locally
        cursor.execute("SELECT set_config('rls.test_var', '123', true)")
        print("Executed set_config(is_local=True)")
        
        # 2. Try to read it in the next statement
        cursor.execute("SELECT current_setting('rls.test_var', true)")
        result = cursor.fetchone()[0]
        
        print(f"Result in next statement: {result}")
        
        if result == '123':
            print("PASS: Variable persisted to next statement.")
        else:
            print("FAIL: Variable DID NOT persist. RLS will fail in autocommit mode.")

if __name__ == "__main__":
    try:
        test_transaction_scope()
    except Exception as e:
        print(f"Error: {e}")
