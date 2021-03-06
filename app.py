import os
import uuid
import json
import requests
from flask_login import UserMixin
from pusher import Pusher
from operator import methodcaller
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager 
from newsapi.newsapi_client import NewsApiClient
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, current_user, logout_user, login_required
from flask import Blueprint, Flask, render_template, request, jsonify, redirect, url_for, request, flash

db = SQLAlchemy()
app = Flask(__name__, template_folder='templates')

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = os.environ.get("OAUTHLIB_INSECURE_TRANSPORT")
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("SQL_DB_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["DISCORD_CLIENT_ID"] = os.environ.get("DISCORD_CLIENT_ID")
app.config["DISCORD_CLIENT_SECRET"] = os.environ.get("DISCORD_CLIENT_SECRET")            

login_manager = LoginManager()
login_manager.login_view = 'app.login'
login_manager.init_app(app)

db.init_app(app)

with app.app_context():

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    db.create_all()

class History(UserMixin, db.Model):
   
    __tablename__ = "history"
    id = db.Column(db.Integer, primary_key =  True)
    email = db.Column(db.String, db.ForeignKey("user.email"))
    post_id = db.Column(db.Integer)
    title = db.Column(db.String(50))
    content = db.Column(db.String(300))
    status = db.Column(db.String(10))
    event_name = db.Column(db.String(20))
    def __repr__(self):
        return '<History %r>' % self.id

class User(UserMixin, db.Model):

    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    age = db.Column(db.Integer)
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    country = db.Column(db.String(100))
    bmi = db.Column(db.Float)
    dob = db.Column(db.String(12))
    gender = db.Column(db.String(20))
    post = db.relationship('History', backref = db.backref('posts'))
    email = db.Column(db.String(100), unique = True)
    diet = db.Column(db.String(100))
    calories = db.Column(db.Integer)
    mealplan = db.Column(db.String(20000))
    
    def __repr__(self):
        return '<User %r>' % self.email

@app.route('/login')
def login():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    user = User.query.filter_by(email = email).first()
    if not user or not check_password_hash(user.password, password): 
        flash('Please check your login details and try again.')
        return redirect(url_for('login')) 
    login_user(user)
    return redirect(url_for('profile'))

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/signup', methods = ['POST'])
def signup_post():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    confirm_password = request.form.get('confpassword')
    user = User.query.filter_by(email = email).first()
    if user:   
        flash('Email address already exists')
        return redirect(url_for('signup'))
    if password != confirm_password:
        flash('Password does not match!')
        return redirect(url_for('signup'))
    new_user = User(email = email, name = name, password = generate_password_hash(password, method = 'sha256'))
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

pusher = Pusher(
      app_id = os.environ.get("PUSHER_ID"),
      key = os.environ.get("PUSHER_KEY"),
      secret = os.environ.get("PUSHER_SECRET"),
      cluster = os.environ.get("PUSHER_CLUSTER"),  
      ssl = True
    )

@app.route('/', methods=['GET', 'POST'])
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/profile')
@login_required
def profile():
    newsapi_client = NewsApiClient(api_key = os.environ.get("NEWSAPI_APIKEY"))
    top_headlines = newsapi_client.get_top_headlines(q = os.environ.get("NEWS_Q"), category = os.environ.get("NEWS_CAT"))
    newsData = []
    for article in top_headlines["articles"]:
        newsData.append({"title" : article["title"],
                         "url": article["url"],
                         "urlToImage" : article["urlToImage"],
                         "description": article["description"],
                         "author": article["author"]})
    return render_template('profile.html', name = current_user.name, feed = newsData[:4])

@app.route('/news')
@login_required
def news():
    newsapi_client = NewsApiClient(api_key = os.environ.get("NEWSAPI_APIKEY"))
    top_headlines = newsapi_client.get_top_headlines(q = os.environ.get("NEWS_Q"),category = os.environ.get("NEWS_CAT"))
    newsData = []
    for article in top_headlines["articles"]:
        newsData.append({"title" : article["title"], "url": article["url"], "urlToImage" : article["urlToImage"]})
    return render_template('news.html', name = current_user.name, feed = newsData[:20])

@app.route('/community')
@login_required
def community():
    return render_template('community.html')

@app.route('/team')
@login_required
def team():
    return render_template('team.html')

@app.route('/blog')
@login_required
def blog():
    return render_template('blog.html')

@app.route('/personal')
@login_required
def personal():
    email = current_user.email
    history = User.query.filter_by(email = email).first().post
    return render_template('personal.html', history = history)

@app.route('/planner')
@login_required
def planner():
    mealplan = current_user.mealplan
    return render_template('diet.html', mealplan=json.loads(mealplan))

@app.route('/about')
@login_required
def about():
    email = current_user.email
    user = User.query.filter_by(email = email).first()
    return render_template('about.html', user = user)

@app.route("/updateprof")
@login_required
def updateProfile():
    email = current_user.email
    user = User.query.filter_by(email = email).first()
    return render_template("update_profile.html", user_det = user)

@app.route("/updatedb", methods=["POST"])
@login_required
def updateDb():
    email = current_user.email
    password = request.form.get("password") if request.form.get("password") else current_user.password
    age = request.form.get("age") if request.form.get("age") else current_user.age
    height = request.form.get("height") if request.form.get("height") else current_user.height
    weight = request.form.get("weight") if request.form.get("weight") else current_user.weight
    bmi = current_user.bmi if current_user.bmi else round(float(weight)/(float(height)/100)**2)
    country = request.form.get("country") if request.form.get("country") else current_user.country
    dob = request.form.get("dob") if request.form.get("dob") else current_user.dob
    gender = request.form.get("gender") if request.form.get("gender") else current_user.gender
    calories = request.form.get("calories") if request.form.get("calories") else current_user.calories
    diet = request.form.get("diet") if request.form.get("diet") else current_user.diet
    if current_user.mealplan:
        mealplan = current_user.mealplan
    else:
        parameters = {
        "timeFrame": os.environ.get("FOOD_TIMEFRAME"),
        "targetCalories":calories,
        "diet":diet,
        "hash":os.environ.get("FOOD_API_HASH"),
        "apiKey":os.environ.get("FOOD_API_APIKEY")
        }
        response = requests.get("https://api.spoonacular.com/mealplanner/generate", params = parameters)
        data = json.loads(response.text)
        mealplan = json.dumps(data)

    update_user = User.query.filter_by(email=email).update(dict(
    password = password,
    age = age, 
    height = height,
    weight = weight,
    bmi = bmi,
    country = country,
    dob = dob,
    gender = gender,
    diet = diet,
    calories = calories,
    mealplan = mealplan))
    db.session.commit()
    return redirect(url_for("app.about"))
    
@app.route('/post', methods=['POST'])
@login_required
def addPost():
    data = {
    'id': "post-{}".format(uuid.uuid4().hex),
    'title': request.form.get('title'),
    'content': request.form.get('content'),
    'status': 'active',
    'event_name': 'created'
    }
    pusher.trigger("blog", "post-added", data)
    email = current_user.email
    user = User.query.filter_by(email=email).first()
    new_post = History(
        email = email,
        post_id = data["id"],
        title = data["title"],
        content = data["content"],
        status = data["status"],
        event_name = data["event_name"],
        posts = user
    )
    db.session.add(new_post)
    db.session.commit()
    return jsonify(data)

@app.route('/post/<id>', methods=['PUT','DELETE'])
@login_required
def updatePost(id):
    data = { 'id': id }
    if request.method == 'DELETE':
        data['event_name'] = 'deleted'
        pusher.trigger("blog", "post-deleted", data)
    else:
        data['event_name'] = 'deactivated'
        pusher.trigger("blog", "post-deactivated", data)
    return jsonify(data)

if __name__ == "__main__":
    app.run(port=5000)