#!/usr/bin/env python3
"""
Domain-specific content extractors for problematic sites
Uses APIs and specialized methods for better extraction
"""

import requests
import logging
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class DomainSpecificExtractors:
    """Specialized extractors for specific domains"""
    
    @staticmethod
    def extract_leetcode_content(url: str) -> Optional[str]:
        """Extract content from LeetCode discussion/problem pages"""
        try:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            content_parts = []
            
            # LeetCode discussion URLs: /discuss/interview-question/... or /discuss/study-guide/...
            if '/discuss/' in path:
                # Extract discussion type and topic
                parts = path.split('/')
                discussion_type = None
                topic_parts = []
                
                for i, part in enumerate(parts):
                    if part == 'discuss' and i + 1 < len(parts):
                        discussion_type = parts[i + 1].replace('-', ' ').title()
                    elif part not in ['discuss', 'interview-question', 'study-guide', 'general', '']:
                        topic_parts.append(part.replace('-', ' ').replace('_', ' '))
                
                if discussion_type:
                    content_parts.append(f"LeetCode {discussion_type}")
                if topic_parts:
                    content_parts.append(f"Topic: {' '.join(topic_parts[:5])}")
                
                if content_parts:
                    return '. '.join(content_parts)
            
            # Problem URLs: /problems/problem-name
            elif '/problems/' in path:
                problem_slug = path.split('/problems/')[-1].split('/')[0]
                problem_name = problem_slug.replace('-', ' ').title()
                return f"LeetCode Problem: {problem_name}"
            
            # Contest URLs: /contest/contest-name
            elif '/contest/' in path:
                contest_slug = path.split('/contest/')[-1].split('/')[0]
                contest_name = contest_slug.replace('-', ' ').title()
                return f"LeetCode Contest: {contest_name}"
            
            return None
        except Exception as e:
            logger.debug(f"LeetCode extraction failed: {e}")
            return None
    
    @staticmethod
    def extract_medium_content(url: str) -> Optional[str]:
        """Extract content from Medium articles"""
        try:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            parts = [p for p in path.split('/') if p]
            
            # Medium URLs: /@username/article-slug or /username/article-slug
            if len(parts) >= 2:
                article_slug = parts[-1]
                article_title = article_slug.replace('-', ' ').title()
                return f"Medium Article: {article_title}"
            
            return None
        except Exception as e:
            logger.debug(f"Medium extraction failed: {e}")
            return None
    
    @staticmethod
    def extract_codeforces_content(url: str) -> Optional[str]:
        """Extract content from Codeforces"""
        try:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            
            # Codeforces problem URLs: /problemset/problem/CONTEST/PROBLEM
            if '/problemset/problem/' in path:
                parts = path.split('/problemset/problem/')[-1].split('/')
                if len(parts) >= 2:
                    return f"Codeforces Problem: Contest {parts[0]}, Problem {parts[1]}"
            
            # Blog URLs: /blog/entry/ENTRY_ID
            elif '/blog/entry/' in path:
                entry_id = path.split('/blog/entry/')[-1].split('/')[0]
                return f"Codeforces Blog Entry: {entry_id}"
            
            return None
        except Exception as e:
            logger.debug(f"Codeforces extraction failed: {e}")
            return None
    
    @staticmethod
    def extract_google_search_content(url: str) -> Optional[str]:
        """Extract search query from Google search URLs"""
        try:
            parsed = urlparse(url)
            if 'search' in parsed.path:
                # Extract query parameter
                from urllib.parse import parse_qs
                query_params = parse_qs(parsed.query)
                query = query_params.get('q', [''])[0]
                if query:
                    return f"Google Search: {query.replace('+', ' ')}"
            return None
        except Exception as e:
            logger.debug(f"Google search extraction failed: {e}")
            return None
    
    @staticmethod
    def extract_render_dashboard_content(url: str) -> Optional[str]:
        """Extract info from Render dashboard URLs"""
        try:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            parts = [p for p in path.split('/') if p]
            
            if 'deploys' in parts or 'services' in parts:
                service_type = 'Deployment' if 'deploys' in parts else 'Service'
                return f"Render Dashboard: {service_type} management page"
            
            return None
        except Exception as e:
            logger.debug(f"Render extraction failed: {e}")
            return None
    
    @staticmethod
    def extract_vercel_content(url: str) -> Optional[str]:
        """Extract content from Vercel-hosted sites"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            path = parsed.path.strip('/')
            
            # For Vercel sites, try to get meaningful content from path
            if path:
                parts = [p.replace('-', ' ').replace('_', ' ') for p in path.split('/') if p]
                if parts:
                    return f"Content from {domain}: {' '.join(parts[:3])}"
            
            return f"Content from {domain}"
        except Exception as e:
            logger.debug(f"Vercel extraction failed: {e}")
            return None
    
    @staticmethod
    def extract_domain_specific_content(url: str) -> Optional[str]:
        """Route to appropriate domain-specific extractor"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        
        if 'leetcode.com' in domain:
            return DomainSpecificExtractors.extract_leetcode_content(url)
        elif 'medium.com' in domain or 'neetishop.medium.com' in domain:
            return DomainSpecificExtractors.extract_medium_content(url)
        elif 'codeforces.com' in domain:
            return DomainSpecificExtractors.extract_codeforces_content(url)
        elif 'google.com' in domain and 'search' in parsed.path:
            return DomainSpecificExtractors.extract_google_search_content(url)
        elif 'render.com' in domain or 'dashboard.render.com' in domain:
            return DomainSpecificExtractors.extract_render_dashboard_content(url)
        elif 'vercel.app' in domain or 'vercel.com' in domain:
            return DomainSpecificExtractors.extract_vercel_content(url)
        
        return None

