from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
import re
import random
from datetime import datetime,timedelta
from functools import wraps
from reportlab.pdfgen import canvas
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import uuid
from PyPDF2 import PdfMerger 
from reportlab.lib.pagesizes import letter 
from PIL import Image   


app = Flask(__name__)
app.secret_key = 'hospital_secret_key'

# =========================
# ROLE REQUIRED DECORATOR
# =========================
def role_required(required_role):

    def decorator(f):

        @wraps(f)
        def decorated_function(*args, **kwargs):

            # USER NOT LOGGED IN
            if 'user' not in session:
                flash('Please Login First')
                return redirect(url_for('login'))

            # WRONG ROLE
            if session.get('role') != required_role:
                flash('Unauthorized Access')
                return redirect(url_for('login'))

            return f(*args, **kwargs)

        return decorated_function

    return decorator

# =========================
# UPLOAD FOLDERS
# =========================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
EMR_FOLDER = os.path.join(BASE_DIR, 'static', 'emr_files')
LAB_REPORT_FOLDER = os.path.join(BASE_DIR, 'static', 'lab_reports')
CONSULTATION_FOLDER = os.path.join(BASE_DIR, 'static', 'consultations')

# Create folders automatically if missing
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EMR_FOLDER, exist_ok=True)
os.makedirs(LAB_REPORT_FOLDER, exist_ok=True)
os.makedirs(CONSULTATION_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['EMR_FOLDER'] = EMR_FOLDER
app.config['LAB_REPORT_FOLDER'] = LAB_REPORT_FOLDER
app.config['CONSULTATION_FOLDER'] = CONSULTATION_FOLDER

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'hospital.db')

# =========================
# SECRET KEYS
# =========================
ROLE_KEYS = {
    'Admin': 'HMS-ADMIN-cls2026',
    'Doctor': 'HMS-DOCTOR-2026',
    'Nurse': 'HMS-NURSE-2026',
    'Receptionist': 'HMS-RECEPTION-2026',
    'Lab Technician': 'HMS-LAB-2026',
    'Pharmacist': 'HMS-PHARMA-2026'
}

# =========================
# FILE VALIDATION
# =========================
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):

    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# =========================
# DATABASE
# =========================
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            username TEXT UNIQUE,
            email TEXT,
            password_hash TEXT,
            role TEXT,
            secret_key TEXT,
            image_path TEXT
        )
    ''')

    # PATIENT TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT UNIQUE,
            full_name TEXT,
            age INTEGER,
            gender TEXT,
            phone TEXT,
            address TEXT,
            blood_group TEXT,
            disease TEXT,
            doctor_assigned TEXT,
            admission_type TEXT,
            admission_date TEXT,
            discharge_date TEXT,
            emergency_contact TEXT,
            insurance_provider TEXT,
            insurance_number TEXT,
            medical_history TEXT
        )
    ''')

    # DOCTOR TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id TEXT UNIQUE,
            doctor_name TEXT,
            department TEXT,
            specialization TEXT,
            phone TEXT,
            email TEXT,
            availability TEXT,
            room_number TEXT,
            experience TEXT,
            joining_date TEXT
        )
    ''')

    # APPOINTMENT TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id TEXT UNIQUE,
            token_number TEXT,
            patient_id TEXT,
            patient_name TEXT,
            doctor_name TEXT,
            appointment_date TEXT,
            appointment_time TEXT,
            status TEXT,
            prescription TEXT,
            notification TEXT,
            diagnosis TEXT,
            lab_test TEXT,
            medical_history TEXT,
            doctor_pdf TEXT,
            follow_up_from TEXT
        )
    ''')
        
    # EMR TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emr_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            doctor_name TEXT,
            diagnosis_history TEXT,
            treatment_history TEXT,
            prescriptions TEXT,
            allergies TEXT,
            reports TEXT,
            xray_mri_path TEXT,
            created_at TEXT
        )
    ''')

    # =========================
    # FIX BILLING TABLE
    # =========================

    # Delete old billing table if broken
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT UNIQUE,
            patient_id TEXT,
            patient_name TEXT,
            treatment_cost REAL,
            medicine_cost REAL,
            room_charges REAL,
            gst_percentage REAL,
            gst_amount REAL,
            total_amount REAL,
            insurance_claim TEXT,
            insurance_status TEXT,
            payment_method TEXT,
            payment_status TEXT,
            refund_status TEXT,
            invoice_date TEXT
        )
        """)
   

    
    # =========================
    # LABORATORY TABLE
    # =========================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS laboratory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id TEXT UNIQUE,
            patient_id TEXT,
            patient_name TEXT,
            test_name TEXT,
            doctor_name TEXT,
            booking_date TEXT,
            test_date TEXT,
            test_status TEXT,
            result_status TEXT,
            technician_name TEXT,
            report_file TEXT,
            remarks TEXT
        )
    ''')

    # =========================
    # PHARMACY TABLE
    # =========================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pharmacy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id TEXT UNIQUE,
            medicine_name TEXT,
            category TEXT,
            supplier TEXT,
            stock_quantity INTEGER,
            price REAL,
            expiry_date TEXT,
            manufacture_date TEXT,
            alert_level INTEGER,
            added_date TEXT
        )
    ''')

    # =========================
    # PHARMACY SALES TABLE
    # =========================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pharmacy_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id TEXT UNIQUE,
            patient_id TEXT,
            patient_name TEXT,
            medicine_name TEXT,
            quantity INTEGER,
            total_price REAL,
            prescription TEXT,
            sale_date TEXT
        )
    ''')
    # =========================
    # WARD & BED MANAGEMENT
    # =========================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_id TEXT UNIQUE,
            patient_id TEXT,
            patient_name TEXT,
            ward_type TEXT,
            room_number TEXT,
            bed_number TEXT,
            admission_status TEXT,
            icu_required TEXT,
            admission_date TEXT,
            discharge_date TEXT
        )
    ''')

    # =========================
    # STAFF ATTENDANCE TABLE
    # =========================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attendance_id TEXT UNIQUE,
            employee_name TEXT,
            employee_role TEXT,
            attendance_date TEXT,
            check_in TEXT,
            check_out TEXT,
            status TEXT
        )
    ''')

    # =========================
    # PAYROLL TABLE
    # =========================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payroll_id TEXT UNIQUE,
            employee_name TEXT,
            employee_role TEXT,
            basic_salary REAL,
            bonus REAL,
            deductions REAL,
            net_salary REAL,
            payment_status TEXT,
            payment_date TEXT
        )
    ''')

    # =========================
    # LEAVE MANAGEMENT TABLE
    # =========================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leaves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            leave_id TEXT UNIQUE,
            employee_name TEXT,
            employee_role TEXT,
            leave_type TEXT,
            start_date TEXT,
            end_date TEXT,
            reason TEXT,
            approval_status TEXT
        )
    ''')

    # =========================
    # SHIFT SCHEDULING TABLE
    # =========================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_id TEXT UNIQUE,
            employee_name TEXT,
            employee_role TEXT,
            shift_date TEXT,
            shift_time TEXT,
            department TEXT
        )
    ''')

        # =========================
    # INVENTORY MANAGEMENT
    # =========================

    # EQUIPMENT TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT UNIQUE,
            equipment_name TEXT,
            category TEXT,
            department TEXT,
            quantity INTEGER,
            condition_status TEXT,
            purchase_date TEXT,
            warranty_expiry TEXT,
            equipment_status TEXT,
            added_date TEXT
        )
    ''')

    # VENDOR TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id TEXT UNIQUE,
            vendor_name TEXT,
            company_name TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            supplied_items TEXT,
            created_at TEXT
        )
    ''')

    # PURCHASE ORDERS TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE,
            vendor_name TEXT,
            equipment_name TEXT,
            quantity INTEGER,
            unit_price REAL,
            total_price REAL,
            order_status TEXT,
            order_date TEXT,
            delivery_date TEXT
        )
    ''')

    # MAINTENANCE LOGS TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maintenance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maintenance_id TEXT UNIQUE,
            equipment_name TEXT,
            engineer_name TEXT,
            maintenance_type TEXT,
            maintenance_date TEXT,
            next_service_date TEXT,
            remarks TEXT,
            status TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT UNIQUE,
            report_type TEXT,
            generated_by TEXT,
            generated_date TEXT,
            total_revenue REAL,
            total_patients INTEGER,
            total_doctors INTEGER,
            emergency_cases INTEGER,
            top_disease TEXT,
            top_doctor TEXT,
            remarks TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS laboratory_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id TEXT,
            patient_id TEXT,
            report_name TEXT,
            file_name TEXT,
            status TEXT DEFAULT 'Pending',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shared_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            doctor_name TEXT,
            report_name TEXT,
            file_name TEXT,
            shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
        

    conn.commit()
    

init_db()

# =========================
# GENERATE IDS
# =========================
def generate_patient_id():
    return "PAT" + str(random.randint(10000, 99999))

def generate_doctor_id():
    return "DOC" + str(random.randint(10000, 99999))

def generate_appointment_id():
    return "APT" + str(random.randint(10000, 99999))

def generate_token():
    return "TK" + str(random.randint(100, 999))

def generate_invoice_id():
    return "INV" + str(random.randint(10000, 99999))
def generate_test_id():
    return "LAB" + str(random.randint(10000, 99999))

def generate_medicine_id():
    return "MED" + str(random.randint(10000, 99999))

def generate_sale_id():
    return "SAL" + str(random.randint(10000, 99999))

def generate_ward_id():
    return "WRD" + str(random.randint(10000, 99999))

def generate_attendance_id():
    return "ATT" + str(random.randint(10000, 99999))

def generate_payroll_id():
    return "PAY" + str(random.randint(10000, 99999))

def generate_leave_id():
    return "LEV" + str(random.randint(10000, 99999))

def generate_shift_id():
    return "SHF" + str(random.randint(10000, 99999))

def generate_equipment_id():
    return "EQP" + str(random.randint(10000, 99999))

def generate_vendor_id():
    return "VND" + str(random.randint(10000, 99999))

def generate_order_id():
    return "ORD" + str(random.randint(10000, 99999))

def generate_maintenance_id():
    return "MNT" + str(random.randint(10000, 99999))

def generate_report_id():
    return "RPT" + str(random.randint(10000, 99999))


# =========================
# HOME
# =========================
@app.route('/')
def home():
    return redirect(url_for('login'))
