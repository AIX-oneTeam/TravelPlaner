from app.utils.ai_utils import get_travel_recommendations


def recommend_tourist_spots(prompt: str) -> list:
    """
    관광지 추천 서비스 로직
    Args:
        prompt (str): 사용자 입력 프롬프트
    Returns:
        list: 추천 관광지 리스트
    """
    return get_travel_recommendations(prompt)
