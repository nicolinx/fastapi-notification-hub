import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.api_key import ApiKey

# A readable prefix makes a leaked key easy to recognise and search for.
KEY_PREFIX = "nh_"


def generate_key() -> str:
    """A new random key, for example `nh_Zk3...`. 32 random bytes = 256 bits."""
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def create_api_key(db: AsyncSession, name: str) -> tuple[ApiKey, str]:
    """Create a key. Returns the row and the raw key, which is shown only once."""
    raw_key = generate_key()

    api_key = ApiKey(name=name, key_hash=hash_key(raw_key))

    db.add(api_key)
    await db.commit()

    return api_key, raw_key


async def find_by_raw_key(db: AsyncSession, raw_key: str) -> ApiKey | None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == hash_key(raw_key))
    )

    return result.scalar_one_or_none()
