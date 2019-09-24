import json
from flask import Flask, request, redirect, g, render_template, jsonify
import requests
from urllib.parse import quote
from pymongo import MongoClient
from datetime import date
from spotifyClient import SpotifyData, SpotifyAuth

#grab date program is being run
td = date.today()
TODAY = td.strftime("%Y%m%d") ##YYYYMMDD

#set up db instance 
client = MongoClient('localhost', 27017)

#creates instance of app
app = Flask(__name__)

# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)

# Server-side Parameters
CLIENT_SIDE_URL = "http://127.0.0.1"
PORT = 8000
REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)
AUTHED_URL = "{}:{}/authed".format(CLIENT_SIDE_URL, PORT)
REFRESH_URL = "{}:{}/refresh".format(CLIENT_SIDE_URL, PORT)
SCOPE = "playlist-read-private"
STATE = "" #Should create a random string generator here to make a new state for each request

@app.route("/")
def index():
    # Auth Step 1: Authorize Spotify User
    u1 = SpotifyAuth() #no access token yet
    url = u1.auth_url
    return redirect(url)


@app.route("/callback/q")
def callback():
    # Auth Step 2: Requests refresh and access tokens
    t1 = SpotifyAuth()
    newPage = t1.get_accessToken(request.args['code'])
    return redirect(newPage)

@app.route("/authed")
def authed():

    #grab the tokens from the URL
    access_token = request.args.get("access_token")
    refresh_token = request.args.get("refresh_token")
    token_type = "Bearer" #always bearer, don't need to grab this each request
    expires_in = request.args["expires_in"]

    #Auth Step 4: Refresh Token is used to get refreshed access token
    refreshPage = "{}?refresh_token={}&access_token={}".format(REFRESH_URL, refresh_token, access_token)

    p1 = SpotifyData(access_token)
    userName = p1.profile()

    #set up db for user
    dbName = str(TODAY) + str(userName)
    db = client[dbName] # Creates db instance per user per date
    #collection=db.test
    #result = collection.insert_one({'name':'test'})

    return render_template("index.html", title='Authenticated', token=access_token, refresh=refresh_token, link=refreshPage, user=userName)

@app.route("/refresh")
def refresh():

    r1 = SpotifyAuth()
    r2 = r1.get_refreshToken(request.args.get("refresh_token"))
    access_token = r2.get('refreshed_access_token')
    refresh_token = r2.get('refreshed_refresh_token')
    expires_in = r2.get('refreshed_expires_in')

    p1 = SpotifyData(access_token)
    userName = p1.profile()

    refreshPage = "{}?refresh_token={}&access_token={}".format(REFRESH_URL, refresh_token, access_token)

    return render_template("index.html", title='Refreshed', token=access_token, refresh=refresh_token, link=refreshPage, user=userName)
    


    # # Use the access token to access Spotify API
    # #authorization_header = {"Authorization": "Bearer {}".format(access_token)}
    
    #return jsonify(access_token) #authorization_header

    # # Get user playlist data
    # playlist_api_endpoint = "{}/me/playlists".format(SPOTIFY_API_URL)
    # playlists_response = requests.get(playlist_api_endpoint, headers=authorization_header)
    # playlist_data = json.loads(playlists_response.text)

    # # Combine profile and playlist data to display
    # display_arr = playlist_data["items"]
    # return render_template("index.html", sorted_array=display_arr)

if __name__ == "__main__":
    app.run(debug=True, port=PORT)
