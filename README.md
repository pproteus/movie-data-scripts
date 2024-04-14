This is a collection of scripts that I use to take a list of movies, and populate a list of helpful information about those movies.
Some functionality may be very tuned to my personal needs.

There are two entry points, both designed to be accessible via command-line.
`movies.py` takes a .txt list of movie titles, searches imdb and other sites for data, and creates a .csv file.
While this requires a lot of calls to the external websites, it caches the results as it downloads them
so if some the requests time out you can just run the function again and it will get straight to filling in the gaps.
`letterboxd_list_fetcher.py` takes a letterboxd.com list page, and converts it into a .txt compatible with the above.

**Sample usage:**
`py -m letterboxd_list_fetcher https://letterboxd.com/awards/list/2024-oscars-all-nominated-films/ oscars2024.txt`
`py -m movies`

Dependencies: [imdb](https://cinemagoer.readthedocs.io/en/latest/)