import json
from datetime import datetime
from functools import reduce
from pathlib import Path

import numpy as np
import pandas as pd
import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
API_KEY = "722729cfa99e33f0f76a6c4385beb4a6394f1728"

VARIABLES_ACS1 = {
    "Total_Population": "B01003_001E",
    "Laborforce_Population": "DP03_0002E",
    "Employed": "DP03_0004E",
    "Median_Household_Income": "S1903_C03_001E",
    "Median_House_Value": "B25077_001E",
    "Total_Housing_Units": "B25002_001E",
    "House_Occupied": "B25002_002E",
    "House_Vacant": "B25002_003E",
    "Median_Gross_Rent": "B25064_001E",
    "5_to_9_units": "DP04_0011E",
    "10_to_19_units": "DP04_0012E",
    "20_or_more_units": "DP04_0013E",
}


def base_url(year: int, code: str) -> str:
    if code.startswith("S"):
        return f"https://api.census.gov/data/{year}/acs/acs1/subject"
    if code.startswith("B"):
        return f"https://api.census.gov/data/{year}/acs/acs1"
    if code.startswith("D"):
        return f"https://api.census.gov/data/{year}/acs/acs1/profile"
    raise ValueError(f"Unsupported code: {code}")


def fetch_recent_n_years(code: str, name: str, n_years: int = 6, max_lookback: int = 12) -> pd.DataFrame:
    current_year = datetime.today().year
    out = []

    for year in range(current_year, current_year - max_lookback, -1):
        if len(out) >= n_years:
            break

        params = {
            "get": f"NAME,{code}",
            "for": "metropolitan statistical area/micropolitan statistical area:*",
            "key": API_KEY,
        }
        response = requests.get(base_url(year, code), params=params, timeout=30)
        if response.status_code != 200:
            continue

        payload = response.json()
        if len(payload) <= 1:
            continue

        df = pd.DataFrame(payload[1:], columns=payload[0])
        if code not in df.columns:
            continue

        df = df.rename(
            columns={
                "NAME": "msa_name",
                "metropolitan statistical area/micropolitan statistical area": "msa_code",
                code: name,
            }
        )
        df[name] = pd.to_numeric(df[name], errors="coerce")
        df["year"] = year
        out.append(df[["msa_code", "msa_name", "year", name]])

    if not out:
        raise RuntimeError(f"No Census data fetched for {name} ({code}).")

    return pd.concat(out, ignore_index=True)


def extract_state(msa_name: str) -> str:
    return msa_name.split(", ")[1].split(" ")[0].split("-")[0]


def minmax01(series: pd.Series) -> pd.Series:
    low, high = series.min(), series.max()
    if pd.isna(low) or pd.isna(high) or high == low:
        return pd.Series(np.full(len(series), 0.5), index=series.index)
    return (series - low) / (high - low)


def load_existing_hers_map() -> dict[str, int]:
    existing_file = PROJECT_ROOT / "docs/data/sample_data.json"
    if not existing_file.exists():
        return {}

    with open(existing_file, "r", encoding="utf-8") as file:
        current = json.load(file)

    return {
        str(msa["msa_code"]): int(round(float(msa.get("Average HERS Index Score", 0))))
        for msa in current.get("msas", [])
    }


