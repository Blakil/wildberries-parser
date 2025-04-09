from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SearchResult:
    """Class for storing search results for a specific keyword"""
    keyword: str
    product_position: Optional[int]  # Position in search results, None if not found
    
    
@dataclass
class ProductDetails:
    """Class for storing detailed product information"""
    id: int
    name: str
    brand: str
    price: float
    rating: float
    feedbacks: int
    image_url: str
    url: str
    

@dataclass
class KeywordAnalysisResult:
    """Class for storing the complete keyword analysis for a product"""
    product: ProductDetails
    found_keywords: List[str]  # Keywords extracted from the product
    search_results: List[SearchResult]  # Results of searching each keyword
