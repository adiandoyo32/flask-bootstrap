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

def getTotalPage(cur, per_page, search):
    # Count total matching records
    if search:
        count_query = """
          SELECT COUNT(*) FROM history
          LEFT JOIN users ON users.id = history.user_id
          WHERE users.username LIKE %s OR history.username LIKE %s OR port LIKE %s
        """
        cur.execute(count_query, (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        count_query = "SELECT COUNT(*) FROM history"
        cur.execute(count_query)
    total_results = cur.fetchone()[0]
    total_pages = math.ceil(total_results / per_page)
    
    return total_pages
  
def searchHistory(cur, sort_column, sort_order, per_page, offset, search):
    # Fetch paginated results
    if search:
        query = f"""SELECT history.*, users.username FROM history
            LEFT JOIN users ON users.id = history.user_id
            WHERE users.username LIKE %s OR history.username LIKE %s OR port LIKE %s
            ORDER BY {sort_column} {sort_order}
            LIMIT {per_page} OFFSET {offset}
        """
        cur.execute(query, (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
      query = f"""
          SELECT history.*, users.username FROM history
          LEFT JOIN users ON users.id = history.user_id
          ORDER BY {sort_column} {sort_order}
          LIMIT {per_page} OFFSET {offset}
      """
      cur.execute(query)
    results = cur.fetchall()
    
    return results

# Mapping for sort keys
SORT_MAP = {
  'username': 'history.username',
  'port': 'port',
  'group': 'history.group',
  'date': 'created_at'
}

@app.route('/')
@login_required
def home():
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    per_page = 10  # Results per page
    offset = (page - 1) * per_page  # Calculate OFFSET for SQL query
    
    # Sorting parameters
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Ensure valid sorting columns and orders
    if sort_by not in SORT_MAP:
        sort_by = 'created_at'
    sort_column = SORT_MAP[sort_by]
    print(sort_column)
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'
        
    cur = mysql.connection.cursor()
    
    total_pages = getTotalPage(cur, per_page, search)
    results = searchHistory(cur, sort_column, sort_order, per_page, offset, search)
    
    histories = [
      {
        'admin': row[8],
        'username': row[2],
        'port': row[4],
        'group': row[5],
        'connected': row[6],
        'date': row[7]
      } for row in results
    ]

    cur.close()
    return render_template(
      'home/home.html',
      title="Home",
      user=current_user,
      histories=histories,
      search=search,
      page=page,
      total_pages=total_pages,
      sort_by=sort_by,
      sort_order=sort_order
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
  
@app.route('/customers')
@login_required
def customers():
    return render_template('home/customers.html', title="Customer", data=[])
  
# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ =='__main__':
	app.run(debug=True)