# =========================
# LOGIN
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        entered_key = request.form.get('secret_key', '')

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT *
            FROM users
            WHERE username=? AND role=?
        ''', (username, role))

        user = cursor.fetchone()

        conn.close()

        if user:

            stored_password = user[4]
            stored_key = user[6]

            # PASSWORD CHECK
            if check_password_hash(stored_password, password):

                # =========================
                # ADMIN LOGIN
                # =========================
                if role == 'Admin':

                    if entered_key != stored_key:
                        flash('Invalid Admin Secret Key')
                        return redirect(url_for('login'))

                    session['user'] = username
                    session['role'] = role
                    session['image'] = user[7]

                    return redirect(url_for('dashboard'))

                # =========================
                # DOCTOR LOGIN
                # =========================
                elif role == 'Doctor':

                    if entered_key != stored_key:
                        flash('Invalid Doctor Secret Key')
                        return redirect(url_for('login'))

                    session['user'] = username
                    session['role'] = role
                    session['image'] = user[7]

                    return redirect(url_for('doctor_portal'))

                # =========================
                # NURSE LOGIN
                # =========================
                elif role == 'Nurse':

                    if entered_key != stored_key:
                        flash('Invalid Nurse Secret Key')
                        return redirect(url_for('login'))

                    session['user'] = username
                    session['role'] = role
                    session['image'] = user[7]

                    return redirect(url_for('nurse_portal'))

                # =========================
                # RECEPTIONIST LOGIN
                # =========================
                elif role == 'Receptionist':

                    if entered_key != stored_key:
                        flash('Invalid Receptionist Secret Key')
                        return redirect(url_for('login'))

                    session['user'] = username
                    session['role'] = role
                    session['image'] = user[7]

                    return redirect(url_for('receptionist_portal'))

                # =========================
                # LAB TECHNICIAN LOGIN
                # =========================
                elif role == 'Lab Technician':

                    if entered_key != stored_key:
                        flash('Invalid Lab Technician Secret Key')
                        return redirect(url_for('login'))

                    session['user'] = username
                    session['role'] = role
                    session['image'] = user[7]

                    return redirect(url_for('lab_technician_portal'))

                # =========================
                # PHARMACIST LOGIN
                # =========================
                elif role == 'Pharmacist':

                    if entered_key != stored_key:
                        flash('Invalid Pharmacist Secret Key')
                        return redirect(url_for('login'))

                    session['user'] = username
                    session['role'] = role
                    session['image'] = user[7]

                    return redirect(url_for('pharmacist_portal'))

                # =========================
                # PATIENT LOGIN
                # =========================
                elif role == 'Patient':

                    session['user'] = username
                    session['role'] = role
                    session['image'] = user[7]

                    return redirect(url_for('patient_portal'))

        # IMPORTANT
        flash('Invalid Credentials')
        return redirect(url_for('login'))

    return render_template('login.html')

# =========================
# SIGNUP
# =========================
@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']

        allowed_roles = [
            'Admin',
            'Doctor',
            'Nurse',
            'Receptionist',
            'Lab Technician',
            'Pharmacist',
            'Patient'
        ]

        if role not in allowed_roles:
            flash('Invalid Role Selected')
            return redirect(url_for('signup'))

        image = request.files['image']

        gmail_pattern = r'^[a-zA-Z0-9._%+-]+@gmail\.com$'

        if not re.match(gmail_pattern, email):
            flash('Only Gmail accounts allowed')
            return redirect(url_for('signup'))

        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('signup'))
        
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('signup'))

        # PASSWORD VALIDATION
        if len(password) < 6:
            flash('Password must be at least 6 characters long')
            return redirect(url_for('signup'))

        if not re.search(r'[A-Z]', password):
            flash('Password must contain at least one uppercase letter')
            return redirect(url_for('signup'))

        if not re.search(r'[a-z]', password):
            flash('Password must contain at least one lowercase letter')
            return redirect(url_for('signup'))

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            flash('Password must contain at least one special character')
            return redirect(url_for('signup'))

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM users WHERE username=?',
            (username,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            flash('Username already exists')
            conn.close()
            return redirect(url_for('signup'))

        filename = secure_filename(image.filename)

        image_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            filename
        )

        image.save(image_path)

        hashed_password = generate_password_hash(password)

        secret_key = ''

        if role != 'Patient':
            secret_key = ROLE_KEYS.get(role, '')

        cursor.execute('''
            INSERT INTO users (
                full_name,
                username,
                email,
                password_hash,
                role,
                secret_key,
                image_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            full_name,
            username,
            email,
            hashed_password,
            role,
            secret_key,
            image_path
        ))

        # =========================
        # AUTO CREATE PATIENT
        # =========================
        if role == 'Patient':

            patient_id = generate_patient_id()

            cursor.execute('''
                INSERT INTO patients (
                    patient_id,
                    full_name,
                    age,
                    gender,
                    phone,
                    address,
                    blood_group,
                    disease,
                    doctor_assigned,
                    admission_type,
                    admission_date,
                    discharge_date,
                    emergency_contact,
                    insurance_provider,
                    insurance_number,
                    medical_history
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_id,
                full_name,
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                ''
            ))
        
        # =========================
        # AUTO CREATE DOCTOR PROFILE
        # =========================
        if role == 'Doctor':

            doctor_id = generate_doctor_id()

            cursor.execute('''
                INSERT INTO doctors (

                    doctor_id,
                    doctor_name,
                    department,
                    specialization,
                    phone,
                    email,
                    availability,
                    room_number,
                    experience,
                    joining_date

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (

                doctor_id,
                full_name,      # user's full name from signup form
                '',
                '',
                '',
                username,       # email/username
                '',
                '',
                '',
                datetime.now().strftime('%Y-%m-%d')

            ))
            

        conn.commit()
        conn.close()

        flash('Account Created Successfully')

        return redirect(url_for('login'))

    return render_template('signup.html')

# =========================
# DASHBOARD
# =========================
@app.route('/dashboard')
@role_required('Admin')
def dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM patients")
    total_patients = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM doctors")
    total_doctors = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM emr_records")
    total_emr = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM billing")
    total_bills = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM patients WHERE admission_type='Emergency'"
    )
    emergency_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM laboratory")
    total_lab_tests = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pharmacy")
    total_medicines = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pharmacy_sales")
    total_sales = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM wards")
    total_wards = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM wards
        WHERE icu_required='Yes'
        AND admission_status='Admitted'
    """)
    total_icu = cursor.fetchone()[0]  

    cursor.execute("SELECT COUNT(*) FROM attendance")
    total_attendance = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM payroll")
    total_payroll = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leaves")
    total_leaves = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM shifts")
    total_shifts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM equipment")
    total_equipment = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM vendors")
    total_vendors = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM purchase_orders")
    total_orders = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM maintenance_logs")
    total_maintenance = cursor.fetchone()[0]


    cursor.execute("""
        SELECT SUM(total_amount)
        FROM billing
    """)

    revenue_data = cursor.fetchone()[0]

    total_revenue = revenue_data if revenue_data else 0

    cursor.execute("""
        SELECT disease, COUNT(*)
        FROM patients
        GROUP BY disease
        ORDER BY COUNT(*) DESC
        LIMIT 5
    """)

    disease_stats = cursor.fetchall()

    cursor.execute("""
        SELECT doctor_assigned, COUNT(*)
        FROM patients
        GROUP BY doctor_assigned
        ORDER BY COUNT(*) DESC
        LIMIT 5
    """)

    doctor_performance = cursor.fetchall()

    # =========================
    # GET ALL DOCTORS
    # =========================
    cursor.execute("""
        SELECT *
        FROM doctors
        ORDER BY doctor_name ASC
    """)

    doctors = cursor.fetchall()


    # =========================
    # GET DOCTOR ACTIVITIES
    # =========================
    cursor.execute("""
        SELECT *
        FROM emr_records
        ORDER BY created_at DESC
    """)

    emr_records = cursor.fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        username=session['user'],
        role=session['role'],
        image=session['image'],
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_appointments=total_appointments,
        total_emr=total_emr,
        total_bills=total_bills,
        emergency_count=emergency_count,
        total_lab_tests=total_lab_tests,
        total_medicines=total_medicines,
        total_sales=total_sales,
        total_wards=total_wards,
        total_icu=total_icu,
        total_attendance=total_attendance,
        total_payroll=total_payroll,
        total_leaves=total_leaves,
        total_shifts=total_shifts,
        total_equipment=total_equipment,
        total_vendors=total_vendors,
        total_orders=total_orders,
        total_maintenance=total_maintenance,
        total_revenue=total_revenue,
        disease_stats=disease_stats,
        doctor_performance=doctor_performance,
        doctors=doctors,
        emr_records=emr_records
    )

# =========================
# PATIENT DASHBOARD
# =========================
@app.route('/patient_dashboard')
def patient_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)

    # IMPORTANT
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            p.*,
            COUNT(e.id) AS total_emr
        FROM patients p
        LEFT JOIN emr_records e
        ON p.patient_id = e.patient_id
        GROUP BY p.patient_id
    """)

    patients = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM appointments
        ORDER BY appointment_date DESC
    """)

    appointments = cursor.fetchall()

    conn.close()

    return render_template(
        'patient_dashboard.html',
        patients=patients,
        appointments=appointments
    )

# =========================
# ADD PATIENT
# =========================
@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():

    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':

        patient_id = generate_patient_id()

        full_name = request.form['full_name']
        age = request.form['age']
        gender = request.form['gender']
        phone = request.form['phone']
        address = request.form['address']
        blood_group = request.form['blood_group']
        disease = request.form['disease']
        doctor_assigned = request.form['doctor_assigned']
        admission_type = request.form['admission_type']
        admission_date = request.form['admission_date']
        discharge_date = request.form['discharge_date']
        emergency_contact = request.form['emergency_contact']
        insurance_provider = request.form['insurance_provider']
        insurance_number = request.form['insurance_number']
        medical_history = request.form['medical_history']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO patients (
                patient_id,
                full_name,
                age,
                gender,
                phone,
                address,
                blood_group,
                disease,
                doctor_assigned,
                admission_type,
                admission_date,
                discharge_date,
                emergency_contact,
                insurance_provider,
                insurance_number,
                medical_history
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_id,
            full_name,
            age,
            gender,
            phone,
            address,
            blood_group,
            disease,
            doctor_assigned,
            admission_type,
            admission_date,
            discharge_date,
            emergency_contact,
            insurance_provider,
            insurance_number,
            medical_history
        ))

        conn.commit()
        conn.close()

        flash('Patient Added Successfully')

        return redirect(url_for('patient_dashboard'))

    return render_template('add_patient.html')

# =========================
# DOCTOR DASHBOARD
# =========================
@app.route('/doctor_dashboard')
def doctor_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM doctors")
    doctors = cursor.fetchall()

    conn.close()

    return render_template(
        'doctor_dashboard.html',
        doctors=doctors
    )

# =========================
# ADD DOCTOR
# =========================
@app.route('/add_doctor', methods=['GET', 'POST'])
def add_doctor():

    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':

        doctor_id = generate_doctor_id()

        doctor_name = request.form['doctor_name']
        department = request.form['department']
        specialization = request.form['specialization']
        phone = request.form['phone']
        email = request.form['email']
        availability = request.form['availability']
        room_number = request.form['room_number']
        experience = request.form['experience']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO doctors (
                doctor_id,
                doctor_name,
                department,
                specialization,
                phone,
                email,
                availability,
                room_number,
                experience
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            doctor_id,
            doctor_name,
            department,
            specialization,
            phone,
            email,
            availability,
            room_number,
            experience
        ))

        conn.commit()
        conn.close()

        flash('Doctor Added Successfully')

        return redirect(url_for('doctor_dashboard'))

    return render_template('add_doctor.html')

# =========================
# APPOINTMENTS
# =========================
@app.route('/appointments')
def appointments():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM appointments
        ORDER BY appointment_date DESC
    """)

    appointments = cursor.fetchall()

    conn.close()

    return render_template(
        'appointments.html',
        appointments=appointments
    )

