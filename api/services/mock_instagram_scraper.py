from typing import Dict, Any, Optional
import asyncio
import json
import re

from api.log_service import LogService

class MockInstagramScraperService:
    """Mock implementation of Instagram scraper for testing purposes"""
    
    def __init__(self, log_service: LogService = None):
        """Initialize the mock Instagram scraper service"""
        self.log_service = log_service or LogService()
        
        # Mock data for different Instagram profiles
        self.mock_data = {
            "nike": {
                "username": "nike",
                "name": "Nike",
                "bio": "Move to Zero. Just Do It.",
                "followers": "295M",
                "followers_count": 295000000,
                "following": "248",
                "following_count": 248,
                "posts": "1,024",
                "posts_count": 1024,
                "website": "nike.com",
                "email": None,
                "business_category": "Sporting Goods & Equipment",
                "location": None
            },
            "apple": {
                "username": "apple",
                "name": "Apple",
                "bio": "Everyone has a story to tell.",
                "followers": "28.9M",
                "followers_count": 28900000,
                "following": "0",
                "following_count": 0,
                "posts": "1,256",
                "posts_count": 1256,
                "website": "apple.com",
                "email": None,
                "business_category": "Electronics & Technology",
                "location": "Cupertino, CA"
            },
            "microsoft": {
                "username": "microsoft",
                "name": "Microsoft",
                "bio": "Empower every person and organization on the planet to achieve more.",
                "followers": "4.2M",
                "followers_count": 4200000,
                "following": "185",
                "following_count": 185,
                "posts": "1,532",
                "posts_count": 1532,
                "website": "microsoft.com",
                "email": None,
                "business_category": "Software & Technology",
                "location": "Redmond, WA"
            }
        }
    
    async def scrape_profile(self, instagram_url: str) -> Dict[str, Any]:
        """Mock scraping of an Instagram profile"""
        try:
            self.log_service.log_debug("Starting mock Instagram profile scraping", {"url": instagram_url})
            
            # Extract username from URL
            username = self._extract_username_from_url(instagram_url)
            if not username:
                self.log_service.log_debug("Invalid Instagram URL format", {"url": instagram_url})
                return {"error": "Invalid Instagram URL format"}
            
            # Simulate API delay
            await asyncio.sleep(0.5)
            
            # Get mock data for the username
            if username.lower() in self.mock_data:
                profile_data = self.mock_data[username.lower()]
                self.log_service.log_debug("Instagram profile data extracted from mock", {"username": username})
                return {"data": profile_data}
            else:
                # Return a generic profile for unknown usernames
                self.log_service.log_debug("Unknown Instagram profile, returning generic data", {"username": username})
                return {
                    "data": {
                        "username": username,
                        "name": f"{username.capitalize()} Account",
                        "bio": "This is a generic profile for testing purposes.",
                        "followers": "10K",
                        "followers_count": 10000,
                        "following": "100",
                        "following_count": 100,
                        "posts": "50",
                        "posts_count": 50,
                        "website": f"https://{username}.com",
                        "email": None,
                        "business_category": None,
                        "location": None
                    }
                }
                
        except Exception as e:
            self.log_service.log_error(f"Error in mock Instagram scraper: {str(e)}")
            return {"error": str(e)}
    
    def _extract_username_from_url(self, url: str) -> Optional[str]:
        """Extract username from Instagram URL or direct username input"""
        if not url:
            return None
            
        # If input is just a username without URL or @ symbol
        if re.match(r'^[\w\.]+$', url):
            return url
            
        # Common Instagram URL patterns
        patterns = [
            r"instagram\.com/([\w\.]+)/?$",  # instagram.com/username
            r"instagram\.com/([\w\.]+)/?\?.*$",  # instagram.com/username?param=value
            r"@([\w\.]+)"  # @username
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None