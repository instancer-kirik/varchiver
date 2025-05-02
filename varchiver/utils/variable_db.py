"""Database interface for Variable Calendar."""

from abc import ABC, abstractmethod
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
import json

class DatabaseInterface(ABC):
    """Abstract base class for database operations."""
    
    @abstractmethod
    def connect(self):
        """Connect to the database."""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from the database."""
        pass
    
    @abstractmethod
    def add_variable(self, name: str, type: str, unit: Optional[str] = None, description: Optional[str] = None) -> int:
        """Add a new variable definition."""
        pass
    
    @abstractmethod
    def add_entry(self, variable_id: int, timestamp: datetime, value: Any, context_id: Optional[int] = None, notes: Optional[str] = None) -> int:
        """Add a new variable entry."""
        pass
    
    @abstractmethod
    def add_context(self, name: str, color: Optional[str] = None, description: Optional[str] = None) -> int:
        """Add a new context/label."""
        pass
    
    @abstractmethod
    def get_entries(self, start_date: datetime, end_date: datetime, variables: Optional[List[int]] = None) -> List[Dict]:
        """Get entries within a date range."""
        pass

class PostgresDatabase(DatabaseInterface):
    """PostgreSQL implementation of the database interface."""
    
    def __init__(self, dbname: str, user: str, password: str, host: str = 'localhost', port: int = 5432):
        """Initialize database connection parameters."""
        self.params = {
            'dbname': dbname,
            'user': user,
            'password': password,
            'host': host,
            'port': port
        }
        self.conn = None
        self.cur = None
        
    def connect(self):
        """Connect to PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(**self.params)
            self.cur = self.conn.cursor(cursor_factory=DictCursor)
            self._create_tables()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to database: {str(e)}")
            
    def disconnect(self):
        """Disconnect from PostgreSQL database."""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
            
    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        try:
            # Create contexts table
            self.cur.execute("""
                CREATE TABLE IF NOT EXISTS contexts (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    color VARCHAR(7),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create variables table
            self.cur.execute("""
                CREATE TABLE IF NOT EXISTS variables (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    unit VARCHAR(50),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create entries table
            self.cur.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id SERIAL PRIMARY KEY,
                    variable_id INTEGER REFERENCES variables(id),
                    timestamp TIMESTAMP NOT NULL,
                    numeric_value DOUBLE PRECISION,
                    string_value TEXT,
                    boolean_value BOOLEAN,
                    context_id INTEGER REFERENCES contexts(id),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create entry tags table
            self.cur.execute("""
                CREATE TABLE IF NOT EXISTS entry_tags (
                    entry_id INTEGER REFERENCES entries(id),
                    context_id INTEGER REFERENCES contexts(id),
                    PRIMARY KEY (entry_id, context_id)
                )
            """)
            
            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to create tables: {str(e)}")
            
    def add_variable(self, name: str, type: str, unit: Optional[str] = None, description: Optional[str] = None) -> int:
        """Add a new variable definition."""
        try:
            self.cur.execute("""
                INSERT INTO variables (name, type, unit, description)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (name, type, unit, description))
            
            variable_id = self.cur.fetchone()[0]
            self.conn.commit()
            return variable_id
            
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to add variable: {str(e)}")
            
    def add_entry(self, variable_id: int, timestamp: datetime, value: Any,
                 context_id: Optional[int] = None, notes: Optional[str] = None) -> int:
        """Add a new variable entry."""
        try:
            # Get variable type
            self.cur.execute("SELECT type FROM variables WHERE id = %s", (variable_id,))
            var_type = self.cur.fetchone()['type']
            
            # Prepare value fields based on type
            numeric_value = None
            string_value = None
            boolean_value = None
            
            if var_type == 'numeric':
                numeric_value = float(value)
            elif var_type == 'boolean':
                boolean_value = bool(value)
            else:
                string_value = str(value)
                
            # Insert entry
            self.cur.execute("""
                INSERT INTO entries (
                    variable_id, timestamp, numeric_value, string_value,
                    boolean_value, context_id, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (variable_id, timestamp, numeric_value, string_value,
                 boolean_value, context_id, notes))
                 
            entry_id = self.cur.fetchone()[0]
            self.conn.commit()
            return entry_id
            
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to add entry: {str(e)}")
            
    def add_context(self, name: str, color: Optional[str] = None, description: Optional[str] = None) -> int:
        """Add a new context/label."""
        try:
            self.cur.execute("""
                INSERT INTO contexts (name, color, description)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (name, color, description))
            
            context_id = self.cur.fetchone()[0]
            self.conn.commit()
            return context_id
            
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to add context: {str(e)}")
            
    def get_entries(self, start_date: datetime, end_date: datetime,
                   variables: Optional[List[int]] = None) -> List[Dict]:
        """Get entries within a date range."""
        try:
            query = """
                SELECT e.*, v.name as variable_name, v.type as variable_type,
                       c.name as context_name, c.color as context_color
                FROM entries e
                JOIN variables v ON e.variable_id = v.id
                LEFT JOIN contexts c ON e.context_id = c.id
                WHERE e.timestamp BETWEEN %s AND %s
            """
            params = [start_date, end_date]
            
            if variables:
                query += " AND e.variable_id = ANY(%s)"
                params.append(variables)
                
            query += " ORDER BY e.timestamp DESC"
            
            self.cur.execute(query, params)
            entries = self.cur.fetchall()
            
            # Convert to list of dicts and format values
            result = []
            for entry in entries:
                value = None
                if entry['variable_type'] == 'numeric':
                    value = entry['numeric_value']
                elif entry['variable_type'] == 'boolean':
                    value = entry['boolean_value']
                else:
                    value = entry['string_value']
                    
                result.append({
                    'id': entry['id'],
                    'variable_id': entry['variable_id'],
                    'variable_name': entry['variable_name'],
                    'timestamp': entry['timestamp'],
                    'value': value,
                    'context_name': entry['context_name'],
                    'context_color': entry['context_color'],
                    'notes': entry['notes']
                })
                
            return result
            
        except Exception as e:
            raise Exception(f"Failed to get entries: {str(e)}")
            
    def get_variables(self) -> List[Dict]:
        """Get all variables."""
        try:
            self.cur.execute("SELECT * FROM variables ORDER BY name")
            return [dict(row) for row in self.cur.fetchall()]
        except Exception as e:
            raise Exception(f"Failed to get variables: {str(e)}")
            
    def get_contexts(self) -> List[Dict]:
        """Get all contexts."""
        try:
            self.cur.execute("SELECT * FROM contexts ORDER BY name")
            return [dict(row) for row in self.cur.fetchall()]
        except Exception as e:
            raise Exception(f"Failed to get contexts: {str(e)}")
            
    def update_variable(self, variable_id: int, name: Optional[str] = None,
                       unit: Optional[str] = None, description: Optional[str] = None) -> None:
        """Update a variable's properties."""
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = %s")
                params.append(name)
            if unit is not None:
                updates.append("unit = %s")
                params.append(unit)
            if description is not None:
                updates.append("description = %s")
                params.append(description)
                
            if updates:
                query = f"UPDATE variables SET {', '.join(updates)} WHERE id = %s"
                params.append(variable_id)
                self.cur.execute(query, params)
                self.conn.commit()
                
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to update variable: {str(e)}")
            
    def update_context(self, context_id: int, name: Optional[str] = None,
                      color: Optional[str] = None, description: Optional[str] = None) -> None:
        """Update a context's properties."""
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = %s")
                params.append(name)
            if color is not None:
                updates.append("color = %s")
                params.append(color)
            if description is not None:
                updates.append("description = %s")
                params.append(description)
                
            if updates:
                query = f"UPDATE contexts SET {', '.join(updates)} WHERE id = %s"
                params.append(context_id)
                self.cur.execute(query, params)
                self.conn.commit()
                
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to update context: {str(e)}")
            
    def delete_entry(self, entry_id: int) -> None:
        """Delete an entry."""
        try:
            self.cur.execute("DELETE FROM entry_tags WHERE entry_id = %s", (entry_id,))
            self.cur.execute("DELETE FROM entries WHERE id = %s", (entry_id,))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to delete entry: {str(e)}")
            
    def delete_variable(self, variable_id: int) -> None:
        """Delete a variable and all its entries."""
        try:
            # First delete all entries
            self.cur.execute("""
                DELETE FROM entry_tags WHERE entry_id IN (
                    SELECT id FROM entries WHERE variable_id = %s
                )
            """, (variable_id,))
            self.cur.execute("DELETE FROM entries WHERE variable_id = %s", (variable_id,))
            self.cur.execute("DELETE FROM variables WHERE id = %s", (variable_id,))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to delete variable: {str(e)}")
            
    def delete_context(self, context_id: int) -> None:
        """Delete a context."""
        try:
            self.cur.execute("DELETE FROM entry_tags WHERE context_id = %s", (context_id,))
            self.cur.execute("UPDATE entries SET context_id = NULL WHERE context_id = %s", (context_id,))
            self.cur.execute("DELETE FROM contexts WHERE id = %s", (context_id,))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to delete context: {str(e)}") 