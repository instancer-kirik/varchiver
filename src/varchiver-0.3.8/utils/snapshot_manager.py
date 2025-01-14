from datetime import datetime
import os
import json
import shutil
from typing import List, Dict, Optional
from dataclasses import dataclass
from ..utils.constants import DEFAULT_SKIP_PATTERNS

@dataclass
class SnapshotInfo:
    """Information about a snapshot"""
    id: str
    name: str
    timestamp: float
    path: str
    size: int
    description: Optional[str] = None
    tags: List[str] = None
    parent_id: Optional[str] = None

class SnapshotManager:
    """Manages archive snapshots with versioning support"""
    
    def __init__(self, base_dir: str):
        self.base_dir = os.path.expanduser(base_dir)
        self.snapshots_dir = os.path.join(self.base_dir, 'snapshots')
        self.index_file = os.path.join(self.base_dir, 'snapshots.json')
        self._ensure_dirs()
        self._load_index()
    
    def _ensure_dirs(self):
        """Ensure required directories exist"""
        os.makedirs(self.snapshots_dir, exist_ok=True)
    
    def _load_index(self) -> Dict:
        """Load snapshots index"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'snapshots': {}}
    
    def _save_index(self, index: Dict):
        """Save snapshots index"""
        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=2)
    
    def create_snapshot(self, source_path: str, name: str = None, 
                       description: str = None, tags: List[str] = None,
                       parent_id: str = None) -> SnapshotInfo:
        """Create a new snapshot from source path"""
        # Generate snapshot ID and name
        timestamp = datetime.now().timestamp()
        snapshot_id = f"snap_{int(timestamp)}"
        if not name:
            name = os.path.basename(source_path)
        
        # Create snapshot directory
        snapshot_dir = os.path.join(self.snapshots_dir, snapshot_id)
        os.makedirs(snapshot_dir)
        
        # Copy source to snapshot directory
        if os.path.isfile(source_path):
            shutil.copy2(source_path, snapshot_dir)
            size = os.path.getsize(source_path)
        else:
            shutil.copytree(source_path, snapshot_dir, dirs_exist_ok=True)
            size = sum(f.stat().st_size for f in os.scandir(snapshot_dir) if f.is_file())
        
        # Create snapshot info
        snapshot = SnapshotInfo(
            id=snapshot_id,
            name=name,
            timestamp=timestamp,
            path=snapshot_dir,
            size=size,
            description=description,
            tags=tags or [],
            parent_id=parent_id
        )
        
        # Update index
        index = self._load_index()
        index['snapshots'][snapshot_id] = {
            'name': name,
            'timestamp': timestamp,
            'path': snapshot_dir,
            'size': size,
            'description': description,
            'tags': tags or [],
            'parent_id': parent_id
        }
        self._save_index(index)
        
        return snapshot
    
    def list_snapshots(self, tag: str = None, 
                      sort_by: str = 'timestamp',
                      reverse: bool = True) -> List[SnapshotInfo]:
        """List all snapshots, optionally filtered by tag"""
        index = self._load_index()
        snapshots = []
        
        for snap_id, info in index['snapshots'].items():
            if tag and tag not in info.get('tags', []):
                continue
            snapshot = SnapshotInfo(
                id=snap_id,
                name=info['name'],
                timestamp=info['timestamp'],
                path=info['path'],
                size=info['size'],
                description=info.get('description'),
                tags=info.get('tags', []),
                parent_id=info.get('parent_id')
            )
            snapshots.append(snapshot)
        
        # Sort snapshots
        if sort_by == 'name':
            snapshots.sort(key=lambda x: x.name, reverse=reverse)
        elif sort_by == 'size':
            snapshots.sort(key=lambda x: x.size, reverse=reverse)
        else:  # default to timestamp
            snapshots.sort(key=lambda x: x.timestamp, reverse=reverse)
        
        return snapshots
    
    def get_snapshot(self, snapshot_id: str) -> Optional[SnapshotInfo]:
        """Get information about a specific snapshot"""
        index = self._load_index()
        info = index['snapshots'].get(snapshot_id)
        if info:
            return SnapshotInfo(
                id=snapshot_id,
                name=info['name'],
                timestamp=info['timestamp'],
                path=info['path'],
                size=info['size'],
                description=info.get('description'),
                tags=info.get('tags', []),
                parent_id=info.get('parent_id')
            )
        return None
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot and its files"""
        index = self._load_index()
        if snapshot_id not in index['snapshots']:
            return False
        
        # Remove snapshot directory
        snapshot_dir = index['snapshots'][snapshot_id]['path']
        if os.path.exists(snapshot_dir):
            shutil.rmtree(snapshot_dir)
        
        # Update index
        del index['snapshots'][snapshot_id]
        self._save_index(index)
        
        return True
    
    def update_snapshot(self, snapshot_id: str, name: str = None,
                       description: str = None, tags: List[str] = None) -> bool:
        """Update snapshot metadata"""
        index = self._load_index()
        if snapshot_id not in index['snapshots']:
            return False
        
        if name:
            index['snapshots'][snapshot_id]['name'] = name
        if description is not None:
            index['snapshots'][snapshot_id]['description'] = description
        if tags is not None:
            index['snapshots'][snapshot_id]['tags'] = tags
        
        self._save_index(index)
        return True
    
    def get_snapshot_history(self, snapshot_id: str) -> List[SnapshotInfo]:
        """Get the history (parent chain) of a snapshot"""
        history = []
        current = self.get_snapshot(snapshot_id)
        
        while current:
            history.append(current)
            if current.parent_id:
                current = self.get_snapshot(current.parent_id)
            else:
                break
        
        return history
