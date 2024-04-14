import time
import requests
import json

import imdb

ia = imdb.Cinemagoer()

def scraping_delay():
    time.sleep(1.5)

class MovieNotFoundException(Exception):
    pass


def fetch_basics_from_imdb(query:str):
    """Given a search query, search imdb and return 
    the id of the first result."""
    movies = ia.search_movie(query)
    scraping_delay()
    try:
        prohibited_kinds = ["tv series", "tv special", "tv mini series"]
        movies = [m for m in movies if m["kind"] not in prohibited_kinds]
        return movies[0]
    except IndexError:
        raise MovieNotFoundException(query)

def fetch_details_from_imdb(imdb_id):
    data = ia.get_movie(imdb_id)
    scraping_delay()
    return data

def generate_content_summary(imdb_id):
    """Given an imdb id, return a personalized (for me, the author) string
    summarizing imdb.com's "parental guide". """
    LOW_DATA_STRING = "Not enough data"
    complaint_list = []
    response = ia.get_movie_parents_guide(imdb_id)
    time.sleep(1.5)
    vote_dict = response["data"]["advisory votes"]
    try:
        if sum(vote_dict["frightening"]["votes"].values()) < 20:
            return LOW_DATA_STRING
    except KeyError:
        return LOW_DATA_STRING

    if vote_dict["violence"]["status"] == "Severe":
        complaint_list += "Intense violence",
    if vote_dict["nudity"]["status"] == "Severe":
        complaint_list += "Abundant sexual content",
    elif vote_dict["nudity"]["status"] == "Moderate":
        complaint_list += "Some sexual content",
    if vote_dict["profanity"]["status"] == "Severe":
        complaint_list += "Abundant swearing",
    elif vote_dict["profanity"]["status"] == "Moderate":
        complaint_list += "Some swearing",
    if vote_dict["violence"]["status"] == "Moderate":
        complaint_list += "Some violence",
    
    if len(complaint_list):
        return "; ".join(complaint_list)
    else:
        return "Ok"
    
def fetch_letterboxd(imdb_id):
    """Given an imdb id, go to the letterboxd page for that movie,
    and return all the data, as a json."""
    page = requests.get(f"https://letterboxd.com/imdb/{imdb_id}")
    time.sleep(1.5)
    lines = page.content.decode().split("\n")
    for i, line in enumerate(lines):
        if "<![CDATA[" in line:
            json_line = lines[i+1]
            break
    return json.loads(json_line)

def fetch_justwatch(imdb_id):
    return {} #not implemented yet


