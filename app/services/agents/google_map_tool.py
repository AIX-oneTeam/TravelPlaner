import datetime
import json
import logging
import os
from typing import Any, Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def _save_results_to_file(content: str) -> None:
    """Saves the search results to a file."""
    try:
        filename = f"maps_search_results_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        with open(filename, "w") as file:
            file.write(content)
        logger.info(f"Results saved to {filename}")
    except IOError as e:
        logger.error(f"Failed to save results to file: {e}")
        raise

class MapsSearchToolSchema(BaseModel):
    """Input schema for MapsSearchTool."""
    search_query: str = Field(
        ..., description="Mandatory search query for searching places on the map"
    )

class MapsSearchTool(BaseTool):
    name: str = "Search for places on Google Maps"
    description: str = (
        "A tool that can be used to search for places on Google Maps with a search_query. "
        "Returns relevant locations based on user preferences."
    )
    args_schema: Type[BaseModel] = MapsSearchToolSchema
    base_url: str = "https://google.serper.dev/maps"
    n_results: int = 10
    save_file: bool = False

    def _make_api_request(self, search_query: str) -> dict:
        """Make API request to Serper Maps API."""
        payload = json.dumps({"q": search_query, "num": self.n_results})
        headers = {
            "X-API-KEY": os.environ["SERPER_API_KEY"],
            "content-type": "application/json",
        }
        
        response = None
        try:
            response = requests.post(
                self.base_url, headers=headers, json=json.loads(payload), timeout=10
            )
            response.raise_for_status()
            results = response.json()
            if not results:
                logger.error("Empty response from Serper API")
                raise ValueError("Empty response from Serper API")
            return results
        except requests.exceptions.RequestException as e:
            error_msg = f"Error making request to Serper API: {e}"
            if response is not None and hasattr(response, "content"):
                error_msg += f"\nResponse content: {response.content}"
            logger.error(error_msg)
            raise
        except json.JSONDecodeError as e:
            if response is not None and hasattr(response, "content"):
                logger.error(f"Error decoding JSON response: {e}")
                logger.error(f"Response content: {response.content}")
            else:
                logger.error(f"Error decoding JSON response: {e} (No response content available)")
            raise

    def _process_search_results(self, results: dict) -> list:
        """Process and structure search results."""
        places = results.get("places", [])
        processed_results = []
        
        for place in places[: self.n_results]:
            try:
                place_data = {
                    "kor_name": place["title"],
                    "address": place.get("address", ""),
                    "url": place.get("website", ""),
                    "image_url": place.get("thumbnailUrl", ""),
                    "map_url": f"https://www.google.com/maps/place/?q=place_id:{place.get('placeId', '')}",
                    "latitude": str(place.get("latitude", "")),
                    "longitude": str(place.get("longitude", "")),
                    "phone_number": str(place.get("phoneNumber", "")),
                    "business_hours": str(place.get("openingHours", "")),
                }
                processed_results.append(place_data)
            except KeyError:
                logger.warning(f"Skipping malformed place result: {place}")
                continue
        
        return processed_results

    def _run(self, **kwargs: Any) -> Any:
        """Execute the search operation."""
        search_query = kwargs.get("search_query")
        save_file = kwargs.get("save_file", self.save_file)

        results = self._make_api_request(search_query)
        formatted_results = self._process_search_results(results)

        if save_file:
            _save_results_to_file(json.dumps(formatted_results, indent=2))
        
        return formatted_results
