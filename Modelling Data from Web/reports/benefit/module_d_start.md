# Before Module D, and the first Module D run

Benefit simulator. 12 Nov 2026. Branch `benefit-simulator`.
Decisions D-177 to D-183 in `DECISIONS.md`.

## Sources

| Source | What we used | Date of data | How we got it |
|---|---|---|---|
| FEMA National Risk Index, census tracts (`fema_miami_dade_dec_2025.csv`) | Coastal and inland flooding expected annual loss to buildings | December 2025 | Already in the repo |
| OpenFEMA NFIP Redacted Policies v3 (`NfipPoliciesV3.parquet`) | Policies in force, take-up, floor elevation fields | Refreshed 9 Sep 2026 | Downloaded whole; size and MD5 checked against FEMA |
| OpenFEMA NFIP claims; ACS occupied homes | Claims check | 1978 to 2025 (2025 dollars) | Stage 2 |
| Florida DOR 2026 tax roll (NAL) | Just value, exemptions, homestead, use codes | Roll year 2026 | Already on disk |
| Miami-Dade County house layer (Property Appraiser) | Bedrooms, bathrooms, living area, latest sale | 11 Nov 2026 | Part 2 (no personal fields) |
| FHFA tract house price index | Moving prices and values between years | Data to 2025 | Already on disk |
| FEMA 2027 FIRM database | Water areas (waterfront, distance to water) | 2027 maps | Part 1 |
| Property Appraiser 2026 adopted millage | Tax change | 2026 | Part 1 |
| Our Modules A to C | Expected yearly damage, project examples | This work | Built here |

## In short

- **National Risk Index (NRI).**
  - **Totals:** the NRI puts flood losses to buildings at $287M a year, mostly
    from inland flooding. Our totals bracket it: $187M (storms from 10% to
    2% only) to $463M (anchored, structure only).
  - **Ranking:** the tract ranking hardly agrees (0.02).
  - **NRI against claims:** the NRI itself matches insurance claims less
    well than our model does (0.25 against 0.35), so it is a check on size,
    not a target.
- **NFIP policies:** the full file is downloaded and verified.
  - **Take-up:** 35.5% of occupied homes have a policy.
  - **Claims check:** with that take-up, the anchored model's insured part
    is 5.0 times claims, with tract ranking 0.46. Stage 2 is 1.45 times
    claims, ranking 0.52.
  - **Floor heights:** the policies' own floor fields put homes a median
    1.1 ft above the ground, higher than we assume for slab homes.
- **Sales.**
  - **Main sample:** 40,901 qualified sales from 2025 and 2026.
  - **Test sample:** a stated non-market rule keeps 41,729 single-family and
    57,824 condo sales from 2021 to 2024.
- **Module D models fit well,** with error on held-out sales of 11%
  (single-family) and 14% (condo), against 20% and 32% for OLS.
- **But the flood effect has the wrong sign for single-family homes.**
  - **Direction:** more expected flood damage goes with higher prices.
  - **Cause:** mostly that damage in dollars grows with the home's own
    value.
  - **Condos:** no consistent discount within neighbourhoods either.
  - **Consequence:** the value-change formula would say flood protection
    lowers home values. **This needs a decision before Module D can be
    used** (options in section 6).

## 1. Benchmark against FEMA's National Risk Index (D-177)

The NRI counts building value only (no contents), so our structure-only
figure is the closest match. Hurricane wind is excluded. Results cover 706
tracts.

| | Total, $M a year | Tract ranking against NRI flood | Against NRI coastal | Tract ranking against NFIP claims |
|---|---|---|---|---|
| NRI coastal flooding | 18 | n/a | n/a | 0.54 |
| NRI inland flooding | 269 | n/a | n/a | 0.17 |
| **NRI total flood** | **287** | n/a | n/a | **0.25** |
| Anchored (structure + contents) | 889 | 0.02 | 0.14 | 0.35 |
| Anchored, structure only | 463 | 0.06 | 0.13 | n/a |
| Frequent storms only (10% to 2%) | 187 | -0.08 | 0.28 | 0.30 |
| Stage 2 | 164 | -0.02 | 0.65 | 0.49 |

Ranking is by loss per dollar of building value (Spearman). The top tenth
of tracts by our anchored version and by the NRI share only 19% of tracts.

**What this means:**
- **Size:** the NRI and our model are of a similar size once we count
  structure only. Our range ($187M to $463M) brackets the NRI's $287M.
- **Location:** they disagree completely on where the losses are. The NRI's
  loss is 94% inland flooding, while ours is 99% coastal. Our model has
  almost no inland rainfall (D-175), so this agrees with the known gap.
- **Neither is the truth:** the NRI ranks the actual insurance claims worse
  than our anchored version does.

## 2. NFIP policies and the claims check per insured home (D-181)

**Download check.** File size 3,713,009,365 bytes and MD5
275e07e99258e4ff7684cf4505f91406 both match FEMA's server. The file was
filtered to Miami-Dade (censusGeoid starting 12086), leaving 3,317,242
policy records from 2009 to 2026. Only non-identifying fields were kept.

