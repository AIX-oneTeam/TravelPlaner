import os
import requests
from typing import List, Dict
from dotenv import load_dotenv
from crewai.tools import BaseTool

# .env 파일 로드
load_dotenv()
KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")

class KakaoMapRouteTool(BaseTool):
    """카카오 맵을 활용하여 최적 경로를 계산하는 툴"""

    name: str = "KakaoMapRoute"
    description: str = "여행 일정의 최적 경로를 계산하고 각 장소 간 거리 정보를 제공합니다."

    def _run(self, spots: List[Dict]) -> Dict:
        """여행 경로 최적화"""
        if len(spots) < 2:
            return {"error": "최소 두 개 이상의 장소가 필요합니다."}

        origin = self._format_location(spots[0])
        destination = self._format_location(spots[-1])
        waypoints = [self._format_location(spot) for spot in spots[1:-1]]

        payload = {
            "origin": origin,
            "destination": destination,
            "waypoints": waypoints,
            "priority": "RECOMMEND"
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"KakaoAK {KAKAO_CLIENT_ID}"
        }

        try:
            response = requests.post(
                "https://apis-navi.kakaomobility.com/v1/waypoints/directions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()  # 오류 발생 시 예외 발생

            route_data = response.json()
            return self._process_route_data(route_data, spots)

        except requests.exceptions.RequestException as e:
            return {"error": f"API 요청 실패: {str(e)}"}

    def _format_location(self, spot: Dict) -> Dict:
        """장소 데이터를 API 요청에 맞게 변환"""
        return {
            "name": spot.get("kor_name", ""),
            "x": str(spot["longitude"]),
            "y": str(spot["latitude"])
        }

    def _process_route_data(self, route_data: Dict, spots: List[Dict]) -> List[Dict]:
        """API 응답을 받아 경로 최적화 데이터를 spots 리스트에 반영"""
        optimized_spots = []
        coordinates = {(spot["latitude"], spot["longitude"]): spot for spot in spots}

        for route in route_data.get("routes", []):
            for section in route.get("sections", []):
                for guide in section.get("guides", []):
                    location = guide.get("location", {})
                    lat, lon = location.get("y"), location.get("x")

                    if (lat, lon) in coordinates:
                        optimized_spot = coordinates[(lat, lon)].copy()
                        optimized_spot["distance_from_prev"] = guide.get("distance", 0)
                        optimized_spots.append(optimized_spot)

        return optimized_spots
