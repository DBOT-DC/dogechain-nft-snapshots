#!/usr/bin/env python3
"""
Dogechain NFT Collection Snapshot — Fast Version

Uses Blockscout getTokenHolders API (one paginated call per collection)
instead of scanning Transfer events (12,000+ RPC calls). ~100x faster.

Output per collection:
  {symbol}_holders.json   — wallet → nft_count (airdrop-ready)
  {symbol}_metadata.json  — contract metadata + token URIs (if available)
  {symbol}_summary.json   — collection stats

Usage:
  python3 nft_snapshot_fast.py                    # all known collections
  python3 nft_snapshot_fast.py 0xCONTRACT SYMBOL  # single collection
"""
import json, time, os, sys, csv, urllib.request
from datetime import datetime, timezone

RPC = "https://rpc.dogechain.dog"
EXPLORER = "https://explorer.dogechain.dog/api"
SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
SNAPSHOT_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

KNOWN_COLLECTIONS = [
    ("0xd38b22794b308a2e55808a13d1e6a80c4be94fd5", "RDP"),
    ("0xb6e6b0167ce72057f6ac28cb5fd836896b4d084e", "DOGE-BEARS"),
    ("0x1836c33b9350d18304e0f701de777cc7501e9c2a", "DH"),
    ("0x9b291b0e9c78ce1c94b701d3d9faad349c4be341", "DOGE-BLINDERS"),
    ("0x8743b1cec8939e456f05194503fbb6500a3ba67d", "FTH"),
    ("0x5f595ff1830b0bd9e67ae6376ad80598876cc34f", "MONOS"),
    ("0x01d675a61d94aea570007374d85301d6619d9e6e", "McRIB"),
    ("0x49ffa5d11cb54a6541e33dc04951b1ffdfaa2852", "CYBERDOGS"),
    ("0xbeae0fd8ccecc76afcc137d89f2b006e8c543c84", "DOGEPUNKS"),
    ("0x63309a2b8f507f667da75c24013a2e18904cc19d", "SOVPUNKS"),
    ("0x6b351dc4439a9ac313f6f4d76c51f2d3717f3101", "SEADOGS"),
    ("0xec10d3091abffcc89f0cca5ae90842f5628bfb56", "DCC"),
    ("0x544870cc7ff94a50e507262b98060f6b15835fde", "BDKC"),
    ("0x58f2fea3d66025cdedbc37b5bcd93647d76d7325", "DAC"),
    ("0x79105d9bb5850bdab32aecd0fe669dcdb33d79d6", "DAYC"),
    ("0x81c3164939f515134f6be6b6f9d295887df6554b", "ASTRO"),
    ("0xb3c75f465f6236985c0a0ce5013c5ae7ae2748e5", "DOGEDOODLE"),
    ("0xf6ee4a3f8529a6b20b8f4792a0ea20a419ba21f5", "PIXELFROGS"),
    ("0xa2e57fa488cf272c87b066e2a3e0672c0c58784d", "RAT"),
]


def api_get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                raise


def rpc(method, params, retries=3):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=15).read()).get("result")
        except:
            if attempt < retries - 1:
                time.sleep(1)
    return None


def get_block():
    r = rpc("eth_blockNumber", [])
    return int(r, 16) if r else 0


def get_contract_info(contract):
    """Get contract name, symbol, type from Blockscout."""
    data = api_get(f"{EXPLORER}?module=token&action=getToken&contractaddress={contract}")
    return data.get("result", {})


def get_holders(contract, page_size=10000):
    """Get all token holders via Blockscout API. Returns list of {address, value}."""
    all_holders = []
    page = 1
    while True:
        data = api_get(
            f"{EXPLORER}?module=token&action=getTokenHolders"
            f"&contractaddress={contract}&page={page}&offset={page_size}"
        )
        result = data.get("result", [])
        if not isinstance(result, list) or len(result) == 0:
            break
        all_holders.extend(result)
        if len(result) < page_size:
            break
        page += 1
        time.sleep(0.3)
    return all_holders


def get_token_uri(contract, token_id):
    """Get tokenURI for a specific token ID."""
    data = "0xc87b56dd" + f"{token_id:064x}"
    result = rpc("eth_call", [{"to": contract, "data": data}, "latest"])
    if not result or result == "0x":
        return None
    raw = bytes.fromhex(result[2:])
    if len(raw) < 64:
        return None
    length = int.from_bytes(raw[32:64], "big")
    if length > 1024 or 64 + length > len(raw):
        return None
    try:
        return raw[64:64 + length].decode("utf-8", errors="replace").strip("\x00").strip()
    except:
        return None


