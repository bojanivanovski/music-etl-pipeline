import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import pandas as pd

from infrastructure.logger import Logger
from config.config_manager import ConfigManager
from validation.data_validator import DataValidator


class Artist:
    """Represents a Spotify artist"""
    
    def __init__(self, spotify_id, name, genres=None, popularity=0, followers=0, external_urls=None, images=None):
        self.spotify_id = spotify_id
        self.name = name
        self.genres = genres or []
        self.popularity = popularity
        self.followers = followers
        self.external_urls = external_urls or {}
        self.images = images or []
    
    @classmethod
    def from_json(cls, json_data):
        """Create Artist object from JSON data"""
        return cls(
            spotify_id=json_data.get('id'),
            name=json_data.get('name'),
            genres=json_data.get('genres', []),
            popularity=json_data.get('popularity', 0),
            followers=json_data.get('followers', 0),
            external_urls=json_data.get('external_urls', {}),
            images=json_data.get('images', [])
        )
    
    def to_json(self):
        """Convert Artist object to JSON dictionary"""
        return {
            'id': self.spotify_id,
            'name': self.name,
            'genres': self.genres,
            'popularity': self.popularity,
            'followers': self.followers,
            'external_urls': self.external_urls,
            'images': self.images
        }
    
    def __repr__(self):
        return f"Artist(id='{self.spotify_id}', name='{self.name}', genres={self.genres})"

class Album:
    """Represents a Spotify album"""
    
    def __init__(self, spotify_id, name, artist_name, release_date, total_tracks, album_type, images=None, external_urls=None):
        self.spotify_id = spotify_id
        self.name = name
        self.artist_name = artist_name
        self.release_date = release_date
        self.total_tracks = total_tracks
        self.album_type = album_type
        self.images = images or []
        self.external_urls = external_urls or {}
    
    @classmethod
    def from_json(cls, json_data):
        """Create Album object from JSON data"""
        return cls(
            spotify_id=json_data.get('id'),
            name=json_data.get('name'),
            artist_name=json_data.get('artists', [{}])[0].get('name', '') if json_data.get('artists') else '',
            release_date=json_data.get('release_date'),
            total_tracks=json_data.get('total_tracks', 0),
            album_type=json_data.get('album_type'),
            images=json_data.get('images', []),
            external_urls=json_data.get('external_urls', {})
        )
    
    def to_json(self):
        """Convert Album object to JSON dictionary"""
        return {
            'id': self.spotify_id,
            'name': self.name,
            'artist_name': self.artist_name,
            'release_date': self.release_date,
            'total_tracks': self.total_tracks,
            'album_type': self.album_type,
            'images': self.images,
            'external_urls': self.external_urls
        }
    
    def __repr__(self):
        return f"Album(id='{self.spotify_id}', name='{self.name}', artist='{self.artist_name}')"

class Song:
    """Represents a Spotify song/track"""
    
    def __init__(self, spotify_id, name, artist_name, album_name, duration_ms, track_number, explicit=False, preview_url=None, external_urls=None, popularity=None, published_at=None):
        self.spotify_id = spotify_id
        self.name = name
        self.artist_name = artist_name
        self.album_name = album_name
        self.duration_ms = duration_ms
        self.track_number = track_number
        self.explicit = explicit
        self.preview_url = preview_url
        self.external_urls = external_urls or {}
        self.popularity = popularity
        self.published_at = published_at
    
    @classmethod
    def from_json(cls, json_data):
        """Create Song object from JSON data"""
        return cls(
            spotify_id=json_data.get('id'),
            name=json_data.get('name'),
            artist_name=json_data.get('artists', [{}])[0].get('name', '') if json_data.get('artists') else '',
            album_name=json_data.get('album', {}).get('name', '') if json_data.get('album') else '',
            duration_ms=json_data.get('duration_ms', 0),
            track_number=json_data.get('track_number', 0),
            explicit=json_data.get('explicit', False),
            preview_url=json_data.get('preview_url'),
            external_urls=json_data.get('external_urls', {}),
            popularity=json_data.get('popularity'),
            published_at=json_data.get('published_at')
        )
    
    def to_json(self):
        """Convert Song object to JSON dictionary"""
        return {
            'id': self.spotify_id,
            'name': self.name,
            'artist_name': self.artist_name,
            'album_name': self.album_name,
            'duration_ms': self.duration_ms,
            'track_number': self.track_number,
            'explicit': self.explicit,
            'preview_url': self.preview_url,
            'external_urls': self.external_urls,
            'popularity': self.popularity,
            'published_at': self.published_at
        }
    
    def __repr__(self):
        return f"Song(id='{self.spotify_id}', name='{self.name}', artist='{self.artist_name}')"

