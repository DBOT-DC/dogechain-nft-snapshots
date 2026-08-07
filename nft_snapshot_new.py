
import json, urllib.request, time, os, csv
from datetime import datetime, timezone

RPC = "https://rpc.dogechain.dog"
EXPLORER = "https://explorer.dogechain.dog/api"
SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
SNAPSHOT_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

NEW_NFTS = [
    {"address": "0x92b995f34cbf637d59c66782e90dfec3ce3c202b", "symbol": "DTOOLS NFT"},
    {"address": "0x221ebe2243d3a4be8b7d53a98c5aebbc37bd7c33", "symbol": "TDH NFT"},
    {"address": "0x011f614b13ef08b905a2ae68443f6344cce32046", "symbol": "DG"},
    {"address": "0xd7f68f4349527dae381233daa120bb42e310c986", "symbol": "Kimon"},
    {"address": "0xafa5f9313f1f2b599173f24807a882f498be118c", "symbol": "hMERK"},
    {"address": "0x45944dd5145ac7815d29c8c5d7c7f1801a7aa6c3", "symbol": "FFNFTS"},
    {"address": "0xfb035ab15a174f6c0702901e7b2a24db8f8cd026", "symbol": "DCC"},
    {"address": "0xf497d4826c3585cee69a0fd3b71b057d7056f64a", "symbol": "MASON"},
    {"address": "0x870fb39328958d9d363ddb88c2e6a4a32a5bef11", "symbol": "BDKC"},
    {"address": "0x474faddd73b6ff260efd281b4eb375a6fd7ea9bc", "symbol": "DCP"},
    {"address": "0x49b958133b53f3a0ebfb9c81d6a080b1439174d2", "symbol": "ED"},
    {"address": "0x5b68749a85e84cbf3a04526d87296d4d988462dc", "symbol": "WTN"},
    {"address": "0xbaff37aa3667abb92d9d10c2b0a1d4128033c4df", "symbol": "DAYC"},
    {"address": "0x82831e9565cb574375596efc090da465283e22a4", "symbol": "ALGB-FARM"},
    {"address": "0xe1b87c4a363be9158323c47c4fdaa70e6dccfe05", "symbol": "McRIB Pix"},
    {"address": "0x58ad22348216bdb0a3a544ad365ee82187d0e8aa", "symbol": "CChimp"},
    {"address": "0xfed9e67c30c76e416371b4763fc02f8a33e52b5d", "symbol": "DDB"},
    {"address": "0xe83c2021550b17169bd2d608c51ba6a2bea0f350", "symbol": ".DC"},
    {"address": "0x491c67db959bda22e1061b43693ea3699675f080", "symbol": "GMNFT"},
    {"address": "0x0af878360b48b5f51f4e919f3cc1ec08b78627ad", "symbol": ".DOGE"},
    {"address": "0x121c02c851cd0434a1bfc584ea9895b6aa2c114b", "symbol": "DTOOLS2023"}
]

def rpc_call(method, params):
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(RPC, data=payload, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())

def get_token_name(addr):
    try:
        r = rpc_call("eth_call", [{"to": addr, "data": "0x06fdde03"}, "latest"])
        hex_bytes = bytes.fromhex(r["result"][2:])
        length = int.from_bytes(hex_bytes[32:64], 'big')
        return hex_bytes[64:64+length].decode('utf-8', errors='replace').strip('\x00')
    except:
        return "?"

def get_token_symbol(addr):
    try:
        r = rpc_call("eth_call", [{"to": addr, "data": "0x95d89b41"}, "latest"])
        hex_bytes = bytes.fromhex(r["result"][2:])
        length = int.from_bytes(hex_bytes[32:64], 'big')
        return hex_bytes[64:64+length].decode('utf-8', errors='replace').strip('\x00')
    except:
        return "?"

def get_total_supply(addr):
    try:
        r = rpc_call("eth_call", [{"to": addr, "data": "0x18160ddd"}, "latest"])
        return int(r["result"], 16)
    except:
        return 0

def get_holders(addr, page=1, offset=10000):
    url = f"{EXPLORER}?module=token&action=getTokenHolders&contractaddress={addr}&page={page}&offset={offset}"
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    return data.get("result", [])

print(f"\n🚀 Quick NFT Snapshot (Holders Only) — {SNAPSHOT_TIME}")
print(f"   New collections to process: {len(NEW_NFTS)}\n")

results = []
for nft in NEW_NFTS:
    addr = nft["address"]
    symbol = nft["symbol"]
    
    name = get_token_name(addr)
    sym = get_token_symbol(addr)
    supply = get_total_supply(addr)
    
    print(f"============================================================")
    print(f"📸 {symbol} ({addr[:10]}...)")
    print(f"============================================================")
    print(f"  {name} ({sym}) | Supply: {supply:,}")
    
    # Get holders
    holders_raw = get_holders(addr)
    holders = {}
    for h in holders_raw:
        h_addr = h.get("address", "").lower()
        try:
            balance = int(h.get("value", "0"))
        except:
            balance = 0
        if balance > 0:
            holders[h_addr] = balance
    
    print(f"  {len(holders)} holders, {sum(holders.values()):,} NFTs")
    
    # Save
    col_dir = os.path.join(SNAPSHOT_DIR, symbol)
    os.makedirs(col_dir, exist_ok=True)
    
    # wallet_tokens.json (wallet -> count)
    with open(os.path.join(col_dir, "wallet_tokens.json"), 'w') as f:
        json.dump(holders, f, indent=2)
    
    # wallets.csv
    with open(os.path.join(col_dir, "wallets.csv"), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["wallet", "nft_count"])
        for w, c in sorted(holders.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([w, c])
    
    # summary.json
    summary = {
        "symbol": symbol, "name": name, "address": addr,
        "supply": supply, "holders": len(holders),
        "total_nfts": sum(holders.values()),
        "snapshot_time": SNAPSHOT_TIME
    }
    with open(os.path.join(col_dir, "summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    
    results.append(summary)
    print(f"  ✅ wallet_tokens.json + wallets.csv + summary.json")
    time.sleep(0.3)

print(f"\n======================================================================")
print(f"✅ {len(results)}/{len(NEW_NFTS)} new collections snapshotted")
print(f"📁 {SNAPSHOT_DIR}\n")

# Print summary table
print(f"{'Symbol':<14} {'Supply':>8} {'Holders':>8} {'NFTs':>8}")
print("-"*42)
for r in sorted(results, key=lambda x: x['holders'], reverse=True):
    print(f"{r['symbol']:<14} {r['supply']:>8,} {r['holders']:>8} {r['total_nfts']:>8,}")
