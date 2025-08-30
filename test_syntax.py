#!/usr/bin/env python3
"""Test rapido sintassi dei file Python"""
import ast
import sys

files_to_check = [
    'ateco_lookup.py',
    'visura_extractor.py'
]

errors = []

for filename in files_to_check:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        print(f"✅ {filename}: Sintassi OK")
    except SyntaxError as e:
        errors.append(f"❌ {filename}: Errore di sintassi alla riga {e.lineno}: {e.msg}")
        print(errors[-1])
    except Exception as e:
        errors.append(f"❌ {filename}: Errore: {str(e)}")
        print(errors[-1])

if errors:
    print(f"\n⚠️ Trovati {len(errors)} errori")
    sys.exit(1)
else:
    print("\n✅ Tutti i file hanno sintassi corretta")
    sys.exit(0)