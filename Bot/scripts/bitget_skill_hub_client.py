#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
"""
Bitget Skill Hub MCP Client -- CryptoSentinel AI
=================================================
Calls the official Bitget Skill Hub market-data MCP server at:
  https://datahub.noxiaohao.com/mcp

This is THE SAME server that all 5 official Bitget Skill Hub skills use:
  - sentiment-analyst  -> calls sentiment_index, derivatives_sentiment
  - market-intel       -> calls crypto_market, news_feed, tradfi_news
  - news-briefing      -> calls news_feed
  - macro-analyst      -> calls crypto_market, tradfi_news
  - technical-analysis -> calls spot candles via Bitget REST API

Protocol: MCP Streamable HTTP (SSE transport)
  1. POST /mcp with initialize request -> returns mcp-session-id header
  2. POST /mcp with session ID header -> returns SSE stream with tool results

Usage:
    from bitget_skill_hub_client import BitgetSkillHubClient
    client = BitgetSkillHubClient()
    result = client.sentiment_index()
    result = client.derivatives_sentiment("BTCUSDT", "4h")
    result = client.crypto_market_global()
    result = client.news_feed(keyword="bitcoin", limit=10)
"""

import json
import urllib.request
import urllib.error
import time
import argparse
import re

# Official Bitget Skill Hub market-data MCP server
# Referenced directly in every SKILL.md: <!-- MCP Server: https://datahub.noxiaohao.com/mcp -->
MCP_SERVER_URL = "https://datahub.noxiaohao.com/mcp"
TIMEOUT = 2


