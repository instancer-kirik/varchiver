#!/usr/bin/env python3
"""
Integration Test Suite for Multi-Project Merge System

This test suite validates the complete multi-project merge workflow,
including dynamic table discovery, dependency analysis, and conflict
resolution strategies.

Usage:
    python test_multi_project_merge.py
    python test_multi_project_merge.py --verbose
    python test_multi_project_merge.py --test-category dependency_analysis
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

# Add varchiver to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from varchiver.supamerge.dependency_analyzer import (
        DependencyAnalyzer,
        TableMetadata,
        TableDependency,
        MergeConflict,
        MergeStrategy,
    )
    from varchiver.supamerge.shared_dependency_resolver import (
        SharedDependencyResolver,
        SharedDependencyConflict,
        ResolutionStrategy,
        DependencyChain,
    )
    from multi_project_merge_workflow import MultiProjectMergeWorkflow
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(
        "Ensure you're in the varchiver directory and have all dependencies installed"
    )
    sys.exit(1)


class TestDependencyAnalyzer(unittest.IsolatedAsyncioTestCase):
    """Test the dependency analysis system."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.analyzer = DependencyAnalyzer()

        # Mock database connections
        self.mock_cursor = Mock()
        self.mock_connection = Mock()
        self.mock_connection.cursor.return_value = self.mock_cursor

    async def test_table_metadata_creation(self):
        """Test creation of table metadata objects."""
        metadata = TableMetadata(
            name="test_table",
            schema="public",
            row_count=42,
            columns=[{"name": "id", "type": "uuid", "nullable": False}],
            primary_keys=["id"],
            has_data=True,
            project_source="test_project",
        )

        self.assertEqual(metadata.name, "test_table")
        self.assertEqual(metadata.row_count, 42)
        self.assertTrue(metadata.has_data)
        self.assertEqual(len(metadata.columns), 1)

    async def test_dependency_detection(self):
        """Test foreign key dependency detection."""
        dependency = TableDependency(
            source_table="orders",
            source_column="customer_id",
            target_table="customers",
            target_column="id",
            constraint_name="fk_orders_customer",
            is_nullable=False,
        )

        self.assertEqual(dependency.source_table, "orders")
        self.assertEqual(dependency.target_table, "customers")
        self.assertFalse(dependency.is_nullable)

    async def test_conflict_risk_assessment(self):
        """Test conflict risk level calculation."""
        # Mock table metadata with dependencies
        source_metadata = {
            "projects": TableMetadata(
                name="projects",
                schema="public",
                row_count=5,
                has_data=True,
                project_source="source",
            )
        }

        target_metadata = {
            "projects": TableMetadata(
                name="projects",
                schema="public",
                row_count=10,
                has_data=True,
                project_source="target",
            )
        }

        # Test conflict analysis (mocked since it requires DB connection)
        conflict = await self.analyzer._analyze_table_conflict(
            "projects",
            source_metadata["projects"],
            target_metadata["projects"],
            source_metadata,
            target_metadata,
        )

        self.assertIsNotNone(conflict)
        self.assertEqual(conflict.table_name, "projects")
        self.assertEqual(conflict.source_rows, 5)
        self.assertEqual(conflict.target_rows, 10)

    @patch("psycopg2.connect")
    async def test_project_analysis_mock(self, mock_connect):
        """Test project analysis with mocked database."""
        # Setup mock database responses
        mock_connect.return_value = self.mock_connection

        # Mock table discovery
        self.mock_cursor.execute.return_value = None
        self.mock_cursor.fetchall.side_effect = [
            [("projects",), ("users",), ("posts",)],  # Table list
            [
                ("id", "uuid", "NO", None),
                ("name", "text", "YES", None),
            ],  # Columns for projects
            [("id",)],  # Primary keys for projects
            [
                ("id", "uuid", "NO", None),
                ("email", "text", "NO", None),
            ],  # Columns for users
            [("id",)],  # Primary keys for users
            [
                ("id", "uuid", "NO", None),
                ("title", "text", "NO", None),
            ],  # Columns for posts
            [("id",)],  # Primary keys for posts
            [],  # Foreign key relationships
        ]
        self.mock_cursor.fetchone.side_effect = [10, 5, 20]  # Row counts

        # Run analysis
        result = await self.analyzer.analyze_project(
            "postgresql://test", "test_project"
        )

        self.assertIsInstance(result, dict)
        self.assertIn("projects", result)
        self.assertIn("users", result)
        self.assertIn("posts", result)

        # Verify metadata structure
        projects_meta = result["projects"]
        self.assertEqual(projects_meta.name, "projects")
        self.assertEqual(projects_meta.row_count, 10)