# =========================
# ADD APPOINTMENT
# =========================
@app.route('/add_appointment', methods=['GET', 'POST'])
def add_appointment():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT doctor_name FROM doctors")
    doctors = cursor.fetchall()

    if request.method == 'POST':

        appointment_id = generate_appointment_id()
        token_number = generate_token()

        patient_name = request.form['patient_name']
        doctor_name = request.form['doctor_name']
        appointment_date = request.form['appointment_date']
        appointment_time = request.form['appointment_time']

        cursor.execute('''
            SELECT * FROM appointments
            WHERE doctor_name=?
            AND appointment_date=?
            AND appointment_time=?
            AND status!='Cancelled'
        ''', (
            doctor_name,
            appointment_date,
            appointment_time
        ))

        already_booked = cursor.fetchone()

        if already_booked:

            flash('Doctor already booked for this slot')

            conn.close()

            return redirect(url_for('add_appointment'))

        notification = f'''
Appointment Confirmed
Token Number : {token_number}
Doctor : {doctor_name}
Date : {appointment_date}
Time : {appointment_time}
'''

        cursor.execute('''
            INSERT INTO appointments (
                appointment_id,
                token_number,
                patient_name,
                doctor_name,
                appointment_date,
                appointment_time,
                status,
                prescription,
                notification
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            appointment_id,
            token_number,
            patient_name,
            doctor_name,
            appointment_date,
            appointment_time,
            'Booked',
            '',
            notification
        ))

        conn.commit()
        conn.close()

        flash('Appointment Booked Successfully')

        return redirect(url_for('appointments'))

    conn.close()

    return render_template(
        'add_appointment.html',
        doctors=doctors
    )

# =========================
# EMR
# =========================
@app.route('/emr/<patient_id>', methods=['GET', 'POST'])
def emr(patient_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM patients WHERE patient_id=?",
        (patient_id,)
    )

    patient = cursor.fetchone()

    if request.method == 'POST':

        diagnosis_history = request.form['diagnosis_history']
        treatment_history = request.form['treatment_history']
        prescriptions = request.form['prescriptions']
        allergies = request.form['allergies']
        reports = request.form['reports']

        file = request.files['xray_mri']

        file_path = ''

        if file and allowed_file(file.filename):

            filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"

            save_path = os.path.join(
                app.config['EMR_FOLDER'],
                filename
            )

            file.save(save_path)

            file_path = filename

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute('''
            INSERT INTO emr_records (
                patient_id,
                diagnosis_history,
                treatment_history,
                prescriptions,
                allergies,
                reports,
                xray_mri_path,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_id,
            diagnosis_history,
            treatment_history,
            prescriptions,
            allergies,
            reports,
            file_path,
            created_at
        ))

        conn.commit()
        conn.close()

        flash('EMR Record Added Successfully')

        return redirect(url_for('view_emr', patient_id=patient_id))

    conn.close()

    return render_template(
        'add_emr.html',
        patient=patient
    )

# =========================
# VIEW EMR
# =========================
@app.route('/view_emr/<patient_id>')
def view_emr(patient_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM patients WHERE patient_id=?",
        (patient_id,)
    )

    patient = cursor.fetchone()

    cursor.execute('''
        SELECT * FROM emr_records
        WHERE patient_id=?
        ORDER BY created_at DESC
    ''', (patient_id,))

    records = cursor.fetchall()

    conn.close()

    return render_template(
        'view_emr.html',
        patient=patient,
        records=records
    )
@app.route('/download_emr/<filename>')
def download_emr(filename):

    if 'user' not in session:
        return redirect(url_for('login'))

    full_path = os.path.join(
        app.config['EMR_FOLDER'],
        filename
    )

    print("Checking EMR:", full_path)

    if os.path.exists(full_path):

        return send_file(
            full_path,
            as_attachment=True
        )

    flash('EMR File Not Found')

    return redirect(url_for('patient_dashboard'))

# =========================
# BILLING DASHBOARD
# =========================
@app.route('/billing')
def billing_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM billing
        ORDER BY invoice_date DESC
    ''')

    bills = cursor.fetchall()

    conn.close()

    return render_template(
        'billing.html',
        bills=bills
    )

# =========================
# LAB DASHBOARD
# =========================
@app.route('/lab_dashboard')
def lab_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)

    # IMPORTANT
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM laboratory
        ORDER BY booking_date DESC
    ''')

    tests = cursor.fetchall()

    conn.close()

    return render_template(
        'lab_dashboard.html',
        tests=tests
    )

# =========================
# BOOK LAB TEST
# =========================
@app.route('/book_test', methods=['GET', 'POST'])
def book_test():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT patient_id, full_name FROM patients"
    )

    patients = cursor.fetchall()

    cursor.execute(
        "SELECT doctor_name FROM doctors"
    )

    doctors = cursor.fetchall()

    if request.method == 'POST':

        test_id = generate_test_id()

        patient_id = request.form['patient_id']
        patient_name = request.form['patient_name']

        test_name = request.form['test_name']
        doctor_name = request.form['doctor_name']

        test_date = request.form['test_date']

        technician_name = request.form['technician_name']

        booking_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute('''
            INSERT INTO laboratory (
                test_id,
                patient_id,
                patient_name,
                test_name,
                doctor_name,
                booking_date,
                test_date,
                test_status,
                result_status,
                technician_name,
                report_file,
                remarks
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            test_id,
            patient_id,
            patient_name,
            test_name,
            doctor_name,
            booking_date,
            test_date,
            'Booked',
            'Pending',
            technician_name,
            '',
            ''
        ))

        conn.commit()
        conn.close()

        flash('Lab Test Booked Successfully')

        return redirect(url_for('lab_dashboard'))

    conn.close()

    return render_template(
        'book_test.html',
        patients=patients,
        doctors=doctors
    )

# =========================
# UPLOAD LAB REPORT
# =========================
@app.route('/upload_report/<test_id>', methods=['GET', 'POST'])
def upload_report(test_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM laboratory WHERE test_id=?",
        (test_id,)
    )

    test = cursor.fetchone()

    if request.method == 'POST':

        remarks = request.form['remarks']

        file = request.files['report_file']

        file_path = ''

        if file and allowed_file(file.filename):

            filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"

            save_path = os.path.join(
                app.config['LAB_REPORT_FOLDER'],
                filename
            )

            file.save(save_path)

            # store only filename in database
            file_path = filename

        cursor.execute('''
            UPDATE laboratory
            SET report_file=?,
                remarks=?,
                result_status=?,
                test_status=?
            WHERE test_id=?
        ''', (
            file_path,
            remarks,
            'Completed',
            'Done',
            test_id
        ))

        conn.commit()
        conn.close()

        flash('Lab Report Uploaded Successfully')

        return redirect(url_for('lab_dashboard'))

    conn.close()

    return render_template(
        'upload_report.html',
        test=test
    )
# =========================
# DOWNLOAD LAB REPORT
# =========================
@app.route('/download_report/<test_id>')
def download_report(test_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT report_file
        FROM laboratory
        WHERE test_id=?
    ''', (test_id,))

    report = cursor.fetchone()

    conn.close()

    if report and report[0]:

        filename = report[0]

        full_path = os.path.join(
            app.config['LAB_REPORT_FOLDER'],
            filename
        )

        print("Checking path:", full_path)

        if os.path.exists(full_path):

            return send_file(
                full_path,
                as_attachment=True
            )

        else:
            print("FILE NOT FOUND")

    flash('Report File Not Found')

    return redirect(url_for('lab_dashboard'))

# =========================
# TRACK LAB RESULT
# =========================
@app.route('/track_results')
def track_results():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM laboratory
        ORDER BY booking_date DESC
    ''')

    results = cursor.fetchall()

    conn.close()

    return render_template(
        'track_results.html',
        results=results
    )

# =========================
# PHARMACY DASHBOARD
# =========================
@app.route('/pharmacy_dashboard')
def pharmacy_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM pharmacy
        ORDER BY added_date DESC
    ''')

    medicines = cursor.fetchall()

    conn.close()

    return render_template(
        'pharmacy_dashboard.html',
        medicines=medicines
    )

# =========================
# ADD MEDICINE
# =========================
@app.route('/add_medicine', methods=['GET', 'POST'])
def add_medicine():

    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':

        medicine_id = generate_medicine_id()

        medicine_name = request.form['medicine_name']
        category = request.form['category']
        supplier = request.form['supplier']

        stock_quantity = int(request.form['stock_quantity'])

        price = float(request.form['price'])

        expiry_date = request.form['expiry_date']
        manufacture_date = request.form['manufacture_date']

        alert_level = int(request.form['alert_level'])

        added_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO pharmacy (
                medicine_id,
                medicine_name,
                category,
                supplier,
                stock_quantity,
                price,
                expiry_date,
                manufacture_date,
                alert_level,
                added_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            medicine_id,
            medicine_name,
            category,
            supplier,
            stock_quantity,
            price,
            expiry_date,
            manufacture_date,
            alert_level,
            added_date
        ))

        conn.commit()
        conn.close()

        flash('Medicine Added Successfully')

        return redirect(url_for('pharmacy_dashboard'))

    return render_template('add_medicine.html')

# =========================
# SELL MEDICINE
# =========================
@app.route('/sell_medicine', methods=['GET', 'POST'])
def sell_medicine():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT medicine_name, stock_quantity, price
        FROM pharmacy
    ''')

    medicines = cursor.fetchall()

    cursor.execute('''
        SELECT patient_id, full_name
        FROM patients
    ''')

    patients = cursor.fetchall()

    if request.method == 'POST':

        sale_id = generate_sale_id()

        patient_id = request.form['patient_id']
        patient_name = request.form['patient_name']

        medicine_name = request.form['medicine_name']

        quantity = int(request.form['quantity'])

        prescription = request.form['prescription']

        cursor.execute('''
            SELECT stock_quantity, price
            FROM pharmacy
            WHERE medicine_name=?
        ''', (medicine_name,))

        medicine = cursor.fetchone()

        stock = medicine[0]
        price = medicine[1]

        if quantity > stock:

            flash('Insufficient Stock')

            conn.close()

            return redirect(url_for('sell_medicine'))

        total_price = quantity * price

        new_stock = stock - quantity

        cursor.execute('''
            UPDATE pharmacy
            SET stock_quantity=?
            WHERE medicine_name=?
        ''', (
            new_stock,
            medicine_name
        ))

        sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute('''
            INSERT INTO pharmacy_sales (
                sale_id,
                patient_id,
                patient_name,
                medicine_name,
                quantity,
                total_price,
                prescription,
                sale_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sale_id,
            patient_id,
            patient_name,
            medicine_name,
            quantity,
            total_price,
            prescription,
            sale_date
        ))

        conn.commit()
        conn.close()

        flash('Medicine Sold Successfully')

        return redirect(url_for('sales_dashboard'))

    conn.close()

    return render_template(
        'sell_medicine.html',
        medicines=medicines,
        patients=patients
    )

# =========================
# SALES DASHBOARD
# =========================
@app.route('/sales_dashboard')
def sales_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM pharmacy_sales
        ORDER BY sale_date DESC
    ''')

    sales = cursor.fetchall()

    conn.close()

    return render_template(
        'sales_dashboard.html',
        sales=sales
    )

# =========================
# LOW STOCK ALERTS
# =========================
@app.route('/stock_alerts')
def stock_alerts():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM pharmacy
        WHERE stock_quantity <= alert_level
    ''')

    alerts = cursor.fetchall()

    conn.close()

    return render_template(
        'stock_alerts.html',
        alerts=alerts
    )