**Your browser copy.** `~/Downloads/NfipPoliciesV3.parquet` has finished
downloading: it is the same size and not partial. It was **not deleted**.
Say if you want it removed.

**Take-up.**
- **Policies:** residential policy-years run at about 340,000 to 355,000 a
  year.
- **Share of homes:** that is 35.5% of occupied homes (2015 to 2025
  average), against the 20.3% that Stage 2's gap breakdown implied.
- **By tract:** the median tract has 16%; the 10th to 90th percentile is
  1% to 73%.

**Claims check (insured part).** Modelled insured loss = residential damage
x the tract's take-up x the paid-to-damage ratio from claims (0.906).

| | Model, residential | Model, insured part | Claims | Ratio | Tract ranking |
|---|---|---|---|---|---|
| Anchored | $499M | $153M | $30.3M | 5.0 | 0.46 (0.39 to 0.51) |
| Stage 2 | $89M | $44M | $30.3M | 1.45 | 0.52 (0.45 to 0.57) |

With measured take-up, the anchored model's tract ranking (0.46) is close
to Stage 2's (0.52). Its level is still 5 times claims.

**Floor heights from the policies.**
- **Source:** lowest floor minus lowest adjacent grade, summarised by block
  group only (2,060 block groups with 10 or more records).
- **Result:** median 1.1 ft (middle half 0.9 to 1.5 ft).
- **Comparison:** our slab homes assume 0.25 to 0.75 ft (NSI). So our floors
  are probably 0.3 to 0.8 ft too low, and our damage too high.
- **Suggested next step:** use these block-group medians for estimated
  floors. Not done yet, so Module B is unchanged.

## 3. Sales samples (D-178, D-179)

**Main sample:** qualified 2025 and 2026 sales of improved homes.

| | Single-family | Condo |
|---|---|---|
| Sales | 17,935 | 22,966 |
| Training (80%) | 14,350 | 18,375 |
| Held out (20%) | 3,585 | 4,591 |
| Share with expected flood damage above 0 | 58% | 63% |
| Waterfront | 4% | 19% |

**Test sample: 2021 to 2024 latest sales, no qualification code.** The
non-market rule was stated before fitting. A sale is kept only if all of
these hold:
1. price at least $50,000;
2. price against the 2026 just value (moved back to the sale year with the
   FHFA county index) inside the middle 95% of the same ratio in qualified
   sales;
3. price per square foot (2025 dollars) inside the middle 99% of qualified
   sales;
4. living area and year built present.

| | Single-family | Condo |
|---|---|---|
| Latest sales 2021 to 2024 | 92,084 | 115,821 |
| Below $50,000 | 44,553 | 37,804 |
| Outside the price-to-value band | 5,452 | 19,590 |
| Outside the price per square foot band | 314 | 569 |
| Missing area or year | 36 | 34 |
| **Kept** | **41,729** | **57,824** |

Most removals are nominal prices (deeds between relatives, transfers),
which is what the rule is meant to catch.

## 4. Module D models (D-180)

**Variables (specification D2):**
- **Outcome:** log price.
- **Flood risk:** expected yearly damage in $1,000s (anchored; frequent
  storms only as a sensitivity).
- **House:** living area, lot size (single-family), age, bedrooms,
  bathrooms, and a pool proxy (single-family: special features value above
  0, which also counts docks and fences).
- **Location:** waterfront, distance to water, ground elevation.
- **Time:** sale year and month.

**Set-up:**
- **Benchmark:** OLS on all training sales.
- **MGWR sample:** 5,000 training sales per model, below the
  specification's 10,000 to 30,000, for time and memory.
- **Bandwidths:** a floor of 500 neighbours. Waterfront and the pool proxy
  are held countywide.
- **Run time:** 15 to 18 minutes per main model.

