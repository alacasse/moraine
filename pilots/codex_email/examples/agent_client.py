"""Official MCP client for the simulated walkthrough; has only the agent token."""
import argparse
import asyncio
import json
from pathlib import Path
import uuid

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main(args):
    token = args.token_file.read_text().strip()
    async with httpx.AsyncClient(headers={"Authorization": "Bearer " + token}, trust_env=False) as http, \
            streamable_http_client("http://127.0.0.1:8765/mcp", http_client=http) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            if args.command == "propose":
                listed = await session.call_tool("list_context", {"grant_id": args.grant_id})
                print(listed.model_dump_json(indent=2))
                read = await session.call_tool("read_context", {"grant_id": args.grant_id,
                                                               "resource_ref": "message-1", "version": 1})
                print(read.model_dump_json(indent=2))
                if listed.isError or read.isError:
                    raise SystemExit("Context refused; no proposal submitted")
                result = await session.call_tool("propose_reply", {
                    "grant_id": args.grant_id, "idempotency_key": str(uuid.uuid4()),
                    "reply_to_ref": "message-1", "body_text": "Mardi à 10 h convient. Merci !"})
            else:
                result = await session.call_tool("get_request", {"request_id": args.request_id})
            print(json.dumps(result.model_dump(mode="json"), ensure_ascii=True, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token-file", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("propose").add_argument("grant_id")
    commands.add_parser("status").add_argument("request_id")
    asyncio.run(main(parser.parse_args()))