def build_payload() -> dict:
    frames = []
    for name, code in VARIABLES_ACS1.items():
        print(f"Fetching {name}...")
        frames.append(fetch_recent_n_years(code, name, n_years=6))

    msa_features = reduce(
        lambda left, right: pd.merge(left, right, on=["msa_code", "msa_name", "year"], how="outer"),
        frames,
    )
    msa_features["msa_code"] = msa_features["msa_code"].astype(str)
    msa_features = msa_features.sort_values(["msa_code", "year"])
    msa_features["Total_Multi_Units"] = (
        msa_features["5_to_9_units"] + msa_features["10_to_19_units"] + msa_features["20_or_more_units"]
    )

    latest_year = int(msa_features["year"].max())
    eligible_codes = msa_features.loc[
        (msa_features["year"] == latest_year)
        & (msa_features["Total_Population"] >= 300000)
        & (msa_features["msa_name"].str.endswith("Metro Area")),
        "msa_code",
    ].unique()
    msa_features = msa_features[msa_features["msa_code"].isin(eligible_codes)].copy()

    df_tax = pd.read_excel(PROJECT_ROOT / "State Property Tax Comparison_ Hotels vs. Multifamily_New.xlsx", sheet_name="Tax new")
    df_tax["Diff_Effective_Rate"] = (
        pd.to_numeric(df_tax["Hotel Effective Rate"], errors="coerce")
        - pd.to_numeric(df_tax["Multifamily Effective Rate"], errors="coerce")
    )

    df_cap = pd.read_excel(PROJECT_ROOT / "Cap Rate Arbitrage Model Update.xlsx")
    df_cap["Hotel Cap"] = pd.to_numeric(df_cap["Hotel Cap Rate"], errors="coerce")
    df_cap["Multifamily Cap"] = pd.to_numeric(df_cap["Apt Cap Rate"], errors="coerce")
    df_cap["Cap Spread"] = df_cap["Hotel Cap"] - df_cap["Multifamily Cap"]

    df_cap_tax = pd.merge(
        df_cap[["State Code", "State", "Hotel Cap", "Multifamily Cap", "Cap Spread"]],
        df_tax[["State", "Hotel Effective Rate", "Multifamily Effective Rate", "Diff_Effective_Rate"]],
        on="State",
        how="left",
    )

    msa_features["State Code"] = msa_features["msa_name"].apply(extract_state)
    msa_features = pd.merge(
        msa_features,
        df_cap_tax[
            [
                "State Code",
                "Hotel Cap",
                "Multifamily Cap",
                "Cap Spread",
                "Hotel Effective Rate",
                "Multifamily Effective Rate",
                "Diff_Effective_Rate",
            ]
        ],
        on="State Code",
        how="left",
    )

    df_oer = pd.read_excel(PROJECT_ROOT / "State OPEX Assumptions for Housing.xlsx")
    df_oer = df_oer.rename(columns={"Default OPEX %": "OPEX%"})
    df_oer["State Code"] = df_oer["State Code"].astype(str)
    df_oer["OPEX%"] = pd.to_numeric(df_oer["OPEX%"], errors="coerce")
    msa_features = pd.merge(msa_features, df_oer[["State Code", "OPEX%"]], on="State Code", how="left")

    msa_features = msa_features.dropna().copy().sort_values(["msa_code", "year"]).reset_index(drop=True)

    factor_df = msa_features.copy()
    # factor_df["Employment_Rate"] = factor_df["Employed"] / factor_df["Laborforce_Population"]
    # factor_df["Employment_Growth"] = factor_df.groupby("msa_code")["Employed"].pct_change()
    # factor_df["Pop_Growth"] = factor_df.groupby("msa_code")["Total_Population"].pct_change()
    # factor_df["Income_Growth"] = factor_df.groupby("msa_code")["Median_Household_Income"].pct_change()
    # factor_df["Rent_to_Income_Ratio"] = factor_df["Median_Gross_Rent"] / factor_df["Median_Household_Income"]
    # factor_df["Vacancy_Rate"] = factor_df["House_Vacant"] / factor_df["Total_Housing_Units"]
    # factor_df["New_Multi_Units"] = factor_df.groupby("msa_code")["Total_Multi_Units"].diff().clip(lower=0)
    # factor_df["Rent_Growth"] = factor_df.groupby("msa_code")["Median_Gross_Rent"].pct_change()
    # factor_df["Implied_Value"] = (
    #     factor_df["Median_Gross_Rent"] * 12 * (1 - factor_df["OPEX%"])
    # ) / factor_df["Multifamily Cap"]

    # ── 1. construct Economic factors ─────────────────────────────────────────────────
    factor_df['Employment_Rate'] = factor_df['Employed'] / factor_df['Laborforce_Population']
    factor_df['Employment_Growth'] = factor_df.groupby(['msa_code'])['Employed'].pct_change()
    factor_df['Pop_Growth'] = factor_df.groupby(['msa_code'])['Total_Population'].pct_change()
    factor_df['Income_Growth'] = factor_df.groupby(['msa_code'])['Median_Household_Income'].pct_change()

    # ── 2. construct Housing Affordability factors ─────────────────────────────────────
    factor_df['Rent_to_Income_Ratio'] = 12*factor_df['Median_Gross_Rent'] / factor_df['Median_Household_Income']
    factor_df['Vacancy_Rate'] = factor_df['House_Vacant'] / (factor_df['House_Vacant'] + factor_df['House_Occupied'])

    # ── 3. construct Supply Pressure factors ─────────────────────────────────────
    factor_df['New_Multi_Units'] = factor_df.groupby(['msa_code'])['Total_Multi_Units'].diff().clip(lower=0)


    # ── 4. construct Pricing Power factors ─────────────────────────────────────
    factor_df['Rent_Growth'] = factor_df.groupby(['msa_code'])['Median_Gross_Rent'].pct_change()

    # ── 5. construct valuation factors ─────────────────────────────────────
    factor_df['Implied_Value'] = (factor_df['Median_Gross_Rent']*12*(1-factor_df['OPEX%'])) / factor_df['Multifamily Cap']


    # ── 6. construct Market factors (already created before) ─────────────────────────────────────
    factor_df['Effective Tax Spread'] = factor_df['Diff_Effective_Rate']
    factor_df['Value Creation'] = 1e6*(1/factor_df['Multifamily Cap'] - 1/factor_df['Hotel Cap'])


    factor_cols = [
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
    ]

    earliest_year = int(factor_df["year"].min())
    factor_df = factor_df[factor_df["year"] > earliest_year].copy()
    factor_df = factor_df[
        [
            "msa_code",
            "msa_name",
            "year",
            "Total_Population",
            "Median_Gross_Rent",
            "Median_Household_Income",
            "Median_House_Value",
        ]
        + factor_cols
    ].dropna()

    latest_year = int(factor_df["year"].max())
    raw_latest = factor_df[factor_df["year"] == latest_year].copy()

    scored = raw_latest[["msa_code", "msa_name"] + factor_cols].copy()
    for col in factor_cols:
        std = scored[col].std()
        scored[col] = 0.0 if std == 0 or pd.isna(std) else (scored[col] - scored[col].mean()) / std

    scored["Vacancy_Rate"] = -scored["Vacancy_Rate"]
    scored["Rent_to_Income_Ratio"] = -scored["Rent_to_Income_Ratio"]
    scored["New_Multi_Units"] = -scored["New_Multi_Units"]

    scored["Economic_Index"] = scored[["Employment_Rate", "Employment_Growth", "Pop_Growth", "Income_Growth"]].mean(axis=1)
    scored["Stability_Index"] = scored[["Rent_to_Income_Ratio", "Vacancy_Rate"]].mean(axis=1)
    scored["Supply_Index"] = scored["New_Multi_Units"]
    scored["Pricing_Index"] = scored["Rent_Growth"]
    scored["Valuation_Index"] = scored["Implied_Value"]
    scored["Capital_Index"] = scored[["Effective Tax Spread", "Value Creation"]].mean(axis=1)

    scored["Index_Score_Raw"] = (
        0.25 * scored["Economic_Index"]
        + 0.15 * scored["Stability_Index"]
        + 0.15 * scored["Supply_Index"]
        + 0.15 * scored["Pricing_Index"]
        + 0.20 * scored["Valuation_Index"]
        + 0.10 * scored["Capital_Index"]
    )

    # Linear transformation: z-score (-3 to 3) → score (0 to 100)
    # weighted_z_score = -3 → score = 0
    # weighted_z_score = 0  → score = 50
    # weighted_z_score = 3  → score = 100
    scored["Investment_Score"] = ((scored["Index_Score_Raw"] + 3) / 6) * 100

    for col in [
        "Economic_Index",
        "Stability_Index",
        "Supply_Index",
        "Pricing_Index",
        "Valuation_Index",
        "Capital_Index",
    ]:
        scored[col] = minmax01(scored[col])

    hers_map = load_existing_hers_map()

    merged = raw_latest.merge(
        scored[
            [
                "msa_code",
                "Economic_Index",
                "Stability_Index",
                "Supply_Index",
                "Pricing_Index",
                "Valuation_Index",
                "Capital_Index",
                "Investment_Score",
            ]
        ],
        on="msa_code",
        how="inner",
    )

    records = []
    for _, row in merged.iterrows():
        msa_code = str(row["msa_code"])
        vacancy_rate = float(row["Vacancy_Rate"])
        implied_value = float(row["Implied_Value"])

        record = {
            "msa_code": int(msa_code),
            "msa_name": row["msa_name"],
            "year": latest_year,
            "Employment_Rate": float(row["Employment_Rate"]),
            "Employment_Growth": float(row["Employment_Growth"]),
            "Pop_Growth": float(row["Pop_Growth"]),
            "Income_Growth": float(row["Income_Growth"]),
            "Rent_to_Income_Ratio": float(row["Rent_to_Income_Ratio"]),
            "Vacancy_Rate": float(row["Vacancy_Rate"]),
            "New_Multi_Units": int(round(float(row["New_Multi_Units"]))),
            "Rent_Growth": float(row["Rent_Growth"]),
            "Implied_Value": implied_value,
            "Effective Tax Spread": float(row["Effective Tax Spread"]),
            "Value Creation": float(row["Value Creation"]),
            "Average HERS Index Score": hers_map.get(msa_code, 0),
            "Economic_Index": float(row["Economic_Index"]),
            "Stability_Index": float(row["Stability_Index"]),
            "Supply_Index": float(row["Supply_Index"]),
            "Pricing_Index": float(row["Pricing_Index"]),
            "Valuation_Index": float(row["Valuation_Index"]),
            "Capital_Index": float(row["Capital_Index"]),
            "Investment_Score": float(row["Investment_Score"]),
            "Total_Population": int(round(float(row["Total_Population"]))),
            "Median_Rent": int(round(float(row["Median_Gross_Rent"]))),
            "Median_Income": int(round(float(row["Median_Household_Income"]))),
            "Median_Home_Value": int(round(float(row["Median_House_Value"]))),
        }

        for key, value in list(record.items()):
            if isinstance(value, float):
                record[key] = round(value, 6)

        records.append(record)

    records.sort(key=lambda item: item["Investment_Score"], reverse=True)

    return {
        "stats": {
            "year": latest_year,
            "total_msa_count": len(records),
            "scoring_system": "6-Dimensional Index (Economic, Stability, Supply, Pricing, Valuation, Capital)",
        },
        "msas": records,
    }


def main() -> None:
    payload = build_payload()

    targets = [
        PROJECT_ROOT / "docs/data/sample_data.json",
    ]

    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        print(f"Updated: {target}")

    print(f"Year: {payload['stats']['year']} | MSA count: {payload['stats']['total_msa_count']}")
    print("Top 5 MSAs:")
    for msa in payload["msas"][:5]:
        print(f" - {msa['msa_name']} ({msa['Investment_Score']})")


if __name__ == "__main__":
    main()
