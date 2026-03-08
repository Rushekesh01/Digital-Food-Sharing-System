from flask import Flask, render_template, request, redirect, session, flash, jsonify
import mysql.connector
from mysql.connector import IntegrityError
import os
from datetime import datetime, timedelta
import random
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static')
app.secret_key = 'food-sharing-secret-key-2026-rushekesh'

app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # 7 din tak login rahega

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",  # apna MySQL username
        password="",  # apna MySQL password
        database="food_sharing"
    )

# Home page
@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')

# Donation page
@app.route('/donate.html')
def donate_page():
    if 'user_id' not in session:
        flash('Please login to donate food', 'danger')
        return redirect('/login.html')
    return render_template('donate.html')

# Submit donation
@app.route('/submit-donation', methods=['POST'])
def submit_donation():
    if 'user_id' not in session:
        return redirect('/login.html')
    
    donor_name = request.form['donor_name']
    phone = request.form['phone']
    food_type = request.form['food_type']
    quantity = request.form['quantity']
    expiry = request.form['expiry_time']
    address = request.form['address']
    notes = request.form.get('notes', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO donations (user_id, donor_name, phone, food_type, quantity, 
                              expiry_time, address, notes, status) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (session['user_id'], donor_name, phone, food_type, quantity, 
          expiry, address, notes, 'available'))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Donation submitted successfully!', 'success')
    return redirect('/dashboard')

# Request page
@app.route('/request.html')
def request_page():
    if 'user_id' not in session:
        flash('Please login to request food', 'danger')
        return redirect('/login.html')
    return render_template('request.html')

# Submit request
@app.route('/submit-request', methods=['POST'])
def submit_request():
    if 'user_id' not in session:
        flash('Please login to request food', 'danger')
        return redirect('/login.html')

    requester_name = request.form['requester_name']
    phone = request.form['phone']
    people_count = request.form['people_count']
    food_type = request.form['food_type']
    address = request.form['address']
    urgency = request.form['urgency']
    requirements = request.form.get('requirements', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO requests (requester_name, phone, people_count, food_type, 
                            address, urgency, requirements, status) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (requester_name, phone, people_count, food_type, address, 
          urgency, requirements, 'pending'))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Request submitted successfully! We will contact you soon.', 'success')
    return redirect('/')

# Login page
@app.route('/login.html')
def login_page():
    return render_template('login.html')

# Login submit
@app.route('/login', methods=['POST'])
def login():
    try:
        # Form se data lena
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"Login attempt - Email: {email}")  # Debug
        
        # Check if email and password provided
        if not email or not password:
            flash('Please enter both email and password', 'danger')
            return redirect('/login.html')
        
        # Database connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Find user by email
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        # Check if user exists
        if not user:
            print("User not found!")  # Debug
            flash('Email not registered. Please sign up first.', 'danger')
            return redirect('/login.html')
        
        # Check password
        if check_password_hash(user['password'], password):
            print("Password correct!")  # Debug
            # Set session
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_phone'] = user['phone']

            session.permanent = True  
            
            flash('Login successful!', 'success')
            return redirect('/dashboard')
        else:
            print("Password incorrect!")  # Debug
            flash('Incorrect password. Please try again.', 'danger')
            return redirect('/login.html')
            
    except Exception as e:
        print(f"Login error: {e}")  # Debug
        flash('An error occurred. Please try again.', 'danger')
        return redirect('/login.html')

# Signup page
@app.route('/signup.html')
def signup_page():
    return render_template('signup.html')

# Signup submit - ONLY ONE SIGNUP ROUTE
@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['fullname']
    email = request.form['email']
    phone = request.form['number']
    password = request.form['password']
    captcha = request.form['captcha']
    
    # Verify captcha
    if captcha != '12':
        flash('Wrong captcha answer', 'danger')
        return redirect('/signup.html')
    
    # Hash password
    hashed_password = generate_password_hash(password)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO users (name, email, phone, password) 
            VALUES (%s, %s, %s, %s)
        """, (name, email, phone, hashed_password))
        conn.commit()
        
        # Auto-login after signup
        user_id = cursor.lastrowid
        session['user_id'] = user_id
        session['user_name'] = name
        session['user_email'] = email
        session['user_phone'] = phone
        
        flash('Account created successfully!', 'success')
        return redirect('/dashboard')
        
    except IntegrityError:
        flash('Email or phone already exists', 'danger')
        return redirect('/signup.html')
        
    finally:
        cursor.close()
        conn.close()

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login.html')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get user's donations
    cursor.execute("SELECT * FROM donations WHERE user_id = %s ORDER BY id DESC LIMIT 5", 
                  (session['user_id'],))
    my_donations = cursor.fetchall()
    
    # Get counts
    cursor.execute("SELECT COUNT(*) as count FROM donations WHERE user_id = %s", 
                  (session['user_id'],))
    donations_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM requests WHERE phone = %s", 
                  (session.get('user_phone', ''),))
    requests_count = cursor.fetchone()['count']
    
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html', 
                         my_donations=my_donations,
                         donations_count=donations_count,
                         requests_count=requests_count,
                         active_count=donations_count)

# Available food
@app.route('/available.html')
def available_food():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT * FROM donations 
        WHERE status = 'available' 
        ORDER BY created_at DESC
    """)
    available_food = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('available.html', available_food=available_food)

# Request specific food
@app.route('/request-food/<int:donation_id>')
def request_food(donation_id):
    if 'user_id' not in session:
        flash('Please login to request food', 'danger')
        return redirect('/login.html')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update donation status
    cursor.execute("UPDATE donations SET status = 'assigned' WHERE id = %s", (donation_id,))
    
    # Create request record
    cursor.execute("""
        INSERT INTO food_requests (donation_id, requester_id, status) 
        VALUES (%s, %s, 'pending')
    """, (donation_id, session['user_id']))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Food requested successfully! The donor will contact you.', 'success')
    return redirect('/dashboard')

# Send OTP
@app.route('/send-otp', methods=['POST'])
def send_otp():
    phone = request.form['phone']
    otp = random.randint(1000, 9999)
    
    # Store OTP in session (temporary)
    session['otp'] = otp
    session['otp_phone'] = phone
    
    # In production, send actual SMS here
    print(f"OTP for {phone}: {otp}")
    
    return jsonify({'status': 'success', 'otp': otp})

# Verify OTP
@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    phone = request.form['phone']
    user_otp = request.form['otp']
    
    if session.get('otp') and session.get('otp_phone') == phone and str(session['otp']) == user_otp:
        # Check if user exists
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE phone = %s", (phone,))
        user = cursor.fetchone()
        
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'User not found'})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid OTP'})

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)