"""Plain-language labels and construct groupings for the professor-facing
document and its figures. No column codes appear in any figure axis or any
prose; the codes live only in the traceability column of the Section 2 table.

Construct groups (fixed display order):
    economic hardship, housing, access and mobility,
    demographic composition, health, environmental exposure

Within each construct, paired measures of the same underlying construct are
kept adjacent so the duplicate blocks fall on the diagonal in Figure 2.
"""

CONSTRUCT_ORDER = [
    "Economic hardship",
    "Housing",
    "Access and mobility",
    "Demographic composition",
    "Health",
    "Environmental exposure",
]

# code -> (plain label, construct, source short)
TRACT_VARS = {
    # --- economic hardship ---
    "EP_POV150": ("Below 150% of poverty line", "Economic hardship", "SVI"),
    "poverty_under125": ("Below 125% of poverty line", "Economic hardship", "ACS"),
    "EP_UNEMP": ("Unemployed", "Economic hardship", "SVI"),
    "no_fulltime_worker_hh": ("Households with no workers", "Economic hardship", "ACS"),
    "EP_HBURD": ("Housing cost burdened", "Economic hardship", "SVI"),
    "EP_NOHSDP": ("No high school diploma", "Economic hardship", "SVI"),
    "no_diploma_pop25": ("No high school diploma (adults 25+)", "Economic hardship", "ACS"),
    # --- housing ---
    "EP_MUNIT": ("Multi-unit housing structures", "Housing", "SVI"),
    "EP_MOBILE": ("Mobile homes", "Housing", "SVI"),
    "EP_CROWD": ("Crowded housing", "Housing", "SVI"),
    "crowding_over100": ("Crowded housing (over 1 per room)", "Housing", "ACS"),
    "EP_GROUPQ": ("Living in group quarters", "Housing", "SVI"),
    # --- access and mobility ---
    "EP_NOVEH": ("Households with no vehicle", "Access and mobility", "SVI"),
    "no_vehicle": ("Households with no vehicle (ACS)", "Access and mobility", "ACS"),
    "EP_NOINT": ("No internet access", "Access and mobility", "SVI"),
    "no_broadband": ("No broadband subscription", "Access and mobility", "ACS"),
    # --- demographic composition ---
    # Scope correction: the seven SVI adjunct race/ethnicity variables
    # (Hispanic, Black, Asian, two or more races, other race, American Indian
    # / Alaska Native, Native Hawaiian / Pacific Islander) are published
    # alongside the index but are not part of it, and were never in the
    # specification, which named one race measure. Removed from the tract set,
    # taking it from 34 variables to 27. They were also the sole source of the
    # compositional multicollinearity problem.
    "EP_MINRTY": ("Minority population share", "Demographic composition", "SVI"),
    "EP_LIMENG": ("Limited English speaking households", "Demographic composition", "SVI"),
    "limited_english_hh": ("Limited English speaking households (ACS)", "Demographic composition", "ACS"),
    "EP_AGE65": ("Aged 65 and over", "Demographic composition", "SVI"),
    "age65plus": ("Aged 65 and over (ACS)", "Demographic composition", "ACS"),
    "EP_AGE17": ("Aged 17 and under", "Demographic composition", "SVI"),
    "EP_SNGPNT": ("Single-parent households", "Demographic composition", "SVI"),
    # --- health ---
    "EP_UNINSUR": ("Without health insurance", "Health", "SVI"),
    "uninsured": ("Without health insurance (ACS)", "Health", "ACS"),
    "EP_DISABL": ("With a disability", "Health", "SVI"),
    "disability": ("With a disability (ACS)", "Health", "ACS"),
}

