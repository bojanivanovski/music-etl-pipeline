import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from infrastructure.logger import Logger
from config.config_manager import ConfigManager
from validation.data_validator import DataValidator


class YouTubeVideo:
    """Represents a YouTube video/track"""
    
    def __init__(self, video_id, title, channel_title, description, published_at, 
                 duration, view_count=0, like_count=0, comment_count=0, 
                 tags=None, category_id=None, thumbnail_url=None):
        self.video_id = video_id
        self.title = title
        self.channel_title = channel_title
        self.description = description
        self.published_at = published_at
        self.duration = duration
        self.view_count = view_count
        self.like_count = like_count
        self.comment_count = comment_count
        self.tags = tags or []
        self.category_id = category_id
        self.thumbnail_url = thumbnail_url
    
    @classmethod
    def from_search_result(cls, search_item, video_details=None):
        """Create YouTubeVideo object from search result and video details"""
        snippet = search_item['snippet']
        
        # Extract video statistics if available
        stats = video_details.get('statistics', {}) if video_details else {}
        content_details = video_details.get('contentDetails', {}) if video_details else {}
        
        return cls(
            video_id=search_item['id']['videoId'],
            title=snippet['title'],
            channel_title=snippet['channelTitle'],
            description=snippet['description'],
            published_at=snippet['publishedAt'],
            duration=content_details.get('duration', ''),
            view_count=int(stats.get('viewCount', 0)),
            like_count=int(stats.get('likeCount', 0)),
            comment_count=int(stats.get('commentCount', 0)),
            tags=snippet.get('tags', []),
            category_id=snippet.get('categoryId'),
            thumbnail_url=snippet.get('thumbnails', {}).get('high', {}).get('url')
        )
    
    def to_json(self):
        """Convert YouTubeVideo object to JSON dictionary"""
        return {
            'video_id': self.video_id,
            'title': self.title,
            'channel_title': self.channel_title,
            'description': self.description,
            'published_at': self.published_at,
            'duration': self.duration,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'tags': self.tags,
            'category_id': self.category_id,
            'thumbnail_url': self.thumbnail_url
        }
    
    def __repr__(self):
        return f"YouTubeVideo(id='{self.video_id}', title='{self.title}', channel='{self.channel_title}')"

