#!/usr/bin/env python3
"""
CSV Viewer Package - Schema-agnostic CSV file viewing and editing

This package provides clean, focused tools for viewing and editing CSV files
without making assumptions about the data structure or content.
"""

from .csv_data_model import (
    CsvDataModel,
    CsvRow,
    ColumnInfo,
    ColumnType,
    CsvStructureDetector
)

from .csv_viewer_widget import (
    CsvViewerWidget,
    CsvTableWidget,
    RowEditDialog
)

from .csv_filter_widget import (
    CsvFilterWidget,
    ColumnFilter
)

from .csv_comparison import (
    CsvComparison,
    CsvComparisonResult
)

from .status_inference_module import (
    StatusInferenceModule,
    StatusType,
    StatusRule
)

from .csv_preview_dialog import (
    CsvPreviewDialog,
    FileAnalysisWorker
)

__all__ = [
    # Core components
    'CsvViewerWidget',
    'CsvDataModel',
    'CsvRow',
    'ColumnInfo',
    'ColumnType',
    'CsvStructureDetector',
    'CsvTableWidget',
    'RowEditDialog',

    # Filter components
    'CsvFilterWidget',
    'ColumnFilter',

    # Comparison components
    'CsvComparison',
    'CsvComparisonResult',

    # Status inference components
    'StatusInferenceModule',
    'StatusType',
    'StatusRule',

    # Preview components
    'CsvPreviewDialog',
    'FileAnalysisWorker'
]

# Version info
__version__ = '1.0.0'
__author__ = 'Varchiver Team'
__description__ = 'Schema-agnostic CSV viewer and editor'
