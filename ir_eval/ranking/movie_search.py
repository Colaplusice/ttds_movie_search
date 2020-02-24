import pickle
from pathlib import Path
import numpy as np
import sys
from db.DB import get_db_instance
from collections import defaultdict
import math
import time
from ir_eval.utils.score_tracker import ScoreTracker, NaiveScoreTracker

MAX_INDEX_SPLITS = 52  # maximum number of different entries in the inverted_index with the same term
# TODO: update the below with total number of movies having at least one term (movies with subtitles)
TOTAL_NUMBER_OF_MOVIES = 120000
batch_size = 20
db = get_db_instance()

# TODO: add a pickle file containing an actual dictionary of movie term counts
movie_term_counts = defaultdict(lambda: 1)
try:
    pickle_path = Path(__file__).parent.absolute() / 'pickles' / 'movie_term_counts.p'
    movie_term_counts = pickle.load(open(pickle_path, 'rb'))
except:
    print("No valid pickle file with movie term counts found. Movie search may not work properly...")



def tfidf(index_movie, total_movie_count_for_term):
    """
    Computes TFIDF score for a document-term pair.
    :param index_movie: movie from inverted index, containing {'_id': string, 'doc_count': int)
    :param total_doc_count: total number of
    :return:
    """
    return tf(index_movie) * idf(total_movie_count_for_term)

def tf(index_movie):
    """
    TF: Term Frequency, which measures how frequently a term occurs in a document. Since every document is different in
    length, it is possible that a term would appear much more times in long documents than shorter ones. Thus, the term
    frequency is often divided by the document length (aka. the total number of terms in the document) as a way of
    normalization:

    TF(t) = (Number of times term t appears in a document) / (Total number of terms in the document).
    """
    return 1.0 * index_movie['doc_count'] / movie_term_counts[index_movie['_id']]


def idf(total_movie_count_for_term):
    """
    DF: Inverse Document Frequency, which measures how important a term is. While computing TF, all terms are considered
    equally important. However it is known that certain terms, such as "is", "of", and "that", may appear a lot of times
    but have little importance. Thus we need to weigh down the frequent terms while scale up the rare ones, by computing
    the following:

    IDF(t) = log_e(Total number of documents / Number of documents with term t in it).
    """

    return math.log(1.0 * TOTAL_NUMBER_OF_MOVIES / total_movie_count_for_term)


def movie_search(query_params, number_results):
    tracker = movie_ranking_query_TFIDF(query_params)
    return tracker.get_top(number_results, skip=0)  # TODO: add pagination here

def movie_ranking_query_TFIDF(query_params):
    tracker = NaiveScoreTracker()  # there's no more than 220k movies, so we can fit all the scores in main memory
    terms = query_params['query']
    # Prepare advanced search if any filters are provided
    filtered_movies = None
    if len(query_params['movie_title']) > 0 or len(query_params['year']) > 0 or len(query_params['actor']) > 0:
        print('advanced search')
        filtered_movies = db.get_movie_ids_advanced_search(query_params)

    for term in terms:
        # Setup
        list_of_indexes = list(db.get_indexed_movies_by_term(term))
        total_movie_count = 0
        for index in list_of_indexes:
            total_movie_count += len(index['movies'])

        print(f"term {term} movie count: {total_movie_count}")

        # Compute
        for index in list_of_indexes:
            total_doc_count = index['doc_count']
            for movie in index['movies']:
                score = tfidf(movie, total_doc_count)
                tracker.add_score(movie['_id'], score)

    if filtered_movies is not None:  # Filter
        for id in list(tracker.scores.keys()):
            if id not in filtered_movies:
                tracker.scores.pop(id, None)

    return tracker


if __name__ == '__main__':

    db = get_db_instance()

    query_params = {'query': ["luke", "father"], 'movie_title': '', 'year': '', 'actor': ''}
    start = time.time()
    tracker = movie_ranking_query_TFIDF(query_params)
    end = time.time()
    print(end-start)
    print(tracker.get_top(10))

    query_params = {"year": "2000-2001", 'query': ["luke", "father"], 'movie_title': '', 'actor': ''}
    start = time.time()
    tracker = movie_ranking_query_TFIDF(query_params)
    end = time.time()
    print(end-start)
    print(tracker.get_top(10))
