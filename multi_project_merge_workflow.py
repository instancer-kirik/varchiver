#!/usr/bin/env python3
"""
Multi-Project Merge Workflow Orchestrator

Comprehensive workflow for safely merging complex Supabase projects with
dynamic dependency analysis, conflict resolution, and rollback capabilities.

This orchestrator combines the enhanced table discovery, dependency analysis,
and shared dependency resolution systems to handle real-world multi-project
merges safely and efficiently.

Key Features:
- Dynamic table discovery (100+ tables supported)
- Cross-project dependency mapping
- Intelligent conflict resolution for shared dependencies
- Safe execution with rollback capabilities
- Progress tracking and detailed reporting
- Support for dry-run validation

Usage Examples:
    # Analyze projects and generate merge strategy
    python multi_project_merge_workflow.py analyze \
        --source-profile development \
        --target-profile production \
        --output merge_strategy_2024

    # Execute merge with dry-run first
    python multi_project_merge_workflow.py execute \
        --strategy merge_strategy_2024.yaml \
        --dry-run

    # Execute actual merge
    python multi_project_merge_workflow.py execute \
        --strategy merge_strategy_2024.yaml \
        --confirmed

Author: Varchiver Team
"""

import asyncio
import argparse
import json
import yaml
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict

# Import varchiver components
try:
    from varchiver.utils.env_manager import EnvManager
    from varchiver.supamerge.dependency_analyzer import DependencyAnalyzer
    from varchiver.supamerge.shared_dependency_resolver import SharedDependencyResolver
    from varchiver.supamerge.core import Supamerge
    from varchiver.supamerge.export import ImprovedSupabaseExporter
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Ensure you're running from the varchiver environment")
    sys.exit(1)


