"""Compile RESULTS_FOR_REVIEW.md from existing output/ CSVs and
correlation_analysis.md. Pure compilation: reads numbers already computed by
Parts 1-5, formats them into embedded markdown tables. Nothing here fits,
re-runs, or recomputes any statistic - it only rounds and renders.

Usage: python scripts/compile_results_for_review.py
Output: RESULTS_FOR_REVIEW.md
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scaler_projects import BASE, OUTPUT_DIR  # noqa: E402

P2 = OUTPUT_DIR / "part2_univariate"
P3 = OUTPUT_DIR / "part3_correlation"
P4 = OUTPUT_DIR / "part4_investment_vs_indicators"
P5 = OUTPUT_DIR / "part5_diagnostics"


# --------------------------------------------------------------------------
# formatting helpers
# --------------------------------------------------------------------------

def fmt_coef(x):
    """3 decimals, but never collapse a genuinely nonzero small value to
    0.000 - switch to scientific notation instead of rounding away the sign
    or the only nonzero digit."""
    if pd.isna(x):
        return ""
    if x == 0:
        return "0.000"
    if abs(x) < 0.0005:
        return f"{x:.2e}"
    return f"{x:.3f}"


def fmt_p(x):
    if pd.isna(x):
        return ""
    if x < 0.0001:
        return f"{x:.2e}"
    return f"{x:.4f}"


def fmt_int(x):
    if pd.isna(x):
        return ""
    return f"{int(x):,}"


def fmt_dollar(x):
    if pd.isna(x):
        return ""
    return f"${x:,.0f}"


def df_to_md(df, formatters=None, index=False):
    """Render as a markdown table. disable_numparse=True stops tabulate from
    re-parsing already-formatted numeric strings (e.g. stripping the trailing
    zeros back off '0.0700') - without it, formatted p-values/coefficients
    silently lose the precision the formatters above were applying."""
    d = df.copy()
    if formatters:
        for c, f in formatters.items():
            if c in d.columns:
                d[c] = d[c].map(f)
    return d.to_markdown(index=index, disable_numparse=True)


def sig_mark(fdr_p, sparse=False):
    if sparse:
        return "SPARSE"
    if pd.isna(fdr_p):
        return ""
    return "**" if fdr_p < 0.05 else ""


# --------------------------------------------------------------------------
# Section 1 - the composition finding
# --------------------------------------------------------------------------

def section1():
    lines = []
    lines.append("## 1. The composition finding (headline)")
    lines.append("")
    lines.append(
        "*Sources: `output/part4_investment_vs_indicators/4b_tract_type_composition_"
        "continuous.csv`, `4c_tract_path_composition_continuous.csv`, "
        "`4d_bg_type_composition_continuous.csv`, `4d_bg_path_composition_continuous.csv`, "
        "and the four matching `_binary.csv` files.*"
    )
    lines.append("")

    type_cont_t = pd.read_csv(P4 / "4b_tract_type_composition_continuous.csv")
    type_cont_b = pd.read_csv(P4 / "4d_bg_type_composition_continuous.csv")
    path_cont_t = pd.read_csv(P4 / "4c_tract_path_composition_continuous.csv")
    path_cont_b = pd.read_csv(P4 / "4d_bg_path_composition_continuous.csv")
    type_bin_t = pd.read_csv(P4 / "4b_tract_type_composition_binary.csv")
    type_bin_b = pd.read_csv(P4 / "4d_bg_type_composition_binary.csv")
    path_bin_t = pd.read_csv(P4 / "4c_tract_path_composition_binary.csv")
    path_bin_b = pd.read_csv(P4 / "4d_bg_path_composition_binary.csv")

    # -- summary statistics on the gray-up/green-down pattern ----------------
    def pattern_summary(cont, grain):
        share = cont[cont.measure == "share"]
        piv_r = share.pivot(index="vuln_var", columns="group", values="spearman_rho")
        piv_fdr = share.pivot(index="vuln_var", columns="group", values="spearman_p_fdr")
        n_vars = len(piv_r)
        pattern = (piv_r["gray"] > 0) & (piv_r["green"] < 0)
        n_pattern = int(pattern.sum())
        both_sig = pattern & (piv_fdr["gray"] < 0.05) & (piv_fdr["green"] < 0.05)
        either_sig = pattern & ((piv_fdr["gray"] < 0.05) | (piv_fdr["green"] < 0.05))
        return {
            "grain": grain, "n_vars": n_vars, "n_pattern": n_pattern,
            "n_both_fdr_sig": int(both_sig.sum()), "n_either_fdr_sig": int(either_sig.sum()),
            "gray_range": (piv_r["gray"].min(), piv_r["gray"].max()),
            "green_range": (piv_r["green"].min(), piv_r["green"].max()),
        }

    st = pattern_summary(type_cont_t, "tract")
    sb = pattern_summary(type_cont_b, "block group")

    lines.append(
        f"**Plain-language read:** Gray infrastructure's *share* of a unit's "
        f"investment tends to rise with several deprivation indicators "
        f"(vehicle access, housing density, internet access) while Green's "
        f"share tends to fall with the same indicators. At **tract** grain "
        f"this gray-up/green-down sign pattern holds for **{st['n_pattern']} "
        f"of {st['n_vars']}** vulnerability variables, but only "
        f"**{st['n_both_fdr_sig']}** have both sides individually "
        f"FDR-significant (**{st['n_either_fdr_sig']}** have at least one side "
        f"significant). At **block group** grain the pattern holds for "
        f"**{sb['n_pattern']} of {sb['n_vars']}**, with **{sb['n_both_fdr_sig']}** "
        f"both-significant (**{sb['n_either_fdr_sig']}** either-significant). "
        f"Gray-share Spearman ρ ranges "
        f"{fmt_coef(st['gray_range'][0])} to {fmt_coef(st['gray_range'][1])} "
        f"(tract) / {fmt_coef(sb['gray_range'][0])} to {fmt_coef(sb['gray_range'][1])} "
        f"(BG); Green-share ρ ranges {fmt_coef(st['green_range'][0])} to "
        f"{fmt_coef(st['green_range'][1])} (tract) / {fmt_coef(sb['green_range'][0])} "
        f"to {fmt_coef(sb['green_range'][1])} (BG). **The sign pattern is broad but "
        f"the FDR-survivable evidence rests on a minority of variables at both grains** "
        f"- this must be read as a directional tendency across the vulnerability "
        f"block, not as a small set of strong individual relationships."
    )
    lines.append("")
    lines.append(
        "Blue infrastructure is flagged sparse at both grains "
        "(19 single-unit-sited receiving units - see Section 3) and every Blue "
        "row below is marked `SPARSE`; its coefficients are shown for "
        "completeness but should not be read as stable."
    )
    lines.append("")

    # -- 1a. type share, both grains, full long table -------------------------
    def render_type_share(cont, grain):
        share = cont[cont.measure == "share"].copy()
        share = share.sort_values(["vuln_var", "group"])
        share["sig"] = share.apply(lambda r: sig_mark(r["spearman_p_fdr"], r["flag_sparse"]), axis=1)
        out = share[["vuln_var", "group", "n", "spearman_rho", "spearman_p",
                     "spearman_p_fdr", "sig"]].rename(columns={
            "vuln_var": "variable", "group": "type", "spearman_rho": "rho",
            "spearman_p": "p_raw", "spearman_p_fdr": "p_fdr"})
        md = df_to_md(out, {"rho": fmt_coef, "p_raw": fmt_p, "p_fdr": fmt_p, "n": fmt_int})
        return f"### 1a. Project-type SHARE vs. vulnerability - {grain} (n={len(out)} pairs)\n\n{md}\n"

    lines.append(render_type_share(type_cont_t, "tract, 698 units, 4 types x 34 vulnerability variables"))
    lines.append(render_type_share(type_cont_b, "block group, 1,843 units, 4 types x 35 vulnerability variables"))

    # -- 1b. path share, both grains -------------------------------------------
    def render_path_share(cont, grain):
        share = cont[cont.measure == "share"].copy()
        share = share.sort_values(["vuln_var", "group"])
        share["sig"] = share.apply(lambda r: sig_mark(r["spearman_p_fdr"], r["flag_sparse"]), axis=1)
        out = share[["vuln_var", "group", "n", "spearman_rho", "spearman_p",
                     "spearman_p_fdr", "sig"]].rename(columns={
            "vuln_var": "variable", "group": "path", "spearman_rho": "rho",
            "spearman_p": "p_raw", "spearman_p_fdr": "p_fdr"})
        md = df_to_md(out, {"rho": fmt_coef, "p_raw": fmt_p, "p_fdr": fmt_p, "n": fmt_int})
        return f"### 1b. Allocation-path SHARE vs. vulnerability - {grain} (n={len(out)} pairs)\n\n{md}\n"

    lines.append(render_path_share(path_cont_t, "tract, 698 units, 3 paths (single-unit/municipality/county) x 34 vars"))
    lines.append(render_path_share(path_cont_b, "block group, 1,843 units, 3 paths x 35 vars"))

    # -- 1c. binary group comparisons -----------------------------------------
    def render_binary(binr, group_label, grain):
        b = binr.copy().sort_values(["vuln_var", "group"])
        b["sig"] = b.apply(lambda r: sig_mark(r["mw_p_fdr"], r["flag_sparse"]), axis=1)
        out = b[["vuln_var", "group", "n_receiving", "n_not", "mean_receiving",
                 "mean_not", "mw_p", "mw_p_fdr", "sig"]].rename(columns={
            "vuln_var": "variable", "group": group_label, "mw_p": "p_raw", "mw_p_fdr": "p_fdr"})
        md = df_to_md(out, {"mean_receiving": fmt_coef, "mean_not": fmt_coef,
                            "p_raw": fmt_p, "p_fdr": fmt_p,
                            "n_receiving": fmt_int, "n_not": fmt_int})
        return (f"### 1c. {group_label.capitalize()}_any group comparison - {grain} "
                f"(Mann-Whitney U, n={len(out)} pairs)\n\n{md}\n")

    lines.append(render_binary(type_bin_t, "type", "tract"))
    lines.append(render_binary(type_bin_b, "type", "block group"))
    lines.append(render_binary(path_bin_t, "path", "tract"))
    lines.append(render_binary(path_bin_b, "path", "block group"))

    return "\n".join(lines)


# --------------------------------------------------------------------------
# Section 2 - spatial structure
# --------------------------------------------------------------------------

def section2():
    lines = []
    lines.append("## 2. Spatial structure (Part 5c, Moran's I)")
    lines.append("")
    lines.append(
        "*Sources: `output/part5_diagnostics/5c_moran_tract.csv`, "
        "`5c_moran_bg.csv`, `5d_zero_skew_tract.csv`, `5d_zero_skew_bg.csv`.*"
    )
    lines.append("")
    lines.append(
        "**Plain-language read:** k-nearest-neighbor weights with **k=6** were "
        "used for both grains (k=6 is a standard spatial-econometrics default "
        "approximating the typical count of contiguous neighbors on an urban "
        "tract/block-group grid; being distance- rather than contiguity-based, "
        "it avoids the zero-neighbor 'island' problem that a fixed distance "
        "band would create given this county's mix of dense urban tracts and "
        "large rural/parcel geography in the south). The core contrast: "
        "`investment_per_capita` shows **no significant spatial clustering** "
        "(I=0.006, p=0.0700) even though **every vulnerability variable tested "
        "is strongly and significantly clustered** (I up to 0.986), and the "
        "binary/composition outcomes sit in between (I=0.138-0.604, all "
        "significant)."
    )
    lines.append("")

    mt = pd.read_csv(P5 / "5c_moran_tract.csv")
    mb = pd.read_csv(P5 / "5c_moran_bg.csv")
    for df, grain in [(mt, "tract (698 units, k=6)"), (mb, "block group (1,843 units, k=6)")]:
        d = df.copy()
        d["highlight"] = d["variable"].isin(
            ["investment_per_capita", "investment_any_excl_county", "investment_any_single_unit"]
        ).map({True: "**outcome**", False: ""})
        out = d[["family", "variable", "n", "I", "p_sim", "z_sim", "highlight", "note"]].copy()
        out["note"] = out["note"].fillna("")
        md = df_to_md(out, {"I": fmt_coef, "p_sim": fmt_p, "z_sim": fmt_coef, "n": fmt_int})
        lines.append(f"### Moran's I - {grain}\n\n{md}\n")

    lines.append("### Zero share and skew per outcome variant (Part 5d)\n")
    zt = pd.read_csv(P5 / "5d_zero_skew_tract.csv")
    zb = pd.read_csv(P5 / "5d_zero_skew_bg.csv")
    for df, grain in [(zt, "tract"), (zb, "block group")]:
        d = df.copy()
        d["flag_50pct_zero"] = (d["pct_zero"] > 50).map({True: "**HURDLE CANDIDATE**", False: ""})
        md = df_to_md(d, {"skew": fmt_coef, "skew_nonzero_only": fmt_coef,
                          "n": fmt_int, "n_zero": fmt_int, "pct_zero": lambda x: f"{x:.1f}%"})
        lines.append(f"**{grain}** (n per variable = table's own `n` column)\n\n{md}\n")
    lines.append(
        "`path_single_unit_amt` at block group is the only variable in either "
        "profile exceeding 50% exact zeros (**68.5%**), flagged as the one "
        "genuine hurdle/two-part candidate; nothing else crosses that line at "
        "either grain."
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Section 3 - project-type / sparsity profile
# --------------------------------------------------------------------------

def section3():
    lines = []
    lines.append("## 3. Project-type, scale-tag, and allocation-path profile (Part 2)")
    lines.append("")
    lines.append("*Source: `output/part2_univariate/sparsity_baseline.csv`.*")
    lines.append("")
    lines.append(
        "**Plain-language read:** this is the sparsity context for Section 1 - "
        "`n_receiving_units_single_unit_only` is the number of units where a "
        "project was actually physically sited (footprint), separate from "
        "`n_receiving_units` which the automatic county allocation path "
        "inflates to nearly every unit regardless of category. Only **Blue** "
        "infrastructure falls under the 20-unit floor (19 single-unit-sited "
        "units at both grains), out of 1,405 filtered projects total "
        "($8,553,271,610)."
    )
    lines.append("")
    sp = pd.read_csv(P2 / "sparsity_baseline.csv")
    sp = sp.copy()
    sp["flag_sparse_lt20units"] = sp["flag_sparse_lt20units"].map({True: "**SPARSE**", False: ""})
    md = df_to_md(sp, {"n_projects": fmt_int, "n_receiving_units": fmt_int,
                       "n_receiving_units_single_unit_only": fmt_int,
                       "dollars": fmt_dollar})
    lines.append(md)
    lines.append("")
    lines.append(
        "Mean/median project size per category is **not computed** in this "
        "baseline table (it reports project count and dollars, not a "
        "per-project size distribution split by category) - deriving it now "
        "would be new computation, so it is left as \"not computed\" rather "
        "than calculated here."
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Section 4 - indicator structure
# --------------------------------------------------------------------------

def section4():
    lines = []
    lines.append("## 4. Indicator structure (Part 3)")
    lines.append("")
    lines.append(
        "*Sources: `output/part3_correlation/tract_high_corr_pairs.csv`, "
        "`bg_high_corr_pairs.csv`, `tract_vif.csv`, `bg_vif.csv`, "
        "`bg_excl_high_missing_vif.csv`, `tract_svi_vs_cre_overlap.csv`, "
        "`bg_flagged_duplicate_candidates.csv`, `tract_spearman.csv` (for the "
        "axis-divergence block), `bg_ejscreen_socio_vs_adi_full_cross.csv`, "
        "`bg_environmental_vs_adi_ej_question.csv`.*"
    )
    lines.append("")
    lines.append(
        "**Plain-language read:** the tract SVI/ACS-CRE overlap is a clean, "
        "confirmed redundancy (7 pairs, all |r|>0.8). At block group only 2 "
        "pairs exceed |r|>0.8, both inside EJScreen's air-quality block. VIF "
        "finds a second, different kind of redundancy at tract - "
        "race/ethnicity shares are collinear *in combination* even though no "
        "single pair crosses 0.8, because they are compositional (sum near "
        "100% of population)."
    )
    lines.append("")

    ht = pd.read_csv(P3 / "tract_high_corr_pairs.csv")
    hb = pd.read_csv(P3 / "bg_high_corr_pairs.csv")
    for df, grain in [(ht, "tract"), (hb, "block group")]:
        md = df_to_md(df.drop(columns=["abs_pearson"]),
                      {"pearson_r": fmt_coef, "spearman_rho": fmt_coef})
        lines.append(f"### 4a. Pairs with |Pearson r| > 0.8 - {grain} (n={len(df)} pairs)\n\n{md}\n")

    vt = pd.read_csv(P3 / "tract_vif.csv").sort_values("VIF", ascending=False)
    vb = pd.read_csv(P3 / "bg_vif.csv").sort_values("VIF", ascending=False)
    vb2 = pd.read_csv(P3 / "bg_excl_high_missing_vif.csv").sort_values("VIF", ascending=False)
    lines.append(f"### 4b. VIF - tract (34 vars, n=697 complete cases)\n\n"
                f"{df_to_md(vt, {'VIF': fmt_coef})}\n")
    lines.append(f"### 4b. VIF - block group, all 35 vars (n=495 complete cases - "
                f"note the large complete-case drop from 3 high-missingness "
                f"dollar variables)\n\n{df_to_md(vb, {'VIF': fmt_coef})}\n")
    lines.append(f"### 4b. VIF - block group, excluding the 3 high-missing "
                f"variables (n=1,185 complete cases, more representative)\n\n"
                f"{df_to_md(vb2, {'VIF': fmt_coef})}\n")

    ov = pd.read_csv(P3 / "tract_svi_vs_cre_overlap.csv")
    lines.append(f"### 4c. Tract SVI <-> ACS-CRE construct pairs (n=9)\n\n"
                f"{df_to_md(ov, {'pearson_r': fmt_coef, 'spearman_rho': fmt_coef, 'n': fmt_int})}\n")

    # axis divergence block - actual correlation values among the variables
    # that drove the divergence claim in correlation_analysis.md
    sp_t = pd.read_csv(P3 / "tract_spearman.csv", index_col=0)
    axis_vars = ["EP_NOVEH", "no_vehicle", "EP_MUNIT", "no_broadband", "EP_NOINT",
                "EP_MINRTY", "EP_HISP", "EP_AFAM"]
    block = sp_t.loc[axis_vars, axis_vars]
    lines.append(
        "### 4d. Race/ethnicity vs. access/connectivity axis divergence\n\n"
        "**No factor analysis or PCA was run anywhere in this analysis - "
        "not computed.** The two-axis language in `correlation_analysis.md` "
        "rests on the Part 4 sign-pattern evidence (Sections 1 and 5 of this "
        "file) plus the raw correlation block below - shown as-is, not "
        "smoothed into a cleaner story than it supports. The "
        "access/connectivity variables (`EP_NOVEH, no_vehicle, EP_MUNIT, "
        "no_broadband, EP_NOINT`) correlate 0.219-0.862 with each other - "
        "consistently positive, moderate-to-strong. The three race/ethnicity "
        "variables do **not** move together as cleanly: `EP_MINRTY` "
        "correlates moderately with both `EP_HISP` (0.383) and `EP_AFAM` "
        "(0.156), but `EP_HISP` and `EP_AFAM` correlate **-0.683** with each "
        "other (expected - they are largely competing shares of the same "
        "population base). Between blocks, `EP_MINRTY` and `EP_NOINT`/"
        "`no_broadband` show moderate positive correlation (0.379-0.448) "
        "rather than near-zero, while `EP_HISP` sits close to zero against "
        "every access/connectivity variable (-0.101 to 0.022). **The "
        "divergence is real for `EP_HISP` specifically and directionally "
        "visible in the Part 4 sign pattern, but the race/ethnicity block is "
        "not internally uniform, and this correlation block alone does not "
        "cleanly separate into two orthogonal axes** - read the two-axis "
        "framing in `correlation_analysis.md` as a description of the sign "
        "pattern in Sections 1/5, not as a validated factor structure.\n"
    )
    lines.append(df_to_md(block.reset_index().rename(columns={"index": "variable"}),
                          {c: fmt_coef for c in axis_vars}))
    lines.append("")

    dup = pd.read_csv(P3 / "bg_flagged_duplicate_candidates.csv")
    lines.append(
        "\n### 4e. Block-group EJScreen <-> ADI flagged duplicate candidates "
        "(4 pairs named in the analysis spec)\n\n"
        f"{df_to_md(dup, {'pearson_r': fmt_coef, 'spearman_rho': fmt_coef})}\n\n"
        "**Columns missing on each side, named explicitly:**\n\n"
        "- *no vehicle*: **absent on both sides.** EJScreen has no raw "
        "\"no vehicle\" column at all in this v2.3 extract (`PTRAF` is a "
        "traffic-proximity hazard measure, not a household-vehicle-access "
        "measure, and was not substituted). ADI also does not carry it - "
        "`DATA_PROCESSING.md` Sec 3 lists \"no motor vehicle\" among the "
        "components dropped from the ADI pull as a presumed EJScreen "
        "duplicate, so it was never collected there either.\n"
        "- *no internet*: **EJScreen has no raw \"no household internet\" "
        "column** in this extract. No ADI-side column either (ADI dropped it "
        "as a presumed EJScreen duplicate at the pull stage, per "
        "`DATA_PROCESSING.md` Sec 3) - both sides are absent.\n"
        "- *unemployment*: **EJScreen's `UNEMPPCT` exists** (present, not "
        "missing). The gap is on the **ADI side** - `DATA_PROCESSING.md` "
        "records unemployment as dropped from the ADI pull as a presumed "
        "EJScreen duplicate, so no ADI unemployment column was ever collected "
        "to correlate against.\n"
        "- *less-than-HS vs <9yrs-education*: **both sides present** "
        "(`LESSHSPCT`, `no_diploma_under9yrs`) - this is the one pair of the "
        "four that could actually be tested. Result: r=0.679, ρ=0.695, "
        "n=1,833 - high but well short of ~1.0, consistent with genuinely "
        "different thresholds (HS-diploma cut vs. 8th-grade cut) rather than "
        "duplication.\n"
    )

    ec = pd.read_csv(P3 / "bg_environmental_vs_adi_ej_question.csv")
    top_ec = ec.reindex(ec.pearson_r.abs().sort_values(ascending=False).index).head(20)
    lines.append(
        f"\n### 4f. EJScreen environmental (13) x ADI (13) co-location - top 20 "
        f"of {len(ec)} pairs by |r| (median |r| across all pairs = "
        f"{ec.pearson_r.abs().median():.3f})\n\n"
        f"{df_to_md(top_ec, {'pearson_r': fmt_coef, 'spearman_rho': fmt_coef, 'n': fmt_int})}\n"
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Section 5 - volume results
# --------------------------------------------------------------------------

def section5():
    lines = []
    lines.append("## 5. Volume results (Part 4a)")
    lines.append("")
    lines.append(
        "*Sources: `output/part4_investment_vs_indicators/4a_tract_volume_"
        "continuous.csv`, `4a_tract_volume_binary.csv`.*"
    )
    lines.append("")
    cont = pd.read_csv(P4 / "4a_tract_volume_continuous.csv")
    binr = pd.read_csv(P4 / "4a_tract_volume_binary.csv")
    max_rho = cont["spearman_rho"].abs().max()
    max_row = cont.loc[cont["spearman_rho"].abs().idxmax()]
    lines.append(
        f"**Plain-language read:** across all 5 volume outcomes x 34 "
        f"vulnerability variables (170 continuous pairs, tract grain), the "
        f"single strongest relationship anywhere in this table is "
        f"**{max_row['vuln_var']} vs. {max_row['outcome']}, Spearman "
        f"ρ={fmt_coef(max_row['spearman_rho'])}** - this is reported as weak "
        f"in `correlation_analysis.md`; the full table below is what makes "
        f"that verifiable rather than asserted. Pearson r is systematically "
        f"weaker than Spearman ρ throughout, consistent with the heavily "
        f"skewed dollar outcomes."
    )
    lines.append("")
    for outcome in ["investment_per_capita", "investment_total", "investment_per_area"]:
        sub = cont[cont.outcome == outcome].sort_values(
            "spearman_rho", key=lambda s: s.abs(), ascending=False)
        out = sub[["vuln_var", "n", "pearson_r", "pearson_p", "pearson_p_fdr",
                   "spearman_rho", "spearman_p", "spearman_p_fdr"]].rename(
            columns={"vuln_var": "variable"})
        md = df_to_md(out, {"pearson_r": fmt_coef, "pearson_p": fmt_p, "pearson_p_fdr": fmt_p,
                            "spearman_rho": fmt_coef, "spearman_p": fmt_p,
                            "spearman_p_fdr": fmt_p, "n": fmt_int})
        lines.append(f"### 5a. `{outcome}` vs. all 34 vulnerability variables (n={len(out)})\n\n{md}\n")

    for outcome in ["investment_any_excl_county", "investment_any_single_unit"]:
        sub = binr[binr.outcome == outcome].copy()
        sub["absdiff"] = (sub.mean_receiving - sub.mean_not).abs()
        sub = sub.sort_values("absdiff", ascending=False)
        out = sub[["vuln_var", "n_receiving", "n_not", "mean_receiving",
                   "mean_not", "mw_p", "mw_p_fdr"]].rename(columns={
            "vuln_var": "variable", "mw_p": "p_raw", "mw_p_fdr": "p_fdr"})
        md = df_to_md(out, {"mean_receiving": fmt_coef, "mean_not": fmt_coef,
                            "p_raw": fmt_p, "p_fdr": fmt_p,
                            "n_receiving": fmt_int, "n_not": fmt_int})
        lines.append(f"### 5b. `{outcome}` group comparison, all 34 variables "
                    f"(Mann-Whitney U, n={len(out)})\n\n{md}\n")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Section 6 - sensitivity checks
# --------------------------------------------------------------------------

def section6():
    lines = []
    lines.append("## 6. Sensitivity checks (Part 5a/5b)")
    lines.append("")
    lines.append(
        "*Sources: `output/part5_diagnostics/5a_pennsuco_influence.csv`, "
        "`5b_flag_large_project_influence.csv`.*"
    )
    lines.append("")
    a = pd.read_csv(P5 / "5a_pennsuco_influence.csv")
    b = pd.read_csv(P5 / "5b_flag_large_project_influence.csv")
    max_a = a["pct_change"].max()
    max_b = b["pct_change"].max()
    lines.append(
        f"**Plain-language read:** both checks are reported in "
        f"`correlation_analysis.md` as moving \"<2%\" on the substantive "
        f"relationships - the tables below show that literally: the largest "
        f"movement on any of the 10 headline pairs is "
        f"{max_a:.2f}% (Pennsuco removal) and {max_b:.2f}% "
        f"(flagged-unit removal), and in both cases the largest moves are on "
        f"pairs that are already near-zero (poverty), not on the substantive "
        f"vehicle/housing-density relationships."
    )
    lines.append("")
    a_r = a.rename(columns={"x": "outcome", "y": "vuln_var"})
    a_out = a_r[["outcome", "vuln_var", "n_all", "spearman_all", "n_excl",
                "spearman_excl_pennsuco", "abs_change", "pct_change"]]
    md = df_to_md(a_out, {"spearman_all": fmt_coef, "spearman_excl_pennsuco": fmt_coef,
                          "abs_change": fmt_coef, "pct_change": lambda x: f"{x:.2f}%",
                          "n_all": fmt_int, "n_excl": fmt_int})
    lines.append(f"### 6a. Pennsuco (12086981100) removed, headline tract pairs (n={len(a_out)})\n\n{md}\n")

    b_r = b.rename(columns={"x": "outcome", "y": "vuln_var"})
    b_out = b_r[["outcome", "vuln_var", "n_all", "spearman_all", "n_excl",
                "spearman_excl_flagged", "abs_change", "pct_change"]]
    md = df_to_md(b_out, {"spearman_all": fmt_coef, "spearman_excl_flagged": fmt_coef,
                          "abs_change": fmt_coef, "pct_change": lambda x: f"{x:.2f}%",
                          "n_all": fmt_int, "n_excl": fmt_int})
    lines.append(f"### 6b. 3 flag_large_project units removed, headline tract pairs (n={len(b_out)})\n\n{md}\n")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Section 7 - data caveats and open questions
# --------------------------------------------------------------------------

def section7():
    lines = []
    lines.append("## 7. Data caveats and open questions")
    lines.append("")
    lines.append(
        "*Sources: `output/variable_dictionary.csv`, "
        "`output/part2_univariate/univariate_tract_vulnerability.csv`, "
        "`univariate_bg_vulnerability.csv`, `correlation_analysis.md` build notes.*"
    )
    lines.append("")

    lines.append(
        "### 7a. EJScreen health-indicator mismatch\n\n"
        "`DATA_PROCESSING.md` describes EJScreen as carrying \"7 socioeconomic "
        "+ 5 health indicators.\" Only **2 of the 5 expected health "
        "indicators actually exist** as raw columns in the on-disk extract "
        "(`EJSCREEN_2024_BG_with_AS_CNMI_GU_VI.csv`, v2.3 reconstruction):\n\n"
        "| present | absent |\n|---|---|\n"
        "| `DISABILITYPCT` (% persons with disabilities) | not found under any name |\n"
        "| `LIFEEXPPCT` (% low life expectancy) | not found under any name |\n"
        "| | 3rd expected health indicator - absent |\n"
        "| | 4th expected health indicator - absent |\n"
        "| | 5th expected health indicator - absent |\n\n"
        "A full-header search of the file (231 columns, including all "
        "percentile/bin/popup-text variants) turned up no additional "
        "health-disparity columns under any recognizable name (life "
        "expectancy, heart disease, asthma, cancer, diabetes, stroke, COPD, "
        "mental health were all checked). **Unresolved**: either "
        "`DATA_PROCESSING.md`'s count of 5 is wrong for this file, or a "
        "different EJScreen product/vintage carries the other 3 and was never "
        "downloaded. Used what's actually there (2) rather than fabricate 3 more.\n"
    )

    # >20% missing, near-constant, rate outside [0,1]
    ut = pd.read_csv(P2 / "univariate_tract_vulnerability.csv")
    ub = pd.read_csv(P2 / "univariate_bg_vulnerability.csv")
    uto = pd.read_csv(P2 / "univariate_tract_outcomes.csv")
    ubo = pd.read_csv(P2 / "univariate_bg_outcomes.csv")

    def flag_table(df, label):
        f = df[df["flag_high_missing_gt20pct"] | df["flag_near_constant"] |
              df["flag_rate_outside_0_1"]]
        if f.empty:
            return f"**{label}**: none flagged.\n"
        cols = ["variable", "n", "n_missing", "pct_missing", "n_distinct",
               "flag_high_missing_gt20pct", "flag_near_constant", "flag_rate_outside_0_1"]
        md = df_to_md(f[cols], {"pct_missing": lambda x: f"{x:.1f}%", "n": fmt_int, "n_missing": fmt_int})
        return f"**{label}**\n\n{md}\n"

    lines.append("### 7b. Variables flagged >20% missing, near-constant, or rate outside [0,1]\n")
    lines.append(flag_table(ut, "Tract vulnerability (SVI EP_* + ACS CRE, n=34)"))
    lines.append(flag_table(ub, "Block-group vulnerability (EJScreen + ADI, n=35)"))
    lines.append(flag_table(uto, "Tract outcomes"))
    lines.append(flag_table(ubo, "Block-group outcomes"))
    lines.append(
        "Note on the 6 block-group environmental variables flagged "
        "\"rate outside [0,1]\" (`PNPL, PRMP, PTSDF, UST, PWDIS, DWATER`): "
        "**not a data bug** - these are EJScreen proximity/count scores in "
        "native units (e.g. facility counts within a distance band), not "
        "0-1 rates; the univariate profiler's rate-style bound check simply "
        "doesn't apply to them, as documented in `output/variable_dictionary.csv`.\n"
    )

    lines.append(
        "\n### 7c. The B25014 (block-group crowding) gap\n\n"
        "`DATA_PROCESSING.md`'s 13-component block-group ADI list includes "
        "B25014 (% households, >1 occupant/room), but only 12 of the 13 ADI "
        "tables had actually been downloaded to `block-group-level/ADI Data/`. "
        "**Flagged mid-build and resolved**: the user supplied the missing "
        "table (`block-group-level/ADI Data/B25014- Tenure by Occupants per "
        "Room/`, same 2024 ACS 5-Year vintage as its 12 siblings) before the "
        "analysis tables were built. All 13 ADI components are present in "
        "`blockgroup_analysis.csv`. Resolved, not an open item.\n"
    )

    lines.append(
        "\n### 7d. Other items flagged mid-build\n\n"
        "- **`income_disparity` (block group) is undefined, not merely "
        "missing, for 34.5% of block groups** (636 of 1,843: 619 with zero "
        "low-income households giving log(0)=-inf, 17 with zero high-income "
        "households giving /0). Left as `NaN` by construction of the "
        "log-ratio formula at fine geography, not imputed, not computed as a "
        "literal infinity. This is *why* `income_disparity` appears on the "
        ">20%-missing list above - the missingness is formula-driven, not a "
        "data-quality problem, and is unresolved only in the sense that no "
        "alternative formula was substituted.\n"
        "- **3 of the 4 block-group EJScreen<->ADI \"flagged duplicate\" "
        "pairs (Section 4e) could not be numerically checked** because a "
        "column was absent on one or both sides. This is a gap in the "
        "duplicate-candidate list itself, not resolved here - worth raising "
        "with whoever compiled that list.\n"
        "- **No factor analysis or PCA exists anywhere in this analysis** "
        "(Section 4d) - the two-axis read is supported only by the raw "
        "correlation block shown there, not by a formal dimension-reduction "
        "result. Unresolved / not attempted, by design (out of scope for a "
        "correlational analysis).\n"
        "- **Jurisdiction name variants in the source project data** "
        "(e.g. `MiamiBeach` vs `Miami Beach`) were normalized for the "
        "municipality-allocation join only; they were not corrected anywhere "
        "else and do not affect any table in this file.\n"
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------

def main():
    header = """# Results for Review — SCALE-R Investment × Vulnerability Correlation Analysis