class BitgetSkillHubClient:
    """
    HTTP client for the official Bitget Skill Hub market-data MCP server.
    Implements the MCP Streamable HTTP (SSE) protocol.
    """

    def __init__(self, server_url: str = MCP_SERVER_URL, verbose: bool = False):
        self.server_url = server_url
        self.verbose = verbose
        self._session_id = None
        self._request_id = 0

    def _initialize(self) -> bool:
        """
        Step 1 of MCP protocol: send initialize request to get a session ID.
        The session ID is returned in the 'mcp-session-id' response header.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "CryptoSentinel-AI",
                    "version": "1.0"
                }
            }
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.server_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "User-Agent": "CryptoSentinel-AI/1.0 (Bitget-Hackathon)",
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                session_id = resp.headers.get("mcp-session-id")
                if session_id:
                    self._session_id = session_id
                    if self.verbose:
                        print(f"[SkillHub] Session initialized: {session_id[:16]}...")
                    return True
                # Try to read body for error info
                body_text = resp.read().decode("utf-8", errors="replace")
                if self.verbose:
                    print(f"[SkillHub] Initialize: no session ID in headers. Body: {body_text[:200]}")
                return False
        except Exception as e:
            if self.verbose:
                print(f"[SkillHub] Initialize failed: {e}")
            return False

    def _call(self, tool_name: str, arguments: dict):
        """
        Step 2 of MCP protocol: call a tool using the session ID.
        Server returns SSE stream; we parse the first 'message' event.
        """
        # Auto-initialize session if needed
        if not self._session_id:
            if not self._initialize():
                if self.verbose:
                    print(f"[SkillHub] Cannot call {tool_name}: session init failed")
                return None

        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.server_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "User-Agent": "CryptoSentinel-AI/1.0 (Bitget-Hackathon)",
                "mcp-session-id": self._session_id,
            },
            method="POST"
        )
        try:
            if self.verbose:
                print(f"[SkillHub] Calling {tool_name}({json.dumps(arguments)[:80]})")
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                # Parse SSE stream: look for 'data: {...}' lines
                return self._parse_sse(raw, tool_name)
        except urllib.error.HTTPError as e:
            # Session expired - try re-initializing once
            if e.code in (400, 401, 404) and self._session_id:
                if self.verbose:
                    print(f"[SkillHub] Session expired (HTTP {e.code}), re-initializing...")
                self._session_id = None
                return self._call(tool_name, arguments)
            if self.verbose:
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8", errors="replace")[:200]
                except Exception:
                    pass
                print(f"[SkillHub] {tool_name} HTTP {e.code}: {err_body}")
            return None
        except Exception as e:
            if self.verbose:
                print(f"[SkillHub] {tool_name} exception: {e}")
            return None

    def _parse_sse(self, raw: str, tool_name: str):
        """Parse SSE stream and extract JSON result from MCP tool response."""
        # SSE format: "event: message\ndata: {...}\n\n"
        for line in raw.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if not data_str or data_str == "[DONE]":
                continue
            try:
                data = json.loads(data_str)
                if "result" in data:
                    result = data["result"]
                    # MCP returns content array with text items
                    if isinstance(result, dict) and "content" in result:
                        for item in result["content"]:
                            if item.get("type") == "text":
                                text = item["text"]
                                try:
                                    parsed = json.loads(text)
                                    if self.verbose:
                                        print(f"[SkillHub] {tool_name} -> OK ({len(text)} chars)")
                                    return parsed
                                except json.JSONDecodeError:
                                    # Return raw text as dict
                                    return {"raw": text}
                    return result
                elif "error" in data:
                    if self.verbose:
                        print(f"[SkillHub] {tool_name} MCP error: {data['error']}")
                    return None
            except json.JSONDecodeError:
                continue
        if self.verbose:
            print(f"[SkillHub] {tool_name}: no parseable data in SSE stream ({len(raw)} chars)")
            if raw:
                print(f"  Raw preview: {raw[:300]}")
        return None

    def list_tools(self):
        """List all available tools on the MCP server."""
        return self._call_raw_method("tools/list", {})

    def _call_raw_method(self, method: str, params: dict):
        """Call any MCP method directly (for listing tools, etc.)."""
        if not self._session_id:
            if not self._initialize():
                return None
        self._request_id += 1
        payload = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.server_url, data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "User-Agent": "CryptoSentinel-AI/1.0",
                "mcp-session-id": self._session_id,
            }, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return self._parse_sse(raw, method)
        except Exception as e:
            if self.verbose:
                print(f"[SkillHub] {method} error: {e}")
            return None

    # -------------------------------------------------------------
    # sentiment-analyst skill calls these:
    # -------------------------------------------------------------

    def sentiment_index(self, action: str = "current"):
        """
        Called by: sentiment-analyst skill (Quick Snapshot step 1)
        Returns: Fear & Greed Index value, classification, historical trend
        """
        return self._call("sentiment_index", {"action": action})

    def derivatives_sentiment(self, symbol: str = "BTCUSDT", action: str = "long_short",
                              period: str = "4h"):
        """
        Called by: sentiment-analyst skill (Quick Snapshot steps 2 & 3)
        Actions: 'long_short' | 'taker_ratio' | 'funding' | 'open_interest'
        Returns: Long/short ratio, taker buy/sell volume ratio, funding rate, OI
        """
        return self._call("derivatives_sentiment", {
            "action": action,
            "symbol": symbol,
            "period": period
        })

    # -------------------------------------------------------------
    # market-intel + macro-analyst skills call these:
    # -------------------------------------------------------------

    def crypto_market(self, action: str = "global", coin_ids: str = "bitcoin,ethereum"):
        """
        Called by: market-intel + macro-analyst skills
        action='global'  -> global market cap, BTC dominance, total volume
        action='price'   -> per-coin price/change/volume
        """
        args = {"action": action}
        if action == "price":
            args["coin_ids"] = coin_ids
        return self._call("crypto_market", args)

    def tradfi_news(self, action: str = "crypto_news", limit: int = 5):
        """
        Called by: market-intel + macro-analyst skills for macro/TradFi context
        Returns: Bloomberg/Reuters/FT style macro + crypto news headlines
        """
        return self._call("tradfi_news", {"action": action, "limit": limit})

    # -------------------------------------------------------------
    # news-briefing skill calls this:
    # -------------------------------------------------------------

    def news_feed(self, action: str = "latest",
                  feeds: str = "cointelegraph,coindesk,decrypt,blockworks",
                  keyword: str = "", limit: int = 10):
        """
        Called by: news-briefing skill
        Aggregates 20+ RSS feeds. Use keyword to filter per-asset.
        """
        args = {"action": action, "feeds": feeds, "limit": limit}
        if keyword:
            args["keyword"] = keyword
        return self._call("news_feed", args)

    # -------------------------------------------------------------
    # Convenience: full perception pull for one symbol
    # -------------------------------------------------------------

    def get_full_perception(self, symbol: str = "BTCUSDT") -> dict:
        """
        Runs all Skill Hub perception calls for a single symbol.
        Equivalent to running all 5 Bitget Skill Hub skills in parallel.
        """
        perception = {"symbol": symbol, "timestamp": time.time()}

        # sentiment-analyst
        fg = self.sentiment_index("current")
        ls = self.derivatives_sentiment(symbol, "long_short", "4h")
        tr = self.derivatives_sentiment(symbol, "taker_ratio", "4h")
        if fg:
            perception["fear_greed"] = fg
        if ls:
            perception["long_short"] = ls
        if tr:
            perception["taker_ratio"] = tr

        # macro-analyst + market-intel
        global_market = self.crypto_market("global")
        if global_market:
            perception["global_market"] = global_market

        # news-briefing
        base_coin = symbol.replace("USDT", "").lower()
        news = self.news_feed(keyword=base_coin, limit=5)
        if news:
            perception["news"] = news

        return perception


def _score_from_perception(perception: dict) -> float:
    """
    Convert raw MCP perception data into a -2 to +2 float score.
    Integrates directly with fetch_signals.py's aggregate score system.
    """
    score = 0.0
    data_found = False

    # --- Fear & Greed ---
    fg = perception.get("fear_greed")
    if fg and isinstance(fg, dict):
        data_found = True
        value = fg.get("value")
        if value is None and "data" in fg:
            d = fg.get("data")
            if isinstance(d, list) and d:
                value = d[0].get("value")
        if value is not None:
            try:
                v = float(value)
                if v <= 25:    score += 2.0
                elif v <= 45:  score += 1.0
                elif v <= 55:  score += 0.0
                elif v <= 75:  score -= 1.0
                else:          score -= 2.0
            except (TypeError, ValueError):
                pass

    # --- Long/Short Ratio ---
    ls = perception.get("long_short")
    if ls and isinstance(ls, dict):
        data_found = True
        ratio = ls.get("longShortRatio") or ls.get("ratio") or ls.get("long_short_ratio")
        if ratio is None and isinstance(ls.get("list"), list) and ls["list"]:
            ratio = ls["list"][0].get("longShortRatio")
        if ratio is not None:
            try:
                r = float(ratio)
                if r > 2.0:    score -= 1.0
                elif r > 1.5:  score -= 0.5
                elif r < 0.5:  score += 1.0
                elif r < 0.75: score += 0.5
            except (TypeError, ValueError):
                pass

    # --- Taker Buy/Sell Ratio ---
    tr = perception.get("taker_ratio")
    if tr and isinstance(tr, dict):
        data_found = True
        buy_ratio = tr.get("buyRatio") or tr.get("takerBuyRatio")
        if buy_ratio is None and isinstance(tr.get("list"), list) and tr["list"]:
            buy_ratio = tr["list"][0].get("buySellRatio") or tr["list"][0].get("buyRatio")
        if buy_ratio is not None:
            try:
                br = float(buy_ratio)
                score += (br - 0.5) * 4.0
            except (TypeError, ValueError):
                pass

    # --- Global Market ---
    gm = perception.get("global_market")
    if gm and isinstance(gm, dict):
        data_found = True
        mkt_change = gm.get("market_cap_change_percentage_24h_usd") or gm.get("market_cap_change_24h")
        if mkt_change is not None:
            try:
                mc = float(mkt_change)
                score += max(-1.0, min(1.0, mc / 3.0))
            except (TypeError, ValueError):
                pass

    return round(score, 3) if data_found else 0.0


def run_test():
    """Test all MCP tool calls and print results."""
    print("=" * 60)
    print("Bitget Skill Hub MCP Client -- Integration Test")
    print(f"Server: {MCP_SERVER_URL}")
    print("Protocol: MCP Streamable HTTP (SSE)")
    print("=" * 60)

    client = BitgetSkillHubClient(verbose=True)

    # First test: initialize session
    print("\n[STEP] Initializing MCP session...")
    ok = client._initialize()
    if ok:
        print(f"  [OK] Session ID: {client._session_id}")
    else:
        print("  [FAIL] Could not initialize session")
        return False

    # Then list tools
    print("\n[STEP] Listing available tools...")
    tools = client._call_raw_method("tools/list", {})
    if tools and isinstance(tools, dict):
        tool_names = [t.get("name") for t in tools.get("tools", [])]
        print(f"  [OK] {len(tool_names)} tools: {tool_names[:8]}...")
    else:
        print(f"  [INFO] tool list raw: {str(tools)[:200]}")

    tests = [
        ("sentiment_index",               lambda: client.sentiment_index()),
        ("derivatives_sentiment (L/S)",    lambda: client.derivatives_sentiment("BTCUSDT", "long_short", "4h")),
        ("derivatives_sentiment (taker)",  lambda: client.derivatives_sentiment("BTCUSDT", "taker_ratio", "4h")),
        ("crypto_market (global)",         lambda: client.crypto_market("global")),
        ("news_feed (bitcoin)",            lambda: client.news_feed(keyword="bitcoin", limit=3)),
        ("tradfi_news",                    lambda: client.tradfi_news()),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n[TEST] {name}")
        try:
            result = fn()
            if result:
                preview = json.dumps(result)[:200]
                print(f"  [OK] {preview}...")
                passed += 1
            else:
                print(f"  [FAIL] returned None/empty (tool may not exist on this server)")
                failed += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if passed > 0:
        print("[PASS] Bitget Skill Hub MCP integration working!")
    elif failed == len(tests):
        print("[WARN] Server reachable but all tool calls failed - tools may have different names.")
    print("=" * 60)
    return passed > 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bitget Skill Hub MCP Client")
    parser.add_argument("--test", action="store_true", help="Run integration tests")
    parser.add_argument("--list-tools", action="store_true", help="List all server tools")
    parser.add_argument("--symbol", default="BTCUSDT", help="Symbol for perception")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.test:
        success = run_test()
        sys.exit(0 if success else 1)

    if args.list_tools:
        client = BitgetSkillHubClient(verbose=True)
        client._initialize()
        tools = client._call_raw_method("tools/list", {})
        print(json.dumps(tools, indent=2, default=str))
        sys.exit(0)

    client = BitgetSkillHubClient(verbose=args.verbose)
    print(f"Fetching full Skill Hub perception for {args.symbol}...")
    perception = client.get_full_perception(args.symbol)
    score = _score_from_perception(perception)
    print(f"\nPerception result:")
    print(json.dumps(perception, indent=2, default=str)[:2000])
    print(f"\nAggregated score: {score:+.3f}")
