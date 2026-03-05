# scripts/generate_large_dataset.py
"""Generate a large dataset (100 tasks per level) with more diverse variations."""
import pandas as pd
from pathlib import Path
import random
from tqdm import tqdm

TARGET_TASKS = 100

# High-formal SQL task templates
SQL_TEMPLATES = [
    # Basic SELECT
    ("CREATE TABLE Products (id INT, name VARCHAR(100), price DECIMAL(10,2));",
     "List all products", "SELECT * FROM Products"),
    ("CREATE TABLE Customers (id INT, name VARCHAR(100), email VARCHAR(100));",
     "Show all customer names", "SELECT name FROM Customers"),
    
    # WHERE clauses
    ("CREATE TABLE Products (id INT, name VARCHAR(100), price DECIMAL(10,2));",
     "Find products cheaper than 50", "SELECT * FROM Products WHERE price < 50"),
    ("CREATE TABLE Employees (id INT, name VARCHAR(100), age INT);",
     "List employees older than 30", "SELECT * FROM Employees WHERE age > 30"),
    
    # ORDER BY
    ("CREATE TABLE Products (id INT, name VARCHAR(100), price DECIMAL(10,2));",
     "List products sorted by price ascending", "SELECT * FROM Products ORDER BY price ASC"),
    ("CREATE TABLE Students (id INT, name VARCHAR(100), gpa DECIMAL(3,2));",
     "Show students ordered by GPA descending", "SELECT * FROM Students ORDER BY gpa DESC"),
    
    # GROUP BY and aggregations
    ("CREATE TABLE Sales (id INT, product_id INT, quantity INT, amount DECIMAL(10,2));",
     "Calculate total sales by product", "SELECT product_id, SUM(amount) FROM Sales GROUP BY product_id"),
    ("CREATE TABLE Employees (id INT, department VARCHAR(50), salary DECIMAL(10,2));",
     "Find average salary per department", "SELECT department, AVG(salary) FROM Employees GROUP BY department"),
    ("CREATE TABLE Orders (id INT, customer_id INT, total DECIMAL(10,2));",
     "Count orders per customer", "SELECT customer_id, COUNT(*) FROM Orders GROUP BY customer_id"),
    
    # JOINs
    ("CREATE TABLE Customers (id INT, name VARCHAR(100)); CREATE TABLE Orders (id INT, customer_id INT, total DECIMAL(10,2));",
     "List customers with their orders", "SELECT c.name, o.total FROM Customers c JOIN Orders o ON c.id = o.customer_id"),
    ("CREATE TABLE Products (id INT, name VARCHAR(100), category_id INT); CREATE TABLE Categories (id INT, name VARCHAR(50));",
     "Show products with category names", "SELECT p.name, c.name FROM Products p JOIN Categories c ON p.category_id = c.id"),
    
    # DISTINCT
    ("CREATE TABLE Orders (id INT, customer_id INT, product_id INT);",
     "Find unique customers who ordered", "SELECT DISTINCT customer_id FROM Orders"),
    
    # HAVING
    ("CREATE TABLE Sales (id INT, product_id INT, amount DECIMAL(10,2));",
     "Find products with total sales over 1000", "SELECT product_id, SUM(amount) FROM Sales GROUP BY product_id HAVING SUM(amount) > 1000"),
    
    # Subqueries
    ("CREATE TABLE Employees (id INT, name VARCHAR(100), salary DECIMAL(10,2));",
     "Find employees earning above average", "SELECT name FROM Employees WHERE salary > (SELECT AVG(salary) FROM Employees)"),
    
    # LEFT JOIN
    ("CREATE TABLE Customers (id INT, name VARCHAR(100)); CREATE TABLE Orders (id INT, customer_id INT);",
     "List customers including those without orders", "SELECT c.name FROM Customers c LEFT JOIN Orders o ON c.id = o.customer_id"),
]

# Semi-formal extraction templates
EXTRACTION_TEMPLATES = [
    # Entity extraction
    ("A library system manages books, members, and loans. Books have ISBN, title, and author. Members have ID, name, and email. Loans track which member borrowed which book.",
     "entity",
     "Book: ISBN, title, author\nMember: ID, name, email\nLoan: member_ID, book_ISBN, loan_date"),
    
    ("An online store has products, customers, and orders. Products have SKU, name, and price. Customers have ID, name, and address. Orders link customers to products.",
     "entity",
     "Product: SKU, name, price\nCustomer: ID, name, address\nOrder: order_ID, customer_ID, product_SKU, quantity"),
    
    # Process extraction
    ("Customer registration: User fills form, system validates email, sends confirmation, user clicks link, account activated.",
     "process",
     "Step1: User fills registration form\nStep2: System validates email\nStep3: System sends confirmation email\nStep4: User clicks confirmation link\nStep5: Account activated"),
    
    ("Order fulfillment: Customer places order, payment processed, warehouse picks items, items packed, shipping label created, package shipped.",
     "process",
     "Step1: Customer places order\nStep2: Payment processed\nStep3: Warehouse picks items\nStep4: Items packed\nStep5: Shipping label created\nStep6: Package shipped"),
]

