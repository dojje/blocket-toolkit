---
name: blocket-toolkit
description: Search all of Blocket.se (Swedish marketplace) from the terminal: general items (torget), cars, boats, motorcycles and full ad details. Use when the user wants to find, search, compare or look up anything on Blocket: begagnade prylar, fynd, priser, bilar, båtar, motorcyklar, annonsdetaljer. Output is JSON by default.
---

# blocket-toolkit

A CLI over Blocket.se. It covers everything on the site: general items (*torget*),
cars, boats, motorcycles, and single-ad details, plus the full filter surface
(category, subcategory, region, brand, price, year, milage, horsepower, colour,
gearbox, wheel drive, length, engine volume).

Everything is read-only. There is no login, no watchlist, no messaging.

## Setup

The command is `blocket-toolkit`. If it is missing, install it:

```bash
uv tool install blocket-toolkit          # after it is published
# or, from a checkout:
uv tool install --editable /path/to/blocket-toolkit
```

Verify with `blocket-toolkit --version`.

## Golden rules for AI use

1. **Output is JSON by default**: parse it directly. Use `-o jsonl` for streaming,
   `-o table` only when showing a human.
2. **Always cap the result set** with `-n <N>` unless you deliberately want everything.
   Blocket returns ~53 ads per page and `--all` can fetch thousands.
3. **Get details with `ad <id> --type <kind>`**, not by re-searching. `recommerce` is the
   default kind; use `car` / `boat` / `mc` for mobility ads (a mobility id does not work
   with `--type recommerce`).
4. **Filter values are names, not free text.** `-m volvo` works, `-m "Volvo XC60"` does
   not: pass the brand as `--model volvo` and put `xc60` in the query instead.
5. **On an unknown filter value the CLI prints the full list of valid names to stderr.**
   Read that list, pick the right value and retry once.
6. **Prefer server-side filters** (`cars --price-max`, `--year-min`, …) over client-side
   post-filtering. For `search` (torget) there are no server-side price filters, so the
   CLI's `--price-min/--price-max/--newer-than` are applied after fetching.
7. **Generic Swedish terms are noisy.** `läsplatta` mostly returns iPad cases and
   keyboards. Search the brand instead (`kindle`, `kobo`, `pocketbook`, `storytel`,
   `boox`), add a `--price-min` floor to drop accessories, and narrow with
   `--sub-category`.

## Commands

### `search`: general items (torget)

```bash
blocket-toolkit search "kindle" -n 10 --price-max 900 --sort price_asc
blocket-toolkit search "grafikkort" -c elektronik_och_vitvaror --sub-category datorer
blocket-toolkit search "cykel" -l stockholm,skane --newer-than 24
blocket-toolkit search "ramminne" -n 20 --sort published_desc
```

Flags: `-c/--category`, `--sub-category`, `-l/--location`, `--sort`, `--price-min`,
`--price-max`, `--newer-than HOURS`, `--page`, `-n/--limit`, `--all`, `--max-pages`,
`-o/--output`, `--raw`.

`--category` and `--sub-category` are mutually exclusive.

### `cars`: used cars

```bash
blocket-toolkit cars "xc60" -m volvo --year-min 2018 --mileage-max 12000
blocket-toolkit cars --model tesla --price-max 350000 --sort price_asc
blocket-toolkit cars --model bmw --transmission automatic --wheel-drive four --color svart
```

Flags: `-m/--model` (brand), `--color`, `--transmission`, `--wheel-drive`,
`--price-min`, `--price-max`, `--year-min`, `--year-max`, `--mileage-min`,
`--mileage-max`, `--hp-min`, `--hp-max`, `-l/--location`, `--sort`, plus the common
paging/output flags.

### `boats`: used boats

```bash
blocket-toolkit boats "segelbat" -t segelbat_motorseglare --length-min 30
blocket-toolkit boats --price-max 100000 -l stockholm
```

Flags: `-t/--type`, `--price-min`, `--price-max`, `--length-min`, `--length-max`
(feet), `-l/--location`, `--sort`, plus the common paging/output flags.

### `mc`: used motorcycles

```bash
blocket-toolkit mc -m yamaha --engine-min 600 --price-max 80000
blocket-toolkit mc --type sport -l skane --sort price_desc
```

Flags: `-m/--model` (brand), `-t/--type`, `--price-min`, `--price-max`, `--engine-min`,
`--engine-max` (cc), `-l/--location`, `--sort`, plus the common paging/output flags.

