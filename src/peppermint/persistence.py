import typing

T = typing.TypeVar("T")


class SyncPersistence(typing.Protocol[T]):
    def persist(self, instance: T) -> T: ...


class AsyncPersistence(typing.Protocol[T]):
    async def persist(self, instance: T) -> T: ...


class RaisingSyncPersistence(SyncPersistence[T]):
    def persist(self, instance: T) -> T:
        raise NotImplementedError("RaisingSyncPersistence is not implemented")


class RaisingAsyncPersistence(AsyncPersistence[T]):
    async def persist(self, instance: T) -> T:
        raise NotImplementedError("RaisingAsyncPersistence is not implemented")