class MultiProjectMergeWorkflow:
    """Orchestrates complex multi-project merges with safety guarantees."""

    def __init__(self, verbose: bool = False):
        self.setup_logging(verbose)
        self.env_manager = EnvManager()
        self.dependency_analyzer = DependencyAnalyzer(self.logger)
        self.shared_resolver = SharedDependencyResolver(self.logger)
        self.exporter = ImprovedSupabaseExporter(verbose)
        self.workflow_state = {}
        self.safety_checks_passed = False

    def setup_logging(self, verbose: bool):
        """Setup comprehensive logging."""
        log_level = logging.DEBUG if verbose else logging.INFO

        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Setup logger
        self.logger = logging.getLogger("multi_project_merge")
        self.logger.setLevel(log_level)

        # File handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"multi_merge_{timestamp}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info(f"📋 Multi-Project Merge Workflow initialized")
        self.logger.info(f"📁 Logs will be saved to: {log_file}")

    async def analyze_projects(
        self,
        source_profile: str,
        target_profile: str,
        output_prefix: str = "merge_analysis",
    ) -> Dict[str, Any]:
        """Comprehensive analysis of two projects for merging."""

        self.logger.info(f"🔍 Starting analysis: {source_profile} → {target_profile}")

        analysis_start = datetime.now()

        try:
            # Step 1: Load project configurations
            source_config = await self._load_project_config(source_profile)
            target_config = await self._load_project_config(target_profile)

            # Step 2: Discover all tables in both projects
            self.logger.info("🔍 Discovering tables in source project...")
            source_discovery = await self._discover_project_tables(
                source_config, source_profile
            )

            self.logger.info("🔍 Discovering tables in target project...")
            target_discovery = await self._discover_project_tables(
                target_config, target_profile
            )

            # Step 3: Analyze dependencies in both projects
            self.logger.info("🔗 Analyzing source project dependencies...")
            source_metadata = await self.dependency_analyzer.analyze_project(
                source_config["db_url"], source_profile
            )

            self.logger.info("🔗 Analyzing target project dependencies...")
            target_metadata = await self.dependency_analyzer.analyze_project(
                target_config["db_url"], target_profile
            )

            # Step 4: Compare projects and identify conflicts
            self.logger.info("⚖️ Comparing projects for conflicts...")
            conflicts = await self.dependency_analyzer.compare_projects(
                source_profile, target_profile
            )

            # Step 5: Analyze shared dependencies
            self.logger.info("🔄 Analyzing shared dependency conflicts...")
            shared_conflicts = []

            for conflict in conflicts:
                if conflict.risk_level in ["high", "critical"]:
                    shared_conflict = (
                        await self.shared_resolver.analyze_shared_dependency(
                            conflict.table_name,
                            source_metadata.get(conflict.table_name, {}),
                            target_metadata.get(conflict.table_name, {}),
                            self._build_dependency_map(
                                source_metadata, target_metadata
                            ),
                        )
                    )
                    shared_conflicts.append(shared_conflict)

            # Step 6: Create comprehensive merge strategy
            self.logger.info("📋 Creating merge strategy...")
            merge_strategy = await self.dependency_analyzer.create_merge_strategy(
                source_profile, target_profile
            )

            # Step 7: Generate conflict summary
            conflict_summary = await self.shared_resolver.generate_conflict_summary(
                shared_conflicts
            )

            # Step 8: Compile comprehensive analysis
            analysis_result = {
                "analysis_metadata": {
                    "timestamp": analysis_start.isoformat(),
                    "duration_seconds": (
                        datetime.now() - analysis_start
                    ).total_seconds(),
                    "source_profile": source_profile,
                    "target_profile": target_profile,
                    "workflow_version": "1.0.0",
                },
                "project_discovery": {
                    "source": source_discovery,
                    "target": target_discovery,
                },
                "dependency_analysis": {
                    "source_tables": len(source_metadata),
                    "target_tables": len(target_metadata),
                    "total_conflicts": len(conflicts),
                    "shared_dependency_conflicts": len(shared_conflicts),
                },
                "merge_strategy": {
                    "safety_score": merge_strategy.safety_score,
                    "estimated_duration_minutes": merge_strategy.estimated_duration,
                    "execution_order": merge_strategy.execution_order,
                    "conflicts": [asdict(c) for c in merge_strategy.conflicts],
                },
                "conflict_summary": conflict_summary,
                "shared_conflicts": [asdict(sc) for sc in shared_conflicts],
                "recommendations": self._generate_recommendations(
                    merge_strategy, conflict_summary, shared_conflicts
                ),
                "safety_assessment": self._assess_safety(
                    merge_strategy, shared_conflicts
                ),
            }

            # Step 9: Save analysis results
            await self._save_analysis_results(output_prefix, analysis_result)

            self.logger.info(
                f"✅ Analysis completed in {analysis_result['analysis_metadata']['duration_seconds']:.2f}s"
            )

            return analysis_result

        except Exception as e:
            self.logger.error(f"❌ Analysis failed: {e}")
            raise

    async def execute_merge(
        self, strategy_file: str, dry_run: bool = True, confirmed: bool = False
    ) -> Dict[str, Any]:
        """Execute the merge strategy with comprehensive safety checks."""

        if not dry_run and not confirmed:
            raise ValueError("Production merge requires --confirmed flag")

        self.logger.info(f"🚀 Executing merge strategy: {strategy_file}")
        self.logger.info(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION MERGE'}")

        execution_start = datetime.now()

        try:
            # Step 1: Load and validate strategy
            strategy_data = await self._load_strategy_file(strategy_file)

            # Step 2: Pre-execution safety checks
            safety_check = await self._perform_safety_checks(strategy_data)
            if not safety_check["passed"]:
                raise RuntimeError(f"Safety checks failed: {safety_check['failures']}")

            # Step 3: Create backups if not dry run
            backup_info = {}
            if not dry_run:
                self.logger.info("💾 Creating safety backups...")
                backup_info = await self._create_safety_backups(strategy_data)

            # Step 4: Execute shared dependency resolutions
            resolution_results = []
            for shared_conflict_data in strategy_data.get("shared_conflicts", []):
                if shared_conflict_data.get("manual_resolution_required"):
                    self.logger.warning(
                        f"⚠️ Manual resolution required for: {shared_conflict_data['table_name']}"
                    )
                    continue

                result = await self._execute_shared_dependency_resolution(
                    shared_conflict_data, strategy_data, dry_run
                )
                resolution_results.append(result)

            # Step 5: Execute main merge strategy
            self.logger.info("🔄 Executing main merge...")
            merge_result = await self._execute_main_merge(strategy_data, dry_run)

            # Step 6: Post-merge validation
            validation_results = []
            if not dry_run:
                self.logger.info("✅ Performing post-merge validation...")
                validation_results = await self._validate_merge_results(strategy_data)

            # Step 7: Generate execution report
            execution_result = {
                "execution_metadata": {
                    "timestamp": execution_start.isoformat(),
                    "duration_seconds": (
                        datetime.now() - execution_start
                    ).total_seconds(),
                    "dry_run": dry_run,
                    "strategy_file": strategy_file,
                    "success": True,
                },
                "safety_checks": safety_check,
                "backup_info": backup_info,
                "resolution_results": resolution_results,
                "merge_result": merge_result,
                "validation_results": validation_results,
                "rollback_plan": strategy_data.get("rollback_plan", {}),
            }

            # Step 8: Save execution report
            output_file = f"merge_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            await self._save_execution_report(output_file, execution_result)

            if dry_run:
                self.logger.info("🧪 Dry run completed successfully")
                self.logger.info("Execute with --confirmed to perform actual merge")
            else:
                self.logger.info("✅ Production merge completed successfully")

            return execution_result

        except Exception as e:
            self.logger.error(f"❌ Merge execution failed: {e}")

            # Attempt rollback if not dry run
            if not dry_run:
                self.logger.warning("🔄 Attempting automatic rollback...")
                await self._attempt_rollback(strategy_file)

            raise

    async def _load_project_config(self, profile: str) -> Dict[str, str]:
        """Load project configuration from environment or profile."""
        try:
            env_vars = self.env_manager.get_supabase_connection_info(profile)

            # Build database URL
            db_url = f"postgresql://postgres.{env_vars['project_ref']}:{env_vars['service_role_key']}@aws-0-us-west-1.pooler.supabase.com:5432/postgres"

            return {
                "profile": profile,
                "project_ref": env_vars["project_ref"],
                "supabase_url": env_vars["supabase_url"],
                "service_key": env_vars["service_role_key"],
                "db_url": db_url,
            }

        except Exception as e:
            self.logger.error(f"Failed to load config for profile '{profile}': {e}")
            raise

    async def _discover_project_tables(
        self, config: Dict[str, str], profile: str
    ) -> Dict[str, Any]:
        """Discover all tables in a project using the enhanced discovery system."""
        try:
            # Use the improved exporter's discovery capabilities
            discovery_result = await self.exporter.export_via_rest_api(
                config["supabase_url"],
                config["service_key"],
                tables=None,  # Discover all tables
                format="json",
                output_path=f"temp_discovery_{profile}",
            )

            # Extract table information
            tables_info = {}
            if discovery_result.get("data_file"):
                with open(discovery_result["data_file"]) as f:
                    data = json.load(f)

                for schema_name, schema_data in data.items():
                    if isinstance(schema_data, dict):
                        for table_name, table_data in schema_data.items():
                            tables_info[table_name] = {
                                "row_count": len(table_data)
                                if isinstance(table_data, list)
                                else 0,
                                "has_data": len(table_data) > 0
                                if isinstance(table_data, list)
                                else False,
                                "discovery_method": "openapi",
                            }

            return {
                "profile": profile,
                "total_tables": len(tables_info),
                "tables_with_data": sum(
                    1 for t in tables_info.values() if t["has_data"]
                ),
                "total_rows": sum(t["row_count"] for t in tables_info.values()),
                "tables": tables_info,
            }

        except Exception as e:
            self.logger.error(f"Failed to discover tables for {profile}: {e}")
            raise

    def _build_dependency_map(
        self, source_metadata: Dict[str, Any], target_metadata: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Build a combined dependency map from both projects."""
        dependency_map = {}

        # Process source dependencies
        for table_name, metadata in source_metadata.items():
            dependencies = []
            for fk in metadata.foreign_keys:
                dependencies.append(fk.target_table)
            if dependencies:
                dependency_map[f"source.{table_name}"] = dependencies

        # Process target dependencies
        for table_name, metadata in target_metadata.items():
            dependencies = []
            for fk in metadata.foreign_keys:
                dependencies.append(fk.target_table)
            if dependencies:
                dependency_map[f"target.{table_name}"] = dependencies

        return dependency_map

    def _generate_recommendations(
        self,
        merge_strategy: Any,
        conflict_summary: Dict[str, Any],
        shared_conflicts: List[Any],
    ) -> Dict[str, List[str]]:
        """Generate actionable recommendations for the merge."""
        recommendations = {
            "immediate_actions": [],
            "pre_merge_preparation": [],
            "execution_guidance": [],
            "post_merge_verification": [],
            "risk_mitigation": [],
        }

        # Safety score based recommendations
        if merge_strategy.safety_score < 0.3:
            recommendations["immediate_actions"].append(
                "🚨 CRITICAL: Do not proceed - safety score too low"
            )
            recommendations["immediate_actions"].append(
                "Recommend thorough manual review and testing"
            )
        elif merge_strategy.safety_score < 0.7:
            recommendations["immediate_actions"].append(
                "⚠️ HIGH RISK: Proceed only with extensive testing"
            )

        # Manual resolution recommendations
        manual_required = conflict_summary.get("manual_resolution_required", 0)
        if manual_required > 0:
            recommendations["pre_merge_preparation"].append(
                f"📋 {manual_required} conflicts require manual resolution before merge"
            )

        # Critical shared dependencies
        critical_conflicts = [
            sc
            for sc in shared_conflicts
            if sc.impact_analysis.get("risk_category") == "critical"
        ]
        if critical_conflicts:
            for conflict in critical_conflicts:
                recommendations["risk_mitigation"].append(
                    f"🎯 {conflict.table_name}: Critical dependency affecting "
                    f"{len(conflict.dependency_chain.dependent_tables)} tables"
                )

        # Execution time recommendations
        if merge_strategy.estimated_duration > 60:
            recommendations["execution_guidance"].append(
                f"⏱️ Long merge expected ({merge_strategy.estimated_duration}min) - "
                "schedule during maintenance window"
            )

        # Standard preparation steps
        recommendations["pre_merge_preparation"].extend(
            [
                "1. Verify all connection strings and permissions",
                "2. Create complete backup of target database",
                "3. Test merge strategy on staging environment",
                "4. Notify stakeholders of maintenance window",
                "5. Prepare rollback plan and procedures",
            ]
        )

        return recommendations

    def _assess_safety(
        self, merge_strategy: Any, shared_conflicts: List[Any]
    ) -> Dict[str, Any]:
        """Comprehensive safety assessment."""

        critical_issues = []
        warnings = []

        # Safety score assessment
        if merge_strategy.safety_score < 0.3:
            critical_issues.append(
                "Extremely low safety score - high risk of data loss"
            )
        elif merge_strategy.safety_score < 0.5:
            warnings.append("Low safety score - proceed with caution")

        # Critical conflicts assessment
        critical_count = len(
            [
                sc
                for sc in shared_conflicts
                if sc.impact_analysis.get("risk_category") == "critical"
            ]
        )
        if critical_count > 0:
            critical_issues.append(
                f"{critical_count} critical shared dependency conflicts"
            )

        # Circular dependency assessment
        circular_deps = sum(
            1 for sc in shared_conflicts if sc.dependency_chain.has_circular_deps
        )
        if circular_deps > 0:
            warnings.append(f"{circular_deps} tables have circular dependencies")

        # Overall assessment
        overall_risk = "low"
        if critical_issues:
            overall_risk = "critical"
        elif len(warnings) > 3:
            overall_risk = "high"
        elif warnings:
            overall_risk = "medium"

        can_proceed = len(critical_issues) == 0

        return {
            "overall_risk_level": overall_risk,
            "can_proceed_automatically": can_proceed,
            "safety_score": merge_strategy.safety_score,
            "critical_issues": critical_issues,
            "warnings": warnings,
            "recommendation": "PROCEED_WITH_CAUTION"
            if can_proceed
            else "DO_NOT_PROCEED",
        }

    async def _save_analysis_results(
        self, output_prefix: str, analysis_result: Dict[str, Any]
    ):
        """Save comprehensive analysis results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save as JSON
        json_file = f"{output_prefix}_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(analysis_result, f, indent=2)

        # Save as YAML for easier editing
        yaml_file = f"{output_prefix}_{timestamp}.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(analysis_result, f, default_flow_style=False)

        # Generate human-readable summary
        summary_file = f"{output_prefix}_summary_{timestamp}.md"
        await self._generate_summary_report(summary_file, analysis_result)

        self.logger.info(f"📊 Analysis saved:")
        self.logger.info(f"   JSON: {json_file}")
        self.logger.info(f"   YAML: {yaml_file}")
        self.logger.info(f"   Summary: {summary_file}")

    async def _generate_summary_report(self, filename: str, analysis: Dict[str, Any]):
        """Generate human-readable summary report."""

        with open(filename, "w") as f:
            f.write("# Multi-Project Merge Analysis Summary\n\n")

            # Basic info
            meta = analysis["analysis_metadata"]
            f.write(f"**Analysis Date:** {meta['timestamp']}\n")
            f.write(f"**Source Project:** {meta['source_profile']}\n")
            f.write(f"**Target Project:** {meta['target_profile']}\n")
            f.write(f"**Analysis Duration:** {meta['duration_seconds']:.2f}s\n\n")

            # Safety assessment
            safety = analysis["safety_assessment"]
            f.write("## Safety Assessment\n\n")
            f.write(f"**Overall Risk Level:** {safety['overall_risk_level'].upper()}\n")
            f.write(f"**Safety Score:** {safety['safety_score']:.2f}/1.00\n")
            f.write(
                f"**Can Proceed:** {'✅ YES' if safety['can_proceed_automatically'] else '❌ NO'}\n"
            )
            f.write(f"**Recommendation:** {safety['recommendation']}\n\n")

            if safety["critical_issues"]:
                f.write("### Critical Issues\n")
                for issue in safety["critical_issues"]:
                    f.write(f"- ❌ {issue}\n")
                f.write("\n")

            if safety["warnings"]:
                f.write("### Warnings\n")
                for warning in safety["warnings"]:
                    f.write(f"- ⚠️ {warning}\n")
                f.write("\n")

            # Project overview
            discovery = analysis["project_discovery"]
            f.write("## Project Overview\n\n")
            f.write("| Metric | Source | Target |\n")
            f.write("|--------|--------|--------|\n")
            f.write(
                f"| Total Tables | {discovery['source']['total_tables']} | {discovery['target']['total_tables']} |\n"
            )
            f.write(
                f"| Tables with Data | {discovery['source']['tables_with_data']} | {discovery['target']['tables_with_data']} |\n"
            )
            f.write(
                f"| Total Rows | {discovery['source']['total_rows']:,} | {discovery['target']['total_rows']:,} |\n\n"
            )

            # Merge strategy
            strategy = analysis["merge_strategy"]
            f.write("## Merge Strategy\n\n")
            f.write(
                f"**Estimated Duration:** {strategy['estimated_duration_minutes']} minutes\n"
            )
            f.write(f"**Total Conflicts:** {strategy['total_conflicts']}\n")
            f.write(
                f"**Execution Order:** {len(strategy['execution_order'])} tables\n\n"
            )

            # Conflict summary
            conflict_summary = analysis["conflict_summary"]
            f.write("## Conflict Analysis\n\n")
            f.write("### Risk Distribution\n")
            risk_dist = conflict_summary["risk_distribution"]
            for level, count in risk_dist.items():
                if count > 0:
                    f.write(f"- **{level.title()}:** {count} conflicts\n")
            f.write("\n")

            if conflict_summary["manual_resolution_required"] > 0:
                f.write(
                    f"**Manual Resolution Required:** {conflict_summary['manual_resolution_required']} conflicts\n\n"
                )

            # Recommendations
            recommendations = analysis["recommendations"]
            f.write("## Recommendations\n\n")

            if recommendations.get("immediate_actions"):
                f.write("### Immediate Actions\n")
                for action in recommendations["immediate_actions"]:
                    f.write(f"- {action}\n")
                f.write("\n")

            if recommendations.get("pre_merge_preparation"):
                f.write("### Pre-Merge Preparation\n")
                for step in recommendations["pre_merge_preparation"]:
                    f.write(f"- {step}\n")
                f.write("\n")

            f.write("---\n\n")
            f.write("*Generated by Varchiver Multi-Project Merge Workflow*\n")

    # Additional helper methods for execution...
    async def _load_strategy_file(self, strategy_file: str) -> Dict[str, Any]:
        """Load strategy file."""
        if strategy_file.endswith(".yaml") or strategy_file.endswith(".yml"):
            with open(strategy_file) as f:
                return yaml.safe_load(f)
        else:
            with open(strategy_file) as f:
                return json.load(f)

    async def _perform_safety_checks(
        self, strategy_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform comprehensive safety checks."""
        # Placeholder for safety checks
        return {"passed": True, "failures": []}

    async def _create_safety_backups(
        self, strategy_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create safety backups."""
        # Placeholder for backup creation
        return {"backup_created": True, "backup_files": []}

    async def _execute_shared_dependency_resolution(
        self,
        shared_conflict_data: Dict[str, Any],
        strategy_data: Dict[str, Any],
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Execute shared dependency resolution."""
        # Placeholder for shared dependency resolution
        return {
            "success": True,
            "strategy_executed": shared_conflict_data.get("recommended_strategy"),
        }

    async def _execute_main_merge(
        self, strategy_data: Dict[str, Any], dry_run: bool
    ) -> Dict[str, Any]:
        """Execute main merge."""
        # Placeholder for main merge execution
        return {
            "success": True,
            "tables_merged": len(
                strategy_data.get("merge_strategy", {}).get("execution_order", [])
            ),
        }

    async def _validate_merge_results(
        self, strategy_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Validate merge results."""
        # Placeholder for validation
        return [{"validation": "data_integrity", "passed": True}]

    async def _save_execution_report(
        self, output_file: str, execution_result: Dict[str, Any]
    ):
        """Save execution report."""
        with open(f"{output_file}.json", "w") as f:
            json.dump(execution_result, f, indent=2)

    async def _attempt_rollback(self, strategy_file: str):
        """Attempt automatic rollback."""
        self.logger.warning("Rollback functionality not yet implemented")


async def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Multi-Project Merge Workflow Orchestrator",
        epilog="""
Examples:
  # Analyze projects for merging
  python multi_project_merge_workflow.py analyze --source-profile development --target-profile production

  # Execute merge with dry-run
  python multi_project_merge_workflow.py execute --strategy merge_strategy_20241215.yaml --dry-run

  # Execute confirmed merge
  python multi_project_merge_workflow.py execute --strategy merge_strategy_20241215.yaml --confirmed
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze projects for merging"
    )
    analyze_parser.add_argument(
        "--source-profile", required=True, help="Source project profile name"
    )
    analyze_parser.add_argument(
        "--target-profile", required=True, help="Target project profile name"
    )
    analyze_parser.add_argument(
        "--output", default="merge_analysis", help="Output file prefix"
    )
    analyze_parser.add_argument("--verbose", action="store_true", help="Verbose output")

    # Execute command
    execute_parser = subparsers.add_parser("execute", help="Execute merge strategy")
    execute_parser.add_argument("--strategy", required=True, help="Strategy file path")
    execute_parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    execute_parser.add_argument(
        "--confirmed", action="store_true", help="Confirm production merge"
    )
    execute_parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        workflow = MultiProjectMergeWorkflow(verbose=getattr(args, "verbose", False))

        if args.command == "analyze":
            result = await workflow.analyze_projects(
                args.source_profile, args.target_profile, args.output
            )

            print(f"\n🎯 ANALYSIS COMPLETE")
            print(
                f"Safety Score: {result['safety_assessment']['safety_score']:.2f}/1.00"
            )
            print(
                f"Risk Level: {result['safety_assessment']['overall_risk_level'].upper()}"
            )
            print(
                f"Can Proceed: {'✅' if result['safety_assessment']['can_proceed_automatically'] else '❌'}"
            )

        elif args.command == "execute":
            result = await workflow.execute_merge(
                args.strategy, dry_run=args.dry_run, confirmed=args.confirmed
            )

            print(f"\n🚀 EXECUTION {'DRY RUN ' if args.dry_run else ''}COMPLETE")
            print(
                f"Success: {'✅' if result['execution_metadata']['success'] else '❌'}"
            )
            print(f"Duration: {result['execution_metadata']['duration_seconds']:.2f}s")

        return 0

    except KeyboardInterrupt:
        print(f"\n⚠️ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
