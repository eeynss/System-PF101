import mysql.connector
from password_utils import new_salt, hash_password

# MySQL SETTINGS. Change these to match the MySQL on your computer. Every screen uses this file.
DB_HOST = "localhost"        # MySQL runs on this same computer
DB_USER = "root"             # MySQL username
DB_PASSWORD = "12345678"     # MySQL password
DB_NAME = "inventory_db"     # our database (like a folder that holds our tables)


# Send one SQL command to MySQL and give back the answer.
#   sql    = the command, for example "SELECT * FROM products WHERE id = %s"
#   values = the real values for each %s blank in the command, in order.
#            MySQL fills them in safely, so typed text can never break the command (no SQL injection).
#   fetch  = what answer we want back:
#            "one" = one row, "all" = a list of rows, None = nothing (INSERT, UPDATE, DELETE give no rows)
# These are the same steps as in our CRUD lessons: connect -> cursor -> execute -> commit -> close.
# If MySQL gives an error, show_error() in app.py shows it in a message box.
def run_sql(sql, values=(), fetch=None, use_database=True):
    # Step 1: connect to MySQL.
    connection = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
                                         database=DB_NAME if use_database else None, connection_timeout=5)
    # Step 2: the cursor is what sends our command and reads the answer.
    cursor = connection.cursor()
    try:
        # Step 3: run the command. MySQL puts each value into its %s blank.
        cursor.execute(sql, values)
        # Step 4: read the answer (only SELECT sends rows back).
        if fetch == "one":
            answer = cursor.fetchone()      # one row, like (5, "BEV-002", "C2 Green Tea", "Beverages", 30.00, 5)
        elif fetch == "all":
            answer = cursor.fetchall()      # a list of rows
        else:
            answer = None
        # Step 5: save the change for good. Without commit, INSERT / UPDATE / DELETE would be lost.
        connection.commit()
        return answer
    finally:
        # Step 6: always close the connection, even if there was an error.
        cursor.close()
        connection.close()


# Make the database and its two tables the first time the program runs.
# "IF NOT EXISTS" = make it only if it isn't there yet, so running the program again causes no error.
def setup_database():
    run_sql("CREATE DATABASE IF NOT EXISTS " + DB_NAME, use_database=False)

    # Table 1: products. One row = one product.
    run_sql("""CREATE TABLE IF NOT EXISTS products (
               id INT AUTO_INCREMENT PRIMARY KEY,     -- 1, 2, 3... MySQL numbers each product by itself
               code VARCHAR(20) NOT NULL UNIQUE,      -- like SNK-001. UNIQUE = no two products can share it
               name VARCHAR(100) NOT NULL,            -- NOT NULL = must not be empty
               category VARCHAR(60) NOT NULL,         -- like Snacks
               price DECIMAL(10, 2) NOT NULL,         -- money with exactly 2 decimals, like 19.75
               quantity INT NOT NULL                  -- INT = whole number: pieces in stock
           )""")

    # Table 2: users. One row = one login account.
    run_sql("""CREATE TABLE IF NOT EXISTS users (
               user_id INT AUTO_INCREMENT PRIMARY KEY,   -- 1, 2, 3...
               username VARCHAR(50) NOT NULL UNIQUE,     -- no two users with the same username
               password_salt CHAR(32) NOT NULL,          -- random letters mixed into the password
               password_hash CHAR(64) NOT NULL           -- the scrambled password (never the real one)
           )""")

    # No users yet? Make the first account: admin / admin123 (saved as a hash, not as plain text).
    # COUNT(*) = how many rows the table has.
    user_count = run_sql("SELECT COUNT(*) FROM users", fetch="one")[0]
    if user_count == 0:
        salt = new_salt()
        run_sql("INSERT INTO users (username, password_salt, password_hash) VALUES (%s, %s, %s)",
                ("admin", salt, hash_password("admin123", salt)))
