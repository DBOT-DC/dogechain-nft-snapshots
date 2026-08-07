#!/usr/bin/env python3
"""Check which of the 50 token addresses from page 1 are ERC-721."""
import json, urllib.request, time

EXPLORER = "https://explorer.dogechain.dog/api"

def api_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read())

addrs = [
    "0x948eed4490833d526688fd1e5ba0b9b35cd2c32e",
    "0x7b4328c127b85369d9f82ca0503b000d09cf9180",
    "0xe3fca919883950c5cd468156392a6477ff5d18de",
    "0xb7ddc6414bf4f5515b52d8bdd69973ae205ff101",
    "0x9913cc60be83db3ffcefb8ca7014e9d6c26ccadf",
    "0xcfa0b0021cb33ec23ee1edd18248ec448a66d0c2",
    "0x1e1026ba0810e6391b0f86afa8a9305c12713b66",
    "0xd3fd6945515e854f58235d91604af288358ffdc1",
    "0x2f90907fd1dc1b7a484b6f31ddf012328c2bab28",
    "0x8530b66ca3ddf50e0447eae8ad7ea7d5e62762ed",
    "0x001c2ef10c26f0d65d9fa7d173071049562999f5",
    "0x4c14c7c1fb471662575b256767ff0fb3a2219515",
    "0xf412636228e45b773ae408c0cd47e878e3c3689a",
    "0xffceb75b722b96713774819d9e45d2d8f777fcb8",
    "0x99510e7ed4c7b5d8d5e0b735e470e127b4488a7e",
    "0xd35b642ca72b5c94a2464f0bf666d8542c39f7e9",
    "0xa6d7137af64280e3eb8715ab6766740984dd35e7",
    "0xc1e78b5fbb70f518467ef4052eea567568e95403",
    "0x81b15e26daa30379ec1a0f4d1e4a454a42637355",
    "0x651757f155edbf1ab1e842923e224b336582def5",
    "0x233abdaf75d1bde0ba820b596e270d2144e473eb",
    "0x765277eebeca2e31912c9946eae1021199b39c61",
    "0x5bf60ea5cf2383f407f09cf38378176298238a6c",
    "0x6fc4563460d5f45932c473334d5c1c5b4aea0e01",
    "0xc534cef5159cba8da4306bbb3a63fb9f4a5e1eb1",
    "0xb9fcaa7590916578087842e017078d7797fa18d0",
    "0x1df5c9b7789bd1416d005c15a42762481c95edc2",
    "0xf197c706c872e2bb90dbc7f04816d6a8320c700c",
    "0x446eb7770d4e34772b75b3c795d2c2cd00a19808",
    "0xb30cd0dd2231a51ea15292f68a50e329e3b831fd",
    "0x58278939723e6d9bed6ed59fbf2a5419066e29f2",
    "0xa83a2d1cf73f163855a1ee447df2fe7d242112ad",
    "0x6cf5a9efb42b2068177a565e094457611721275d",
    "0x2cae51f077a795deda55ecf89a24da15de16f614",
    "0x332254235e55433b195eec743ae1e770db7057ae",
    "0xa0eb9a6063df850f611aa69c60025c7f8eb4d6ee",
    "0x5cc1d860c0d1a695912e5aedc5cf3ccf5af83eca",
    "0xebc46cfc26d2872f9300f21fbc34ca33a12695ab",
    "0x5f2f0fd21bc656e98ef91136910624b9df9c1fd4",
    "0x769b1442f0fbae3525647c9b81126f62f6a64ff8",
    "0x8a764cf73438de795c98707b07034e577af54825",
    "0x6e55472109e6abe4054a8e8b8d9edffcb31032c5",
    "0xaaad8509134229d4d0e509add54ce5c2e870b059",
    "0x0b012055f770ae7bb7a8303968a7fb6088a2296e",
    "0x72ab1babed0502b08225fa1ef777fa673d82ee3e",
    "0x3abde71c12b7f34bc33d7d2c5f3236393eac7880",
    "0x2be0096b24343549e34224aa9aa297e99961023d",
    "0x49cd2140e36fa56ef04c56991843b6926b233b7b",
    "0x16623a42b2018dab973b275f084d7cce8c9efb22",
    "0x70af23749e2ad56903a498495832df3a4fd7b59b",
]

nfts = []
erc20s = []
for addr in addrs:
    try:
        data = api_get(f"{EXPLORER}?module=token&action=getToken&contractaddress={addr}")
        info = data.get("result", {})
        ttype = info.get("type", "?")
        name = info.get("name", "?")
        sym = info.get("symbol", "?")
        supply = info.get("totalSupply", "?")
        if "721" in ttype:
            nfts.append({"address": addr, "name": name, "symbol": sym, "supply": supply})
            print(f"  NFT: {sym:>12} | {name[:30]:>30} | {addr}")
        else:
            erc20s.append(f"{sym}({ttype})")
    except Exception as e:
        print(f"  ERR: {addr[:12]}... {e}")
    time.sleep(0.15)

print(f"\nNFTs: {len(nfts)}, ERC-20s/Other: {len(erc20s)}")

with open("/Users/penny/.openclaw-telegram/workspace/nft-snapshot/page1_nfts.json", "w") as f:
    json.dump(nfts, f, indent=2)
print("Saved to page1_nfts.json")