### `ad`: one listing

```bash
blocket-toolkit ad 26586567
blocket-toolkit ad 26586567 --type recommerce
blocket-toolkit ad 24313362 --type car
blocket-toolkit ad 26586567 --raw
```

`recommerce` returns a cleaned object with `title`, `description`, `price`, `location`,
`category`, `extras`, `images`, `image_urls`, `meta` and `jsonLd`.
`car` / `boat` / `mc` return a scraped object with `title`, `subtitle`, `price`,
`description`, `specifications`, `equipment` (cars), `seller_type` and `ad_id`.
`--raw` returns Blocket's untouched payload.

### Listing valid filter values

```bash
blocket-toolkit categories
blocket-toolkit subcategories -c elektronik_och_vitvaror
blocket-toolkit locations
blocket-toolkit car-options          # brands, colours, gearboxes, wheel drives, sorts
blocket-toolkit boat-options         # types, sorts
blocket-toolkit mc-options           # brands, types, sorts
```

## Output shape

Search commands return an object with paging plus `items`:

```json
{
  "page": 1,
  "last_page": 50,
  "total": 17720,
  "count": 3,
  "items": [
    {
      "id": 26586567,
      "ad_id": 26586567,
      "heading": "Kindle Oasis 9th generation",
      "price": 500,
      "location": "Göteborg",
      "trade_type": "Säljes",
      "url": "https://www.blocket.se/recommerce/forsale/item/26586567",
      "image_url": "https://images.blocketcdn.se/...",
      "flags": ["private", "shipping_exists", "buy_now"],
      "labels": [{"id": "buy_now", "text": "Köp nu", "type": "SECONDARY"}],
      "timestamp": 1789391194000,
      "published_at": "2026-09-14T13:06:34+00:00"
    }
  ]
}
```

- `total` is the number of matching ads on Blocket; `count` is how many are in `items`.
- Vehicle ads add `year`, `mileage` + `mileage_unit`, `make`, `model`, `fuel`,
  `transmission`, `regno`; boats add `length`, `motor_type`, `motor_size`; MC adds
  `volume` (cc).
- `price` is the numeric amount in SEK. `price_unit` is only set for non-default units
  (e.g. monthly fees on cars).

## Reference: general search

### Categories (`-c/--category`)

- `AFFARSVERKSAMHET` (`0.91`)
- `DJUR_OCH_TILLBEHOR` (`0.77`)
- `ELEKTRONIK_OCH_VITVAROR` (`0.93`)
- `FORDONSTILLBEHOR` (`0.90`)
- `FRITID_HOBBY_OCH_UNDERHALLNING` (`0.86`)
- `FORALDRAR_OCH_BARN` (`0.68`)
- `KLADER_KOSMETIKA_OCH_ACCESSOARER` (`0.71`)
- `KONST_OCH_ANTIKT` (`0.76`)
- `MOBLER_OCH_INREDNING` (`0.78`)
- `SPORT_OCH_FRITID` (`0.69`)
- `TRADGARD_OCH_RENOVERING` (`0.67`)

### Subcategories (`--sub-category`)

**AFFARSVERKSAMHET**: `BUTIK_OCH_DETALJHANDEL`, `CONTAINRAR_OCH_BARACKER`, `DOMANER_OCH_SAJTER`, `HALSA_OCH_FORSTA_HJALPEN`, `JORDBRUK`, `KONTORSUTRUSTNING_OCH_INREDNING`, `LAST_OCH_TRANSPORT`, `MASKINUTRUSTNING_OCH_RESERVDELAR`, `SCEN`, `STORKOK_OCH_RESTAURANG`, `VERKSTAD_BYGG_OCH_KONSTRUKTION`

**DJUR_OCH_TILLBEHOR**: `AKVARIUM`, `BURAR`, `FISKAR`, `FODER_DJURVARD_KENNLAR_OCH_STALL`, `FAGLAR`, `GNAGARE_OCH_KANINER`, `HUNDAR`, `HUNDTILLBEHOR`, `HAST_OCH_RIDUTRUSTNING`, `HASTAR`, `KATTER`, `KATTILLBEHOR`, `LANTBRUKSDJUR`, `REPTILER`, `SPINDLAR_OCH_INSEKTER`, `OVRIGA_DJUR`, `OVRIGA_DJURTILLBEHOR`

