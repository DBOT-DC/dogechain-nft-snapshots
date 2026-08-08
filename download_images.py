#!/usr/bin/env python3
"""
Download NFT images for all collections with accessible metadata.
Fetches tokenURI for every token ID, downloads the image, saves to disk.

For IPFS URIs: uses public gateways (ipfs.io, cloudflare, w3s.link)
For Arweave URIs: uses arweave.net gateway
For HTTP URIs: direct download
For GitHub raw: direct download
"""
import json, os, sys, time, requests, base64, re
from concurrent.futures import ThreadPoolExecutor, as_completed

RPC = "https://rpc.dogechain.dog"
SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nft_images")
SNAPSHOT_TIME = "2026-08-07"

IPFS_GATEWAYS = [
    "https://ipfs.io/ipfs/",
    "https://w3s.link/ipfs/",
    "https://cloudflare-ipfs.com/ipfs/",
]

# Collections with confirmed accessible metadata
COLLECTIONS = {
    # IPFS collections
    "0xd38b22794b308a2e55808a13d1e6a80c4be94fd5": "RDP",
    "0xb6e6b0167ce72057f6ac28cb5fd836896b4d084e": "DOGE-BEARS",
    "0xbeae0fd8ccecc76afcc137d89f2b006e8c543c84": "DOGEPUNKS",
    "0x63309a2b8f507f667da75c24013a2e18904cc19d": "SOVPUNKS",
    "0x6b351dc4439a9ac313f6f4d76c51f2d3717f3101": "SEADOGS",
    "0x49ffa5d11cb54a6541e33dc04951b1ffdfaa2852": "CYBERDOGS",
    "0x5f595ff1830b0bd9e67ae6376ad80598876cc34f": "MONOS",
    "0x8743b1cec8939e456f05194503fbb6500a3ba67d": "FTH",
    "0xb3c75f465f6236985c0a0ce5013c5ae7ae2748e5": "DOGEDOODLE",
    "0x81c3164939f515134f6be6b6f9d295887df6554b": "ASTRO",
    "0xf497d4826c3585cee69a0fd3b71b057d7056f64a": "MASON",
    "0xfed9e67c30c76e416371b4763fc02f8a33e52b5d": "DDB",
    "0x45944dd5145ac7815d29c8c5d7c7f1801a7aa6c3": "FFNFTS",
    "0x5b68749a85e84cbf3a04526d87296d4d988462dc": "WTN",
    "0x121c02c851cd0434a1bfc584ea9895b6aa2c114b": "DTOOLS-2023",
    # Arweave collections
    "0x1836c33b9350d18304e0f701de777cc7501e9c2a": "DH",
    "0x221ebe2243d3a4be8b7d53a98c5aebbc37bd7c33": "TDH-NFT",
    # GitHub raw collections
    "0x58ad22348216bdb0a3a544ad365ee82187d0e8aa": "CCHIMP",
    "0x870fb39328958d9d363ddb88c2e6a4a32a5bef11": "BDKC2",
    "0xfb035ab15a174f6c0702901e7b2a24db8f8cd026": "DCC2",
    "0xf6ee4a3f8529a6b20b8f4792a0ea20a419ba21f5": "PIXELFROGS",
    # HTTP collections (accessible)
    "0x9b291b0e9c78ce1c94b701d3d9faad349c4be341": "DOGE-BLINDERS",
    "0xafa5f9313f1f2b599173f24807a882f498be118c": "hMERK",
    "0xa2e57fa488cf272c87b066e2a3e0672c0c58784d": "RAT",
    "0xbaff37aa3667abb92d9d10c2b0a1d4128033c4df": "DAYC2",
}


def rpc_call(method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    for attempt in range(3):
        try:
            req = requests.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            # Use requests directly
            r = requests.post(RPC, data=body, headers={"Content-Type": "application/json"}, timeout=30)
            return r.json().get("result")
        except:
            time.sleep(1 * (attempt + 1))
    return None


def decode_string(hex_result):
    if not hex_result or hex_result == "0x":
        return ""
    try:
        hb = bytes.fromhex(hex_result[2:])
        if len(hb) < 64:
            return ""
        length = int.from_bytes(hb[32:64], "big")
        return hb[64:64+length].decode("utf-8", errors="replace").strip("\x00")
    except:
        return ""


def get_token_uri(contract, token_id):
    """Get tokenURI for a specific token ID."""
    data_call = "0xc87b56dd" + f"{token_id:064x}"
    result = rpc_call("eth_call", [{"to": contract, "data": data_call}, "latest"])
    return decode_string(result)


def get_supply(contract):
    result = rpc_call("eth_call", [{"to": contract, "data": "0x18160ddd"}, "latest"])
    if result and result != "0x":
        return int(result, 16)
    return 0


def resolve_ipfs(uri):
    """Convert ipfs:// URI to a gateway URL."""
    cid_path = uri.replace("ipfs://", "")
    # Try each gateway, return first that works
    for gateway in IPFS_GATEWAYS:
        url = gateway + cid_path
        try:
            r = requests.head(url, timeout=10, allow_redirects=True)
            if r.status_code == 200:
                return url
        except:
            pass
    # Default to ipfs.io even if HEAD failed (some return 404 on HEAD but work on GET)
    return IPFS_GATEWAYS[0] + cid_path


def fetch_metadata(uri):
    """Fetch metadata JSON from URI."""
    if not uri:
        return None
    
    if uri.startswith("data:"):
        # On-chain data URI
        if "base64," in uri:
            b64 = uri.split("base64,")[1]
            try:
                return json.loads(base64.b64decode(b64).decode("utf-8"))
            except:
                return None
        return None
    
    if uri.startswith("ipfs://"):
        url = resolve_ipfs(uri)
    elif uri.startswith("arweave"):
        tx = uri.split("/")[-1] if "/" in uri else uri.replace("arweave://", "")
        url = f"https://arweave.net/{tx}"
    else:
        url = uri
    
    try:
        r = requests.get(url, timeout=20, allow_redirects=True)
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "")
            if "json" in content_type or r.text.strip().startswith("{"):
                return r.json()
            elif r.text.strip().startswith("["):
                return r.json()
            else:
                return {"raw": r.text[:200]}
    except:
        pass
    return None


