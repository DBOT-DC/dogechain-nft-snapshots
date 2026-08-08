#!/usr/bin/env python3
"""
Fast NFT image archiver — uses cached base CIDs to skip per-token RPC calls.
Downloads metadata + images in parallel from IPFS/HTTP gateways.
"""
import json, os, sys, time, requests, base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nft_images")
SNAPSHOT_TIME = "2026-08-07"

IPFS_GATEWAYS = [
    "https://ipfs.io/ipfs/",
    "https://w3s.link/ipfs/",
    "https://cloudflare-ipfs.com/ipfs/",
    "https://dweb.link/ipfs/",
]

# Pre-discovered base URIs (from tokenURI(1) calls)
# Format: symbol -> (address, base_uri_template, supply, uri_suffix)
# uri_template uses {} where token ID goes
COLLECTIONS = [
    # IPFS folder-based (most common pattern: ipfs://CID/{id}.json)
    {"symbol": "RDP",         "addr": "0xd38b22794b308a2e55808a13d1e6a80c4be94fd5", "supply": 10000, "uri_pattern": "ipfs://bafybeiad2qisjt6a3gt2muzc33slhhlq2uyx62jzj5mueiespg5fgz74m4/{}.json"},
    {"symbol": "DOGE-BEARS",  "addr": "0xb6e6b0167ce72057f6ac28cb5fd836896b4d084e", "supply": 10000, "uri_pattern": "ipfs://bafybeiexbr7264djrc37domydv65yzkkmnm6vmurrhiwvmpfjfhviq7qy4/{}.json"},
    {"symbol": "DOGEPUNKS",   "addr": "0xbeae0fd8ccecc76afcc137d89f2b006e8c543c84", "supply": 10000, "uri_pattern": "ipfs://bafybeibl2xlwzvhoifc6saka4xhq6petfkv36v4sy33onwewomqjxtddxm/{}"},
    {"symbol": "SOVPUNKS",    "addr": "0x63309a2b8f507f667da75c24013a2e18904cc19d", "supply": 2408,  "uri_pattern": "ipfs://bafybeicmssdadxrqet2t6nap5swg4v7j5d7wkgww3qb7jayl4xuifjilga/{}"},
    {"symbol": "SEADOGS",     "addr": "0x6b351dc4439a9ac313f6f4d76c51f2d3717f3101", "supply": 1446,  "uri_pattern": "ipfs://QmRg6oBmedhE66x539HdqeLjrwK79FjNJzfWp2gDdbG5h2/{}.json"},
    {"symbol": "CYBERDOGS",   "addr": "0x49ffa5d11cb54a6541e33dc04951b1ffdfaa2852", "supply": 3333,  "uri_pattern": "ipfs://QmXcQ5u7q7Jv5zrzEyu8RCKRCRMiNt48TVm9CALQZLZPi5/{}.json"},
    {"symbol": "MONOS",       "addr": "0x5f595ff1830b0bd9e67ae6376ad80598876cc34f", "supply": 2449,  "uri_pattern": "ipfs://QmUmbask76R2CEuEPdwSEWHy9PmAvP6sABZLaU81T8u5uS/{}.json"},
    {"symbol": "FTH",         "addr": "0x8743b1cec8939e456f05194503fbb6500a3ba67d", "supply": 5000,  "uri_pattern": "ipfs://bafybeih2hv6lbydmen3ka4h2lauqgglmnyk4gqolagpk7rhspds2xintdy/{}"},
    {"symbol": "DOGEDOODLE",  "addr": "0xb3c75f465f6236985c0a0ce5013c5ae7ae2748e5", "supply": 1800,  "uri_pattern": "ipfs://QmdW2E2b8u5EJbGzCqDSQh5RdQBBndzsVonzH4TpLKvNSL/{}.json"},
    {"symbol": "ASTRO",       "addr": "0x81c3164939f515134f6be6b6f9d295887df6554b", "supply": 231,   "uri_pattern": "ipfs://QmTpXxVuaHnPaTDLnB8c6FAgdbX4zsgcXPVo8x5uvTci9R/{}.json"},
    {"symbol": "MASON",       "addr": "0xf497d4826c3585cee69a0fd3b71b057d7056f64a", "supply": 362,   "uri_pattern": "ipfs://QmRkXUCX59DquAKpiSidaocNSZDtyixQkWVv5y7bjswArH/{}"},
    {"symbol": "DDB",         "addr": "0xfed9e67c30c76e416371b4763fc02f8a33e52b5d", "supply": 3333,  "uri_pattern": "ipfs://QmXucZ4Su3AfP5jc9vRRLaRhTkZHdEVuQCKReeAB8wRAiZ/{}"},
    {"symbol": "FFNFTS",      "addr": "0x45944dd5145ac7815d29c8c5d7c7f1801a7aa6c3", "supply": 482,   "uri_pattern": "ipfs://QmZ5ae5Cg2pzxFsZatAuDuUnj5Dcap1VxFdUTqmysPC3Ep/{}"},
    {"symbol": "WTN",         "addr": "0x5b68749a85e84cbf3a04526d87296d4d988462dc", "supply": 789,   "uri_pattern": "ipfs://QmbQ8GBkDAMAYVLdmn3uR6rvvnhuLy1P8oGb3GdUvkR7BX/{}.json"},
    {"symbol": "DTOOLS-2023", "addr": "0x121c02c851cd0434a1bfc584ea9895b6aa2c114b", "supply": 75,    "uri_pattern": "ipfs://bafybeicsc5sugujb5p4h5im5xzfmradmpatj52yodb24b7ormf75r3pdfm/{}.json"},
    # Arweave
    {"symbol": "DH",          "addr": "0x1836c33b9350d18304e0f701de777cc7501e9c2a", "supply": 3371,  "uri_pattern": "https://arweave.net/xu3Zu0KJHlKlKc1inhX5DBVccYM9GZpofFsKnFuxVlg/{}.json"},
    {"symbol": "TDH-NFT",     "addr": "0x221ebe2243d3a4be8b7d53a98c5aebbc37bd7c33", "supply": 3620,  "uri_pattern": "https://arweave.net/xu3Zu0KJHlKlKc1inhX5DBVccYM9GZpofFsKnFuxVlg/{}.json"},
    # GitHub raw
    {"symbol": "CCHIMP",      "addr": "0x58ad22348216bdb0a3a544ad365ee82187d0e8aa", "supply": 3666,  "uri_pattern": "https://raw.githubusercontent.com/oliviachef/chimpers/main/{}.json"},
    {"symbol": "BDKC2",       "addr": "0x870fb39328958d9d363ddb88c2e6a4a32a5bef11", "supply": 1732,  "uri_pattern": "https://raw.githubusercontent.com/oliviachef/BKYC/main/metadata/{}.json"},
    {"symbol": "DCC2",        "addr": "0xfb035ab15a174f6c0702901e7b2a24db8f8cd026", "supply": 3666,  "uri_pattern": "https://raw.githubusercontent.com/oliviachef/chimpers/main/{}.json"},
    {"symbol": "PIXELFROGS",  "addr": "0xf6ee4a3f8529a6b20b8f4792a0ea20a419ba21f5", "supply": 666,   "uri_pattern": "https://raw.githubusercontent.com/imzensuke/Frogs/Frogs/metadata/{}.json"},
    # HTTP
    {"symbol": "DOGE-BLINDERS","addr": "0x9b291b0e9c78ce1c94b701d3d9faad349c4be341","supply": 10000, "uri_pattern": "https://bafybeidltf4kklyiht5kenvh4vjzsr3pijpzduwhdujzt5xh3szyo25nzi.ipfs.w3s.link/{}.json"},
    {"symbol": "DAYC2",       "addr": "0xbaff37aa3667abb92d9d10c2b0a1d4128033c4df", "supply": 10000, "uri_pattern": "https://bafybeif22hdvvdl77m3jak7jurcets2jmroeg4nhj3n3cu6pvoiby6n7di.ipfs.nftstorage.link/{}.json"},
]


def ipfs_url(cid_path):
    """Convert IPFS path to a gateway URL, trying multiple gateways."""
    return IPFS_GATEWAYS[0] + cid_path


def fetch_url(url, timeout=20, retries=2):
    """Fetch URL with retries."""
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, timeout=timeout, allow_redirects=True)
            if r.status_code == 200:
                return r
        except:
            time.sleep(0.5 * (attempt + 1))
    return None


def resolve_ipfs_with_fallbacks(cid_path, timeout=15):
    """Try multiple IPFS gateways, return content from first that works."""
    for gateway in IPFS_GATEWAYS:
        url = gateway + cid_path
        r = fetch_url(url, timeout=timeout)
        if r:
            return r
    return None


def download_token_image(token_id, uri_pattern, col_dir):
    """Download a single token's image. Returns (token_id, success, filepath)."""
    # Check if already downloaded
    for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]:
        if os.path.exists(os.path.join(col_dir, f"{token_id}{ext}")):
            return (token_id, "exists", None)
    
    uri = uri_pattern.format(token_id)
    
    # Fetch metadata
    if uri.startswith("ipfs://"):
        cid_path = uri.replace("ipfs://", "")
        r = resolve_ipfs_with_fallbacks(cid_path)
    else:
        r = fetch_url(uri)
    
    if not r:
        return (token_id, "meta_failed", None)
    
    # Parse metadata
    try:
        meta = r.json()
    except:
        return (token_id, "meta_parse_failed", None)
    
    image_url = meta.get("image", meta.get("image_url", ""))
    if not image_url:
        return (token_id, "no_image", None)
    
    # Resolve image URL
    if image_url.startswith("ipfs://"):
        img_cid = image_url.replace("ipfs://", "")
        img_r = resolve_ipfs_with_fallbacks(img_cid)
    elif image_url.startswith("arweave"):
        tx = image_url.split("/")[-1]
        img_r = fetch_url(f"https://arweave.net/{tx}")
    else:
        img_r = fetch_url(image_url)
    
    if not img_r or img_r.status_code != 200:
        return (token_id, "img_failed", None)
    
    # Determine extension from content-type
    ct = img_r.headers.get("content-type", "")
    if "png" in ct: ext = ".png"
    elif "webp" in ct: ext = ".webp"
    elif "gif" in ct: ext = ".gif"
    elif "svg" in ct: ext = ".svg"
    elif "jpeg" in ct or "jpg" in ct: ext = ".jpg"
    else:
        if ".png" in image_url: ext = ".png"
        elif ".gif" in image_url: ext = ".gif"
        elif ".webp" in image_url: ext = ".webp"
        elif ".svg" in image_url: ext = ".svg"
        else: ext = ".jpg"
    
    filepath = os.path.join(col_dir, f"{token_id}{ext}")
    with open(filepath, "wb") as f:
        f.write(img_r.content)
    
    return (token_id, "ok", filepath)


