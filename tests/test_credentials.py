import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

def test_spotify_credentials():
    """Test if Spotify credentials are working."""
    load_dotenv()
    
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("❌ Spotify credentials not found in .env file")
        return False
    
    try:
        client_credentials_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        
        # Test API call
        results = sp.new_releases(limit=1)
        
        print("✅ Spotify API credentials are working!")
        print(f"📊 Test result: Found album '{results['albums']['items'][0]['name']}'")
        return True
        
    except Exception as e:
        print(f"❌ Spotify API test failed: {str(e)}")
        return False

def test_youtube_credentials():
    """Test YouTube API credentials (optional)."""
    load_dotenv()
    
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("⚠️  YouTube API key not found (optional)")
        return True
    
    try:
        import requests
        
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': 'music',
            'type': 'video',
            'key': api_key,
            'maxResults': 1
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        print("✅ YouTube API credentials are working!")
        return True
        
    except Exception as e:
        print(f"❌ YouTube API test failed: {str(e)}")
        return False
    
if __name__ == "__main__":
    print("🔍 Testing API credentials...")
    print()
    
    spotify_ok = test_spotify_credentials()
    youtube_ok = test_youtube_credentials()
    
    print()
    if spotify_ok:
        print("🎉 Ready to run Spotify ingestion!")
    else:
        print("🔧 Fix Spotify credentials before proceeding")
    