import requests
import time
import re

def download_movies_from_list(url, outfile="movie_list.txt", npages=1):
    """
    Given a letterboxd.com list url, save a file with the name of each of those movies.
    """
    movie_list = []
    for i in range(1, int(npages)+1):
        this_url = url
        if i > 1:
            this_url = f"{url.rstrip("/")}/page/{i}"
        response = requests.get(this_url)
        page = response.content.decode()
        time.sleep(1)
        for line in page.split("\n"):
            if 'class="poster-container' in line:
                movie = re.findall('data-film-slug=\"(.+?)\" ', line)[0]
                print(movie)
                movie_list += movie,

    with open(outfile, "w", encoding='utf-8') as f:
        for movie in movie_list:
            f.write(f"{movie}\n")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Takes a list of movies, downloads info, and makes a csv.")

    parser.add_argument("url", nargs="?", type=str, help="Letterboxd list url")
    parser.add_argument("outfile", nargs="?", type=str, help="Output filepath")
    parser.add_argument("-n", "--npages", type=int, default=1, help="Large lists are paginated. How many pages does this one have?")

    args = parser.parse_args()

    if args.url is None:
        args.url = input("Paste a url here: ")
    if args.outfile is None:
        args.outfile = "movie_list.txt"

    download_movies_from_list(args.url, outfile=args.outfile, npages=args.npages)