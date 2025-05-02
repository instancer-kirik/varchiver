Variable Calendar Design Document
Overview
A flexible calendar system for tracking variables over time with support for different data types, custom contexts/labels, and database persistence.
Core Features
Variable Tracking
Track numeric variables (float/int)
Track categorical variables (strings, enums)
Track mood/context labels with color associations
Support for multiple variables per day
Optional time granularity (daily, hourly, etc.)
Database Integration
Abstract database interface for flexibility
Initial PostgreSQL implementation
Schema design for efficient querying
Support for future database types
User Interface
Calendar view with variable visualization
Input forms for adding/editing entries
Color coding for moods/contexts
Filtering and search capabilities
Context/label management
-- Contexts/Labels table
CREATE TABLE contexts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(7),  -- Hex color code
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Variables table
CREATE TABLE variables (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL,  -- 'numeric', 'string', 'boolean'
    unit VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Variable entries
CREATE TABLE entries (
    id SERIAL PRIMARY KEY,
    variable_id INTEGER REFERENCES variables(id),
    timestamp TIMESTAMP NOT NULL,
    numeric_value DOUBLE PRECISION,
    string_value TEXT,
    boolean_value BOOLEAN,
    context_id INTEGER REFERENCES contexts(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tags for entries
CREATE TABLE entry_tags (
    entry_id INTEGER REFERENCES entries(id),
    context_id INTEGER REFERENCES contexts(id),
    PRIMARY KEY (entry_id, context_id)
);
class DatabaseInterface(ABC):
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def disconnect(self):
        pass
    
    @abstractmethod
    def add_variable(self, name, type, unit=None, description=None):
        pass
    
    @abstractmethod
    def add_entry(self, variable_id, timestamp, value, context_id=None):
        pass
        class VariableCalendar:
    def __init__(self, database):
        self.db = database
        
    def add_variable(self, name, type, unit=None):
        pass
        
    def add_entry(self, variable_name, value, timestamp=None):
        pass
        
    def get_entries(self, start_date, end_date, variables=None):
        pass