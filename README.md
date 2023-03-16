# Statipy

Track your interactions.py bot statistics!

## Installation

### Prerequites

- A MongoDB instance
- `beanie==1.17.0`
- `interactions>=5.0`

## Usage

```py
from statipy import StatipyClient, init_db

client = StatipyClient()

client.load_extension("statipy.client")

client.start("token")
```

## Advanced Settings

```py
client = StatipyClient(
    mongo_user="username",
    mongo_pass="password",
    mongo_host="host",
    mongo_port=27017
)
```
