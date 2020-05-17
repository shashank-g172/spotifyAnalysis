import json
from flask import Flask, Markup, request, redirect, render_template, jsonify
import requests
from datetime import date
from spotifyClient import data, auth, create
from statisticalAnalysis import stats
import pandas as pd
from flask_wtf import FlaskForm
from wtforms import widgets, SelectMultipleField
import itertools
from collections import Counter
from operator import itemgetter
import time
import os

ENV = os.environ.get('ENV')
SECRET_KEY = ' ' #This doesn't actually get used, but simpleForm needs this to run

#grab date program is being run
td = date.today()
TODAY = td.strftime("%Y%m%d") ##YYYYMMDD
YEAR = td.strftime("%Y") ##YYYY
NICEDATE = td.strftime("%b %d %Y") ##MMM DD YYYY

#creates instance of app
app = Flask(__name__)
app.config.from_object(__name__)

# Server-side Parameters based on where it's running
if ENV == 'dev':
    CLIENT_SIDE_URL = "http://127.0.0.1"
    PORT = 8000
    REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)
elif ENV == 'heroku':
    CLIENT_SIDE_URL = "https://musicincontext.herokuapp.com"
    REDIRECT_URI = "{}/callback/q".format(CLIENT_SIDE_URL)

@app.route("/")
def index():
    # Auth Step 1: Authorize Spotify User
    authorization = auth()
    return redirect(authorization.auth_url)

@app.route("/callback/q")
def callback():
    # Auth Step 2: Requests refresh and access tokens
    authorization = auth()
    return redirect(authorization.get_accessToken(request.args['code']))

@app.route("/authed", methods=["GET","POST"])
def authed():

    #grab the tokens from the URL + intialize data class
    access_token = request.args.get("access_token")
    refresh_token = request.args.get("refresh_token")
    token_type = "Bearer" #always bearer, don't need to grab this each request
    expires_in = request.args["expires_in"]
    spotifyDataRetrieval = data(access_token)
    authorization = auth()

    rawTrack = spotifyDataRetrieval.getTracks('3RWKoVWGXvMas3mn7tRRbI')
    cleanTrack = spotifyDataRetrieval.cleanTrackData(rawTrack)
    print(spotifyDataRetrieval.getAudioFeatures(cleanTrack))
    input()

    profile = spotifyDataRetrieval.profile()
    userName = profile.get("userName")
    image = profile.get("images")

    if len(image) == 0:
        imgurl = 'N/A'
    else:
        imgurl = image[0]['url']
        
    #build the link for each playlist
    allUserPLaylists = spotifyDataRetrieval.userPlaylists()
    checkboxData = []
    for playlist in allUserPLaylists:
        checkboxFormatPlaylist = (playlist['uri'],playlist['playlistName'])
        checkboxData.append(checkboxFormatPlaylist)

    #set up the checkbox classes
    class MultiCheckboxField(SelectMultipleField):
        widget = widgets.ListWidget(prefix_label=False)
        option_widget = widgets.CheckboxInput()

    class SimpleForm(FlaskForm):
        # create a list of value/description tuples
        files = [(x, y) for x,y in checkboxData]
        playlistSelections = MultiCheckboxField('Label', choices=files)

    form = SimpleForm()

    if form.validate_on_submit():
        formData = form.playlistSelections.data
        if not formData:
            return render_template("index.html", title='Home', user=userName, token=access_token, refresh=refresh_token, url=imgurl, form=form)
        else:
            clusterVisPage = "{}?refresh_token={}&access_token={}&data={}".format(authorization.visualizationURL(), refresh_token, access_token, ",".join(formData))
            return redirect(clusterVisPage) 
    else:
        print(form.errors)

    return render_template("index.html", title='Home', user=userName, token=access_token, refresh=refresh_token, url=imgurl, form=form)

