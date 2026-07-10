import sqlite3
import random
from datetime import date, timedelta

DB_PATH = "sales.db"

CUSTOMERS = [
    ("Acme Retail", "Frankfurt"), ("Nordwind GmbH", "Hamburg"),
    ("Rheinbau AG", "Cologne"), ("Bavaria Foods", "Munich"),
    ("Alster Logistics", "Hamburg"), ("Main Valley Traders", "Frankfurt"),
    ("Ruhr Industrial", "Essen"), ("Elbe Consulting", "Dresden"),
]

PRODUCTS = [
    ("Widget A", "Hardware", 19.99), ("Widget B", "Hardware", 29.99),
    ("Service Plan Basic", "Services", 49.00), ("Service Plan Pro", "Services", 99.00),
    ("Gadget X", "Electronics", 149.50), ("Gadget Y", "Electronics", 249.00),
    ("Consulting Hour", "Services", 120.00), ("Cloud Storage 1TB", "Software", 9.99),
]

def build():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS OrderItems;
    DROP TABLE IF EXISTS Orders;
    DROP TABLE IF EXISTS Products;
    DROP TABLE IF EXISTS Customers;
    CREATE TABLE Customers (CustomerId INTEGER PRIMARY KEY, Name TEXT NOT NULL, City TEXT NOT NULL);
    CREATE TABLE Products (ProductId INTEGER PRIMARY KEY, Name TEXT NOT NULL, Category TEXT NOT NULL, UnitPrice REAL NOT NULL);
    CREATE TABLE Orders (OrderId INTEGER PRIMARY KEY, CustomerId INTEGER NOT NULL, OrderDate TEXT NOT NULL, FOREIGN KEY (CustomerId) REFERENCES Customers(CustomerId));
    CREATE TABLE OrderItems (OrderItemId INTEGER PRIMARY KEY, OrderId INTEGER NOT NULL, ProductId INTEGER NOT NULL, Quantity INTEGER NOT NULL, FOREIGN KEY (OrderId) REFERENCES Orders(OrderId), FOREIGN KEY (ProductId) REFERENCES Products(ProductId));
    """)
    cur.executemany("INSERT INTO Customers (Name, City) VALUES (?, ?)", CUSTOMERS)
    cur.executemany("INSERT INTO Products (Name, Category, UnitPrice) VALUES (?, ?, ?)", PRODUCTS)
    random.seed(42)
    start = date(2025, 1, 1)
    order_id = 1
    for _ in range(300):
        customer_id = random.randint(1, len(CUSTOMERS))
        order_date = start + timedelta(days=random.randint(0, 550))
        cur.execute("INSERT INTO Orders (OrderId, CustomerId, OrderDate) VALUES (?, ?, ?)", (order_id, customer_id, order_date.isoformat()))
        for _ in range(random.randint(1, 4)):
            product_id = random.randint(1, len(PRODUCTS))
            quantity = random.randint(1, 10)
            cur.execute("INSERT INTO OrderItems (OrderId, ProductId, Quantity) VALUES (?, ?, ?)", (order_id, product_id, quantity))
        order_id += 1
    con.commit()
    con.close()
    print(f"Created {DB_PATH} with {len(CUSTOMERS)} customers, {len(PRODUCTS)} products, and {order_id - 1} orders.")

if __name__ == "__main__":
    build()
