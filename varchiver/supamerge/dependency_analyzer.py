#!/usr/bin/env python3
"""
Multi-Project Dependency Analyzer and Merge Strategy Tool

This module provides sophisticated analysis of table dependencies and foreign key
relationships across multiple Supabase projects, with intelligent conflict resolution
for complex merging scenarios like shared `projects` tables.

Key Features:
- Dynamic foreign key dependency mapping
- Cross-project table relationship analysis
- Intelligent merge conflict resolution strategies
- Data integrity validation during merges
- Rollback capability planning

Author: Varchiver Team
"""

import asyncio
import json
import logging
import psycopg2
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime
from pathlib import Path
import networkx as nx
import yaml


@dataclass
class TableDependency:
    """Represents a foreign key dependency between tables."""

    source_table: str
    source_column: str
    target_table: str
    target_column: str
    constraint_name: str
    is_nullable: bool
    dependency_type: str = "foreign_key"  # foreign_key, reference, composite


@dataclass
class TableMetadata:
    """Comprehensive metadata for a database table."""

    name: str
    schema: str
    row_count: int
    columns: List[Dict[str, Any]] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[TableDependency] = field(default_factory=list)
    referenced_by: List[TableDependency] = field(default_factory=list)
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    has_data: bool = False
    project_source: str = ""


@dataclass
class MergeConflict:
    """Represents a conflict between two projects during merge."""

    table_name: str
    conflict_type: str  # "data_conflict", "schema_mismatch", "dependency_cycle"
    source_rows: int
    target_rows: int
    resolution_strategy: str = (
        "manual"  # "merge", "overwrite", "skip", "rename", "manual"
    )
    affected_dependencies: List[str] = field(default_factory=list)
    risk_level: str = "medium"  # "low", "medium", "high", "critical"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MergeStrategy:
    """Complete strategy for merging two projects."""

    source_project: str
    target_project: str
    execution_order: List[str] = field(default_factory=list)
    conflicts: List[MergeConflict] = field(default_factory=list)
    dependency_graph: Optional[nx.DiGraph] = None
    rollback_plan: Dict[str, Any] = field(default_factory=dict)
    estimated_duration: int = 0  # minutes
    safety_score: float = 0.0  # 0.0-1.0


