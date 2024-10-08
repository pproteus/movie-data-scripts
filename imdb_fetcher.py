import time
import requests
import json
import re

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
        prohibited_kinds = ["tv series", "tv special", "tv mini series", "tv movie", "video movie"]
        #if you were hoping to search for a real tv movie, that's understandable, 
        #but false positives are far less likely if these are excluded
        movies = [m for m in movies if m["kind"] not in prohibited_kinds]
        return movies[0]
    except IndexError:
        raise MovieNotFoundException(query)

def fetch_details_from_imdb(imdb_id):
    data = ia.get_movie(imdb_id)
    scraping_delay()
    return data

def generate_content_summary(imdb_id):
    """Given an imdb id, return a summary string
    for imdb.com's "parental guide". """
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

def fetch_letterboxd_dictionary(letterboxd_url):
    "Return all letterboxd page data, as a json."
    page = requests.get(letterboxd_url)
    scraping_delay()
    lines = page.content.decode().split("\n")
    for i, line in enumerate(lines):
        if "<![CDATA[" in line:
            json_line = lines[i+1]
        if "www.imdb.com" in line:
            imdb_line = line
    try:
        dict = json.loads(json_line)
    except UnboundLocalError:
        #if you pass a handwritten list as though it was a letterboxd list,
        #this page will not be a proper movie page, but letterboxd may still handle it
        #but there's not going to be proper data here so we have to stop.
        raise MovieNotFoundException("Hint: Are you sure this input list wasnt handwritten?")
    dict["IMDB_ID"] = re.findall(r"tt(\d+)", imdb_line)[0]
    return dict
    
def fetch_letterboxd_from_imdb_id(imdb_id):
    """Given an imdb id, go to the letterboxd page for that movie,
      and return all the data, as a json."""
    url = f"https://letterboxd.com/imdb/{imdb_id}"
    return fetch_letterboxd_dictionary(url)

def fetch_letterboxd_from_page_string(page_string):
    url = f"https://letterboxd.com/film/{page_string}/"
    return fetch_letterboxd_dictionary(url)

def fetch_justwatch_url_from_letterboxd(letterboxd_url):
    """Given the url to the movie's letterboxd page,
      visit the secret /csi page with useful info.
      There we can get the link to the correct JustWatch page.
    """
    film_name = letterboxd_url.rstrip("/").split("/")[-1]
    url = f"https://letterboxd.com/csi/film/{film_name}/availability/"
    page = requests.get(url)
    scraping_delay()
    lines = page.content.decode().split("\n")
    data = {}
    for line in lines:
        if "www.justwatch.com" in line:
            justwatch_url = re.findall('<a href="(.+?)".*>JustWatch</a>', line)[0]
    return justwatch_url

def fetch_justwatch(justwatch_url):
    """Scrapes a JustWatch url for a list of available services."""
    data = {}
    #despite not mentioning this on their robots.txt, justwatch 403s the default python-requests agent
    page = requests.get(justwatch_url, headers={"User-Agent": "movie-data-scripts"})
    scraping_delay()
    lines = page.content.decode().split("\n")
    try:
        #find the correct line in the page
        services_line = [line for line in lines if "We checked for updates" in line][0]
        #crop only the relevant part of that very long line
        services_line = services_line[services_line.find("Watch Now") : services_line.find("We checked for updates")]
        #and then separate out each service
        pattern = 'alt="(.*?)".*?class="offer__icon".*?class="offer__label__text".*?>(.*?)</p>'
        service_modality_pairs = re.findall(pattern, services_line)
        for service, modality in service_modality_pairs:
            if modality in data:
                if service not in data[modality]:
                    data[modality] += service,
            else:
                data[modality] = [service]
        return data
    except Exception as e:
        print("Justwatch website not formatted as expected")
        raise e

