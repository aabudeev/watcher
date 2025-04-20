#!venv/bin/python3
# -*- coding: utf-8 -*-

import os
from cryptography.fernet import Fernet

key = os.environ.get('ENCRYPTION_KEY')
if key is None:
    key = Fernet.generate_key()
    print(f"ENCRYPTION_KEY: {key.decode()}")
    print(
        f"You need export to bash environments\n"
        f"\texport ENCRYPTION_KEY='{key.decode()}'\n"
        f"or write into service file\n"
        f"\t[Service]\n\t...\n\tEnvironment='{key.decode()}'\n\t..."
    )
else:
    print(f"ENCRYPTION_KEY: {key}")