class TestSharedDependencyResolver(unittest.IsolatedAsyncioTestCase):
    """Test the shared dependency resolution system."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.resolver = SharedDependencyResolver()

    def test_default_strategies_loaded(self):
        """Test that default resolution strategies are loaded."""
        strategies = self.resolver.resolution_strategies

        self.assertIn("union_merge", strategies)
        self.assertIn("source_priority", strategies)
        self.assertIn("target_priority", strategies)
        self.assertIn("namespace_separation", strategies)
        self.assertIn("manual_review", strategies)

        # Test strategy properties
        union_strategy = strategies["union_merge"]
        self.assertEqual(union_strategy.name, "Union Merge with ID Remapping")
        self.assertEqual(union_strategy.risk_level, "medium")
        self.assertTrue(union_strategy.requires_manual_approval)

    async def test_dependency_chain_building(self):
        """Test dependency chain construction."""
        # Mock dependencies
        dependencies = {
            "table_a": ["projects"],
            "table_b": ["projects", "users"],
            "table_c": ["table_a"],
        }

        chain = await self.resolver._build_dependency_chain("projects", dependencies)

        self.assertEqual(chain.root_table, "projects")
        self.assertIn("table_a", chain.dependent_tables)
        self.assertIn("table_b", chain.dependent_tables)

    async def test_impact_analysis(self):
        """Test impact analysis calculation."""
        source_metadata = {"row_count": 100, "has_data": True}
        target_metadata = {"row_count": 200, "has_data": True}

        dependency_chain = DependencyChain(
            root_table="critical_table",
            dependent_tables=["dep1", "dep2", "dep3"],
            chain_depth=2,
            total_rows_affected=300,
            critical_path=True,
        )

        impact = await self.resolver._analyze_impact(
            "critical_table", source_metadata, target_metadata, dependency_chain
        )

        self.assertIn("impact_score", impact)
        self.assertIn("risk_category", impact)
        self.assertIn("affected_table_count", impact)
        self.assertEqual(impact["affected_table_count"], 3)
        self.assertEqual(impact["estimated_affected_rows"], 300)

    def test_strategy_recommendation(self):
        """Test strategy recommendation logic."""
        # Test no source data scenario
        available_strategies = list(self.resolver.resolution_strategies.values())
        impact_analysis = {
            "risk_category": "medium",
            "data_overlap_type": "no_source_data",
        }

        recommended = self.resolver._recommend_strategy(
            available_strategies, impact_analysis
        )
        self.assertEqual(recommended, "target_priority")

        # Test critical risk scenario
        impact_analysis = {
            "risk_category": "critical",
            "data_overlap_type": "different_datasets",
        }
        recommended = self.resolver._recommend_strategy(
            available_strategies, impact_analysis
        )
        self.assertEqual(recommended, "manual_review")

    async def test_strategy_execution_dry_run(self):
        """Test strategy execution in dry run mode."""
        # Create mock conflict
        conflict = SharedDependencyConflict(
            table_name="test_table",
            source_rows=10,
            target_rows=15,
            dependency_chain=DependencyChain(root_table="test_table"),
            available_strategies=[self.resolver.resolution_strategies["union_merge"]],
            recommended_strategy="union_merge",
        )

        result = await self.resolver.execute_resolution_strategy(
            conflict, "union_merge", "source_db_url", "target_db_url", dry_run=True
        )

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["strategy_id"], "union_merge")
        self.assertIn("steps_completed", result)

    async def test_conflict_summary_generation(self):
        """Test conflict summary generation."""
        conflicts = [
            SharedDependencyConflict(
                table_name="table1",
                source_rows=10,
                target_rows=20,
                dependency_chain=DependencyChain(root_table="table1"),
                impact_analysis={"risk_category": "high", "impact_score": 75},
            ),
            SharedDependencyConflict(
                table_name="table2",
                source_rows=5,
                target_rows=8,
                dependency_chain=DependencyChain(root_table="table2"),
                impact_analysis={"risk_category": "medium", "impact_score": 35},
            ),
        ]

        summary = await self.resolver.generate_conflict_summary(conflicts)

        self.assertEqual(summary["total_conflicts"], 2)
        self.assertEqual(summary["risk_distribution"]["high"], 1)
        self.assertEqual(summary["risk_distribution"]["medium"], 1)
        self.assertEqual(summary["highest_impact_table"], "table1")


class TestMultiProjectMergeWorkflow(unittest.IsolatedAsyncioTestCase):
    """Test the complete workflow orchestrator."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.workflow = MultiProjectMergeWorkflow(verbose=False)

    def test_workflow_initialization(self):
        """Test workflow initialization."""
        self.assertIsNotNone(self.workflow.dependency_analyzer)
        self.assertIsNotNone(self.workflow.shared_resolver)
        self.assertIsNotNone(self.workflow.logger)

    async def test_recommendation_generation(self):
        """Test recommendation generation."""
        # Mock merge strategy
        mock_strategy = Mock()
        mock_strategy.safety_score = 0.4
        mock_strategy.estimated_duration = 90

        conflict_summary = {"manual_resolution_required": 2, "total_conflicts": 5}

        shared_conflicts = [
            Mock(
                impact_analysis={"risk_category": "critical"},
                dependency_chain=Mock(dependent_tables=["dep1", "dep2"]),
                table_name="critical_table",
            )
        ]

        recommendations = self.workflow._generate_recommendations(
            mock_strategy, conflict_summary, shared_conflicts
        )

        self.assertIn("immediate_actions", recommendations)
        self.assertIn("pre_merge_preparation", recommendations)
        self.assertIn("risk_mitigation", recommendations)

        # Should have high risk warning due to low safety score
        immediate_actions = " ".join(recommendations["immediate_actions"])
        self.assertIn("HIGH RISK", immediate_actions)

    async def test_safety_assessment(self):
        """Test safety assessment logic."""
        # Mock merge strategy with low safety score
        mock_strategy = Mock()
        mock_strategy.safety_score = 0.25

        shared_conflicts = [
            Mock(
                impact_analysis={"risk_category": "critical"},
                dependency_chain=Mock(has_circular_deps=True),
            )
        ]

        assessment = self.workflow._assess_safety(mock_strategy, shared_conflicts)

        self.assertEqual(assessment["overall_risk_level"], "critical")
        self.assertFalse(assessment["can_proceed_automatically"])
        self.assertEqual(assessment["recommendation"], "DO_NOT_PROCEED")
        self.assertGreater(len(assessment["critical_issues"]), 0)

    @patch("builtins.open", create=True)
    async def test_summary_report_generation(self, mock_open):
        """Test summary report generation."""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        analysis = {
            "analysis_metadata": {
                "timestamp": "2024-01-01T00:00:00",
                "source_profile": "dev",
                "target_profile": "prod",
                "duration_seconds": 45.5,
            },
            "safety_assessment": {
                "overall_risk_level": "medium",
                "safety_score": 0.65,
                "can_proceed_automatically": True,
                "recommendation": "PROCEED_WITH_CAUTION",
                "critical_issues": [],
                "warnings": ["Some warning"],
            },
            "project_discovery": {
                "source": {
                    "total_tables": 48,
                    "tables_with_data": 25,
                    "total_rows": 95,
                },
                "target": {
                    "total_tables": 114,
                    "tables_with_data": 78,
                    "total_rows": 300,
                },
            },
            "merge_strategy": {
                "estimated_duration_minutes": 45,
                "total_conflicts": 3,
                "execution_order": ["table1", "table2", "table3"],
            },
            "conflict_summary": {
                "risk_distribution": {"high": 1, "medium": 2},
                "manual_resolution_required": 1,
            },
            "recommendations": {
                "immediate_actions": ["Review critical conflicts"],
                "pre_merge_preparation": ["Create backups"],
            },
        }

        await self.workflow._generate_summary_report("test_summary.md", analysis)

        # Verify file was written
        mock_file.write.assert_called()

        # Check that key information was included
        written_content = "".join(
            [call[0][0] for call in mock_file.write.call_args_list]
        )
        self.assertIn("Multi-Project Merge Analysis Summary", written_content)
        self.assertIn("Safety Score: 0.65", written_content)
        self.assertIn("Source Project: dev", written_content)
        self.assertIn("Target Project: prod", written_content)


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for the complete system."""

    async def asyncSetUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []

    async def asyncTearDown(self):
        """Clean up test files."""
        import shutil

        for file_path in self.test_files:
            try:
                os.unlink(file_path)
            except:
                pass
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass

    async def test_end_to_end_workflow_components(self):
        """Test that all components work together."""
        # Test component initialization
        analyzer = DependencyAnalyzer()
        resolver = SharedDependencyResolver()
        workflow = MultiProjectMergeWorkflow()

        # Verify they can work together
        self.assertIsNotNone(analyzer)
        self.assertIsNotNone(resolver)
        self.assertIsNotNone(workflow)

        # Test strategy availability
        strategies = resolver.resolution_strategies
        self.assertGreater(len(strategies), 0)

        # Test workflow has access to components
        self.assertIsNotNone(workflow.dependency_analyzer)
        self.assertIsNotNone(workflow.shared_resolver)

    async def test_configuration_validation(self):
        """Test configuration file handling."""
        # Create test configuration
        test_config = {
            "analysis_metadata": {
                "source_profile": "test_source",
                "target_profile": "test_target",
            },
            "merge_strategy": {
                "safety_score": 0.75,
                "execution_order": ["table1", "table2"],
            },
            "shared_conflicts": [],
        }

        # Save as JSON
        config_file = os.path.join(self.temp_dir, "test_config.json")
        with open(config_file, "w") as f:
            json.dump(test_config, f)

        self.test_files.append(config_file)

        # Test loading
        workflow = MultiProjectMergeWorkflow()
        loaded_config = await workflow._load_strategy_file(config_file)

        self.assertEqual(
            loaded_config["analysis_metadata"]["source_profile"], "test_source"
        )
        self.assertEqual(loaded_config["merge_strategy"]["safety_score"], 0.75)

    async def test_error_handling(self):
        """Test error handling in various scenarios."""
        workflow = MultiProjectMergeWorkflow()

        # Test invalid strategy file
        with self.assertRaises(FileNotFoundError):
            await workflow._load_strategy_file("nonexistent_file.json")

        # Test analyzer error handling
        analyzer = DependencyAnalyzer()
        with self.assertRaises(Exception):
            await analyzer.analyze_project("invalid://connection", "test")


def run_specific_test_category(category):
    """Run tests for a specific category."""
    if category == "dependency_analysis":
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDependencyAnalyzer)
    elif category == "conflict_resolution":
        suite = unittest.TestLoader().loadTestsFromTestCase(
            TestSharedDependencyResolver
        )
    elif category == "workflow":
        suite = unittest.TestLoader().loadTestsFromTestCase(
            TestMultiProjectMergeWorkflow
        )
    elif category == "integration":
        suite = unittest.TestLoader().loadTestsFromTestCase(TestIntegration)
    else:
        print(f"Unknown test category: {category}")
        return False

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


def main():
    """Main test runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Project Merge Test Suite")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--test-category",
        help="Run specific test category",
        choices=[
            "dependency_analysis",
            "conflict_resolution",
            "workflow",
            "integration",
        ],
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    print("🧪 Multi-Project Merge Test Suite")
    print("=" * 50)

    success = True

    if args.test_category:
        print(f"Running {args.test_category} tests...")
        success = run_specific_test_category(args.test_category)
    else:
        print("Running all tests...")

        # Discover and run all tests
        loader = unittest.TestLoader()
        suite = loader.discover(".", pattern="test_multi_project_merge.py")

        runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
        result = runner.run(suite)
        success = result.wasSuccessful()

    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
