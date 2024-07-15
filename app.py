import csv
from flask import Flask, render_template, request, redirect, flash, url_for,jsonify,session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
from pytz import timezone 

imported_files = []

app = Flask(__name__)
app.secret_key = '0000' 


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
db=SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"
    
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    students = db.relationship('Student', backref='subject', lazy=True)
    attendances = db.relationship('Attendance', backref='subject', lazy=True)

class Student(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    enrollment_no = db.Column(db.String(20), nullable=False)
    branch = db.Column(db.String(50), nullable=False)  
    batch = db.Column(db.String(10), nullable=False)
    semester = db.Column(db.String(10), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    attendances = db.relationship('Attendance', backref='student', lazy=True)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.now(timezone('Asia/Kolkata')))
    status = db.Column(db.String(10), nullable=False)
    attendance_type = db.Column(db.String(10), nullable=False) 
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different username.', 'error')
            return redirect(url_for('register'))

        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logout successful!', 'success')
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    subjects = Subject.query.all()
    return render_template('index.html', subjects=subjects)



@app.route('/subject/add', methods=['GET', 'POST'])
def add_subject():
    if request.method == 'POST':
        subject_name = request.form['subject_name']
        subject = Subject(name=subject_name)
        db.session.add(subject)
        db.session.commit()
        flash('Subject added successfully!', 'success')
        return redirect('/')
    return render_template('add_subject.html')

@app.route('/subject/<int:subject_id>/students', methods=['GET', 'POST'])
def add_students(subject_id):
    subject = Subject.query.get(subject_id)
    if request.method == 'POST':
        student_name = request.form['student_name']
        enrollment_no = request.form['enrollment_no']
        branch = request.form['branch']
        batch = request.form['batch']
        semester = request.form['semester']

        student = Student(name=student_name, enrollment_no=enrollment_no, branch=branch, batch=batch, semester=semester, subject=subject)
        db.session.add(student)
        db.session.commit()

        flash('Student added successfully!', 'success')
        return redirect(url_for('add_students', subject_id=subject_id))
    return render_template('add_students.html', subject=subject)

@app.route('/subject/<int:subject_id>/attendance', methods=['GET', 'POST'])
def take_attendance(subject_id):
    subject = Subject.query.get(subject_id)
    students = subject.students
    current_time = datetime.now(timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S %Z%z')

    if request.method == 'POST':
        attendance_type = request.form['attendance_type']  # Lab or Lecture
        for student in students:
            attendance_status = request.form.get(str(student.id))
            if attendance_status == 'present':
                status = 'present'
            else:
                status = 'absent'
            attendance = Attendance(student_id=student.id, subject_id=subject_id, attendance_type=attendance_type, status=status)
            db.session.add(attendance)
        db.session.commit()
        flash('Attendance taken successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('take_attendance.html', subject=subject, students=students, current_time=current_time)


@app.route('/attendance')
def attendance_list():
    search_query = request.args.get('search')
    if search_query:
        attendances = Attendance.query \
            .join(Student) \
            .join(Subject) \
            .filter(db.or_(
                Student.name.contains(search_query),
                Subject.name.contains(search_query) )) \
            .all()
    else:
        attendances = Attendance.query.join(Student).join(Subject).all()
    
    current_time = datetime.now(timezone('Asia/Kolkata'))
    return render_template('attendance_list.html', attendances=attendances, current_time=current_time)


@app.route('/import', methods=['GET', 'POST'])
def import_file():
    if request.method == 'POST':
        file = request.files['file']
        if file.filename.endswith('.xlsx'):
            try:
                df = pd.read_excel(file)
                # Your logic to process the imported file as needed

                # Add the imported file name to the list
                imported_files.append(file.filename)

                flash('File imported successfully!', 'success')
            except Exception as e:
                flash(f'Error importing file: {str(e)}', 'error')
        elif file.filename.endswith('.html'):
            try:
                content = file.read().decode('utf-8')
                # Your logic to process the imported file as needed

                # Add the imported file name to the list
                imported_files.append(file.filename)

                flash('File imported successfully!', 'success')
            except Exception as e:
                flash(f'Error importing file: {str(e)}', 'error')
        else:
            flash('Invalid file format. Only .xlsx and .html files are allowed.', 'error')

        return redirect(url_for('index'))

    return render_template('import.html')

@app.route('/bulk_attendance', methods=['GET', 'POST'])
def add_bulk_attendance():
    if request.method == 'POST':
        file = request.files['file']
        if file.filename.endswith('.csv'):
            try:
                # Read the CSV file and process the attendance data
                csv_data = csv.reader(file)
                next(csv_data)  # Skip the header row if present

                attendance_data = []  # List to store attendance records

                for row in csv_data:
                    enrollment_no = row[0]
                    subject_name = row[1]
                    # ... process other fields as needed

                    # Query the database to get the subject and student
                    subject = Subject.query.filter_by(name=subject_name).first()
                    student = Student.query.filter_by(enrollment_no=enrollment_no).first()

                    if subject and student:
                        # Create an attendance record
                        attendance = Attendance(student_id=student.id, subject_id=subject.id, status='Present')
                        attendance_data.append(attendance)

                db.session.add_all(attendance_data)
                db.session.commit()
                flash('Bulk attendance added successfully!', 'success')

                # Redirect to the attendance list page
                return redirect(url_for('attendance_list'))
            except Exception as e:
                flash(f'Error importing file: {str(e)}', 'error')
        else:
            flash('Invalid file format. Only CSV files are allowed.', 'error')

    return render_template('bulk_attendance.html')

if __name__ == '__main__':
    app.run(debug=True)
 
 