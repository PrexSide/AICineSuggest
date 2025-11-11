import streamlit as st
import pandas as pd
from recommender.content_based import ContentBasedRecommender, load_movies

st.set_page_config(page_title="AI Movie Recommender", page_icon="🎬", layout="wide")

@st.cache_resource
def get_recommender():
	movies = load_movies()
	return ContentBasedRecommender(movies)

recommender = get_recommender()

st.title("🎬 AI-Powered Movie Recommendation System")

with st.sidebar:
	st.header("Search & Recommend")
	mode = st.radio("Mode", ["Search by keywords", "Similar to a movie"], index=0)
	top_k = st.slider("Results", 3, 20, 8)

if mode == "Search by keywords":
	query = st.text_input("Describe the kind of movie you want (keywords)", placeholder="dreams heist thriller, space survival, epic fantasy quest ...")
	if query:
		matches = recommender.search_titles(query, top_k=top_k)
		st.subheader("Top matches")
		for movie_id, title in matches:
			st.markdown(f"- **{title}** (id: {movie_id})")
else:
	title = st.text_input("Type a movie title to find similar ones", placeholder="Inception, The Matrix, Interstellar ...")
	if title:
		recs = recommender.recommend_similar(title, top_k=top_k, include_scores=True)
		if not recs:
			st.info("No matches found. Try another title or use keyword search.")
		else:
			st.subheader(f"Because you like: {title}")
			for r in recs:
				with st.container(border=True):
					left, right = st.columns([3, 1])
					with left:
						st.markdown(f"**{r['title']}** ({r.get('year', '')})")
						st.caption(r.get("genres", ""))
						if r.get("overview"):
							st.write(r["overview"])
					with right:
						if "score" in r:
							st.metric("Similarity", f"{r['score']:.2f}")

st.divider()
with st.expander("About this app"):
	st.markdown(
		"This demo uses a content-based approach (TF-IDF + cosine similarity) over movie metadata to recommend similar titles."
	)
