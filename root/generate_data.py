import json
import os
from datetime import datetime
from functools import reduce

import numpy as np
import pandas as pd
import requests

# Put your Census API key here.
CENSUS_API_KEY =  "722729cfa99e33f0f76a6c4385beb4a6394f1728" # "your_key_here"

VARIABLES_ACS1 = {
    "Total_Population": "B01003_001E",
    "Laborforce_Population": "DP03_0002E",
    "Employed": "DP03_0004E",
    "Median_Household_Income": "S1903_C03_001E",
    "Total_Housing_Units": "B25002_001E",
    "House_Occupied": "B25002_002E",
    "House_Vacant": "B25002_003E",
    "Median_Gross_Rent": "B25064_001E",
    "5_to_9_units": "DP04_0011E",
    "10_to_19_units": "DP04_0012E",
    "20_or_more_units": "DP04_0013E",
}

DEFAULT_WEIGHTS = {
    "Economic_Index": 0.25,
    "Stability_Index": 0.15,
    "Supply_Index": 0.15,
    "Pricing_Index": 0.15,
    "Valuation_Index": 0.20,
    "Capital_Index": 0.10,
}


def census_base_url(year: int, var_code: str) -> str:
    if var_code.startswith("B"):
        return f"https://api.census.gov/data/{year}/acs/acs1"
    if var_code.startswith("S"):
        return f"https://api.census.gov/data/{year}/acs/acs1/subject"
    if var_code.startswith("D"):
        return f"https://api.census.gov/data/{year}/acs/acs1/profile"
    raise ValueError(f"Unsupported Census variable code prefix: {var_code}")


def fetch_msa_variable_recent_years(var_code: str, var_name: str, api_key: str, n_years: int) -> pd.DataFrame:
    current_year = datetime.today().year
    collected = []

    for year in range(current_year, current_year - 12, -1):
        if len(collected) >= n_years:
            break

        url = census_base_url(year, var_code)
        params = {
            "get": f"NAME,{var_code}",
            "for": "metropolitan statistical area/micropolitan statistical area:*",
            "key": api_key,
        }

        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                continue
            payload = resp.json()
        except Exception:
            continue

        if not payload or len(payload) <= 1:
            continue

        df = pd.DataFrame(payload[1:], columns=payload[0])
        if var_code not in df.columns:
            continue

        df = df.rename(
            columns={
                "NAME": "msa_name",
                "metropolitan statistical area/micropolitan statistical area": "msa_code",
                var_code: var_name,
            }
        )
        df[var_name] = pd.to_numeric(df[var_name], errors="coerce")
        df["year"] = year
        collected.append(df[["msa_code", "msa_name", "year", var_name]])

    if not collected:
        raise RuntimeError(f"No Census data fetched for {var_name} ({var_code}).")

    return pd.concat(collected, ignore_index=True)


def extract_principal_state(msa_name: str) -> str:
    return msa_name.split(", ")[1].split(" ")[0].split("-")[0]


def read_existing_path(options):
    for p in options:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"None of these files were found: {options}")


def robust_sigmoid(series: pd.Series, slope: float = 1.5) -> pd.Series:
    med = series.median()
    iqr = series.quantile(0.75) - series.quantile(0.25)
    if iqr == 0:
        return pd.Series(np.full(len(series), 50.0), index=series.index)
    z_robust = (series - med) / iqr
    return 100 / (1 + np.exp(-slope * z_robust))


