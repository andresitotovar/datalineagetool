import os
import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword
import pandas as pd
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
            logic_snippets.append(str(stmt).strip())  # Save query logic
            for token in stmt.tokens:
                if from_seen and isinstance(token, (IdentifierList, Identifier)):
                    tables.add(token.get_real_name())
                if token.ttype is Keyword and token.value.upper() == "FROM":
                    from_seen = True
    return tables, logic_snippets

# Search all SQL files for the target table
def find_files_with_table(repo_path, target_table):
    relevant_files = {}
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".sql"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    if target_table.lower() in content:
                        tables, logic = extract_tables(content)
                        relevant_files[file_path] = {"tables": tables, "logic": logic}
    return relevant_files

# Recursive function to trace lineage
def trace_lineage(target_table, repo_path, lineage=None, visited_files=None):
    if lineage is None:
        lineage = {}
    if visited_files is None:
        visited_files = set()

    relevant_files = find_files_with_table(repo_path, target_table)
    for file_path, details in relevant_files.items():
        if file_path in visited_files:
            continue  # Avoid re-parsing the same file
        visited_files.add(file_path)

        if target_table not in lineage:
            lineage[target_table] = []

        for table in details["tables"]:
            if table != target_table and table not in lineage[target_table]:
                lineage[target_table].append((table, file_path, details["logic"]))
                trace_lineage(table, repo_path, lineage, visited_files)

    return lineage

# Generate a visual lineage graph
def visualize_lineage(lineage):
    dot = Digraph(comment="Full Table Lineage")
    for parent, children in lineage.items():
        for child, file_path, _ in children:
            dot.edge(child, parent, label=os.path.basename(file_path))
    return dot

# Streamlit UI
def main():
    st.title("Cross-Folder Repo-to-Table Lineage Mapping Tool")
    st.write("Trace table lineage across folders starting from a Gold table.")

    # User input
    repo_path = st.text_input("Enter the path to your SQL repo:", "")
    gold_table = st.text_input("Enter the Gold table name to trace lineage:", "")

    if repo_path and gold_table and st.button("Trace Lineage"):
        with st.spinner("Tracing lineage across folders..."):
            full_lineage = trace_lineage(gold_table, repo_path)
            if not full_lineage:
                st.error("No lineage found for the specified Gold table.")
                return

            # Prepare lineage table for display
            st.write("### Lineage Table:")
            lineage_data = []
            for parent, children in full_lineage.items():
                for child, file, logic in children:
                    lineage_data.append([parent, child, os.path.basename(file), "\n".join(logic[:2])])  # First 2 lines of logic
            lineage_df = pd.DataFrame(lineage_data, columns=["Parent Table", "Child Table", "SQL File", "Logic Snippet"])
            st.dataframe(lineage_df)

            # Visualize lineage graph
            st.write("### Lineage Visualization:")
            lineage_graph = visualize_lineage(full_lineage)
            st.graphviz_chart(lineage_graph.source)

            # Download report
            st.write("### Download Lineage Report:")
            lineage_df.to_excel("cross_folder_lineage_report.xlsx", index=False)
            with open("cross_folder_lineage_report.xlsx", "rb") as file:
                st.download_button("Download Report", file, "cross_folder_lineage_report.xlsx")

if __name__ == "__main__":
    main()
