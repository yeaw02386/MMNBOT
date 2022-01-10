from re import M
from googleapiclient.discovery import build
from oauth2client.transport import request
from dotenv import load_dotenv
import os


load_dotenv()
api_key = os.getenv('API_KEY')


#ใช้ youtube data api เพื่อดึงข้อมูลเพลงแบบเป็น playlist
def yt_playlist(playlistid,req,que):
    youtube = build('youtube', 'v3', developerKey=api_key)
    token = None
    playlist = []
    while True :
        request = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlistid,
            maxResults=45,
            pageToken=token
        )
        response = request.execute()

        i = 0
        try :
            while True :
                temp = {'webpage_url':'https://www.youtube.com/watch?v='
                                    +response['items'][i]['snippet']
                                    ['resourceId']['videoId'],
                        'requester':req,
                        'title':response['items'][i]['snippet']['title'],
                        'thumbnails':response['items'][i]['snippet']
                                    ['thumbnails']['default']['url'],
                        'queue':que
                        }
                playlist.append(temp)
                que += 1
                i += 1
        except : pass
        try : 
            token = response['nextPageToken']
        except : 
            return playlist,que

#ใช้ youtube data api เพื่อดึงข้อมูลเพลงแบบเป็น video
def yt_video(id,req,que):
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.videos().list(
        part="snippet,contentDetails",
        id=id
    )
    response = request.execute()
    if que != 1: 
        que += 1  

    return {'webpage_url':'https://www.youtube.com/watch?v='+id,
            'requester':req,
            'title':response['items'][0]['snippet']['title'],
            'thumbnails':response['items'][0]['snippet']['thumbnails']['default']['url'],
            'queue':que,
            'check':'True'},que