def main():
    if CENSUS_API_KEY == "your_key_here":
        raise ValueError("Please set CENSUS_API_KEY in generate_data.py before running.")

    print("Fetching ACS1 variables...")
    frames = []
    for var_name, var_code in VARIABLES_ACS1.items():
        var_df = fetch_msa_variable_recent_years(
            var_code=var_code,
            var_name=var_name,
            api_key=CENSUS_API_KEY,
            n_years=6,
        )
        frames.append(var_df)

    msa_features = reduce(
        lambda left, right: pd.merge(
            left,
            right,
            on=["msa_code", "msa_name", "year"],
            how="outer",
        ),
        frames,
    )

    msa_features["msa_code"] = msa_features["msa_code"].astype(str)
    msa_features = msa_features.sort_values(["msa_code", "year"])

    msa_features['Total_Multi_Units']=msa_features['5_to_9_units']
    +msa_features['10_to_19_units']+msa_features['20_or_more_units']
    

    latest_year = int(msa_features["year"].max())
    eligible_codes = msa_features.loc[
        (msa_features["year"] == latest_year)
        & (msa_features["msa_name"].str.endswith("Metro Area"))
        & (msa_features["Total_Population"] >= 300000),
        "msa_code",
    ].unique()

    msa_features = msa_features[msa_features["msa_code"].isin(eligible_codes)].copy()

    print("Loading external Excel files...")
    tax_path = "../../../State Property Tax Comparison_ Hotels vs. Multifamily_New.xlsx"
    cap_path = "../../../Cap Rate Arbitrage Model Update.xlsx"
    opex_path = "../../../State OPEX Assumptions for Housing.xlsx"

    df_tax = pd.read_excel(tax_path, sheet_name="Tax new")
    df_tax["Diff_Effective_Rate"] = (
        pd.to_numeric(df_tax["Hotel Effective Rate"], errors="coerce")
        - pd.to_numeric(df_tax["Multifamily Effective Rate"], errors="coerce")
    )

    df_cap = pd.read_excel(cap_path)
    df_cap["Hotel Cap"] = pd.to_numeric(df_cap["Hotel Cap Rate"], errors="coerce")
    df_cap["Multifamily Cap"] = pd.to_numeric(df_cap["Apt Cap Rate"], errors="coerce")
    df_cap["Cap Spread"] = df_cap["Hotel Cap"] - df_cap["Multifamily Cap"]

    df_cap_tax = pd.merge(
        df_cap[["State Code", "State", "Hotel Cap", "Multifamily Cap", "Cap Spread"]],
        df_tax[["State", "Hotel Effective Rate", "Multifamily Effective Rate", "Diff_Effective_Rate"]],
        on="State",
        how="left",
    )

    df_oer = pd.read_excel(opex_path)
    df_oer = df_oer.rename(columns={"Default OPEX %": "OPEX%"})
    df_oer["State Code"] = df_oer["State Code"].astype(str)
    df_oer["OPEX%"] = pd.to_numeric(df_oer["OPEX%"], errors="coerce")

    print("Merging census + external datasets...")
    msa_features["State Code"] = msa_features["msa_name"].apply(extract_principal_state)

    msa_features = pd.merge(
        msa_features,
        df_cap_tax[
            [
                "State Code",
                "Hotel Cap",
                "Multifamily Cap",
                "Cap Spread",
                "Diff_Effective_Rate",
            ]
        ],
        on="State Code",
        how="left",
    )

    msa_features = pd.merge(
        msa_features,
        df_oer[["State Code", "OPEX%"]],
        on="State Code",
        how="left",
    )

    msa_features = msa_features.dropna().copy()
    msa_features = msa_features.sort_values(["msa_code", "year"]).reset_index(drop=True)

    print("Computing factors...")
    data = msa_features.copy()

    # ── 1. construct Economic factors ─────────────────────────────────────────────────
    data['Employment_Rate'] = data['Employed'] / data['Laborforce_Population']
    data['Employment_Growth'] = data.groupby(['msa_code'])['Employed'].pct_change()
    data['Pop_Growth'] = data.groupby(['msa_code'])['Total_Population'].pct_change()
    data['Income_Growth'] = data.groupby(['msa_code'])['Median_Household_Income'].pct_change()


    # ── 2. construct Housing Affordability factors ─────────────────────────────────────
    data['Rent_to_Income_Ratio'] = 12*data['Median_Gross_Rent'] / data['Median_Household_Income']
    data['Vacancy_Rate'] = data['House_Vacant'] / (data['House_Vacant'] + data['House_Occupied'])


    # ── 3. construct Supply Pressure factors ─────────────────────────────────────
    data['New_Multi_Units'] = data.groupby(['msa_code'])['Total_Multi_Units'].diff().clip(lower=0)


    # ── 4. construct Pricing Power factors ─────────────────────────────────────
    data['Rent_Growth'] = data.groupby(['msa_code'])['Median_Gross_Rent'].pct_change()


    # ── 5. construct valuation factors ─────────────────────────────────────
    data['Implied_Value'] = (data['Median_Gross_Rent']*12*(1-data['OPEX%'])) / data['Multifamily Cap']


    # ── 6. construct Market factors (already created before) ─────────────────────────────────────
    data['Effective Tax Spread'] = data['Diff_Effective_Rate']
    data['Value Creation'] = 1e6*(1/data['Multifamily Cap'] - 1/data['Hotel Cap'])


    # all useful factors (raw & newly constructed) for the sake of investors
    # 计划去除Market_Tightness、Value_Potential
    factor_list=['Employment_Rate', 'Employment_Growth', 'Pop_Growth', 'Income_Growth',
                 'Rent_to_Income_Ratio', 'Vacancy_Rate', 'New_Multi_Units', 'Rent_Growth',
                 'Implied_Value', 'Effective Tax Spread', 'Value Creation']

    latest_year = int(data["year"].max())
    raw_latest = data[data["year"] == latest_year].copy()
    raw_latest = raw_latest[["msa_code", "msa_name"] + factor_list].dropna().copy()

    print(f"Scoring year: {latest_year}, MSAs: {len(raw_latest)}")

    scored = raw_latest.copy()

    for col in factor_list:
        std = scored[col].std()
        if std == 0 or pd.isna(std):
            scored[col] = 0.0
        else:
            scored[col] = (scored[col] - scored[col].mean()) / std

    # Directional correction
    scored["Vacancy_Rate"] = -scored["Vacancy_Rate"]
    scored["Rent_to_Income_Ratio"] = -scored["Rent_to_Income_Ratio"]
    scored["New_Multi_Units"] = -scored["New_Multi_Units"]

    # Sub-indices
    scored["Economic_Index"] = scored[
        ["Employment_Rate", "Employment_Growth", "Pop_Growth", "Income_Growth"]
    ].mean(axis=1)
    scored["Stability_Index"] = scored[["Rent_to_Income_Ratio", "Vacancy_Rate"]].mean(axis=1)
    scored["Supply_Index"] = scored["New_Multi_Units"]
    scored["Pricing_Index"] = scored["Rent_Growth"]
    scored["Valuation_Index"] = scored["Implied_Value"]
    scored["Capital_Index"] = scored[["Effective Tax Spread", "Value Creation"]].mean(axis=1)

    scored["Index_Score_Raw"] = (
        DEFAULT_WEIGHTS["Economic_Index"] * scored["Economic_Index"]
        + DEFAULT_WEIGHTS["Stability_Index"] * scored["Stability_Index"]
        + DEFAULT_WEIGHTS["Supply_Index"] * scored["Supply_Index"]
        + DEFAULT_WEIGHTS["Pricing_Index"] * scored["Pricing_Index"]
        + DEFAULT_WEIGHTS["Valuation_Index"] * scored["Valuation_Index"]
        + DEFAULT_WEIGHTS["Capital_Index"] * scored["Capital_Index"]
    )

    # Linear transformation: z-score (-3 to 3) → score (0 to 100)
    # weighted_z_score = -3 → score = 0
    # weighted_z_score = 0  → score = 50
    # weighted_z_score = 3  → score = 100
    scored["Index_Score"] = ((scored["Index_Score_Raw"] + 3) / 6) * 100

    # Keep raw factors in JSON for dashboard raw-data tab.
    output = raw_latest.merge(
        scored[
            [
                "msa_code",
                "Economic_Index",
                "Stability_Index",
                "Supply_Index",
                "Pricing_Index",
                "Valuation_Index",
                "Capital_Index",
                "Index_Score",
            ]
        ],
        on="msa_code",
        how="left",
    )

    output_cols = [
        "msa_code",
        "msa_name",
        "Employment_Rate",
        "Employment_Growth",
        "Pop_Growth",
        "Income_Growth",
        "Rent_to_Income_Ratio",
        "Vacancy_Rate",
        "New_Multi_Units",
        "Rent_Growth",
        "Implied_Value",
        "Effective Tax Spread",
        "Value Creation",
        "Economic_Index",
        "Stability_Index",
        "Supply_Index",
        "Pricing_Index",
        "Valuation_Index",
        "Capital_Index",
        "Index_Score",
    ]

    output = output[output_cols].dropna().copy()
    output = output.sort_values("Index_Score", ascending=False).reset_index(drop=True)

    os.makedirs("data", exist_ok=True)
    payload = {
        "year": latest_year,
        "msas": output.round(6).to_dict(orient="records"),
    }

    with open("data/msa_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Exported {len(output)} MSAs -> data/msa_data.json")


if __name__ == "__main__":
    main()