**Compiled for a reader with no access to this directory.** Every number
below was pulled from existing output files, not recomputed. This is a
descriptive/correlational analysis only — nothing here was fit, tuned, or
validated as a predictive model, and no FEMA NRI or other physical-risk layer
is used anywhere (this is investment × vulnerability, not investment × risk ×
vulnerability).

**Grains:** tract = 698 units (of 707; 9 zero-population tracts excluded —
see `zero_population_investigation.md`). Block group = 1,843 units, none
excluded. Filtered project universe = 1,405 projects (Completed/Funded/
Ongoing only), $8,553,271,610 total allocated.

**Source files for this compilation, by section**, are named at the top of
each section below. The full narrative version of these results, with
plain-language framing throughout, is `correlation_analysis.md`. The
underlying scripts are `scripts/part2_univariate.py` through
`scripts/part5_diagnostics.py`.

**Table conventions:** coefficients rounded to 3 decimals (scientific
notation only if rounding to 3 decimals would show `0.000` for a genuinely
nonzero value); p-values rounded to 4 decimals, or scientific notation below
0.0001. `**` in a `sig` column = FDR-adjusted p < 0.05. `SPARSE` = fewer than
20 single-unit-sited receiving units behind this row (Section 3) — read as
flagged, not as a finding, regardless of its coefficient or p-value."""
    parts = [header, section1(), section2(), section3(), section4(),
            section5(), section6(), section7()]
    out_path = BASE / "RESULTS_FOR_REVIEW.md"
    out_path.write_text("\n\n---\n\n".join(parts))
    print(f"wrote {out_path} ({len(out_path.read_text().splitlines())} lines)")


if __name__ == "__main__":
    main()
