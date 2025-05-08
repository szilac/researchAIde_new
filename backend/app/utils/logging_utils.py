import logging

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Gets a configured logger instance."""
    logger = logging.getLogger(name)
    # Basic configuration if not already configured by a higher-level setup
    if not logger.hasHandlers(): # Avoid adding multiple handlers
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger 