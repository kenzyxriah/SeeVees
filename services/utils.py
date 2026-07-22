from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select


async def paginate_query(
    db: AsyncSession,
    stmt: Select,
    start: int = 0,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Perform database-level SQL OFFSET and LIMIT slicing with total count calculation.

    Args:
        db (AsyncSession): Active database session.
        stmt (Select): The base SQLAlchemy select query statement.
        start (int): Starting offset index (default is 0).
        limit (int): Number of items to retrieve (default is 10).

    Returns:
        dict[str, Any]: Dictionary containing:
            - total_count (int): Total count of matching records in database.
            - items (list): List of query results within the requested range.
    """
    start = max(0, start)
    limit = max(1, min(100, limit))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total_count = count_result.scalar_one() or 0

    paginated_stmt = stmt.offset(start).limit(limit)
    result = await db.execute(paginated_stmt)
    items = list(result.scalars().all())

    return {
        "total_count": total_count,
        "items": items,
    }
