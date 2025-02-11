
import enum

class SpotType(enum):
    숙소 = 0
    관광지 = 1
    맛집 = 2
    카페 = 3

class AccomodationType(enum):
    HOTEL = "호텔"
    MOTEL = "모텔"
    GUESTHOUSE = "게스트하우스"
    HOSTEL = "호스텔"
    PENSION = "펜션"
    RESORT = "리조트"
    CONDO = "콘도"
    INN = "여관"
    RYOKAN = "료칸"
    HANOK = "한옥"
    CAMP = "캠핑"
    GLAMPING = "글램핑"
    FULL_VILLA = "풀빌라"


class CafeType(enum):
    BAKERY = "베이커리"
    DESSERT = "디저트"
    CAKE = "케이크"
    TAKEOUT = "테이크아웃"
    DRIVE_THRU = "드라이브스루"
    LARGE = "대형 카페"
    SMALL = "소형 카페"
    TERRACE = "야외 카페"
    ROOFTOP = "옥상 카페"
    VEGAN = "비건 카페"
    PET_FRIENDLY = "반려동물 동반 카페"
    FULL_HOURS = "24시간 카페"
    BOOK_CAFE = "책카페"
    BOARD_GAME = "보드게임 카페"
    ALONE_CAFFE = "혼자 가기 좋은 카페"
    FRANCHISE = "프랜차이즈 카페"


class RestaurantType(enum):
    KOREAN = "한식"
    CHINESE = "중식"
    JAPANESE = "일식"
    WESTERN = "양식"
    MAXCIAN = "멕시칸"
    ITALIAN = "이탈리안"
    THAI = "태국"
    VIETNAMESE = "베트남"
    INDIAN = "인도"
    MIDDLE_EASTERN = "중동"
    FASTFOOD = "패스트푸드"
    FUSION = "퓨전"
    PUB = "펍"
    BUFFET = "뷔페"
    VEGETARIAN = "채식"
    SEAFOOD = "해산물"
    FINE_DINING = "고급 요리"
    FAMILY_STYLE = "가족 스타일"
    STEAKHOUSE = "스테이크 하우스"

class SpotType(enum):
    HISTORICAL = "역사"
    NATURAL = "자연"
    CULTURAL = "문화"
    ENTERTAINMENT = "엔터"
    SHOPPING = "쇼핑"
    FOOD_STREET = "먹자 골목"
    SPORTS = "스포츠"
    LEISURE = "레저"
    RELIGIOUS = "종교"
    WELLNESS = "웰빙"
    FESTIVAL = "축제"

class CompanionType(enum):
    adult = "성인"
    teen = "청소년"
    child = "어린이"
    infant = "영유아"
    pet = "반려견"
    senior = "시니어"

class AgeType(enum):
    teen = "10대"
    twenties = "20대"
    thirties = "30대"
    forties = "40대"
    fifties = "50대"
    sixties = "60대"
    seventies = "70대"
    eighties = "80대"
