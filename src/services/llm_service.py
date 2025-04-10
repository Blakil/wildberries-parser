import asyncio
import json
import abc
import aiohttp
import logging
from typing import List, Optional, Dict, Any

from src.config.config import config
from src.services.proxy_service import AbstractProxyService, PiaProxyService
from src.utils.retry import async_retry

# Set up logging
logger = logging.getLogger(__name__)


class AbstractLLMService(abc.ABC):
    """Abstract base class for LLM services"""
    
    def __init__(self, proxy_service: AbstractProxyService = None):
        """Initialize the LLM service with optional proxy service"""
        self.proxy_service = proxy_service if proxy_service else PiaProxyService()
        self.keywords_count = config.SEARCH_KEYWORDS_COUNT
    
    @abc.abstractmethod
    async def _make_request_implementation(self, payload: dict, user_id: int) -> Optional[dict]:
        """Implementation of the API request to the LLM provider"""
        pass
    
    async def _make_request(self, payload: dict, user_id: int) -> Optional[dict]:
        """Make an API request to the LLM provider with retry mechanism"""
        return await self._make_request_with_retry(payload, user_id)
    
    async def _make_request_with_retry(self, payload: dict, user_id: int) -> Optional[dict]:
        """Make an API request to LLM provider with retry mechanism applied"""
        logger.info(f"Making LLM API request")
        return await self._make_request_implementation(payload, user_id)
    
    @abc.abstractmethod
    async def _prepare_prompt_payload(self, product_json: dict) -> dict:
        """Prepare the prompt payload specific to each LLM provider"""
        pass
    
    @abc.abstractmethod
    async def _parse_response(self, response: dict) -> List[str]:
        """Parse the response from the LLM provider"""
        pass
    
    @async_retry(
        max_retries=config.LLM_MAX_RETRIES,
        initial_backoff=config.LLM_INITIAL_BACKOFF,
        max_backoff=config.LLM_MAX_BACKOFF,
        backoff_factor=config.LLM_BACKOFF_FACTOR,
        jitter=True,
        retryable_exceptions=(
            aiohttp.ClientError,
            asyncio.TimeoutError,
            Exception
        )
    )
    async def extract_keywords(self, product_json: dict, user_id: int) -> List[str]:
        """Extract keywords from product data using LLM"""
        try:
            # Prepare provider-specific payload
            payload = await self._prepare_prompt_payload(product_json)
            
            # Make request to LLM provider
            response = await self._make_request(payload, user_id)
            
            if not response:
                logger.error("Received empty response from LLM API")
                raise Exception("Empty response from LLM API")
            
            # Log the raw response for debugging
            logger.info(f"Raw LLM response: {json.dumps(response, ensure_ascii=False, indent=2)}")
            
            # Parse response using provider-specific parser
            try:
                return await self._parse_response(response)
            except Exception as e:
                # Log the error with the full response as string for debugging
                logger.error(f"Error parsing response: {str(e)}", exc_info=True)
                logger.error(f"Response as string: {str(response)}")
                raise Exception(f"Error parsing LLM response: {str(e)}")
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}", exc_info=True)
            raise


class OpenRouterLLMService(AbstractLLMService):
    """OpenRouter implementation of the LLM service"""
    
    def __init__(self, proxy_service: AbstractProxyService = None):
        super().__init__(proxy_service)
        self.api_key = config.OPENROUTER_API_KEY
        self.model = config.OPENROUTER_MODEL
        self.use_proxy = config.OPENROUTER_USE_PROXY
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    async def _make_request_implementation(self, payload: dict, user_id: int) -> Optional[dict]:
        """Implementation for making an API request to OpenRouter"""
        
        # Get proxy settings if enabled    
        proxy = self.proxy_service.get_proxy(user_id) if self.use_proxy else None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Making OpenRouter API request with model: {self.model}")
        
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
                    response_data = await response.json()
                    logger.info("OpenRouter API request successful")
                    return response_data
                else:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API error: {response.status} - {error_text}")
                    raise Exception(f"API error: {response.status} - {error_text}")
    
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
                logger.info(f"Successfully parsed {len(keywords)} keywords")
                return keywords[:self.keywords_count]
            else:
                logger.error("Invalid keywords format - not a list or empty list")
                raise Exception("Invalid keywords format - not a list or empty list")
        except KeyError as e:
            logger.error(f"Key error in response structure: {e}, Response keys: {list(response.keys()) if response else 'None'}")
            raise Exception(f"Key error in response structure: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}, Content: {content if 'content' in locals() else 'None'}")
            raise Exception(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Error parsing OpenRouter response: {str(e)}, response: "+str(response))
            raise


class DeepSeekLLMService(AbstractLLMService):
    """DeepSeek implementation of the LLM service"""
    
    def __init__(self, proxy_service: AbstractProxyService = None):
        super().__init__(proxy_service)
        self.api_key = config.DEEPSEEK_API_KEY
        self.model = config.DEEPSEEK_MODEL
        self.use_proxy = config.DEEPSEEK_USE_PROXY
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
    
    async def _make_request_implementation(self, payload: dict, user_id: int) -> Optional[dict]:
        """Implementation for making an API request to DeepSeek"""
        
        # Get proxy settings if enabled
        proxy = self.proxy_service.get_proxy(user_id) if self.use_proxy else None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Making DeepSeek API request with model: {self.model}")
        
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
                    response_data = await response.json()
                    logger.info("DeepSeek API request successful")
                    return response_data
                else:
                    error_text = await response.text()
                    logger.error(f"DeepSeek API error: {response.status} - {error_text}")
                    raise Exception(f"API error: {response.status} - {error_text}")
    
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
                logger.info(f"Successfully parsed {len(keywords)} keywords")
                return keywords[:self.keywords_count]
            else:
                logger.error("Invalid keywords format - not a list or empty list")
                raise Exception("Invalid keywords format - not a list or empty list")
        except KeyError as e:
            logger.error(f"Key error in response structure: {e}, Response keys: {list(response.keys()) if response else 'None'}")
            raise Exception(f"Key error in response structure: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}, Content: {content if 'content' in locals() else 'None'}")
            raise Exception(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Error parsing DeepSeek response: {str(e)}, response: "+str(response))
            raise


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
