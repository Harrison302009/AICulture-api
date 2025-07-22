from flask import Flask, Response, render_template, jsonify, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import StandardScaler
import plotly.graph_objs as go
from plotly.offline import plot
from datetime import date
import calendar

db = SQLAlchemy()


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.secret_key = "197519792007200920112013514618161412"
db.init_app(app)
init_temp=25


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False)
    crops = db.relationship('Crop', backref='owner', lazy=True)

class Crop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crop_name = db.Column(db.String(100), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)
    image_name = db.Column(db.String(100), nullable=False)
    image_mimetype = db.Column(db.String(50), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    

with app.app_context():
    db.create_all()

@app.route('/api/data')
def index():
    return render_template('index.html')

@app.route("/login", methods=['POST', 'GET'])
def login():
    if 'user_id' in session:
        print("User already logged in, redirecting to dashboard")
        return redirect('/dashboard')
    else:
        print("Rendering login page")
        return render_template("login.html")

@app.route("/tables")
def tables():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    return jsonify(tables)

@app.route("/validate", methods=['POST', 'GET'])
def validate():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        existing_user = User.query.filter_by(email=email, password=password).first()
        if existing_user:
            session['user_id'] = existing_user.id
            session['user_email'] = existing_user.email
            session['user_password'] = existing_user.password
            session['name'] = existing_user.name
            print(f"User with email {email} and password ******** found.")
            return jsonify({"message": "User logged in successfully", "status": "success"}), 200
        else:
            print(f"No user found with email {email} and password *******.")
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": "Invalid Request"}), 500

@app.route('/signup_page', methods=['GET', 'POST'])
def signup_page():
    if 'user_id' in session:
        print("User already logged in, redirecting to dashboard")
        return redirect('/dashboard')
    else:
        print("Rendering signup page")
    return render_template("signup.html")

@app.route('/register', methods=['POST', 'GET'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"User with email {email} already exists.")
            return jsonify({"status": "error", "message": "User with this email already exists"}), 401
        print(f"Registering user with email: {email}, password: ********, name: {name}")
        new_user = User(email=email, password=password, name=name)
        db.session.add(new_user)
        db.session.commit()
        print(f"New user created with email: {email}")
        session['user_id'] = new_user.id
        session['user_email'] = new_user.email
        session['user_password'] = new_user.password
        session['name'] = new_user.name
        return jsonify({"message": "Registration successful", "status": "success"}), 200
    except Exception as e:
        print(f"Error parsing registration data: {e}")
        return jsonify({"status": "error", "message": "Invalid data"}), 400
    
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' in session:
        today = date.today()
        month = today.month
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        current_month = months[month]
        year = today.year
        current_period = f"{current_month} {year}"
        days_count = calendar.monthrange(year, month)[1]
        days = [str(day) for day in range(1, days_count + 1)]
        # For plotly graph
        # fig = go.Figure()
        # fig.add_trace(go.Scatter(x = days, y=[81, 80, 85, 85, 83, 82, 85, 86, 87, 84, 83, 82, 81, 83, 84, 83, 82, 80, 82, 83, 82, 90], mode='lines', name='Humidity'))
        # plotted_graph = plot(fig, output_type='div')
        df = pd.read_csv('weather.csv')
        df.dropna(inplace=True)
        temperature = df['Temperature'].tolist()
        humidity = df['Humidity'].tolist()
        precipitation = df['Precipitation'].tolist()
        wind = df['Wind'].tolist()
        print(f"temperature: {temperature}")
        return render_template('dashboard.html', name=session['name'], labels=days,  temperature=init_temp, current_date=current_period, temperature_data=temperature, humidity_data=humidity, precipitation_data=precipitation, wind_data=wind)
    else:
        print("User not logged in, redirecting to login page")
        return redirect('/login')
    
@app.route('/logout')
def logout():
    if 'user_id' in session:
        session.clear()
        return redirect('/api/data')
    
@app.route('/weather_data', methods=['GET', 'POST'])
def weather_data():
    if 'user_id' in session:
        df = pd.read_csv('weather.csv')
        df.dropna(inplace=True)
        df = df[df['Temperature'] < 70]
        X = df[['Humidity', 'Precipitation', 'Wind']]
        y = df['Temperature']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3)
        model = LinearRegression()
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        mse = mean_squared_error(y_test, predictions)
        errors = predictions - y_test
        print(errors.describe())
        rounded_mse = round(mse, 1)
        global init_temp
        init_temp = rounded_mse
        return redirect('/dashboard')

@app.route('/crop_monitor', methods=['GET', 'POST'])
def crop_monitor():
    if 'user_id' in session:
        crops = Crop.query.filter_by(owner_id=session['user_id']).all()
        return render_template('crop_monitor.html', crops=crops)
    else:
        print("User not logged in, redirecting to login page")
        return redirect('/login')        

@app.route('/crop_image/<int:crop_id>')
def crop_image(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    return Response(
        crop.image_data,
        mimetype=crop.image_mimetype,
        headers={"Content-Disposition": f"inline; filename={crop.image_name}"}
    )

@app.route('/upload_crop', methods=['POST'])
def upload_crop():
    if 'user_id' in session:
        try:
            file = request.files['cropimage']
            name = request.form['cropname']
            if file and name:
                existing_crop = Crop.query.filter_by(crop_name=name).first()
                if existing_crop:
                    print(f"Crop with name {name} already exists.")
                    return jsonify({"status": "error", "message": "Crop with this name already exists"}), 401
                new_crop = Crop(crop_name=name, owner_id=session['user_id'], image_data=file.read(), image_name=file.filename, image_mimetype=file.mimetype)
                db.session.add(new_crop)
                db.session.commit()
                print("New crop uploaded successfully.")
                return redirect('/crop_monitor')
        except Exception as e:
            print(f"Error uploading crop image: {e}")
            return jsonify({"status": "error", "message": "Invalid data"}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