class YouTubeIngestion:
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.approved_genres = self.config_manager.get_approved_genres()
        
        # Initialize validator  
        self.validator = DataValidator(self.config_manager)
        
        self.logger = Logger("YouTubeIngestion")
        load_dotenv()
        
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            self.logger.error("YouTube API key not found in .env file")
            raise ValueError("YouTube API key is required")
        
        try:
            self.youtube = build('youtube', 'v3', developerKey=api_key)
        except Exception as e:
            self.logger.error(f"Failed to initialize YouTube API client: {str(e)}")
            raise e
    
    def ingest_youtube_data(self, days_behind=7):
        """Main method to ingest YouTube music data from the previous week"""
        self.logger.info(f"Starting YouTube music ingestion for last {days_behind} days")
        
        # Get videos for each approved genre
        all_videos = []
        for genre in self.approved_genres:
            videos = self.search_music_by_genre(genre, days_behind)
            all_videos.extend(videos)
        
        # Remove duplicates based on video_id
        unique_videos = self._remove_duplicate_videos(all_videos)
        
        # Create DataFrame and add metadata
        df = pd.DataFrame([video.to_json() for video in unique_videos])
        df['ingested_timestamp'] = datetime.now()
        df['source'] = 'youtube'
        
        is_valid, validation_report = self.validator.validate_youtube_data(df)
        
        if not is_valid:
            self.logger.error("❌ Data validation failed")
            for issue in validation_report['issues']:
                self.logger.error(f"  - {issue}")
            return None
        
        # Log validation summary
        metrics = validation_report['metrics']
        self.logger.success(f"✅ Data validation passed: {len(df)} records")
        self.logger.info(f"📊 Unique videos: {metrics.get('unique_videos', 0)}")
        self.logger.info(f"📊 Unique channels: {metrics.get('unique_channels', 0)}")
        self.logger.info(f"📊 Avg views: {metrics.get('avg_view_count', 0):,}")
        
        if validation_report['warnings']:
            self.logger.warning(f"⚠️  {len(validation_report['warnings'])} data quality warnings")
            for warning in validation_report['warnings']:
                self.logger.warning(f"  - {warning}")
                    
        # Save to parquet file
        data_dir = Path("data/raw/youtube")
        data_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = data_dir / f"youtube_videos_{timestamp}.parquet"
        df.to_parquet(filename, index=False)
        
        self.logger.success(f"Ingested {len(unique_videos)} unique YouTube videos and saved to {filename}")
        return df
    
    def search_music_by_genre(self, genre, days_behind=7):
        """Search for music videos by genre published in the last N days"""
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_behind)
            
            # Format dates for YouTube API (RFC 3339)
            published_after = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            published_before = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            self.logger.info(f"Searching for {genre} music from {published_after} to {published_before}")
            
            videos = []
            next_page_token = None
            max_results_per_page = 50
            max_total_results = 200  # Limit to avoid quota issues
            
            while len(videos) < max_total_results:
                try:
                    # Search for videos
                    search_response = self.youtube.search().list(
                        q=f'{genre} music',
                        part='snippet',
                        type='video',
                        order='date',
                        publishedAfter=published_after,
                        publishedBefore=published_before,
                        videoCategoryId='10',  # Music category
                        maxResults=min(max_results_per_page, max_total_results - len(videos)),
                        pageToken=next_page_token
                    ).execute()
                    
                    if not search_response['items']:
                        break
                    
                    # Get video IDs for detailed information
                    video_ids = [item['id']['videoId'] for item in search_response['items']]
                    
                    # Get detailed video information
                    video_details = self.get_video_details(video_ids)
                    
                    # Create video objects
                    for search_item in search_response['items']:
                        video_id = search_item['id']['videoId']
                        details = video_details.get(video_id, {})
                        
                        video = YouTubeVideo.from_search_result(search_item, details)
                        
                        # Filter by genre relevance (check title, description, tags)
                        if self._is_genre_relevant(video, genre):
                            videos.append(video)
                    
                    # Check for next page
                    next_page_token = search_response.get('nextPageToken')
                    if not next_page_token:
                        break
                    
                    # Rate limiting
                    time.sleep(0.1)
                    
                except HttpError as e:
                    if e.resp.status == 403:
                        self.logger.warning(f"Quota exceeded for {genre} search")
                        break
                    else:
                        raise e
            
            self.logger.info(f"Found {len(videos)} {genre} videos")
            return videos
            
        except Exception as e:
            self.logger.error(f"Failed to search for {genre} music: {str(e)}")
            return []
    
    def get_video_details(self, video_ids):
        """Get detailed information for a list of video IDs"""
        try:
            if not video_ids:
                return {}
            
            # YouTube API allows up to 50 video IDs per request
            batch_size = 50
            all_details = {}
            
            for i in range(0, len(video_ids), batch_size):
                batch_ids = video_ids[i:i + batch_size]
                
                response = self.youtube.videos().list(
                    part='statistics,contentDetails,snippet',
                    id=','.join(batch_ids)
                ).execute()
                
                for item in response['items']:
                    all_details[item['id']] = item
                
                # Rate limiting
                time.sleep(0.1)
            
            return all_details
            
        except Exception as e:
            self.logger.error(f"Failed to get video details: {str(e)}")
            return {}
    
    def _is_genre_relevant(self, video, genre):
        """Check if a video is relevant to the specified genre"""
        genre_lower = genre.lower()
        
        # Check title
        if genre_lower in video.title.lower():
            return True
        
        # Check description
        if genre_lower in video.description.lower():
            return True
        
        # Check tags
        for tag in video.tags:
            if genre_lower in tag.lower():
                return True
        
        # Check for related terms
        related_terms = {
            'techno': ['electronic', 'edm', 'rave', 'underground'],
            'house': ['electronic', 'edm', 'dance', 'club'],
            'acid techno': ['acid', 'electronic', 'rave'],
            'disco house': ['disco', 'funky', 'groove'],
            'funky house': ['funky', 'groove', 'disco'],
            'acid house': ['acid', 'electronic', 'rave'],
            'chicago house': ['chicago', 'deep house'],
            'progressive house': ['progressive', 'electronic', 'trance']
        }
        
        if genre in related_terms:
            text_to_check = f"{video.title} {video.description}".lower()
            for term in related_terms[genre]:
                if term in text_to_check:
                    return True
        
        return False
    
    def _remove_duplicate_videos(self, videos):
        """Remove duplicate videos based on video_id"""
        seen_ids = set()
        unique_videos = []
        
        for video in videos:
            if video.video_id not in seen_ids:
                seen_ids.add(video.video_id)
                unique_videos.append(video)
        
        duplicates_removed = len(videos) - len(unique_videos)
        if duplicates_removed > 0:
            self.logger.info(f"Removed {duplicates_removed} duplicate videos")
        
        return unique_videos