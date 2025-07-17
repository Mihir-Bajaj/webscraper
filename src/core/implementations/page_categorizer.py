"""
Fast Page Categorizer using URL patterns and keyword matching.

Categorizes pages into:
- Content: Blogs, videos, product pages, advertising materials
- Hubs: Home pages, archives, landing pages, navigation pages  
- Recruitment: Career pages, job listings, company culture
- Interactable: Forms, payment pages, tools, calculators

Uses URL patterns and keyword matching for fast classification.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class CategoryMatch:
    category: str
    confidence: float
    matched_patterns: List[str]
    matched_keywords: List[str]


class PageCategorizer:
    """
    Fast page categorizer using URL patterns and keyword matching.
    """
    
    def __init__(self):
        # URL patterns for each category
        self.url_patterns = {
            'content': [
                r'/blog/', r'/article/', r'/post/', r'/news/', r'/story/',
                r'/video/', r'/podcast/', r'/webinar/', r'/whitepaper/',
                r'/case-study/', r'/success-story/', r'/testimonial/',
                r'/product/', r'/service/', r'/solution/', r'/feature/',
                r'/about/', r'/company/', r'/team/', r'/leadership/',
                r'/press/', r'/media/', r'/resources/', r'/download/',
                r'/guide/', r'/tutorial/', r'/how-to/', r'/tips/',
                r'/industry/', r'/market/', r'/trend/', r'/insight/'
            ],
            'hubs': [
                r'^/$', r'/home', r'/index', r'/main',
                r'/archive', r'/category/', r'/tag/', r'/topic/',
                r'/sitemap', r'/directory', r'/listing', r'/browse/',
                r'/search', r'/results', r'/filter', r'/sort',
                r'/landing', r'/welcome', r'/start', r'/entry'
            ],
            'recruitment': [
                r'/career', r'/job', r'/position', r'/employment',
                r'/work', r'/opportunity', r'/vacancy', r'/opening',
                r'/apply', r'/application', r'/candidate', r'/talent',
                r'/hiring', r'/recruit', r'/join', r'/team-join',
                r'/culture', r'/values', r'/benefits', r'/perks',
                r'/growth', r'/development', r'/training', r'/mentorship'
            ],
            'interactable': [
                r'/contact', r'/reach', r'/get-in-touch', r'/support',
                r'/help', r'/faq', r'/ticket', r'/chat',
                r'/payment', r'/checkout', r'/cart', r'/order',
                r'/signup', r'/register', r'/login', r'/account',
                r'/profile', r'/dashboard', r'/portal', r'/app',
                r'/tool', r'/calculator', r'/form', r'/survey',
                r'/quote', r'/estimate', r'/demo', r'/trial',
                r'/download', r'/subscribe', r'/newsletter', r'/opt-in'
            ]
        }
        
        # Keywords for each category (case-insensitive)
        self.keywords = {
            'content': [
                'blog', 'article', 'post', 'news', 'story', 'video', 'podcast',
                'webinar', 'whitepaper', 'case study', 'success story', 'testimonial',
                'product', 'service', 'solution', 'feature', 'about', 'company',
                'team', 'leadership', 'press', 'media', 'resources', 'download',
                'guide', 'tutorial', 'how to', 'tips', 'industry', 'market',
                'trend', 'insight', 'content', 'information', 'learn', 'discover'
            ],
            'hubs': [
                'home', 'main', 'index', 'archive', 'category', 'tag', 'topic',
                'sitemap', 'directory', 'listing', 'browse', 'search', 'results',
                'filter', 'sort', 'landing', 'welcome', 'start', 'entry',
                'navigation', 'menu', 'hub', 'center', 'portal'
            ],
            'recruitment': [
                'career', 'job', 'position', 'employment', 'work', 'opportunity',
                'vacancy', 'opening', 'apply', 'application', 'candidate', 'talent',
                'hiring', 'recruit', 'join', 'team', 'culture', 'values',
                'benefits', 'perks', 'growth', 'development', 'training',
                'mentorship', 'employee', 'staff', 'hire', 'recruitment'
            ],
            'interactable': [
                'contact', 'reach', 'get in touch', 'support', 'help', 'faq',
                'ticket', 'chat', 'payment', 'checkout', 'cart', 'order',
                'signup', 'register', 'login', 'account', 'profile', 'dashboard',
                'portal', 'app', 'tool', 'calculator', 'form', 'survey',
                'quote', 'estimate', 'demo', 'trial', 'download', 'subscribe',
                'newsletter', 'opt in', 'submit', 'send', 'request'
            ]
        }
        
        # Compile regex patterns for performance
        self.compiled_patterns = {}
        for category, patterns in self.url_patterns.items():
            self.compiled_patterns[category] = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    def categorize_page(self, url: str, title: str = "", markdown: str = "") -> CategoryMatch:
        """
        Categorize a page based on URL, title, and markdown content.
        
        Args:
            url: Page URL
            title: Page title
            markdown: Page markdown content
            
        Returns:
            CategoryMatch with category, confidence, and matched patterns
        """
        url_matches = self._match_url_patterns(url)
        keyword_matches = self._match_keywords(title, markdown)
        
        # Combine URL and keyword matches
        all_matches = {}
        for category in ['content', 'hubs', 'recruitment', 'interactable']:
            url_score = url_matches.get(category, 0)
            keyword_score = keyword_matches.get(category, 0)
            
            # Weight URL patterns more heavily than keywords
            combined_score = (url_score * 0.7) + (keyword_score * 0.3)
            all_matches[category] = combined_score
        
        # Find the best match
        if not all_matches:
            return CategoryMatch('content', 0.1, [], [])  # Default fallback
        
        best_category = max(all_matches, key=all_matches.get)
        confidence = min(all_matches[best_category], 1.0)
        
        # Get matched patterns for debugging
        matched_patterns = []
        matched_keywords = []
        
        if url_matches.get(best_category, 0) > 0:
            matched_patterns = self._get_matched_url_patterns(url, best_category)
        
        if keyword_matches.get(best_category, 0) > 0:
            matched_keywords = self._get_matched_keywords(title, markdown, best_category)
        
        return CategoryMatch(
            category=best_category,
            confidence=confidence,
            matched_patterns=matched_patterns,
            matched_keywords=matched_keywords
        )
    
    def _match_url_patterns(self, url: str) -> Dict[str, float]:
        """Match URL against patterns for each category."""
        matches = {}
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        for category, patterns in self.compiled_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(path):
                    score += 1
            
            # Normalize score (0-1 range)
            if patterns:
                matches[category] = min(score / len(patterns), 1.0)
            else:
                matches[category] = 0
        
        return matches
    
    def _match_keywords(self, title: str, markdown: str) -> Dict[str, float]:
        """Match keywords in title and markdown for each category."""
        matches = {}
        text = f"{title} {markdown}".lower()
        
        for category, keywords in self.keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text:
                    score += 1
            
            # Normalize score (0-1 range)
            if keywords:
                matches[category] = min(score / len(keywords), 1.0)
            else:
                matches[category] = 0
        
        return matches
    
    def _get_matched_url_patterns(self, url: str, category: str) -> List[str]:
        """Get list of matched URL patterns for debugging."""
        matched = []
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        for pattern in self.compiled_patterns[category]:
            if pattern.search(path):
                matched.append(pattern.pattern)
        
        return matched
    
    def _get_matched_keywords(self, title: str, markdown: str, category: str) -> List[str]:
        """Get list of matched keywords for debugging."""
        matched = []
        text = f"{title} {markdown}".lower()
        
        for keyword in self.keywords[category]:
            if keyword.lower() in text:
                matched.append(keyword)
        
        return matched
    
    def get_category_description(self, category: str) -> str:
        """Get human-readable description of a category."""
        descriptions = {
            'content': 'Informational/entertainment pages (blogs, videos, product info)',
            'hubs': 'Navigation/aggregation pages (home, archives, category pages)',
            'recruitment': 'Career/job-related pages',
            'interactable': 'User input pages (forms, tools, payments)'
        }
        return descriptions.get(category, 'Unknown category') 