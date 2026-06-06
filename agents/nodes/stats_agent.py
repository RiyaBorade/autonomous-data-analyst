import os
import json
import pandas as pd
from scipy import stats
from agents.state import GraphState

def stats_agent_node(state: GraphState) -> GraphState:
    # Skip if planner decided no stats needed
    if not state["needs_stats"]:
        state["stats_result"] = ""
        return state

    # Skip if no data
    if not state["sql_result"] or state["sql_result"] == "Query returned no rows.":
        state["stats_result"] = "No data available for statistical analysis."
        return state

    try:
        # Convert SQL result into DataFrame
        data = json.loads(state["sql_result"])
        df = pd.DataFrame(data)

        results = []
        results.append(f"Rows returned: {len(df)}")
        results.append(f"Columns: {', '.join(df.columns.tolist())}")

        # Convert any numeric-looking string columns to numbers
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:
                pass

        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        text_cols = df.select_dtypes(include="object").columns.tolist()

        # Descriptive stats for all numeric columns
        if numeric_cols:
            results.append("\nDescriptive statistics:")
            for col in numeric_cols:
                results.append(
                    f"  {col}: mean={df[col].mean():.2f}, "
                    f"min={df[col].min():.2f}, "
                    f"max={df[col].max():.2f}, "
                    f"std={df[col].std():.2f}"
                )

        # Correlation — run for any 2 numeric columns found in question
        question = state["user_question"].lower()
        if "correlation" in question or "relationship" in question or "vs" in question:
            if len(numeric_cols) >= 2:
                results.append("\nCorrelation analysis:")
                # Run correlation for every pair of numeric columns
                for i in range(len(numeric_cols)):
                    for j in range(i + 1, len(numeric_cols)):
                        col_a = numeric_cols[i]
                        col_b = numeric_cols[j]
                        try:
                            clean = df[[col_a, col_b]].dropna()
                            if len(clean) >= 2:
                                corr, pvalue = stats.pearsonr(clean[col_a], clean[col_b])
                                significance = "significant" if pvalue < 0.05 else "not significant"
                                strength = (
                                    "strong" if abs(corr) > 0.7
                                    else "moderate" if abs(corr) > 0.4
                                    else "weak"
                                )
                                direction = "positive" if corr > 0 else "negative"
                                results.append(
                                    f"  {col_a} vs {col_b}: "
                                    f"r={corr:.3f} ({strength} {direction}), "
                                    f"p={pvalue:.4f} ({significance})"
                                )
                        except Exception:
                            pass

        # Distribution breakdown for categorical columns
        if text_cols and numeric_cols:
            results.append("\nBreakdown by category:")
            for cat_col in text_cols[:2]:  # Max 2 categorical columns
                for num_col in numeric_cols[:2]:  # Max 2 numeric columns
                    try:
                        grouped = df.groupby(cat_col)[num_col].agg(['mean', 'sum', 'count'])
                        results.append(f"  {num_col} by {cat_col}:")
                        for idx, row in grouped.iterrows():
                            results.append(
                                f"    {idx}: mean={row['mean']:.2f}, "
                                f"total={row['sum']:.2f}, count={int(row['count'])}"
                            )
                    except Exception:
                        pass

        # Small sample warning
        if len(df) < 30:
            results.append(f"\nWarning: Small sample ({len(df)} rows). Interpret carefully.")

        state["stats_result"] = "\n".join(results)

    except Exception as e:
        state["stats_result"] = f"Statistics could not be computed: {str(e)}"

    return state