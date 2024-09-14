import sqlite3

def init_db():
    conn = sqlite3.connect('qa_system.db')
    cursor = conn.cursor()
    
    # 创建表格
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def add_training_data(question, answer):
    conn = sqlite3.connect('qa_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO training_data (question, answer)
        VALUES (?, ?)
    ''', (question, answer))
    
    conn.commit()
    conn.close()

def get_training_data():
    conn = sqlite3.connect('qa_system.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT question, answer FROM training_data')
    rows = cursor.fetchall()
    
    conn.close()
    return rows

def add_pending_data(question):
    conn = sqlite3.connect('qa_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO pending_data (question)
        VALUES (?)
    ''', (question,))
    
    conn.commit()
    conn.close()

def get_all_questions():
    conn = sqlite3.connect('qa_system.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT question FROM training_data')
    rows = cursor.fetchall()
    
    conn.close()
    return [row[0] for row in rows]  # 返回所有问题列表

def delete_question(question):
    conn = sqlite3.connect('qa_system.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM training_data WHERE question = ?', (question,))
    
    conn.commit()
    conn.close()
