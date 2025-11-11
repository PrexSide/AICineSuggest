from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os, sys, requests
from functools import lru_cache
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from recommender.content_based import ContentBasedRecommender, load_movies

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(80), unique=True, nullable=True)
	email = db.Column(db.String(120), unique=True, nullable=False)
	password_hash = db.Column(db.String(120), nullable=False)

@login_manager.user_loader
def load_user(user_id):
	return User.query.get(int(user_id))

# Lazy init recommender
_recommender = None


def get_recommender():
	global _recommender
	if _recommender is None:
		movies = load_movies()
		_recommender = ContentBasedRecommender(movies)
	return _recommender


def get_movies_df():
	return get_recommender().movies_df


@lru_cache(maxsize=2048)
def fetch_poster_omdb(title: str):
	api_key = os.getenv("OMDB_API_KEY", "")
	if not api_key or not title:
		return None
	try:
		resp = requests.get(
			"https://www.omdbapi.com/",
			params={"t": title, "apikey": api_key},
			timeout=5,
		)
		if resp.status_code == 200:
			data = resp.json()
			poster = data.get("Poster")
			return poster if poster and poster != "N/A" else None
	except Exception:
		return None
	return None


def list_all_genres():
	genres_series = get_movies_df().get("genres")
	if genres_series is None:
		return []
	all_genres = set()
	for g in genres_series.fillna(""):
		for token in str(g).split("|"):
			token = token.strip()
			if token:
				all_genres.add(token)
	return sorted(all_genres)


@app.route("/")
def home():
	if current_user.is_authenticated:
		return render_template("welcome.html")
	return redirect(url_for('login'))

@app.route("/login", methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('welcome'))
	
	if request.method == 'POST':
		email = request.form['email']
		password = request.form['password']
		user = User.query.filter_by(email=email).first()
		
		if user and check_password_hash(user.password_hash, password):
			login_user(user)
			return redirect(url_for('welcome'))
		else:
			return render_template("auth.html", signup=False, error="Invalid email or password")
	
	return render_template("auth.html", signup=False)

@app.route("/signup", methods=['GET', 'POST'])
def signup():
	if current_user.is_authenticated:
		return redirect(url_for('welcome'))
	
	if request.method == 'POST':
		username = request.form.get('username')
		email = request.form['email']
		password = request.form['password']
		
		if User.query.filter_by(email=email).first():
			return render_template("auth.html", signup=True, error="Email already registered")
		
		user = User(
			username=username,
			email=email,
			password_hash=generate_password_hash(password)
		)
		db.session.add(user)
		db.session.commit()
		
		login_user(user)
		return redirect(url_for('welcome'))
	
	return render_template("auth.html", signup=True)

@app.route("/logout")
@login_required
def logout():
	logout_user()
	return redirect(url_for('login'))


@app.route("/welcome")
@login_required
def welcome():
	return render_template("welcome.html")

@app.route("/discover")
@login_required
def discover():
	return render_template("index.html", genres=list_all_genres())

@app.route("/mood")
@login_required
def mood():
	# Slider 0..100 maps to moods and query tokens
	level = int(request.args.get("level", 50))
	# Buckets: 0-20 Happy, 20-40 Romantic, 40-60 Nostalgic, 60-80 Dark, 80-100 Intense
	if level < 20:
		label, tokens = "Happy", ["feel-good comedy", "uplifting", "family"]
	elif level < 40:
		label, tokens = "Romantic", ["romance drama", "romantic comedy", "love story"]
	elif level < 60:
		label, tokens = "Nostalgic", ["classic adventure", "coming-of-age", "nostalgia"]
	elif level < 80:
		label, tokens = "Dark", ["psychological thriller", "crime drama", "noir"]
	else:
		label, tokens = "Intense", ["action sci-fi", "high stakes", "survival"]

	# Join tokens as a query and search
	query = " ".join(tokens)
	top_k = int(request.args.get("k", 12))
	results = get_recommender().search_titles(query, top_k=top_k)

	# Enrich rows
	df = get_movies_df()
	rows = []
	for mid, title in results:
		row = df[df["movie_id"] == mid].iloc[0].to_dict()
		row["poster"] = fetch_poster_omdb(row.get("title", ""))
		rows.append(row)

	return render_template("mood.html", level=level, label=label, results=rows)


