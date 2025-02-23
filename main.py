import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from openai import OpenAI
from typing import Any, Dict

load_dotenv()

# 環境変数からAPIキーを取得
google_ai_key = os.getenv("GOOGLE_AI_KEY")
open_ai_key = os.getenv("OPEN_AI_KEY")
sp_client_id = os.getenv("SPOTIFY_CLIENT_ID")
sp_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

if (not google_ai_key and not open_ai_key) or not sp_client_id or not sp_client_secret:
    raise ValueError("APIキーまたはクライアントシークレットが設定されていません")

genai.configure(api_key=google_ai_key)
client = OpenAI(api_key=open_ai_key)

# モデルの準備
model = genai.GenerativeModel(
    "gemini-1.5-flash",
    generation_config={"response_mime_type": "application/json"}
)

def askGoogleAI(prompt):
    try:
        raw_response = model.generate_content(prompt)
        response_parsed = json.loads(raw_response.text)
        return response_parsed
    except Exception as e:
        print(f"Error in askGoogleAI: {e}")
        return {}

def askGPT(system_prompt, message, format):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content": message}
            ],
            response_format=format,
            model="gpt-4o-2024-08-06",
        )
        response_str = chat_completion.choices[0].message.content
        print(response_str)
        response_parsed = json.loads(response_str)
        return response_parsed
    except Exception as e:
        print(f"Error in askGPT: {e}")
        return {}

def generate_arrange_json() -> Dict[str, Any]:
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "arranged_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "artist": {"type": "string"},
                    "album": {"type": "string"},
                    "year": {"type": "string"},
                    "genre": {"type": "string"},
                    "others": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["title", "artist", "album", "year", "genre", "others"],
                "additionalProperties": False,
            },
        },
    }
    return response_format

def generate_song_json() -> Dict[str, Any]:
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "song_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "song_ids": {
                        "type": "array",
                        "items": {"type": "integer"}
                    }
                },
                "required": ["song_ids"],
                "additionalProperties": False,
            }
        }
    }
    return response_format

system_prompt1 = """
あなたはユーザーのリクエストした曲の特徴を整理するアシスタントです。要望を項目ごとにまとめてください。
title: 曲のタイトル。文字列。
artist: アーティスト名。文字列。
album: アルバム名。文字列。
year: その曲が出た年。2023年〜2024年なら"2023-2024"。2022年なら"2022"。文字列。
genre: その曲のジャンル。文字列。
other: その他に雰囲気などの曲の特徴。リスト形式
要望が特にない項目はから文字('')にしてください。

- 例1
  ユーザー: "米津玄師の曲で、2022年に出た曲で、アップテンポで盛り上がるなものにしてください"
  リスポンス: {{'title': '', 'artist': '米津玄師', 'album': '', 'year': '2022', 'genre': '', 'others': ['アップテンポ', '盛り上がる']}}
- 例2
  ユーザー: "2022年以降に出て、artcoreの曲にしてください"
  リスポンス: {{'title': '', 'artist': '', 'album': '', 'year': '2022-2025', 'genre': 'artcore', 'others': []}}
"""

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=sp_client_id, client_secret=sp_client_secret))

def search_track(title, artist, album, year, genre, limit=30):
    query = " ".join(filter(None, [
        f"track:{title}" if title else "",
        f"artist:{artist}" if artist else "",
        f"album:{album}" if album else "",
        f"year:{year}" if year else "",
        f"genre:{genre}" if genre else ""
    ]))
    print(query)
    results = sp.search(q=query, limit=limit, type='track')
    tracks = results['tracks']['items']
    return tracks

user_query1 = input("曲の条件を指定してください: \t")

try:
    conditions = askGPT(system_prompt1, user_query1, generate_arrange_json())
    print(conditions)
    song_list_tracks = search_track(conditions["title"], conditions["artist"], conditions["album"], conditions["year"], conditions["genre"], limit=30)

    song_list = [{'artist': track["artists"][0]["name"], 'track': track["name"], 'id': idx} for idx, track in enumerate(song_list_tracks)]

    print(song_list)

    system_prompt2 = """
    あなたは、曲の雰囲気や、特徴、情報などを考えて、条件に合うような10個を選ぶアシスタントです。
    ユーザーから与えられるsong_listの中で、conditionを満たすようなものを10個教えてください。
    song_listのそれぞれの曲に数字が割り当てられているので、その数字のみをリストにして返してください
    """

    user_query2 = f"""
    song_list: {song_list}
    condition: {conditions["others"]}
    """

    song_ids = askGPT(system_prompt2, user_query2, generate_song_json())["song_ids"]
    print(song_ids)
    for song_id in song_ids:
        try:
            track_info = song_list_tracks[song_id]
            print(f"TITLE: {track_info['name'].ljust(30)} URL: {track_info['id']}")
        except (IndexError, ValueError) as e:
            print(f"Error retrieving track info for song_id {song_id}: {e}")
except Exception as e:
    print(f"Error in main process: {e}")

del sp