**ELEKTRONIK_OCH_VITVAROR**: `DATORER`, `FOTO_OCH_VIDEO`, `HUSHALLSAPPARATER`, `LJUD_OCH_BILD`, `PERSONVARD`, `TELEFONER_OCH_TILLBEHOR`, `TV_SPEL_OCH_SPELKONSOLER`, `VITVAROR`

**FORDONSTILLBEHOR**: `BILDELAR_OCH_TILLBEHOR`, `HUSVAGNS_OCH_HUSBILSDELAR`, `SLAP_OCH_TRAILER`, `BATDELAR_OCH_TILLBEHOR`, `ATV_RESERVDELAR`, `MC_UTRUSTNING_OCH_RESERVDELAR`

**FRITID_HOBBY_OCH_UNDERHALLNING**: `BILJETTER_OCH_RESOR`, `BOCKER_OCH_TIDNINGAR`, `HANTVERK`, `MAT_OCH_DRYCK`, `MODELLER_OCH_BYGGSATSER`, `MUSIK_OCH_FILM`, `MUSIKINSTRUMENT`, `RADIOSTYRDA_ENHETER`, `SAMLAROBJEKT`, `SALLSKAPS_OCH_BRADSPEL`

**FORALDRAR_OCH_BARN**: `BARNBOCKER`, `BARNKLADER`, `BARNMOBLER`, `BARNSKOR`, `BARNTILLBEHOR_OCH_SAKERHET`, `BARNVAGNAR`, `BILBARNSTOLAR_OCH_BABYSKYDD`, `GRAVIDKLADER`, `INREDNING_TILL_BARNRUM`, `LEKSAKER`

**KLADER_KOSMETIKA_OCH_ACCESSOARER**: `ACCESSOARER`, `DAMKLADER`, `GLASOGON_OCH_SOLGLASOGON`, `HERRKLADER`, `HUD_HAR_OCH_KROPPSVARD`, `KLOCKOR_OCH_ARMBANDSUR`, `KOSMETIK`, `MASKERADKLADER`, `SKOR`, `SMYCKEN_OCH_SMYCKESFORVARING`, `VASKOR_OCH_PLANBOCKER`

**KONST_OCH_ANTIKT**: `ANTIKA_MOBLER`, `KERAMIK_PORSLIN_OCH_GLAS`, `KONST`, `SILVERFOREMAL_OCH_SILVERBESTICK`, `OVRIGA_ANTIKVITETER`

**MOBLER_OCH_INREDNING**: `BORD_OCH_STOLAR`, `DEKORATION_OCH_PRYDNADER`, `GARDEROBER_OCH_FORVARING`, `HYLLOR_OCH_BYRAER`, `KOKSUTRUSTNING_OCH_PORSLIN`, `LAMPOR`, `MATTOR_OCH_TEXTILIER`, `PYNT_TILL_HOGTIDER_OCH_FEST`, `SOFFOR_OCH_FATOLJER`, `SANGAR_OCH_MADRASSER`, `OVRIGA_MOBLER_OCH_INREDNING`

**SPORT_OCH_FRITID**: `BOLLSPORTER`, `CYKEL`, `EXTREMSPORT`, `GOLF`, `JAKT_FISKE_OCH_CAMPING`, `KOSTTILLSKOTT`, `RULLSKRIDSKOR_ISHOCKEY_OCH_KONSTAKNING`, `SKYTTE`, `SUPPORTERPRODUKTER`, `TRANINGSKLOCKOR_OCH_AKTIVITETSARMBAND`, `TRANINGSKLADER_OCH_SKOR`, `TRANINGSUTRUSTNING`, `VATTENSPORT`, `VINTERSPORT`, `OVRIGA_SPORTER`

**TRADGARD_OCH_RENOVERING**: `BADRUM_OCH_BASTU`, `BYGGMATERIAL_OCH_RENOVERING`, `GARAGEDELAR_OCH_TILLBEHOR`, `KOKSINREDNING_OCH_KOKSSTOMMAR`, `LARM_OCH_SAKERHET`, `TRADGARD_OCH_UTEMILJO`, `UTRUSTNING_FOR_FRITIDSHUS`, `VERKTYG`, `VARME_OCH_VENTILATION`, `OVRIGT`

### Locations (`-l/--location`)

