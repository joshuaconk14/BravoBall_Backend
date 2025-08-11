#!/usr/bin/env python3
"""
Schema Comparison Tool for BravoBall v2 Migration
Compares production schema with local v2 schema and generates migration scripts
"""

import re
import os
import argparse
from datetime import datetime
from typing import Dict, List, Set, Tuple

class SchemaComparator:
    def __init__(self, production_schema_file: str, v2_schema_file: str):
        self.production_schema_file = production_schema_file
        self.v2_schema_file = v2_schema_file
        self.production_tables = {}
        self.v2_tables = {}
        self.migration_statements = []
        
    def read_schema_file(self, filename: str) -> str:
        """Read and return contents of schema file"""
        with open(filename, 'r') as f:
            return f.read()
    
    def parse_create_table(self, schema_content: str) -> Dict[str, Dict]:
        """Parse CREATE TABLE statements from schema content"""
        tables = {}
        
        # ✅ FIXED: Updated regex to handle schema prefix (public.table_name)
        table_pattern = r'CREATE TABLE (?:public\.)?(\w+) \((.*?)\);'
        matches = re.findall(table_pattern, schema_content, re.DOTALL | re.IGNORECASE)
        
        for table_name, columns_content in matches:
            columns = {}
            
            # Parse individual columns - skip sequences and constraints
            lines = columns_content.split('\n')
            for line in lines:
                line = line.strip().rstrip(',')
                if not line or line.startswith('CONSTRAINT') or line.startswith('PRIMARY KEY') or line.startswith('FOREIGN KEY'):
                    continue
                    
                # Extract column name and type
                parts = line.split()
                if len(parts) >= 2:
                    col_name = parts[0].strip('"')
                    col_type = ' '.join(parts[1:])
                    columns[col_name] = col_type
            
            tables[table_name] = columns
        
        return tables
    
    def compare_schemas(self):
        """Compare production and v2 schemas"""
        print("🔍 Reading schema files...")
        
        production_content = self.read_schema_file(self.production_schema_file)
        v2_content = self.read_schema_file(self.v2_schema_file)
        
        print("📊 Parsing table structures...")
        self.production_tables = self.parse_create_table(production_content)
        self.v2_tables = self.parse_create_table(v2_content)
        
        print(f"Production tables: {list(self.production_tables.keys())}")
        print(f"V2 tables: {list(self.v2_tables.keys())}")
        
        self.find_differences()
    
    def find_differences(self):
        """Find differences between schemas"""
        print("\n🔄 Analyzing schema differences...")
        
        # Find new tables
        new_tables = set(self.v2_tables.keys()) - set(self.production_tables.keys())
        if new_tables:
            print(f"📝 New tables in v2: {new_tables}")
            for table in new_tables:
                self.generate_create_table_statement(table)
        
        # Find dropped tables
        dropped_tables = set(self.production_tables.keys()) - set(self.v2_tables.keys())
        if dropped_tables:
            print(f"🗑️ Dropped tables in v2: {dropped_tables}")
            for table in dropped_tables:
                self.migration_statements.append(f"-- WARNING: Table '{table}' exists in production but not in v2")
                self.migration_statements.append(f"-- DROP TABLE IF EXISTS {table};")
        
        # Find modified tables
        common_tables = set(self.production_tables.keys()) & set(self.v2_tables.keys())
        for table in common_tables:
            self.compare_table_columns(table)
    
    def generate_create_table_statement(self, table_name: str):
        """Generate CREATE TABLE statement for new table"""
        self.migration_statements.append(f"\n-- Create new table: {table_name}")
        
        # This is a simplified version - you'll need to get the full CREATE TABLE from your v2 schema
        columns = self.v2_tables[table_name]
        column_defs = []
        
        for col_name, col_type in columns.items():
            column_defs.append(f"    {col_name} {col_type}")
        
        create_stmt = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
        create_stmt += ",\n".join(column_defs)
        create_stmt += "\n);"
        
        self.migration_statements.append(create_stmt)
    
    def compare_table_columns(self, table_name: str):
        """Compare columns between production and v2 for a specific table"""
        prod_cols = self.production_tables[table_name]
        v2_cols = self.v2_tables[table_name]
        
        # Find new columns
        new_columns = set(v2_cols.keys()) - set(prod_cols.keys())
        if new_columns:
            print(f"📝 New columns in {table_name}: {new_columns}")
            for col in new_columns:
                col_type = v2_cols[col]
                self.migration_statements.append(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col} {col_type};")
        
        # Find dropped columns
        dropped_columns = set(prod_cols.keys()) - set(v2_cols.keys())
        if dropped_columns:
            print(f"🗑️ Dropped columns in {table_name}: {dropped_columns}")
            for col in dropped_columns:
                self.migration_statements.append(f"-- WARNING: Column '{col}' exists in production but not in v2")
                self.migration_statements.append(f"-- ALTER TABLE {table_name} DROP COLUMN IF EXISTS {col};")
        
        # Find modified columns
        common_columns = set(prod_cols.keys()) & set(v2_cols.keys())
        for col in common_columns:
            if prod_cols[col] != v2_cols[col]:
                print(f"🔄 Modified column {table_name}.{col}: {prod_cols[col]} -> {v2_cols[col]}")
                self.migration_statements.append(f"-- ALTER TABLE {table_name} ALTER COLUMN {col} TYPE {v2_cols[col]};")
    
    def generate_migration_file(self):
        """Generate the migration file using the existing template"""
        if not self.migration_statements:
            print("✅ No schema differences found!")
            return
        
        timestamp = datetime.now().strftime("%Y_%m_%d")
        filename = f"{timestamp}_migrate_to_v2_schema.py"
        
        # Get the actual migration SQL
        migration_sql = '\n'.join(self.migration_statements)
        
        migration_content = f'''#!/usr/bin/env python3
"""
Migration: Migrate Database Schema to v2
Date: {datetime.now().strftime("%Y-%m-%d")}
Purpose: Apply all schema changes for BravoBall v2
"""

import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

def setup_logging():
    """Setup logging for migration"""
    log_filename = f"migration_log_{{{{datetime.now().strftime('%Y%m%d_%H%M%S')}}}}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_filename

def backup_database(engine):
    """Create database backup before migration"""
    backup_filename = f"v2_schema_backup_{{{{datetime.now().strftime('%Y%m%d_%H%M%S')}}}}.sql"
    database_url = str(engine.url)
    
    logging.info(f"Creating backup: {{{{backup_filename}}}}")
    
    # Use pg_dump to create backup
    import subprocess
    try:
        result = subprocess.run([
            'pg_dump', database_url, '--no-owner', '--no-privileges'
        ], capture_output=True, text=True, check=True)
        
        with open(backup_filename, 'w') as f:
            f.write(result.stdout)
        
        logging.info(f"✅ Backup created: {{{{backup_filename}}}}")
        return backup_filename
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Backup failed: {{{{e}}}}")
        raise

def run_migration(engine, dry_run=False):
    """Run the v2 schema migration"""
    
    migration_sql = """{migration_sql}""".strip()
    
    statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
    
    logging.info(f"Migration contains {{{{len(statements)}}}} SQL statements")
    
    if dry_run:
        logging.info("🔍 DRY RUN MODE - No changes will be applied")
        for i, stmt in enumerate(statements, 1):
            if not stmt.startswith('--'):
                logging.info(f"Would execute {{{{i}}}}: {{{{stmt[:100]}}}}...")
        return
    
    # Execute migration statements
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            for i, stmt in enumerate(statements, 1):
                if stmt.startswith('--'):
                    logging.info(f"Comment {{{{i}}}}: {{{{stmt}}}}")
                    continue
                    
                logging.info(f"Executing {{{{i}}}}: {{{{stmt[:100]}}}}...")
                conn.execute(text(stmt))
            
            trans.commit()
            logging.info("✅ Migration completed successfully")
            
        except Exception as e:
            trans.rollback()
            logging.error(f"❌ Migration failed: {{{{e}}}}")
            raise

def verify_migration(engine):
    """Verify migration was applied correctly"""
    logging.info("🔍 Verifying migration...")
    
    # Add verification queries here
    verification_queries = [
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
        # Add more verification queries as needed
    ]
    
    with engine.connect() as conn:
        for query in verification_queries:
            result = conn.execute(text(query))
            logging.info(f"Verification: {{{{result.rowcount}}}} results for: {{{{query[:50]}}}}...")
    
    logging.info("✅ Migration verification completed")

def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate to BravoBall v2 Schema')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--database-url', help='Custom database URL')
    parser.add_argument('--skip-backup', action='store_true', help='Skip backup creation')
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = setup_logging()
    logging.info("🚀 Starting BravoBall v2 schema migration")
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Get database URL
        database_url = args.database_url or os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL not found in environment or arguments")
        
        # Create engine
        engine = create_engine(database_url)
        logging.info(f"Connected to database: {{{{database_url.split('@')[1] if '@' in database_url else 'localhost'}}}}")
        
        # Create backup (unless skipped or dry run)
        backup_file = None
        if not args.dry_run and not args.skip_backup:
            backup_file = backup_database(engine)
        
        # Run migration
        run_migration(engine, dry_run=args.dry_run)
        
        # Verify migration (unless dry run)
        if not args.dry_run:
            verify_migration(engine)
        
        logging.info("🎉 Migration process completed successfully")
        if backup_file:
            logging.info(f"💾 Backup saved as: {{{{backup_file}}}}")
        
    except Exception as e:
        logging.error(f"💥 Migration failed: {{{{e}}}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        with open(filename, 'w') as f:
            f.write(migration_content)
        
        # Make file executable
        os.chmod(filename, 0o755)
        
        print(f"\n✅ Migration file generated: {filename}")
        print(f"📋 Contains {len(self.migration_statements)} migration statements")
        
        return filename

def main():
    parser = argparse.ArgumentParser(description='Compare database schemas and generate migration')
    parser.add_argument('--production-schema', default='production_schema.sql', 
                       help='Production schema file')
    parser.add_argument('--v2-schema', default='v2_local_schema.sql',
                       help='V2 local schema file')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.production_schema):
        print(f"❌ Production schema file not found: {args.production_schema}")
        print("Please export it with: pg_dump 'YOUR_PROD_URL' --schema-only > production_schema.sql")
        return
    
    if not os.path.exists(args.v2_schema):
        print(f"❌ V2 schema file not found: {args.v2_schema}")
        print("Please export it with: pg_dump 'YOUR_LOCAL_URL' --schema-only > v2_local_schema.sql")
        return
    
    comparator = SchemaComparator(args.production_schema, args.v2_schema)
    comparator.compare_schemas()
    migration_file = comparator.generate_migration_file()
    
    if migration_file:
        print("\n🚀 Next steps:")
        print(f"1. Review the generated migration: {migration_file}")
        print(f"2. Test on staging: python {migration_file} --dry-run")
        print(f"3. Apply to staging: python {migration_file}")
        print(f"4. Verify results and apply to production")

if __name__ == "__main__":
    main() 