import os
import re
import streamlit as st
import networkx as nx
from graphviz import Digraph

# Function to scan SQL files and map table names to file paths
def scan_sql_files(base_dir):
    # Dictionary to map SQL-style table names to their full file paths
    table_file_map = {}
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.sql'):  # Process only .sql files
                file_path = os.path.join(root, file)
                file_lower = file.lower()  # Convert file name to lowercase for consistency
                # Extract the prefix, descriptive part, and base table name from the file name
                match = re.match(r'(g_|s_|b_)(\w+?)_(.+)\.sql', file_lower)
                if match:
                    prefix = match.group(1)  # e.g., "s_"
                    base_name = match.group(3)  # e.g., "market_table"
                    # Reconstruct the SQL-style table name
                    sql_table_name = f"{prefix}{base_name}"
                    table_file_map[sql_table_name] = file_path  # Map SQL table name to file path
    return table_file_map

# Function to parse SQL content and extract referenced table names
def extract_referenced_tables(sql_content):
    # Find all table names matching the pattern (e.g., g_table, s_table)
    matches = re.findall(r'\b(g_|s_|b_)[a-z0-9_]+', sql_content)
    return set(matches)  # Return unique table names

# Recursive function to build lineage of tables
# Resolves table references in SQL files to their corresponding file paths
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
            # Ensure the referenced table exists in the map
            if ref_table in table_file_map:
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

# Function to log diagnostic information to a text file
def log_diagnostics(base_dir, selected_table, lineage, table_file_map):
    log_file = "lineage_diagnostics.log"
    with open(log_file, "w") as log:
        log.write("Diagnostics Log\n")
        log.write(f"Base Directory: {base_dir}\n")
        log.write(f"Selected Table: {selected_table}\n")
        log.write("\nTable File Map:\n")
        for table, path in table_file_map.items():
            log.write(f"{table}: {path}\n")
        log.write("\nLineage:\n")
        for parent, child in lineage:
            log.write(f"{parent} -> {child}\n")
    return log_file

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

        # Log diagnostics to a file
        log_file = log_diagnostics(base_dir, selected_table, lineage, table_file_map)
        st.info(f"Diagnostics log created: {log_file}")

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