`BLEKINGE`, `DALARNA`, `GOTLAND`, `GAVLEBORG`, `HALLAND`, `JAMTLAND`, `JONKOPING`,
`KALMAR`, `KRONOBERG`, `NORRBOTTEN`, `SKANE`, `STOCKHOLM`, `SODERMANLAND`, `UPPSALA`,
`VARMLAND`, `VASTERBOTTEN`, `VASTERNORRLAND`, `VASTMANLAND`, `VASTRA_GOTALAND`, `OREBRO`,
`OSTERGOTLAND`

### Sort orders

`RELEVANCE`, `PRICE_DESC`, `PRICE_ASC`, `PUBLISHED_DESC` and `PUBLISHED_ASC` work
everywhere. Each command adds its own:

- `search`: the five above.
- `cars`: + `MILEAGE_DESC`, `MILEAGE_ASC`, `MODEL`, `YEAR_DESC`, `YEAR_ASC`.
- `boats`: + `LENGTH_DESC`, `LENGTH_ASC`, `SPEED_DESC`, `SPEED_ASC`, `YEAR_DESC`, `YEAR_ASC`.
- `mc`: + `MILAGE_DESC`, `MILAGE_ASC`, `MODEL`, `YEAR_DESC`, `YEAR_ASC`.

## Reference: vehicles

### Car brands (`-m/--model`)

`ABARTH`, `AC`, `ACURA`, `AIWAYS`, `ALFA_ROMEO`, `ALPINA`, `AMC`, `ARIEL`,
`ARMSTRONG_SIDDELEY`, `ASTON_MARTIN`, `AUDI`, `AUSTIN`, `AUSTIN_HEALEY`, `AUTO_UNION`,
`AUTOBIANCHI`, `BEDFORD`, `BENTLEY`, `BMW`, `BUGATTI`, `BUICK`, `BYD`, `CADILLAC`,
`CATERHAM`, `CHEVROLET`, `CHRYSLER`, `CITROEN`, `CUPRA`, `DACIA`, `DAEWOO`, `DAF`,
`DAIHATSU`, `DAIMLER`, `DATSUN`, `DE_TOMASO`, `DELOREAN`, `DESOTO`, `DFSK`, `DKW`,
`DODGE`, `DS`, `EDSEL`, `ERSKINE`, `EXCALIBUR`, `FERRARI`, `FIAT`, `FISKER`, `FORD`,
`FORDSON`, `GAZ`, `GINETTA`, `GMC`, `HEINKEL`, `HILLMAN`, `HOLDEN`, `HONDA`, `HONGQI`,
`HUDSON`, `HUMBER`, `HUMMER`, `HYUNDAI`, `INEOS`, `INFINITI`, `INTERNATIONAL`, `ISUZU`,
`IVECO`, `JAC`, `JAGUAR`, `JEEP`, `JENSEN`, `KAISER_JEEP`, `KGM`, `KIA`, `KTM`, `LADA`,
`LAMBORGHINI`, `LANCIA`, `LAND_ROVER`, `LEVC`, `LEXUS`, `LEYLAND`, `LINCOLN`, `LOTUS`,
`LYNK_CO`, `MAN`, `MASERATI`, `MAXUS`, `MAZDA`, `MCLAREN`, `MERCEDES_BENZ`, `MERCURY`,
`MESSERSCHMITT`, `MG`, `MINI`, `MINI_MARCOS`, `MITSUBISHI`, `MORGAN`, `MORRIS`, `NIO`,
`NISSAN`, `OLDSMOBILE`, `OPEL`, `PACKARD`, `PEUGEOT`, `PLYMOUTH`, `POLESTAR`, `PONTIAC`,
`PORSCHE`, `PRO_SPORT`, `RADICAL`, `RAM`, `RENAULT`, `ROLLS_ROYCE`, `ROVER`, `SAAB`,
`SCION`, `SEAT`, `SERES`, `SHELBY`, `SIMCA`, `SKODA`, `SMART`, `SSANGYONG`, `STANDARD`,
`STUDEBAKER`, `SUBARU`, `SUZUKI`, `TESLA`, `TOYOTA`, `TRABANT`, `TRIUMPH`, `TVR`,
`VAUXHALL`, `VOLKSWAGEN`, `VOLVO`, `WILLYS`, `XPENG`, `ZEEKR`, `ZIMMER`, `OVRIGA`

### Car colours (`--color`)

`BEIGE`, `BLA`, `BRONS`, `BRUN`, `GRA`, `GRON`, `GUL`, `GULD`, `VIT`, `LILA`, `ORANGE`,
`ROSA`, `ROD`, `SILVER`, `SVART`, `TURKOS`

