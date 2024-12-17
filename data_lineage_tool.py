import os
import sqlparse
import pandas as pd
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword
from graphviz import Digraph
import streamlit as st

# Function to extract table names and logic from SQL content
def extract_tables(sql_content):
    parsed = sqlparse.parse(sql_content)
    tables = set()
    logic_snippets = []
    
    for stmt in parsed:
        if stmt.get_type() == "SELECT":
            from_seen = False
            logic_snippets.append(str(stmt).strip())  # Store SQL logic
            for token in stmt.tokens:
                if from_seen and isinstance(token, (IdentifierList, Identifier)):
                    tables.add(token.get_real_name())
                if token.ttype is Keyword and token.value.upper() == "FROM":
                    from_seen = True
    return tables, logic_snippets

# Search for SQL files referencing the Gold table
def find_files_with_table(repo_path, gold_table):
    relevant_files = {}
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".sql"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    if gold_table.lower() in content:
                        tables, logic = extract_tables(content)
                        relevant_files[file_path] = {"tables": tables, "logic": logic}
    return relevant_files

# Recursively trace lineage
def trace_lineage(target_table, files):
    lineage = {}
    for file_path, details in files.items():
        if target_table in details["tables"]:
            lineage[target_table] = {"children": details["tables"], "file": file_path, "logic": details["logic"]}
            for table in details["tables"]:
                if table != target_table:
                    lineage.update(trace_lineage(table, files))
    return lineage

# Generate lineage visualization
def visualize_lineage(lineage):
    dot = Digraph(comment="Table Lineage")
    for parent, details in lineage.items():
        for child in details["children"]:
            dot.edge(child, parent, label=os.path.basename(details["file"]))
    return dot

# Streamlit GUI
def main():
    st.title("Repo-to-Table Lineage Mapping Tool")
    st.write("Trace table lineage starting from a specific Gold table.")

    # User Input
    repo_path = st.text_input("Enter the path to your SQL repo:", "")
    gold_table = st.text_input("Enter the Gold table name to trace lineage:", "")

    if repo_path and gold_table and st.button("Trace Lineage"):
        with st.spinner("Searching for relevant SQL files..."):
            relevant_files = find_files_with_table(repo_path, gold_table)
            if not relevant_files:
                st.error("No SQL files found referencing the specified Gold table.")
                return
            st.success(f"Found {len(relevant_files)} relevant SQL files.")

        with st.spinner("Tracing lineage..."):
            lineage = trace_lineage(gold_table, relevant_files)
            if not lineage:
                st.warning("No lineage found for the specified Gold table.")
                return

            # Display Lineage Table
            st.write("### Lineage Table:")
            lineage_data = []
            for parent, details in lineage.items():
                for child in details["children"]:
                    lineage_data.append([
                        parent, child, os.path.basename(details["file"]), "\n".join(details["logic"])
                    ])
            lineage_df = pd.DataFrame(lineage_data, columns=["Parent Table", "Child Table", "SQL File", "Logic Snippets"])
            st.dataframe(lineage_df)

            # Visualize Lineage
            st.write("### Lineage Visualization:")
            lineage_graph = visualize_lineage(lineage)
            st.graphviz_chart(lineage_graph.source)

            # Download Report
            st.write("### Download Lineage Report:")
            lineage_df.to_excel("table_lineage_report.xlsx", index=False)
            with open("table_lineage_report.xlsx", "rb") as file:
                st.download_button("Download Report", file, "table_lineage_report.xlsx")

if __name__ == "__main__":
    main()
