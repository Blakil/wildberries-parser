import json
import abc
import aiohttp
from typing import List, Optional, Dict, Any

from src.config.config import config
from src.services.proxy_service import AbstractProxyService, PiaProxyService


class AbstractLLMService(abc.ABC):
    """Abstract base class for LLM services"""
    
    def __init__(self, proxy_service: AbstractProxyService = None):
        """Initialize the LLM service with optional proxy service"""
        self.proxy_service = proxy_service if proxy_service else PiaProxyService()
        self.keywords_count = config.SEARCH_KEYWORDS_COUNT
    
    @abc.abstractmethod
    async def _make_request(self, payload: dict, user_id: int) -> Optional[dict]:
        """Make an API request to the LLM provider"""
        pass
    
    @abc.abstractmethod
    async def _prepare_prompt_payload(self, product_json: dict) -> dict:
        """Prepare the prompt payload specific to each LLM provider"""
        pass
    
    @abc.abstractmethod
    async def _parse_response(self, response: dict) -> List[str]:
        """Parse the response from the LLM provider"""
        pass
    
    async def extract_keywords(self, product_json: dict, user_id: int) -> List[str]:
        """Extract keywords from product data using LLM"""
        try:
            # Prepare provider-specific payload
            payload = await self._prepare_prompt_payload(product_json)
            
            # Make request to LLM provider
            response = await self._make_request(payload, user_id)
            
            if not response:
                return ["Ошибка получения ключевых слов"]
            
            # Parse response using provider-specific parser
            return await self._parse_response(response)
        except Exception as e:
            print(f"Error extracting keywords: {str(e)}")
            return ["Ошибка обработки ключевых слов"]


class OpenRouterLLMService(AbstractLLMService):
    """OpenRouter implementation of the LLM service"""
    
    def __init__(self, proxy_service: AbstractProxyService = None):
        super().__init__(proxy_service)
        self.api_key = config.OPENROUTER_API_KEY
        self.model = config.OPENROUTER_MODEL
        self.use_proxy = config.OPENROUTER_USE_PROXY
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    async def _make_request(self, payload: dict, user_id: int) -> Optional[dict]:
        """Make an API request to OpenRouter"""
        
        # Get proxy settings if enabled    
        proxy = self.proxy_service.get_proxy(user_id) if self.use_proxy else None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    proxy=proxy["url"] if proxy else None,
                    proxy_auth=proxy["auth"] if proxy and "auth" in proxy else None,
                    timeout=15
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"OpenRouter API error: {str(e)}")
            return None
    
    async def _prepare_prompt_payload(self, product_json: dict) -> dict:
        """Prepare the prompt payload for OpenRouter"""
        system_prompt = f"""
        You are a product analyst that helps extract search keywords from product data.
        Analyze the product data and identify the {self.keywords_count} most relevant search keywords
        that potential customers might use to find this product.
        
        Rules:
        1. Return exactly {self.keywords_count} keywords
        2. Keywords should be specific and relevant to the product
        3. Include both generic and specific terms
        4. Consider product name, description, and characteristics
        5. Return ONLY a JSON array of strings, with no explanations
        """
        
        # Prepare the product data as a string for the prompt
        product_data = json.dumps(product_json, ensure_ascii=False)
        
        user_prompt = f"""
        Here is the product data:
        
        {product_data}
        
        Extract the {self.keywords_count} most relevant search keywords for this product.
        Return ONLY a JSON array of strings, with no explanation.
        """
        
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
    
    async def _parse_response(self, response: dict) -> List[str]:
        """Parse the response from OpenRouter"""
        try:
            # Extract the response content
            content = response["choices"][0]["message"]["content"]
            
            # Parse the JSON array
            keywords = json.loads(content)
            
            # Ensure we have the right format and count
            if isinstance(keywords, list) and len(keywords) > 0:
                return keywords[:self.keywords_count]
            else:
                return ["Ошибка формата ключевых слов"]
        except Exception as e:
            print(f"Error parsing OpenRouter response: {str(e)}")
            return ["Ошибка обработки ключевых слов"]


class DeepSeekLLMService(AbstractLLMService):
    """DeepSeek implementation of the LLM service"""
    
    def __init__(self, proxy_service: AbstractProxyService = None):
        super().__init__(proxy_service)
        self.api_key = config.DEEPSEEK_API_KEY
        self.model = config.DEEPSEEK_MODEL
        self.use_proxy = config.DEEPSEEK_USE_PROXY
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
    
    async def _make_request(self, payload: dict, user_id: int) -> Optional[dict]:
        """Make an API request to DeepSeek"""
        
        # Get proxy settings if enabled
        proxy = self.proxy_service.get_proxy(user_id) if self.use_proxy else None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    proxy=proxy["url"] if proxy else None,
                    proxy_auth=proxy["auth"] if proxy and "auth" in proxy else None,
                    timeout=15
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"DeepSeek API error: {str(e)}")
            return None
    
    async def _prepare_prompt_payload(self, product_json: dict) -> dict:
        """Prepare the prompt payload for DeepSeek"""
        system_prompt = f"""
        You are a product analyst that helps extract search keywords from product data.
        Analyze the product data and identify the {self.keywords_count} most relevant search keywords
        that potential customers might use to find this product.
        
        Rules:
        1. Return exactly {self.keywords_count} keywords
        2. Keywords should be specific and relevant to the product
        3. Include both generic and specific terms
        4. Consider product name, description, and characteristics
        5. Return ONLY a JSON array of strings, with no explanations
        """
        
        # Prepare the product data as a string for the prompt
        product_data = json.dumps(product_json, ensure_ascii=False)
        
        user_prompt = f"""
        Here is the product data:
        
        {product_data}
        
        Extract the {self.keywords_count} most relevant search keywords for this product.
        Return ONLY a JSON array of strings, with no explanation.
        """
        
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
    
    async def _parse_response(self, response: dict) -> List[str]:
        """Parse the response from DeepSeek"""
        try:
            # Extract the response content (DeepSeek uses a similar format to OpenAI)
            content = response["choices"][0]["message"]["content"]
            
            # Parse the JSON array
            keywords = json.loads(content)
            
            # Ensure we have the right format and count
            if isinstance(keywords, list) and len(keywords) > 0:
                return keywords[:self.keywords_count]
            else:
                return ["Ошибка формата ключевых слов"]
        except Exception as e:
            print(f"Error parsing DeepSeek response: {str(e)}")
            return ["Ошибка обработки ключевых слов"]


def create_llm_service(proxy_service: AbstractProxyService = None) -> AbstractLLMService:
    """Create the appropriate LLM service based on configuration"""
    provider = config.LLM_PROVIDER.lower()
    
    if provider == "openrouter":
        return OpenRouterLLMService(proxy_service)
    elif provider == "deepseek":
        return DeepSeekLLMService(proxy_service)
    else:
        # Default to OpenRouter if the provider is not recognized
        print(f"Unknown LLM provider: {provider}. Using OpenRouter as default.")
        return OpenRouterLLMService(proxy_service)

LLMService = create_llm_service
