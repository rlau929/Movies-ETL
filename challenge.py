{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 1,
   "metadata": {},
   "outputs": [],
   "source": [
    "import json\n",
    "import pandas as pd\n",
    "import numpy as np\n",
    "import re\n",
    "from config import db_password\n",
    "import time\n",
    "\n",
    "from sqlalchemy import create_engine"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 2,
   "metadata": {},
   "outputs": [],
   "source": [
    "file_dir = 'C:/Users/Rob/Desktop/UC_Berkeley_Bootcamp/Module8_ETL/Movies-ETL'"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 3,
   "metadata": {},
   "outputs": [],
   "source": [
    "with open(f'{file_dir}/wikipedia.movies.json', mode='r') as file:\n",
    "    wiki_movies_raw = json.load(file)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 4,
   "metadata": {},
   "outputs": [],
   "source": [
    "kaggle_metadata = pd.read_csv('movies_metadata.csv', low_memory = False)\n",
    "ratings = pd.read_csv('ratings.csv')"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 5,
   "metadata": {},
   "outputs": [],
   "source": [
    "wiki_movies = [movie for movie in wiki_movies_raw\n",
    "               if ('Director' in movie or 'Directed by' in movie)\n",
    "                   and 'imdb_link' in movie\n",
    "                   and 'No. of episodes' not in movie]"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 6,
   "metadata": {},
   "outputs": [],
   "source": [
    "def clean_movie(movie):\n",
    "    movie = dict(movie) #create a non-destructive copy\n",
    "    alt_titles = {}\n",
    "    # combine alternate titles into one list\n",
    "    for key in ['Also known as','Arabic','Cantonese','Chinese','French',\n",
    "                'Hangul','Hebrew','Hepburn','Japanese','Literally',\n",
    "                'Mandarin','McCune-Reischauer','Original title','Polish',\n",
    "                'Revised Romanization','Romanized','Russian',\n",
    "                'Simplified','Traditional','Yiddish']:\n",
    "        if key in movie:\n",
    "            alt_titles[key] = movie[key]\n",
    "            movie.pop(key)\n",
    "    if len(alt_titles) > 0:\n",
    "        movie['alt_titles'] = alt_titles\n",
    "\n",
    "    # merge column names\n",
    "    def change_column_name(old_name, new_name):\n",
    "        if old_name in movie:\n",
    "            movie[new_name] = movie.pop(old_name)\n",
    "    change_column_name('Adaptation by', 'Writer(s)')\n",
    "    change_column_name('Country of origin', 'Country')\n",
    "    change_column_name('Directed by', 'Director')\n",
    "    change_column_name('Distributed by', 'Distributor')\n",
    "    change_column_name('Edited by', 'Editor(s)')\n",
    "    change_column_name('Length', 'Running time')\n",
    "    change_column_name('Original release', 'Release date')\n",
    "    change_column_name('Music by', 'Composer(s)')\n",
    "    change_column_name('Produced by', 'Producer(s)')\n",
    "    change_column_name('Producer', 'Producer(s)')\n",
    "    change_column_name('Productioncompanies ', 'Production company(s)')\n",
    "    change_column_name('Productioncompany ', 'Production company(s)')\n",
    "    change_column_name('Released', 'Release Date')\n",
    "    change_column_name('Release Date', 'Release date')\n",
    "    change_column_name('Screen story by', 'Writer(s)')\n",
    "    change_column_name('Screenplay by', 'Writer(s)')\n",
    "    change_column_name('Story by', 'Writer(s)')\n",
    "    change_column_name('Theme music composer', 'Composer(s)')\n",
    "    change_column_name('Written by', 'Writer(s)')\n",
    "\n",
    "    return movie\n",
    "\n",
    "clean_movies = [clean_movie(movie) for movie in wiki_movies]\n",
    "wiki_movies_df = pd.DataFrame(clean_movies)\n",
    "\n",
    "wiki_movies_df['imdb_id'] = wiki_movies_df['imdb_link'].str.extract(r'(tt\\d{7})')\n",
    "wiki_movies_df.drop_duplicates(subset='imdb_id', inplace=True)\n",
    "\n",
    "box_office = wiki_movies_df['Box office'].dropna()\n",
    "\n",
    "# We can update our map() call to use the lambda function directly instead\n",
    "box_office[box_office.map(lambda x: type(x) != str)]\n",
    "\n",
    "box_office = box_office.apply(lambda x: ' '.join(x) if type(x) == list else x)\n",
    "\n",
    "form_one = r'\\$\\s*\\d+\\.?\\d*\\s*[mb]illi?on'\n",
    "# 2. Some values use a period as a thousands separator, not a comma.\n",
    "form_two = r'\\$\\s*\\d{1,3}(?:[,\\.]\\d{3})+(?!\\s[mb]illion)'\n",
    "\n",
    "matches_form_one = box_office.str.contains(form_one, flags=re.IGNORECASE)\n",
    "matches_form_two = box_office.str.contains(form_two, flags=re.IGNORECASE)\n",
    "box_office[~matches_form_one & ~matches_form_two]\n",
    "\n",
    "box_office = box_office.str.replace(r'\\$.*[-—–](?![a-z])', '$', regex=True)\n",
    "\n",
    "box_office.str.extract(f'({form_one}|{form_two})')\n",
    "\n",
    "def parse_dollars(s):\n",
    "    # if s is not a string, return NaN\n",
    "    if type(s) != str:\n",
    "        return np.nan\n",
    "\n",
    "    # if input is of the form $###.# million\n",
    "    if re.match(r'\\$\\s*\\d+\\.?\\d*\\s*milli?on', s, flags=re.IGNORECASE):\n",
    "\n",
    "        # remove dollar sign and \" million\"\n",
    "        s = re.sub('\\$|\\s|[a-zA-Z]','', s)\n",
    "\n",
    "        # convert to float and multiply by a million\n",
    "        value = float(s) * 10**6\n",
    "\n",
    "        # return value\n",
    "        return value\n",
    "\n",
    "    # if input is of the form $###.# billion\n",
    "    elif re.match(r'\\$\\s*\\d+\\.?\\d*\\s*billi?on', s, flags=re.IGNORECASE):\n",
    "\n",
    "        # remove dollar sign and \" billion\"\n",
    "        s = re.sub('\\$|\\s|[a-zA-Z]','', s)\n",
    "\n",
    "        # convert to float and multiply by a billion\n",
    "        value = float(s) * 10**9\n",
    "\n",
    "        # return value\n",
    "        return value\n",
    "\n",
    "    # if input is of the form $###,###,###\n",
    "    elif re.match(r'\\$\\s*\\d{1,3}(?:[,\\.]\\d{3})+(?!\\s[mb]illion)', s, flags=re.IGNORECASE):\n",
    "\n",
    "        # remove dollar sign and commas\n",
    "        s = re.sub('\\$|,','', s)\n",
    "\n",
    "        # convert to float\n",
    "        value = float(s)\n",
    "\n",
    "        # return value\n",
    "        return value\n",
    "\n",
    "    # otherwise, return NaN\n",
    "    else:\n",
    "        return np.nan\n",
    "    \n",
    "wiki_movies_df['box_office'] = box_office.str.extract(f'({form_one}|{form_two})', flags=re.IGNORECASE)[0].apply(parse_dollars)\n",
    "\n",
    "wiki_movies_df.drop('Box office', axis=1, inplace=True)\n",
    "\n",
    "# Create a budget variable with the following code:\n",
    "budget = wiki_movies_df['Budget'].dropna()\n",
    "\n",
    "# Convert any lists to strings:\n",
    "budget = budget.map(lambda x: ' '.join(x) if type(x) == list else x)\n",
    "\n",
    "# Then remove any values between a dollar sign and a hyphen (for budgets given in ranges):\n",
    "budget = budget.str.replace(r'\\$.*[-—–](?![a-z])', '$', regex=True)\n",
    "\n",
    "matches_form_one = budget.str.contains(form_one, flags=re.IGNORECASE)\n",
    "matches_form_two = budget.str.contains(form_two, flags=re.IGNORECASE)\n",
    "budget[~matches_form_one & ~matches_form_two]\n",
    "\n",
    "budget = budget.str.replace(r'\\[\\d+\\]\\s*', '')\n",
    "budget[~matches_form_one & ~matches_form_two]\n",
    "\n",
    "wiki_movies_df['budget'] = budget.str.extract(f'({form_one}|{form_two})', flags=re.IGNORECASE)[0].apply(parse_dollars)\n",
    "# We can also drop the original Budget column.\n",
    "wiki_movies_df.drop('Budget', axis=1, inplace=True)\n",
    "\n",
    "release_date = wiki_movies_df['Release date'].dropna().apply(lambda x: ' '.join(x) if type(x) == list else x)\n",
    "\n",
    "# One way to parse those forms is with the following:\n",
    "date_form_one = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\\s[123]\\d,\\s\\d{4}'\n",
    "date_form_two = r'\\d{4}.[01]\\d.[123]\\d'\n",
    "date_form_three = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\\s\\d{4}'\n",
    "date_form_four = r'\\d{4}'\n",
    "\n",
    "# And then we can extract the dates with:\n",
    "release_date.str.extract(f'({date_form_one}|{date_form_two}|{date_form_three}|{date_form_four})', flags=re.IGNORECASE)\n",
    "\n",
    "wiki_movies_df['release_date'] = pd.to_datetime(release_date.str.extract(f'({date_form_one}|{date_form_two}|{date_form_three}|{date_form_four})')[0], infer_datetime_format=True)\n",
    "\n",
    "running_time = wiki_movies_df['Running time'].dropna().apply(lambda x: ' '.join(x) if type(x) == list else x)\n",
    "running_time_extract = running_time.str.extract(r'(\\d+)\\s*ho?u?r?s?\\s*(\\d*)|(\\d+)\\s*m')\n",
    "running_time_extract = running_time_extract.apply(lambda col: pd.to_numeric(col, errors='coerce')).fillna(0)\n",
    "\n",
    "wiki_movies_df['running_time'] = running_time_extract.apply(lambda row: row[0]*60 + row[1] if row[2] == 0 else row[2], axis=1)\n",
    "wiki_movies_df.drop('Running time', axis=1, inplace=True)\n",
    "\n",
    "kaggle_metadata[~kaggle_metadata['adult'].isin(['True','False'])]\n",
    "kaggle_metadata = kaggle_metadata[kaggle_metadata['adult'] == 'False'].drop('adult',axis='columns')\n",
    "\n",
    "# Convert:\n",
    "kaggle_metadata['video'] = kaggle_metadata['video'] == 'True'\n",
    "kaggle_metadata['budget'] = kaggle_metadata['budget'].astype(int)\n",
    "kaggle_metadata['id'] = pd.to_numeric(kaggle_metadata['id'], errors='raise')\n",
    "kaggle_metadata['popularity'] = pd.to_numeric(kaggle_metadata['popularity'], errors='raise')\n",
    "kaggle_metadata['release_date'] = pd.to_datetime(kaggle_metadata['release_date'], errors='raise')\n",
    "\n",
    "ratings['timestamp'] = pd.to_datetime(ratings['timestamp'], unit='s')\n",
    "\n",
    "movies_df = pd.merge(wiki_movies_df, kaggle_metadata, on='imdb_id', suffixes=['_wiki','_kaggle'])\n",
    "\n",
    "# Then we can drop that row\n",
    "movies_df = movies_df.drop(movies_df[(movies_df['release_date_wiki'] >'1996-01-01') & (movies_df['release_date_kaggle'] < '1965-01-01')].index)\n",
    "\n",
    "# First, we’ll drop the title_wiki, release_date_wiki, Language, \n",
    "# and Production company(s) columns\n",
    "movies_df.drop(columns=['title_wiki','release_date_wiki','Language','Production company(s)'], inplace=True)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 7,
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "Recorded\n",
      "Venue\n",
      "Label\n",
      "video\n"
     ]
    }
   ],
   "source": [
    "# Make a function that fills in missing data for a column pair \n",
    "# and then drops the redundant column\n",
    "def fill_missing_kaggle_data(df, kaggle_column, wiki_column):\n",
    "    df[kaggle_column] = df.apply(\n",
    "        lambda row: row[wiki_column] if row[kaggle_column] == 0 \n",
    "        else row[kaggle_column]\n",
    "        , axis=1)\n",
    "    df.drop(columns=wiki_column, inplace=True)\n",
    "    \n",
    "# Run the function for the three column pairs that we \n",
    "# decided to fill in zeros\n",
    "fill_missing_kaggle_data(movies_df, 'runtime', 'running_time')\n",
    "fill_missing_kaggle_data(movies_df, 'budget_kaggle', 'budget_wiki')\n",
    "fill_missing_kaggle_data(movies_df, 'revenue', 'box_office')\n",
    "\n",
    "# Since we’ve merged our data and filled in values, \n",
    "#it’s good to check that there aren’t any columns with only one value\n",
    "for col in movies_df.columns:\n",
    "    lists_to_tuples = lambda x: tuple(x) if type(x) == list else x\n",
    "    value_counts = movies_df[col].apply(lists_to_tuples).value_counts(dropna=False)\n",
    "    num_values = len(value_counts)\n",
    "    if num_values == 1:\n",
    "        print(col)\n",
    "        \n",
    "# Reorder the columns\n",
    "movies_df = movies_df.loc[:, ['imdb_id','id','title_kaggle','original_title','tagline','belongs_to_collection','url','imdb_link',\n",
    "                       'runtime','budget_kaggle','revenue','release_date_kaggle','popularity','vote_average','vote_count',\n",
    "                       'genres','original_language','overview','spoken_languages','Country',\n",
    "                       'production_companies','production_countries','Distributor',\n",
    "                       'Producer(s)','Director','Starring','Cinematography','Editor(s)','Writer(s)','Composer(s)','Based on'\n",
    "                      ]]\n",
    "\n",
    "# We need to rename the columns to be consistent.\n",
    "movies_df.rename({'id':'kaggle_id',\n",
    "                  'title_kaggle':'title',\n",
    "                  'url':'wikipedia_url',\n",
    "                  'budget_kaggle':'budget',\n",
    "                  'release_date_kaggle':'release_date',\n",
    "                  'Country':'country',\n",
    "                  'Distributor':'distributor',\n",
    "                  'Producer(s)':'producers',\n",
    "                  'Director':'director',\n",
    "                  'Starring':'starring',\n",
    "                  'Cinematography':'cinematography',\n",
    "                  'Editor(s)':'editors',\n",
    "                  'Writer(s)':'writers',\n",
    "                  'Composer(s)':'composers',\n",
    "                  'Based on':'based_on'\n",
    "                 }, axis='columns', inplace=True)\n",
    "\n",
    "# Rename the “userId” column to “count.”\n",
    "# We can pivot this data so that movieId is the index, \n",
    "# the columns will be all the rating values, and the rows will be \n",
    "# the counts for each rating value.\n",
    "rating_counts = ratings.groupby(['movieId','rating'], as_index=False).count() \\\n",
    "                .rename({'userId':'count'}, axis=1) \\\n",
    "                .pivot(index='movieId', columns='rating', values='count')\n",
    "\n",
    "# Rename the columns so they’re easier to understand. \n",
    "# We’ll prepend rating_ to each column with a list comprehension\n",
    "rating_counts.columns = ['rating_' + str(col) for col in rating_counts.columns]\n",
    "\n",
    "# Use a left merge, since we want to keep everything in movies_df\n",
    "movies_with_ratings_df = pd.merge(movies_df, rating_counts, left_on='kaggle_id', right_index=True, how='left')\n",
    "\n",
    "# Not every movie got a rating for each rating level, \n",
    "# there will be missing values instead of zeros\n",
    "movies_with_ratings_df[rating_counts.columns] = movies_with_ratings_df[rating_counts.columns].fillna(0)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 8,
   "metadata": {},
   "outputs": [],
   "source": [
    "# CHALLENGE: Create a function that takes in three arguments: \n",
    "# Wikipedia data, Kaggle metadata, and MovieLens rating data (from Kaggle)\n",
    "def challenge(wiki_data, kaggle_data, rating_data):\n",
    "    wiki_data = 'title'\n",
    "    kaggle_data = 'budget'\n",
    "    rating_data = 'rating'\n",
    "    if rating_data > 5 & kaggle_data > 1000000:\n",
    "        print(f'The movie is called {wiki_data} with a budget of {kaggle_data} and it has an average rating of {rating_data}. The movie has a budget over $1 million')\n",
    "    else:\n",
    "        print(f'The movie is called {wiki_data} with a budget of {kaggle_data} and it has an average rating of {rating_data}. The movie has a budget below $1 million')"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "db_string = f\"postgres://postgres:{db_password}@127.0.0.1:5432/movie_data\""
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "engine = create_engine(db_string)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "db_string = f\"postgres://postgres:{db_password}@127.0.0.1:5432/movie_data\""
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "engine = create_engine(db_string)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# To save the movies_df DataFrame to a SQL table, we only have to specify \n",
    "#the name of the table and the engine in the to_sql() method.\n",
    "movies_df.to_sql(name='challenge', con=engine)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# create a variable for the number of rows imported\n",
    "rows_imported = 0\n",
    "for data in pd.read_csv(f'{file_dir}/ratings.csv', chunksize=1000000):\n",
    "\n",
    "    # print out the range of rows that are being imported\n",
    "    print(f'importing rows {rows_imported} to {rows_imported + len(data)}...', end='')\n",
    "\n",
    "    data.to_sql(name='ratings', con=engine, if_exists='append')\n",
    "\n",
    "    # increment the number of rows imported by the size of 'data'\n",
    "    rows_imported += len(data)\n",
    "\n",
    "    # print that the rows have finished importing\n",
    "    print('Done.')"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.7.6"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
