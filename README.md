# Dogechain NFT Snapshots

Complete NFT collection census for Dogechain mainnet. Full chain scan of 62.5M blocks identified all ERC-721 (DOG-721) contracts via Transfer event analysis. Every legitimate collection snapshotted with wallet-level holder data and token ID → owner mappings.

## Census Summary

- **42 collections** snapshotted (of 57 total ERC-721 contracts found; 15 excluded as spam/test/duplicates)
- **37 collections** have full token ID → owner mappings (97,152 tokens)
- **5 collections** have holder-level data only (contracts lack ERC721Enumerable)
- **11,305 holder records** across all collections (includes duplicates across collections)
- Snapshot date: August 7, 2026
- Block: ~62,535,818

## Methodology

1. **Chain Scan**: `eth_getLogs` across 62.5M blocks in 5K windows, filtering for ERC-721 Transfer events (4-topic signature: `Transfer(address,address,uint256)` with tokenId as indexed topic3)
2. **ERC-721 Verification**: `supportsInterface(0x80ac58cd)` via RPC for each candidate contract
3. **Metadata**: `name()`, `symbol()`, `totalSupply()` via RPC calls
4. **Holder Enumeration**: Blockscout `getTokenHolders` API
5. **Token-Level Mapping**: `tokenOfOwnerByIndex()` per holder via RPC (37 collections)
6. **Contracts without ERC721Enumerable**: 5 collections retain holder counts only

### DOG-721 Standard

DOG-721 is Dogechain's native name for the ERC-721 NFT standard (analogous to DOG-20 for ERC-20). DOG-721 contracts use identical Transfer event signatures and are fully ERC-721 compatible. All DOG-721 tokens on Dogechain are included in this census. [Source: Dogechain Blog #6, Airlyft integration announcement]

### Excluded Contracts (15)

15 contracts were excluded as spam, test deployments, or duplicates:
- **Glyphs of Grace** — 6 deployed copies, all 0 supply (never minted)
- **McRibPixels** — 6 clones with 1-27 supply (we have the canonical one)
- **Test NFT** — 2 contracts literally named "Test NFT", 1 supply each
- **MULTI_EXCHANGE_YELLOW/BLACK** — Deploy artifacts, 2-4 supply
- **FurryFensNFT clone** — 1 supply copy (canonical has 482)
- **Dogechain Name Service** — 0 supply, never launched
- **NINJA HOPE NFT** — 18 supply, never launched

## Collections

| Symbol | Name | Supply | Holders | Token IDs |
|--------|------|--------|---------|-----------|
| RDP | Realdogepunks | 10,000 | 1,089 | 10,000 ✅ |
| ALGB-POS | Algebra Positions | 8,629 | 1,606 | 8,627 ✅ |
| hMERK | Merkly Hyperlane NFT | 1,520 | 716 | 722 ✅ |
| DOGE-DOMAINS | .doge domains | 1,978 | 661 | 1,972 ✅ |
| WTN | WORLD TOUR NFT | 789 | 650 | — ⚠️ |
| SOVPUNKS | SovPunks | 2,408 | 544 | 2,405 ✅ |
| DOGE-BEARS | DogeBears | 10,000 | 515 | 9,377 ✅ |
| TDH-NFT | The Drugged Huskies | 3,620 | 444 | 3,620 ✅ |
| DOGEPUNKS | DOGEPUNKS | 10,000 | 436 | 7,809 ✅ |
| DAYC | Doge Ape Yacht Club | 2,555 | 392 | 2,555 ✅ |
| DAYC2 | Doge Ape YC (v2) | 10,000 | 392 | 4,764 ✅ |
| DH | The Drugged Huskies | 3,371 | 391 | 3,238 ✅ |
| DOGE-BLINDERS | Doge Blinders | 10,000 | 229 | 3,500 ✅ |
| DTOOLS-NFT | DogeTools NFT | 3,008 | 223 | 1,736 ✅ |
| DDB | Doge DickButts | 3,333 | 251 | 3,333 ✅ |
| SEADOGS | Sea Dogs | 1,446 | 203 | 1,446 ✅ |
| RAT | CryptoR.AT | 2,076 | 197 | 2,076 ✅ |
| DG | DogeGang | 3,466 | 195 | 3,466 ✅ |
| CYBERDOGS | Cyberdogs | 3,333 | 174 | 3,333 ✅ |
| DCC | DogeChain Chimps | 3,666 | 166 | 3,636 ✅ |
| DCC2 | DogeChain Chimps (v2) | 3,666 | 147 | 3,666 ✅ |
| ALGB-FARM | Algebra Farming V2 | 160 | 148 | 160 ✅ |
| MONOS | Monos | 2,449 | 346 | 2,449 ✅ |
| ASTRO | Doge Astronauts | 231 | 95 | — ⚠️ |
| FTH | Fox and the Hounds | 5,000 | 98 | 1,979 ✅ |
| ED | Eden | — | 92 | — ⚠️ |
| KIMON | Kimon NFTs | 7,563 | 77 | 1,763 ✅ |
| PIXELFROGS | PixelFrogs | 666 | 76 | 666 ✅ |
| BDKC | Bored Doge KC | 1,774 | 82 | 1,774 ✅ |
| BDKC2 | Bored Doge KC (v2) | 1,732 | 61 | 1,732 ✅ |
| C0F | Council of Frogs | 649 | 118 | 649 ✅ |
| DAC | DogeApeClub | 1,043 | 118 | 1,043 ✅ |
| DOGEDOODLE | DogeDoodle | 1,800 | 105 | 1,800 ✅ |
| MASON | All Seeing Eye | 362 | 50 | — ⚠️ |
| GMNFT | GrimaceMandalaNFT | 66 | 41 | 66 ✅ |
| FFNFTS | FurryFensNFT | 482 | 38 | — ⚠️ |
| DC-DOMAINS | .dc domains | 129 | 38 | 129 ✅ |
| DTOOLS-2023 | DogeTools Commemorative | 75 | 32 | 75 ✅ |
| McRIB | McRibPixels | 638 | 40 | 638 ✅ |
| DCP | Dogechain Paws | 140 | 16 | 140 ✅ |
| CCHIMP | CherisherChimp | 3,666 | 11 | 744 ✅ |
| McRIB-PIX | McRibPixels | 64 | 2 | 64 ✅ |

**Legend:** ✅ = full token ID → owner mapping | ⚠️ = holder counts only (contract lacks ERC721Enumerable)

## Data Format

### Token-Level Collections (37 collections)
Each collection directory contains:
- `{SYMBOL}_token_owners.json` — token ID → owner address (complete mapping)
- `{SYMBOL}_wallet_tokens.json` — wallet address → [token IDs]
- `{SYMBOL}_wallets.csv` — airdrop-ready CSV (wallet, count, token IDs)
- `{SYMBOL}_summary.json` — collection metadata

### Holder-Only Collections (5 collections)
WTN, ASTRO, ED, MASON, FFNFTS — these contracts do not implement the optional `ERC721Enumerable` extension, so `tokenOfOwnerByIndex()` is unavailable. Each directory contains:
- `wallet_tokens.json` — wallet address → NFT count
- `wallets.csv` — airdrop-ready CSV (wallet, count)
- `summary.json` — collection metadata

## License

MIT