# =========================
# EXPIRY TRACKING
# =========================
@app.route('/expiry_tracking')
def expiry_tracking():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM pharmacy
        ORDER BY expiry_date ASC
    ''')

    medicines = cursor.fetchall()

    conn.close()

    return render_template(
        'expiry_tracking.html',
        medicines=medicines
    )

# =========================
# DELETE MEDICINE
# =========================
@app.route('/delete_medicine/<int:id>')
def delete_medicine(id):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        'DELETE FROM pharmacy WHERE id=?',
        (id,)
    )

    conn.commit()
    conn.close()

    flash('Medicine Deleted Successfully')

    return redirect(url_for('pharmacy_dashboard'))

# =========================
# ADD BILL
# =========================
@app.route('/add_bill', methods=['GET', 'POST'])
def add_bill():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    selected_patient_id = request.args.get('patient_id', '')

    cursor.execute("SELECT patient_id, full_name FROM patients")
    patients = cursor.fetchall()

    selected_patient_name = ''
    patient = None

    if selected_patient_id:

        cursor.execute("""
            SELECT full_name
            FROM patients
            WHERE patient_id = ?
        """, (selected_patient_id,))

        patient = cursor.fetchone()

        if patient:
            selected_patient_name = patient[0]


    # POST block OUTSIDE
    if request.method == 'POST':

        invoice_id = generate_invoice_id()

        patient_id = request.form['patient_id']
        patient_name = request.form['patient_name']
        # Get appointment_id of this patient
        cursor.execute("""
            SELECT appointment_id,
                doctor_name
            FROM appointments
            WHERE patient_name = ?
            AND status = 'Waiting for Confirmation'
            ORDER BY id DESC
            LIMIT 1
            """, (patient_name,))

        appt = cursor.fetchone()

        appointment_id = appt[0] if appt else None

        doctor_name = appt[1] if appt else None

        gst_percentage = float(request.form['gst_percentage'])
        treatment_cost = float(request.form['treatment_cost'])
        medicine_cost = float(request.form['medicine_cost'])
        room_charges = float(request.form['room_charges'])

        gst_percentage = float(request.form['gst_percentage'])

        subtotal = treatment_cost + medicine_cost + room_charges
        gst_amount = (subtotal * gst_percentage) / 100
        total_amount = subtotal + gst_amount

        insurance_claim = request.form['insurance_claim']
        insurance_status = request.form['insurance_status']
        payment_method = request.form['payment_method']
        payment_status = request.form['payment_status']
        refund_status = request.form['refund_status']

        invoice_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute('''
            INSERT INTO billing (
                invoice_id,
                patient_id,
                patient_name,
                treatment_cost,
                medicine_cost,
                room_charges,
                gst_percentage,
                gst_amount,
                total_amount,
                insurance_claim,
                insurance_status,
                payment_method,
                payment_status,
                refund_status,
                invoice_date,
                appointment_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_id,
            patient_id,
            patient_name,
            treatment_cost,
            medicine_cost,
            room_charges,
            gst_percentage,
            gst_amount,
            total_amount,
            insurance_claim,
            insurance_status,
            payment_method,
            payment_status,
            refund_status,
            invoice_date,
            appointment_id
        ))
        if payment_status == "Paid" and appointment_id:

            cursor.execute("""
                UPDATE appointments
                SET status='Confirmed',
                    notification='Appointment Confirmed'
                WHERE appointment_id=?
            """, (appointment_id,))

            cursor.execute("""
                UPDATE patients
                SET doctor_assigned=?
                WHERE patient_id=?
            """, (
                doctor_name,
                patient_id
            ))

        conn.commit()
        
        conn.close()

        flash('Invoice Generated Successfully')

        return redirect(url_for('billing_dashboard'))

    conn.close()

    return render_template(
        'add_bill.html',
        patients=patients,
        selected_patient_id=selected_patient_id,
        selected_patient_name=selected_patient_name
    )

# =========================
# DELETE PATIENT
# =========================
@app.route('/delete_patient/<int:id>')
def delete_patient(id):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        'DELETE FROM patients WHERE id=?',
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for('patient_dashboard'))

# =========================
# DELETE DOCTOR
# =========================
@app.route('/delete_doctor/<int:id>')
def delete_doctor(id):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        'DELETE FROM doctors WHERE id=?',
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for('doctor_dashboard'))

# =========================
# WARD DASHBOARD
# =========================
@app.route('/ward_dashboard')
def ward_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM wards
        ORDER BY admission_date DESC
    ''')

    wards = cursor.fetchall()

    conn.close()

    return render_template(
        'ward_dashboard.html',
        wards=wards
    )


# =========================
# ADD WARD / BED
# =========================
@app.route('/add_ward', methods=['GET', 'POST'])
def add_ward():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT patient_id, full_name
        FROM patients
    ''')

    patients = cursor.fetchall()

    if request.method == 'POST':

        ward_id = generate_ward_id()

        patient_id = request.form['patient_id']
        patient_name = request.form['patient_name']

        ward_type = request.form['ward_type']
        room_number = request.form['room_number']
        bed_number = request.form['bed_number']

        admission_status = request.form['admission_status']
        icu_required = request.form['icu_required']

        admission_date = request.form['admission_date']
        discharge_date = request.form['discharge_date']

        # CHECK BED AVAILABILITY
        cursor.execute('''
            SELECT * FROM wards
            WHERE room_number=?
            AND bed_number=?
            AND admission_status='Admitted'
        ''', (
            room_number,
            bed_number
        ))

        already_allocated = cursor.fetchone()

        if already_allocated:

            flash('Bed Already Occupied')

            conn.close()

            return redirect(url_for('add_ward'))

        cursor.execute('''
            INSERT INTO wards (
                ward_id,
                patient_id,
                patient_name,
                ward_type,
                room_number,
                bed_number,
                admission_status,
                icu_required,
                admission_date,
                discharge_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ward_id,
            patient_id,
            patient_name,
            ward_type,
            room_number,
            bed_number,
            admission_status,
            icu_required,
            admission_date,
            discharge_date
        ))

        conn.commit()
        conn.close()

        flash('Ward & Bed Assigned Successfully')

        return redirect(url_for('ward_dashboard'))

    conn.close()

    return render_template(
        'add_ward.html',
        patients=patients
    )


# =========================
# DISCHARGE PATIENT
# =========================
@app.route('/discharge_patient/<ward_id>')
def discharge_patient(ward_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    discharge_date = datetime.now().strftime("%Y-%m-%d")

    cursor.execute('''
        UPDATE wards
        SET admission_status=?,
            discharge_date=?
        WHERE ward_id=?
    ''', (
        'Discharged',
        discharge_date,
        ward_id
    ))

    conn.commit()
    conn.close()

    flash('Patient Discharged Successfully')

    return redirect(url_for('ward_dashboard'))

# =========================
# ATTENDANCE DASHBOARD
# =========================
@app.route('/attendance_dashboard')
def attendance_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM attendance
        ORDER BY attendance_date DESC
    ''')

    attendance_records = cursor.fetchall()

    conn.close()

    return render_template(
        'attendance_dashboard.html',
        attendance_records=attendance_records
    )

# =========================
# MARK ATTENDANCE
# =========================
@app.route('/mark_attendance', methods=['GET', 'POST'])
def mark_attendance():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT full_name, role FROM users
    ''')

    employees = cursor.fetchall()

    if request.method == 'POST':

        attendance_id = generate_attendance_id()

        employee_name = request.form['employee_name']
        employee_role = request.form['employee_role']

        attendance_date = request.form['attendance_date']
        check_in = request.form['check_in']
        check_out = request.form['check_out']
        status = request.form['status']

        cursor.execute('''
            INSERT INTO attendance (
                attendance_id,
                employee_name,
                employee_role,
                attendance_date,
                check_in,
                check_out,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            attendance_id,
            employee_name,
            employee_role,
            attendance_date,
            check_in,
            check_out,
            status
        ))

        conn.commit()
        conn.close()

        flash('Attendance Marked Successfully')

        return redirect(url_for('attendance_dashboard'))

    conn.close()

    return render_template(
        'mark_attendance.html',
        employees=employees
    )

# =========================
# PAYROLL DASHBOARD
# =========================
@app.route('/payroll_dashboard')
def payroll_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM payroll
        ORDER BY payment_date DESC
    ''')

    payrolls = cursor.fetchall()

    conn.close()

    return render_template(
        'payroll_dashboard.html',
        payrolls=payrolls
    )

# =========================
# ADD PAYROLL
# =========================
@app.route('/add_payroll', methods=['GET', 'POST'])
def add_payroll():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT full_name, role FROM users
    ''')

    employees = cursor.fetchall()

    if request.method == 'POST':

        payroll_id = generate_payroll_id()

        employee_name = request.form['employee_name']
        employee_role = request.form['employee_role']

        basic_salary = float(request.form['basic_salary'])
        bonus = float(request.form['bonus'])
        deductions = float(request.form['deductions'])

        net_salary = basic_salary + bonus - deductions

        payment_status = request.form['payment_status']

        payment_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute('''
            INSERT INTO payroll (
                payroll_id,
                employee_name,
                employee_role,
                basic_salary,
                bonus,
                deductions,
                net_salary,
                payment_status,
                payment_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            payroll_id,
            employee_name,
            employee_role,
            basic_salary,
            bonus,
            deductions,
            net_salary,
            payment_status,
            payment_date
        ))

        conn.commit()
        conn.close()

        flash('Payroll Added Successfully')

        return redirect(url_for('payroll_dashboard'))

    conn.close()

    return render_template(
        'add_payroll.html',
        employees=employees
    )

# =========================
# LEAVE DASHBOARD
# =========================
@app.route('/leave_dashboard')
def leave_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM leaves
        ORDER BY start_date DESC
    ''')

    leaves = cursor.fetchall()

    conn.close()

    return render_template(
        'leave_dashboard.html',
        leaves=leaves
    )

# =========================
# APPLY LEAVE
# =========================
@app.route('/apply_leave', methods=['GET', 'POST'])
def apply_leave():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT full_name, role FROM users
    ''')

    employees = cursor.fetchall()

    if request.method == 'POST':

        leave_id = generate_leave_id()

        employee_name = request.form['employee_name']
        employee_role = request.form['employee_role']

        leave_type = request.form['leave_type']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        reason = request.form['reason']

        approval_status = request.form['approval_status']

        cursor.execute('''
            INSERT INTO leaves (
                leave_id,
                employee_name,
                employee_role,
                leave_type,
                start_date,
                end_date,
                reason,
                approval_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            leave_id,
            employee_name,
            employee_role,
            leave_type,
            start_date,
            end_date,
            reason,
            approval_status
        ))

        conn.commit()
        conn.close()

        flash('Leave Applied Successfully')

        return redirect(url_for('leave_dashboard'))

    conn.close()

    return render_template(
        'apply_leave.html',
        employees=employees
    )   

# =========================
# SHIFT DASHBOARD
# =========================
@app.route('/shift_dashboard')
def shift_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM shifts
        ORDER BY shift_date DESC
    ''')

    shifts = cursor.fetchall()

    conn.close()

    return render_template(
        'shift_dashboard.html',
        shifts=shifts
    )

# =========================
# ADD SHIFT
# =========================
@app.route('/add_shift', methods=['GET', 'POST'])
def add_shift():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT full_name, role FROM users
    ''')

    employees = cursor.fetchall()

    if request.method == 'POST':

        shift_id = generate_shift_id()

        employee_name = request.form['employee_name']
        employee_role = request.form['employee_role']

        shift_date = request.form['shift_date']
        shift_time = request.form['shift_time']
        department = request.form['department']

        cursor.execute('''
            INSERT INTO shifts (
                shift_id,
                employee_name,
                employee_role,
                shift_date,
                shift_time,
                department
            )
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            shift_id,
            employee_name,
            employee_role,
            shift_date,
            shift_time,
            department
        ))

        conn.commit()
        conn.close()

        flash('Shift Assigned Successfully')

        return redirect(url_for('shift_dashboard'))

    conn.close()

    return render_template(
        'add_shift.html',
        employees=employees
    )

# =========================
# INVENTORY DASHBOARD
# =========================
@app.route('/inventory_dashboard')
def inventory_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM equipment
        ORDER BY added_date DESC
    ''')

    equipments = cursor.fetchall()

    conn.close()

    return render_template(
        'inventory_dashboard.html',
        equipments=equipments
    )