def download_image(url, filepath, timeout=30):
    """Download an image to a file."""
    # Resolve IPFS/arweave if needed
    if url and url.startswith("ipfs://"):
        url = resolve_ipfs(url)
    
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True, stream=True)
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "")
            # Determine extension
            if "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"
            elif "gif" in content_type:
                ext = ".gif"
            elif "svg" in content_type:
                ext = ".svg"
            elif "jpeg" in content_type or "jpg" in content_type:
                ext = ".jpg"
            else:
                # Try to guess from URL
                if ".png" in url:
                    ext = ".png"
                elif ".gif" in url:
                    ext = ".gif"
                elif ".webp" in url:
                    ext = ".webp"
                else:
                    ext = ".jpg"
            
            final_path = filepath + ext
            with open(final_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            return ext
    except:
        pass
    return None


def process_collection(addr, symbol):
    """Download all images for a collection."""
    col_dir = os.path.join(IMAGE_DIR, symbol)
    os.makedirs(col_dir, exist_ok=True)
    
    supply = get_supply(addr)
    if supply == 0:
        # Try loading from summary
        for sf in ["summary.json", f"{symbol}_summary.json"]:
            path = os.path.join(SNAPSHOT_DIR, symbol, sf)
            if os.path.exists(path):
                with open(path) as f:
                    supply = json.load(f).get("total_supply", 0)
                break
    
    # Cap large collections to avoid extreme downloads
    max_tokens = min(supply, 10000)
    
    print(f"  {symbol}: {supply:,} supply, downloading up to {max_tokens}...", flush=True)
    
    # Save metadata + track downloads
    metadata_log = []
    downloaded = 0
    failed = 0
    
    for token_id in range(1, max_tokens + 1):
        # Check if already downloaded
        existing = [f for f in os.listdir(col_dir) if f.startswith(f"{token_id}.")]
        if existing:
            downloaded += 1
            continue
        
        # Get token URI
        uri = get_token_uri(addr, token_id)
        if not uri:
            # Try token ID 0
            if token_id == 1:
                uri = get_token_uri(addr, 0)
            if not uri:
                failed += 1
                continue
        
        # Fetch metadata
        meta = fetch_metadata(uri)
        if not meta:
            failed += 1
            continue
        
        # Extract image URL
        image_url = meta.get("image", meta.get("image_url", ""))
        
        # Some IPFS images need gateway resolution
        if image_url and image_url.startswith("ipfs://"):
            pass  # download_image handles this
        
        # Download image
        if image_url:
            filepath = os.path.join(col_dir, str(token_id))
            ext = download_image(image_url, filepath)
            if ext:
                downloaded += 1
                metadata_log.append({
                    "token_id": token_id,
                    "uri": uri,
                    "image": image_url,
                    "file": f"{token_id}{ext}",
                    "name": meta.get("name", ""),
                })
            else:
                failed += 1
        else:
            # Some metadata might have image in different field
            image_url = meta.get("image_data", meta.get("animation_url", ""))
            if image_url:
                filepath = os.path.join(col_dir, str(token_id))
                ext = download_image(image_url, filepath)
                if ext:
                    downloaded += 1
                else:
                    failed += 1
            else:
                failed += 1
        
        # Rate limiting
        if token_id % 50 == 0:
            print(f"    {symbol}: {token_id}/{max_tokens} done ({downloaded} images, {failed} failed)", flush=True)
            # Save progress
            with open(os.path.join(col_dir, "_metadata.json"), "w") as f:
                json.dump(metadata_log, f, indent=2)
        
        time.sleep(0.1)  # 10 req/s
    
    # Save final metadata
    with open(os.path.join(col_dir, "_metadata.json"), "w") as f:
        json.dump(metadata_log, f, indent=2)
    
    # Save collection summary
    with open(os.path.join(col_dir, "_summary.json"), "w") as f:
        json.dump({
            "symbol": symbol,
            "address": addr,
            "supply": supply,
            "downloaded": downloaded,
            "failed": failed,
            "snapshot_date": SNAPSHOT_TIME,
        }, f, indent=2)
    
    print(f"  {symbol}: DONE — {downloaded} images, {failed} failed", flush=True)
    return {"symbol": symbol, "supply": supply, "downloaded": downloaded, "failed": failed}


def main():
    print(f"🐕 NFT Image Archiver — {SNAPSHOT_TIME}", flush=True)
    print(f"   {len(COLLECTIONS)} collections to process\n", flush=True)
    
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    results = []
    for i, (addr, symbol) in enumerate(COLLECTIONS.items(), 1):
        print(f"[{i}/{len(COLLECTIONS)}]", flush=True)
        try:
            r = process_collection(addr, symbol)
            results.append(r)
        except Exception as e:
            print(f"  ❌ {symbol}: {e}", flush=True)
            results.append({"symbol": symbol, "error": str(e)})
    
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
