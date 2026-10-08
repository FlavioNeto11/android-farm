import sqlite3
conn = sqlite3.connect(r'C:\git\android-farm\backend\data\farm.db')
cursor = conn.cursor()
cursor.execute("SELECT id, handle, status, error_message FROM accounts WHERE id = '90bb7729-899a-440b-a6ba-3af101501635'")
row = cursor.fetchone()
if row:
    print(f"ID: {row[0]}")
    print(f"Handle: {row[1]}")
    print(f"Status: {row[2]}")
    print(f"Error: {row[3]}")
else:
    print("Account not found")
conn.close()
