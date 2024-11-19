from __future__ import annotations
import time
import requests
import json
import re
from dataclasses import dataclass, field, asdict


def generate_content_summary(vote_dict):
    """Given the votes from imdb.com's "parental guide",
    return a string summarizing some of it.
    You may want to rewrite this for yourself. """

    complaint_list = []
    LOW_DATA_STRING = "Not enough data"
    BAD_DATA_STRING = "Invalid content data"
    try:
        if sum(vote_dict["FRIGHTENING"].values()) < 20:
            return LOW_DATA_STRING
    except (KeyError, TypeError):    # malformed input
        return BAD_DATA_STRING

    if max(vote_dict["VIOLENCE"], key=vote_dict["VIOLENCE"].get) == "Severe":
        complaint_list += "Intense violence",
    if max(vote_dict["NUDITY"], key=vote_dict["NUDITY"].get) == "Severe":
        complaint_list += "Abundant sexual content",
    elif max(vote_dict["NUDITY"], key=vote_dict["NUDITY"].get) == "Moderate":
        complaint_list += "Some sexual content",
    if max(vote_dict["PROFANITY"], key=vote_dict["PROFANITY"].get) == "Severe":
        complaint_list += "Abundant swearing",
    elif max(vote_dict["PROFANITY"], key=vote_dict["PROFANITY"].get) == "Moderate":
        complaint_list += "Some swearing",
    if max(vote_dict["VIOLENCE"], key=vote_dict["VIOLENCE"].get) == "Moderate":
        complaint_list += "Some violence",
    if len(complaint_list):
        return "; ".join(complaint_list)
    else:
        return "Ok"


def justwatch_formatting_function(list_of_services):
    if list_of_services is None or not len(list_of_services):
        return "."
    short_services = []
    for i in list_of_services:
        service = i.split(" ")[0]
        if service not in short_services:
            short_services += service,
    return ", ".join(short_services)


@dataclass
class Movie:
    letterboxd_url: str = field(default=None)
    justwatch_url: str = field(default=None)
    imdb_id: str = field(default=None)     # just the digits, not including the "tt"
    title: str = field(default=None, metadata={"label": "Title"})
    runtime: int = field(default=None, metadata={"label": "Minutes"})
    year: int = field(default=None, metadata={"label": "Year"})
    letterboxd_rating: float = field(default=None, metadata={"label": "Letterboxd Rating"})
    letterboxd_count: int = field(default=None, metadata={"label": "Letterboxd Count"})
    imdb_rating: float = field(default=None, metadata={"label": "IMDB Rating"})
    imdb_count: int = field(default=None, metadata={"label": "IMDB Count"})
    justwatch_free: list[str] = field(default=None, metadata={"label": "Stream?", "formatter": justwatch_formatting_function})
    justwatch_rent: list[str] = field(default=None, metadata={"label": "Rent?", "formatter": justwatch_formatting_function})
    list_of_genres: list[str] = field(default=None, metadata={"label": "Genres", "formatter": lambda x: "" if x is None else "-".join(x)})
    list_of_actors: list[str] = field(default=None, metadata={"label": "Leads", "formatter": lambda x:
                                                              None if x is None else "Nobody" if not len(x) else ", ".join(x[:2])})
    content_warning_dict: dict = field(default=None, metadata={"label": "Objectionable Content", "formatter": generate_content_summary})
    plot: str = field(default=None, metadata={"label": "Summary"})
    kind: str = None
    director: str = None

    def asdict(self):
        return asdict(self)

    def merge(self, other_movie: Movie, overwrite=True):
        for k, v in other_movie.asdict().items():
            if v is not None:
                current_value = self.__getattribute__(k)
                if overwrite or current_value is None or not len(current_value):
                    self.__setattr__(k, v)


def scraping_delay(seconds=1.5):
    time.sleep(seconds)


class MovieNotFoundException(Exception):
    pass


def fetch_imdb(imdb_id):
    """Scrapes imdb page for parents guide, ratings, and generic movie info."""
    url = f"https://www.imdb.com/title/tt{imdb_id}/parentalguide/"
    print(f"Fetching data from {url}.")
    page = requests.get(url, headers={"User-Agent": "movie-data-scripts"})
    scraping_delay()
    lines = page.content.decode().split("\n")
    line = [i for i in lines if "__NEXT_DATA__" in i][0]
    pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script><script>'
    data = json.loads(re.findall(pattern, line)[0])["props"]["pageProps"]["contentData"]["data"]["title"]
    return Movie(content_warning_dict={cat["category"]["id"]: {level["text"]: level["votedFor"] for level in cat["severityBreakdown"]}
                                       for cat in data["parentsGuide"]["categories"]},
                 runtime=data["runtime"]["seconds"]//60, imdb_rating=data["ratingsSummary"]["aggregateRating"],
                 imdb_count=data["ratingsSummary"]["voteCount"], list_of_genres=[g["genre"]["text"] for g in data["titleGenres"]["genres"]],
                 kind=data["titleType"]["text"], title=data["titleText"]["text"], year=data["releaseYear"]["year"],
                 plot=data["plot"]["plotText"]["plainText"], director=data["directorsPageTitle"][0]["credits"][0]["name"]["nameText"]["text"],
                 list_of_actors=[person["node"]["name"]["nameText"]["text"] for person in data["castPageTitle"]["edges"]])


