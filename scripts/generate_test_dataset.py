# scripts/generate_test_dataset.py
"""Generate a larger, representative test dataset for all three formalization levels."""
import pandas as pd
from pathlib import Path
import json

# High-formal (SQL) tasks
HIGH_FORMAL_TASKS = [
    {
        "id": 1,
        "schema": "CREATE TABLE Customers (id INT, name VARCHAR(100), email VARCHAR(100)); CREATE TABLE Orders (id INT, customer_id INT, total DECIMAL(10,2));",
        "question": "Find all customers who have placed orders",
        "gold_sql": "SELECT DISTINCT c.name FROM Customers c JOIN Orders o ON c.id = o.customer_id"
    },
    {
        "id": 2,
        "schema": "CREATE TABLE Products (id INT, name VARCHAR(100), price DECIMAL(10,2));",
        "question": "List all products sorted by price",
        "gold_sql": "SELECT * FROM Products ORDER BY price ASC"
    },
    {
        "id": 3,
        "schema": "CREATE TABLE Employees (id INT, name VARCHAR(100), department VARCHAR(50), salary DECIMAL(10,2));",
        "question": "Find the average salary per department",
        "gold_sql": "SELECT department, AVG(salary) FROM Employees GROUP BY department"
    },
    {
        "id": 4,
        "schema": "CREATE TABLE Students (id INT, name VARCHAR(100), age INT); CREATE TABLE Courses (id INT, name VARCHAR(100)); CREATE TABLE Enrollments (student_id INT, course_id INT);",
        "question": "List all students enrolled in at least one course",
        "gold_sql": "SELECT DISTINCT s.name FROM Students s JOIN Enrollments e ON s.id = e.student_id"
    },
    {
        "id": 5,
        "schema": "CREATE TABLE Books (id INT, title VARCHAR(200), author VARCHAR(100), year INT);",
        "question": "Find all books published after 2020",
        "gold_sql": "SELECT * FROM Books WHERE year > 2020"
    },
    {
        "id": 6,
        "schema": "CREATE TABLE Orders (id INT, customer_id INT, order_date DATE, total DECIMAL(10,2));",
        "question": "Count the number of orders per customer",
        "gold_sql": "SELECT customer_id, COUNT(*) FROM Orders GROUP BY customer_id"
    },
    {
        "id": 7,
        "schema": "CREATE TABLE Products (id INT, name VARCHAR(100), category VARCHAR(50), price DECIMAL(10,2));",
        "question": "Find the most expensive product in each category",
        "gold_sql": "SELECT category, MAX(price) FROM Products GROUP BY category"
    },
    {
        "id": 8,
        "schema": "CREATE TABLE Employees (id INT, name VARCHAR(100), manager_id INT);",
        "question": "List all employees who are managers",
        "gold_sql": "SELECT e1.name FROM Employees e1 WHERE e1.id IN (SELECT manager_id FROM Employees WHERE manager_id IS NOT NULL)"
    },
    {
        "id": 9,
        "schema": "CREATE TABLE Customers (id INT, name VARCHAR(100), city VARCHAR(50)); CREATE TABLE Orders (id INT, customer_id INT, amount DECIMAL(10,2));",
        "question": "Find the total order amount for customers in each city",
        "gold_sql": "SELECT c.city, SUM(o.amount) FROM Customers c JOIN Orders o ON c.id = o.customer_id GROUP BY c.city"
    },
    {
        "id": 10,
        "schema": "CREATE TABLE Products (id INT, name VARCHAR(100), stock INT);",
        "question": "List products that are out of stock",
        "gold_sql": "SELECT * FROM Products WHERE stock = 0"
    },
]

