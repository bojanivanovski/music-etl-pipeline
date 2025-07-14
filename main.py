#!/usr/bin/env python3
"""
Main orchestrator for the Music ETL Pipeline
Coordinates ingestion from multiple sources (Spotify, YouTube)
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent))

from ingestion.scripts.spotify_ingestion import SpotifyIngestion
from ingestion.scripts.youtube_ingestion import YouTubeIngestion
from infrastructure.logger import Logger

class MusicETLPipeline:
    """Main orchestrator for the Music ETL Pipeline"""
    
    def __init__(self):
        self.logger = Logger("MusicETLPipeline")
        self.spotify_ingestion = None
        self.youtube_ingestion = None
        
    def initialize_services(self):
        """Initialize ingestion services"""
        self.logger.info("Initializing ingestion services...")
        
        try:
            self.spotify_ingestion = SpotifyIngestion()
            self.logger.success("Spotify ingestion service initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Spotify ingestion: {str(e)}")
            self.spotify_ingestion = None
        
        try:
            self.youtube_ingestion = YouTubeIngestion()
            self.logger.success("YouTube ingestion service initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize YouTube ingestion: {str(e)}")
            self.youtube_ingestion = None
        
        if not self.spotify_ingestion and not self.youtube_ingestion:
            raise RuntimeError("Failed to initialize any ingestion services")
    
    def run_spotify_ingestion(self, days_behind=7):
        """Run Spotify data ingestion"""
        if not self.spotify_ingestion:
            self.logger.warning("Spotify ingestion service not available")
            return None
        
        try:
            self.logger.info(f"Starting Spotify ingestion for last {days_behind} days")
            start_time = time.time()
            
            result = self.spotify_ingestion.ingest_spotify_data(days_behind)
            
            elapsed_time = time.time() - start_time
            self.logger.success(f"Spotify ingestion completed in {elapsed_time:.2f} seconds")
            return result
            
        except Exception as e:
            self.logger.error(f"Spotify ingestion failed: {str(e)}")
            return None
    
    def run_youtube_ingestion(self, days_behind=7):
        """Run YouTube data ingestion"""
        if not self.youtube_ingestion:
            self.logger.warning("YouTube ingestion service not available")
            return None
        
        try:
            self.logger.info(f"Starting YouTube ingestion for last {days_behind} days")
            start_time = time.time()
            
            result = self.youtube_ingestion.ingest_youtube_data(days_behind)
            
            elapsed_time = time.time() - start_time
            self.logger.success(f"YouTube ingestion completed in {elapsed_time:.2f} seconds")
            return result
            
        except Exception as e:
            self.logger.error(f"YouTube ingestion failed: {str(e)}")
            return None
    
    def run_all_ingestions(self, days_behind=7, parallel=True):
        """Run all available ingestion services"""
        self.logger.info(f"Starting full ingestion pipeline (parallel={parallel})")
        pipeline_start = time.time()
        
        results = {}
        
        if parallel:
            # Run ingestions in parallel
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {}
                
                if self.spotify_ingestion:
                    futures['spotify'] = executor.submit(self.run_spotify_ingestion, days_behind)
                
                if self.youtube_ingestion:
                    futures['youtube'] = executor.submit(self.run_youtube_ingestion, days_behind)
                
                # Collect results
                for source, future in futures.items():
                    try:
                        results[source] = future.result(timeout=300)  # 5 minute timeout
                    except Exception as e:
                        self.logger.error(f"Failed to complete {source} ingestion: {str(e)}")
                        results[source] = None
        else:
            # Run ingestions sequentially
            if self.spotify_ingestion:
                results['spotify'] = self.run_spotify_ingestion(days_behind)
            
            if self.youtube_ingestion:
                results['youtube'] = self.run_youtube_ingestion(days_behind)
        
        pipeline_elapsed = time.time() - pipeline_start
        
        # Summary
        successful_ingestions = [source for source, result in results.items() if result is not None]
        failed_ingestions = [source for source, result in results.items() if result is None]
        
        self.logger.info(f"Pipeline completed in {pipeline_elapsed:.2f} seconds")
        
        if successful_ingestions:
            self.logger.success(f"Successful ingestions: {', '.join(successful_ingestions)}")
        
        if failed_ingestions:
            self.logger.error(f"Failed ingestions: {', '.join(failed_ingestions)}")
        
        return results
    
    def health_check(self):
        """Check the health of all ingestion services"""
        self.logger.info("Performing health check...")
        
        health_status = {
            'spotify': self.spotify_ingestion is not None,
            'youtube': self.youtube_ingestion is not None,
            'timestamp': datetime.now().isoformat()
        }
        
        for service, status in health_status.items():
            if service != 'timestamp':
                status_msg = "✓ Available" if status else "✗ Unavailable"
                self.logger.info(f"{service.capitalize()} service: {status_msg}")
        
        return health_status

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Music ETL Pipeline - Ingest music data from multiple sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --all                    # Run all ingestions (parallel)
  python main.py --spotify               # Run only Spotify ingestion
  python main.py --youtube               # Run only YouTube ingestion
  python main.py --all --sequential      # Run all ingestions sequentially
  python main.py --all --days-behind 14  # Ingest data from last 14 days
  python main.py --health-check          # Check service health
        """
    )
    
    # Source selection
    parser.add_argument('--all', action='store_true', 
                       help='Run all available ingestion services')
    parser.add_argument('--spotify', action='store_true',
                       help='Run Spotify ingestion only')
    parser.add_argument('--youtube', action='store_true',
                       help='Run YouTube ingestion only')
    
    # Configuration options
    parser.add_argument('--days-behind', type=int, default=7,
                       help='Number of days to look back for data (default: 7)')
    parser.add_argument('--sequential', action='store_true',
                       help='Run ingestions sequentially instead of parallel')
    parser.add_argument('--health-check', action='store_true',
                       help='Check the health of all services')
    
    # Logging options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress non-error output')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.all, args.spotify, args.youtube, args.health_check]):
        parser.error("Must specify at least one action: --all, --spotify, --youtube, or --health-check")
    
    if args.days_behind < 1:
        parser.error("--days-behind must be at least 1")
    
    # Initialize pipeline
    try:
        pipeline = MusicETLPipeline()
        pipeline.initialize_services()
        
        # Handle health check
        if args.health_check:
            health_status = pipeline.health_check()
            print(f"Health check completed at {health_status['timestamp']}")
            return 0
        
        # Run ingestions based on arguments
        if args.all:
            results = pipeline.run_all_ingestions(
                days_behind=args.days_behind,
                parallel=not args.sequential
            )
        elif args.spotify:
            results = {'spotify': pipeline.run_spotify_ingestion(args.days_behind)}
        elif args.youtube:
            results = {'youtube': pipeline.run_youtube_ingestion(args.days_behind)}
        
        # Check if any ingestion was successful
        successful = any(result is not None for result in results.values())
        
        if successful:
            print("✓ Pipeline execution completed successfully")
            return 0
        else:
            print("✗ All ingestion attempts failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
        return 130
    except Exception as e:
        print(f"✗ Pipeline failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())