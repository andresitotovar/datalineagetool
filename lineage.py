import os
import re
import streamlit as st
import networkx as nx
from graphviz import Digraph

# Function to scan SQL files and map table names to file paths
def scan_sql_files(base_dir):
    # Dictionary to map table names to their respective SQL file paths
    table_file_map = {}
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.sql'):  # Process only .sql files
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    content = f.read().lower()  # Convert content to lowercase
                    # Extract table name (e.g., g_table) from the file name
                    match = re.search(r'\b(g_|s_|b_)[a-z0-9_]+', file.lower())
                    if match:
                        table_name = match.group(0)
                        table_file_map[table_name] = file_path  # Map table name to file path
    return table_file_map

# Function to parse SQL content and extract referenced table names
def extract_referenced_tables(sql_content):
    # Find all table names matching the pattern (e.g., g_table, s_table)
    matches = re.findall(r'\b(g_|s_|b_)[a-z0-9_]+', sql_content)
    return set(matches)  # Return unique table names

# Recursive function to build lineage of tables
def build_lineage(table_name, table_file_map, visited):
    if table_name in visited:  # Avoid infinite loops for cyclic dependencies
        return []

    visited.add(table_name)  # Mark the current table as visited
    file_path = table_file_map.get(table_name)
    if not file_path:  # If the table file is not found, return empty lineage
        return []

    with open(file_path, 'r') as f:
        content = f.read().lower()  # Convert content to lowercase
        # Extract tables referenced in the SQL content
        referenced_tables = extract_referenced_tables(content)
        lineage = []
        for ref_table in referenced_tables:
            lineage.append((table_name, ref_table))  # Add relationship to lineage
            # Recursively build lineage for the referenced table
            lineage.extend(build_lineage(ref_table, table_file_map, visited))
        return lineage

# Function to visualize the lineage as a directed graph using Graphviz
def visualize_lineage(lineage):
    dot = Digraph()  # Create a new directed graph
    for parent, child in lineage:
        dot.edge(parent, child)  # Add an edge from parent to child
    return dot

# Streamlit GUI to interact with the tool
def main():
    st.title("Table Lineage Tracker")  # Application title

    # Define base directory for SQL files
    base_dir = "SQL/Extract"

    # Scan for all SQL files and map table names to paths
    table_file_map = scan_sql_files(base_dir)
    # Filter only Gold tables (those starting with 'g_')
    gold_tables = [t for t in table_file_map.keys() if t.startswith('g_')]

    # User selects a Gold table from a dropdown menu
    selected_table = st.selectbox("Select a Gold Table", gold_tables)

    if selected_table:  # If a table is selected
        st.write(f"Selected Table: {selected_table}")

        # Build lineage for the selected table
        visited = set()  # Track visited tables to avoid infinite loops
        lineage = build_lineage(selected_table, table_file_map, visited)

        # Visualize the lineage graph
        st.subheader("Lineage Graph")
        graph = visualize_lineage(lineage)
        st.graphviz_chart(graph.source)  # Display the graph in Streamlit

        # Display the lineage as a text-based hierarchy
        st.subheader("Text-Based Hierarchy")
        hierarchy = "\n".join([f"{parent} -> {child}" for parent, child in lineage])
        st.text(hierarchy)  # Show the hierarchy as plain text

        # Provide export options for the graph and hierarchy
        st.subheader("Export Options")
        if st.button("Export Graph as PNG"):
            graph.render("lineage_graph", format="png", cleanup=True)  # Save graph as PNG
            st.success("Graph exported as lineage_graph.png")

        if st.button("Export Hierarchy as Text"):
            with open("lineage_hierarchy.txt", "w") as f:
                f.write(hierarchy)  # Save hierarchy to a text file
            st.success("Hierarchy exported as lineage_hierarchy.txt")

if __name__ == "__main__":
    main()
