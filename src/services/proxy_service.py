import time
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple, Union
from src.config.config import config
import hashlib
from aiohttp import BasicAuth


class AbstractProxyService(ABC):
    """Abstract base class for proxy services"""
    
    def __init__(self):
        self.enabled = config.PROXY_ENABLED
        self.timeout_minutes = config.PROXY_TIMEOUT_MINUTES
    
    
    @abstractmethod
    def get_proxy(self, user_id: int) -> Optional[Dict[str, Union[str, BasicAuth]]]:
        """Get proxy configuration for HTTP requests"""
        pass


class PiaProxyService(AbstractProxyService):
    """Service for managing PIA Proxies based on configuration"""
    
    def __init__(self):
        super().__init__()
        self.proxy_base_host = config.PIA_BASE_HOST
        self.proxy_port = config.PIA_PORT
        self.proxy_check_endpoint = "ipinfo.piaproxy.pro"
        
    def get_proxy_hash(self, user_id: int) -> str:
        timestamp = time.time()
        normalized_time = int(timestamp / (60 * self.timeout_minutes))

        hash_components = f"{user_id}_{normalized_time}"
        return hash_components
    
    def generate_session_id(self, user_id: int) -> str:
        """
        Generate a unique session ID for PIA proxy
        
        Args:
            user_id: User ID to generate a session for
            
        Returns:
            Session ID string
        """
        hash_input = self.get_proxy_hash(user_id)
        hash_object = hashlib.md5(hash_input.encode())
        hash_hex = hash_object.hexdigest()
        return hash_hex[:11]
    
    def get_proxy(self, user_id: int) -> Optional[Dict[str, Union[str, BasicAuth]]]:

        if not self.enabled:
            return None
            
        # Get credentials from config
        username = config.PIA_USERNAME
        password = config.PIA_PASSWORD
        
        if not username or not password:
            return None
            
        session_id = self.generate_session_id(user_id)
        proxy_username = f"{username}-region-ru-sessid-{session_id}-sesstime-10080"
        
        # Create a BasicAuth object for aiohttp
        auth = BasicAuth(login=proxy_username, password=password)
        
        return {
            "url": f"http://{self.proxy_base_host}:{self.proxy_port}",
            "auth": auth
        }
