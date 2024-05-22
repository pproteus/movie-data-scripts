import os
import json

import imdb_fetcher

class Data:
    def __init__(self, filename="movies.json"):
        self.filename = filename
        if self.filename not in os.listdir():
            with open(filename,"w") as f:
                self.data = {} 
                self.save() #make the file
        else:
            with open(filename,"r") as f:
                self.data = json.load(f)

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f)

    def set_value(self, movie, key, value):
        if movie in self.data:
            self.data[movie][key] = value
        else:  
            self.data[movie] = {key:value}

    def get_value(self, movie, key, as_num=False):
        if as_num:
            try:
                return float(self.data[movie][key])
            except KeyError:
                return 0
            except ValueError:
                return 0
            
        try:
            return self.data[movie][key]
        except KeyError:
            return ""

    def delete_movie(self, movie):
        if movie in self.data.keys():
            self.data.pop(movie)
            self.save()

    def get_all_keys(self):
        return {key for movie in self.data.values() for key in movie.keys()}


def perform_imdb_search(query, data):
    print(f"Searching imdb for '{query}'")
    info = imdb_fetcher.fetch_basics_from_imdb(query)
    data.set_value(query, "Title", info["title"])
    data.set_value(query, "Year", info["year"])
    imdb_id = info.movieID
    data.set_value(query, "IMDB_ID", imdb_id)

def extract_imdb_main_data(imdb_id, query, data):
    print(f"Fetching film details for '{data.get_value(query, "Title")}'")
    info = imdb_fetcher.fetch_details_from_imdb(imdb_id)
    data.set_value(query, "Minutes", info["runtimes"][0])
    data.set_value(query, "IMDB Rating", info["rating"])
    data.set_value(query, "IMDB Count", info["votes"])
    if data.get_value(query, "Lead") == "": #IMDB's cast ordering is not by billing order
        try:
            data.set_value(query, "Lead", info["cast"][0]["name"])
        except KeyError:
            data.set_value(query, "Lead", "Nobody") #some movies just don't have a cast
    data.set_value(query, "Genres", "-".join(info["genres"]))
    plot = info["plot"][0]
    data.set_value(query, "Plot", plot[:plot.find(" ", 60)] + "...")
    data.set_value(query, "Kind", info["kind"])

def extract_imdb_parental_guide(imdb_id, query, data):
    print(f"Fetching parental guide for '{data.get_value(query, "Title")}'")
    data.set_value(query, "Objectionable Content", imdb_fetcher.generate_content_summary(imdb_id))

def extract_letterboxd_data(imdb_id, query, data, use_id=True):
    """If use_id is true, find the page using the provided imdb id.
    Otherwise, assume the query is the page string.
    """
    if use_id:
        print(f"Fetching Letterboxd info for '{data.get_value(query, "Title")}'")
        info = imdb_fetcher.fetch_letterboxd_from_imdb_id(imdb_id)
    else:
        print(f"Fetching Letterboxd info for '{query}'")
        info = imdb_fetcher.fetch_letterboxd_from_page_string(query)
        #and then we have to grab some extra data
        data.set_value(query, "IMDB_ID", info["IMDB_ID"])
        data.set_value(query, "Title", info["name"])
        data.set_value(query, "Year", info["releasedEvent"][0]["startDate"])

    data.set_value(query, "Letterboxd URL", info["@id"])
    data.set_value(query, "Letterboxd Rating", info["aggregateRating"]["ratingValue"])
    data.set_value(query, "Letterboxd Count", info["aggregateRating"]["ratingCount"])
    try:
        data.set_value(query, "Lead", info["actors"][0]["name"])
    except KeyError:
        data.set_value(query, "Lead", "Nobody") #some movies just don't have a cast



def extract_justwatch_data(letterboxd_url, query, data):
    print(f"Fetching availability info for '{data.get_value(query, "Title")}'")
    info = imdb_fetcher.fetch_justwatch(letterboxd_url)
    play_services = []
    for i in info.get("Play", []):
        service = i.split(" ")[0]
        if service not in play_services:
            play_services += service,
    rent_services = []
    for i in info.get("Rent", []):
        service = i.split(" ")[0]
        if service not in play_services and service not in rent_services:
            rent_services += service,
    data.set_value(query, "Stream?", ", ".join(play_services))
    data.set_value(query, "Rent?", ", ".join(rent_services))


