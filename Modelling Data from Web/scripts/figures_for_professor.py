"""Build the professor-facing figures from existing output CSVs.

Compile only: every value plotted is read from output/part2-part7, nothing is
recomputed. Plain-language axis labels throughout (no column codes).

Figure 1 (per grain) - vulnerability variables x outcome measures, Spearman
    rho, diverging scale centred at zero, FDR-significant cells marked.
    Only the outcome columns for which rho exists in the outputs are drawn:
    5 at tract, 4 at block group. The two binary outcomes were tested with
    rank-based group comparisons (no rho computed) and appear as a table in
    the document instead; block-group investment per capita was deliberately
    never correlated under the earlier instability decision.
Figure 2 (per grain) - indicator-by-indicator Spearman matrix, ordered by
    construct so duplicate blocks fall on the diagonal, confirmed duplicate
    pairs boxed, race/ethnicity block boxed.
Figure 3 - access and mobility variables x gray sub-category shares,
    zero-order and density-controlled, sparse categories marked.

Usage: python scripts/figures_for_professor.py
Outputs: output/figures_professor/*.png
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from professor_labels import (  # noqa: E402
    BG_VARS, CONSTRUCT_ORDER, GRAY_SUBCAT_LABELS, OUTCOME_LABELS, SPARSE_OUTCOMES,
    CAUTION_SUBCATS, GRAY_SUBCAT_UNITS, SPARSE_SUBCATS, TRACT_VARS,
    construct_of, label_of, ordered_vars,
)
from scaler_projects import OUTPUT_DIR  # noqa: E402

FIGDIR = OUTPUT_DIR / "figures_professor"
FIGDIR.mkdir(exist_ok=True)
P3 = OUTPUT_DIR / "part3_correlation"
P4 = OUTPUT_DIR / "part4_investment_vs_indicators"
P7 = OUTPUT_DIR / "part7_gray"

DPI = 200
CMAP = "RdBu_r"

# the seven confirmed duplicate pairs (|r| > 0.8), from Part 3
TRACT_DUPLICATE_PAIRS = [
    ("EP_NOVEH", "no_vehicle"), ("EP_NOHSDP", "no_diploma_pop25"),
    ("EP_AGE65", "age65plus"), ("EP_NOINT", "no_broadband"),
    ("EP_UNINSUR", "uninsured"), ("EP_LIMENG", "limited_english_hh"),
    ("EP_POV150", "poverty_under125"),
]
BG_DUPLICATE_PAIRS = [("PM25", "OZONE"), ("PM25", "DSLPM")]
# The compositional race block is gone with the scope correction: only one
# race measure remains in scope, so there is no longer a block to outline.
TRACT_RACE_BLOCK = []


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def construct_bands(codes, varmap):
    """[(construct, start_index, end_index_exclusive), ...] in display order."""
    bands, start = [], 0
    for i, c in enumerate(codes):
        if i > 0 and construct_of(c, varmap) != construct_of(codes[i - 1], varmap):
            bands.append((construct_of(codes[i - 1], varmap), start, i))
            start = i
    bands.append((construct_of(codes[-1], varmap), start, len(codes)))
    return bands


def draw_band_separators(ax, bands, axis="both"):
    # imshow centres cell i at coordinate i, so the boundary between cells
    # end-1 and end sits at end - 0.5; drawing at `end` strikes through the
    # next row's label.
    for _, _, end in bands[:-1]:
        if axis in ("both", "y"):
            ax.axhline(end - 0.5, color="black", lw=1.4)
        if axis in ("both", "x"):
            ax.axvline(end - 0.5, color="black", lw=1.4)


# --------------------------------------------------------------------------
# Figure 1
# --------------------------------------------------------------------------

def figure1(grain):
    varmap = TRACT_VARS if grain == "tract" else BG_VARS
    codes = ordered_vars(varmap)

    type_file = (P4 / "4b_tract_type_composition_continuous.csv" if grain == "tract"
                 else P4 / "4d_bg_type_composition_continuous.csv")
    tc = pd.read_csv(type_file)
    tc = tc[tc["measure"] == "share"]

    cols, rho, fdr = [], {}, {}
    for t in ["gray", "green", "blue", "hybrid"]:
        key = f"type_{t}_share"
        cols.append(key)
        sub = tc[tc["group"] == t].set_index("vuln_var")
        rho[key] = sub["spearman_rho"]
        fdr[key] = sub["spearman_p_fdr"]

    if grain == "tract":
        vc = pd.read_csv(P4 / "4a_tract_volume_continuous.csv")
        sub = vc[vc["outcome"] == "investment_per_capita"].set_index("vuln_var")
        cols.append("investment_per_capita")
        rho["investment_per_capita"] = sub["spearman_rho"]
        fdr["investment_per_capita"] = sub["spearman_p_fdr"]

    M = pd.DataFrame({c: rho[c].reindex(codes) for c in cols}, index=codes)
    F = pd.DataFrame({c: fdr[c].reindex(codes) for c in cols}, index=codes)

    vmax = float(np.nanmax(np.abs(M.values)))
    vmax = np.ceil(vmax * 20) / 20

    fig, ax = plt.subplots(figsize=(1.55 * len(cols) + 5.2, 0.30 * len(codes) + 2.0))
    im = ax.imshow(M.values, cmap=CMAP, vmin=-vmax, vmax=vmax, aspect="auto")

    for i in range(len(codes)):
        for j, c in enumerate(cols):
            v = M.iloc[i, j]
            if pd.isna(v):
                continue
            sig = pd.notna(F.iloc[i, j]) and F.iloc[i, j] < 0.05
            ax.text(j, i, f"{v:+.2f}" + ("*" if sig else ""),
                    ha="center", va="center", fontsize=7.4,
                    color="white" if abs(v) > vmax * 0.62 else "black",
                    fontweight="bold" if sig else "normal")

    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([OUTCOME_LABELS[c] + ("\n(sparse)" if c in SPARSE_OUTCOMES else "")
                        for c in cols], fontsize=9)
    ax.set_yticks(range(len(codes)))
    ax.set_yticklabels([label_of(c, varmap) for c in codes], fontsize=8)

    bands = construct_bands(codes, varmap)
    draw_band_separators(ax, bands, axis="y")
    for name, s, e in bands:
        # a short band cannot fit its label on one rotated line without
        # colliding with its neighbours, so wrap onto one word per line
        height = e - s
        text = name.upper() if height >= 6 else "\n".join(name.upper().split())
        ax.text(len(cols) - 0.35, (s + e - 1) / 2, text,
                rotation=270, va="center", ha="left",
                fontsize=7.6 if height >= 6 else 6.4,
                linespacing=0.95, color="#333333", fontweight="bold")

    grain_label = "census tracts (n = 698)" if grain == "tract" else "block groups (n = 1,843)"
    ax.set_title(f"Figure 1{'a' if grain == 'tract' else 'b'}. Vulnerability indicators against "
                 f"investment outcomes\n{grain_label}. Spearman correlation; "
                 f"* and bold = significant after false-discovery-rate adjustment",
                 fontsize=10.5, pad=12)
    fig.colorbar(im, ax=ax, fraction=0.022, pad=0.13, label="Spearman correlation")
    plt.tight_layout()
    out = FIGDIR / f"figure1_{grain}_variables_vs_outcomes.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out} ({len(codes)} variables x {len(cols)} outcomes)")


# --------------------------------------------------------------------------
# Figure 2
# --------------------------------------------------------------------------

def figure2(grain):
    varmap = TRACT_VARS if grain == "tract" else BG_VARS
    codes = ordered_vars(varmap)
    mat = pd.read_csv(P3 / f"{'tract' if grain == 'tract' else 'bg'}_spearman.csv",
                      index_col=0)
    M = mat.loc[codes, codes]

    n = len(codes)
    fig, ax = plt.subplots(figsize=(0.34 * n + 4.6, 0.34 * n + 3.2))
    im = ax.imshow(M.values, cmap=CMAP, vmin=-1, vmax=1)

    ax.set_xticks(range(n))
    ax.set_xticklabels([label_of(c, varmap) for c in codes], rotation=90, fontsize=7.4)
    ax.set_yticks(range(n))
    ax.set_yticklabels([label_of(c, varmap) for c in codes], fontsize=7.4)

    bands = construct_bands(codes, varmap)
    draw_band_separators(ax, bands)

    idx = {c: i for i, c in enumerate(codes)}
    pairs = TRACT_DUPLICATE_PAIRS if grain == "tract" else BG_DUPLICATE_PAIRS
    for a, b in pairs:
        if a not in idx or b not in idx:
            continue
        for (r, c) in [(idx[a], idx[b]), (idx[b], idx[a])]:
            ax.add_patch(patches.Rectangle((c - 0.5, r - 0.5), 1, 1, fill=False,
                                           edgecolor="#111111", lw=2.0))
    rb = [idx[c] for c in TRACT_RACE_BLOCK if c in idx]
    if grain == "tract" and rb:
        lo, hi = min(rb), max(rb)
        ax.add_patch(patches.Rectangle((lo - 0.5, lo - 0.5), hi - lo + 1, hi - lo + 1,
                                       fill=False, edgecolor="#1a7f37", lw=2.4,
                                       linestyle="--"))

    grain_label = "census tracts (n = 698)" if grain == "tract" else "block groups (n = 1,843)"
    note = ("Black boxes: the seven confirmed duplicate pairs."
            if grain == "tract" else
            "Black boxes: the two confirmed duplicate pairs (both within air quality).")
    ax.set_title(f"Figure 2{'a' if grain == 'tract' else 'b'}. Redundancy among the "
                 f"indicators\n{grain_label}. Spearman correlation, ordered by construct.\n{note}",
                 fontsize=10.5, pad=12)
    fig.colorbar(im, ax=ax, fraction=0.030, pad=0.02, label="Spearman correlation")
    plt.tight_layout()
    out = FIGDIR / f"figure2_{grain}_indicator_redundancy.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out} ({n} x {n})")


# --------------------------------------------------------------------------
# Figure 3
# --------------------------------------------------------------------------

def figure3():
    d = pd.read_csv(P7 / "2b_subcat_vs_access_tract.csv")
    # "other or unclassified" is 23.6% of gray dollars and 109 receiving
    # units; omitting it would imply the decomposition is complete when it
    # covers only about three quarters of gray spending.
    subcats = ["drainage_stormwater", "water_sewer", "other_unclassified",
               "road", "transit"]
    order = ["EP_NOVEH", "no_vehicle", "EP_MUNIT", "EP_NOINT", "no_broadband"]

    panels = [("zero_order_rho", "Before density control"),
              ("partial_rho", "After controlling for population density")]
    fig, axes = plt.subplots(1, 2, figsize=(15.4, 4.1), sharey=True)

    vmax = 0.30
    for ax, (valcol, title) in zip(axes, panels):
        M = pd.DataFrame(index=order, columns=subcats, dtype=float)
        S = pd.DataFrame(index=order, columns=subcats, dtype=float)
        for cat in subcats:
            sub = d[d["subcategory"] == cat].set_index("variable")
            M[cat] = sub[valcol].reindex(order)
            S[cat] = sub["p_partial_fdr"].reindex(order)
        im = ax.imshow(M.values.astype(float), cmap=CMAP, vmin=-vmax, vmax=vmax, aspect="auto")
        for i in range(len(order)):
            for j, cat in enumerate(subcats):
                v = M.iloc[i, j]
                if pd.isna(v):
                    continue
                sig = pd.notna(S.iloc[i, j]) and S.iloc[i, j] < 0.05 and valcol == "partial_rho"
                ax.text(j, i, f"{v:+.2f}" + ("*" if sig else ""), ha="center", va="center",
                        fontsize=8.6, color="white" if abs(v) > vmax * 0.62 else "black",
                        fontweight="bold" if sig else "normal")
        labels = []
        for c in subcats:
            tag = ""
            if c in SPARSE_SUBCATS:
                tag = "\nTOO SPARSE"
            elif c in CAUTION_SUBCATS:
                tag = "\nCAUTION"
            labels.append(f"{GRAY_SUBCAT_LABELS[c]}\n({GRAY_SUBCAT_UNITS[c]} units){tag}")
        ax.set_xticks(range(len(subcats)))
        ax.set_xticklabels(labels, fontsize=8.4)
        ax.set_title(title, fontsize=10)
        for j, cat in enumerate(subcats):
            # red = not interpretable at all; amber = interpret with caution
            edge = ("#b30000" if cat in SPARSE_SUBCATS
                    else "#d98200" if cat in CAUTION_SUBCATS else None)
            if edge:
                ax.add_patch(patches.Rectangle((j - 0.5, -0.5), 1, len(order),
                                               fill=False, edgecolor=edge, lw=2.2,
                                               linestyle="--"))
    axes[0].set_yticks(range(len(order)))
    axes[0].set_yticklabels([label_of(c, TRACT_VARS) for c in order], fontsize=9)

    fig.suptitle(
        "Figure 3. Where the gray infrastructure relationship actually lives\n"
        "Census tracts (n = 698). Access and mobility indicators against each gray "
        "sub-category's share of a tract's investment. Unit counts in each column "
        "label are the tracts where a project of that type was sited.\n"
        "* and bold = significant after false-discovery-rate adjustment.  "
        "Amber dashed (water and sewer, 21 units): clears the 20-unit floor only just, "
        "carries the largest coefficients here, interpret with caution.  "
        "Red dashed (transit, 2 units): too sparse to interpret at all.",
        fontsize=10.2, y=1.20)
    fig.colorbar(im, ax=axes, fraction=0.018, pad=0.02, label="Spearman correlation")
    out = FIGDIR / "figure3_gray_decomposition.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out} ({len(order)} indicators x {len(subcats)} sub-categories)")


def main():
    figure1("tract")
    figure1("bg")
    figure2("tract")
    figure2("bg")
    figure3()


if __name__ == "__main__":
    main()
