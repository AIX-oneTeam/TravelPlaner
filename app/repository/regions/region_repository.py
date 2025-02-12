from sqlmodel import select
from app.data_models.data_model import AdministrativeDivision
from sqlmodel.ext.asyncio.session import AsyncSession

# 모든 행정구역 데이터 가져오기
async def get_all_divisions(session: AsyncSession):
    try:
        statement = select(AdministrativeDivision)
        query = await session.exec(statement)
        results = query.all()
        return [
            {"city_province": r.city_province, "city_county": r.city_county}
            for r in results
        ]
    except Exception as e:
        print("[ administrativeDivisionRepository ] get_all_divisions() 에러 : ", e)
        return []
