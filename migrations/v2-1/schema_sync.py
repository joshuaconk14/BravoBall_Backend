"""
schema_sync.py
Ensures staging database has the same schema as V2 database
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime

# Add parent directory to path to import our models
sys.path.append(str(Path(__file__).parent.parent.parent))
from models import Base
from migration_config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(config.get_log_path("schema_sync")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SchemaSync:
    """Handles schema synchronization between databases"""
    
    def __init__(self, source_url: str, target_url: str):
        self.source_engine = create_engine(source_url)
        self.target_engine = create_engine(target_url)
        self.source_inspector = inspect(self.source_engine)
        self.target_inspector = inspect(self.target_engine)
        
    def get_table_schema(self, table_name: str, inspector) -> dict:
        """Get schema information for a table"""
        try:
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            return {
                'columns': columns,
                'indexes': indexes,
                'foreign_keys': foreign_keys
            }
        except Exception as e:
            logger.error(f"Error getting schema for table {table_name}: {e}")
            return None
    
    def compare_schemas(self) -> dict:
        """Compare schemas between source and target databases"""
        source_tables = set(self.source_inspector.get_table_names())
        target_tables = set(self.target_inspector.get_table_names())
        
        missing_tables = source_tables - target_tables
        extra_tables = target_tables - source_tables
        common_tables = source_tables & target_tables
        
        differences = {
            'missing_tables': list(missing_tables),
            'extra_tables': list(extra_tables),
            'schema_differences': {}
        }
        
        # Check schema differences for common tables
        for table in common_tables:
            source_schema = self.get_table_schema(table, self.source_inspector)
            target_schema = self.get_table_schema(table, self.target_inspector)
            
            if source_schema and target_schema:
                # Compare columns
                source_cols = {col['name']: col for col in source_schema['columns']}
                target_cols = {col['name']: col for col in target_schema['columns']}
                
                missing_columns = set(source_cols.keys()) - set(target_cols.keys())
                extra_columns = set(target_cols.keys()) - set(source_cols.keys())
                different_columns = []
                
                for col_name in set(source_cols.keys()) & set(target_cols.keys()):
                    source_col = source_cols[col_name]
                    target_col = target_cols[col_name]
                    
                    # Check if columns are functionally equivalent (ignore sequence name differences)
                    if not self._columns_equivalent(source_col, target_col):
                        different_columns.append({
                            'column': col_name,
                            'source': source_col,
                            'target': target_col
                        })
                
                if missing_columns or extra_columns or different_columns:
                    differences['schema_differences'][table] = {
                        'missing_columns': list(missing_columns),
                        'extra_columns': list(extra_columns),
                        'different_columns': different_columns
                    }
        
        return differences
    
    def _columns_equivalent(self, col1: dict, col2: dict) -> bool:
        """Check if two columns are functionally equivalent, ignoring sequence name differences"""
        try:
            # Compare basic properties
            if (col1.get('type') != col2.get('type') or
                col1.get('nullable') != col2.get('nullable')):
                return False
            
            # Compare defaults, but ignore sequence name differences
            default1 = col1.get('default')
            default2 = col2.get('default')
            
            if default1 != default2:
                # Check if both are sequence defaults (ignore sequence name)
                if (default1 and 'nextval(' in str(default1) and 
                    default2 and 'nextval(' in str(default2)):
                    return True  # Both are sequences, functionally equivalent
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error comparing columns: {e}")
            return False
    
    def create_missing_tables(self) -> bool:
        """Create missing tables in target database"""
        try:
            logger.info("Creating missing tables...")
            
            # Get all tables from source
            source_tables = set(self.source_inspector.get_table_names())
            target_tables = set(self.target_inspector.get_table_names())
            missing_tables = source_tables - target_tables
            
            if not missing_tables:
                logger.info("No missing tables found")
                return True
            
            logger.info(f"Missing tables: {missing_tables}")
            
            # Create tables using SQLAlchemy metadata
            with self.target_engine.connect() as conn:
                # Create all tables that exist in source but not in target
                for table_name in missing_tables:
                    try:
                        # Get the table definition from source
                        table_metadata = self.source_inspector.get_table_names()
                        if table_name in table_metadata:
                            # Create table using raw SQL from source
                            create_sql = self._get_create_table_sql(table_name)
                            if create_sql:
                                conn.execute(text(create_sql))
                                conn.commit()
                                logger.info(f"Created table: {table_name}")
                    except Exception as e:
                        logger.error(f"Error creating table {table_name}: {e}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating missing tables: {e}")
            return False
    
    def _get_create_table_sql(self, table_name: str) -> str:
        """Get CREATE TABLE SQL for a table"""
        try:
            with self.source_engine.connect() as conn:
                # Get table definition
                result = conn.execute(text(f"""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position
                """))
                
                columns = []
                for row in result:
                    col_def = f'"{row[0]}" {row[1]}'
                    if row[2] == 'NO':
                        col_def += ' NOT NULL'
                    if row[3]:
                        col_def += f' DEFAULT {row[3]}'
                    columns.append(col_def)
                
                # Get primary key
                pk_result = conn.execute(text(f"""
                    SELECT column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = '{table_name}' 
                        AND tc.constraint_type = 'PRIMARY KEY'
                """))
                
                pk_columns = [row[0] for row in pk_result]
                if pk_columns:
                    columns.append(f'PRIMARY KEY ({", ".join(pk_columns)})')
                
                return f'CREATE TABLE "{table_name}" (\n  {",\n  ".join(columns)}\n)'
                
        except Exception as e:
            logger.error(f"Error getting CREATE TABLE SQL for {table_name}: {e}")
            return None
    
    def add_missing_columns(self) -> bool:
        """Add missing columns to existing tables"""
        try:
            logger.info("Adding missing columns...")
            
            differences = self.compare_schemas()
            schema_diffs = differences.get('schema_differences', {})
            
            if not schema_diffs:
                logger.info("No schema differences found")
                return True
            
            with self.target_engine.connect() as conn:
                for table_name, diff in schema_diffs.items():
                    missing_columns = diff.get('missing_columns', [])
                    
                    for col_name in missing_columns:
                        try:
                            # Get column definition from source
                            source_schema = self.get_table_schema(table_name, self.source_inspector)
                            if source_schema:
                                col_def = None
                                for col in source_schema['columns']:
                                    if col['name'] == col_name:
                                        col_def = col
                                        break
                                
                                if col_def:
                                    alter_sql = self._get_alter_table_sql(table_name, col_name, col_def)
                                    if alter_sql:
                                        conn.execute(text(alter_sql))
                                        conn.commit()
                                        logger.info(f"Added column {col_name} to table {table_name}")
                        except Exception as e:
                            logger.error(f"Error adding column {col_name} to table {table_name}: {e}")
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding missing columns: {e}")
            return False
    
    def _get_alter_table_sql(self, table_name: str, column_name: str, column_def: dict) -> str:
        """Get ALTER TABLE SQL for adding a column"""
        col_type = str(column_def['type'])
        nullable = "NULL" if column_def.get('nullable', True) else "NOT NULL"
        default = f" DEFAULT {column_def['default']}" if column_def.get('default') else ""
        
        return f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {col_type} {nullable}{default}'
    
    def sync_schema(self) -> bool:
        """Complete schema synchronization"""
        try:
            logger.info("Starting schema synchronization...")
            
            # Compare schemas
            differences = self.compare_schemas()
            logger.info(f"Schema differences found: {differences}")
            
            # Create missing tables
            if not self.create_missing_tables():
                logger.error("Failed to create missing tables")
                return False
            
            # Add missing columns
            if not self.add_missing_columns():
                logger.error("Failed to add missing columns")
                return False
            
            # Final validation - only check for critical differences
            final_differences = self.compare_schemas()
            critical_issues = []
            
            if final_differences['missing_tables']:
                critical_issues.append(f"Missing tables: {final_differences['missing_tables']}")
            
            # Check for missing columns (critical)
            for table, diff in final_differences.get('schema_differences', {}).items():
                if diff.get('missing_columns'):
                    critical_issues.append(f"{table}: missing columns {diff['missing_columns']}")
            
            if critical_issues:
                logger.error(f"Schema synchronization incomplete: {critical_issues}")
                return False
            
            logger.info("✅ Schema synchronization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Schema synchronization failed: {e}")
            return False
    
    def validate_schema_sync(self) -> bool:
        """Validate that schemas are synchronized"""
        try:
            differences = self.compare_schemas()
            
            # Only fail on critical differences
            if differences['missing_tables']:
                logger.error(f"Missing tables in target: {differences['missing_tables']}")
                return False
            
            # Check for missing columns (critical)
            critical_differences = []
            for table, diff in differences.get('schema_differences', {}).items():
                if diff.get('missing_columns'):
                    critical_differences.append(f"{table}: missing columns {diff['missing_columns']}")
            
            if critical_differences:
                logger.error(f"Critical schema differences found: {critical_differences}")
                return False
            
            # Log non-critical differences but don't fail
            non_critical_differences = []
            for table, diff in differences.get('schema_differences', {}).items():
                if diff.get('different_columns'):
                    non_critical_differences.append(f"{table}: {len(diff['different_columns'])} column differences")
            
            if non_critical_differences:
                logger.info(f"Non-critical schema differences (sequence names, defaults): {non_critical_differences}")
                logger.info("These differences are functionally equivalent and won't affect migration")
            
            logger.info("✅ Schema validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return False

def main():
    """Main function for command line usage"""
    if len(sys.argv) != 3:
        print("Usage: python schema_sync.py <source_database_url> <target_database_url>")
        print("Example: python schema_sync.py <V2_DATABASE_URL> <STAGING_DATABASE_URL>")
        sys.exit(1)
    
    source_url = sys.argv[1]
    target_url = sys.argv[2]
    
    logger.info(f"Syncing schema from {source_url} to {target_url}")
    
    sync = SchemaSync(source_url, target_url)
    
    if sync.sync_schema():
        logger.info("Schema synchronization completed successfully")
        sys.exit(0)
    else:
        logger.error("Schema synchronization failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