### Car transmission and wheel drive

- `--transmission`: `AUTOMATIC`, `MANUAL`
- `--wheel-drive`: `FWD`, `RWD`, `FOUR`, `TWO`

### Boat types (`-t/--type`)

`BOWRIDER`, `DAYCRUISER`, `FISKEBAT_ARBETSBAT`, `HYTTBAT`, `KABINBAT`, `POWERBOAT`, `RIB`,
`SEGELBAT_MOTORSEGLARE`, `SMABAT_GUMMIBAT`, `SNIPA`, `STYRPULPETBAT`, `VATTENSKOTER`,
`YACHT`, `ANNAT`

### MC brands (`-m/--model`)

`ADLY`, `AGIRRA`, `AIXAM`, `AJP`, `AJS`, `AMERICAN_IRON_HORSE`, `APRILIA`, `BAJAJ`,
`BAOTIAN`, `BAROSSA`, `BENDA`, `BENGHE`, `BETA`, `BIG_DOG`, `BIMOTA`, `BMW`, `BOSS_HOSS`,
`BSA`, `BUELL`, `BULTACO`, `CAGIVA`, `CAKE`, `CAN_AM`, `CFMOTO`, `COBRA`, `DUCATI`,
`ENDURO`, `ENERGICA`, `EUROSCOOTER`, `FANTIC`, `GASGAS`, `GILERA`, `GOES`,
`HARLEY_DAVIDSON`, `HERO`, `HONDA`, `HUSABERG`, `HUSQVARNA`, `HYOSUNG`, `INDIAN`,
`ITALJET`, `JAWA_CZ`, `KAWASAKI`, `KTM`, `KYMCO`, `LAMBRETTA`, `LIFAN`, `LIGIER`, `LYNX`,
`MOTO_GUZZI`, `MV_AGUSTA`, `MZ`, `NIU`, `NORTON`, `OSET`, `PEUGEOT`, `PIAGGIO`, `POLARIS`,
`QINGQI`, `QUADRO`, `REGAL_RAPTOR`, `RENAULT`, `RIEJU`, `ROMET`, `ROYAL_ENFIELD`, `SEGWAY`,
`SHERCO`, `SILENCE`, `SKI_DOO`, `SMC`, `STARK`, `SUPER_SOCO`, `SUR_RON`, `SUZUKI`, `SWM`,
`SYM`, `TALARIA`, `TEN7`, `TGB`, `THUNDER_BY_CITY_WHEELS`, `TM`, `TOMOS`, `TRIUMPH`,
`URAL`, `V8_CHOPPERS`, `VERTIGO`, `VESPA`, `VIARELLI`, `VICTORY`, `VOGE`, `X_PRO`,
`YADEA`, `YAMAHA`, `ZERO`, `ZONTES`, `ZUNDAPP`, `OVRIGA`

### MC types (`-t/--type`)

`ADVENTURE`, `CHOPPER`, `CROSS_ENDURO_TRIAL`, `CRUISER`, `CUSTOM`, `KLASSISK_NAKEN`,
`LATT_MC`, `MC_SCOOTER`, `OFFROAD_MOTARD`, `SPORT`, `SUPERMOTO`, `TOURING`, `TREHJULIG`,
`TRIKE`, `VETERAN`, `ANNAT`

## Gotchas

- **Note the ASCII-only names.** Blocket's own ids are ASCII: `SKANE`, `VASTRA_GOTALAND`,
  `MERCEDES_BENZ`, `VIT`, `ROD`. Diacritics are not accepted.
- **Spelling traps in sort orders**: cars use `MILEAGE_ASC`/`MILEAGE_DESC` but mc use
  `MILAGE_ASC`/`MILAGE_DESC` (one L).
- **`total` vs `count`.** `total` is the whole result set (can be tens of thousands);
  `count` is what you actually got back.
- **Torget paging is coarse.** ~53 ads per page; `--all` follows pages up to
  `--max-pages` (default 20). Be considerate: don't scrape the whole site.
- **`ad` for `car`/`boat`/`mc` is scraped**, so fields are less consistent than for
  `recommerce`. `price` there is a string like `"214 800 kr"`.
- **Ids are not interchangeable across verticals.** A torget id needs
  `--type recommerce`; a mobility id needs `--type car|boat|mc`.
- Blocket has no official public API. Behaviour can change without notice.
