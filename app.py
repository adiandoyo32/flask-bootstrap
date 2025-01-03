from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import math

app = Flask(__name__)
app.secret_key = 'secret_key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'mikrotik'

mysql = MySQL(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@app.route('/login',  methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('You are already logged in!', 'info')
        return redirect(url_for('home'))
      
    if request.method == 'POST':
          username = request.form['username']
          password = request.form['password']
          
          cur = mysql.connection.cursor()
          cur.execute("SELECT * FROM users WHERE username=%s", (username,))
          user = cur.fetchone()
          cur.close()
          
          if user and bcrypt.check_password_hash(user[2], password):
              login_user(User(id=user[0], username=user[1]))
              flash('Login successful!', 'success')
              return redirect(url_for('home'))
          else:
              flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', title="Login")
  
@login_manager.user_loader
def load_user(user_id):
      cur = mysql.connection.cursor()
      cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
      user = cur.fetchone()
      cur.close()
      if user:
          return User(id=user[0], username=user[1])
      return None
  
@app.route('/register',  methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
          print(current_user)
          flash('You are already logged in!', 'info')
          return redirect(url_for('home'))
      
    if request.method == 'POST':
          username = request.form['username']
          password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
          
          cur = mysql.connection.cursor()
          cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
          mysql.connection.commit()
          cur.close()
          
          flash('Registration successful. Please login.', 'success')
          return redirect(url_for('login'))
    return render_template('auth/register.html', title="Register")

@app.route('/')
@login_required
def home():
    search = request.args.get('search')
    page = int(request.args.get('page', 1))  # Current page (default 1)
    per_page = 10  # Results per page
    offset = (page - 1) * per_page  # Calculate OFFSET for SQL query
    
    cur = mysql.connection.cursor()
    
    # Count total matching records
    if search:
        count_query = "SELECT COUNT(*) FROM history WHERE username LIKE %s OR port LIKE %s"
        cur.execute(count_query, (f"%{search}%", f"%{search}%"))
    else:
        count_query = "SELECT COUNT(*) FROM history"
        cur.execute(count_query)
    
    total_results = cur.fetchone()[0]
    print(total_results)
    total_pages = math.ceil(total_results / per_page)
    
    # Fetch paginated results
    if search:
        query = """SELECT history.*, users.username FROM history
            LEFT JOIN users ON users.id = history.user_id
            WHERE history.username LIKE %s OR port LIKE %s
            LIMIT %s OFFSET %s
        """
        cur.execute(query, (f"%{search}%", f"%{search}%", per_page, offset))
    else:
      query = """
          SELECT history.*, users.username FROM history
          LEFT JOIN users ON users.id = history.user_id
          LIMIT %s OFFSET %s
      """
      cur.execute(query, (per_page, offset))
    history = cur.fetchall()
    cur.close()
    return render_template(
      'home/home.html',
      title="Home",
      user=current_user,
      histories=history,
      search=search,
      page=page,
      total_pages=total_pages
    )

@app.route('/add-user', methods=['GET', 'POST'])
@login_required
def addUser():
    if request.method == 'POST':
          username = request.form['username']
          password = request.form['password']
          port = request.form['port']
          group = request.form['group']
          print('curernt user')
          print(current_user.username)
          cur = mysql.connection.cursor()
          cur.execute("INSERT INTO `history` (`user_id`, `username`, `password`, `port`, `group`, `is_connected`) VALUES (%s, %s, %s, %s, %s, %s)", (current_user.id, username, password, port, group, 1))
          mysql.connection.commit()
          cur.close()
          flash('User added successfully!')
          return redirect(url_for('home'))
    return render_template('home/add-user.html',title="Add User")

@app.route('/block-by-port')
@login_required
def blockByPort():
    return render_template('home/block-by-port.html', title="Block by Port")
  
# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ =='__main__':
	app.run(debug=True)