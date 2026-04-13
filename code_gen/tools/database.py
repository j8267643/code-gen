"""
Database tools for SQL operations
Inspired by PraisonAI's database tools
"""
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from code_gen.tools.base import Tool, ToolResult


class DuckDBQueryTool(Tool):
    """Execute SQL queries using DuckDB (analytical database)"""
    
    name = "duckdb_query"
    description = "Execute SQL queries using DuckDB. Supports querying CSV, JSON, Parquet files and in-memory analytics."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "SQL query to execute",
            },
            "file_path": {
                "type": "string",
                "description": "Optional: Path to data file (CSV, JSON, Parquet) to query",
            },
        },
        "required": ["query"],
    }
    
    async def execute(self, query: str, file_path: Optional[str] = None) -> ToolResult:
        try:
            import duckdb
            
            # Create connection
            conn = duckdb.connect(":memory:")
            
            # If file provided, create view for it
            if file_path:
                path = Path(file_path)
                if not path.exists():
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"File not found: {file_path}"
                    )
                
                suffix = path.suffix.lower()
                table_name = path.stem.replace("-", "_").replace(".", "_")
                
                if suffix == ".csv":
                    conn.execute(f"CREATE VIEW {table_name} AS SELECT * FROM read_csv_auto('{file_path}')")
                elif suffix == ".json":
                    conn.execute(f"CREATE VIEW {table_name} AS SELECT * FROM read_json_auto('{file_path}')")
                elif suffix == ".parquet":
                    conn.execute(f"CREATE VIEW {table_name} AS SELECT * FROM read_parquet('{file_path}')")
                else:
                    conn.close()
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"Unsupported file format: {suffix}. Use CSV, JSON, or Parquet."
                    )
            
            # Execute query
            result = conn.execute(query)
            
            # Fetch results
            columns = [desc[0] for desc in result.description] if result.description else []
            rows = result.fetchall()
            
            # Format output
            output = []
            output.append(f"Query: {query}")
            output.append(f"Rows returned: {len(rows)}")
            output.append("")
            
            if rows:
                # Calculate column widths
                col_widths = [len(str(col)) for col in columns]
                for row in rows[:50]:  # Limit to 50 rows for display
                    for i, val in enumerate(row):
                        col_widths[i] = max(col_widths[i], len(str(val)[:50]))
                
                # Header
                header = " | ".join(str(col).ljust(col_widths[i]) for i, col in enumerate(columns))
                output.append(header)
                output.append("-" * len(header))
                
                # Rows
                for row in rows[:50]:
                    row_str = " | ".join(str(val)[:50].ljust(col_widths[i]) for i, val in enumerate(row))
                    output.append(row_str)
                
                if len(rows) > 50:
                    output.append(f"\n... and {len(rows) - 50} more rows")
            else:
                output.append("No rows returned")
            
            conn.close()
            
            return ToolResult(
                success=True,
                content="\n".join(output),
                data={
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows)
                }
            )
            
        except ImportError:
            return ToolResult(
                success=False,
                content="",
                error="DuckDB not installed. Install with: pip install duckdb"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Query failed: {str(e)}"
            )


