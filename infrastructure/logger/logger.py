import logging

class Logger:
    """Custom logger for Music ETL pipeline"""
    def __init__(self, name="music-etl-pipeline", level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Clear existing handlers to avoid duplicates
        # self.logger.handlers.clear()
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        if not self.logger.hasHandlers():
            self.logger.addHandler(console_handler)

        
        

    def info(self, message):
        self.logger.info(f"{message}")
    
    def error(self, message):
        self.logger.error(f"❌ {message}")
    
    def warning(self, message):
        self.logger.warning(f"⚠️ {message}")
    
    def success(self, message):
        self.logger.info(f"✅ {message}")
    
    def debug(self, message):
        self.logger.debug(f"🔧 {message}")

    def critical(self, message):
        self.logger.critical(f"💀 {message}")                       


# Create default logger instance
spotify_logger = Logger()