def process_collection(coll, max_workers=6):
    symbol = coll["symbol"]
    supply = coll["supply"]
    uri_pattern = coll["uri_pattern"]
    
    col_dir = os.path.join(IMAGE_DIR, symbol)
    os.makedirs(col_dir, exist_ok=True)
    
    max_tokens = min(supply, 10000)
    print(f"  {symbol}: {supply:,} supply, {max_tokens} to download ({max_workers} workers)", flush=True)
    
    ok = 0
    failed = 0
    exists = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for token_id in range(1, max_tokens + 1):
            f = executor.submit(download_token_image, token_id, uri_pattern, col_dir)
            futures[f] = token_id
        
        done = 0
        for future in as_completed(futures):
            tid, status, filepath = future.result()
            done += 1
            if status == "ok":
                ok += 1
            elif status == "exists":
                exists += 1
            else:
                failed += 1
            
            if done % 100 == 0:
                print(f"    {symbol}: {done}/{max_tokens} ({ok} new, {exists} cached, {failed} failed)", flush=True)
    
    # Save summary
    with open(os.path.join(col_dir, "_summary.json"), "w") as f:
        json.dump({
            "symbol": symbol, "address": coll["addr"],
            "supply": supply, "downloaded": ok + exists,
            "failed": failed, "snapshot_date": SNAPSHOT_TIME,
        }, f, indent=2)
    
    total = ok + exists
    print(f"  {symbol}: DONE — {total} images, {failed} failed", flush=True)
    return {"symbol": symbol, "supply": supply, "downloaded": total, "failed": failed}


def main():
    print(f"🐕 Fast NFT Image Archiver — {SNAPSHOT_TIME}", flush=True)
    print(f"   {len(COLLECTIONS)} collections to process", flush=True)
    print(f"   Pattern: metadata → extract image URL → download\n", flush=True)
    
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    # Process smallest collections first (quick wins)
    sorted_cols = sorted(COLLECTIONS, key=lambda c: c["supply"])
    
    results = []
    for i, coll in enumerate(sorted_cols, 1):
        print(f"[{i}/{len(sorted_cols)}]", flush=True)
        try:
            r = process_collection(coll)
            results.append(r)
        except Exception as e:
            print(f"  ❌ {coll['symbol']}: {e}", flush=True)
            results.append({"symbol": coll["symbol"], "error": str(e)})
    
    print(f"\n{'='*60}", flush=True)
    total_dl = sum(r.get("downloaded", 0) for r in results)
    total_fail = sum(r.get("failed", 0) for r in results)
    print(f"TOTAL: {total_dl} images downloaded, {total_fail} failed", flush=True)
    print(f"\n{'Symbol':<16} {'Supply':>8} {'Images':>8} {'Failed':>8}", flush=True)
    print("-" * 44, flush=True)
    for r in sorted(results, key=lambda x: x.get("downloaded", 0), reverse=True):
        if "error" in r:
            print(f"{r['symbol']:<16} ERROR", flush=True)
        else:
            print(f"{r['symbol']:<16} {r.get('supply',0):>8} {r['downloaded']:>8} {r['failed']:>8}", flush=True)


if __name__ == "__main__":
    main()
