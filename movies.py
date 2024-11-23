import os
import json

import imdb_fetcher


class Data:
    def __init__(self, filename="movies.json"):
        self.filename = filename
        if self.filename not in os.listdir():
            with open(filename, "w") as f:
                self.data = {}
                self.save()    # make the file
        else:
            with open(filename, "r") as f:
                j = json.load(f)
                self.data = {k: imdb_fetcher.Movie(**v) for k, v in j.items()}

    def save(self):
        with open(self.filename, "w") as f:
            d = {k: v.asdict() for k, v in self.data.items()}
            json.dump(d, f)

    def add_info(self, query, movie, overwrite=True):
        if query not in self.data:
            self.data[query] = movie
        else:
            self.data[query].merge(movie)
        self.save()

    def get_value(self, movie, key, as_num=False, formatted=False):
        if formatted:
            formatting_function = imdb_fetcher.Movie.__dataclass_fields__.get(key, dict()).metadata.get("formatter", lambda x: x)
            value = formatting_function(self.data.get(movie, imdb_fetcher.Movie()).__getattribute__(key))
            if value is not None:
                return str(value)
            else:
                return ""

        if as_num:
            try:
                return float(self.data[movie].__getattribute__(key))
            except (KeyError, ValueError, TypeError):
                return 0
        else:
            try:
                s = self.data[movie].__getattribute__(key)
                if s is not None:
                    return s
                else:
                    return ""
            except KeyError:
                return ""

    def get_label(self, attr):
        return imdb_fetcher.Movie.__dataclass_fields__.get(attr, dict()).metadata.get("label", attr)

    def delete_movie(self, movie):
        if movie in self.data.keys():
            self.data.pop(movie)
            self.save()
            print(f"Cache deleted: {movie}")
        else:
            print(f"No cache found to delete: {movie}")


def perform_imdb_search(query, data):
    print(f"Searching imdb for '{query}'")
    info = imdb_fetcher.fetch_basics_from_imdb(query)
    data.set_value(query, "Title", info["title"])
    data.set_value(query, "Year", info["year"])
    imdb_id = info.movieID
    data.set_value(query, "IMDB_ID", imdb_id)


def write_movie_csv(outfile, movies, moviedata, desired_colnames=None, skip_genres=None):
    """Function that manages creating/formatting the csv, assuming you have all the data already."""
    with open(outfile, 'w', newline='', encoding='utf-8') as f:
        if skip_genres is None:   # if you want this to be empty, pass it the empty list, not None
            skip_genres = ["Short"]
        if desired_colnames is None:
            desired_colnames = ["year", "title", "runtime", "imdb_rating", "letterboxd_rating",
                            "list_of_actors", "content_warning_dict",
                            "justwatch_free", "justwatch_rent",
                            "imdb_count", "letterboxd_count", "list_of_genres", "plot", "kind"]

        for col in desired_colnames:
            f.write(moviedata.get_label(col))
            f.write("\t")
        f.write("\n")

        for movie in sorted(movies, key=lambda x: moviedata.get_value(x, "imdb_count", as_num=True), reverse=True):
            genres = moviedata.get_value(movie, "list_of_genres")
            if any([g in genres for g in skip_genres]):
                continue
            for col in desired_colnames:
                f.write(str(moviedata.get_value(movie, col, formatted=True)))
                f.write("\t")
            f.write("\n")


def manage_movies(inputfile="test.txt", outfile=None, requires_search=False, datafile="movies.json", force_justwatch_update=False):
    """
    For each line in the inputfile, fetch all the various data for it, save that, and make a csv.
    This function is long because it's responsible for minimizing the number of outgoing calls.
    Networking errors should be handled gracefully by simply moving on to the next thing.
    """
    data = Data(datafile)
    with open(inputfile, "r") as f:
        queries = [line.rstrip("\n").lower() for line in f]    # preprocessing
        for query in queries:
            if query == "":
                continue
            if query[:2] == "//":
                continue    # these are comments
            try:
                if query[:23] == "https://letterboxd.com/":    # we can fetch the ID directly without guessing
                    if data.get_value(query, "imdb_id") == "" or data.get_value(query, "letterboxd_count") == "":
                        data.add_info(query, imdb_fetcher.fetch_letterboxd(query))

                elif not requires_search:    # in this case, the query is the letterboxd string
                    if data.get_value(query, "imdb_id") == "" or data.get_value(query, "letterboxd_count") == "":
                        data.add_info(query, imdb_fetcher.fetch_letterboxd_from_page_string(query))

                imdb_id = data.get_value(query, "imdb_id")
                if imdb_id == "":      # then we probably need a search
                    raise NotImplementedError("No search function implemented")

                if data.get_value(query, "imdb_count") == "":
                    data.add_info(query, imdb_fetcher.fetch_imdb(imdb_id))

                if data.get_value(query, "letterboxd_count") == "":
                    data.add_info(query, imdb_fetcher.fetch_letterboxd_from_imdb_id(imdb_id))

                if force_justwatch_update or data.get_value(query, "justwatch_rent") == "":
                    justwatch_url = data.get_value(query, "justwatch_url")
                    if justwatch_url == "":   # then we have to make an extra call to fetch it
                        letterboxd_url = data.get_value(query, "letterboxd_url")
                        data.add_info(query, imdb_fetcher.fetch_justwatch_url_from_letterboxd(letterboxd_url))
                        justwatch_url = data.get_value(query, "justwatch_url")
                    if justwatch_url not in ("", "https://www.justwatch.com/"):     # the former means the url fetcher failed, the latter means it returned nothing
                        data.add_info(query, imdb_fetcher.fetch_justwatch(justwatch_url))

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
            args.handwritten = input("Type 'h' if list is handwritten, or anything else to continue  ").lower() == "h"
        if args.outfile is None or len(args.outfile) < 2:
            manage_movies(args.file, requires_search=args.handwritten,
                          datafile=args.datafile, force_justwatch_update=args.justwatch)
        else:
            manage_movies(args.file, args.outfile, requires_search=args.handwritten,
                          datafile=args.datafile, force_justwatch_update=args.justwatch)
