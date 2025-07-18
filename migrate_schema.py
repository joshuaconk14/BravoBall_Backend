#!/usr/bin/env python3
"""
migrate_schema.py
Comprehensive database migration script that uses models.py as the single source of truth.

This script safely migrates your database to match your SQLAlchemy models:
- Creates missing tables
- Adds missing columns (with proper defaults)
- Creates missing indexes and constraints
- Handles data type changes (with warnings)
- Seeds initial data (mental training quotes, drills)
- Syncs data changes from files to database
- Provides rollback recommendations
- Safe for production use with proper backups

Usage:
    python migrate_schema.py status                    # Show current status
    python migrate_schema.py migrate --dry-run         # See what would change (safe)
    python migrate_schema.py migrate                   # Run full migration
    python migrate_schema.py migrate --seed            # Run migration + seed data
    python migrate_schema.py seed                      # Seed data only
    python migrate_schema.py sync-drills               # Sync drill data only
    python migrate_schema.py backup                    # Generate backup commands
    python migrate_schema.py production <DATABASE_URL> # Production migration
"""

import sys
import os
import json
from pathlib import Path
from sqlalchemy import create_engine, inspect, text, MetaData, Column, Index
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
import models
from db import SQLALCHEMY_DATABASE_URL
from config import get_logger
from datetime import datetime

logger = get_logger(__name__)