@app.route("/search")
@login_required
def search():
	q = request.args.get("q", "").strip()
	top_k = int(request.args.get("k", 12))
	# Filters
	genre = request.args.get("genre", "").strip()
	year_min = request.args.get("year_min")
	year_max = request.args.get("year_max")
	sort = request.args.get("sort", "relevance")

	results = get_recommender().search_titles(q, top_k=top_k if q else top_k)

	# Convert to full rows for filtering/sorting
	df = get_movies_df()
	rows = []
	for mid, title in results:
		row = df[df["movie_id"] == mid].iloc[0].to_dict()
		row["poster"] = fetch_poster_omdb(row.get("title", ""))
		rows.append(row)

	# Apply filters
	if genre:
		rows = [r for r in rows if genre in str(r.get("genres", "")).split("|")]
	if year_min and str(year_min).isdigit():
		ymin = int(year_min)
		rows = [r for r in rows if str(r.get("year", "")).isdigit() and int(r["year"]) >= ymin]
	if year_max and str(year_max).isdigit():
		ymax = int(year_max)
		rows = [r for r in rows if str(r.get("year", "")).isdigit() and int(r["year"]) <= ymax]

	# Sorting
	if sort == "year_desc":
		rows.sort(key=lambda r: int(r["year"]) if str(r.get("year", "")).isdigit() else -9999, reverse=True)
	elif sort == "year_asc":
		rows.sort(key=lambda r: int(r["year"]) if str(r.get("year", "")).isdigit() else 9999)
	elif sort == "title":
		rows.sort(key=lambda r: str(r.get("title", "")).lower())
	# else relevance: keep original order

	return render_template("results.html", query=q, results=rows, genres=list_all_genres(), selected_genre=genre, year_min=year_min or "", year_max=year_max or "", sort=sort)


@app.route("/similar")
@login_required
def similar():
	title = request.args.get("title", "").strip()
	top_k = int(request.args.get("k", 12))
	genre = request.args.get("genre", "").strip()
	year_min = request.args.get("year_min")
	year_max = request.args.get("year_max")
	sort = request.args.get("sort", "relevance")

	recs = get_recommender().recommend_similar(title, top_k=top_k, include_scores=True)

	# Enrich + filter
	rows = []
	df = get_movies_df()
	for r in recs:
		row = r.copy()
		row["poster"] = fetch_poster_omdb(r.get("title", ""))
		rows.append(row)

	if genre:
		rows = [r for r in rows if genre in str(r.get("genres", "")).split("|")]
	if year_min and str(year_min).isdigit():
		ymin = int(year_min)
		rows = [r for r in rows if str(r.get("year", "")).isdigit() and int(r["year"]) >= ymin]
	if year_max and str(year_max).isdigit():
		ymax = int(year_max)
		rows = [r for r in rows if str(r.get("year", "")).isdigit() and int(r["year"]) <= ymax]

	if sort == "year_desc":
		rows.sort(key=lambda r: int(r["year"]) if str(r.get("year", "")).isdigit() else -9999, reverse=True)
	elif sort == "year_asc":
		rows.sort(key=lambda r: int(r["year"]) if str(r.get("year", "")).isdigit() else 9999)
	elif sort == "title":
		rows.sort(key=lambda r: str(r.get("title", "")).lower())
	elif sort == "relevance":
		rows.sort(key=lambda r: float(r.get("score", 0.0)), reverse=True)

	return render_template("similar.html", title=title, recs=rows, genres=list_all_genres(), selected_genre=genre, year_min=year_min or "", year_max=year_max or "", sort=sort)


# JSON APIs
@app.route("/api/search")
@login_required
def api_search():
	q = request.args.get("q", "").strip()
	top_k = int(request.args.get("k", 8))
	results = get_recommender().search_titles(q, top_k=top_k)
	return jsonify({"query": q, "results": [{"movie_id": mid, "title": t} for mid, t in results]})


@app.route("/api/similar")
@login_required
def api_similar():
	title = request.args.get("title", "").strip()
	top_k = int(request.args.get("k", 8))
	recs = get_recommender().recommend_similar(title, top_k=top_k, include_scores=True)
	return jsonify({"title": title, "results": recs})


@app.route("/api/autocomplete")
@login_required
def api_autocomplete():
	prefix = request.args.get("prefix", "").strip().lower()
	if not prefix:
		return jsonify({"results": []})
	df = get_movies_df()
	titles = df["title"].astype(str).tolist()
	matches = [t for t in titles if t.lower().startswith(prefix)]
	return jsonify({"results": matches[:10]})


if __name__ == "__main__":
	with app.app_context():
		db.create_all() 
	port = int(os.environ.get("PORT", 5000))  
	app.run(host="0.0.0.0", port=port, debug=False)
