#!/usr/bin/env python3
"""
migrate_production.py
Safe database migration script for production environment
"""

import sys
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import models
from config import get_logger

logger = get_logger(__name__)

class ProductionMigrator:
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.inspector = inspect(self.engine)
        self.metadata = models.Base.metadata
        
    def get_existing_tables(self):
        """Get list of existing tables in database"""
        return set(self.inspector.get_table_names())
    
    def get_model_tables(self):
        """Get list of tables defined in models"""
        return set(self.metadata.tables.keys())
    
    def get_table_columns(self, table_name):
        """Get existing columns for a table"""
        try:
            columns = self.inspector.get_columns(table_name)
            return {col['name']: col for col in columns}
        except Exception:
            return {}
    
    def create_missing_tables(self):
        """Create tables that exist in models but not in database"""
        existing_tables = self.get_existing_tables()
        model_tables = self.get_model_tables()
        missing_tables = model_tables - existing_tables
        
        if missing_tables:
            logger.info(f"Creating missing tables: {missing_tables}")
            for table_name in missing_tables:
                try:
                    table = self.metadata.tables[table_name]
                    table.create(self.engine)
                    logger.info(f"✅ Created table: {table_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to create table {table_name}: {e}")
                    raise
        else:
            logger.info("✅ All tables exist")
    
    def add_missing_columns(self):
        """Add columns that exist in models but not in database tables"""
        existing_tables = self.get_existing_tables()
        
        for table_name in existing_tables:
            if table_name in self.metadata.tables:
                model_table = self.metadata.tables[table_name]
                existing_columns = self.get_table_columns(table_name)
                
                for column in model_table.columns:
                    if column.name not in existing_columns:
                        try:
                            self.add_column(table_name, column)
                            logger.info(f"✅ Added column {column.name} to {table_name}")
                        except Exception as e:
                            logger.error(f"❌ Failed to add column {column.name} to {table_name}: {e}")
                            raise
    
    def add_column(self, table_name, column):
        """Add a single column to a table"""
        column_type = column.type.compile(self.engine.dialect)
        nullable = "NULL" if column.nullable else "NOT NULL"
        default = ""
        
        # Handle default values
        if column.default is not None:
            if hasattr(column.default, 'arg'):
                if callable(column.default.arg):
                    default = f"DEFAULT {column.default.arg.__name__}()"
                else:
                    default = f"DEFAULT {column.default.arg}"
        
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {column_type} {nullable} {default}"
        
        with self.engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
    
    def create_missing_indexes(self):
        """Create indexes defined in models"""
        logger.info("Creating missing indexes...")
        
        # Add the password_reset_codes indexes if table exists
        if 'password_reset_codes' in self.get_existing_tables():
            try:
                with self.engine.connect() as conn:
                    # Check if indexes exist
                    indexes = self.inspector.get_indexes('password_reset_codes')
                    index_names = [idx['name'] for idx in indexes]
                    
                    if 'idx_password_reset_codes_code' not in index_names:
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_password_reset_codes_code ON password_reset_codes(code)"))
                        logger.info("✅ Created index on password_reset_codes.code")
                    
                    if 'idx_password_reset_codes_user_id' not in index_names:
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_password_reset_codes_user_id ON password_reset_codes(user_id)"))
                        logger.info("✅ Created index on password_reset_codes.user_id")
                    
                    conn.commit()
            except Exception as e:
                logger.error(f"❌ Failed to create indexes: {e}")
                raise
    
    def show_status(self):
        """Show current database status compared to models"""
        logger.info("📊 Production Database Status Report:")
        
        existing_tables = self.get_existing_tables()
        model_tables = self.get_model_tables()
        
        logger.info(f"Tables in database: {len(existing_tables)}")
        logger.info(f"Tables in models: {len(model_tables)}")
        
        missing_tables = model_tables - existing_tables
        extra_tables = existing_tables - model_tables
        
        if missing_tables:
            logger.info(f"Missing tables: {missing_tables}")
        
        if extra_tables:
            logger.info(f"Extra tables (not in models): {extra_tables}")
        
        # Check for missing columns
        missing_columns = []
        for table_name in existing_tables:
            if table_name in self.metadata.tables:
                model_table = self.metadata.tables[table_name]
                existing_columns = self.get_table_columns(table_name)
                
                for column in model_table.columns:
                    if column.name not in existing_columns:
                        missing_columns.append(f"{table_name}.{column.name}")
        
        if missing_columns:
            logger.info(f"Missing columns: {missing_columns}")
        
        if not missing_tables and not extra_tables and not missing_columns:
            logger.info("✅ Database is in sync with models")
        
        return {
            'missing_tables': missing_tables,
            'missing_columns': missing_columns,
            'needs_migration': bool(missing_tables or missing_columns)
        }
    
    def run_migration(self):
        """Run the complete migration process"""
        logger.info("🚀 Starting PRODUCTION database migration...")
        
        try:
            # Show status first
            status = self.show_status()
            
            if not status['needs_migration']:
                logger.info("✅ No migration needed!")
                return
            
            # Step 1: Create missing tables
            logger.info("Step 1: Creating missing tables...")
            self.create_missing_tables()
            
            # Step 2: Add missing columns
            logger.info("Step 2: Adding missing columns...")
            self.add_missing_columns()
            
            # Step 3: Create missing indexes
            logger.info("Step 3: Creating missing indexes...")
            self.create_missing_indexes()
            
            logger.info("✅ Production migration completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Production migration failed: {e}")
            raise

def main():
    """Main migration function"""
    if len(sys.argv) < 2:
        print("Usage: python migrate_production.py <DATABASE_URL> [status|migrate]")
        print("Example: python migrate_production.py 'postgresql://user:pass@host:5432/db' migrate")
        sys.exit(1)
    
    database_url = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else "status"
    
    try:
        migrator = ProductionMigrator(database_url)
        
        if command == "status":
            migrator.show_status()
        elif command == "migrate":
            migrator.run_migration()
        else:
            print("Invalid command. Use 'status' or 'migrate'")
    
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 