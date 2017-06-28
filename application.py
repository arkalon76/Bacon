'''
MIT License

Copyright (c) 2017 Kenth Fagerlund

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from flask import Flask, render_template, url_for
from flask import request
import requests_cache
import requests
import json
import codecs
import datetime
import pymongo

import time

class TorrentFile(object):
    """docstring for TorrentFile."""

    CATEGORY_MOVIE_H264_1080P = 44
    CATEGORY_MOVIE_H264_720P = 45
    CATEGORY_MOVIE_H264_3D = 47
    CATEGORY_MOVIE_FULL_BD = 42
    CATEGORY_MOVIE_BD_REMUX = 46

    def __init__(self, torrent_json):
        self.title = torrent_json['title']
        self.category = torrent_json['category']
        self.magnet = torrent_json['download']
        self.seeder_count = torrent_json['seeders']
        self.info_page = torrent_json['info_page']



class VideoFile(object):

    def __init__(self, mediainfo_json):

        self.high_quality_codecs = ['AVC','HEVC','VC-1']
        self.high_quality_resolution = 1080
        self.high_quality_bitrate = 20000000

        if 'other_overall_bit_rate' in mediainfo_json['tracks'][0]:
            self.video_bitrate_txt = mediainfo_json['tracks'][0]['other_overall_bit_rate'][0]
        else:
            self.video_bitrate_txt = '0'

        if 'overall_bit_rate' in mediainfo_json['tracks'][0]:
            self.video_bitrate_int = int(mediainfo_json['tracks'][0]['overall_bit_rate'])
        else:
            self.video_bitrate_int = 11

        self.video_resolution = mediainfo_json['tracks'][1]['sampled_height']
        self.movie_title = mediainfo_json['tracks'][0]['file_name']
        self.video_codec = mediainfo_json['tracks'][1]['format']
        self.video_profile = mediainfo_json['tracks'][1]['format_profile']
        try:
            self.video_imdb_id = mediainfo_json['quick_facts']['imdb_id']
        except KeyError:
            self.video_imdb_id = None

    def __repr__(self):
        return '{}: {} {}'.format(self.__class__.__name__,
                                  self.movie_title,
                                  self.video_bitrate_txt)

    def getVideoBitrate(self):
        return self.video_bitrate_txt

    def getVideoResolution(self):
        return self.video_resolution

    def getMovieTitle(self):
        return self.movie_title

    def getVideoCodec(self):
        return self.video_codec

    def getVideoProfile(self):
        return self.video_profile

    def getIMDB_ID(self):
        return self.video_imdb_id

    def isOfGoodQuality(self):
        if int(self.video_resolution) < self.high_quality_resolution:
            return False
        elif not self.video_codec in self.high_quality_codecs:
            return False
        elif self.video_bitrate_int < self.high_quality_bitrate:
            return False
        else:
            return True

def get_Torrent_List_By_IMDB_ID(imdb_id):
    token_response = requests.get('https://torrentapi.org/pubapi_v2.php?get_token=get_token')
    token_json = json.loads(token_response.text)

    search_uri = 'https://torrentapi.org/pubapi_v2.php?category=42;46&format=json_extended&mode=search&token=' + token_json['token'] + '&search_imdb=' + imdb_id
    print(search_uri)

    if token_response.from_cache == False: #Let's make sure we don't call to fast if we just got a new key
        print('We just got a new token, Lets wait for 3 secs before we move on')
        time.sleep(2)

    response = requests.get(search_uri)
    print("Was that API request cached? ",response.from_cache)
    json_resp = json.loads(response.text)
    if 'error' in json_resp:
        return json_resp
    torrent_list = []
    for torrent in json_resp['torrent_results']:
        torrent_list.append(TorrentFile(torrent))
    return torrent_list

def getVideoRate(VideoFile):
    return VideoFile.video_bitrate_int;

def getMovieListFromDB():
    result = db.Movies.find()
    formated_result = list(result)
    video_list = []
    for movie in formated_result:
        video_list.append(VideoFile(movie))
        sorted_list = sorted(video_list, key=getVideoRate)
    return sorted_list

application = Flask(__name__)
cache_expire_time = datetime.timedelta(minutes=15)
requests_cache.install_cache(expire_after=cache_expire_time)
requests_cache.clear()
client = pymongo.MongoClient('ds137261.mlab.com',37261)
db = client['bacon_2017']
db.authenticate('bacon','F463Rlund')
# app.config['MONGO_DBNAME'] = 'something'
# app.config['MONGO_URI'] = 'URI'
#
# mongo = PyMongo(app)

@application.route('/movies', methods=['GET'])
def list_movies():
    # https://torrentapi.org/apidocs_v2.txt
    url_for('static', filename='css/movies.css')
    video_list = getMovieListFromDB()
    return render_template('movies.html', movie_list=video_list)

@application.route('/movies/update/<imdb_id>', methods=['GET'])
def list_torrents(imdb_id):
    url_for('static', filename='css/movies.css')
    torrent_list = get_Torrent_List_By_IMDB_ID(imdb_id)
    return render_template('torrents.html', torrent_list=torrent_list)

@application.route('/pickup/wilson', methods=['GET'])
def announce_wilson():
    url_for('static', filename='style.css')
    return render_template('wilson.html')


@application.route('/ferry', methods=['GET'])
def get_all_ferry():

    # TODO: Set a timout for the cache
    response = requests.get('http://www.nwff.com.hk/api/time_table_search.php?lang=eng&origin=CE&destination=MW&vessel=any')
    print("Was that API request cached? ",response.from_cache)

    schedule = json.loads(response.text.replace(u'\ufeff', ''))
    index = find_last_two_departures_from_now(schedule)
    url_for('static', filename='css/ferry.css')
    url_for('static', filename='css/bootstrap.min.css')
    url_for('static', filename='js/bootstrap.min.js')
    return render_template('ferry.html', schedule=schedule)

@application.route('/api', methods=['GET'])
def test_api():

    return json.text

def find_last_two_departures_from_now(json):
    current_time = datetime.datetime.now()
    for departure in json:
        departure_time_str = departure['schedule']['time'];
        departure_date_str = datetime.date.fromtimestamp(departure['date'])
        d = datetime.datetime.strptime(departure_date_str.isoformat() + "-" + departure_time_str, '%Y-%m-%d-%H:%M:%S')
        print(d)
        if current_time < d:
            return json.index(departure)-2

if __name__ == '__main__':
    application.debug = True
    application.run()
