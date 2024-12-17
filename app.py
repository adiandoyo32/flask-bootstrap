from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home/home.html',title="Home")

@app.route('/add-user')
def addUser():
    return render_template('home/add-user.html',title="Add User")

@app.route('/block-by-port')
def blockByPort():
    return render_template('home/block-by-port.html', title="Block by Port")

if __name__ =='__main__':
	app.run(debug=True)