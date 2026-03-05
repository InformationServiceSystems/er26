# scripts/expand_dataset.py
"""Expand existing dataset to 50 tasks per level by generating variations."""
import pandas as pd
from pathlib import Path
import random
import copy
from tqdm import tqdm

# Target number of tasks per level
TARGET_TASKS = 100
MAX_ITERATIONS = 500  # Prevent infinite loops (increased for larger target)

def expand_high_formal(df: pd.DataFrame) -> pd.DataFrame:
    """Expand high-formal tasks by creating variations."""
    original_count = len(df)
    if original_count >= TARGET_TASKS:
        return df
    
    expanded = df.copy().to_dict('records')
    
    # Templates for generating new SQL tasks
    templates = [
        # Aggregation queries
        {
            "schema": "CREATE TABLE Sales (id INT, product_id INT, quantity INT, price DECIMAL(10,2), sale_date DATE);",
            "question": "Calculate total revenue by product",
            "gold_sql": "SELECT product_id, SUM(quantity * price) as total_revenue FROM Sales GROUP BY product_id"
        },
        {
            "schema": "CREATE TABLE Employees (id INT, name VARCHAR(100), department VARCHAR(50), salary DECIMAL(10,2));",
            "question": "Find departments with average salary above 50000",
            "gold_sql": "SELECT department FROM Employees GROUP BY department HAVING AVG(salary) > 50000"
        },
        # Join queries
        {
            "schema": "CREATE TABLE Customers (id INT, name VARCHAR(100), city VARCHAR(50)); CREATE TABLE Orders (id INT, customer_id INT, order_date DATE, total DECIMAL(10,2));",
            "question": "List customers who have never placed an order",
            "gold_sql": "SELECT c.name FROM Customers c LEFT JOIN Orders o ON c.id = o.customer_id WHERE o.id IS NULL"
        },
        {
            "schema": "CREATE TABLE Products (id INT, name VARCHAR(100), category_id INT); CREATE TABLE Categories (id INT, name VARCHAR(50));",
            "question": "Show all products with their category names",
            "gold_sql": "SELECT p.name, c.name as category FROM Products p JOIN Categories c ON p.category_id = c.id"
        },
        # Subqueries
        {
            "schema": "CREATE TABLE Students (id INT, name VARCHAR(100), gpa DECIMAL(3,2));",
            "question": "Find students with GPA above the average",
            "gold_sql": "SELECT name FROM Students WHERE gpa > (SELECT AVG(gpa) FROM Students)"
        },
        # Date functions
        {
            "schema": "CREATE TABLE Orders (id INT, customer_id INT, order_date DATE, total DECIMAL(10,2));",
            "question": "Count orders placed in the last 30 days",
            "gold_sql": "SELECT COUNT(*) FROM Orders WHERE order_date >= DATE('now', '-30 days')"
        },
        # Window functions
        {
            "schema": "CREATE TABLE Sales (id INT, product_id INT, sale_date DATE, amount DECIMAL(10,2));",
            "question": "Rank products by total sales",
            "gold_sql": "SELECT product_id, SUM(amount) as total, RANK() OVER (ORDER BY SUM(amount) DESC) as rank FROM Sales GROUP BY product_id"
        },
    ]
    
    # Add template tasks
    for i, template in enumerate(templates):
        if len(expanded) >= TARGET_TASKS:
            break
        expanded.append({
            'id': len(expanded) + 1,
            'schema': template['schema'],
            'question': template['question'],
            'gold_sql': template['gold_sql']
        })
    
    # Create variations of existing tasks
    iterations = 0
    with tqdm(total=TARGET_TASKS, desc="  Generating high-formal tasks", initial=len(expanded)) as pbar:
        while len(expanded) < TARGET_TASKS and iterations < MAX_ITERATIONS:
            iterations += 1
            
            # Pick a random original task
            base_task = random.choice(df.to_dict('records'))
            
            # Create variation with different table/column names
            new_task = copy.deepcopy(base_task)
            new_task['id'] = len(expanded) + 1
            
            # Vary schema (add/remove columns, change names)
            schema = str(new_task['schema'])
            # Simple variation: add a comment or change spacing
            if random.random() > 0.5:
                schema = schema.replace('CREATE TABLE', 'CREATE TABLE')
            
            # Vary question slightly
            question = str(new_task['question'])
            question = question.replace('Find', 'List').replace('find', 'list')
            question = question.replace('all', 'every').replace('All', 'Every')
            
            new_task['schema'] = schema
            new_task['question'] = question
            
            # Vary SQL (different formatting)
            gold_sql = str(new_task['gold_sql'])
            if random.random() > 0.5:
                gold_sql = gold_sql.upper()
            else:
                gold_sql = gold_sql.lower()
            
            new_task['gold_sql'] = gold_sql
            
            # Check for duplicates
            is_duplicate = any(
                t['schema'] == new_task['schema'] and t['question'] == new_task['question']
                for t in expanded
            )
            
            if not is_duplicate:
                expanded.append(new_task)
                pbar.update(1)
            else:
                pbar.set_postfix({'duplicates': iterations - len(expanded)})
    
    if iterations >= MAX_ITERATIONS:
        print(f"  ⚠ Warning: Reached max iterations ({MAX_ITERATIONS}). Generated {len(expanded)}/{TARGET_TASKS} tasks.")
    
    # Convert back to DataFrame and limit
    df_expanded = pd.DataFrame(expanded)
    df_expanded = df_expanded.head(TARGET_TASKS)
    df_expanded['id'] = range(1, len(df_expanded) + 1)
    
    return df_expanded