class DependencyAnalyzer:
    """Advanced dependency analyzer for multi-project Supabase merges."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._setup_logging()
        self.projects_metadata: Dict[str, Dict[str, TableMetadata]] = {}
        self.dependency_graphs: Dict[str, nx.DiGraph] = {}

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the analyzer."""
        logger = logging.getLogger("dependency_analyzer")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    async def analyze_project(
        self, db_url: str, project_name: str
    ) -> Dict[str, TableMetadata]:
        """Analyze a single project's table dependencies."""
        self.logger.info(f"🔍 Analyzing project dependencies: {project_name}")

        tables_metadata = {}

        try:
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()

            # Get all tables
            tables = await self._get_all_tables(cur)
            self.logger.info(f"Found {len(tables)} tables in {project_name}")

            # Analyze each table
            for table_name in tables:
                metadata = await self._analyze_table(cur, table_name, project_name)
                tables_metadata[table_name] = metadata

            # Build dependency relationships
            await self._build_dependency_relationships(cur, tables_metadata)

            # Create dependency graph
            self.dependency_graphs[project_name] = self._create_dependency_graph(
                tables_metadata
            )

            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to analyze project {project_name}: {e}")
            raise

        self.projects_metadata[project_name] = tables_metadata
        return tables_metadata

    async def _get_all_tables(self, cursor) -> List[str]:
        """Get all tables from information_schema."""
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        return [row[0] for row in cursor.fetchall()]

    async def _analyze_table(
        self, cursor, table_name: str, project_name: str
    ) -> TableMetadata:
        """Analyze individual table metadata."""
        # Get row count
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            row_count = cursor.fetchone()[0]
        except:
            row_count = 0

        # Get columns
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """,
            (table_name,),
        )

        columns = []
        for row in cursor.fetchall():
            columns.append(
                {
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "default": row[3],
                }
            )

        # Get primary keys
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.key_column_usage
            WHERE table_schema = 'public' AND table_name = %s
            AND constraint_name IN (
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_schema = 'public' AND table_name = %s
                AND constraint_type = 'PRIMARY KEY'
            )
        """,
            (table_name, table_name),
        )

        primary_keys = [row[0] for row in cursor.fetchall()]

        return TableMetadata(
            name=table_name,
            schema="public",
            row_count=row_count,
            columns=columns,
            primary_keys=primary_keys,
            has_data=row_count > 0,
            project_source=project_name,
        )

    async def _build_dependency_relationships(
        self, cursor, tables_metadata: Dict[str, TableMetadata]
    ):
        """Build foreign key relationships between tables."""
        cursor.execute("""
            SELECT
                tc.table_name as source_table,
                kcu.column_name as source_column,
                ccu.table_name as target_table,
                ccu.column_name as target_column,
                tc.constraint_name,
                col.is_nullable
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
            JOIN information_schema.columns col
                ON col.table_name = tc.table_name
                AND col.column_name = kcu.column_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
        """)

        for row in cursor.fetchall():
            source_table, source_col, target_table, target_col, constraint, nullable = (
                row
            )

            dependency = TableDependency(
                source_table=source_table,
                source_column=source_col,
                target_table=target_table,
                target_column=target_col,
                constraint_name=constraint,
                is_nullable=nullable == "YES",
            )

            if source_table in tables_metadata:
                tables_metadata[source_table].foreign_keys.append(dependency)

            if target_table in tables_metadata:
                tables_metadata[target_table].referenced_by.append(dependency)

    def _create_dependency_graph(
        self, tables_metadata: Dict[str, TableMetadata]
    ) -> nx.DiGraph:
        """Create a directed graph of table dependencies."""
        graph = nx.DiGraph()

        # Add nodes
        for table_name, metadata in tables_metadata.items():
            graph.add_node(
                table_name,
                **{
                    "row_count": metadata.row_count,
                    "has_data": metadata.has_data,
                    "primary_keys": metadata.primary_keys,
                },
            )

        # Add edges (dependencies)
        for table_name, metadata in tables_metadata.items():
            for fk in metadata.foreign_keys:
                graph.add_edge(
                    fk.target_table,
                    fk.source_table,
                    **{
                        "constraint": fk.constraint_name,
                        "columns": f"{fk.target_column}->{fk.source_column}",
                        "nullable": fk.is_nullable,
                    },
                )

        return graph

    async def compare_projects(
        self, source_project: str, target_project: str
    ) -> List[MergeConflict]:
        """Compare two projects and identify merge conflicts."""
        self.logger.info(f"🔄 Comparing {source_project} → {target_project}")

        if source_project not in self.projects_metadata:
            raise ValueError(f"Source project {source_project} not analyzed")
        if target_project not in self.projects_metadata:
            raise ValueError(f"Target project {target_project} not analyzed")

        source_tables = self.projects_metadata[source_project]
        target_tables = self.projects_metadata[target_project]

        conflicts = []

        # Find overlapping tables
        common_tables = set(source_tables.keys()) & set(target_tables.keys())
        self.logger.info(f"Found {len(common_tables)} common tables")

        for table_name in common_tables:
            source_meta = source_tables[table_name]
            target_meta = target_tables[table_name]

            conflict = await self._analyze_table_conflict(
                table_name, source_meta, target_meta, source_tables, target_tables
            )
            if conflict:
                conflicts.append(conflict)

        return conflicts

    async def _analyze_table_conflict(
        self,
        table_name: str,
        source_meta: TableMetadata,
        target_meta: TableMetadata,
        source_tables: Dict[str, TableMetadata],
        target_tables: Dict[str, TableMetadata],
    ) -> Optional[MergeConflict]:
        """Analyze conflict between two versions of the same table."""

        # No conflict if both tables are empty
        if not source_meta.has_data and not target_meta.has_data:
            return None

        # Count dependencies dynamically
        total_dependents = 0
        critical_dependents = []

        # Check dependencies across both projects
        all_project_tables = {**source_tables, **target_tables}
        for tbl_meta in all_project_tables.values():
            for fk in tbl_meta.foreign_keys:
                if fk.target_table == table_name:
                    total_dependents += 1
                    if tbl_meta.has_data:
                        critical_dependents.append(
                            f"{tbl_meta.project_source}.{tbl_meta.name}"
                        )

        # Determine conflict type and risk level dynamically
        conflict_type = "data_conflict"
        risk_level = "medium"
        resolution_strategy = "merge"

        # Risk escalation based on dependencies and data
        if source_meta.has_data and target_meta.has_data:
            if total_dependents >= 5:  # High dependency table
                risk_level = "critical"
                conflict_type = "critical_shared_dependency"
                resolution_strategy = "manual"
            elif total_dependents >= 2:  # Medium dependency table
                risk_level = "high"
                conflict_type = "shared_dependency_conflict"
            else:
                risk_level = "high"

        return MergeConflict(
            table_name=table_name,
            conflict_type=conflict_type,
            source_rows=source_meta.row_count,
            target_rows=target_meta.row_count,
            resolution_strategy=resolution_strategy,
            affected_dependencies=critical_dependents,
            risk_level=risk_level,
            details={
                "source_columns": len(source_meta.columns),
                "target_columns": len(target_meta.columns),
                "source_pks": source_meta.primary_keys,
                "target_pks": target_meta.primary_keys,
                "total_dependent_tables": total_dependents,
                "tables_with_data_depending": len(critical_dependents),
                "dependency_score": total_dependents
                * (1.5 if source_meta.has_data and target_meta.has_data else 1.0),
            },
        )

    async def create_merge_strategy(
        self, source_project: str, target_project: str
    ) -> MergeStrategy:
        """Create a comprehensive merge strategy."""
        self.logger.info(
            f"📋 Creating merge strategy: {source_project} → {target_project}"
        )

        conflicts = await self.compare_projects(source_project, target_project)

        # Create execution order based on dependency graph
        execution_order = self._calculate_execution_order(
            source_project, target_project
        )

        # Calculate safety score
        safety_score = self._calculate_safety_score(conflicts)

        # Estimate duration
        estimated_duration = self._estimate_merge_duration(conflicts, execution_order)

        # Create rollback plan
        rollback_plan = self._create_rollback_plan(conflicts)

        return MergeStrategy(
            source_project=source_project,
            target_project=target_project,
            execution_order=execution_order,
            conflicts=conflicts,
            dependency_graph=self.dependency_graphs.get(target_project),
            rollback_plan=rollback_plan,
            estimated_duration=estimated_duration,
            safety_score=safety_score,
        )

    def _calculate_execution_order(
        self, source_project: str, target_project: str
    ) -> List[str]:
        """Calculate safe execution order based on dependencies."""
        if target_project not in self.dependency_graphs:
            return []

        graph = self.dependency_graphs[target_project]

        try:
            # Topological sort for dependency-safe order
            execution_order = list(nx.topological_sort(graph))
            self.logger.info(
                f"Calculated execution order: {len(execution_order)} tables"
            )
            return execution_order
        except nx.NetworkXError as e:
            self.logger.warning(f"Circular dependency detected: {e}")
            # Fallback: tables with no dependencies first
            no_deps = [node for node in graph.nodes() if graph.in_degree(node) == 0]
            return no_deps + [node for node in graph.nodes() if node not in no_deps]

    def _calculate_safety_score(self, conflicts: List[MergeConflict]) -> float:
        """Calculate overall safety score (0.0 = dangerous, 1.0 = safe)."""
        if not conflicts:
            return 1.0

        risk_weights = {"low": 0.1, "medium": 0.3, "high": 0.6, "critical": 1.0}
        total_risk = sum(
            risk_weights.get(conflict.risk_level, 0.5) for conflict in conflicts
        )
        max_possible_risk = len(conflicts) * 1.0

        return max(0.0, 1.0 - (total_risk / max_possible_risk))

    def _estimate_merge_duration(
        self, conflicts: List[MergeConflict], execution_order: List[str]
    ) -> int:
        """Estimate merge duration in minutes."""
        base_minutes = len(execution_order) * 2  # 2 minutes per table
        conflict_minutes = len(conflicts) * 10  # 10 minutes per conflict

        critical_conflicts = [c for c in conflicts if c.risk_level == "critical"]
        critical_minutes = (
            len(critical_conflicts) * 30
        )  # 30 minutes for critical conflicts

        return base_minutes + conflict_minutes + critical_minutes

    def _create_rollback_plan(self, conflicts: List[MergeConflict]) -> Dict[str, Any]:
        """Create comprehensive rollback plan."""
        return {
            "backup_required": True,
            "critical_tables": [
                c.table_name for c in conflicts if c.risk_level == "critical"
            ],
            "rollback_order": "reverse_dependency_order",
            "verification_queries": self._generate_verification_queries(conflicts),
            "emergency_contacts": ["database_admin", "project_owner"],
            "estimated_rollback_time": len(conflicts) * 5,  # 5 minutes per conflict
        }

    def _generate_verification_queries(
        self, conflicts: List[MergeConflict]
    ) -> List[str]:
        """Generate SQL queries to verify merge success."""
        queries = []
        for conflict in conflicts:
            table = conflict.table_name
            queries.extend(
                [
                    f"SELECT COUNT(*) as total_rows FROM {table};",
                    f"SELECT COUNT(DISTINCT id) as unique_ids FROM {table} WHERE id IS NOT NULL;",
                ]
            )
        return queries

    async def save_analysis_report(self, output_path: str, strategy: MergeStrategy):
        """Save comprehensive analysis report."""
        report = {
            "analysis_timestamp": datetime.now().isoformat(),
            "source_project": strategy.source_project,
            "target_project": strategy.target_project,
            "summary": {
                "total_conflicts": len(strategy.conflicts),
                "critical_conflicts": len(
                    [c for c in strategy.conflicts if c.risk_level == "critical"]
                ),
                "safety_score": strategy.safety_score,
                "estimated_duration_minutes": strategy.estimated_duration,
            },
            "execution_plan": {
                "order": strategy.execution_order,
                "total_tables": len(strategy.execution_order),
            },
            "conflicts": [
                {
                    "table": c.table_name,
                    "type": c.conflict_type,
                    "risk_level": c.risk_level,
                    "source_rows": c.source_rows,
                    "target_rows": c.target_rows,
                    "resolution": c.resolution_strategy,
                    "affected_dependencies": c.affected_dependencies,
                    "details": c.details,
                }
                for c in strategy.conflicts
            ],
            "rollback_plan": strategy.rollback_plan,
        }

        # Save as both JSON and YAML
        with open(f"{output_path}_analysis.json", "w") as f:
            json.dump(report, f, indent=2)

        with open(f"{output_path}_analysis.yaml", "w") as f:
            yaml.dump(report, f, default_flow_style=False)

        self.logger.info(f"📊 Analysis report saved to {output_path}")

    def generate_merge_recommendations(self, strategy: MergeStrategy) -> Dict[str, Any]:
        """Generate actionable merge recommendations."""
        recommendations = {
            "immediate_actions": [],
            "pre_merge_steps": [],
            "merge_execution": [],
            "post_merge_verification": [],
            "risk_mitigation": [],
        }

        # Immediate actions based on safety score
        if strategy.safety_score < 0.3:
            recommendations["immediate_actions"].append(
                "🚨 HIGH RISK: Do not proceed without thorough review and testing"
            )
        elif strategy.safety_score < 0.7:
            recommendations["immediate_actions"].append(
                "⚠️ MEDIUM RISK: Proceed with caution and extra validation"
            )

        # Pre-merge steps
        recommendations["pre_merge_steps"].extend(
            [
                "1. Create full backup of target database",
                "2. Verify all connection strings and permissions",
                "3. Test merge strategy on staging environment first",
                "4. Notify all stakeholders of maintenance window",
            ]
        )

        # Handle critical shared dependency conflicts
        critical_shared_conflicts = [
            c
            for c in strategy.conflicts
            if c.conflict_type == "critical_shared_dependency"
        ]
        for conflict in critical_shared_conflicts:
            recommendations["risk_mitigation"].append(
                f"🎯 {conflict.table_name.upper()} TABLE: Critical shared dependency - {len(conflict.affected_dependencies)} dependent tables require careful merge strategy"
            )

        return recommendations


