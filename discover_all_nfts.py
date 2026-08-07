#!/usr/bin/env python3
"""
Discover ALL ERC-721 contracts on Dogechain by scanning all deployed contracts.
Uses Blockscout listcontracts API + supportsInterface check.
"""
import json, urllib.request, time, sys

EXPLORER = "https://explorer.dogechain.dog/api"
RPC = "https://rpc.dogechain.dog"

def api_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

def rpc_call(method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read()).get("result")

def get_string(call_result):
    if not call_result or call_result == "0x":
        return None
    raw = bytes.fromhex(call_result[2:])
    if len(raw) < 64:
        return None
    length = int.from_bytes(raw[32:64], "big")
    if length > 256 or 64 + length > len(raw):
        return None
    try:
        return raw[64:64+length].decode("utf-8", errors="replace").strip("\x00").strip()
    except:
        return None

def is_erc721(addr):
    # supportsInterface(0x80ac58cd)
    data = "0x01ffc9a7" + "0000000000000000000000000000000000000000000000000000000080ac58cd"
    result = rpc_call("eth_call", [{"to": addr, "data": data}, "latest"])
    if result and len(result) >= 66 and int(result, 16) == 1:
        return True
    # Fallback: ownerOf(1)
    data = "0x6352211e" + "0000000000000000000000000000000000000000000000000000000000000001"
    result = rpc_call("eth_call", [{"to": addr, "data": data}, "latest"])
    if result and result != "0x" and len(result) >= 42:
        addr_result = "0x" + result[-40:]
        if addr_result != "0x" + "0" * 40:
            return True
    return False

print("Discovering all contracts on Dogechain...")

# Get ALL contracts from Blockscout
all_contracts = []
page = 1
while True:
    try:
        data = api_get(f"{EXPLORER}?module=account&action=listcontracts&page={page}&offset=100&filter=0")
        result = data.get("result", [])
        if not isinstance(result, list) or len(result) == 0:
            break
        for c in result:
            addr = c.get("contractAddress", "")
            if addr:
                all_contracts.append(addr)
        print(f"  Page {page}: {len(result)} contracts (total: {len(all_contracts)})")
        page += 1
        time.sleep(0.3)
        if page > 500:
            break
    except Exception as e:
        print(f"  Page {page} error: {e}")
        break

print(f"\nTotal contracts discovered: {len(all_contracts)}")
print(f"\nChecking each for ERC-721...")

# Check each for ERC-721
nft_contracts = []
for i, addr in enumerate(all_contracts):
    try:
        if is_erc721(addr):
            name = get_string(rpc_call("eth_call", [{"to": addr, "data": "0x06fdde03"}, "latest"]))
            sym = get_string(rpc_call("eth_call", [{"to": addr, "data": "0x95d89b41"}, "latest"]))
            supply_r = rpc_call("eth_call", [{"to": addr, "data": "0x18160ddd"}, "latest"])
            supply = int(supply_r, 16) if supply_r and supply_r != "0x" else 0
            nft_contracts.append({
                "address": addr,
                "name": name or "?",
                "symbol": sym or "?",
                "total_supply": supply
            })
            print(f"  ✅ {sym or '?':>12} | {(name or '?')[:30]:>30} | supply={supply:>6} | {addr}")
    except:
        pass
    time.sleep(0.1)
    if (i + 1) % 100 == 0:
        print(f"  Checked {i+1}/{len(all_contracts)}, found {len(nft_contracts)} NFTs...")

print(f"\n{'='*60}")
print(f"Found {len(nft_contracts)} ERC-721 contracts out of {len(all_contracts)} total")

# Save
out_path = "/Users/penny/.openclaw-telegram/workspace/nft-snapshot/discovered_nfts.json"
with open(out_path, "w") as f:
    json.dump(nft_contracts, f, indent=2)
print(f"Saved to {out_path}")
