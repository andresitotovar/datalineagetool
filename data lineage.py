import streamlit as st
import os
import sqlparse
import pandas as pd
from graphviz import Digraph

# Function to extract tables from SQL files
def extract_tables(sql):
    parsed = sqlparse.parse(sql)
    tables = set()
    for stmt in parsed:
        if stmt.get_type() == "SELECT":
            from_seen = False
            for token in stmt.tokens:
                if from_seen and isinstance(token, (sqlparse.sql.IdentifierList, sqlparse.sql.Identifier)):
                    tables.add(token.get_real_name())
                if token.ttype is sqlparse.tokens.Keyword and token.value.upper() == "FROM":
                    from_seen = True
    return tables

# Parse all SQL files in the directory
def parse_repo(directory):
    table_map = {}
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".sql"):
                with open(os.path.join(root, file), 'r') as f:
                    sql_content = f.read()
                    tables = extract_tables(sql_content)
                    table_map[file] = tables
    return table_map

# Recursive function to trace lineage
def trace_lineage(start_table, table_map, lineage=None):
    if lineage is None:
        lineage = {}
    for file, tables in table_map.items():
        if start_table in tables:
            lineage[start_table] = tables
            for table in tables:
                if table != start_table:
                    trace_lineage(table, table_map, lineage)
    return lineage

# Visualize lineage using Graphviz
def visualize_lineage(lineage):
    dot = Digraph(comment="Table Lineage")
    for parent, children in lineage.items():
        for child in children:
            dot.edge(child, parent)
    return dot

# Streamlit UI
def main():
    st.title("Repo-to-Table Lineage Mapping Tool")
    st.write("Select your SQL repo directory and choose a Gold table to trace lineage.")

    # Input: Repo folder path
    repo_path = st.text_input("Enter the path to your SQL repo:", "")

    # Button to parse repo
    if repo_path and st.button("Parse Repo"):
        with st.spinner("Parsing SQL files..."):
            table_map = parse_repo(repo_path)
            st.success("SQL files parsed successfully!")
            
            # Display parsed tables
            st.write("### Parsed Tables:")
            table_df = pd.DataFrame([(file, tables) for file, tables in table_map.items()],
                                    columns=["File Name", "Tables Found"])
            st.dataframe(table_df)

            # Input: Select Gold table
            gold_table = st.text_input("Enter the Gold table to start lineage tracing:", "")

            # Button to trace lineage
            if gold_table and st.button("Trace Lineage"):
                with st.spinner("Tracing lineage..."):
                    full_lineage = trace_lineage(gold_table, table_map)
                    st.success("Lineage traced successfully!")
                    
                    # Display lineage as a table
                    st.write("### Lineage Table:")
                    lineage_data = []
                    for parent, children in full_lineage.items():
                        for child in children:
                            lineage_data.append([parent, child])
                    lineage_df = pd.DataFrame(lineage_data, columns=["Parent Table", "Child Table"])
                    st.dataframe(lineage_df)
                    
                    # Visualize lineage
                    st.write("### Lineage Visualization:")
                    lineage_graph = visualize_lineage(full_lineage)
                    st.graphviz_chart(lineage_graph.source)

                    # Download lineage report
                    st.write("### Download Report:")
                    lineage_df.to_excel("lineage_report.xlsx", index=False)
                    with open("lineage_report.xlsx", "rb") as file:
                        st.download_button("Download Lineage Report", file, "lineage_report.xlsx")

if __name__ == "__main__":
    main()
