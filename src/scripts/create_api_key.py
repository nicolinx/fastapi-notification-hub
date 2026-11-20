import asyncio
import sys

from src.core.database import SessionLocal, engine
from src.services import api_key_service


async def main(name: str) -> None:
    async with SessionLocal() as db:
        api_key, raw_key = await api_key_service.create_api_key(db, name)

    await engine.dispose()

    print(f"Created API key #{api_key.id} ({api_key.name})")
    print(f"Key: {raw_key}")
    print("Save it now. It cannot be shown again.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m src.scripts.create_api_key <name>")

    asyncio.run(main(sys.argv[1]))
