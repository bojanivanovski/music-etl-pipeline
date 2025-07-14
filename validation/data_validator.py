"""Data validation for the Music ETL Pipeline"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re

from infrastructure.logger import Logger
from config.config_manager import ConfigManager

class DataValidationError(Exception):
    """Custom exception for data validation errors"""
    pass

class DataValidator:
    """Validates data quality and integrity for music data"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.validation_rules = config_manager.get_validation_rules()
        self.logger = Logger("DataValidator")
    
    def validate_spotify_data(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """Validate Spotify song data
        
        Returns:
            Tuple of (is_valid, validation_report)
        """
        self.logger.info(f"Validating Spotify data: {len(df)} records")
        
        validation_report = {
            'data_type': 'spotify_songs',
            'total_records': len(df),
            'validation_timestamp': datetime.now().isoformat(),
            'issues': [],
            'warnings': [],
            'metrics': {}
        }
        
        is_valid = True
        
        try:
            # Check if DataFrame is empty
            if df.empty:
                validation_report['issues'].append("Dataset is empty")
                return False, validation_report
            
            # 1. Required fields validation
            required_fields = self.config.get_required_fields('spotify_song')
            missing_fields = [field for field in required_fields if field not in df.columns]
            
            if missing_fields:
                validation_report['issues'].append(f"Missing required fields: {missing_fields}")
                is_valid = False
            
            # 2. Record count validation
            min_records = self.validation_rules.get('min_records_per_run', 1)
            max_records = self.validation_rules.get('max_records_per_run', 10000)
            
            if len(df) < min_records:
                validation_report['issues'].append(f"Too few records: {len(df)} < {min_records}")
                is_valid = False
            elif len(df) > max_records:
                validation_report['warnings'].append(f"High record count: {len(df)} > {max_records}")
            
            # 3. Null value validation
            null_percentage = (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
            max_null_pct = self.validation_rules.get('max_null_percentage', 20)
            
            if null_percentage > max_null_pct:
                validation_report['issues'].append(f"Too many null values: {null_percentage:.1f}% > {max_null_pct}%")
                is_valid = False
            
            # 4. Spotify-specific validations
            spotify_rules = self.validation_rules.get('spotify', {})
            
            # Duration validation
            if 'duration_ms' in df.columns:
                min_duration = spotify_rules.get('min_duration_ms', 10000)
                max_duration = spotify_rules.get('max_duration_ms', 1800000)
                
                invalid_durations = df[
                    (df['duration_ms'] < min_duration) | 
                    (df['duration_ms'] > max_duration)
                ]
                
                if not invalid_durations.empty:
                    validation_report['warnings'].append(
                        f"{len(invalid_durations)} tracks with invalid duration"
                    )
            
            # Popularity validation
            if 'popularity' in df.columns:
                min_pop = spotify_rules.get('min_popularity', 0)
                max_pop = spotify_rules.get('max_popularity', 100)
                
                invalid_popularity = df[
                    (df['popularity'] < min_pop) | 
                    (df['popularity'] > max_pop)
                ]
                
                if not invalid_popularity.empty:
                    validation_report['warnings'].append(
                        f"{len(invalid_popularity)} tracks with invalid popularity scores"
                    )
            
            # 5. Duplicate validation
            if 'id' in df.columns:
                duplicates = df.duplicated(subset=['id']).sum()
                if duplicates > 0:
                    validation_report['warnings'].append(f"{duplicates} duplicate track IDs found")
            
            # 6. Data quality metrics
            validation_report['metrics'] = {
                'null_percentage': round(null_percentage, 2),
                'unique_tracks': df['id'].nunique() if 'id' in df.columns else 0,
                'unique_artists': df['artist_name'].nunique() if 'artist_name' in df.columns else 0,
                'unique_albums': df['album_name'].nunique() if 'album_name' in df.columns else 0,
                'avg_duration_minutes': round(df['duration_ms'].mean() / 60000, 2) if 'duration_ms' in df.columns else 0,
                'avg_popularity': round(df['popularity'].mean(), 1) if 'popularity' in df.columns else 0
            }
            
            # Log results
            if is_valid:
                self.logger.success(f"Spotify data validation passed: {len(df)} records")
            else:
                self.logger.error(f"Spotify data validation failed: {len(validation_report['issues'])} issues")
            
            if validation_report['warnings']:
                self.logger.warning(f"Spotify data has {len(validation_report['warnings'])} warnings")
            
            return is_valid, validation_report
            
        except Exception as e:
            validation_report['issues'].append(f"Validation error: {str(e)}")
            self.logger.error(f"Data validation failed: {str(e)}")
            return False, validation_report
    
    def validate_youtube_data(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """Validate YouTube video data"""
        self.logger.info(f"Validating YouTube data: {len(df)} records")
        
        validation_report = {
            'data_type': 'youtube_videos',
            'total_records': len(df),
            'validation_timestamp': datetime.now().isoformat(),
            'issues': [],
            'warnings': [],
            'metrics': {}
        }
        
        is_valid = True
        
        try:
            # Check if DataFrame is empty
            if df.empty:
                validation_report['issues'].append("Dataset is empty")
                return False, validation_report
            
            # 1. Required fields validation
            required_fields = self.config.get_required_fields('youtube_video')
            missing_fields = [field for field in required_fields if field not in df.columns]
            
            if missing_fields:
                validation_report['issues'].append(f"Missing required fields: {missing_fields}")
                is_valid = False
            
            # 2. Record count validation
            min_records = self.validation_rules.get('min_records_per_run', 1)
            max_records = self.validation_rules.get('max_records_per_run', 10000)
            
            if len(df) < min_records:
                validation_report['issues'].append(f"Too few records: {len(df)} < {min_records}")
                is_valid = False
            elif len(df) > max_records:
                validation_report['warnings'].append(f"High record count: {len(df)} > {max_records}")
            
            # 3. YouTube-specific validations
            youtube_rules = self.validation_rules.get('youtube', {})
            
            # Title length validation
            if 'title' in df.columns:
                max_title_length = youtube_rules.get('max_title_length', 200)
                long_titles = df[df['title'].str.len() > max_title_length]
                
                if not long_titles.empty:
                    validation_report['warnings'].append(
                        f"{len(long_titles)} videos with titles exceeding {max_title_length} characters"
                    )
            
            # View count validation
            if 'view_count' in df.columns:
                min_views = youtube_rules.get('min_view_count', 0)
                invalid_views = df[df['view_count'] < min_views]
                
                if not invalid_views.empty:
                    validation_report['warnings'].append(
                        f"{len(invalid_views)} videos with invalid view counts"
                    )
            
            # 4. Date validation
            if 'published_at' in df.columns:
                try:
                    # Attempt to parse dates
                    pd.to_datetime(df['published_at'])
                except:
                    validation_report['issues'].append("Invalid date format in published_at field")
                    is_valid = False
            
            # 5. Duplicate validation
            if 'video_id' in df.columns:
                duplicates = df.duplicated(subset=['video_id']).sum()
                if duplicates > 0:
                    validation_report['warnings'].append(f"{duplicates} duplicate video IDs found")
            
            # 6. Data quality metrics
            validation_report['metrics'] = {
                'unique_videos': df['video_id'].nunique() if 'video_id' in df.columns else 0,
                'unique_channels': df['channel_title'].nunique() if 'channel_title' in df.columns else 0,
                'avg_view_count': int(df['view_count'].mean()) if 'view_count' in df.columns else 0,
                'avg_like_count': int(df['like_count'].mean()) if 'like_count' in df.columns else 0,
                'avg_title_length': round(df['title'].str.len().mean(), 1) if 'title' in df.columns else 0
            }
            
            # Log results
            if is_valid:
                self.logger.success(f"YouTube data validation passed: {len(df)} records")
            else:
                self.logger.error(f"YouTube data validation failed: {len(validation_report['issues'])} issues")
            
            if validation_report['warnings']:
                self.logger.warning(f"YouTube data has {len(validation_report['warnings'])} warnings")
            
            return is_valid, validation_report
            
        except Exception as e:
            validation_report['issues'].append(f"Validation error: {str(e)}")
            self.logger.error(f"Data validation failed: {str(e)}")
            return False, validation_report
    
    def generate_validation_summary(self, reports: List[Dict[str, Any]]) -> str:
        """Generate a human-readable validation summary"""
        if not reports:
            return "No validation reports to summarize"
        
        summary = []
        summary.append("=" * 50)
        summary.append("DATA VALIDATION SUMMARY")
        summary.append("=" * 50)
        
        total_records = sum(report['total_records'] for report in reports)
        total_issues = sum(len(report['issues']) for report in reports)
        total_warnings = sum(len(report['warnings']) for report in reports)
        
        summary.append(f"Total Records Validated: {total_records}")
        summary.append(f"Total Issues: {total_issues}")
        summary.append(f"Total Warnings: {total_warnings}")
        summary.append("")
        
        for report in reports:
            summary.append(f"Dataset: {report['data_type']}")
            summary.append(f"  Records: {report['total_records']}")
            summary.append(f"  Issues: {len(report['issues'])}")
            summary.append(f"  Warnings: {len(report['warnings'])}")
            
            if report['issues']:
                summary.append("  Critical Issues:")
                for issue in report['issues']:
                    summary.append(f"    - {issue}")
            
            if report['warnings']:
                summary.append("  Warnings:")
                for warning in report['warnings']:
                    summary.append(f"    - {warning}")
            
            if 'metrics' in report:
                summary.append("  Metrics:")
                for key, value in report['metrics'].items():
                    summary.append(f"    {key}: {value}")
            
            summary.append("")
        
        validation_status = "PASSED" if total_issues == 0 else "FAILED"
        summary.append(f"Overall Validation Status: {validation_status}")
        summary.append("=" * 50)
        
        return "\n".join(summary)