class SpotifyIngestion:
    
    def __init__(self):
        # Replace the hardcoded approved_genres with config
        self.config_manager = ConfigManager()
        self.approved_genres = self.config_manager.get_approved_genres()
        
        # Initialize validator
        self.validator = DataValidator(self.config_manager)
        
        self.logger =  Logger("SpotifyIngestion")
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
            self.spotify_client = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        except Exception as e:
            print(f"❌ Spotify create client fail: {str(e)}")
            return False
        
    def ingest_spotify_data(self, days_behind=7):
        # get artists
        artists = self.fetch_genre_artists()
        new_songs:list[Song] = []
        for artist in artists:
            albums = self.get_artist_recent_albums(artist.spotify_id)
            if len(albums) > 0 :
                songs = self.get_songs_for_albums(albums)
                if len(songs) > 0:
                    new_songs.append(songs)
        
        if len(new_songs) == 0:
            self.logger.warning("No songs found")
            return None
        
        all_songs = [song for songs in new_songs for song in songs]
        df = pd.DataFrame([song.to_json() for song in all_songs])
        df['ingested_timestamp'] = datetime.now()
        df['source'] = 'spotify'

        # NEW: Add data validation
        is_valid, validation_report = self.validator.validate_spotify_data(df)
        
        if not is_valid:
            self.logger.error("❌ Data validation failed")
            for issue in validation_report['issues']:
                self.logger.error(f"  - {issue}")
            return None
        
        # Log validation summary
        metrics = validation_report['metrics']
        self.logger.success(f"✅ Data validation passed: {len(df)} records")
        self.logger.info(f"📊 Unique tracks: {metrics.get('unique_tracks', 0)}")
        self.logger.info(f"📊 Unique artists: {metrics.get('unique_artists', 0)}")
        self.logger.info(f"📊 Avg popularity: {metrics.get('avg_popularity', 0)}")
        
        if validation_report['warnings']:
            self.logger.warning(f"⚠️  {len(validation_report['warnings'])} data quality warnings")
            for warning in validation_report['warnings']:
                self.logger.warning(f"  - {warning}")
        
        # Save to parquet file
        data_dir = Path("data/raw/spotify")
        data_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = data_dir / f"spotify_songs_{timestamp}.parquet"
        df.to_parquet(filename, index=False)

        
    
    def _query_artists_by_genre(self, genre, max_results=1000):
        """Query Spotify for artists by genre with pagination"""
        try:
            self.logger.info(f"Querying {genre} artists from Spotify with pagination")
            
            artists = []
            offset = 0
            limit = 50  # Spotify API max limit per request
            
            while len(artists) < max_results:
                try:
                    # Search for artists with the specified genre
                    results = self.spotify_client.search(
                        q=f'genre:"{genre}"',
                        type='artist',
                        limit=limit,
                        offset=offset
                    )
                    
                    # Check if we have results
                    if not results['artists']['items']:
                        self.logger.info(f"No more {genre} artists available")
                        break
                    
                    # Process current batch
                    for artist in results['artists']['items']:
                        if len(artists) >= max_results:
                            break
                            
                        artist_obj = Artist(
                            spotify_id=artist['id'],
                            name=artist['name'],
                            genres=artist['genres'],
                            popularity=artist['popularity'],
                            followers=artist['followers']['total'],
                            external_urls=artist['external_urls'],
                            images=artist['images']
                        )
                        artists.append(artist_obj)
                    
                    # Check if we've reached the end of available results
                    if len(results['artists']['items']) < limit:
                        self.logger.info(f"Reached end of {genre} artists results")
                        break
                    
                    offset += limit
                    self.logger.info(f"Retrieved {len(artists)} {genre} artists so far...")
                    
                    # Add small delay to avoid rate limiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    if "429" in str(e) or "rate limit" in str(e).lower():
                        self.logger.warning(f"Rate limit hit, waiting 30 seconds...")
                        time.sleep(30)
                        continue
                    else:
                        raise e
            
            # Filter artists by approved genres
            filtered_artists = self._filter_artists_by_approved_genres(artists)
            
            self.logger.success(f"Found {len(artists)} {genre} artists total, {len(filtered_artists)} after filtering")
            return filtered_artists
            
        except Exception as e:
            self.logger.error(f"Failed to query {genre} artists: {str(e)}")
            return []
    
    def _filter_artists_by_approved_genres(self, artists):
        """Filter artists to only include those with at least one approved genre"""
        filtered_artists = []
        
        for artist in artists:
            artist_genres = [genre.lower() for genre in artist.genres]
            approved_genres_lower = [genre.lower() for genre in self.approved_genres]
            
            # Check if artist has at least one approved genre
            has_approved_genre = any(genre in approved_genres_lower for genre in artist_genres)
            
            if has_approved_genre:
                filtered_artists.append(artist)
        
        return filtered_artists
    
    def _remove_duplicate_artists(self, artists):
        """Remove duplicate artists based on spotify_id"""
        seen_ids = set()
        unique_artists = []
        
        for artist in artists:
            if artist.spotify_id not in seen_ids:
                seen_ids.add(artist.spotify_id)
                unique_artists.append(artist)
        
        duplicates_removed = len(artists) - len(unique_artists)
        if duplicates_removed > 0:
            self.logger.info(f"Removed {duplicates_removed} duplicate artists")
        
        return unique_artists
    
    def _load_artists_locally(self, genre):
        """Load artist data from local JSON file and convert to Artist objects"""
        try:
            data_dir = Path("data/artists")
            filename = data_dir / f"{genre}_artists.json"
            
            if filename.exists():
                with open(filename, 'r') as f:
                    artists_data = json.load(f)
                
                # Convert JSON data to Artist objects
                artists = [Artist.from_json(artist_data) for artist_data in artists_data]
                self.logger.info(f"Loaded {len(artists)} {genre} artists from local file")
                return artists
            else:
                self.logger.info(f"No local {genre} artists file found")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to load {genre} artists from local file: {str(e)}")
            return None
    
    def _get_artists_by_genre(self, genre, max_results=1000, force_refresh=False):
        """Generic method to get artists by genre from local cache or API"""
        if not force_refresh:
            # Try to load from local file first
            local_artists = self._load_artists_locally(genre)
            if local_artists:
                return local_artists
        
        # If no local data or force refresh, query from API
        self.logger.info(f"Fetching {genre} artists from Spotify API")
        artists = self._query_artists_by_genre(genre, max_results)
        if artists:
            self._save_artists_locally(artists, genre)
        return artists
    
    def _get_house_artists(self, max_results=1000, force_refresh=False):
        """Get house genre artists from local cache or API"""
        return self._get_artists_by_genre('house', max_results, force_refresh)
    
    def _get_techno_artists(self, max_results=1000, force_refresh=False):
        """Get techno genre artists from local cache or API"""
        return self._get_artists_by_genre('techno', max_results, force_refresh)
    
    def _save_artists_locally(self, artists, genre):
        """Save Artist objects to local JSON file"""
        try:
            # Create data directory if it doesn't exist
            data_dir = Path("data/artists")
            data_dir.mkdir(parents=True, exist_ok=True)
            
            filename = data_dir / f"{genre}_artists.json"
            
            # Convert Artist objects to JSON data
            artists_data = [artist.to_json() for artist in artists]
            
            with open(filename, 'w') as f:
                json.dump(artists_data, f, indent=2)
            
            self.logger.success(f"Saved {len(artists)} {genre} artists to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save {genre} artists: {str(e)}")
            return False
    
    def fetch_genre_artists(self, genres=['house', 'techno'], max_results=1000, force_refresh=False) -> list[Artist]:
        """Main method to discover and save artists from specified genres"""
        self.logger.info(f"Starting genre artist discovery for: {', '.join(genres)}")
        
        all_artists = []
        
        for genre in genres:
            artists = self._get_artists_by_genre(genre, max_results, force_refresh)
            all_artists.extend(artists)
        
        # Remove duplicates based on spotify_id
        unique_artists = self._remove_duplicate_artists(all_artists)
        
        self.logger.success(f"Discovery complete! Found {len(unique_artists)} unique artists total")
        return unique_artists
    
    def get_artist_recent_albums(self, artist_id: str):
        """Get albums from artist released this week."""
        try:
            albums = self.spotify_client.artist_albums(artist_id, album_type='album,single', limit=50)
        
            recent_albums = []
            for album in albums['items']:
                if self.is_released_this_week(album['release_date']):
                    album_obj = Album.from_json(album)
                    recent_albums.append(album_obj)
        
            self.logger.info(f"Fetched {len(recent_albums)} albums for artist:{artist_id}")
            return recent_albums
        except Exception as e:
            self.logger.error(f"Error fetching artist albums, artist:{artist_id}: {str(e)}")
            return []

 
    
    def get_songs_for_albums(self, albums) -> list[Song]:
        """Get songs for a list of albums"""
        all_songs:list[Song] = []
        
        for album in albums:
            try:
                # Get tracks from the album
                tracks = self.spotify_client.album_tracks(album.spotify_id, limit=50)
                
                for track in tracks['items']:
                    # Create song object with album information
                    song_data = track.copy()
                    song_data['album'] = {'name': album.name}
                    song_data['published_at'] = album.release_date
                    song_obj = Song.from_json(song_data)
                    all_songs.append(song_obj)
                
                self.logger.info(f"Fetched {len(tracks['items'])} songs from album: {album.name}")
                
            except Exception as e:
                self.logger.error(f"Error fetching songs for album {album.name}: {str(e)}")
                continue
        
        # Get popularity data for all songs
        all_songs_with_popularity = self.get_tracks_popularity(all_songs)
        
        self.logger.success(f"Fetched {len(all_songs_with_popularity)} songs total from {len(albums)} albums")
        return all_songs_with_popularity
    
    def is_released_this_week(self, release_date_str):
        """Check if album was released in the last 7 days."""
        try:
            # Handle different date formats: '2024-01-15' or '2024'
            if len(release_date_str) == 4:  # Just year
                return False
            
            release_date = datetime.strptime(release_date_str, '%Y-%m-%d')
            week_ago = datetime.now() - timedelta(days=7)
            return release_date >= week_ago
        except:
            return False
    
    def get_tracks_popularity(self, songs: list[Song]) -> list[Song]:
        """Get popularity data for tracks using Spotify's Get Several Tracks API"""
        if not songs:
            return songs
        
        try:
            # Spotify API allows up to 50 tracks per request
            batch_size = 50
            updated_songs = []
            
            for i in range(0, len(songs), batch_size):
                batch = songs[i:i + batch_size]
                track_ids = [song.spotify_id for song in batch if song.spotify_id]
                
                if not track_ids:
                    updated_songs.extend(batch)
                    continue
                
                # Get track details including popularity
                tracks_data = self.spotify_client.tracks(track_ids)
                
                # Create a mapping of track_id to popularity
                popularity_map = {}
                for track in tracks_data['tracks']:
                    if track:  # API can return None for invalid track IDs
                        popularity_map[track['id']] = track['popularity']
                
                # Update songs with popularity data
                for song in batch:
                    if song.spotify_id in popularity_map:
                        song.popularity = popularity_map[song.spotify_id]
                    updated_songs.append(song)
                
                # Add small delay to avoid rate limiting
                time.sleep(0.1)
                
            self.logger.success(f"Updated popularity data for {len(updated_songs)} tracks")
            return updated_songs
            
        except Exception as e:
            self.logger.error(f"Error fetching track popularity: {str(e)}")
            return songs