| | Single-family OLS | Single-family MGWR | Condo OLS | Condo MGWR |
|---|---|---|---|---|
| R² | 0.68 | 0.90 | 0.52 | 0.89 |
| Held-out error (median) | 20.4% | **11.3%** | 32.2% | **14.0%** |
| Leftover spatial clustering (Moran's I) | 0.49 | 0.18 | 0.70 | 0.18 |
| Standard errors usable | n/a | yes (all finite) | n/a | yes |

**Bandwidths (single-family):** most variables settle at the 500 floor,
except bedrooms (1,310 neighbours); waterfront and the pool proxy are
countywide. For condos, time is close to countywide (1,548). Held-out error
by place is in `single_family_main.json` and `condo_main.json`.

**Flood coefficient (% change in price per $1,000 of expected yearly damage):**

| Model | OLS (95% range) | MGWR median (10th to 90th percentile) | Share of locations negative |
|---|---|---|---|
| Single-family, anchored (main) | +1.6 (+0.4 to +2.8) | +1.3 (-0.1 to +4.2) | 12% |
| Single-family, frequent storms | +0.4 (-1.0 to +1.8) | +1.8 (-3.5 to +24) | 27% |
| Single-family, with 2021 to 2024 sales | +1.4 (+0.3 to +2.4) | +0.8 (-0.6 to +2.8) | 24% |
| Condo, anchored (main) | -1.2 (-2.0 to -0.3) | +0.1 (-19 to +16) | 43% |
| Condo, frequent storms | -5.5 (-10.0 to -0.8) | +4.6 (-41 to +163) | 34% |
| Condo, with 2021 to 2024 sales | -0.9 (-1.7 to -0.1) | +3.2 (-10 to +13) | 29% |

**Adding the 2021 to 2024 sales.** Results with and without them are
similar. Held-out error barely changes (single-family 12.2% against 11.3%;
condo 16.5% against 14.0%). The flood coefficient keeps its sign. The extra
sales neither help nor hurt much.

## 5. Why the flood coefficient is positive: checks (D-183)

These are single-family OLS checks, in % per $1,000:

| Check | Single-family | Condo |
|---|---|---|
| Specification variables | +1.6 | -1.2 |
| Within tracts (tract fixed effects) | +0.4 (0.0 to +0.9) | 0.0 |
| Within block groups | +0.5 (0.0 to +0.9) | 0.0 |
| Homes more than 1 km from water | +3.0 | -1.0 |
| Only sales inside the 1% zone | +0.9 | -1.0 |
| **Flood risk as damage per $100,000 of building value** | **-0.06 (-0.39 to +0.26)** | **-4.8 (-6.0 to -3.6)** |
| Same, within tracts | +0.05 | +0.9 |

The damage-rate line is per $100 a year of damage per $100,000 of value.

**What this means:**
- **The positive sign is not waterfront appeal.** It persists more than
  1 km from water and within tracts.
- **It is mostly mechanical.** Expected damage in dollars grows with the
  home's own value, because a bigger, pricier house has more to lose. So the
  "flood" variable partly measures house value. Measured as a share of
  value, the single-family effect is zero.
- **Condos** show a clear discount across the county per share of value.
  But it disappears within tracts, so it is about which neighbourhoods are
  exposed, not the flood risk itself.
- **Bottom line:** in 2025 to 2026 sales, we cannot yet find a reliable flood
  discount within neighbourhoods.

## 6. Value and tax change for the test projects (D-182): method works, results not usable yet

**Method:**
- **Coefficients:** the MGWR flood coefficient and its standard error are
  stored on 383,978 single-family and 103,882 condo buildings.
- **Value change:** building value x (exp(coefficient x change in
  damage) - 1), with a range from the coefficient ± 2 standard errors.
- **Tax:** follows Florida's caps over 10 years (Save Our Homes for
  homesteads, 10% for others on non-school levies) with 2026 exemptions and
  millage.

**What the current coefficients give** (shown only to explain the problem):

| Project | Losses avoided, per year | Value change, main model | Value change, frequent-storm model | Frequent ÷ main | Tax change, year 1 / year 10 (main) |
|---|---|---|---|---|---|
| Seawall 8 ft, North Miami | $2.2M | -$15.2M (-$35.9M to +$6.9M) | -$4.7M (-$23.5M to +$16.1M) | 0.31 | -$163,000 / -$236,000 |
| Elevate 3 ft, Princeton | $8.4M | -$20.3M (-$72.2M to +$34.6M) | -$20.9M (-$84.3M to +$47.3M) | 1.03 | -$127,000 / -$174,000 |

**How much the two flood variables differ:**
- **Elevation project:** about the same (1.03 times).
- **Seawall:** very different (0.31 times).
- **Ranges:** both are very wide and cross zero.

**The bigger point is the sign.** With these coefficients, protecting homes
"lowers" their value, which is not credible. Also, the coefficients stretch
beyond the calibration range when carried to some buildings (condo median
+8% per $1,000).

**Options (your and the professor's decision):**
1. **Flood variable as a damage rate** (per $100,000 of building value)
   instead of dollars. This removes the mechanical link. It changes the
   specification's variable, and the value-change formula then uses the
   change in damage rate.
2. **Keep the specification's variable, but use only local coefficients that
   are negative and significant.** Elsewhere, value change is "not
   estimated". Simple, but few places pass today.
3. **Use a published flood discount as a labelled assumption** until the
   before-and-after check (specification D6) can run on 2021 to 2024
   qualified sales (needs the DOR request).

Options 1 and 3 can be combined.

## 7. Estimated against assumed

- **Measured:**
  - NRI and claims totals;
  - policy counts and take-up;
  - floor heights from policies;
  - sale prices and house features.
- **Estimated:**
  - all model coefficients;
  - held-out errors;
  - value and tax changes.
- **Assumed:**
  - the non-market rule;
  - the pool proxy;
  - waterfront within 10 m;
  - 3% market growth;
  - Save Our Homes at 2.9%;
  - no sales during 10 years;
  - an equal split of condo building damage across units;
  - the 5,000-sale MGWR sample.

## 8. Main limitations

- **No reliable flood discount yet** for single-family homes (section 5).
- **The MGWR sample is below the specification's range.** A 10,000-sale run
  is possible overnight.
- **2021 to 2024 sales have no qualification codes** until DOR's files
  arrive.
- **Our damage is likely too high.** The floor heights from the policies,
  and the 5 times claims ratio, both point that way.
- **Inland rainfall is still missing** (D-175), which the NRI comparison
  confirms.
