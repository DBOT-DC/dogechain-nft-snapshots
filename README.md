# Dogechain NFT Snapshots

Complete NFT collection snapshots for Dogechain mainnet. Wallet-level holder data for airdrops, migration, and historical records.

## Coverage

42 ERC-721 collections discovered via full chain scan (62.5M blocks, Transfer event analysis).

### Collections

| Symbol | Name | Supply | Holders |
|---|---|---|---|
| RDP | Realdogepunks | 10,000 | 1,089 |
| DOGE-BEARS | Doge Bears | 10,000 | 515 |
| DOGE-BLINDERS | Doge Blinders | 10,000 | 229 |
| DOGEPUNKS | DogePunks | 10,000 | 436 |
| ALGB-POS | Algebra Positions | 8,629 | 1,606 |
| DH | Doge Huskies | 3,371 | 391 |
| DAYC | Doge Ape Yacht Club | 2,555 | 109 |
| DAYC2 | Doge Ape YC (v2) | 10,000 | 392 |
| DCC | DogeChain Chimps | 3,666 | 166 |
| DCC2 | DogeChain Chimps (v2) | 3,666 | 147 |
| CChimp | CherisherChimp | 3,666 | 11 |
| TDH-NFT | The Drugged Huskies | 3,620 | 444 |
| DG | DogeGang | 3,466 | 195 |
| DDB | Doge DickButts | 3,333 | 251 |
| CYBERDOGS | CyberDogs | 3,333 | 174 |
| SEADOGS | SeaDogs | 1,446 | 203 |
| KIMON | Kimon NFTs | 7,563 | 77 |
| BDKC | Bored Doge KC | 1,774 | 82 |
| BDKC2 | Bored Doge KC (v2) | 1,732 | 61 |
| hMERK | Merkly Hyperlane NFT | 1,520 | 716 |
| MONOS | Monos | 2,449 | 346 |
| RAT | Rat NFT | 2,076 | 197 |
| SOVPUNKS | SovPunks | 2,408 | 544 |
| .DOGE | .doge domains | 1,978 | 661 |
| FTH | FTH | 5,000 | 98 |
| WTN | WORLD TOUR NFT | 789 | 650 |
| DTOOLS-NFT | DogeTools NFT | 3,008 | 223 |
| DOGEDOODLE | DogeDoodle | 1,800 | 105 |
| PIXELFROGS | Pixel Frogs | 666 | 76 |
| McRIB | McRIB | 638 | 40 |
| FFNFTS | FurryFensNFT | 482 | 38 |
| MASON | All Seeing Eye | 362 | 50 |
| ALGB-FARM | Algebra Farming V2 | 160 | 148 |
| DCP | Dogechain Paws | 140 | 16 |
| .DC | .dc domains | 129 | 38 |
| DTOOLS-2023 | DogeTools Commemorative | 75 | 32 |
| McRIB-PIX | McRibPixels | 64 | 2 |
| GMNFT | GrimaceMandalaNFT | 66 | 41 |
| C0F | Council of Frogs | 649 | 118 |
| DAC | DogeApeCoin | 1,043 | 118 |
| ASTRO | Astro | 231 | 95 |
| ED | Eden | - | 92 |

## Data Format

Each collection directory contains:
- `wallets.csv` — wallet address, NFT count (airdrop-ready)
- `wallet_tokens.json` — wallet → token count mapping
- `summary.json` — collection metadata
- Collections from v2 also include `token_owners.json` — token ID → owner mapping

## License

MIT