def snapshot_collection(contract, symbol, block, snapshot_time):
    print(f"\n{'='*60}")
    print(f"📸 {symbol} ({contract[:10]}...)")
    print(f"{'='*60}")

    result = {
        "contract": contract,
        "symbol": symbol,
        "snapshot_block": block,
        "snapshot_time": snapshot_time,
    }

    # Contract info
    try:
        info = get_contract_info(contract)
        name = info.get("name", "?")
        csymbol = info.get("symbol", "?")
        ctype = info.get("type", "?")
        total_supply = info.get("totalSupply", "0")
        print(f"  Name: {name} ({csymbol})")
        print(f"  Type: {ctype}")
        print(f"  Supply: {total_supply}")
        result["name"] = name
        result["type"] = ctype
        result["total_supply"] = total_supply
    except Exception as e:
        print(f"  ⚠️  Contract info failed: {e}")
        result["status"] = "contract_info_failed"
        return result

    # Get holders
    print(f"  Fetching holders...")
    try:
        holders = get_holders(contract)
    except Exception as e:
        print(f"  ❌ Holders fetch failed: {e}")
        result["status"] = "holders_failed"
        return result

    if not holders:
        print(f"  ⚠️  No holders found")
        result["status"] = "no_holders"
        return result

    # Parse holders
    holder_list = []
    total_nfts = 0
    for h in holders:
        addr = h.get("address", "")
        count = int(h.get("value", "0"))
        holder_list.append({"address": addr, "nft_count": count})
        total_nfts += count

    print(f"  Holders: {len(holder_list):,}")
    print(f"  Total NFTs: {total_nfts:,}")
    print(f"  Top holder: {holder_list[0]['address'][:12]}... = {holder_list[0]['nft_count']} NFTs")

    result["holder_count"] = len(holder_list)
    result["total_nfts_held"] = total_nfts

    # Get a sample of token URIs (first 10 tokens for metadata sample)
    print(f"  Sampling token metadata (first 10)...")
    token_uris = {}
    sample_size = min(10, total_nfts)
    for tid in range(sample_size):
        uri = get_token_uri(contract, tid)
        if uri:
            token_uris[tid] = uri
        time.sleep(0.1)

    result["metadata_sample"] = token_uris

    # Save outputs
    coll_dir = os.path.join(SNAPSHOT_DIR, symbol)
    os.makedirs(coll_dir, exist_ok=True)

    # Holders JSON (complete)
    holders_path = os.path.join(coll_dir, f"{symbol}_holders.json")
    with open(holders_path, "w") as f:
        json.dump({
            "contract": contract,
            "name": result.get("name"),
            "symbol": symbol,
            "snapshot_block": block,
            "snapshot_time": snapshot_time,
            "total_holders": len(holder_list),
            "total_nfts": total_nfts,
            "holders": holder_list,
        }, f, indent=2)

    # Holders CSV (airdrop-ready)
    csv_path = os.path.join(coll_dir, f"{symbol}_holders.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["wallet", "nft_count", "contract", "snapshot_block", "snapshot_time"])
        for h in sorted(holder_list, key=lambda x: x["nft_count"], reverse=True):
            writer.writerow([h["address"], h["nft_count"], contract, block, snapshot_time])

    # Summary
    summary_path = os.path.join(coll_dir, f"{symbol}_summary.json")
    result["status"] = "complete"
    with open(summary_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"  ✅ Saved holders.json + holders.csv + summary.json")
    return result


def main():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    block = get_block()

    print(f"🚀 Dogechain NFT Snapshot — {SNAPSHOT_TIME}")
    print(f"   Block: {block:,}")
    print(f"   Output: {SNAPSHOT_DIR}")

    # Determine collections
    if len(sys.argv) >= 3 and sys.argv[1].startswith("0x"):
        collections = [(sys.argv[1], sys.argv[2])]
    else:
        collections = KNOWN_COLLECTIONS

    print(f"   Collections: {len(collections)}")

    all_results = []
    for contract, symbol in collections:
        try:
            result = snapshot_collection(contract, symbol, block, SNAPSHOT_TIME)
            all_results.append(result)
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            all_results.append({"contract": contract, "symbol": symbol, "status": f"error: {e}"})

    # Master index
    index_path = os.path.join(SNAPSHOT_DIR, "SNAPSHOT_INDEX.json")
    with open(index_path, "w") as f:
        json.dump({
            "snapshot_time": SNAPSHOT_TIME,
            "snapshot_block": block,
            "chain": "Dogechain (2000)",
            "total_collections": len(all_results),
            "successful": sum(1 for r in all_results if r.get("status") == "complete"),
            "collections": all_results,
        }, f, indent=2)

    # Summary
    print(f"\n{'='*60}")
    print(f"{'Symbol':<16} {'Supply':>8} {'Holders':>8} {'NFTs':>8} {'Status'}")
    print("-" * 60)
    for r in all_results:
        supply = str(r.get("total_supply", "?"))[:8]
        holders = f"{r.get('holder_count', 0):,}" if r.get("holder_count") else "0"
        nfts = f"{r.get('total_nfts_held', 0):,}" if r.get("total_nfts_held") else "0"
        print(f"{r['symbol']:<16} {supply:>8} {holders:>8} {nfts:>8} {r.get('status', '?')}")

    complete = sum(1 for r in all_results if r.get("status") == "complete")
    print(f"\n✅ {complete}/{len(all_results)} collections snapshot successfully")
    print(f"📁 Index: {index_path}")


if __name__ == "__main__":
    main()
