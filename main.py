import spotipy
import os
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
from song_list import return_songs

load_dotenv()
sp_client_id = os.getenv("SPOTIFY_CLIENT_ID")
sp_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
sp_redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
sp_playlist_id = os.getenv("SPOTER_PLAYLIST_ID")

scope = "playlist-modify-private"

# songs = return_songs("t+pazoliteの曲でアップテンポなもの", "Gemini")

sp_oauth = SpotifyOAuth(client_id=sp_client_id, client_secret=sp_client_secret, redirect_uri=sp_redirect_uri, scope=scope)
sp = spotipy.Spotify(auth_manager=sp_oauth)

user_id = sp.current_user()["id"]

user_query = input("曲のイメージを教えてください: \t")
songs = return_songs(user_query, "GPT")
print(f"song_uris: {songs}")
if songs:
  current_songs = sp.playlist_items(sp_playlist_id)["items"]
  current_song_ids = [song["track"]["uri"] for song in current_songs]
  if current_song_ids:
    sp.playlist_remove_all_occurrences_of_items(sp_playlist_id, current_song_ids)
  sp.playlist_add_items(sp_playlist_id, songs)