# =========================
# ADD EQUIPMENT
# =========================
@app.route('/add_equipment', methods=['GET', 'POST'])
def add_equipment():

    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':

        equipment_id = generate_equipment_id()

        equipment_name = request.form['equipment_name']
        category = request.form['category']
        department = request.form['department']

        quantity = int(request.form['quantity'])

        condition_status = request.form['condition_status']

        purchase_date = request.form['purchase_date']
        warranty_expiry = request.form['warranty_expiry']

        equipment_status = request.form['equipment_status']

        added_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO equipment (
                equipment_id,
                equipment_name,
                category,
                department,
                quantity,
                condition_status,
                purchase_date,
                warranty_expiry,
                equipment_status,
                added_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            equipment_id,
            equipment_name,
            category,
            department,
            quantity,
            condition_status,
            purchase_date,
            warranty_expiry,
            equipment_status,
            added_date
        ))

        conn.commit()
        conn.close()

        flash('Equipment Added Successfully')

        return redirect(url_for('inventory_dashboard'))

    return render_template('add_equipment.html')

# =========================
# VENDOR DASHBOARD
# =========================
@app.route('/vendor_dashboard')
def vendor_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM vendors
        ORDER BY created_at DESC
    ''')

    vendors = cursor.fetchall()

    conn.close()

    return render_template(
        'vendor_dashboard.html',
        vendors=vendors
    )

# =========================
# ADD VENDOR
# =========================
@app.route('/add_vendor', methods=['GET', 'POST'])
def add_vendor():

    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':

        vendor_id = generate_vendor_id()

        vendor_name = request.form['vendor_name']
        company_name = request.form['company_name']

        phone = request.form['phone']
        email = request.form['email']

        address = request.form['address']

        supplied_items = request.form['supplied_items']

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO vendors (
                vendor_id,
                vendor_name,
                company_name,
                phone,
                email,
                address,
                supplied_items,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            vendor_id,
            vendor_name,
            company_name,
            phone,
            email,
            address,
            supplied_items,
            created_at
        ))

        conn.commit()
        conn.close()

        flash('Vendor Added Successfully')

        return redirect(url_for('vendor_dashboard'))

    return render_template('add_vendor.html')

# =========================
# PURCHASE ORDER DASHBOARD
# =========================
@app.route('/purchase_orders')
def purchase_orders():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM purchase_orders
        ORDER BY order_date DESC
    ''')

    orders = cursor.fetchall()

    conn.close()

    return render_template(
        'purchase_orders.html',
        orders=orders
    )

# =========================
# ADD PURCHASE ORDER
# =========================
@app.route('/add_purchase_order', methods=['GET', 'POST'])
def add_purchase_order():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT vendor_name FROM vendors")
    vendors = cursor.fetchall()

    cursor.execute("SELECT equipment_name FROM equipment")
    equipments = cursor.fetchall()

    if request.method == 'POST':

        order_id = generate_order_id()

        vendor_name = request.form['vendor_name']
        equipment_name = request.form['equipment_name']

        quantity = int(request.form['quantity'])

        unit_price = float(request.form['unit_price'])

        total_price = quantity * unit_price

        order_status = request.form['order_status']

        order_date = request.form['order_date']
        delivery_date = request.form['delivery_date']

        cursor.execute('''
            INSERT INTO purchase_orders (
                order_id,
                vendor_name,
                equipment_name,
                quantity,
                unit_price,
                total_price,
                order_status,
                order_date,
                delivery_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_id,
            vendor_name,
            equipment_name,
            quantity,
            unit_price,
            total_price,
            order_status,
            order_date,
            delivery_date
        ))

        conn.commit()
        conn.close()

        flash('Purchase Order Added Successfully')

        return redirect(url_for('purchase_orders'))

    conn.close()

    return render_template(
        'add_purchase_order.html',
        vendors=vendors,
        equipments=equipments
    )

# =========================
# MAINTENANCE DASHBOARD
# =========================
@app.route('/maintenance_dashboard')
def maintenance_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM maintenance_logs
        ORDER BY maintenance_date DESC
    ''')

    logs = cursor.fetchall()

    conn.close()

    return render_template(
        'maintenance_dashboard.html',
        logs=logs
    )

# =========================
# ADD MAINTENANCE LOG
# =========================
@app.route('/add_maintenance', methods=['GET', 'POST'])
def add_maintenance():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT equipment_name FROM equipment")
    equipments = cursor.fetchall()

    if request.method == 'POST':

        maintenance_id = generate_maintenance_id()

        equipment_name = request.form['equipment_name']

        engineer_name = request.form['engineer_name']

        maintenance_type = request.form['maintenance_type']

        maintenance_date = request.form['maintenance_date']

        next_service_date = request.form['next_service_date']

        remarks = request.form['remarks']

        status = request.form['status']

        cursor.execute('''
            INSERT INTO maintenance_logs (
                maintenance_id,
                equipment_name,
                engineer_name,
                maintenance_type,
                maintenance_date,
                next_service_date,
                remarks,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            maintenance_id,
            equipment_name,
            engineer_name,
            maintenance_type,
            maintenance_date,
            next_service_date,
            remarks,
            status
        ))

        conn.commit()
        conn.close()

        flash('Maintenance Log Added Successfully')

        return redirect(url_for('maintenance_dashboard'))

    conn.close()

    return render_template(
        'add_maintenance.html',
        equipments=equipments
    )

# =========================
# DELETE EQUIPMENT
# =========================
@app.route('/delete_equipment/<int:id>')
def delete_equipment(id):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        'DELETE FROM equipment WHERE id=?',
        (id,)
    )

    conn.commit()
    conn.close()

    flash('Equipment Deleted Successfully')

    return redirect(url_for('inventory_dashboard'))


# =========================
# REPORTS DASHBOARD
# =========================
@app.route('/reports_dashboard')
def reports_dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # TOTAL REVENUE
    cursor.execute("""
        SELECT SUM(total_amount)
        FROM billing
    """)

    revenue = cursor.fetchone()[0]

    if revenue is None:
        revenue = 0

    # TOTAL PATIENTS
    cursor.execute("""
        SELECT COUNT(*)
        FROM patients
    """)

    total_patients = cursor.fetchone()[0]

    # TOTAL DOCTORS
    cursor.execute("""
        SELECT COUNT(*)
        FROM doctors
    """)

    total_doctors = cursor.fetchone()[0]

    # DISEASE TRENDS
    cursor.execute("""
        SELECT disease, COUNT(*)
        FROM patients
        GROUP BY disease
        ORDER BY COUNT(*) DESC
    """)

    disease_trends = cursor.fetchall()

    # DOCTOR PERFORMANCE
    cursor.execute("""
        SELECT doctor_assigned, COUNT(*)
        FROM patients
        GROUP BY doctor_assigned
        ORDER BY COUNT(*) DESC
    """)

    doctor_stats = cursor.fetchall()

    # GENERATED REPORTS
    cursor.execute("""
        SELECT *
        FROM reports
        ORDER BY generated_date DESC
    """)

    reports = cursor.fetchall()

    conn.close()

    return render_template(
        'reports_dashboard.html',
        revenue=revenue,
        total_patients=total_patients,
        total_doctors=total_doctors,
        disease_trends=disease_trends,
        doctor_stats=doctor_stats,
        reports=reports
    )

# =========================
# GENERATE REPORT
# =========================
@app.route('/generate_report')
def generate_report():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    report_id = generate_report_id()

    generated_by = session['user']

    generated_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # TOTAL REVENUE
    cursor.execute("""
        SELECT SUM(total_amount)
        FROM billing
    """)

    revenue = cursor.fetchone()[0]

    if revenue is None:
        revenue = 0

    # TOTAL PATIENTS
    cursor.execute("""
        SELECT COUNT(*)
        FROM patients
    """)

    total_patients = cursor.fetchone()[0]

    # TOTAL DOCTORS
    cursor.execute("""
        SELECT COUNT(*)
        FROM doctors
    """)

    total_doctors = cursor.fetchone()[0]

    # EMERGENCY CASES
    cursor.execute("""
        SELECT COUNT(*)
        FROM patients
        WHERE admission_type='Emergency'
    """)

    emergency_cases = cursor.fetchone()[0]

    # TOP DISEASE
    cursor.execute("""
        SELECT disease, COUNT(*)
        FROM patients
        GROUP BY disease
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """)

    disease_data = cursor.fetchone()

    top_disease = disease_data[0] if disease_data else "N/A"

    # TOP DOCTOR
    cursor.execute("""
        SELECT doctor_assigned, COUNT(*)
        FROM patients
        GROUP BY doctor_assigned
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """)

    doctor_data = cursor.fetchone()

    top_doctor = doctor_data[0] if doctor_data else "N/A"

    cursor.execute('''
        INSERT INTO reports (
            report_id,
            report_type,
            generated_by,
            generated_date,
            total_revenue,
            total_patients,
            total_doctors,
            emergency_cases,
            top_disease,
            top_doctor,
            remarks
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        report_id,
        'Hospital Analytics',
        generated_by,
        generated_date,
        revenue,
        total_patients,
        total_doctors,
        emergency_cases,
        top_disease,
        top_doctor,
        'System Generated Report'
    ))

    conn.commit()
    conn.close()

    flash('Report Generated Successfully')

    return redirect(url_for('reports_dashboard'))

# =========================
# PATIENT PORTAL
# =========================
@app.route('/patient_portal')
@role_required('Patient')
def patient_portal():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    # GET USER FULL NAME
    cursor.execute('''
        SELECT full_name
        FROM users
        WHERE username=?
    ''', (session['user'],))

    user_data = cursor.fetchone()

    full_name = user_data['full_name']

    # GET PATIENT DETAILS
    cursor.execute('''
        SELECT *
        FROM patients
        WHERE full_name=?
    ''', (full_name,))

    patient = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM doctors
    """)

    doctors = cursor.fetchall()

    # GET PATIENT BILLS
    bills = []

    if patient:
        cursor.execute("""
            SELECT *
            FROM billing
            WHERE patient_id=?
            ORDER BY invoice_date DESC
        """, (patient['patient_id'],))

        bills = cursor.fetchall()


    # fetch laboratory reports

    cursor.execute('''
        SELECT
            report_name,
            status,
            file_name,
            uploaded_at,
            test_id
        FROM laboratory_reports
        WHERE patient_id=?
    ''', (patient['patient_id'],))

    lab_reports = cursor.fetchall()

    cursor.execute("""
        SELECT
            a.appointment_id,
            a.doctor_name,
            a.appointment_date,
            a.appointment_time,
            d.doctor_id
        FROM appointments a
        LEFT JOIN doctors d
            ON a.doctor_name = d.doctor_name
        WHERE a.patient_name = ?
        AND a.status = 'Confirmed'
        ORDER BY a.appointment_date DESC
    """, (full_name,))

    my_appointments = cursor.fetchall()

    cursor.execute(""" 
        SELECT * 
        FROM appointments 
        WHERE patient_name=? 
        ORDER BY appointment_date DESC 
    """, (full_name,)) 
    
    my_appointments = cursor.fetchall()

    conn.close()

    return render_template(
        'patient_portal.html',
        patient=patient,
        doctors=doctors,
        bills=bills,
        lab_reports=lab_reports,
        appointments=appointments,
        my_appointments=my_appointments
        
    )

# =========================
# UPDATE PATIENT DISEASE
# =========================
@app.route('/update_disease', methods=['POST'])
@role_required('Patient')
def update_disease():

    disease = request.form['disease']

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Get logged-in user's full name
    cursor.execute("""
        SELECT full_name
        FROM users
        WHERE username=?
    """, (session['user'],))

    user = cursor.fetchone()

    if user:

        full_name = user[0]

        # Update disease in patients table
        cursor.execute("""
            UPDATE patients
            SET disease=?
            WHERE full_name=?
        """, (disease, full_name))

        conn.commit()

    conn.close()

    flash('Disease Updated Successfully')

    return redirect(url_for('patient_portal'))

# =========================
# ASSIGN DOCTOR TO PATIENT
# =========================
@app.route('/assign_doctor/<patient_id>', methods=['POST'])
@role_required('Admin')
def assign_doctor(patient_id):

    doctor_name = request.form['doctor_name']

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE patients
        SET doctor_assigned=?
        WHERE patient_id=?
    """, (
        doctor_name,
        patient_id
    ))

    conn.commit()
    conn.close()

    flash('Doctor Assigned Successfully')

    return redirect(url_for('dashboard'))