class SchemaMigrator:
    def __init__(self, database_url=None):
        self.database_url = database_url or SQLALCHEMY_DATABASE_URL
        self.engine = create_engine(self.database_url)
        self.inspector = inspect(self.engine)
        self.metadata = models.Base.metadata
        self.changes_applied = []
        self.warnings = []
        
        # ✅ NEW: Data seeding paths
        self.drills_dir = Path("drills")
        self.quotes_file = self.drills_dir / "mental_training_quotes.txt"
        
    def get_existing_tables(self):
        """Get list of existing tables in database"""
        return set(self.inspector.get_table_names())
    
    def get_model_tables(self):
        """Get list of tables defined in models (single source of truth)"""
        return set(self.metadata.tables.keys())
    
    def get_table_columns(self, table_name):
        """Get existing columns for a table with their properties"""
        try:
            columns = self.inspector.get_columns(table_name)
            return {col['name']: col for col in columns}
        except Exception:
            return {}
    
    def get_table_indexes(self, table_name):
        """Get existing indexes for a table"""
        try:
            indexes = self.inspector.get_indexes(table_name)
            return {idx['name']: idx for idx in indexes}
        except Exception:
            return {}
    
    def get_foreign_keys(self, table_name):
        """Get existing foreign keys for a table"""
        try:
            fks = self.inspector.get_foreign_keys(table_name)
            return {fk['name']: fk for fk in fks}
        except Exception:
            return {}
    
    def create_missing_tables(self, dry_run=False):
        """Create tables that exist in models but not in database"""
        existing_tables = self.get_existing_tables()
        model_tables = self.get_model_tables()
        missing_tables = model_tables - existing_tables
        
        if missing_tables:
            logger.info(f"🆕 Found {len(missing_tables)} missing tables: {list(missing_tables)}")
            
            if dry_run:
                for table_name in missing_tables:
                    logger.info(f"   [DRY RUN] Would create table: {table_name}")
                return missing_tables
            
            for table_name in missing_tables:
                try:
                    table = self.metadata.tables[table_name]
                    table.create(self.engine)
                    logger.info(f"✅ Created table: {table_name}")
                    self.changes_applied.append(f"Created table: {table_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to create table {table_name}: {e}")
                    raise
        else:
            logger.info("✅ All tables exist")
            
        return missing_tables
    
    def add_missing_columns(self, dry_run=False):
        """Add columns that exist in models but not in database tables"""
        existing_tables = self.get_existing_tables()
        missing_columns = []
        
        for table_name in existing_tables:
            if table_name in self.metadata.tables:
                model_table = self.metadata.tables[table_name]
                existing_columns = self.get_table_columns(table_name)
                
                for column in model_table.columns:
                    if column.name not in existing_columns:
                        missing_columns.append((table_name, column))
        
        if missing_columns:
            logger.info(f"🔧 Found {len(missing_columns)} missing columns")
            
            if dry_run:
                for table_name, column in missing_columns:
                    logger.info(f"   [DRY RUN] Would add column: {table_name}.{column.name} ({column.type})")
                return missing_columns
            
            for table_name, column in missing_columns:
                try:
                    self.add_column(table_name, column)
                    logger.info(f"✅ Added column: {table_name}.{column.name}")
                    self.changes_applied.append(f"Added column: {table_name}.{column.name}")
                except Exception as e:
                    logger.error(f"❌ Failed to add column {table_name}.{column.name}: {e}")
                    raise
        else:
            logger.info("✅ All columns exist")
            
        return missing_columns
    
    def add_column(self, table_name, column):
        """Add a single column to a table with appropriate defaults"""
        column_type = column.type.compile(self.engine.dialect)
        nullable = "NULL" if column.nullable else "NOT NULL"
        default_clause = ""
        
        # Handle default values intelligently
        if column.default is not None:
            if hasattr(column.default, 'arg'):
                if callable(column.default.arg):
                    # For server defaults like func.now()
                    if column.default.arg == func.now:
                        default_clause = "DEFAULT CURRENT_TIMESTAMP"
                    else:
                        default_clause = f"DEFAULT {column.default.arg.__name__}()"
                elif isinstance(column.default.arg, (str, int, float, bool)):
                    # For literal defaults
                    if isinstance(column.default.arg, str):
                        default_clause = f"DEFAULT '{column.default.arg}'"
                    elif isinstance(column.default.arg, bool):
                        default_clause = f"DEFAULT {str(column.default.arg).lower()}"
                    else:
                        default_clause = f"DEFAULT {column.default.arg}"
            elif hasattr(column.default, 'server_default'):
                default_clause = f"DEFAULT {column.default.server_default}"
        elif not column.nullable:
            # Provide sensible defaults for NOT NULL columns without defaults
            if 'varchar' in str(column.type).lower() or 'text' in str(column.type).lower():
                default_clause = "DEFAULT ''"
            elif 'int' in str(column.type).lower():
                default_clause = "DEFAULT 0"
            elif 'bool' in str(column.type).lower():
                default_clause = "DEFAULT false"
            elif 'timestamp' in str(column.type).lower():
                default_clause = "DEFAULT CURRENT_TIMESTAMP"
        
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {column_type} {nullable} {default_clause}"
        
        with self.engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
    
    def check_column_changes(self):
        """Check for column type changes (warns but doesn't auto-modify)"""
        existing_tables = self.get_existing_tables()
        type_changes = []
        
        for table_name in existing_tables:
            if table_name in self.metadata.tables:
                model_table = self.metadata.tables[table_name]
                existing_columns = self.get_table_columns(table_name)
                
                for column in model_table.columns:
                    if column.name in existing_columns:
                        existing_col = existing_columns[column.name]
                        model_type = str(column.type).upper()
                        existing_type = str(existing_col['type']).upper()
                        
                        # Normalize type comparisons
                        if model_type != existing_type:
                            # Handle common equivalent types
                            if not self._are_types_compatible(model_type, existing_type):
                                type_changes.append({
                                    'table': table_name,
                                    'column': column.name,
                                    'current_type': existing_type,
                                    'model_type': model_type
                                })
        
        if type_changes:
            logger.warning(f"⚠️  Found {len(type_changes)} potential column type changes:")
            for change in type_changes:
                logger.warning(f"   {change['table']}.{change['column']}: {change['current_type']} → {change['model_type']}")
                self.warnings.append(f"Column type change needed: {change['table']}.{change['column']}")
        
        return type_changes
    
    def _are_types_compatible(self, model_type, existing_type):
        """Check if two column types are compatible (to avoid false positives)"""
        # Common equivalent type mappings
        equivalents = [
            ('VARCHAR', 'CHARACTER VARYING'),
            ('INTEGER', 'INT4'),
            ('BOOLEAN', 'BOOL'),
            ('TIMESTAMP', 'TIMESTAMP WITHOUT TIME ZONE'),
            ('JSONB', 'JSON'),
        ]
        
        for type1, type2 in equivalents:
            if (type1 in model_type and type2 in existing_type) or (type2 in model_type and type1 in existing_type):
                return True
        
        return model_type == existing_type
    
    def create_missing_indexes(self, dry_run=False):
        """Create missing indexes and constraints"""
        missing_indexes = []
        
        # Check indexes for each table
        for table_name, table in self.metadata.tables.items():
            if table_name in self.get_existing_tables():
                existing_indexes = self.get_table_indexes(table_name)
                
                # Check table indexes
                for index in table.indexes:
                    if index.name not in existing_indexes:
                        missing_indexes.append((table_name, index))
        
        if missing_indexes:
            logger.info(f"📊 Found {len(missing_indexes)} missing indexes")
            
            if dry_run:
                for table_name, index in missing_indexes:
                    logger.info(f"   [DRY RUN] Would create index: {index.name} on {table_name}")
                return missing_indexes
            
            for table_name, index in missing_indexes:
                try:
                    index.create(self.engine)
                    logger.info(f"✅ Created index: {index.name} on {table_name}")
                    self.changes_applied.append(f"Created index: {index.name}")
                except Exception as e:
                    logger.error(f"❌ Failed to create index {index.name}: {e}")
                    # Don't raise for index creation failures, just warn
                    self.warnings.append(f"Failed to create index: {index.name}")
        else:
            logger.info("✅ All indexes exist")
        
        return missing_indexes
    
    # ✅ NEW: Data seeding functionality
    def seed_mental_training_quotes(self, dry_run=False):
        """Seed mental training quotes from the text file"""
        if not self.quotes_file.exists():
            logger.warning(f"⚠️  Mental training quotes file not found: {self.quotes_file}")
            return 0
        
        try:
            with open(self.quotes_file, 'r') as f:
                quotes_data = json.load(f)
            
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            db = SessionLocal()
            
            try:
                # Get existing quotes to avoid duplicates
                existing_quotes = set()
                for quote in db.query(models.MentalTrainingQuote).all():
                    existing_quotes.add((quote.content.strip(), quote.author.strip()))
                
                new_quotes = []
                for quote_data in quotes_data:
                    content = quote_data['content'].strip()
                    author = quote_data['author'].strip()
                    
                    if (content, author) not in existing_quotes:
                        new_quotes.append(models.MentalTrainingQuote(
                            content=content,
                            author=author,
                            type=quote_data.get('type', 'motivational'),
                            display_duration=quote_data.get('display_duration', 8)
                        ))
                
                if new_quotes:
                    logger.info(f"🧠 Found {len(new_quotes)} new mental training quotes to seed")
                    
                    if dry_run:
                        for quote in new_quotes[:3]:  # Show first 3
                            logger.info(f"   [DRY RUN] Would add: \"{quote.content[:50]}...\" - {quote.author}")
                        if len(new_quotes) > 3:
                            logger.info(f"   [DRY RUN] ... and {len(new_quotes) - 3} more quotes")
                        return len(new_quotes)
                    
                    for quote in new_quotes:
                        db.add(quote)
                    
                    db.commit()
                    logger.info(f"✅ Seeded {len(new_quotes)} mental training quotes")
                    self.changes_applied.append(f"Seeded {len(new_quotes)} mental training quotes")
                    return len(new_quotes)
                else:
                    logger.info("✅ All mental training quotes already exist")
                    return 0
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Failed to seed mental training quotes: {e}")
            raise
    
    def sync_drill_data(self, dry_run=False):
        """Sync drill data from JSON files to database"""
        if not self.drills_dir.exists():
            logger.warning(f"⚠️  Drills directory not found: {self.drills_dir}")
            return 0
        
        drill_files = list(self.drills_dir.glob("*_drills.txt"))
        if not drill_files:
            logger.info("ℹ️  No drill files found to sync")
            return 0
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        db = SessionLocal()
        
        try:
            total_synced = 0
            
            for drill_file in drill_files:
                category_name = drill_file.stem.replace('_drills', '')
                logger.info(f"🏃 Syncing {category_name} drills from {drill_file.name}")
                
                try:
                    with open(drill_file, 'r') as f:
                        drills_data = json.load(f)
                    
                    # Get or create drill category
                    category = db.query(models.DrillCategory).filter(
                        models.DrillCategory.name == category_name
                    ).first()
                    
                    if not category:
                        if dry_run:
                            logger.info(f"   [DRY RUN] Would create category: {category_name}")
                        else:
                            category = models.DrillCategory(name=category_name, description=f"{category_name.title()} drills")
                            db.add(category)
                            db.commit()
                            db.refresh(category)
                            logger.info(f"✅ Created drill category: {category_name}")
                    
                    synced_count = 0
                    for drill_data in drills_data:
                        # Create a unique identifier for the drill (title + category)
                        drill_title = drill_data.get('title', '').strip()
                        if not drill_title:
                            continue
                        
                        # Check if drill exists
                        existing_drill = db.query(models.Drill).filter(
                            models.Drill.title == drill_title,
                            models.Drill.category_id == category.id
                        ).first()
                        
                        if existing_drill:
                            # ✅ UPDATE: Sync changes to existing drill
                            updated = self._update_drill_from_data(existing_drill, drill_data, dry_run)
                            if updated:
                                synced_count += 1
                        else:
                            # ✅ CREATE: Add new drill
                            if dry_run:
                                logger.info(f"   [DRY RUN] Would create drill: {drill_title}")
                                synced_count += 1
                            else:
                                new_drill = self._create_drill_from_data(drill_data, category.id, db)
                                if new_drill:
                                    synced_count += 1
                    
                    if not dry_run and synced_count > 0:
                        db.commit()
                    
                    logger.info(f"✅ Synced {synced_count} drills for {category_name}")
                    total_synced += synced_count
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON in {drill_file}: {e}")
                except Exception as e:
                    logger.error(f"❌ Failed to sync drills from {drill_file}: {e}")
            
            if total_synced > 0:
                self.changes_applied.append(f"Synced {total_synced} drills from files")
            
            return total_synced
            
        finally:
            db.close()
    
    def _update_drill_from_data(self, drill, drill_data, dry_run=False):
        """Update existing drill with data from JSON file"""
        # Compare key fields and update if different
        changes = []
        
        if drill.description != drill_data.get('description', ''):
            changes.append('description')
        if drill.difficulty != drill_data.get('difficulty', ''):
            changes.append('difficulty')
        if drill.duration != drill_data.get('duration'):
            changes.append('duration')
        
        # Add more field comparisons as needed
        
        if changes:
            if dry_run:
                logger.info(f"   [DRY RUN] Would update drill '{drill.title}': {', '.join(changes)}")
                return True
            else:
                # Update the drill
                drill.description = drill_data.get('description', drill.description)
                drill.difficulty = drill_data.get('difficulty', drill.difficulty)
                drill.duration = drill_data.get('duration', drill.duration)
                drill.sets = drill_data.get('sets', drill.sets)
                drill.reps = drill_data.get('reps', drill.reps)
                drill.rest = drill_data.get('rest', drill.rest)
                drill.equipment = drill_data.get('equipment', drill.equipment)
                drill.suitable_locations = drill_data.get('suitable_locations', drill.suitable_locations)
                drill.intensity = drill_data.get('intensity', drill.intensity)
                drill.training_styles = drill_data.get('training_styles', drill.training_styles)
                drill.instructions = drill_data.get('instructions', drill.instructions)
                drill.tips = drill_data.get('tips', drill.tips)
                drill.common_mistakes = drill_data.get('common_mistakes', drill.common_mistakes)
                drill.progression_steps = drill_data.get('progression_steps', drill.progression_steps)
                drill.variations = drill_data.get('variations', drill.variations)
                drill.video_url = drill_data.get('video_url', drill.video_url)
                drill.thumbnail_url = drill_data.get('thumbnail_url', drill.thumbnail_url)
                
                return True
        
        return False
    
    def _create_drill_from_data(self, drill_data, category_id, db):
        """Create new drill from JSON data"""
        try:
            drill = models.Drill(
                title=drill_data.get('title', ''),
                description=drill_data.get('description', ''),
                category_id=category_id,
                type=drill_data.get('type', 'time_based'),
                duration=drill_data.get('duration'),
                sets=drill_data.get('sets'),
                reps=drill_data.get('reps'),
                rest=drill_data.get('rest'),
                equipment=drill_data.get('equipment', []),
                suitable_locations=drill_data.get('suitable_locations', []),
                intensity=drill_data.get('intensity', 'medium'),
                training_styles=drill_data.get('training_styles', []),
                difficulty=drill_data.get('difficulty', 'beginner'),
                instructions=drill_data.get('instructions', []),
                tips=drill_data.get('tips', []),
                common_mistakes=drill_data.get('common_mistakes', []),
                progression_steps=drill_data.get('progression_steps', []),
                variations=drill_data.get('variations', []),
                video_url=drill_data.get('video_url'),
                thumbnail_url=drill_data.get('thumbnail_url')
            )
            
            db.add(drill)
            
            # Add skill focus relationships
            primary_skill = drill_data.get('primary_skill', {})
            if primary_skill:
                skill_focus = models.DrillSkillFocus(
                    drill=drill,
                    category=primary_skill.get('category', ''),
                    sub_skill=primary_skill.get('sub_skill', ''),
                    is_primary=True
                )
                db.add(skill_focus)
            
            # Add secondary skills
            for secondary_skill in drill_data.get('secondary_skills', []):
                skill_focus = models.DrillSkillFocus(
                    drill=drill,
                    category=secondary_skill.get('category', ''),
                    sub_skill=secondary_skill.get('sub_skill', ''),
                    is_primary=False
                )
                db.add(skill_focus)
            
            return drill
            
        except Exception as e:
            logger.error(f"Failed to create drill from data: {e}")
            return None
    
    def analyze_database(self):
        """Comprehensive analysis of database vs models"""
        logger.info("🔍 Analyzing database schema vs models...")
        
        existing_tables = self.get_existing_tables()
        model_tables = self.get_model_tables()
        
        analysis = {
            'existing_tables': len(existing_tables),
            'model_tables': len(model_tables),
            'missing_tables': model_tables - existing_tables,
            'extra_tables': existing_tables - model_tables,
            'missing_columns': [],
            'total_columns': 0,
            'total_indexes': 0,
        }
        
        # Analyze columns
        for table_name in existing_tables & model_tables:
            model_table = self.metadata.tables[table_name]
            existing_columns = self.get_table_columns(table_name)
            
            analysis['total_columns'] += len(existing_columns)
            
            for column in model_table.columns:
                if column.name not in existing_columns:
                    analysis['missing_columns'].append(f"{table_name}.{column.name}")
        
        # Analyze indexes
        for table_name in existing_tables:
            indexes = self.get_table_indexes(table_name)
            analysis['total_indexes'] += len(indexes)
        
        return analysis
    
    def show_status(self):
        """Show comprehensive database status"""
        logger.info("📊 Database Schema Status Report")
        logger.info("=" * 50)
        
        analysis = self.analyze_database()
        
        logger.info(f"📋 Tables: {analysis['existing_tables']} in DB, {analysis['model_tables']} in models")
        logger.info(f"📋 Columns: {analysis['total_columns']} total")
        logger.info(f"📋 Indexes: {analysis['total_indexes']} total")
        
        if analysis['missing_tables']:
            logger.warning(f"🆕 Missing tables ({len(analysis['missing_tables'])}): {list(analysis['missing_tables'])}")
        
        if analysis['extra_tables']:
            logger.warning(f"🗑️  Extra tables ({len(analysis['extra_tables'])}): {list(analysis['extra_tables'])}")
        
        if analysis['missing_columns']:
            logger.warning(f"🔧 Missing columns ({len(analysis['missing_columns'])}): {analysis['missing_columns']}")
        
        # Check for type changes
        type_changes = self.check_column_changes()
        
        # ✅ NEW: Check data integrity status
        logger.info("")
        self._show_data_status()
        
        # Check if data integrity fixes are needed
        data_fixes_needed = 0
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM drill_skill_focus dsf
                    LEFT JOIN drills d ON dsf.drill_uuid = d.uuid
                    WHERE d.uuid IS NULL
                """))
                data_fixes_needed = result.scalar()
        except Exception:
            pass
        
        # Summary
        needs_migration = bool(
            analysis['missing_tables'] or 
            analysis['missing_columns'] or 
            type_changes or
            data_fixes_needed > 0
        )
        
        logger.info("")
        if needs_migration:
            logger.warning("⚠️  Database is OUT OF SYNC with models.py")
            if data_fixes_needed > 0:
                logger.warning(f"⚠️  {data_fixes_needed} data integrity issues found")
            logger.info("💡 Run 'python migrate_schema.py migrate' to fix everything")
            logger.info("💡 Run 'python migrate_schema.py migrate --dry-run' to preview changes")
        else:
            logger.info("✅ Database is IN SYNC with models.py")
            logger.info("✅ All data integrity checks passed")
        
        return analysis
    
    def _show_data_status(self):
        """Show status of data integrity and seeding"""
        logger.info("📊 Data Integrity Status")
        logger.info("-" * 30)
        
        try:
            with self.engine.connect() as conn:
                # Check mental training quotes
                result = conn.execute(text("SELECT COUNT(*) FROM mental_training_quotes"))
                quotes_count = result.scalar()
                logger.info(f"📝 Mental training quotes: {quotes_count}")
                
                # Check drill count
                result = conn.execute(text("SELECT COUNT(*) FROM drills"))
                drills_count = result.scalar()
                logger.info(f"🏃 Drills: {drills_count}")
                
                # ✅ NEW: Check drill_skill_focus integrity
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM drill_skill_focus dsf
                    LEFT JOIN drills d ON dsf.drill_uuid = d.uuid
                    WHERE d.uuid IS NULL
                """))
                orphaned_skill_focus = result.scalar()
                
                if orphaned_skill_focus > 0:
                    logger.warning(f"⚠️  Orphaned drill_skill_focus records: {orphaned_skill_focus}")
                    logger.warning("   💡 Run 'python migrate_schema.py fix-data' to repair")
                else:
                    logger.info(f"✅ Drill skill focus integrity: OK")
                
        except Exception as e:
            logger.warning(f"⚠️  Could not check data status: {e}")

    def fix_data_integrity(self, dry_run=False):
        """Fix data integrity issues, specifically drill_skill_focus UUID relationships"""
        logger.info("🔧 Checking and fixing data integrity issues...")
        
        fixed_count = 0
        
        try:
            with self.engine.connect() as conn:
                # Check for orphaned drill_skill_focus records
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM drill_skill_focus dsf
                    LEFT JOIN drills d ON dsf.drill_uuid = d.uuid
                    WHERE d.uuid IS NULL
                """))
                orphaned_count = result.scalar()
                
                if orphaned_count == 0:
                    logger.info("✅ No data integrity issues found")
                    return 0
                
                logger.info(f"🔍 Found {orphaned_count} orphaned drill_skill_focus records")
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would fix {orphaned_count} orphaned drill_skill_focus records")
                    return orphaned_count
                
                # Create backup table first
                backup_table = f"drill_skill_focus_backup_{int(datetime.now().timestamp())}"
                conn.execute(text(f"""
                    CREATE TABLE {backup_table} AS 
                    SELECT * FROM drill_skill_focus
                """))
                logger.info(f"💾 Created backup table: {backup_table}")
                
                # Get drill ID to UUID mapping
                result = conn.execute(text("SELECT id, uuid FROM drills"))
                id_to_uuid = {row[0]: str(row[1]) for row in result}
                logger.info(f"📋 Found {len(id_to_uuid)} drill ID to UUID mappings")
                
                # Get orphaned records and try to fix them
                result = conn.execute(text("""
                    SELECT dsf.id, dsf.drill_uuid, dsf.category, dsf.sub_skill, dsf.is_primary
                    FROM drill_skill_focus dsf
                    LEFT JOIN drills d ON dsf.drill_uuid = d.uuid
                    WHERE d.uuid IS NULL
                """))
                
                orphaned_records = result.fetchall()
                
                for record in orphaned_records:
                    record_id, old_drill_uuid, category, sub_skill, is_primary = record
                    
                    try:
                        # Try to parse the old drill_uuid as an integer (probably old drill_id)
                        old_drill_id = int(old_drill_uuid) if old_drill_uuid else None
                        
                        if old_drill_id and old_drill_id in id_to_uuid:
                            correct_uuid = id_to_uuid[old_drill_id]
                            
                            # Update the record
                            conn.execute(text("""
                                UPDATE drill_skill_focus 
                                SET drill_uuid = :new_uuid
                                WHERE id = :record_id
                            """), {
                                'new_uuid': correct_uuid,
                                'record_id': record_id
                            })
                            
                            fixed_count += 1
                            logger.info(f"   ✅ Fixed record {record_id}: drill_id {old_drill_id} -> UUID {correct_uuid}")
                        else:
                            # Remove orphaned record that can't be fixed
                            conn.execute(text("""
                                DELETE FROM drill_skill_focus WHERE id = :record_id
                            """), {'record_id': record_id})
                            logger.warning(f"   🗑️  Removed orphaned record {record_id} (drill_uuid: {old_drill_uuid})")
                            
                    except (ValueError, TypeError):
                        # Remove records with invalid drill_uuid values
                        conn.execute(text("""
                            DELETE FROM drill_skill_focus WHERE id = :record_id
                        """), {'record_id': record_id})
                        logger.warning(f"   🗑️  Removed invalid record {record_id} (drill_uuid: {old_drill_uuid})")
                
                conn.commit()
                
                # Verify the fix
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM drill_skill_focus dsf
                    LEFT JOIN drills d ON dsf.drill_uuid = d.uuid
                    WHERE d.uuid IS NULL
                """))
                remaining_orphaned = result.scalar()
                
                if remaining_orphaned == 0:
                    logger.info(f"✅ Successfully fixed all drill_skill_focus relationships")
                    logger.info(f"   📊 {fixed_count} records updated, {orphaned_count - fixed_count} invalid records removed")
                    logger.info(f"   💾 Backup available at: {backup_table}")
                    self.changes_applied.append(f"Fixed {fixed_count} drill_skill_focus relationships")
                else:
                    logger.warning(f"⚠️  {remaining_orphaned} orphaned records remain")
                
        except Exception as e:
            logger.error(f"❌ Failed to fix data integrity: {e}")
            raise
        
        return fixed_count
    
    def run_migration(self, dry_run=False, seed_data=False):
        """Run the complete migration process"""
        action = "DRY RUN" if dry_run else "MIGRATION"
        if seed_data:
            action += " + DATA SEEDING"
            
        logger.info(f"🚀 Starting {action}...")
        logger.info("=" * 50)
        
        try:
            # Step 1: Create missing tables
            logger.info("Step 1: Checking for missing tables...")
            missing_tables = self.create_missing_tables(dry_run=dry_run)
            
            # Step 2: Add missing columns
            logger.info("Step 2: Checking for missing columns...")
            missing_columns = self.add_missing_columns(dry_run=dry_run)
            
            # Step 3: Check for type changes (warning only)
            logger.info("Step 3: Checking for column type changes...")
            type_changes = self.check_column_changes()
            
            # Step 4: Create missing indexes
            logger.info("Step 4: Checking for missing indexes...")
            missing_indexes = self.create_missing_indexes(dry_run=dry_run)
            
            # ✅ NEW: Step 5: Fix data integrity issues
            logger.info("Step 5: Checking data integrity...")
            fixed_data_count = self.fix_data_integrity(dry_run=dry_run)
            
            # ✅ UPDATED: Step 6: Seed data if requested (moved after data fixes)
            seeded_quotes = 0
            synced_drills = 0
            if seed_data:
                logger.info("Step 6: Seeding mental training quotes...")
                seeded_quotes = self.seed_mental_training_quotes(dry_run=dry_run)
                
                logger.info("Step 7: Syncing drill data...")
                synced_drills = self.sync_drill_data(dry_run=dry_run)
            
            # Summary
            total_changes = len(missing_tables) + len(missing_columns) + len(missing_indexes) + fixed_data_count
            total_data_changes = seeded_quotes + synced_drills
            
            if dry_run:
                logger.info(f"📋 DRY RUN COMPLETE")
                logger.info(f"   - {total_changes} total changes would be applied")
                logger.info(f"     • {len(missing_tables)} tables created")
                logger.info(f"     • {len(missing_columns)} columns added")
                logger.info(f"     • {len(missing_indexes)} indexes created")
                logger.info(f"     • {fixed_data_count} data integrity fixes")
                if seed_data:
                    logger.info(f"   - {total_data_changes} data changes would be applied")
                if total_changes > 0 or (seed_data and total_data_changes > 0):
                    logger.info("💡 Run without --dry-run to apply changes")
            else:
                logger.info(f"✅ MIGRATION COMPLETE")
                logger.info(f"   - {total_changes} total changes applied")
                logger.info(f"     • {len(missing_tables)} tables created")
                logger.info(f"     • {len(missing_columns)} columns added") 
                logger.info(f"     • {len(missing_indexes)} indexes created")
                logger.info(f"     • {fixed_data_count} data integrity fixes")
                if seed_data:
                    logger.info(f"   - {total_data_changes} data changes applied")
                
                if self.changes_applied:
                    logger.info("📝 Changes applied:")
                    for change in self.changes_applied:
                        logger.info(f"   ✓ {change}")
                
                if self.warnings:
                    logger.warning("⚠️  Warnings:")
                    for warning in self.warnings:
                        logger.warning(f"   ! {warning}")
            
        except Exception as e:
            logger.error(f"❌ {action} failed: {e}")
            raise
    
    def generate_backup_commands(self):
        """Generate backup commands for production safety"""
        logger.info("💾 Database Backup Commands")
        logger.info("=" * 50)
        
        # Extract database info from URL
        url_parts = self.database_url.split('/')
        if len(url_parts) > 3:
            db_name = url_parts[-1].split('?')[0]  # Remove query params
            
            backup_file = f"backup_{db_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            
            logger.info("🔹 PostgreSQL backup command:")
            logger.info(f"   pg_dump {self.database_url} > {backup_file}")
            logger.info("")
            logger.info("🔹 Restore command (if needed):")
            logger.info(f"   psql {self.database_url} < {backup_file}")
            logger.info("")
            logger.info("🔹 Backup verification:")
            logger.info(f"   pg_restore --list {backup_file}")
        else:
            logger.info("⚠️  Could not parse database URL for backup commands")
            logger.info("   Please create a backup manually before running migration")


