"""
Type safety utilities for ensuring correct sync/async session usage.

This module provides type hints and utilities to prevent common sync/async
session mixing issues in SQLAlchemy operations.
"""

from typing import TypeVar, Generic, Protocol, runtime_checkable
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

# Generic type variables for session-aware operations
SyncSessionT = TypeVar('SyncSessionT', bound=Session)
AsyncSessionT = TypeVar('AsyncSessionT', bound=AsyncSession)
SessionT = TypeVar('SessionT', bound=Session | AsyncSession)


@runtime_checkable
class SyncSessionProtocol(Protocol):
    """Protocol for synchronous database session operations."""
    
    def execute(self, stmt): ...
    def scalar(self, stmt): ...
    def scalars(self, stmt): ...
    def add(self, instance): ...
    def delete(self, instance): ...
    def commit(self): ...
    def rollback(self): ...
    def refresh(self, instance): ...
    def flush(self): ...
    def close(self): ...


@runtime_checkable  
class AsyncSessionProtocol(Protocol):
    """Protocol for asynchronous database session operations."""
    
    async def execute(self, stmt): ...
    async def scalar(self, stmt): ...
    async def scalars(self, stmt): ...
    def add(self, instance): ...
    async def delete(self, instance): ...
    async def commit(self): ...
    async def rollback(self): ...
    async def refresh(self, instance): ...
    async def flush(self): ...
    async def close(self): ...


class SyncOperation(Generic[SyncSessionT]):
    """
    Generic class for operations that require synchronous sessions.
    
    Example usage:
        def create_user_sync(session: SyncOperation[Session], user_data):
            # mypy will enforce that only sync session methods are used
            session.add(user)
            session.commit()  # OK - sync method
            # await session.commit()  # Type error - can't await sync method
    """
    pass


class AsyncOperation(Generic[AsyncSessionT]):
    """
    Generic class for operations that require asynchronous sessions.
    
    Example usage:
        async def create_user_async(session: AsyncOperation[AsyncSession], user_data):
            # mypy will enforce that async session methods are awaited
            session.add(user)  # OK - add is sync even in async sessions
            await session.commit()  # OK - async method awaited
            # session.commit()  # Type error - async method not awaited
    """
    pass


def ensure_sync_session(session) -> SyncSessionProtocol:
    """
    Runtime type guard to ensure session is synchronous.
    
    Args:
        session: Database session of unknown type
        
    Returns:
        session: Confirmed synchronous session
        
    Raises:
        TypeError: If session is not synchronous
    """
    if not isinstance(session, Session):
        raise TypeError(f"Expected sync Session, got {type(session)}")
    return session


def ensure_async_session(session) -> AsyncSessionProtocol:
    """
    Runtime type guard to ensure session is asynchronous.
    
    Args:
        session: Database session of unknown type
        
    Returns:
        session: Confirmed asynchronous session
        
    Raises:
        TypeError: If session is not asynchronous
    """
    if not isinstance(session, AsyncSession):
        raise TypeError(f"Expected async AsyncSession, got {type(session)}")
    return session


# Type aliases for common session patterns
SyncCRUDSession = Session
AsyncCRUDSession = AsyncSession