# Semi-formal (Entity/Process) tasks
SEMI_FORMAL_TASKS = [
    {
        "id": 1,
        "text": "The university has students, professors, and courses. Each student has a student ID, name, and email. Professors have a professor ID, name, and department. Courses have a course code, title, and credits.",
        "task_type": "entity",
        "gold_extraction": "Student: student_id, name, email\nProfessor: professor_id, name, department\nCourse: course_code, title, credits"
    },
    {
        "id": 2,
        "text": "To enroll in a course, first check if the course has available seats. Then verify the student meets prerequisites. Next, add the student to the course roster and update the seat count. Finally, send a confirmation email.",
        "task_type": "process",
        "gold_extraction": "Step1: Check course availability\nStep2: Verify prerequisites\nStep3: Add student to roster\nStep4: Update seat count\nStep5: Send confirmation email"
    },
    {
        "id": 3,
        "text": "A library system manages books, members, and loans. Books have an ISBN, title, author, and publication year. Members have a member ID, name, and address. Loans record which member borrowed which book and when.",
        "task_type": "entity",
        "gold_extraction": "Book: ISBN, title, author, publication_year\nMember: member_id, name, address\nLoan: member_id, book_ISBN, loan_date"
    },
    {
        "id": 4,
        "text": "When processing a book return, first verify the book was actually borrowed. Then check if it's overdue and calculate any fines. Update the loan record to mark it as returned. Finally, update the book's availability status.",
        "task_type": "process",
        "gold_extraction": "Step1: Verify book was borrowed\nStep2: Check if overdue\nStep3: Calculate fines if applicable\nStep4: Update loan record\nStep5: Update book availability"
    },
    {
        "id": 5,
        "text": "An e-commerce platform has products, customers, and orders. Products have a product ID, name, description, and price. Customers have a customer ID, name, email, and shipping address. Orders contain order ID, customer ID, order date, and total amount.",
        "task_type": "entity",
        "gold_extraction": "Product: product_id, name, description, price\nCustomer: customer_id, name, email, shipping_address\nOrder: order_id, customer_id, order_date, total_amount"
    },
    {
        "id": 6,
        "text": "To process a new order, validate the customer information, check product availability, calculate the total price including taxes, create the order record, and send an order confirmation to the customer.",
        "task_type": "process",
        "gold_extraction": "Step1: Validate customer information\nStep2: Check product availability\nStep3: Calculate total with taxes\nStep4: Create order record\nStep5: Send order confirmation"
    },
    {
        "id": 7,
        "text": "A hospital system tracks patients, doctors, and appointments. Patients have a patient ID, name, date of birth, and medical record number. Doctors have a doctor ID, name, specialization, and license number. Appointments record the patient, doctor, date, and time.",
        "task_type": "entity",
        "gold_extraction": "Patient: patient_id, name, date_of_birth, medical_record_number\nDoctor: doctor_id, name, specialization, license_number\nAppointment: patient_id, doctor_id, appointment_date, appointment_time"
    },
    {
        "id": 8,
        "text": "When scheduling an appointment, first check the doctor's availability for the requested time slot. Then verify the patient's insurance coverage. Create the appointment record and send reminders to both the patient and doctor.",
        "task_type": "process",
        "gold_extraction": "Step1: Check doctor availability\nStep2: Verify patient insurance\nStep3: Create appointment record\nStep4: Send patient reminder\nStep5: Send doctor reminder"
    },
    {
        "id": 9,
        "text": "A restaurant management system handles menus, orders, and staff. Menu items have an item ID, name, description, category, and price. Orders contain order ID, table number, order time, and items ordered. Staff members have an employee ID, name, role, and shift schedule.",
        "task_type": "entity",
        "gold_extraction": "MenuItem: item_id, name, description, category, price\nOrder: order_id, table_number, order_time, items\nStaff: employee_id, name, role, shift_schedule"
    },
    {
        "id": 10,
        "text": "To handle a customer complaint, first listen to the customer's concerns and document them. Then investigate the issue by reviewing relevant records. Determine an appropriate resolution, implement it, and follow up with the customer to ensure satisfaction.",
        "task_type": "process",
        "gold_extraction": "Step1: Listen and document concerns\nStep2: Investigate the issue\nStep3: Determine resolution\nStep4: Implement resolution\nStep5: Follow up with customer"
    },
]

