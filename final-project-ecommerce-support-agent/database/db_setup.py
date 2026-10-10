import os
import sqlite3

# Getting the direct path to the database folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Get the directory of the current file (database folder)
DB_PATH = os.path.join(BASE_DIR, "ecommerce.db") # Get the path to the database file (database/ecommerce.db)
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql") # Get the path to the schema file (database/schema.sql)
SEED_PATH = os.path.join(BASE_DIR, "seed_data.sql") # Get the path to the seed data file (database/seed_data.sql)

def init_db():
    print(f"Creating database at path: {DB_PATH} ...") # Print the path of the database file
    
    # Connecting to the database (will be created automatically if it doesn't exist)
    conn = sqlite3.connect(DB_PATH) # Connect to the database
    cursor = conn.cursor() # Create a cursor object to execute SQL commands

    # 1. Reading and executing the schema (schema.sql)
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:   
        schema_script = f.read()
    cursor.executescript(schema_script)
    print("✓ Tables created successfully.")

    # 2. Reading and executing the sample data (seed_data.sql)
    with open(SEED_PATH, 'r', encoding='utf-8') as f:
        seed_script = f.read()
    cursor.executescript(seed_script)
    print("✓ Sample data inserted successfully.") 

    # Saving the changes and closing the connection
    conn.commit()
    conn.close()
    print("🚀 Database setup complete! The file 'ecommerce.db' is ready to use.")

if __name__ == "__main__":
    init_db()