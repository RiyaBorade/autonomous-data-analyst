import os
import json
import pandas as pd
from scipy import stats
from agents.state import GraphState

def stats_agent_node(state: GraphState) -> GraphState:
    # Skip this agent if planner decided no stats are needed
    if not state["needs_stats"]:
        state["stats_result"] = ""
        return state

    # Skip if there is no SQL result
    if not state["sql_result"] or state["sql_result"] == "Query returned no rows.":
        state["stats_result"] = "No data available for statistical analysis."
        return state

    try:
        # Convert SQL result JSON string back into a Pandas DataFrame
        data = json.loads(state["sql_result"])
        df = pd.DataFrame(data)

        results = []

        # Basic shape info
        results.append(f"Rows returned: {len(df)}")
        results.append(f"Columns: {', '.join(df.columns.tolist())}")

        # Find numeric columns for analysis
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

        if numeric_cols:
            results.append("\nDescriptive statistics:")
            for col in numeric_cols:
                results.append(
                    f"  {col}: mean={df[col].mean():.2f}, "
                    f"min={df[col].min():.2f}, "
                    f"max={df[col].max():.2f}, "
                    f"std={df[col].std():.2f}"
                )

        # If exactly 2 numeric columns — run correlation
        if len(numeric_cols) == 2:
            corr, pvalue = stats.pearsonr(
                df[numeric_cols[0]].dropna(),
                df[numeric_cols[1]].dropna()
            )
            results.append(f"\nCorrelation between {numeric_cols[0]} and {numeric_cols[1]}:")
            results.append(f"  Pearson r = {corr:.3f}, p-value = {pvalue:.4f}")
            if pvalue < 0.05:
                results.append("  Result: Statistically significant correlation (p < 0.05)")
            else:
                results.append("  Result: No significant correlation (p >= 0.05)")

        # Warn if sample is small
        if len(df) < 30:
            results.append(f"\nWarning: Small sample size ({len(df)} rows). Interpret results carefully.")

        state["stats_result"] = "\n".join(results)

    except Exception as e:
        state["stats_result"] = f"Statistics could not be computed: {str(e)}"

    return state