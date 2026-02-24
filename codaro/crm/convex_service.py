import os
from convex import ConvexClient

CONVEX_URL = os.environ["CONVEX_URL"]  # from Convex dashboard Settings


_client = ConvexClient(CONVEX_URL)

def list_clients():
    return _client.query("clients:listClients", {})

def create_client(payload: dict):
    return _client.mutation("clients:createClient", payload)