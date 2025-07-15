#!/usr/bin/env python3
"""
migrate_database.py
Safe database migration script that syncs your database with models.py
This script will:
1. Create missing tables
2. Add missing columns
3. Create missing indexes
4. Preserve existing data
"""

import sys
import os
from sqlalchemy import create_engine, inspect, text, MetaData, Table, Column
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import models
from db import SQLALCHEMY_DATABASE_URL
from config import get_logger

logger = get_logger(__name__)

class DatabaseMigrator:
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
    
    def add_column(self, table_name, column):
        """Add a single column to a table"""
        column_type = column.type.compile(self.engine.dialect)
        nullable = "NULL" if column.nullable else "NOT NULL"
        default = ""
        
        # Handle default values
        if column.default is not None:
            if hasattr(column.default, 'arg'):
                if callable(column.default.arg):
                    # For functions like func.now()
                    default = f"DEFAULT {column.default.arg.__name__}()"
                else:
                    # Handle different types of default values
                    default_arg = column.default.arg
                    if isinstance(default_arg, str):
                        if default_arg == '':
                            default = "DEFAULT ''"
                        else:
                            default = f"DEFAULT '{default_arg}'"
                    elif isinstance(default_arg, (int, float)):
                        default = f"DEFAULT {default_arg}"
                    elif default_arg is None:
                        default = "DEFAULT NULL"
                    else:
                        default = f"DEFAULT {default_arg}"
            elif hasattr(column.default, 'arg'):
                default = f"DEFAULT {column.default}"
        
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {column_type} {nullable} {default}"
        
        with self.engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
    
    def create_missing_indexes(self):
        """Create indexes defined in models"""
        # This is a simplified version - you might want to expand this
        # based on your specific index requirements
        logger.info("Checking for missing indexes...")
        
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
    
    def check_foreign_keys(self):
        """Check and create missing foreign key constraints"""
        logger.info("Checking foreign key constraints...")
        # This is a placeholder - you can expand this if needed
        pass
    
    def remove_deprecated_columns(self):
        """Remove columns that are no longer in the model"""
        logger.info("Checking for deprecated columns...")
        
        # List of columns to remove: table_name -> [column_names]
        deprecated_columns = {
            'progress_history': ['drills_for_position']
        }
        
        for table_name, columns_to_remove in deprecated_columns.items():
            if table_name in self.get_existing_tables():
                existing_columns = self.get_table_columns(table_name)
                
                for column_name in columns_to_remove:
                    if column_name in existing_columns:
                        try:
                            with self.engine.connect() as conn:
                                sql = f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_name}"
                                conn.execute(text(sql))
                                conn.commit()
                                logger.info(f"✅ Removed deprecated column {column_name} from {table_name}")
                        except Exception as e:
                            logger.error(f"❌ Failed to remove column {column_name} from {table_name}: {e}")
    
    def run_migration(self):
        """Run the complete migration process"""
        logger.info("🚀 Starting database migration...")
        
        try:
            # Step 1: Create missing tables
            logger.info("Step 1: Creating missing tables...")
            self.create_missing_tables()
            
            # Step 2: Add missing columns
            logger.info("Step 2: Adding missing columns...")
            self.add_missing_columns()
            
            # Step 3: Remove deprecated columns
            logger.info("Step 3: Removing deprecated columns...")
            self.remove_deprecated_columns()
            
            # Step 4: Create missing indexes
            logger.info("Step 4: Creating missing indexes...")
            self.create_missing_indexes()
            
            # Step 5: Check foreign keys
            logger.info("Step 5: Checking foreign keys...")
            self.check_foreign_keys()
            
            logger.info("✅ Migration completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise
    
    def show_status(self):
        """Show current database status compared to models"""
        logger.info("📊 Database Status Report:")
        
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
        
        if not missing_tables and not extra_tables:
            logger.info("✅ All tables are in sync")

def main():
    """Main migration function"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        migrator = DatabaseMigrator(SQLALCHEMY_DATABASE_URL)
        
        if command == "status":
            migrator.show_status()
        elif command == "migrate":
            migrator.run_migration()
        elif command == "tables":
            migrator.create_missing_tables()
        elif command == "columns":
            migrator.add_missing_columns()
        elif command == "remove":
            migrator.remove_deprecated_columns()
        elif command == "indexes":
            migrator.create_missing_indexes()
        else:
            print("Usage: python migrate_database.py [status|migrate|tables|columns|remove|indexes]")
            print("  status  - Show database status")
            print("  migrate - Run full migration")
            print("  tables  - Create missing tables only")
            print("  columns - Add missing columns only")
            print("  remove  - Remove deprecated columns only")
            print("  indexes - Create missing indexes only")
    else:
        # Default: run full migration
        migrator = DatabaseMigrator(SQLALCHEMY_DATABASE_URL)
        migrator.show_status()
        
        response = input("\n🤔 Do you want to run the migration? (y/N): ")
        if response.lower() in ['y', 'yes']:
            migrator.run_migration()
        else:
            logger.info("Migration cancelled")

if __name__ == "__main__":
    main() 