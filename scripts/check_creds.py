import sqlite3

conn = sqlite3.connect('C:/git/android-farm/data/farm.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT c.id, c.account_id, c.login_identifier, c.secret_ref, c.status, a.platform 
    FROM credentials c 
    JOIN accounts a ON c.account_id = a.id 
    WHERE a.profile_id = 'persona-jK7q7X9O-Y3PGRMk'
""")

rows = cursor.fetchall()
print('Credentials:')
for row in rows:
    print(f'  Platform: {row[5]}')
    print(f'  Login: {row[2]}')
    print(f'  Secret Ref: {row[3]}')
    print(f'  Status: {row[4]}')
    print()

conn.close()
