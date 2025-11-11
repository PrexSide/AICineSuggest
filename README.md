## AI-Powered Movie Recommendation System

A minimal, fully offline content-based movie recommender with both Streamlit and Flask web UIs.

### Features
- Keyword search over title/overview/genres/cast/director/year
- "Similar to this movie" recommendations using TF-IDF + cosine similarity
- Streamlit app for quick prototyping
- Flask website with HTML templates and JSON APIs

### Setup

1) Ensure Python 3.10+ is installed (Python 3.13 supported).
2) Install dependencies:

```powershell
pip install -r requirements.txt
```

If you hit wheel errors on Windows, upgrade build tools and let pip choose compatible wheels automatically:

```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Optionally use a fresh virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Run the Streamlit app

```powershell
streamlit run app.py
```

### Run the Flask website

```powershell
python web/app_web.py
```

- Visit `http://localhost:8000`
- JSON APIs: `GET /api/search?q=...&k=8`, `GET /api/similar?title=...&k=8`

### Extend the dataset
Edit `data/movies.csv` to add more rows with the following columns:
- `movie_id` (int)
- `title` (str)
- `genres` (pipe-separated optional)
- `overview` (str)
- `cast` (pipe-separated optional)
- `director` (pipe-separated optional)
- `year` (int)

### Notes
- This is a content-based model; it does not use collaborative filtering.
- For larger datasets, consider persisting the TF-IDF model and using approximate nearest neighbors for faster queries.