def main():
    """Main migration function"""
    if len(sys.argv) < 2:
        print("Usage: python migrate_schema.py [command] [options]")
        print("")
        print("Commands:")
        print("  status                     - Show database status vs models")
        print("  migrate                    - Run full migration")
        print("  migrate --dry-run          - Show what would be changed")
        print("  migrate --seed             - Run migration + seed data")
        print("  seed                       - Seed data only (quotes + drills)")
        print("  sync-drills                - Sync drill data only")
        print("  backup                     - Show backup commands")
        print("  production <DATABASE_URL>  - Production migration with safety checks")
        print("  fix-data                   - Fix drill_skill_focus UUID integrity issues")
        print("")
        print("Examples:")
        print("  python migrate_schema.py status")
        print("  python migrate_schema.py migrate --dry-run")
        print("  python migrate_schema.py migrate --seed")
        print("  python migrate_schema.py seed")
        print("  python migrate_schema.py sync-drills")
        print("  python migrate_schema.py production 'postgresql://user:pass@host:5432/db'")
        print("  python migrate_schema.py fix-data")
        sys.exit(1)
    
    command = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    seed_data = "--seed" in sys.argv
    
    try:
        if command == "production":
            if len(sys.argv) < 3:
                print("❌ Production command requires database URL")
                print("Usage: python migrate_schema.py production <DATABASE_URL>")
                sys.exit(1)
            
            database_url = sys.argv[2]
            migrator = SchemaMigrator(database_url)
            
            logger.info("🔐 PRODUCTION MIGRATION MODE")
            logger.info("⚠️  Make sure you have a backup before proceeding!")
            logger.info("")
            
            # Show backup commands first
            migrator.generate_backup_commands()
            
            response = input("\n🤔 Have you created a backup? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                logger.info("❌ Migration cancelled - create backup first")
                sys.exit(1)
            
            # Run migration
            migrator.run_migration(dry_run=dry_run, seed_data=seed_data)
            
        elif command == "fix-data":
            migrator = SchemaMigrator()
            fixed_count = migrator.fix_data_integrity(dry_run=dry_run)
            if dry_run:
                logger.info(f"[DRY RUN] Would fix {fixed_count} drill_skill_focus relationships")
            else:
                logger.info(f"✅ Fixed {fixed_count} drill_skill_focus relationships")
        else:
            migrator = SchemaMigrator()
            
            if command == "status":
                migrator.show_status()
            elif command == "migrate":
                migrator.run_migration(dry_run=dry_run, seed_data=seed_data)
            elif command == "seed":
                logger.info("🌱 Seeding database with initial data...")
                quotes_seeded = migrator.seed_mental_training_quotes(dry_run=dry_run)
                drills_synced = migrator.sync_drill_data(dry_run=dry_run)
                if dry_run:
                    logger.info(f"[DRY RUN] Would seed {quotes_seeded} quotes and sync {drills_synced} drills")
                else:
                    logger.info(f"✅ Seeded {quotes_seeded} quotes and synced {drills_synced} drills")
            elif command == "sync-drills":
                logger.info("🏃 Syncing drill data from files...")
                synced = migrator.sync_drill_data(dry_run=dry_run)
                if dry_run:
                    logger.info(f"[DRY RUN] Would sync {synced} drills")
                else:
                    logger.info(f"✅ Synced {synced} drills")
            elif command == "backup":
                migrator.generate_backup_commands()
            else:
                print(f"❌ Unknown command: {command}")
                sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("\n❌ Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 