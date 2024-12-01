import streamlit as st
import pandas as pd

def calculate_metrics(df, decision_columns, decision_mapping):
    results = {}
    
    def map_score(decision):
        decision = str(decision)  # Ensure the decision is a string
        if pd.isna(decision) or decision_mapping.get(decision) == "Ignore":
            return (0, 0, 0)  # Ignore
        elif decision_mapping.get(decision) == "TP":
            return (1, 0, 0)
        elif decision_mapping.get(decision) == "FP":
            return (0, 0, 1)
        elif decision_mapping.get(decision) == "FN":
            return (0, 1, 0)
        else:
            return (0, 0, 0)  # Default to Ignore
    
    for event in df['Event Detail'].unique():
        event_rows = df[df['Event Detail'] == event]
        tp, fn, fp = 0, 0, 0
        
        for _, row in event_rows.iterrows():
            for col in decision_columns:
                row_tp, row_fn, row_fp = map_score(row[col])
                tp += row_tp
                fn += row_fn
                fp += row_fp
        
        precision = tp / (tp + fp) if tp + fp > 0 else 0
        recall = tp / (tp + fn) if tp + fn > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0
        
        results[event] = {
            "Precision": precision,
            "Recall": recall,
            "F1 Score": f1_score,
            "TP": tp,
            "FN": fn,
            "FP": fp
        }
    
    results_df = pd.DataFrame.from_dict(results, orient="index")
    results_df.reset_index(inplace=True)
    results_df.rename(columns={"index": "Event Detail"}, inplace=True)
    return results_df

# Streamlit app
st.title("The F1 Score Calculator")

# Upload the Excel file
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    # Load Excel file
    xls = pd.ExcelFile(uploaded_file)
    sheet_name = st.selectbox("Select Sheet", xls.sheet_names)
    df = pd.read_excel(xls, sheet_name=sheet_name)
    
    # Select the columns for Decision 1 and Decision 2
    decision_columns = st.multiselect("Select Decision Columns", df.columns)
    
    if decision_columns:
        # Extract unique values from the selected columns
        unique_decisions = set()
        for col in decision_columns:
            unique_decisions.update(df[col].dropna().unique())
        
        # Allow the user to map each unique value to TP, FP, FN, or Ignore
        st.write("Map Decisions to TP, FP, FN, or Ignore:")
        decision_mapping = {}
        for decision in sorted(unique_decisions):
            decision_mapping[decision] = st.selectbox(f"Map '{decision}' to:", ["TP", "FP", "FN", "Ignore"])
        
        if st.button("Calculate Metrics"):
            if 'Event Detail' not in df.columns:
                st.error("The sheet must contain an 'Event Detail' column.")
            else:
                results = calculate_metrics(df, decision_columns, decision_mapping)
                st.success("Metrics calculated successfully!")
                st.dataframe(results)

                # Download results
                csv = results.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name="metrics_results.csv",
                    mime="text/csv",
                )