# Low-formal management templates
MANAGEMENT_TEMPLATES = [
    ("A company is experiencing high employee turnover in the IT department. Exit interviews reveal concerns about work-life balance and limited career growth.",
     "What strategies should management implement to improve retention?"),
    
    ("A retail business wants to expand online but has limited digital expertise and a tight budget.",
     "How should the company approach digital transformation?"),
    
    ("A manufacturing plant is facing quality control issues with 15% defect rate. Current inspection is manual and inconsistent.",
     "What improvements should be prioritized?"),
]

def generate_variations(template, num_variations, task_type="sql"):
    """Generate variations of a template."""
    variations = []
    
    if task_type == "sql":
        schema, question, sql = template
        
        # Generate variations
        for i in range(num_variations):
            var_question = question
            var_sql = sql
            
            # Vary question wording
            replacements = [
                ("List", "Show"), ("Find", "Get"), ("all", "every"),
                ("Calculate", "Compute"), ("total", "sum")
            ]
            for old, new in replacements:
                if random.random() > 0.5:
                    var_question = var_question.replace(old, new)
            
            # Vary SQL formatting
            if random.random() > 0.5:
                var_sql = var_sql.upper()
            else:
                var_sql = var_sql.lower()
            
            variations.append({
                'schema': schema,
                'question': var_question,
                'gold_sql': var_sql
            })
    
    elif task_type == "extraction":
        text, task_subtype, gold = template
        
        for i in range(num_variations):
            var_text = text
            
            # Vary text wording
            replacements = [
                ("has", "contains"), ("manages", "handles"),
                ("tracks", "records"), ("system", "platform")
            ]
            for old, new in replacements:
                if random.random() > 0.5:
                    var_text = var_text.replace(old, new)
            
            variations.append({
                'text': var_text,
                'task_type': task_subtype,
                'gold_extraction': gold
            })
    
    elif task_type == "management":
        scenario, question = template
        
        for i in range(num_variations):
            var_question = question
            
            # Vary question wording
            replacements = [
                ("should", "could"), ("What", "Which"),
                ("How", "In what way"), ("implement", "apply")
            ]
            for old, new in replacements:
                if random.random() > 0.5:
                    var_question = var_question.replace(old, new)
            
            variations.append({
                'scenario': scenario,
                'question': var_question
            })
    
    return variations

def main():
    """Generate large dataset."""
    print(f"\n{'='*70}")
    print(f"Generating Large Dataset: {TARGET_TASKS} tasks per level")
    print(f"{'='*70}\n")
    
    base_path = Path("data")
    
    # High-formal
    print("Generating high-formal (SQL) tasks...")
    high_tasks = []
    tasks_per_template = TARGET_TASKS // len(SQL_TEMPLATES) + 1
    
    with tqdm(total=TARGET_TASKS, desc="  High-formal") as pbar:
        for template in SQL_TEMPLATES:
            variations = generate_variations(template, tasks_per_template, "sql")
            for var in variations:
                if len(high_tasks) >= TARGET_TASKS:
                    break
                high_tasks.append(var)
                pbar.update(1)
    
    df_high = pd.DataFrame(high_tasks[:TARGET_TASKS])
    df_high['id'] = range(1, len(df_high) + 1)
    high_path = base_path / "high_formal" / "sql_tasks.csv"
    df_high.to_csv(high_path, index=False)
    print(f"✓ Generated {len(df_high)} high-formal tasks")
    
    # Semi-formal
    print("\nGenerating semi-formal (extraction) tasks...")
    semi_tasks = []
    tasks_per_template = TARGET_TASKS // len(EXTRACTION_TEMPLATES) + 1
    
    with tqdm(total=TARGET_TASKS, desc="  Semi-formal") as pbar:
        for template in EXTRACTION_TEMPLATES:
            variations = generate_variations(template, tasks_per_template, "extraction")
            for var in variations:
                if len(semi_tasks) >= TARGET_TASKS:
                    break
                semi_tasks.append(var)
                pbar.update(1)
    
    df_semi = pd.DataFrame(semi_tasks[:TARGET_TASKS])
    df_semi['id'] = range(1, len(df_semi) + 1)
    semi_path = base_path / "semi_formal" / "semi_formal_tasks.csv"
    df_semi.to_csv(semi_path, index=False)
    print(f"✓ Generated {len(df_semi)} semi-formal tasks")
    
    # Low-formal
    print("\nGenerating low-formal (management) tasks...")
    low_tasks = []
    tasks_per_template = TARGET_TASKS // len(MANAGEMENT_TEMPLATES) + 1
    
    with tqdm(total=TARGET_TASKS, desc="  Low-formal") as pbar:
        for template in MANAGEMENT_TEMPLATES:
            variations = generate_variations(template, tasks_per_template, "management")
            for var in variations:
                if len(low_tasks) >= TARGET_TASKS:
                    break
                low_tasks.append(var)
                pbar.update(1)
    
    df_low = pd.DataFrame(low_tasks[:TARGET_TASKS])
    df_low['id'] = range(1, len(df_low) + 1)
    low_path = base_path / "low_formal" / "low_formal_tasks.csv"
    df_low.to_csv(low_path, index=False)
    print(f"✓ Generated {len(df_low)} low-formal tasks")
    
    print(f"\n{'='*70}")
    print("Dataset Generation Complete!")
    print(f"{'='*70}")
    print(f"Total: {len(df_high) + len(df_semi) + len(df_low)} tasks")
    print(f"  - High-formal: {len(df_high)}")
    print(f"  - Semi-formal: {len(df_semi)}")
    print(f"  - Low-formal: {len(df_low)}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()