# Low-formal (Management/Policy) tasks
LOW_FORMAL_TASKS = [
    {
        "id": 1,
        "scenario": "A company is considering implementing a remote work policy. The management team needs to decide on guidelines for remote work eligibility, communication protocols, and performance evaluation.",
        "question": "What are the key considerations for developing a remote work policy?"
    },
    {
        "id": 2,
        "scenario": "A university department is reviewing its course evaluation process. Students currently provide feedback at the end of each semester, but the department wants to improve response rates and actionability of feedback.",
        "question": "How should the department redesign the course evaluation process to be more effective?"
    },
    {
        "id": 3,
        "scenario": "A small business is experiencing high employee turnover. The owner wants to understand the root causes and develop strategies to improve retention.",
        "question": "What factors should be investigated and what retention strategies could be implemented?"
    },
    {
        "id": 4,
        "scenario": "A hospital is implementing a new electronic health record system. Staff are resistant to change and there are concerns about patient data security and workflow disruption.",
        "question": "How should the hospital manage the transition to ensure successful adoption while maintaining security?"
    },
    {
        "id": 5,
        "scenario": "A retail chain wants to expand into online sales but is concerned about maintaining brand consistency, managing inventory across channels, and handling customer service.",
        "question": "What approach should the company take to successfully launch an online sales channel?"
    },
    {
        "id": 6,
        "scenario": "A nonprofit organization needs to improve its volunteer recruitment and retention. Current volunteers are aging out and younger volunteers are harder to attract.",
        "question": "What strategies could help attract and retain volunteers across different age groups?"
    },
    {
        "id": 7,
        "scenario": "A software company is transitioning from waterfall to agile development methodology. Some teams are struggling with the change and project timelines are becoming unpredictable.",
        "question": "How should the company manage this transition to improve team adaptation and project predictability?"
    },
    {
        "id": 8,
        "scenario": "A school district is facing budget cuts and needs to reduce costs while maintaining educational quality. Options include reducing staff, cutting programs, or increasing class sizes.",
        "question": "What factors should guide the decision-making process for budget reductions?"
    },
    {
        "id": 9,
        "scenario": "A manufacturing company wants to implement sustainable practices to reduce environmental impact and meet new regulations, but is concerned about costs and operational efficiency.",
        "question": "How can the company balance sustainability goals with cost and efficiency considerations?"
    },
    {
        "id": 10,
        "scenario": "A customer service department is receiving increasing complaints about response times and service quality. The team is understaffed and using outdated systems.",
        "question": "What improvements should be prioritized to address customer service issues?"
    },
]

def main():
    """Generate test datasets for all three formalization levels."""
    base_path = Path("data")
    
    # Create directories
    (base_path / "high_formal").mkdir(parents=True, exist_ok=True)
    (base_path / "semi_formal").mkdir(parents=True, exist_ok=True)
    (base_path / "low_formal").mkdir(parents=True, exist_ok=True)
    
    # Generate high-formal dataset
    df_high = pd.DataFrame(HIGH_FORMAL_TASKS)
    high_path = base_path / "high_formal" / "sql_tasks.csv"
    df_high.to_csv(high_path, index=False)
    print(f"✓ Generated {len(df_high)} high-formal tasks: {high_path}")
    
    # Generate semi-formal dataset
    df_semi = pd.DataFrame(SEMI_FORMAL_TASKS)
    semi_path = base_path / "semi_formal" / "semi_formal_tasks.csv"
    df_semi.to_csv(semi_path, index=False)
    print(f"✓ Generated {len(df_semi)} semi-formal tasks: {semi_path}")
    
    # Generate low-formal dataset
    df_low = pd.DataFrame(LOW_FORMAL_TASKS)
    low_path = base_path / "low_formal" / "low_formal_tasks.csv"
    df_low.to_csv(low_path, index=False)
    print(f"✓ Generated {len(df_low)} low-formal tasks: {low_path}")
    
    print(f"\n{'='*60}")
    print(f"Dataset Generation Complete")
    print(f"{'='*60}")
    print(f"Total tasks: {len(df_high) + len(df_semi) + len(df_low)}")
    print(f"  - High-formal (SQL): {len(df_high)} tasks")
    print(f"  - Semi-formal (Entity/Process): {len(df_semi)} tasks")
    print(f"  - Low-formal (Management/Policy): {len(df_low)} tasks")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