# CLI and utility functions
async def main():
    """Main function for standalone usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Project Dependency Analyzer")
    parser.add_argument(
        "--source-db", required=True, help="Source database connection string"
    )
    parser.add_argument(
        "--target-db", required=True, help="Target database connection string"
    )
    parser.add_argument("--source-name", default="source", help="Source project name")
    parser.add_argument("--target-name", default="target", help="Target project name")
    parser.add_argument("--output", default="merge_analysis", help="Output file prefix")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO if not args.verbose else logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    analyzer = DependencyAnalyzer()

    try:
        # Analyze both projects
        print(f"🔍 Analyzing source project: {args.source_name}")
        await analyzer.analyze_project(args.source_db, args.source_name)

        print(f"🔍 Analyzing target project: {args.target_name}")
        await analyzer.analyze_project(args.target_db, args.target_name)

        # Create merge strategy
        print(f"📋 Creating merge strategy...")
        strategy = await analyzer.create_merge_strategy(
            args.source_name, args.target_name
        )

        # Generate recommendations
        recommendations = analyzer.generate_merge_recommendations(strategy)

        # Save analysis
        await analyzer.save_analysis_report(args.output, strategy)

        # Print summary
        print(f"\n🎯 MERGE ANALYSIS SUMMARY")
        print(f"=" * 50)
        print(f"Safety Score: {strategy.safety_score:.2f}/1.00")
        print(f"Total Conflicts: {len(strategy.conflicts)}")
        print(
            f"Critical Conflicts: {len([c for c in strategy.conflicts if c.risk_level == 'critical'])}"
        )
        print(f"Estimated Duration: {strategy.estimated_duration} minutes")
        print(f"Execution Order: {len(strategy.execution_order)} tables")

        if strategy.safety_score < 0.5:
            print(f"\n⚠️ HIGH RISK MERGE - Manual review required!")
        else:
            print(f"\n✅ Merge strategy generated successfully")

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    asyncio.run(main())
