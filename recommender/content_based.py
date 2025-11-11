import os
from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ContentBasedRecommender:
	"""Simple TF-IDF + cosine similarity recommender for movies.

	This model builds a text corpus combining multiple metadata fields
	(e.g., overview, genres, cast, director) and computes similarities.
	"""

	def __init__(self, movies_df: pd.DataFrame) -> None:
		self.movies_df = movies_df.copy()
		self.movies_df.fillna("", inplace=True)

		# Build combined text field
		self.movies_df["combined_text"] = self.movies_df.apply(
			lambda row: " ".join([
				str(row.get("title", "")),
				str(row.get("overview", "")),
				str(row.get("genres", "")),
				str(row.get("cast", "")),
				str(row.get("director", "")),
				str(row.get("year", "")),
			]),
			axis=1,
		)

		self._vectorizer = TfidfVectorizer(
			stop_words="english",
			max_features=5000,
			ngram_range=(1, 2),
		)
		self._tfidf_matrix = self._vectorizer.fit_transform(self.movies_df["combined_text"])  # sparse matrix

		# Build title index for quick lookup
		self._title_to_index = {t.lower(): i for i, t in enumerate(self.movies_df["title"].astype(str))}

	def search_titles(self, query: str, top_k: int = 10) -> List[Tuple[int, str]]:
		"""Return top_k titles whose combined text is most similar to the query."""
		if not query:
			return []
		query_vec = self._vectorizer.transform([query])
		sims = cosine_similarity(query_vec, self._tfidf_matrix).ravel()
		indices = np.argsort(-sims)[:top_k]
		return [(int(self.movies_df.iloc[i]["movie_id"]), str(self.movies_df.iloc[i]["title"])) for i in indices]

	def recommend_similar(self, title: str, top_k: int = 5, include_scores: bool = False):
		"""Recommend movies similar to the given title.

		Returns list of dicts with movie metadata. If include_scores is True, adds similarity score.
		"""
		if not title:
			return []
		idx = self._title_to_index.get(title.lower())
		if idx is None:
			# Try fuzzy match via vector space using the title string itself
			matches = self.search_titles(title, top_k=1)
			if not matches:
				return []
			match_movie_id = matches[0][0]
			idx = int(self.movies_df.index[self.movies_df["movie_id"] == match_movie_id][0])

		target_vec = self._tfidf_matrix[idx]
		sims = cosine_similarity(target_vec, self._tfidf_matrix).ravel()
		# Exclude self
		sims[idx] = -1.0
		indices = np.argsort(-sims)[:top_k]

		recs = []
		for i in indices:
			row = self.movies_df.iloc[i]
			item = {
				"movie_id": int(row["movie_id"]),
				"title": str(row["title"]),
				"genres": str(row.get("genres", "")),
				"overview": str(row.get("overview", "")),
				"director": str(row.get("director", "")),
				"year": int(row.get("year", 0)) if str(row.get("year", "")).isdigit() else row.get("year", ""),
			}
			if include_scores:
				item["score"] = float(sims[i])
			recs.append(item)
		return recs


def load_movies(csv_path: str = "data/movies.csv") -> pd.DataFrame:
	if not os.path.exists(csv_path):
		raise FileNotFoundError(f"Movies CSV not found at {csv_path}")
	return pd.read_csv(csv_path)