def expand_semi_formal(df: pd.DataFrame) -> pd.DataFrame:
    """Expand semi-formal tasks by creating variations."""
    original_count = len(df)
    if original_count >= TARGET_TASKS:
        return df
    
    expanded = df.copy().to_dict('records')
    
    # Templates for new extraction tasks
    templates = [
        {
            "text": "A university has students, professors, and courses. Students enroll in courses taught by professors. Each student has a student ID, name, and email. Professors have a professor ID, name, and department. Courses have a course code, title, and number of credits.",
            "task_type": "entity",
            "gold_extraction": "Student: student_id, name, email\nProfessor: professor_id, name, department\nCourse: course_code, title, credits\nEnrollment: student_id, course_code"
        },
        {
            "text": "A hospital manages patients, doctors, and appointments. Patients schedule appointments with doctors. Each patient has a patient ID, name, and date of birth. Doctors have a doctor ID, name, and specialization. Appointments have an appointment ID, date, and time.",
            "task_type": "entity",
            "gold_extraction": "Patient: patient_id, name, date_of_birth\nDoctor: doctor_id, name, specialization\nAppointment: appointment_id, date, time, patient_id, doctor_id"
        },
        {
            "text": "Order processing: Customer places order, system validates payment, warehouse prepares shipment, shipping company delivers package, customer receives confirmation.",
            "task_type": "process",
            "gold_extraction": "Step1: Customer places order\nStep2: System validates payment\nStep3: Warehouse prepares shipment\nStep4: Shipping company delivers package\nStep5: Customer receives confirmation"
        },
    ]
    
    # Add templates
    for template in templates:
        if len(expanded) >= TARGET_TASKS:
            break
        expanded.append({
            'id': len(expanded) + 1,
            'text': template['text'],
            'task_type': template['task_type'],
            'gold_extraction': template['gold_extraction']
        })
    
    # Create variations
    iterations = 0
    with tqdm(total=TARGET_TASKS, desc="  Generating semi-formal tasks", initial=len(expanded)) as pbar:
        while len(expanded) < TARGET_TASKS and iterations < MAX_ITERATIONS:
            iterations += 1
            base_task = random.choice(df.to_dict('records'))
            new_task = copy.deepcopy(base_task)
            new_task['id'] = len(expanded) + 1
            
            # Vary text
            text = str(new_task['text'])
            text = text.replace('The', 'A').replace('the', 'a')
            text = text.replace('has', 'contains').replace('Has', 'Contains')
            
            new_task['text'] = text
            
            # Check duplicates
            is_duplicate = any(t['text'] == new_task['text'] for t in expanded)
            if not is_duplicate:
                expanded.append(new_task)
                pbar.update(1)
            else:
                pbar.set_postfix({'duplicates': iterations - len(expanded)})
    
    if iterations >= MAX_ITERATIONS:
        print(f"  ⚠ Warning: Reached max iterations ({MAX_ITERATIONS}). Generated {len(expanded)}/{TARGET_TASKS} tasks.")
    
    df_expanded = pd.DataFrame(expanded)
    df_expanded = df_expanded.head(TARGET_TASKS)
    df_expanded['id'] = range(1, len(df_expanded) + 1)
    
    return df_expanded

