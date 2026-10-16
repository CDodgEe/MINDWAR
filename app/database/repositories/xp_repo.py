"""Репозиторий XP-транзакций."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import XPTransaction, XPTransactionType


class XPRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        amount: int,
        transaction_type: XPTransactionType,
        description: str,
        xp_before: int,
        xp_after: int,
        reference_id: int | None = None,
    ) -> XPTransaction:
        tx = XPTransaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            reference_id=reference_id,
            description=description,
            xp_before=xp_before,
            xp_after=xp_after,
        )
        self.session.add(tx)
        await self.session.flush()
        return tx

    async def get_user_history(self, user_id: int, limit: int = 10) -> list[XPTransaction]:
        result = await self.session.execute(
            select(XPTransaction)
            .where(XPTransaction.user_id == user_id)
            .order_by(XPTransaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
