import re
import aiohttp
import asyncio
from typing import Dict, List, Optional, Tuple, Union

from aiohttp import BasicAuth
from src.config.config import config
from src.models.models import SearchResult, KeywordAnalysisResult, ProductDetails
from src.services.proxy_service import AbstractProxyService, PiaProxyService


class WildberriesService:
    """Service for interacting with Wildberries API"""
    
    def __init__(self, proxy_service: AbstractProxyService = None):
        self.region = config.WB_REGION
        self.use_proxy = config.WB_USE_PROXY
        self.max_search_pages = config.MAX_SEARCH_PAGES
        self.proxy_service = proxy_service if proxy_service else PiaProxyService()
    
    def extract_article_id(self, url: str) -> Optional[int]:
        """Extract article ID from Wildberries URL"""
        match = re.search(r'wildberries\.ru/catalog/(\d+)/detail\.aspx', url)
        if match:
            return int(match.group(1))
        return None
    
    def get_card_url(self, article_id: int) -> str:
        """Generate URL for product card data"""
        vol = str(article_id // 100000)
        part = str(article_id // 1000)
        basket_number = self._resolve_basket_id(article_id)
        return f"https://basket-{basket_number}.wbbasket.ru/vol{vol}/part{part}/{article_id}/info/{self.region}/card.json"
    
    def get_detail_url(self, article_id: int) -> str:
        """Generate URL for detailed product data"""
        return f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-363095&hide_dtype=13&lang=ru&spp=30&nm={article_id}"
    
    def _resolve_basket_id(self, nmid: int) -> str:
        """Calculate basket ID for a product"""
        s = nmid // 100000
        
        if s <= 143: return "01"
        elif s <= 287: return "02"
        elif s <= 431: return "03"
        elif s <= 719: return "04"
        elif s <= 1007: return "05"
        elif s <= 1061: return "06"
        elif s <= 1115: return "07"
        elif s <= 1169: return "08"
        elif s <= 1313: return "09"
        elif s <= 1601: return "10"
        elif s <= 1655: return "11"
        elif s <= 1919: return "12"
        elif s <= 2045: return "13"
        elif s <= 2189: return "14"
        elif s <= 2405: return "15"
        elif s <= 2621: return "16"
        elif s <= 2837: return "17"
        elif s <= 3053: return "18"
        elif s <= 3269: return "19"
        elif s <= 3485: return "20"
        elif s <= 3701: return "21"
        elif s <= 3917: return "22"
        elif s <= 4133: return "23"
        elif s <= 4349: return "24"
        elif s <= 4565: return "25"
        else: return "26"
    
    def get_image_url(self, article_id: int) -> str:
        """Generate URL for product image"""
        vol = str(article_id // 100000)
        part = str(article_id // 1000)
        basket_number = self._resolve_basket_id(article_id)
        return f"https://basket-{basket_number}.wbbasket.ru/vol{vol}/part{part}/{article_id}/images/c516x688/1.webp"
    
    def get_search_url(self, query: str, page: int = 1) -> str:
        """Generate URL for search request"""
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        
        return (f"https://search.wb.ru/exactmatch/{self.region}/common/v9/search"
                f"?ab_testing=false&appType=1&curr=rub&dest=-363095&hide_dtype=13"
                f"&lang={self.region}&page={page}&query={encoded_query}"
                f"&resultset=catalog&sort=popular&spp=30&suppressSpellcheck=false")
    
    async def _make_request(self, url: str, user_id: int) -> Optional[Dict]:
        """Make HTTP request with proxy if enabled"""
        proxy = self.proxy_service.get_proxy(user_id) if self.use_proxy else None
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    proxy=proxy["url"] if proxy else None,
                    proxy_auth=proxy["auth"] if proxy and "auth" in proxy else None,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        try:
                            # First try normal json parsing
                            return await response.json()
                        except aiohttp.ContentTypeError:
                            # If content type error, get text and parse manually
                            text = await response.text()
                            import json
                            try:
                                return json.loads(text)
                            except json.JSONDecodeError as e:
                                print(f"JSON decode error: {str(e)} for url: {url}")
                                return None
                    else:
                        print(f"Error fetching {url}: {response.status}")
                        return None
        except Exception as e:
            print(f"Request error for {url}: {str(e)}")
            return None
    
    async def get_product_data(self, product_url: str, user_id: int) -> Optional[Dict]:
        article_id = self.extract_article_id(product_url)
        if not article_id:
            return None
        
        card_url = self.get_card_url(article_id)
        return await self._make_request(card_url, user_id)
    
    async def get_product_details(self, product_url: str, user_id: int) -> Optional[ProductDetails]:
        """Get detailed product information"""
        article_id = self.extract_article_id(product_url)
        if not article_id:
            return None
        
        detail_url = self.get_detail_url(article_id)
        detail_data = await self._make_request(detail_url, user_id)
        
        if not detail_data or 'data' not in detail_data or 'products' not in detail_data['data'] or not detail_data['data']['products']:
            return None
        
        product = detail_data['data']['products'][0]
        
        price = 0
        if 'sizes' in product and product['sizes'] and 'price' in product['sizes'][0]:
            price_data = product['sizes'][0]['price']
            price = price_data.get('product', 0) / 100
        
        return ProductDetails(
            id=product.get('id', article_id),
            name=product.get('name', f"Товар {article_id}"),
            brand=product.get('brand', ""),
            price=price,
            rating=product.get('reviewRating', 0),
            feedbacks=product.get('feedbacks', 0),
            image_url=self.get_image_url(article_id),
            url=product_url
        )
    
    async def find_product_position(self, query: str, product_id: int, user_id: int) -> int:
        current_position = 0
        
        for page in range(1, self.max_search_pages + 1):
            search_url = self.get_search_url(query, page)
            search_results = await self._make_request(search_url, user_id)
            
            if not search_results or 'data' not in search_results or 'products' not in search_results['data']:
                break
            
            products = search_results['data']['products']
            
            for product in products:
                current_position += 1
                if product['id'] == product_id:
                    return current_position
            
            if not products:
                break
            
            await asyncio.sleep(0.5)
        
        return -1
    
    async def analyze_product_keywords(self, product_url: str, keywords: List[str], user_id: int) -> KeywordAnalysisResult:
        """Analyze product position for each keyword"""
        article_id = self.extract_article_id(product_url)
        if not article_id:
            # Create a default product details if article ID can't be extracted
            product_details = ProductDetails(
                id=0,
                name="Товар не найден",
                brand="",
                price=0,
                rating=0,
                feedbacks=0,
                image_url="",
                url=product_url
            )
            return KeywordAnalysisResult(
                product=product_details,
                found_keywords=[],
                search_results=[]
            )
        
        # Get detailed product information
        product_details = await self.get_product_details(product_url, user_id)
        if not product_details:
            # Fallback to basic product details if API fails
            product_details = ProductDetails(
                id=article_id,
                name=f"Товар {article_id}",
                brand="",
                price=0,
                rating=0,
                feedbacks=0,
                image_url=self.get_image_url(article_id),
                url=product_url
            )
        
        # Find position for each keyword
        search_results = []
        for keyword in keywords:
            position = await self.find_product_position(keyword, article_id, user_id)
            
            # If position is -1 (not found), set to None to indicate "below limit"
            result = SearchResult(
                keyword=keyword,
                product_position=position if position > 0 else None
            )
            search_results.append(result)
            
            await asyncio.sleep(0.3)
        
        return KeywordAnalysisResult(
            product=product_details,
            found_keywords=keywords,
            search_results=search_results
        )
