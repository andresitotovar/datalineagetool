import os
import re
import streamlit as st
import networkx as nx
from graphviz import Digraph

# Function to scan SQL files and map table names to file paths
def scan_sql_files(base_dir):
    table_file_map = {}
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.sql'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    content = f.read()
                    # Extract table name (e.g., G_Table)
                    match = re.search(r'\b(G_|S_|B_)[A-Za-z0-9_]+', file)
                    if match:
                        table_name = match.group(0)
                        table_file_map[table_name] = file_path
    return table_file_map

# Function to parse SQL and extract referenced tables
def extract_referenced_tables(sql_content):
    matches = re.findall(r'\b(G_|S_|B_)[A-Za-z0-9_]+', sql_content)
    return set(matches)

# Recursive function to build lineage
def build_lineage(table_name, table_file_map, visited):
    if table_name in visited:
        return []

    visited.add(table_name)
    file_path = table_file_map.get(table_name)
    if not file_path:
        return []

    with open(file_path, 'r') as f:
        content = f.read()
        referenced_tables = extract_referenced_tables(content)
        lineage = []
        for ref_table in referenced_tables:
            lineage.append((table_name, ref_table))
            lineage.extend(build_lineage(ref_table, table_file_map, visited))
        return lineage

# Function to visualize lineage using Graphviz
def visualize_lineage(lineage):
    dot = Digraph()
    for parent, child in lineage:
        dot.edge(parent, child)
    return dot

# Streamlit GUI
def main():
    st.title("Table Lineage Tracker")

    # Folder structure
    base_dir = "SQL/Extract"
    gold_dir = os.path.join(base_dir, "Gold")

    # Scan for Gold tables
    table_file_map = scan_sql_files(base_dir)
    gold_tables = [t for t in table_file_map.keys() if t.startswith('G_')]

    # Select Gold table
    selected_table = st.selectbox("Select a Gold Table", gold_tables)

    if selected_table:
        st.write(f"Selected Table: {selected_table}")

        # Build lineage
        visited = set()
        lineage = build_lineage(selected_table, table_file_map, visited)

        # Visualize graph
        st.subheader("Lineage Graph")
        graph = visualize_lineage(lineage)
        st.graphviz_chart(graph.source)

        # Display text-based hierarchy
        st.subheader("Text-Based Hierarchy")
        hierarchy = "\n".join([f"{parent} -> {child}" for parent, child in lineage])
        st.text(hierarchy)

        # Export options
        st.subheader("Export Options")
        if st.button("Export Graph as PNG"):
            graph.render("lineage_graph", format="png", cleanup=True)
            st.success("Graph exported as lineage_graph.png")

        if st.button("Export Hierarchy as Text"):
            with open("lineage_hierarchy.txt", "w") as f:
                f.write(hierarchy)
            st.success("Hierarchy exported as lineage_hierarchy.txt")

if __name__ == "__main__":
    main()