def write_movie_csv(outfile, movies, moviedata, desired_colnames=None, skip_genres=None):
    """Function that manages creating/formatting the csv, assuming you have all the data already."""
    with open(outfile, 'w', newline='', encoding='utf-8') as f:
        if skip_genres is None: #if you want this to be empty, pass it the empty list, not None
            skip_genres = ["Short"]
        if desired_colnames is None:
            desired_colnames = ["Year", "Title", "Minutes", "IMDB Rating", "Letterboxd Rating",
                            "Lead", "Objectionable Content",
                            "Genres", "Stream?", "Rent?", 
                            "IMDB Count", "Letterboxd Count"]

        for col in desired_colnames:
            f.write(col)
            f.write("\t")
        f.write("\n")

        for movie in sorted(movies, key=lambda x: moviedata.get_value(x, "IMDB Count", as_num=True), reverse=True):
            genres = moviedata.get_value(movie, "Genres")
            if any([g in genres for g in skip_genres]):
                continue
            for col in desired_colnames:
                f.write(str(moviedata.get_value(movie, col)))
                f.write("\t")
            f.write("\n")


def manage_movies(inputfile="test.txt", outfile=None, requires_imdb_search=False, datafile="movies.json", force_justwatch_update=False):
    """
    For each line in the inputfile, fetch all the various data for it, save that, and make a csv.
    This function is long because we're caching specific bits of information rather than the entirety of the incoming data.
    The saved data is keyed via the query string.
    Networking errors should be handled gracefully by simply moving on to the next thing.
    """
    data = Data(datafile)
    with open(inputfile, "r") as f:
        queries = [line.rstrip("\n").lower() for line in f] #preprocessing
        for query in queries:
            if query == "": continue
            try:
                if not requires_imdb_search: # we can fetch the ID directly without guessing
                     if data.get_value(query, "IMDB_ID") == "" or data.get_value(query, "Letterboxd Rating") == "":
                        extract_letterboxd_data("Dummy id string", query, data, use_id=False)

                imdb_id = data.get_value(query, "IMDB_ID")
                if imdb_id == "":
                    perform_imdb_search(query, data)
                    imdb_id = data.get_value(query, "IMDB_ID")

                if data.get_value(query, "IMDB Rating") == "" or  data.get_value(query, "Kind") == "":
                    extract_imdb_main_data(imdb_id, query, data)

                if data.get_value(query, "Objectionable Content") == "":
                    extract_imdb_parental_guide(imdb_id, query, data)

                if data.get_value(query, "Letterboxd Rating") == "":
                    extract_letterboxd_data(imdb_id, query, data)

                if force_justwatch_update or (data.get_value(query, "Stream?") == "" and data.get_value(query, "Rent?") == ""):
                    letterboxd_url = data.get_value(query, "Letterboxd URL")
                    extract_justwatch_data(letterboxd_url, query, data)

            except imdb_fetcher.MovieNotFoundException as e:
                print(f"Error: {e} not found.")
                continue
            except Exception as e:
                print(f"Unknown exception, probably a timeout: {e}")
                continue
            finally:
                data.save()

    if outfile is None:
        outfile = "out_" + inputfile + ".csv"
    write_movie_csv(outfile, queries, data)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Takes a list of movies, downloads info, and makes a csv.")

    parser.add_argument("file", nargs="?", type=str, help="Input filepath")
    parser.add_argument("outfile", nargs="?", type=str, help="Output filepath")
    parser.add_argument("-j", "--datafile", type=str, default="movies.json", help="Database file to use/create")
    parser.add_argument("-d", "--delete", type=str, help="Querystring to delete from the database")
    parser.add_argument("-f", "--justwatch", action="store_true", help="Flag to force redownload all Justwatch data")
    parser.add_argument("-w", "--handwritten", action="store_true", help="Flag to use imdb search (when queries are not taken from letterboxd)")

    args = parser.parse_args()

    if args.delete is not None:
        d = Data(args.datafile)
        d.delete_movie(args.delete)
    else:
        if args.file is None:
            args.file = input("Input filepath:  ")
            args.outfile = input("Output filepath:  ")
        if len(args.outfile) is None or len(args.outfile) < 2:
            manage_movies(args.file, requires_imdb_search=args.handwritten, 
                          datafile=args.datafile, force_justwatch_update=args.justwatch)
        else:
            manage_movies(args.file, args.outfile, requires_imdb_search=args.handwritten, 
                          datafile=args.datafile, force_justwatch_update=args.justwatch)

    

    ##Todo:
    #how to get proper justwatch data?????
    #"lead" isn't pulling the stars. Can I fix this?