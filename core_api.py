import os
import requests
import logging

logger = logging.getLogger(__name__)

class CoreAPI:
    def __init__(self, api_key=None, api_url=None):
        logger.debug(f"Initializing CoreAPI with api_key={'*' * len(api_key) if api_key else 'None'}")
        logger.debug(f"API URL: {api_url}")
        
        self.api_key = api_key or os.environ.get('CORE_API_KEY')
        if not self.api_key:
            logger.error("CORE_API_KEY not found in environment variables or constructor")
            raise ValueError("CORE_API_KEY is required")
            
        self.base_url = api_url.rstrip('/') if api_url else 'https://api.core.ac.uk/v3'
        logger.debug(f"CoreAPI initialized with base_url: {self.base_url}")

    def search_papers(self, query, page=1, page_size=10):
        """Search for papers using the CORE API"""
        try:
            headers = {'Authorization': f'Bearer {self.api_key}'}
            params = {
                'q': query,
                'page': page,
                'pageSize': page_size,
                'entities': 'papers'
            }

            logger.debug(f"Sending request to CORE API with params: {params}")
            response = requests.get(
                f'{self.base_url}/search/works',
                headers=headers,
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'results': [{
                        'title': item.get('title'),
                        'authors': [author.get('name') for author in item.get('authors', [])],
                        'abstract': item.get('abstract'),
                        'doi': item.get('doi'),
                        'year': item.get('yearPublished'),
                        'publisher': item.get('publisher'),
                        'pdf_url': item.get('downloadUrl'),
                        'repository': item.get('repositoryName')
                    } for item in data.get('results', [])],
                    'total_hits': data.get('totalHits', 0),
                    'page': page,
                    'page_size': page_size
                }
            elif response.status_code == 401:
                logger.error("Invalid CORE API key")
                return None
            elif response.status_code == 429:
                logger.error("CORE API rate limit exceeded")
                return None
            else:
                logger.error(f"CORE API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error searching papers: {str(e)}")
            return None