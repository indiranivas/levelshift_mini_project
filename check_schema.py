import sqlite3

conn = sqlite3.connect('hiring.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print('TABLES IN DATABASE:')
for table in tables:
    table_name = table[0]
    print(f'\nTable: {table_name}')
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = cursor.fetchall()
    for col in columns:
        col_name = col[1]
        col_type = col[2]
        print(f'  - {col_name} ({col_type})')

conn.close()