# =========================
# DOCTOR PORTAL
# =========================
@app.route('/doctor_portal')
@role_required('Doctor')
def doctor_portal():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT doctor_name
        FROM doctors
        WHERE email=?
    """, (session['user'],))

    doctor = cursor.fetchone()

    if not doctor:
        flash('Doctor profile not found')
        return redirect(url_for('login'))

    doctor_name = doctor['doctor_name']

    # GET ASSIGNED PATIENTS (ONLY PAID/CONFIRMED APPOINTMENTS)
    cursor.execute("""
        SELECT DISTINCT
            p.*,
            a.appointment_date,
            a.appointment_time,
            a.appointment_id
        FROM patients p
        INNER JOIN appointments a
            ON p.patient_id = a.patient_id
        WHERE a.doctor_name = ?
        AND (
                a.status = 'Confirmed'
                OR
                (
                    a.status = 'Follow-Up'
                    AND a.appointment_date = DATE('now')
                )
            )
        ORDER BY p.full_name
    """, (doctor_name,))

    patients = cursor.fetchall()

    # GET APPOINTMENTS
    cursor.execute('''
        SELECT *
        FROM appointments
        WHERE doctor_name=?
        AND (
                status='Confirmed'
                OR
                (
                    status='Follow-Up'
                    AND appointment_date = DATE('now')
                )
            )
        ORDER BY appointment_date DESC
    ''', (doctor_name,))

    appointments = cursor.fetchall()

    cursor.execute('''
        SELECT *
        FROM shared_reports
        WHERE doctor_name=?
        ORDER BY shared_at DESC
    ''', (doctor_name,))

    shared_reports = cursor.fetchall()

    conn.close()

    return render_template(
        'doctor_portal.html',
        doctor_name=doctor_name,
        patients=patients,
        appointments=appointments,
        shared_reports=shared_reports
    )

@app.route('/view_shared_report/<path:filename>')
def view_shared_report(filename):

    if 'user' not in session:
        return redirect(url_for('login'))

    full_path = os.path.join(
        app.config['LAB_REPORT_FOLDER'],
        filename
    )

    if os.path.exists(full_path):

        return send_file(
            full_path,
            as_attachment=False
        )

    flash('Report Not Found')

    return redirect(url_for('doctor_portal'))

# =========================
# DOCTOR VIEW SHARED REPORTS
# =========================
@app.route('/doctor_view_shared_reports/<appointment_id>')
@role_required('Doctor')
def doctor_view_shared_reports(appointment_id):

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    # GET DOCTOR NAME
    cursor.execute("""
        SELECT doctor_name
        FROM doctors
        WHERE email=?
    """, (session['user'],))

    doctor = cursor.fetchone()

    doctor_name = doctor['doctor_name']

    # GET SHARED REPORTS
    cursor.execute("""
        SELECT *
        FROM shared_reports
        WHERE appointment_id=?
        AND doctor_name=?
        ORDER BY shared_at DESC
    """, (
        appointment_id,
        doctor_name
    ))

    reports = cursor.fetchall()

    conn.close()

    return render_template(
        'doctor_shared_reports.html',
        reports=reports
    )
# =========================
# UPDATE DIAGNOSIS
# =========================
@app.route('/update_diagnosis/<patient_id>', methods=['POST'])
@role_required('Doctor')
def update_diagnosis(patient_id):

    diagnosis = request.form['disease']
    medical_history = request.form['medical_history']

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE patients
        SET disease=?,
            medical_history=?
        WHERE patient_id=?
    ''', (
        diagnosis,
        medical_history,
        patient_id
    ))
    @app.route('/update_payment/<invoice_id>', methods=['POST'])
    @role_required('Admin')
    def update_payment(invoice_id):

        payment_status = request.form['payment_status']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE billing
            SET payment_status=?
            WHERE invoice_id=?
        """, (
            payment_status,
            invoice_id
        ))
        if payment_status == "Paid":

            cursor.execute("""
            SELECT appointment_id
            FROM billing
            WHERE invoice_id=?
        """, (invoice_id,))

            appointment_id = cursor.fetchone()[0]

            cursor.execute("""
                UPDATE appointments
                SET status='Confirmed',
                    notification='Appointment Confirmed'
                WHERE appointment_id=?
            """, (appointment_id,))

        conn.commit()
        conn.close()

        flash('Payment Status Updated Successfully')

        return redirect(url_for('billing_dashboard'))

    conn.commit()
    conn.close()

    flash('Diagnosis Updated Successfully')

    return redirect(url_for('doctor_portal'))

