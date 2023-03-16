# Statipy

Track your interactions.py bot statistics!

## Installation

### Prerequites

- MongoDB 5.0 or newer
- `beanie==1.17.0`
- `interactions>=5.0`

## Usage

```py
import asyncio
from statipy import StatipyClient, init_db


async def run():
    await init_db()
    client = StatipyClient()

    client.load_extension("statipy.ext")

    client.astart("token")

asyncio.run(run())
```

## Advanced Settings

```py
await init_db(
    username="username",
    password="password",
    host="host",
    port=27017
)
```
