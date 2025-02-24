import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from openai import OpenAI
from typing import Any, Dict, List

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

def askGPT(client, system_prompt, message, format):
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
                    "others": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["title", "artist", "album", "year", "others"],
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
                        "items": {
                            "anyOf": [
                                {"type": "integer"},
                                {
                                    "type": "array",
                                    "items": {"type": "string"},
                                }
                            ]
                        },
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
ただし、ユーザーの打ち間違えや、アーティスト・曲名の略称とかもあるかもしれないので、Spotifyで検索するときに引っ掛かるような正式なものにちゃんと変えてください。
例: "Mrs.GREENAPPLE" → "Mrs.GREEN APPLE", "ずとまよ" → "ずっと真夜中でいいのに。"
title: 曲のタイトル。文字列。
artist: アーティスト名。文字列。
album: アルバム名。文字列。
year: その曲が出た年。2023年〜2024年なら"2023-2024"。2022年なら"2022"。文字列。
other: その他に雰囲気などの曲の特徴。リスト形式
要望が特にない項目はから文字('')にしてください。

- 例1
  ユーザー: "米津玄師の曲で、2022年に出た曲で、アップテンポで盛り上がるなものにしてください"
  リスポンス: {{'title': '', 'artist': '米津玄師', 'album': '', 'year': '2022', 'others': ['アップテンポ', '盛り上がる']}}
- 例2
  ユーザー: "2022年以降に出て、artcoreの曲にしてください"
  リスポンス: {{'title': '', 'artist': '', 'album': '', 'year': '2022-2025', 'others': ['artcore']}}
"""

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=sp_client_id, client_secret=sp_client_secret))

def search_track(title, artist, album, year, limit=30):
    if not title and not artist and not album and not year:
        return []
    else:
        query = " ".join(filter(None, [
            f"track:{title}" if title else "",
            f"artist:{artist}" if artist else "",
            f"album:{album}" if album else "",
            f"year:{year}" if year else ""
        ]))
        print(query)
        try:
            results = sp.search(q=query, limit=limit, type='track')
            tracks = results['tracks']['items']
            return tracks
        except Exception as e:
            print(f"Error in search_track: {e}")
            return []

def return_songs(user_query: str, model_type: str = "GPT") -> List[Dict[str, str]]:
    try:
        if model_type == "GPT":
            conditions = askGPT(client, system_prompt1, user_query, generate_arrange_json())
        elif model_type == "Gemini":
            conditions = askGoogleAI(system_prompt1 + "\n実際のユーザーのリクエスト: " + user_query + "\n リスポンス形式: {'title': str, 'artist': str, 'album': str, 'year': str, 'others': list(str)}")
        else:
            print("Invalid model type specified")
            return []

        print(conditions)
        song_list_tracks = search_track(conditions.get("title", ""), conditions.get("artist", ""), conditions.get("album", ""), conditions.get("year", ""), limit=50)

        song_list = []
        for idx, track in enumerate(song_list_tracks):
            artists = []
            for artist in track["artists"]:
                artists.append(artist["name"])
            song_list.append(
                {
                    "title": track['name'],
                    "artist": artists, 
                    "id": idx
                }
            )

        print(song_list)

        system_prompt2 = """
        あなたは、曲の雰囲気や、特徴、情報などを考えて、条件に合うような10個を選ぶアシスタントです。
        ユーザーから与えられるsong_listの中で、conditionを満たすようなものを10個教えてください。
        song_listのそれぞれの曲に数字が割り当てられているので、その数字のみをintegerとして、リストにして返してください。

        もしsong_listが空の場合は、conditionを満たすような10個を自由に選んで、['{artist名}', '{タイトル名}']の形式でarray<string>としてリストにして返してください。
        もしsong_list内でconditionを満たすような曲が10個に満たない場合、song_listの傾向から、それを選んだ人が好きそうな、conditionを満たす曲を10曲自由に選んで、['{artist名}', '{タイトル名}']の形式でarray<string>としてリストにして返してください。

        つまり、idは必ずsong_listにあるidのみ。そして、条件を満たす曲が10曲に満たなければ、合計が10になるように、['{artist名}', '{タイトル名}']の形式で適切な曲を選んでください。
        例      song_ids: [0, 1, 2, 3, 4, 5, 6, 7, ['米津玄師', 'Lemon'], ['Mrs.GREEN APPLE', 'ライラック']]
        """

        user_query2 = f"""
        song_list: {song_list}
        condition: {conditions.get("others", [])}
        """

        if model_type == "GPT":
            song_ids = askGPT(client, system_prompt2, user_query2, generate_song_json()).get("song_ids", [])
        elif model_type == "Gemini":
            song_ids = askGoogleAI(system_prompt2 + "\n実際のユーザーのリクエスト: " + user_query2 + "\n リスポンス形式: {'song_ids': list(int)}").get("song_ids", [])

        print(song_ids)
        result_songs = []
        for song_id in song_ids:
            try:
                if isinstance(song_id, int):
                    track_info = song_list_tracks[song_id]
                    result_songs.append(track_info["uri"])
                else:
                    track_info = search_track(song_id[1], song_id[0], "", "", limit=1)[0]
                    result_songs.append(track_info["uri"])
            except (IndexError, ValueError) as e:
                print(f"Error retrieving track info for song_id {song_id}: {e}")
        return result_songs
    except Exception as e:
        print(f"Error in return_songs: {e}")
        return []

# テスト用のコード
if __name__ == "__main__":
    user_query = input("曲の条件を指定してください: \t")
    model_type = input("使用するモデルを指定してください (GPT/Gemini): \t")
    songs = return_songs(user_query, model_type)
    for song in songs:
        print(f"URI: {song}")