class SQLiteQueryTool(Tool):
    """Execute SQL queries on SQLite databases"""
    
    name = "sqlite_query"
    description = "Execute SQL queries on SQLite databases. Supports SELECT, INSERT, UPDATE, DELETE operations."
    input_schema = {
        "type": "object",
        "properties": {
            "database": {
                "type": "string",
                "description": "Path to SQLite database file (or ':memory:' for temporary)",
            },
            "query": {
                "type": "string",
                "description": "SQL query to execute",
            },
            "readonly": {
                "type": "boolean",
                "description": "Open database in read-only mode",
                "default": True,
            },
        },
        "required": ["database", "query"],
    }
    
    async def execute(self, database: str, query: str, readonly: bool = True) -> ToolResult:
        try:
            # Connect to database
            if readonly and database != ":memory:":
                uri = f"file:{database}?mode=ro"
                conn = sqlite3.connect(uri, uri=True)
            else:
                conn = sqlite3.connect(database)
            
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Execute query
            cursor.execute(query)
            
            # Check if query returns results
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                # Convert to list of dicts
                results = [dict(row) for row in rows]
                
                # Format output
                output = []
                output.append(f"Query: {query}")
                output.append(f"Rows returned: {len(results)}")
                output.append("")
                
                if results:
                    # Calculate column widths
                    col_widths = [len(str(col)) for col in columns]
                    for row in results[:50]:
                        for i, col in enumerate(columns):
                            col_widths[i] = max(col_widths[i], len(str(row.get(col, ""))[:50]))
                    
                    # Header
                    header = " | ".join(str(col).ljust(col_widths[i]) for i, col in enumerate(columns))
                    output.append(header)
                    output.append("-" * len(header))
                    
                    # Rows
                    for row in results[:50]:
                        row_str = " | ".join(str(row.get(col, ""))[:50].ljust(col_widths[i]) for i, col in enumerate(columns))
                        output.append(row_str)
                    
                    if len(results) > 50:
                        output.append(f"\n... and {len(results) - 50} more rows")
                
                conn.close()
                
                return ToolResult(
                    success=True,
                    content="\n".join(output),
                    data={
                        "columns": columns,
                        "rows": results,
                        "row_count": len(results)
                    }
                )
            else:
                # Non-SELECT query
                conn.commit()
                rowcount = cursor.rowcount
                conn.close()
                
                return ToolResult(
                    success=True,
                    content=f"Query executed successfully.\nRows affected: {rowcount}",
                    data={"rows_affected": rowcount}
                )
                
        except sqlite3.Error as e:
            return ToolResult(
                success=False,
                content="",
                error=f"SQLite error: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Query failed: {str(e)}"
            )


class CSVQueryTool(Tool):
    """Query CSV files using SQL"""
    
    name = "csv_query"
    description = "Query CSV files using SQL-like operations. Supports filtering, aggregation, and sorting."
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to CSV file",
            },
            "select": {
                "type": "array",
                "description": "Columns to select (empty for all)",
                "default": [],
            },
            "where": {
                "type": "string",
                "description": "Filter condition (e.g., 'age > 18')",
            },
            "order_by": {
                "type": "string",
                "description": "Column to sort by",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum rows to return",
                "default": 100,
            },
        },
        "required": ["file_path"],
    }
    
    async def execute(
        self,
        file_path: str,
        select: List[str] = None,
        where: Optional[str] = None,
        order_by: Optional[str] = None,
        limit: int = 100
    ) -> ToolResult:
        try:
            import csv
            
            path = Path(file_path)
            if not path.exists():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"File not found: {file_path}"
                )
            
            # Read CSV
            with open(path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Apply WHERE filter
            if where and rows:
                filtered_rows = []
                for row in rows:
                    try:
                        # Simple eval for conditions like 'age > 18'
                        # Convert values to appropriate types
                        context = {}
                        for key, val in row.items():
                            try:
                                context[key] = float(val) if val else 0
                            except:
                                context[key] = val
                        
                        if eval(where, {"__builtins__": {}}, context):
                            filtered_rows.append(row)
                    except:
                        pass
                rows = filtered_rows
            
            # Apply ORDER BY
            if order_by and rows:
                reverse = order_by.startswith("-")
                sort_key = order_by[1:] if reverse else order_by
                
                try:
                    rows.sort(key=lambda x: float(x.get(sort_key, 0) or 0), reverse=reverse)
                except:
                    rows.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)
            
            # Apply LIMIT
            total_rows = len(rows)
            rows = rows[:limit]
            
            # Apply SELECT
            if select and rows:
                rows = [{k: v for k, v in row.items() if k in select} for row in rows]
            
            # Format output
            if not rows:
                return ToolResult(
                    success=True,
                    content="Query returned no results.",
                    data={"row_count": 0, "columns": []}
                )
            
            columns = list(rows[0].keys())
            
            output = []
            output.append(f"CSV Query Results: {file_path}")
            output.append(f"Total rows: {total_rows}, Returned: {len(rows)}")
            output.append("")
            
            # Calculate column widths
            col_widths = [len(str(col)) for col in columns]
            for row in rows:
                for i, col in enumerate(columns):
                    col_widths[i] = max(col_widths[i], len(str(row.get(col, ""))[:50]))
            
            # Header
            header = " | ".join(str(col).ljust(col_widths[i]) for i, col in enumerate(columns))
            output.append(header)
            output.append("-" * len(header))
            
            # Rows
            for row in rows:
                row_str = " | ".join(str(row.get(col, ""))[:50].ljust(col_widths[i]) for i, col in enumerate(columns))
                output.append(row_str)
            
            return ToolResult(
                success=True,
                content="\n".join(output),
                data={
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "total_rows": total_rows
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"CSV query failed: {str(e)}"
            )
