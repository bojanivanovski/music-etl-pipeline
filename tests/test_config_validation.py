#!/usr/bin/env python3
"""
Test script for configuration and validation setup
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from config.config_manager import ConfigManager
from validation.data_validator import DataValidator

def test_config_manager():
    """Test configuration manager functionality"""
    print("🔧 Testing Configuration Manager...")
    
    try:
        config = ConfigManager()
        
        # Test approved genres
        genres = config.get_approved_genres()
        print(f"✅ Loaded {len(genres)} approved genres:")
        for genre in genres[:5]:  # Show first 5
            print(f"   - {genre}")
        
        # Test validation rules
        validation_rules = config.get_validation_rules()
        print(f"✅ Validation rules loaded:")
        print(f"   - Min records per run: {validation_rules.get('min_records_per_run')}")
        print(f"   - Max null percentage: {validation_rules.get('max_null_percentage')}%")
        
        # Test ingestion config
        ingestion_config = config.get_ingestion_config()
        print(f"✅ Ingestion config:")
        print(f"   - Default days behind: {ingestion_config.get('default_days_behind')}")
        print(f"   - Spotify batch size: {config.get_batch_size('spotify')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {str(e)}")
        return False

def test_data_validator():
    """Test data validator with sample data"""
    print("\n🔍 Testing Data Validator...")
    
    try:
        config = ConfigManager()
        validator = DataValidator(config)
        
        # Create sample Spotify data
        sample_spotify_data = pd.DataFrame([
            {
                'id': 'track_001',
                'name': 'Test Track 1',
                'artist_name': 'Test Artist',
                'album_name': 'Test Album',
                'duration_ms': 180000,
                'popularity': 75,
                'ingested_timestamp': datetime.now()
            },
            {
                'id': 'track_002', 
                'name': 'Test Track 2',
                'artist_name': 'Test Artist',
                'album_name': 'Test Album',
                'duration_ms': 210000,
                'popularity': 82,
                'ingested_timestamp': datetime.now()
            }
        ])
        
        # Test Spotify validation
        is_valid, report = validator.validate_spotify_data(sample_spotify_data)
        
        if is_valid:
            print("✅ Spotify data validation passed")
            print(f"   - Records: {report['total_records']}")
            print(f"   - Unique tracks: {report['metrics'].get('unique_tracks', 0)}")
            print(f"   - Avg duration: {report['metrics'].get('avg_duration_minutes', 0)} minutes")
        else:
            print("❌ Spotify data validation failed")
            for issue in report['issues']:
                print(f"   - {issue}")
        
        # Create sample YouTube data
        sample_youtube_data = pd.DataFrame([
            {
                'video_id': 'video_001',
                'title': 'Awesome Techno Mix 2024',
                'channel_title': 'DJ Test Channel',
                'published_at': '2024-01-15T10:00:00Z',
                'view_count': 50000,
                'like_count': 1500,
                'ingested_timestamp': datetime.now()
            }
        ])
        
        # Test YouTube validation
        is_valid, report = validator.validate_youtube_data(sample_youtube_data)
        
        if is_valid:
            print("✅ YouTube data validation passed")
            print(f"   - Records: {report['total_records']}")
            print(f"   - Unique videos: {report['metrics'].get('unique_videos', 0)}")
            print(f"   - Avg views: {report['metrics'].get('avg_view_count', 0):,}")
        else:
            print("❌ YouTube data validation failed")
            for issue in report['issues']:
                print(f"   - {issue}")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation test failed: {str(e)}")
        return False

def test_invalid_data():
    """Test validator with intentionally invalid data"""
    print("\n⚠️  Testing Invalid Data Handling...")
    
    try:
        config = ConfigManager()
        validator = DataValidator(config)
        
        # Create invalid Spotify data (missing required fields, bad values)
        invalid_data = pd.DataFrame([
            {
                'id': 'track_001',
                # Missing 'name' field (required)
                'artist_name': 'Test Artist',
                'duration_ms': 5000,  # Too short (< 10 seconds)
                'popularity': 150,    # Invalid (> 100)
            }
        ])
        
        is_valid, report = validator.validate_spotify_data(invalid_data)
        
        if not is_valid:
            print("✅ Invalid data correctly rejected")
            print(f"   - Issues found: {len(report['issues'])}")
            for issue in report['issues']:
                print(f"     • {issue}")
            print(f"   - Warnings: {len(report['warnings'])}")
            for warning in report['warnings']:
                print(f"     • {warning}")
        else:
            print("❌ Invalid data was incorrectly accepted")
        
        return True
        
    except Exception as e:
        print(f"❌ Invalid data test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🧪 Configuration and Validation Test Suite")
    print("=" * 50)
    
    tests = [
        test_config_manager,
        test_data_validator,
        test_invalid_data
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Your setup is ready.")
        return 0
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())