def fetch_letterboxd(letterboxd_url):
    "Return all letterboxd page data, as a json."
    print(f"Fetching data from {letterboxd_url}.")
    page = requests.get(letterboxd_url)
    scraping_delay()
    lines = page.content.decode().split("\n")
    for i, line in enumerate(lines):
        if "<![CDATA[" in line:
            info_line = lines[i+1]
        if "var filmData" in line:
            runtime_line = line
        if "www.imdb.com" in line:
            imdb_line = line
    imdb_id = re.findall(r"tt(\d+)", imdb_line)[0]
    try:
        info = json.loads(info_line)
    except UnboundLocalError:
        # if you pass a handwritten list as though it was a letterboxd list,
        # this page will not be a proper movie page, but letterboxd may still handle it
        # but there's not going to be proper data here so we have to stop.
        raise MovieNotFoundException("Hint: Are you sure this input list wasn't handwritten?")
    runtime = int(re.findall(r"runTime: (\d+)", runtime_line)[0])

    return Movie(title=info["name"], kind=info["@type"], runtime=runtime, director=info["director"][0]["name"], year=int(info["releasedEvent"][0]["startDate"]),
                 list_of_actors=[actor["name"] for actor in info["actors"]], list_of_genres=info["genre"], letterboxd_url=info["@id"], imdb_id=imdb_id,
                 letterboxd_count=info["aggregateRating"]["ratingCount"], letterboxd_rating=info["aggregateRating"]["ratingValue"])


def fetch_letterboxd_from_imdb_id(imdb_id):
    """Given an imdb id, go to the letterboxd page for that movie,
      and return all the data, as a json."""
    url = f"https://letterboxd.com/imdb/{imdb_id}"
    return fetch_letterboxd(url)


def fetch_letterboxd_from_page_string(page_string):
    url = f"https://letterboxd.com/film/{page_string}/"
    return fetch_letterboxd(url)


def fetch_justwatch_url_from_letterboxd(letterboxd_url):
    """Given the url to the movie's letterboxd page,
      visit the secret /csi page with useful info.
      There we can get the link to the correct JustWatch page.
    """
    film_name = letterboxd_url.rstrip("/").split("/")[-1]
    print(f"Fetching justwatch url from {letterboxd_url}")
    url = f"https://letterboxd.com/csi/film/{film_name}/availability/"
    page = requests.get(url)
    scraping_delay()
    lines = page.content.decode().split("\n")
    for line in lines:
        if "www.justwatch.com" in line:
            return Movie(justwatch_url=re.findall('<a href="(.+?)".*>JustWatch</a>', line)[0])


def fetch_justwatch(justwatch_url):
    """Scrapes a JustWatch url for a list of available services."""
    data = {"Subscription": [], "Rent": []}
    print(f"Fetching data from {justwatch_url}.")
    page = requests.get(justwatch_url, headers={"User-Agent": "movie-data-scripts"})
    scraping_delay()
    lines = page.content.decode().split("\n")
    try:
        # find the correct line in the page
        services_line = [line for line in lines if "We checked for updates" in line][0]
        # crop only the relevant part of that very long line
        services_line = services_line[services_line.find("Watch Now") : services_line.find("We checked for updates")]
        if "offer__label__text" in services_line:   # (if that's not the case, there's no data, and the regex might take forever to fail)
            # and then separate out each service
            pattern = 'alt="(.*?)".*?class="offer__icon".*?class="offer__label__text".*?>(.*?)</p>'
            service_modality_pairs = re.findall(pattern, services_line)
            for service, modality in service_modality_pairs:
                if modality in data:
                    if service not in data[modality]:
                        data[modality] += service,
                else:
                    data[modality] = [service]
        return Movie(justwatch_free=data["Subscription"], justwatch_rent=data["Rent"])
    except Exception as e:
        print("Justwatch website not formatted as expected")
        raise e


if __name__ == "__main__":
    # x = fetch_justwatch_url_from_letterboxd("https://letterboxd.com/film/being-there/")
    x = fetch_justwatch('https://www.justwatch.com/ca/movie/biking-borders-eine-etwas-andere-reise')
    # x = fetch_imdb('0078841')
    print(x)
