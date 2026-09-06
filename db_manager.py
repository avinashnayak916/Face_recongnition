import sqlite3
import hashlib
from datetime import datetime
import os

DB_PATH = "attendance.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create admins table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    ''')

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            registered_date TEXT NOT NULL DEFAULT 'Unknown'
        )
    ''')
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN registered_date TEXT DEFAULT "Unknown"')
    except sqlite3.OperationalError:
        pass

    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_code TEXT,
            name TEXT,
            date TEXT,
            time TEXT,
            UNIQUE(user_code, date)
        )
    ''')
    
    # Seed default admin if not exists
    cursor.execute("SELECT * FROM admins WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", 
                       ("admin", hash_password("admin123")))

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_admin(username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    hashed_pwd = hash_password(password)
    
    cursor.execute("SELECT * FROM admins WHERE username = ? AND password_hash = ?", (username, hashed_pwd))
    result = cursor.fetchone()
    
    conn.close()
    return result is not None

def add_user(user_code, name, reg_date=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = reg_date if (reg_date and reg_date.strip()) else datetime.now().strftime('%Y-%m-%d')
    
    try:
        cursor.execute("INSERT INTO users (user_code, name, registered_date) VALUES (?, ?, ?)", (user_code, name, today))
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        # User code already exists
        return -1
    finally:
        conn.close()

def get_user_by_id(numeric_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_code, name FROM users WHERE id = ?", (numeric_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result

def mark_attendance(user_code, name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    
    try:
        cursor.execute("INSERT INTO attendance (user_code, name, date, time) VALUES (?, ?, ?, ?)", 
                       (user_code, name, current_date, current_time))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        # Already marked attendance for this user today
        success = False
        current_time = None
    finally:
        conn.close()
        
    return success, current_time

def get_daily_attendance_stats():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM attendance WHERE date = ?', (today,))
    total_present = c.fetchone()[0]
    conn.close()
    
    total_absent = max(0, total_users - total_present)
    percentage = (total_present / total_users * 100) if total_users > 0 else 0.0
    return {
        'total': total_users,
        'present': total_present,
        'absent': total_absent,
        'percentage': round(percentage, 1)
    }

def get_all_users():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('SELECT id, user_code, name, registered_date FROM users ORDER BY id DESC')
    records = c.fetchall()
    conn.close()
    return records

def get_today_attendance():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('SELECT user_code, name, date, time FROM attendance WHERE date = ? ORDER BY entry_id DESC', (today,))
    records = c.fetchall()
    conn.close()
    return records

def update_user(numeric_id, new_user_code, new_name, new_reg_date=None):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    try:
        # Check old user_code to update attendance records as well
        c.execute('SELECT user_code FROM users WHERE id = ?', (numeric_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return False, "User not found."
        old_code = row[0]

        if new_reg_date and new_reg_date.strip():
            # Update users table
            c.execute('UPDATE users SET user_code = ?, name = ?, registered_date = ? WHERE id = ?', 
                      (new_user_code, new_name, new_reg_date, numeric_id))
        else:
            c.execute('UPDATE users SET user_code = ?, name = ? WHERE id = ?', 
                      (new_user_code, new_name, numeric_id))

        # Update corresponding attendance logs to keep history synced
        c.execute('UPDATE attendance SET user_code = ?, name = ? WHERE user_code = ?', 
                  (new_user_code, new_name, old_code))

        conn.commit()
        conn.close()
        return True, "User updated successfully."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "User Code already exists. Please choose a unique code."
    except Exception as e:
        conn.close()
        return False, str(e)

def get_user_attendance_summary():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()

    # 1. Total unique working/attendance dates recorded in system
    c.execute('SELECT COUNT(DISTINCT date) FROM attendance')
    total_working_days = c.fetchone()[0] or 0

    # 2. Fetch all registered users
    c.execute('SELECT id, user_code, name, registered_date FROM users ORDER BY id ASC')
    users = c.fetchall()

    summary = []
    for u_id, code, name, reg_date in users:
        # Count distinct attendance dates for this specific user
        c.execute('SELECT COUNT(DISTINCT date) FROM attendance WHERE user_code = ?', (code,))
        present_days = c.fetchone()[0] or 0

        # Absent calculation
        absent_days = max(0, total_working_days - present_days)

        # Percentage calculation
        if total_working_days > 0:
            pct = round((present_days / total_working_days) * 100, 1)
        else:
            pct = 0.0

        summary.append({
            'id': u_id,
            'user_code': code,
            'name': name,
            'total_days': total_working_days,
            'present': present_days,
            'absent': absent_days,
            'percentage': f"{pct}%"
        })

    conn.close()
    return summary

if __name__ == "__main__":
    init_db()