BG_VARS = {
    # --- economic hardship ---
    "LOWINCPCT": ("Low income", "Economic hardship", "EJScreen"),
    "poverty_under150": ("Below 150% of poverty line", "Economic hardship", "ADI"),
    "poverty_pct_families": ("Families below poverty line", "Economic hardship", "ADI"),
    "median_family_income": ("Median family income", "Economic hardship", "ADI"),
    "income_disparity": ("Income disparity (low to high earner ratio)", "Economic hardship", "ADI"),
    "UNEMPPCT": ("Unemployed", "Economic hardship", "EJScreen"),
    "LESSHSPCT": ("Less than high school education", "Economic hardship", "EJScreen"),
    "no_diploma_under9yrs": ("Under 9 years of schooling", "Economic hardship", "ADI"),
    # --- housing ---
    "median_home_value": ("Median home value", "Housing", "ADI"),
    "median_gross_rent": ("Median gross rent", "Housing", "ADI"),
    "median_monthly_mortgage": ("Median monthly mortgage cost", "Housing", "ADI"),
    "pct_owner_occupied": ("Owner-occupied homes", "Housing", "ADI"),
    "pct_crowding_over100": ("Crowded housing (over 1 per room)", "Housing", "ADI"),
    "pct_no_plumbing": ("Lacking complete plumbing", "Housing", "ADI"),
    "pct_no_kitchen": ("Lacking complete kitchen", "Housing", "ADI"),
    # --- access and mobility ---
    "no_vehicle": ("Households with no vehicle", "Access and mobility", "ACS"),
    "no_broadband": ("No broadband subscription", "Access and mobility", "ACS"),
    # --- demographic composition ---
    "PEOPCOLORPCT": ("People of colour share", "Demographic composition", "EJScreen"),
    "LINGISOPCT": ("Limited English speaking households", "Demographic composition", "EJScreen"),
    "pct_single_parent_children": ("Single-parent households with children", "Demographic composition", "ADI"),
    "OVER64PCT": ("Aged 65 and over", "Demographic composition", "EJScreen"),
    "UNDER5PCT": ("Aged under 5", "Demographic composition", "EJScreen"),
    # --- health ---
    "DISABILITYPCT": ("With a disability", "Health", "EJScreen"),
    "LIFEEXPPCT": ("Low life expectancy", "Health", "EJScreen"),
    # --- environmental exposure ---
    "PM25": ("Fine particulate matter", "Environmental exposure", "EJScreen"),
    "OZONE": ("Ozone", "Environmental exposure", "EJScreen"),
    "NO2": ("Nitrogen dioxide", "Environmental exposure", "EJScreen"),
    "DSLPM": ("Diesel particulate matter", "Environmental exposure", "EJScreen"),
    "RSEI_AIR": ("Air toxics released", "Environmental exposure", "EJScreen"),
    "PTRAF": ("Traffic proximity", "Environmental exposure", "EJScreen"),
    "PNPL": ("Superfund site proximity", "Environmental exposure", "EJScreen"),
    "PRMP": ("Chemical accident risk site proximity", "Environmental exposure", "EJScreen"),
    "PTSDF": ("Hazardous waste site proximity", "Environmental exposure", "EJScreen"),
    "UST": ("Underground storage tanks", "Environmental exposure", "EJScreen"),
    "PWDIS": ("Wastewater discharge", "Environmental exposure", "EJScreen"),
    "DWATER": ("Drinking water non-compliance", "Environmental exposure", "EJScreen"),
    "PRE1960PCT": ("Pre-1960 housing (lead paint indicator)", "Environmental exposure", "EJScreen"),
}

# outcome columns, plain language
OUTCOME_LABELS = {
    "type_gray_share": "Gray share",
    "type_green_share": "Green share",
    "type_blue_share": "Blue share",
    "type_hybrid_share": "Hybrid share",
    "investment_per_capita": "Investment per person",
}
SPARSE_OUTCOMES = {"type_blue_share"}  # 19 receiving units, below the 20-unit floor

GRAY_SUBCAT_LABELS = {
    # line breaks so the column labels do not collide at figure width
    "drainage_stormwater": "Drainage and\nstormwater",
    "water_sewer": "Water and\nsewer",
    "other_unclassified": "Other or\nunclassified",
    "road": "Road",
    "transit": "Transit",
}

# tract-grain receiving units (projects physically sited there), from
# output/part7_gray/2a_gray_subcategory_profile.csv. Shown in every column
# label so no category's base is invisible to a reader of the figure.
GRAY_SUBCAT_UNITS = {
    "drainage_stormwater": 298,
    "water_sewer": 21,
    "other_unclassified": 109,
    "road": 38,
    "transit": 2,
}

# two distinct markings, because these are two different problems:
#   sparse  = below the 20-unit floor, not interpretable at all
#   caution = clears the floor but only just, interpret with care
SPARSE_SUBCATS = {"transit"}        # 2 receiving units
CAUTION_SUBCATS = {"water_sewer"}   # 21 receiving units, largest coefficients


def ordered_vars(varmap):
    """Codes in construct order, preserving the within-construct order of the
    dict (which keeps paired measures adjacent)."""
    out = []
    for construct in CONSTRUCT_ORDER:
        out += [k for k, v in varmap.items() if v[1] == construct]
    return out


def label_of(code, varmap):
    return varmap[code][0] if code in varmap else code


def construct_of(code, varmap):
    return varmap[code][1] if code in varmap else "Other"
