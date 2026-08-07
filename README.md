# Dogechain NFT Snapshots

Complete NFT collection census for Dogechain mainnet. Full chain scan of 62.5M blocks identified all ERC-721 (DOG-721) contracts via Transfer event analysis.

## Census Summary

- **42 collections** snapshotted (of 57 total ERC-721 contracts found; 15 excluded as spam/test/duplicates)
- **4,346 holder records** across all collections (includes duplicates across collections)
- **119,904 NFTs** mapped
- **21 collections** have full token-level data (token ID → owner mapping via `tokenOfOwnerByIndex`)
- **19 collections** have holder-level data (wallet → NFT count via Blockscout API)
- Snapshot date: August 7, 2026
- Block: ~62,535,818

## Methodology

1. **Chain Scan**: `eth_getLogs` across 62.5M blocks in 5K windows, filtering for ERC-721 Transfer events (4-topic signature)
2. **ERC-721 Verification**: `supportsInterface(0x80ac58cd)` via RPC for each candidate contract
3. **Metadata**: `name()`, `symbol()`, `totalSupply()` via RPC calls
4. **Holder Enumeration**: Blockscout `getTokenHolders` API
5. **Token-Level Mapping** (v2 collections): `tokenOfOwnerByIndex()` per holder via parallel RPC

### DOG-721 Standard

DOG-721 is Dogechain's native name for the ERC-721 NFT standard (analogous to DOG-20 for ERC-20). DOG-721 contracts use identical Transfer event signatures and are fully ERC-721 compatible. All DOG-721 tokens on Dogechain are included in this census.

## Collections

| Symbol | Name | Supply | Holders |
|--------|------|--------|---------|
| RDP | Realdogepunks | 10,000 | 1,089 |
| ALGB-POS | Algebra Positions | 8,629 | 1,606 |
| SOVPUNKS | SovPunks | 2,408 | 544 |
| DOGE-BEARS | Doge Bears | 10,000 | 515 |
| hMERK | Merkly Hyperlane NFT | 1,520 | 716 |
| .DOGE | .doge domains | 1,978 | 661 |
| WTN | WORLD TOUR NFT | 789 | 650 |
| DH | Doge Huskies | 3,371 | 391 |
| DAYC2 | Doge Ape YC (v2) | 10,000 | 392 |
| MONOS | Monos | 2,449 | 346 |
| TDH-NFT | The Drugged Huskies | 3,620 | 444 |
| DOGE-BLINDERS | Doge Blinders | 10,000 | 229 |
| DTOOLS NFT | DogeTools NFT | 3,008 | 223 |
| DDB | Doge DickButts | 3,333 | 251 |
| RAT | Rat NFT | 2,076 | 197 |
| DG | DogeGang | 3,466 | 195 |
| SEADOGS | SeaDogs | 1,446 | 203 |
| DOGEDOODLE | DogeDoodle | 1,800 | 105 |
| DCC | DogeChain Chimps | 3,666 | 166 |
| DCC2 | DogeChain Chimps (v2) | 3,666 | 147 |
| ALGB-FARM | Algebra Farming V2 | 160 | 148 |
| ASTRO | Astro | 231 | 95 |
| DAYC | Doge Ape Yacht Club | 2,555 | 109 |
| C0F | Council of Frogs | 649 | 118 |
| DAC | DogeApeCoin | 1,043 | 118 |
| KIMON | Kimon NFTs | 7,563 | 77 |
| BDKC | Bored Doge KC | 1,774 | 82 |
| BDKC2 | Bored Doge KC (v2) | 1,732 | 61 |
| PIXELFROGS | Pixel Frogs | 666 | 76 |
| MASON | All Seeing Eye | 362 | 50 |
| CYBERDOGS | CyberDogs | 3,333 | 174 |
| McRIB | McRIB | 638 | 40 |
| FTH | FTH | 5,000 | 98 |
| DOGEPUNKS | DogePunks | 10,000 | 436 |
| FFNFTS | FurryFensNFT | 482 | 38 |
| .DC | .dc domains | 129 | 38 |
| DTOOLS-2023 | DogeTools Commemorative | 75 | 32 |
| ED | Eden | 1B* | 92 |
| GMNFT | GrimaceMandalaNFT | 66 | 41 |
| DCP | Dogechain Paws | 140 | 16 |
| CChimp | CherisherChimp | 3,666 | 11 |
| McRIB-PIX | McRibPixels | 64 | 2 |

\* Eden reports 1B supply but only 1,258 tokens are actually held.

## Data Format

### V2 Collections (21 collections, token-level data)
Each collection directory contains:
- `{SYMBOL}_token_owners.json` — token ID → owner address (complete mapping)
- `{SYMBOL}_wallet_tokens.json` — wallet address → token count
- `{SYMBOL}_wallets.csv` — airdrop-ready CSV (wallet, count)
- `{SYMBOL}_summary.json` — collection metadata

### Holder-Only Collections (19 collections)
Each collection directory contains:
- `wallet_tokens.json` — wallet address → NFT count
- `wallets.csv` — airdrop-ready CSV (wallet, count)
- `summary.json` — collection metadata

## License

MIT
