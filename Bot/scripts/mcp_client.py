#!/usr/bin/env python3
"""
Simple MCP Client for Bitget MCP Server.

This allows the CryptoSentinel bot to directly use the Bitget MCP Server as active tools for perception data (the same tools the Skill Hub skills use).

The MCP Server is spawned via npx, and we communicate over stdio with JSON-RPC.

This makes the bot "directly using the bitget-mcp-server as active tools".

For Skill Hub: the skills are high-level instructions for LLMs on which MCP tools to call and how to format. Our bot replicates the skills by calling the same MCP tools and formatting similarly.

Usage in the bot:

client = BitgetMCPClient()

client.start()

tools = client.list_tools()

data = client.call_tool("crypto_market", {"symbol": "BTCUSDT"})

# then use the data for technicals, sentiment, etc.

See the hackathon docs for the full list of MCP tools the skills use (crypto_market, sentiment_index, news_feed, macro_indicators, etc.).

The trading tools can be called via the bgc CLI or if the MCP exposes them.

"""

import subprocess
import json
import threading
import queue
import os
import time

class BitgetMCPClient:
    def __init__(self):
        self.process = None
        self.message_id = 0
        self.responses = {}
        self.tools = {}
        self.read_thread = None
        self._stop = False

    def start(self, env=None):
        """Start the bitget-mcp-server via npx."""
        if env is None:
            env = os.environ.copy()
        # Ensure keys if set for authenticated tools
        cmd = ["npx", "--yes", "bitget-mcp-server"]
        # Use shell=True on Windows to resolve npx from PATH (npx is a shell command in node installation)
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
            shell=True
        )
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        # Give it a moment to start
        time.sleep(1)

    def _read_loop(self):
        for line in self.process.stdout:
            if self._stop:
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                if "id" in msg and msg["id"] is not None:
                    self.responses[msg["id"]] = msg
                # Could handle notifications here
            except json.JSONDecodeError:
                # Server may print logs
                pass
            except Exception:
                pass

    def _send(self, msg):
        if self.process and self.process.stdin:
            line = json.dumps(msg) + "\n"
            self.process.stdin.write(line)
            self.process.stdin.flush()

    def _next_id(self):
        self.message_id += 1
        return self.message_id

    def initialize(self):
        """Send initialize request."""
        req_id = self._next_id()
        msg = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "cryptosentinel",
                    "version": "1.0"
                }
            }
        }
        self._send(msg)
        # Wait for response
        for _ in range(50):  # ~5s
            if req_id in self.responses:
                return self.responses.pop(req_id)
            time.sleep(0.1)
        return None

    def list_tools(self):
        """List available tools from the MCP server."""
        req_id = self._next_id()
        msg = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/list",
            "params": {}
        }
        self._send(msg)
        for _ in range(50):
            if req_id in self.responses:
                resp = self.responses.pop(req_id)
                if "result" in resp:
                    self.tools = {t["name"]: t for t in resp["result"].get("tools", [])}
                return resp
            time.sleep(0.1)
        return None

    def call_tool(self, name, arguments):
        """Call a tool on the MCP server."""
        req_id = self._next_id()
        msg = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }
        self._send(msg)
        for _ in range(100):  # up to ~10s
            if req_id in self.responses:
                return self.responses.pop(req_id)
            time.sleep(0.1)
        return {"error": "timeout"}

    def close(self):
        self._stop = True
        if self.process:
            try:
                self.process.terminate()
            except:
                pass

# Example usage for the bot:
# client = BitgetMCPClient()
# client.start()
# client.initialize()
# tools = client.list_tools()
# data = client.call_tool("crypto_market", {"symbol": "BTCUSDT"})
# print(data)
# client.close()
