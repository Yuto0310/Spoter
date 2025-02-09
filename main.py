import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials



load_dotenv()

# 環境変数からAPIキーを取得
google_ai_key = os.getenv("GOOGLE_AI_KEY")
sp_client_id = os.getenv("SPOTIFY_CLIENT_ID")
sp_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

if not google_ai_key or not sp_client_id or not sp_client_secret:
    raise ValueError("APIキーまたはクライアントシークレットが設定されていません")

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=sp_client_id, client_secret=sp_client_secret))

def search_track(title, artist, album, year, genre, limit=10):
    query = (f"track:{title} " if title != "" else "") + (f"artist:{artist} " if artist != "" else "") + (f"album:{album} " if album != "" else "") + (f"year:{year} " if year != "" else "") + (f"genre:{genre} " if genre != "" else "")
    print(query)
    results = sp.search(q=query, limit=limit, type='track')
    tracks = results['tracks']['items']

    return tracks


genai.configure(api_key=google_ai_key)

# モデルの準備
model = genai.GenerativeModel(
    "gemini-1.5-flash",
    generation_config={"response_mime_type": "application/json"}
)

def askGoogleAI(prompt):

    # 推論実行
    raw_response = model.generate_content(prompt)
    response_parsed = json.loads(raw_response.text)
    return response_parsed
user_query = input("曲の条件を指定してください: \t")

prompt1 = f"""
以下のユーザーの曲の情報を整理して以下の形式にしてください。ちなみに今は2025年です。
要望が特にない項目はから文字('')にしてください。

- 例1
  ユーザー: "米津玄師の曲で、2022年に出た曲で、アップテンポで盛り上がるなものにしてください"
  リスポンス: {{'title': '', 'artist': '米津玄師', 'album': '', 'year': '2022', 'genre': '', 'other': ['アップテンポ', '盛り上がる']}}
- 例2
  ユーザー: "2022年以降に出て、artcoreの曲にしてください"
  リスポンス: {{'title': '', 'artist': '', 'album': '', 'year': '2022-2025', 'genre': 'artcore', 'other': []}}

実際のユーザーの希望: "{user_query}"


形式
Return: {{'title': str, 'artist': str, 'album': str, 'year': str, 'genre': str, 'other': str[]}}

"""
conditions = askGoogleAI(prompt1)
print(conditions)
song_list_tracks = search_track(conditions["title"], conditions["artist"], conditions["album"], conditions["year"], conditions["genre"], limit=5)

song_list = []
for track in song_list_tracks:
    song_list.append({'artist': track["artists"][0]["name"], 'track': track["name"]})

print(song_list)
prompt2 = f"""
以下のsong_listの中で、conditionを満たすようなものを3個教えてください。
song_list: {song_list}
condition: {conditions["other"]}
以下の形式でお願いします

Song = {{'song_title': str}}
Return: list[Song]
"""

song_names = askGoogleAI(prompt2)
responses = [song["song_title"] for song in song_names]
print(responses)
for response in responses:
    print(f"TITLE: {response.ljust(30)} URL: {search_track(response, conditions['artist'], conditions['album'], conditions['year'], conditions['genre'], 5)[0]['external_urls']['spotify']}")

del sp