@app.route("/analysis", methods=["GET"])
def analysis():

    #list of spotify attributes used in the model
    spotifyAudioFeatures = ['acousticness','danceability','energy','instrumentalness','liveness','speechiness','valence']

    #intialize data retrieval class
    access_token = request.args.get("access_token")
    refresh_token = request.args.get("refresh_token")
    token_type = "Bearer"
    spotifyDataRetrieval = data(access_token)


    ################################################################
    ###               CLUSTER SECTION                            ###
    ################################################################

    # #raw data from the checklist (a list of playlist URIs specifically)
    # pldata = request.args["data"]
    # unpackedData = pldata.split(",")
    
    # profile = spotifyDataRetrieval.profile()
    # userName = profile.get("userName")

    # #retrieve songs and analysis for user selected playlists
    # masterSongList=[]
    # for i in range(len(unpackedData)):
    #     songs = spotifyDataRetrieval.getPlaylistTracks(unpackedData[i])
    #     masterSongList.extend(songs)

    # masterSongListWithFeatures = spotifyDataRetrieval.trackFeatures(masterSongList)

    # #set up kmeans, check how many songs
    # if len(masterSongListWithFeatures)<5:
    #     clusters = len(masterSongListWithFeatures)
    # else:
    #     clusters = 5

    # statistics = stats(masterSongListWithFeatures)
    # statistics.kMeans(spotifyAudioFeatures, clusters)
    # dataframeWithClusters = statistics.df
    # clusterCenterCoordinates = statistics.centers

    # #create playlists for each kmeans assignment
    # spotifyCreate = create(access_token)
    # repeatgenres = {}
    # for i in range(clusters):
    #     descript = ""
    #     selectedClusterCenter = clusterCenterCoordinates[i]
    #     for j in range(len(spotifyAudioFeatures)):
    #         entry = str(" "+str(spotifyAudioFeatures[j])+":"+str(round(selectedClusterCenter[j],3))+" ")
    #         descript += entry
    #         #we can return less detail here, maybe 'highly danceable' is sufficient

    #     descript +=" created on {}".format(NICEDATE)
    #     descript+=" by JTokarowski "

    #     dataframeFilteredToSingleCluster = dataframeWithClusters.loc[dataframeWithClusters['kMeansAssignment'] == i]

    #     genres = dataframeFilteredToSingleCluster['genres'].values.tolist()
    #     genreslist = genres[0]

    #     genreDict = {}
    #     for genre in genreslist:
    #         g =  genre.replace(" ", "_")
    #         if g in genreDict:
    #             genreDict[g]+=1
    #         else:
    #             genreDict[g]=1

    #     v=list(genreDict.values())
    #     k=list(genreDict.keys())

    #     try:
    #         maxGenre = k[v.index(max(v))]
    #     except:
    #         maxGenre = "¯\_(ツ)_/¯"

    #     if maxGenre in repeatgenres.keys():
    #         repeatgenres[maxGenre]+=1
    #         maxGenre += "_"+str(repeatgenres[maxGenre])
    #     else:
    #         repeatgenres[maxGenre]=1

    #     maxGenre = maxGenre.replace("_", " ")

    #     newPlaylistInfo = spotifyCreate.newPlaylist(userName, "+| "+str(maxGenre)+" |+",descript)
    #     newPlaylistID = spotifyDataRetrieval.URItoID(newPlaylistInfo['uri'])


    #     dataframeFilteredToSingleCluster = dataframeFilteredToSingleCluster['trackId']
    #     newPlaylistTracksIDList = dataframeFilteredToSingleCluster.values.tolist()

    #     outputPlaylistTracks=[]
    #     for spotifyID in newPlaylistTracksIDList:
    #         outputPlaylistTracks.append(spotifyDataRetrieval.idToURI("track",spotifyID))

    #     if len(outputPlaylistTracks)>0:
    #         n = 50 #spotify playlist addition limit
    #         for j in range(0, len(outputPlaylistTracks), n):  
    #             playlistTracksSegment = outputPlaylistTracks[j:j + n]
    #             spotifyCreate.addSongs(newPlaylistID, ",".join(playlistTracksSegment))
            
    # return render_template('radar_chart.html', title='Cluster Centers', max = 1.0, labels=spotifyAudioFeatures, centers=clusterCenterCoordinates)

    ################################################################
    ###               TUNNEL SEGMENT BETA                       ###
    ################################################################

    #key = "target_{}".format(spotifyAudioFeatures[j])
    #key2 = "min_{}".format(featuresList[j])
    #key3 = "max_{}".format(featuresList[j])
    #targets[key] = selectedClusterCenter[j]
    #targets[key2] = center[j]-0.2
    #targets[key3] = center[j]+0.2

    topListenType = 'artists'
    userTopList = []
    userTopList.extend(spotifyDataRetrieval.getMyTop(topType=topListenType, term='short_term', limit=10))
    userTopList.extend(spotifyDataRetrieval.getMyTop(topType=topListenType, term='medium_term', limit=10))
    userTopList.extend(spotifyDataRetrieval.getMyTop(topType=topListenType, term='long_term', limit=10))

    itemIDs = []
    for topItem in userTopList:
        if topListenType=='tracks':
            itemIDs.append(topItem['track_id'])
        else:
            itemIDs.append(topItem['artist_id'])

    #remove dupes
    itemIDs = list(set(itemIDs))

    ## Build up a large pool of options by grabbing suggestions for each
    ## of top artists, target 0 and target 1 to get almost all of pool
    masterTrackPool = []
    masterTrackPoolIDList = []
    for spotifyID in itemIDs:  
        recommendedTracks = spotifyDataRetrieval.getRecommendations(limit=100, seed_artists=spotifyID)
        for track in recommendedTracks:
            if track['trackId'] not in masterTrackPoolIDList:
                masterTrackPool.append(spotifyDataRetrieval.trackFeatures(track, isList=false))
        
            print(masterTrackPool)
            input()

    # recs = []
    # recids = []
    # for song in playlistsongs:
    #     #for each song in target list, find ED to each reccomendation
    #     #choose the one with lowest ED        
    #     #totalEuclideanDistance
    #     TEDS=[]
    #     for rec in finalrecs:
    #         TED = 0
    #         for feature in featuresList:
    #             skip_features = ['liveness']
    #             if feature not in skip_features:
    #                 diff = (rec['audioFeatures'][feature]*100)-(song['audioFeatures'][feature]*100)
    #                 TED += diff * diff
    #                 rec["TED"] = TED
            
    #         TEDS.append(TED)

    #     # sort the recommendations by min ED
    #     sorted_recs = sorted(finalrecs, key=itemgetter('TED'))

    #     i = 0 
    #     while sorted_recs[i]['trackId'] in recids:
    #         i+=1
        
    #     print("TARGET")
    #     print(song)
    #     print("################################################################")
    #     print("SUGGESTION")
    #     print(sorted_recs[i])
    #     print("################################################################")
    #     recids.append(sorted_recs[i]['trackId'])
    #     recs.append(sorted_recs[i]) 

    # c1 = create(access_token)
    # response2 = c1.newPlaylist(userName, "+| TEST SET |+","N/A")
    # r2 = response2['uri']
    # fields = r2.split(":")
    # plid = fields[2]
    # uriList=[]
    # for item in recids:
    #     uriList.append("spotify:track:{}".format(item))
    # if len(uriList)>0:
    #     n = 50 #spotify playlist addition limit
    #     for j in range(0, len(uriList), n):  
    #         listToSend = uriList[j:j + n]
    #         stringList = ",".join(listToSend)
    #         response3 = c1.addSongs(plid, stringList)

    # print('DONE')
    # input()

   ################################################################ 
    #sort by minimum euclidean distance from coordinates of curve
    #get recomendations from first chosen song
    #as we move forward in the set, trailing 5 songs as seeds


   #  #print(d.getMyTop(topType='tracks', term='long_term'))    

#instantiate app
if __name__ == "__main__":
    if ENV == 'heroku':
        app.run(debug=False)
    else:
        app.run(debug=True, port=PORT)