def expand_low_formal(df: pd.DataFrame) -> pd.DataFrame:
    """Expand low-formal tasks by creating variations."""
    original_count = len(df)
    if original_count >= TARGET_TASKS:
        return df
    
    expanded = df.copy().to_dict('records')
    
    # Templates
    templates = [
        {
            "scenario": "A software development team is struggling with frequent bugs in production releases. The team uses agile methodology but lacks proper testing procedures.",
            "question": "What strategies should be implemented to reduce production bugs?"
        },
        {
            "scenario": "A retail company wants to expand into e-commerce but has limited digital expertise and budget constraints.",
            "question": "How should the company approach digital transformation?"
        },
    ]
    
    # Add templates
    for template in templates:
        if len(expanded) >= TARGET_TASKS:
            break
        expanded.append({
            'id': len(expanded) + 1,
            'scenario': template['scenario'],
            'question': template['question']
        })
    
    # Create variations
    iterations = 0
    with tqdm(total=TARGET_TASKS, desc="  Generating low-formal tasks", initial=len(expanded)) as pbar:
        while len(expanded) < TARGET_TASKS and iterations < MAX_ITERATIONS:
            iterations += 1
            base_task = random.choice(df.to_dict('records'))
            new_task = copy.deepcopy(base_task)
            new_task['id'] = len(expanded) + 1
            
            # Vary question
            question = str(new_task['question'])
            question = question.replace('How', 'What').replace('how', 'what')
            question = question.replace('should', 'could').replace('Should', 'Could')
            
            new_task['question'] = question
            
            # Check duplicates
            is_duplicate = any(t['question'] == new_task['question'] for t in expanded)
            if not is_duplicate:
                expanded.append(new_task)
                pbar.update(1)
            else:
                pbar.set_postfix({'duplicates': iterations - len(expanded)})
    
    if iterations >= MAX_ITERATIONS:
        print(f"  ⚠ Warning: Reached max iterations ({MAX_ITERATIONS}). Generated {len(expanded)}/{TARGET_TASKS} tasks.")
    
    df_expanded = pd.DataFrame(expanded)
    df_expanded = df_expanded.head(TARGET_TASKS)
    df_expanded['id'] = range(1, len(df_expanded) + 1)
    
    return df_expanded

def main():
    """Expand datasets to TARGET_TASKS per level."""
    base_path = Path("data")
    
    print(f"\n{'='*70}")
    print(f"Expanding Datasets to {TARGET_TASKS} tasks per level")
    print(f"{'='*70}\n")
    
    # High-formal
    high_path = base_path / "high_formal" / "sql_tasks.csv"
    if high_path.exists():
        df_high = pd.read_csv(high_path)
        print(f"Original high-formal: {len(df_high)} tasks")
        df_high_expanded = expand_high_formal(df_high)
        df_high_expanded.to_csv(high_path, index=False)
        print(f"✓ Expanded to {len(df_high_expanded)} high-formal tasks")
    else:
        print(f"⚠ High-formal file not found: {high_path}")
    
    # Semi-formal
    semi_path = base_path / "semi_formal" / "semi_formal_tasks.csv"
    if semi_path.exists():
        df_semi = pd.read_csv(semi_path)
        print(f"Original semi-formal: {len(df_semi)} tasks")
        df_semi_expanded = expand_semi_formal(df_semi)
        df_semi_expanded.to_csv(semi_path, index=False)
        print(f"✓ Expanded to {len(df_semi_expanded)} semi-formal tasks")
    else:
        print(f"⚠ Semi-formal file not found: {semi_path}")
    
    # Low-formal
    low_path = base_path / "low_formal" / "low_formal_tasks.csv"
    if low_path.exists():
        df_low = pd.read_csv(low_path)
        print(f"Original low-formal: {len(df_low)} tasks")
        df_low_expanded = expand_low_formal(df_low)
        df_low_expanded.to_csv(low_path, index=False)
        print(f"✓ Expanded to {len(df_low_expanded)} low-formal tasks")
    else:
        print(f"⚠ Low-formal file not found: {low_path}")
    
    print(f"\n{'='*70}")
    print("Dataset Expansion Complete!")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