# =========================
# ADD PRESCRIPTION
# =========================
@app.route('/add_prescription/<patient_id>', methods=['POST'])
@role_required('Doctor')
def add_prescription(patient_id):

    prescription = request.form['prescription']

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO emr_records (
            patient_id,
            doctor_name,
            diagnosis,
            prescription,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    ''', (
        patient_id,
        session['user'],
        '',
        prescription,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))

    conn.commit()
    conn.close()

    flash('Prescription Added')

    return redirect(url_for('doctor_portal'))

# =========================
# NURSE PORTAL
# =========================
@app.route('/nurse_portal')
@role_required('Nurse')
def nurse_portal():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute('''
        SELECT *
        FROM wards
        ORDER BY admission_date DESC
    ''')

    wards = cursor.fetchall()

    conn.close()

    return render_template(
        'nurse_portal.html',
        wards=wards
    )

# =========================
# RECEPTIONIST PORTAL
# =========================
@app.route('/receptionist_portal')
@role_required('Receptionist')
def receptionist_portal():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute('''
        SELECT *
        FROM appointments
        ORDER BY appointment_date DESC
    ''')

    appointments = cursor.fetchall()

    conn.close()

    return render_template(
        'receptionist_portal.html',
        appointments=appointments
    )

# =========================
# LAB TECHNICIAN PORTAL
# =========================
@app.route('/lab_technician_portal')
@role_required('Lab Technician')
def lab_technician_portal():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute('''
        SELECT *
        FROM laboratory
        ORDER BY booking_date DESC
    ''')

    tests = cursor.fetchall()

    conn.close()

    return render_template(
        'lab_technician_portal.html',
        tests=tests
    )

# =========================
# PHARMACIST PORTAL
# =========================
@app.route('/pharmacist_portal')
@role_required('Pharmacist')
def pharmacist_portal():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute('''
        SELECT *
        FROM pharmacy
        ORDER BY added_date DESC
    ''')

    medicines = cursor.fetchall()

    conn.close()

    return render_template(
        'pharmacist_portal.html',
        medicines=medicines
    )

# =========================
# UPDATE PATIENT PROFILE
# =========================
@app.route('/update_patient_profile', methods=['POST'])
@role_required('Patient')
def update_patient_profile():

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # GET USER FULL NAME
    cursor.execute('''
        SELECT full_name
        FROM users
        WHERE username=?
    ''', (session['user'],))

    user = cursor.fetchone()

    if not user:

        flash('User not found')
        return redirect(url_for('patient_portal'))

    full_name = user[0]

    # FORM DATA
    age = request.form['age']
    gender = request.form['gender']
    phone = request.form['phone']
    address = request.form['address']
    blood_group = request.form['blood_group']
    emergency_contact = request.form['emergency_contact']
    insurance_provider = request.form['insurance_provider']
    insurance_number = request.form['insurance_number']

    # UPDATE PATIENT TABLE
    cursor.execute('''
        UPDATE patients
        SET
            age=?,
            gender=?,
            phone=?,
            address=?,
            blood_group=?,
            emergency_contact=?,
            insurance_provider=?,
            insurance_number=?
        WHERE full_name=?
    ''', (
        age,
        gender,
        phone,
        address,
        blood_group,
        emergency_contact,
        insurance_provider,
        insurance_number,
        full_name
    ))

    conn.commit()
    conn.close()

    flash('Profile Updated Successfully')

    return redirect(url_for('patient_portal'))

@app.route('/doctor_portal_preview/<doctor_name>')
@role_required('Admin')
def doctor_portal_preview(doctor_name):

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM appointments
        WHERE doctor_name=?
    """, (doctor_name,))
    appointments = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM emr_records
        WHERE doctor_name=?
    """, (doctor_name,))
    emr_records = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM patients
        WHERE doctor_assigned=?
    """, (doctor_name,))
    patients = cursor.fetchall()

    conn.close()

    return render_template(
        'doctor_portal.html',
        doctor_name=doctor_name,
        patients=patients,
        appointments=appointments,
        emr_records=emr_records
    )

@app.route('/edit_doctor/<int:id>')
@role_required('Admin')
def edit_doctor(id):

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM doctors
        WHERE id=?
    """, (id,))

    doctor = cursor.fetchone()

    conn.close()

    return render_template(
        'edit_doctor.html',
        doctor=doctor
    )

@app.route('/update_doctor/<int:id>', methods=['POST'])
@role_required('Admin')
def update_doctor(id):

    department = request.form['department']
    specialization = request.form['specialization']
    availability = request.form['availability']
    room_number = request.form['room_number']
    experience = request.form['experience']

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE doctors
        SET
            department=?,
            specialization=?,
            availability=?,
            room_number=?,
            experience=?
        WHERE id=?
    """, (
        department,
        specialization,
        availability,
        room_number,
        experience,
        id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for('doctor_dashboard'))

@app.route('/assign_disease_doctor', methods=['POST'])
@role_required('Patient')
def assign_disease_doctor():

    disease = request.form['disease']
    doctor_name = request.form['doctor_name']

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE patients
        SET
            disease=?,
            doctor_assigned=?
        WHERE full_name=?
    """, (
        disease,
        doctor_name,
        session['user']
    ))

    conn.commit()
    conn.close()

    flash("Doctor assigned successfully")

    return redirect(
        url_for('patient_portal')
    )

@app.route('/edit_patient/<int:id>')
@role_required('Admin')
def edit_patient(id):

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM patients
        WHERE id=?
    """, (id,))

    patient = cursor.fetchone()

    conn.close()

    return render_template(
        'edit_patient.html',
        patient=patient
    )

@app.route('/update_patient/<int:id>', methods=['POST'])
@role_required('Admin')
def update_patient(id):

    age = request.form['age']
    gender = request.form['gender']
    phone = request.form['phone']
    blood_group = request.form['blood_group']
    disease = request.form['disease']
    doctor_assigned = request.form['doctor_assigned']
    admission_type = request.form['admission_type']
    address = request.form['address']

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE patients
        SET
            age=?,
            gender=?,
            phone=?,
            blood_group=?,
            disease=?,
            doctor_assigned=?,
            admission_type=?,
            address=?
        WHERE id=?
    """, (
        age,
        gender,
        phone,
        blood_group,
        disease,
        doctor_assigned,
        admission_type,
        address,
        id
    ))

    conn.commit()
    conn.close()

    flash("Patient Updated Successfully")

    return redirect(url_for('patient_dashboard'))

@app.route('/view_lab_reports/<test_id>')
def view_lab_reports(test_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # laboratory test details
    cursor.execute('''
        SELECT *
        FROM laboratory
        WHERE test_id=?
    ''', (test_id,))

    test = cursor.fetchone()

    # uploaded reports
    cursor.execute('''
        SELECT *
        FROM laboratory_reports
        WHERE test_id=?
        ORDER BY uploaded_at DESC
    ''', (test_id,))

    reports = cursor.fetchall()

    conn.close()

    return render_template(
        'view_lab_reports.html',
        test=test,
        reports=reports
    )

@app.route('/upload_lab_report/<test_id>', methods=['GET', 'POST'])
def upload_lab_report(test_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':

        report_name = request.form['report_name']
        file = request.files['report_file']

        if file and allowed_file(file.filename):

            import uuid

            filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"

            save_path = os.path.join(
                app.config['LAB_REPORT_FOLDER'],
                filename
            )

            file.save(save_path)

            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()

            # get patient id
            cursor.execute('''
                SELECT patient_id
                FROM laboratory
                WHERE test_id=?
            ''', (test_id,))

            patient = cursor.fetchone()

            patient_id = patient[0]

            cursor.execute('''
                INSERT INTO laboratory_reports
                (
                    test_id,
                    patient_id,
                    report_name,
                    file_name,
                    status
                )

                VALUES (?, ?, ?, ?, ?)
            ''', (

                test_id,
                patient_id,
                report_name,
                filename,
                'Completed'
            ))

            conn.commit()
            conn.close()

            flash('Report Uploaded Successfully')

            return redirect(
                url_for(
                    'view_lab_reports',
                    test_id=test_id
                )
            )

    return render_template(
        'upload_lab_report.html',
        test_id=test_id
    )

@app.route('/download_lab_report/<filename>')
def download_lab_report(filename):

    full_path = os.path.join(
        app.config['LAB_REPORT_FOLDER'],
        filename
    )

    if os.path.exists(full_path):

        return send_file(
            full_path,
            as_attachment=True
        )

    flash('File Not Found')

    return redirect(url_for('lab_dashboard'))


# =========================
# MAIN
# =========================
@app.route('/update_payment/<invoice_id>', methods=['POST'])
def update_payment(invoice_id):

    payment_status = request.form.get('payment_status')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE billing
        SET payment_status = ?
        WHERE invoice_id = ?
    """, (payment_status, invoice_id))

    conn.commit()
    conn.close()

    flash("Payment status updated successfully")

    return redirect(url_for('billing_dashboard'))

@app.route('/delete_bill/<invoice_id>', methods=['POST'])
def delete_bill(invoice_id):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM billing WHERE invoice_id=?",
        (invoice_id,)
    )

    conn.commit()
    conn.close()

    flash("Invoice deleted successfully!")

    return redirect(url_for('billing_dashboard'))

@app.route('/download_invoice/<invoice_id>')
@role_required('Patient')
def download_invoice(invoice_id):

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM billing
        WHERE invoice_id = ?
    """, (invoice_id,))

    bill = cursor.fetchone()

    conn.close()

    if not bill:
        flash("Invoice not found")
        return redirect(url_for('patient_portal'))

    if bill['payment_status'] != 'Paid':
        flash("Invoice can only be downloaded after payment.")
        return redirect(url_for('patient_portal'))

    invoice_folder = os.path.join(os.getcwd(), "invoices")

    os.makedirs(invoice_folder, exist_ok=True)

    pdf_file = os.path.join(
        invoice_folder,
        f"{invoice_id}.pdf"
    )

    print("PDF will be saved at:")
    print(pdf_file)
    doc = SimpleDocTemplate(pdf_file)

    styles = getSampleStyleSheet()

    content = []

    content.append(
        Paragraph(
            "HOSPITAL MANAGEMENT SYSTEM",
            styles['Title']
        )
    )

    content.append(Spacer(1, 20))

    content.append(
        Paragraph(
            f"<b>Invoice ID:</b> {bill['invoice_id']}",
            styles['Normal']
        )
    )

    content.append(
        Paragraph(
            f"<b>Patient ID:</b> {bill['patient_id']}",
            styles['Normal']
        )
    )

    content.append(
        Paragraph(
            f"<b>Patient Name:</b> {bill['patient_name']}",
            styles['Normal']
        )
    )

    content.append(
        Paragraph(
            f"<b>Invoice Date:</b> {bill['invoice_date']}",
            styles['Normal']
        )
    )

    content.append(Spacer(1, 15))

    content.append(
        Paragraph(
            "<b>Billing Details</b>",
            styles['Heading2']
        )
    )

    content.append(
        Paragraph(
            f"Treatment Cost: Rs. {bill['treatment_cost']}",
            styles['Normal']
        )
    )

    content.append(
        Paragraph(
            f"Medicine Cost: Rs. {bill['medicine_cost']}",
            styles['Normal']
        )
    )

    content.append(
        Paragraph(
            f"Room Charges: Rs. {bill['room_charges']}",
            styles['Normal']
        )
    )

    content.append(
        Paragraph(
            f"GST Percentage: {bill['gst_percentage']}%",
            styles['Normal']
        )
    )

    content.append(
        Paragraph(
            f"GST Amount: Rs. {bill['gst_amount']}",
            styles['Normal']
        )
    )

    content.append(
        Paragraph(
            f"Total Amount: Rs. {bill['total_amount']}",
            styles['Normal']
        )
    )

    content.append(Spacer(1, 15))

    content.append(
        Paragraph(
            "<b>Payment Information</b>",
            styles['Heading2']
        )
    )

    content.append(
        Paragraph(
            f"Payment Method: {bill['payment_method']}",
            styles['Normal']
        )
    )

    content.append(
        Paragraph(
            f"Payment Status: {bill['payment_status']}",
            styles['Normal']
        )
    )

    content.append(
        Paragraph(
            f"Refund Status: {bill['refund_status']}",
            styles['Normal']
        )
    )

    content.append(Spacer(1, 15))

    content.append(
        Paragraph(
            "<b>Insurance Information</b>",
            styles['Heading2']
        )
    )

    content.append(
        Paragraph(
            f"Insurance Claim: {bill['insurance_claim']}",
            styles['Normal']
        )
    )

    content.append(
        Paragraph(
            f"Insurance Status: {bill['insurance_status']}",
            styles['Normal']
        )
    )

    content.append(Spacer(1, 25))

    content.append(
        Paragraph(
            "Thank you for choosing our hospital.",
            styles['Italic']
        )
    )

    doc.build(content)

    return send_file(
        pdf_file,
        as_attachment=True
    )

@app.route('/share_report_with_doctor', methods=['POST'])
@role_required('Patient')
def share_report_with_doctor():

    filename = request.form['filename']
    report_name = request.form['report_name']
    appointment_id = request.form['appointment_id']

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT doctor_name
        FROM appointments
        WHERE appointment_id=?
    """, (appointment_id,))

    doctor = cursor.fetchone()

    if not doctor:

        flash("Invalid appointment")

        conn.close()

        return redirect(url_for('patient_portal'))

    doctor_name = doctor[0]

    # GET LOGGED-IN PATIENT
    cursor.execute('''
        SELECT full_name
        FROM users
        WHERE username=?
    ''', (session['user'],))

    user_data = cursor.fetchone()

    # GET PATIENT ID
    cursor.execute('''
        SELECT patient_id
        FROM patients
        WHERE full_name=?
    ''', (user_data[0],))

    patient = cursor.fetchone()

    if not patient:

        conn.close()

        flash('Patient not found')

        return redirect(url_for('patient_portal'))

    patient_id = patient[0]

    # PREVENT DUPLICATE SHARING
    cursor.execute('''
        SELECT *
        FROM shared_reports
        WHERE appointment_id=?
        AND file_name=?
    ''', (
        appointment_id,
        filename
    ))

    existing = cursor.fetchone()


    if not existing:

        cursor.execute('''
            INSERT INTO shared_reports
            (
                appointment_id,
                patient_id,
                doctor_name,
                report_name,
                file_name
            )
            VALUES (?, ?, ?, ?, ?)
        ''', (
            appointment_id,
            patient_id,
            doctor_name,
            report_name,
            filename
        ))

        conn.commit()

        flash('Report Shared Successfully')

    else:

        flash('Report Already Shared With This Doctor')


    conn.close()

    return redirect(url_for('patient_portal'))


@app.route('/patient_reports/<patient_id>')
def patient_reports(patient_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    # get all reports shared by this patient
    cursor.execute('''
        SELECT *
        FROM shared_reports
        WHERE patient_id=?
        ORDER BY shared_at DESC
    ''', (patient_id,))

    reports = cursor.fetchall()

    conn.close()

    return render_template(
        'patient_reports.html',
        reports=reports,
        patient_id=patient_id
    )

@app.route('/book_patient_appointment', methods=['POST'])
@role_required('Patient')
def book_patient_appointment():

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT full_name
        FROM users
        WHERE username=?
    """, (session['user'],))

    patient_name = cursor.fetchone()[0]
    cursor.execute("""
        SELECT patient_id
        FROM patients
        WHERE full_name = ?
    """, (patient_name,))

    patient_id = cursor.fetchone()[0]

    appointment_id = generate_appointment_id()
    token_number = generate_token()

    doctor_name = request.form['doctor_name']
    appointment_date = request.form['appointment_date']
    appointment_time = request.form['appointment_time']
    

    cursor.execute("""
        SELECT *
        FROM appointments
        WHERE doctor_name=?
        AND appointment_date=?
        AND appointment_time=?
        AND status!='Cancelled'
    """, (
        doctor_name,
        appointment_date,
        appointment_time
    ))

    existing = cursor.fetchone()

    if existing:

        flash("Slot already booked")
        conn.close()

        return redirect(url_for('patient_portal'))

    # Appointment is available
    status = "Waiting for Confirmation"

    cursor.execute("""
        INSERT INTO appointments (
            appointment_id,
            token_number,
            patient_name,
            doctor_name,
            appointment_date,
            appointment_time,
            status,
            prescription,
            notification,
            patient_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        appointment_id,
        token_number,
        patient_name,
        doctor_name,
        appointment_date,
        appointment_time,
        status,
        '',
        'Waiting For Payment Approval',
        patient_id

    ))

    disease = request.form['disease']
    cursor.execute("""
        UPDATE patients
        SET disease=?
        WHERE full_name=?
    """, (disease, patient_name))

    conn.commit()
    conn.close()

    flash("Appointment Booked Successfully")

    return redirect(url_for('patient_portal'))

@app.route('/cancel_appointment/<appointment_id>')
@role_required('Patient')
def cancel_appointment(appointment_id):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM appointments
        WHERE appointment_id=?
    """, (appointment_id,))

    conn.commit()
    conn.close()

    flash("Appointment Cancelled")

    return redirect(url_for('patient_portal'))

@app.route('/edit_appointment/<appointment_id>',
           methods=['GET','POST'])
@role_required('Patient')
def edit_appointment(appointment_id):

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    if request.method == 'POST':

        appointment_date = request.form['appointment_date']
        appointment_time = request.form['appointment_time']

        cursor.execute("""
            SELECT *
            FROM appointments
            WHERE appointment_id=?
        """, (appointment_id,))

        appointment = cursor.fetchone()

        followup_date = datetime.strptime(
            appointment['appointment_date'],
            "%Y-%m-%d"
        ).date()

        allowed_last_date = followup_date - timedelta(days=1)

        selected_date = datetime.strptime(
            appointment_date,
            "%Y-%m-%d"
        ).date()

        if selected_date > allowed_last_date:

            flash(
                f"Appointment can only be updated until {allowed_last_date}"
            )

            conn.close()

            return redirect(
                url_for(
                    'edit_appointment',
                    appointment_id=appointment_id
                )
            )

        cursor.execute("""
            UPDATE appointments
            SET appointment_date=?,
                appointment_time=?
            WHERE appointment_id=?
        """, (

            appointment_date,
            appointment_time,
            appointment_id

        ))

        conn.commit()
        conn.close()

        flash("Appointment Updated")

        return redirect(url_for('patient_portal'))

    cursor.execute("""
        SELECT *
        FROM appointments
        WHERE appointment_id=?
    """, (appointment_id,))

    appointment = cursor.fetchone()

    # FOLLOW-UP DATE LIMIT
    today = datetime.today().date()

    max_date = (
        datetime.strptime(
            appointment['appointment_date'],
            "%Y-%m-%d"
        ).date() - timedelta(days=1)
    )

    min_date = today.strftime("%Y-%m-%d")
    max_date = max_date.strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT *
        FROM doctors
    """)

    doctors = cursor.fetchall()


    conn.close()

    return render_template(
        'edit_appointment.html',
        appointment=appointment,
        doctors=doctors,
        min_date=min_date,
        max_date=max_date
    )
@app.route('/get_available_slots')
def get_available_slots():

    doctor_name = request.args.get('doctor_name')
    appointment_date = request.args.get('appointment_date')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # GET LOGGED-IN PATIENT NAME
    username = session.get('user')

    cursor.execute("""
        SELECT full_name
        FROM users
        WHERE username = ?
    """, (username,))

    patient = cursor.fetchone()

    patient_name = patient[0] if patient else ''

    all_slots = [
        "09:00 AM",
        "10:00 AM",
        "11:00 AM",
        "12:00 PM",
        "02:00 PM",
        "03:00 PM",
        "04:00 PM"
    ]

    # DOCTOR BOOKED SLOTS
    cursor.execute("""
        SELECT appointment_time
        FROM appointments
        WHERE doctor_name = ?
        AND appointment_date = ?
        AND status != 'Cancelled'
    """, (doctor_name, appointment_date))

    booked = [
        row[0] for row in cursor.fetchall()
    ]

    # PATIENT BOOKED SLOTS
    cursor.execute("""
        SELECT appointment_time
        FROM appointments
        WHERE patient_name = ?
        AND appointment_date = ?
        AND status != 'Cancelled'
    """, (patient_name, appointment_date))

    patient_booked_slots = [
        row[0] for row in cursor.fetchall()
    ]

    conn.close()

    # COMBINE BLOCKED SLOTS
    blocked_slots = list(
        set(booked + patient_booked_slots)
    )

    # FINAL AVAILABLE SLOTS
    available_slots = [

        slot for slot in all_slots

        if slot not in blocked_slots
    ]

    return jsonify({
        "slots": available_slots
    })



@app.route('/complete_appointment/<appointment_id>', methods=['POST'])
def complete_appointment(appointment_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    diagnosis = request.form.get('diagnosis')
    medical_history = request.form.get('medical_history')
    prescription = request.form.get('prescription')
    lab_test = request.form.get('lab_test')

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # =====================================
    # GET APPOINTMENT
    # =====================================

    cursor.execute("""
        SELECT *
        FROM appointments
        WHERE appointment_id=?
    """, (appointment_id,))

    appointment = cursor.fetchone()

    if not appointment:

        flash("Appointment Not Found")
        return redirect(url_for('doctor_portal'))

    patient_id = appointment['patient_id']
    patient_name = appointment['patient_name']
    doctor_name = appointment['doctor_name']

    # =====================================
    # GET SHARED REPORTS
    # =====================================

    cursor.execute("""
        SELECT *
        FROM shared_reports
        WHERE appointment_id=?
        ORDER BY shared_at DESC
    """, (appointment_id,))

    reports = cursor.fetchall()

    # =====================================
    # CREATE CONSULTATION PDF
    # =====================================

    consultation_filename = f"{appointment_id}_consultation.pdf"

    consultation_path = os.path.join(
        app.config['CONSULTATION_FOLDER'],
        consultation_filename
    )

    doc = SimpleDocTemplate(
        consultation_path,
        pagesize=letter
    )

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            "<b>Hospital Consultation Report</b>",
            styles['Title']
        )
    )

    elements.append(Spacer(1, 20))

    elements.append(
        Paragraph(
            f"<b>Patient:</b> {patient_name}",
            styles['BodyText']
        )
    )

    elements.append(
        Paragraph(
            f"<b>Doctor:</b> {doctor_name}",
            styles['BodyText']
        )
    )

    elements.append(
        Paragraph(
            f"<b>Diagnosis:</b> {diagnosis}",
            styles['BodyText']
        )
    )

    elements.append(
        Paragraph(
            f"<b>Medical History:</b> {medical_history}",
            styles['BodyText']
        )
    )

    elements.append(
        Paragraph(
            f"<b>Prescription:</b> {prescription}",
            styles['BodyText']
        )
    )

    elements.append(
        Paragraph(
            f"<b>Lab Test:</b> {lab_test}",
            styles['BodyText']
        )
    )

    doc.build(elements)

    # =====================================
    # MERGE PDFs
    # =====================================

    merger = PdfMerger()

    # ADD CONSULTATION PDF FIRST
    merger.append(consultation_path)

    # =====================================
    # PREVENT DUPLICATES
    # =====================================

    added_files = set()

    # =====================================
    # ADD SHARED REPORT FILES
    # =====================================

    for report in reports:

        report_filename = report['file_name']

        # SKIP DUPLICATE FILES
        if report_filename in added_files:
            continue

        added_files.add(report_filename)

      
        possible_paths = [

            os.path.join(
                app.config['UPLOAD_FOLDER'],
                report_filename
            ),

            os.path.join(
                app.config['LAB_REPORT_FOLDER'],
                report_filename
            ),

            os.path.join(
                app.config['EMR_FOLDER'],
                report_filename
            )
        ]

        report_path = None

        for path in possible_paths:

            if os.path.exists(path):

                report_path = path

                break

        if not report_path:

            print("FILE NOT FOUND:", report_filename)

            continue

        print("CHECKING:", report_path)

        if not os.path.exists(report_path):

            print("FILE NOT FOUND:", report_path)
            continue

        ext = report_filename.lower().split('.')[-1]

        try:

            # =================================
            # PDF FILE
            # =================================

            if ext == 'pdf':

                print("ADDING PDF:", report_filename)

                merger.append(report_path)

            # =================================
            # IMAGE FILE
            # =================================

            elif ext in ['png', 'jpg', 'jpeg']:

                print("ADDING IMAGE:", report_filename)

                image = Image.open(report_path)

                image = image.convert('RGB')

                image_pdf_path = os.path.join(
                    app.config['CONSULTATION_FOLDER'],
                    f"{report_filename}.pdf"
                )

                image.save(image_pdf_path)

                merger.append(image_pdf_path)

            else:

                print("UNSUPPORTED FILE:", report_filename)

        except Exception as e:

            print("ERROR ADDING FILE:", report_filename)
            print(str(e))

    # =====================================
    # FINAL MERGED PDF
    # =====================================

    final_pdf_name = f"{appointment_id}_final_report.pdf"

    final_pdf_path = os.path.join(
        app.config['CONSULTATION_FOLDER'],
        final_pdf_name
    )

    merger.write(final_pdf_path)

    merger.close()

    # =====================================
    # UPDATE APPOINTMENT
    # =====================================

    cursor.execute("""
        UPDATE appointments
        SET
            status=?,
            diagnosis=?,
            prescription=?,
            lab_test=?,
            medical_history=?,
            doctor_pdf=?
        WHERE appointment_id=?
    """, (
        'Completed',
        diagnosis,
        prescription,
        lab_test,
        medical_history,
        final_pdf_name,
        appointment_id
    ))

    # =====================================
    # AUTO CREATE FOLLOW-UP AFTER 3 DAYS
    # =====================================

    try:

        # DO NOT CREATE FOLLOW-UP OF FOLLOW-UP
        if appointment['follow_up_from']:

            print("THIS IS ALREADY A FOLLOW-UP APPOINTMENT")

        else:

            followup_date = (
                datetime.strptime(
                    appointment['appointment_date'],
                    '%Y-%m-%d'
                ) + timedelta(days=3)
            ).strftime('%Y-%m-%d')

            # CHECK IF FOLLOW-UP ALREADY EXISTS
            cursor.execute("""
                SELECT *
                FROM appointments
                WHERE follow_up_from = ?
            """, (appointment_id,))

            existing_followup = cursor.fetchone()

            if existing_followup:

                print("FOLLOW-UP ALREADY EXISTS")

            else:

                followup_id = generate_appointment_id()

                cursor.execute("""
                    INSERT INTO appointments (
                        appointment_id,
                        token_number,
                        patient_id,
                        patient_name,
                        doctor_name,
                        appointment_date,
                        appointment_time,
                        status,
                        prescription,
                        notification,
                        follow_up_from
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    followup_id,
                    generate_token(),
                    patient_id,
                    patient_name,
                    doctor_name,
                    followup_date,
                    appointment['appointment_time'],
                    'Follow-Up',
                    '',
                    'Automatic free follow-up visit',
                    appointment_id
                ))

                print("FOLLOW-UP CREATED")

    except Exception as e:

        print("FOLLOW-UP ERROR:", str(e))


    conn.commit()
    conn.close()

    flash('Appointment Completed & PDF Generated')

    return redirect(url_for('doctor_portal'))

# =========================
# DOWNLOAD FINAL CONSULTATION PDF
# =========================

@app.route('/download_prescription_pdf/<appointment_id>')
def download_prescription_pdf(appointment_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE, timeout=10)

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM appointments
        WHERE appointment_id=?
    """, (appointment_id,))

    appt = cursor.fetchone()

    conn.close()

    if not appt:

        flash('Appointment Not Found')

        return redirect(url_for('patient_portal'))

    # ====================================
    # CHECK IF PDF EXISTS
    # ====================================

    if not appt['doctor_pdf']:

        flash('Consultation PDF Not Ready')

        return redirect(url_for('patient_portal'))

    # ====================================
    # CONSULTATION PDF PATH
    # ====================================

    pdf_path = os.path.join(
        app.config['CONSULTATION_FOLDER'],
        appt['doctor_pdf']
    )

    # ====================================
    # CHECK FILE EXISTS
    # ====================================

    if not os.path.exists(pdf_path):

        flash('PDF File Missing')

        return redirect(url_for('patient_portal'))

    # ====================================
    # DOWNLOAD PDF
    # ====================================

    return send_file(
        pdf_path,
        as_attachment=True
    )

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):

    return send_from_directory(
        app.config['LAB_REPORT_FOLDER'],
        filename
    )

@app.route('/doctor_cancel_appointment/<appointment_id>')
def doctor_cancel_appointment(appointment_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE appointments
        SET status=?
        WHERE appointment_id=?
    """, (
        'Cancelled by Doctor',
        appointment_id
    ))

    conn.commit()
    conn.close()

    flash('Appointment Cancelled')

    return redirect(url_for('doctor_portal'))

# =========================
# LOGOUT
# =========================
@app.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('login'))


if __name__ == "__main__":
    

    if not os.path.exists(app.config['LAB_REPORT_FOLDER']):
        os.makedirs(app.config['LAB_REPORT_FOLDER'])

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    if not os.path.exists(app.config['EMR_FOLDER']):
        os.makedirs(app.config['EMR_FOLDER'])

    app.run(debug=True, use_reloader=False)
