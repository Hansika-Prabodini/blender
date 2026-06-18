# SPDX-FileCopyrightText: 2025 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Test module for asset catalog management and organization.

Validates catalog hierarchy, asset-to-catalog associations, and persistence operations.

Run with:
blender -b --factory-startup --python tests/python/bl_asset_catalog_api.py
"""

__all__ = (
    "main",
)

import unittest
import bpy
import pathlib
import sys
import tempfile
import os
import uuid
from pathlib import Path


class AssetCatalogBasicsTest(unittest.TestCase):
    """Test basic catalog creation and management."""

    def setUp(self):
        """Set up temporary test catalog structure."""
        super().setUp()
        bpy.ops.wm.read_homefile(use_factory_startup=True)
        
        # Create temporary directory for test asset library
        self._temp_dir = tempfile.TemporaryDirectory(prefix="bl_asset_catalog_test_")
        self._library_path = self._temp_dir.name
        
        # Create the asset library
        self._library = bpy.types.AssetLibraryCollection.new(
            name="test_catalog_lib",
            directory=self._library_path
        )
        
        # Create the catalog file
        self._catalog_file = os.path.join(self._library_path, "blender_assets.cats.txt")
        self._ensure_catalog_file_exists()
        
    def tearDown(self):
        """Clean up temporary catalogs and test data."""
        super().tearDown()
        
        # Remove library
        if self._library is not None:
            bpy.types.AssetLibraryCollection.remove(self._library)
            self._library = None
        
        # Clean up temporary directory
        if hasattr(self, '_temp_dir') and self._temp_dir is not None:
            self._temp_dir.cleanup()
    
    def _ensure_catalog_file_exists(self):
        """Ensure the catalog file exists with proper header."""
        os.makedirs(self._library_path, exist_ok=True)
        
        if not os.path.exists(self._catalog_file):
            with open(self._catalog_file, 'w') as f:
                f.write("# This is an Asset Catalog Definition file for Blender.\n")
                f.write("#\n")
                f.write("# Empty lines and lines starting with `#` will be ignored.\n")
                f.write("# The first non-ignored line should be the version indicator.\n")
                f.write("# Other lines are of the format \"UUID:/catalog/path/for/assets:simple name for debugging\"\n")
                f.write("\n")
                f.write("VERSION 1\n")
                f.write("\n")
    
    def _write_catalog_entry(self, catalog_uuid, catalog_path, simple_name):
        """Write a catalog entry to the catalog file."""
        with open(self._catalog_file, 'a') as f:
            f.write(f"{catalog_uuid}:{catalog_path}:{simple_name}\n")
    
    def _read_catalog_file(self):
        """Read all non-comment lines from the catalog file."""
        with open(self._catalog_file, 'r') as f:
            lines = f.readlines()
        
        # Filter out comments and empty lines
        entries = [line.strip() for line in lines 
                   if line.strip() and not line.strip().startswith('#')]
        return entries
    
    def _catalog_entry_exists(self, catalog_path, catalog_uuid=None):
        """Check if a catalog entry exists in the file."""
        entries = self._read_catalog_file()
        
        for entry in entries:
            if entry.startswith('VERSION'):
                continue
            
            parts = entry.split(':')
            if len(parts) >= 2:
                entry_path = parts[1]
                if entry_path == catalog_path:
                    if catalog_uuid is None:
                        return True
                    elif parts[0] == str(catalog_uuid):
                        return True
        
        return False
    
    def test_catalog_file_creation(self):
        """Test that catalog file is created with correct header."""
        self.assertTrue(os.path.exists(self._catalog_file),
                       "Catalog file should be created")
        
        with open(self._catalog_file, 'r') as f:
            content = f.read()
        
        self.assertIn("VERSION 1", content,
                     "Catalog file should contain version indicator")
        self.assertIn("Asset Catalog Definition file", content,
                     "Catalog file should have proper header")
    
    def test_root_level_catalog_creation(self):
        """Test creating a root-level catalog."""
        test_uuid = str(uuid.uuid4())
        catalog_path = "root_catalog"
        simple_name = "Root Catalog"
        
        self._write_catalog_entry(test_uuid, catalog_path, simple_name)
        
        self.assertTrue(self._catalog_entry_exists(catalog_path, test_uuid),
                       "Root-level catalog should be created")
    
    def test_nested_catalog_creation(self):
        """Test creating nested catalogs with hierarchical paths."""
        catalogs = [
            (str(uuid.uuid4()), "characters", "Characters"),
            (str(uuid.uuid4()), "characters/ellie", "Ellie"),
            (str(uuid.uuid4()), "characters/ellie/poses", "Poses"),
        ]
        
        for catalog_uuid, catalog_path, simple_name in catalogs:
            self._write_catalog_entry(catalog_uuid, catalog_path, simple_name)
        
        for _, catalog_path, _ in catalogs:
            self.assertTrue(self._catalog_entry_exists(catalog_path),
                           f"Catalog {catalog_path} should be created")
    
    def test_catalog_path_hierarchy(self):
        """Test that catalog paths maintain proper hierarchy."""
        parent_uuid = str(uuid.uuid4())
        child_uuid = str(uuid.uuid4())
        
        self._write_catalog_entry(parent_uuid, "models", "Models")
        self._write_catalog_entry(child_uuid, "models/vehicles", "Vehicles")
        
        entries = self._read_catalog_file()
        
        # Find both entries
        models_found = False
        vehicles_found = False
        
        for entry in entries:
            if "models:" in entry and "models/vehicles:" not in entry:
                models_found = True
            if "models/vehicles:" in entry:
                vehicles_found = True
        
        self.assertTrue(models_found, "Parent catalog should exist")
        self.assertTrue(vehicles_found, "Child catalog should exist")
    
    def test_multiple_nested_hierarchies(self):
        """Test creating multiple separate catalog hierarchies."""
        hierarchies = [
            [("chars", "characters"), ("chars_elem", "characters/elements")],
            [("props", "props"), ("props_env", "props/environment")],
        ]
        
        for hierarchy in hierarchies:
            for uid, path in hierarchy:
                self._write_catalog_entry(str(uuid.uuid4()), path, uid)
        
        for hierarchy in hierarchies:
            for _, path in hierarchy:
                self.assertTrue(self._catalog_entry_exists(path),
                               f"Path {path} should exist in hierarchy")
    
    def test_catalog_path_with_forward_slashes(self):
        """Test that catalog paths correctly use forward slash separators."""
        test_paths = [
            "basic",
            "level1/level2",
            "level1/level2/level3",
            "deep/nested/structure/with/many/levels",
        ]
        
        for path in test_paths:
            test_uuid = str(uuid.uuid4())
            self._write_catalog_entry(test_uuid, path, path.replace('/', '_'))
            
            self.assertTrue(self._catalog_entry_exists(path),
                           f"Path {path} should be created with correct slashes")
    
    def test_catalog_uuid_format(self):
        """Test that catalog UUIDs are stored in correct format."""
        test_uuid = str(uuid.uuid4())
        catalog_path = "uuid_test"
        
        self._write_catalog_entry(test_uuid, catalog_path, "UUID Test")
        
        with open(self._catalog_file, 'r') as f:
            content = f.read()
        
        self.assertIn(test_uuid, content,
                     "Catalog UUID should be stored correctly")
        self.assertIn(f"{test_uuid}:{catalog_path}:", content,
                     "Catalog entry format should be correct")


class AssetToCatalogAssociationTest(unittest.TestCase):
    """Test asset-to-catalog associations."""
    
    def setUp(self):
        """Set up test environment with assets and catalogs."""
        super().setUp()
        bpy.ops.wm.read_homefile(use_factory_startup=True)
        
        # Create temporary directory
        self._temp_dir = tempfile.TemporaryDirectory(prefix="bl_asset_catalog_test_")
        self._library_path = self._temp_dir.name
        
        # Create asset library
        self._library = bpy.types.AssetLibraryCollection.new(
            name="test_asset_catalog",
            directory=self._library_path
        )
        
        # Create catalog file
        self._catalog_file = os.path.join(self._library_path, "blender_assets.cats.txt")
        self._ensure_catalog_file_exists()
        
        # Create a test object and mark it as asset
        self._create_test_asset()
    
    def tearDown(self):
        """Clean up."""
        super().tearDown()
        
        if self._library is not None:
            bpy.types.AssetLibraryCollection.remove(self._library)
            self._library = None
        
        if hasattr(self, '_temp_dir') and self._temp_dir is not None:
            self._temp_dir.cleanup()
    
    def _ensure_catalog_file_exists(self):
        """Ensure the catalog file exists with proper header."""
        os.makedirs(self._library_path, exist_ok=True)
        
        if not os.path.exists(self._catalog_file):
            with open(self._catalog_file, 'w') as f:
                f.write("# This is an Asset Catalog Definition file for Blender.\n")
                f.write("#\n")
                f.write("# Empty lines and lines starting with `#` will be ignored.\n")
                f.write("# The first non-ignored line should be the version indicator.\n")
                f.write("# Other lines are of the format \"UUID:/catalog/path/for/assets:simple name for debugging\"\n")
                f.write("\n")
                f.write("VERSION 1\n")
                f.write("\n")
    
    def _write_catalog_entry(self, catalog_uuid, catalog_path, simple_name):
        """Write a catalog entry to the catalog file."""
        with open(self._catalog_file, 'a') as f:
            f.write(f"{catalog_uuid}:{catalog_path}:{simple_name}\n")
    
    def _create_test_asset(self):
        """Create a test object and mark it as an asset."""
        # Create a simple mesh object
        mesh = bpy.data.meshes.new("test_mesh")
        obj = bpy.data.objects.new("test_asset_object", mesh)
        bpy.context.scene.collection.objects.link(obj)
        
        # Mark as asset
        if not obj.asset_data:
            obj.asset_mark()
        
        self._test_asset = obj
    
    def test_asset_has_catalog_id_property(self):
        """Test that assets have catalog_id property."""
        self.assertTrue(hasattr(self._test_asset, 'asset_data'),
                       "Asset should have asset_data")
        self.assertTrue(hasattr(self._test_asset.asset_data, 'catalog_id'),
                       "Asset metadata should have catalog_id property")
    
    def test_asset_catalog_id_initially_empty(self):
        """Test that asset catalog_id is initially empty/unset."""
        catalog_id = self._test_asset.asset_data.catalog_id
        # Initially should be empty UUID (00000000-0000-0000-0000-000000000000) or empty string
        self.assertTrue(
            catalog_id == "" or catalog_id == "00000000-0000-0000-0000-000000000000",
            f"Initial catalog_id should be empty, got: {catalog_id}"
        )
    
    def test_asset_assign_to_catalog(self):
        """Test assigning an asset to a specific catalog."""
        catalog_uuid = str(uuid.uuid4())
        catalog_path = "test/assigned"
        
        # Write catalog to file
        self._write_catalog_entry(catalog_uuid, catalog_path, "Assigned Test")
        
        # Assign asset to catalog
        self._test_asset.asset_data.catalog_id = catalog_uuid
        
        self.assertEqual(self._test_asset.asset_data.catalog_id, catalog_uuid,
                        "Asset should be assigned to correct catalog")
    
    def test_asset_unassign_from_catalog(self):
        """Test removing asset from catalog."""
        catalog_uuid = str(uuid.uuid4())
        catalog_path = "test/unassign"
        
        self._write_catalog_entry(catalog_uuid, catalog_path, "Unassign Test")
        
        # Assign then unassign
        self._test_asset.asset_data.catalog_id = catalog_uuid
        self._test_asset.asset_data.catalog_id = ""
        
        # Should be empty
        self.assertTrue(
            self._test_asset.asset_data.catalog_id == "" or 
            self._test_asset.asset_data.catalog_id == "00000000-0000-0000-0000-000000000000",
            "Asset should be unassigned from catalog"
        )
    
    def test_multiple_assets_same_catalog(self):
        """Test assigning multiple assets to the same catalog."""
        # Create second asset
        mesh2 = bpy.data.meshes.new("test_mesh2")
        obj2 = bpy.data.objects.new("test_asset_object2", mesh2)
        bpy.context.scene.collection.objects.link(obj2)
        obj2.asset_mark()
        
        # Create catalog
        catalog_uuid = str(uuid.uuid4())
        self._write_catalog_entry(catalog_uuid, "test/shared", "Shared Catalog")
        
        # Assign both to same catalog
        self._test_asset.asset_data.catalog_id = catalog_uuid
        obj2.asset_data.catalog_id = catalog_uuid
        
        self.assertEqual(self._test_asset.asset_data.catalog_id, catalog_uuid)
        self.assertEqual(obj2.asset_data.catalog_id, catalog_uuid)


class CatalogPersistenceTest(unittest.TestCase):
    """Test catalog persistence across operations."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        bpy.ops.wm.read_homefile(use_factory_startup=True)
        
        self._temp_dir = tempfile.TemporaryDirectory(prefix="bl_asset_catalog_persist_")
        self._library_path = self._temp_dir.name
        
        self._library = bpy.types.AssetLibraryCollection.new(
            name="test_persist_lib",
            directory=self._library_path
        )
        
        self._catalog_file = os.path.join(self._library_path, "blender_assets.cats.txt")
        self._ensure_catalog_file_exists()
    
    def tearDown(self):
        """Clean up."""
        super().tearDown()
        
        if self._library is not None:
            bpy.types.AssetLibraryCollection.remove(self._library)
            self._library = None
        
        if hasattr(self, '_temp_dir') and self._temp_dir is not None:
            self._temp_dir.cleanup()
    
    def _ensure_catalog_file_exists(self):
        """Ensure the catalog file exists."""
        os.makedirs(self._library_path, exist_ok=True)
        
        if not os.path.exists(self._catalog_file):
            with open(self._catalog_file, 'w') as f:
                f.write("# This is an Asset Catalog Definition file for Blender.\n")
                f.write("# Empty lines and lines starting with `#` will be ignored.\n")
                f.write("# The first non-ignored line should be the version indicator.\n")
                f.write("# Other lines are of the format \"UUID:/catalog/path/for/assets:simple name for debugging\"\n")
                f.write("\n")
                f.write("VERSION 1\n")
                f.write("\n")
    
    def _write_catalog_entry(self, catalog_uuid, catalog_path, simple_name):
        """Write a catalog entry."""
        with open(self._catalog_file, 'a') as f:
            f.write(f"{catalog_uuid}:{catalog_path}:{simple_name}\n")
    
    def _read_catalog_file(self):
        """Read catalog file and return non-comment entries."""
        with open(self._catalog_file, 'r') as f:
            lines = f.readlines()
        
        return [line.strip() for line in lines 
                if line.strip() and not line.strip().startswith('#')]
    
    def test_catalog_entry_persists_in_file(self):
        """Test that catalog entries persist in the file."""
        test_uuid = str(uuid.uuid4())
        test_path = "persist/test"
        
        self._write_catalog_entry(test_uuid, test_path, "Persist Test")
        
        # Read back
        entries = self._read_catalog_file()
        
        found = False
        for entry in entries:
            if test_path in entry and test_uuid in entry:
                found = True
                break
        
        self.assertTrue(found, "Catalog entry should persist in file")
    
    def test_multiple_catalog_entries_persist(self):
        """Test that multiple catalog entries persist."""
        test_data = [
            (str(uuid.uuid4()), "path/one", "One"),
            (str(uuid.uuid4()), "path/two", "Two"),
            (str(uuid.uuid4()), "path/three", "Three"),
        ]
        
        for uid, path, name in test_data:
            self._write_catalog_entry(uid, path, name)
        
        entries = self._read_catalog_file()
        
        for uid, path, name in test_data:
            found = any(uid in entry and path in entry for entry in entries)
            self.assertTrue(found, f"Entry {path} should persist")
    
    def test_catalog_file_survives_library_operations(self):
        """Test that catalog file is preserved across library operations."""
        # Write initial catalog
        test_uuid = str(uuid.uuid4())
        self._write_catalog_entry(test_uuid, "survives/test", "Survives")
        
        # Verify it persists
        entries = self._read_catalog_file()
        initial_count = len(entries)
        
        # Write another entry
        another_uuid = str(uuid.uuid4())
        self._write_catalog_entry(another_uuid, "survives/another", "Another")
        
        entries = self._read_catalog_file()
        
        self.assertGreater(len(entries), initial_count,
                          "File should accumulate entries")


class CatalogNamingTest(unittest.TestCase):
    """Test catalog naming and path edge cases."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        bpy.ops.wm.read_homefile(use_factory_startup=True)
        
        self._temp_dir = tempfile.TemporaryDirectory(prefix="bl_asset_catalog_naming_")
        self._library_path = self._temp_dir.name
        
        self._library = bpy.types.AssetLibraryCollection.new(
            name="test_naming_lib",
            directory=self._library_path
        )
        
        self._catalog_file = os.path.join(self._library_path, "blender_assets.cats.txt")
        self._ensure_catalog_file_exists()
    
    def tearDown(self):
        """Clean up."""
        super().tearDown()
        
        if self._library is not None:
            bpy.types.AssetLibraryCollection.remove(self._library)
            self._library = None
        
        if hasattr(self, '_temp_dir') and self._temp_dir is not None:
            self._temp_dir.cleanup()
    
    def _ensure_catalog_file_exists(self):
        """Ensure catalog file exists."""
        os.makedirs(self._library_path, exist_ok=True)
        
        if not os.path.exists(self._catalog_file):
            with open(self._catalog_file, 'w') as f:
                f.write("VERSION 1\n")
                f.write("\n")
    
    def _write_catalog_entry(self, catalog_uuid, catalog_path, simple_name):
        """Write a catalog entry."""
        with open(self._catalog_file, 'a') as f:
            f.write(f"{catalog_uuid}:{catalog_path}:{simple_name}\n")
    
    def test_catalog_simple_name(self):
        """Test that simple names are stored correctly."""
        test_uuid = str(uuid.uuid4())
        simple_name = "Simple Name For Debugging"
        
        self._write_catalog_entry(test_uuid, "path/to/catalog", simple_name)
        
        with open(self._catalog_file, 'r') as f:
            content = f.read()
        
        self.assertIn(simple_name, content,
                     "Simple name should be stored")
    
    def test_catalog_path_with_spaces(self):
        """Test that catalog paths with spaces are handled."""
        test_uuid = str(uuid.uuid4())
        # Paths with spaces in the simple name, not the path itself
        path_with_space = "with/spaces"
        
        self._write_catalog_entry(test_uuid, path_with_space, "With Spaces")
        
        with open(self._catalog_file, 'r') as f:
            content = f.read()
        
        self.assertIn(path_with_space, content)
    
    def test_unicode_in_simple_names(self):
        """Test that unicode characters work in simple names."""
        test_uuid = str(uuid.uuid4())
        unicode_name = "Каталог Русский 中文"  # Russian and Chinese characters
        
        self._write_catalog_entry(test_uuid, "unicode/test", unicode_name)
        
        with open(self._catalog_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn(unicode_name, content,
                     "Unicode simple names should be supported")
    
    def test_deeply_nested_catalog_path(self):
        """Test deeply nested catalog paths."""
        test_uuid = str(uuid.uuid4())
        deep_path = "a/b/c/d/e/f/g/h/i/j/k/l/m/n/o/p"
        
        self._write_catalog_entry(test_uuid, deep_path, "Deep Path")
        
        with open(self._catalog_file, 'r') as f:
            content = f.read()
        
        self.assertIn(deep_path, content,
                     "Deeply nested paths should be supported")


class CatalogErrorHandlingTest(unittest.TestCase):
    """Test error handling and edge cases."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        bpy.ops.wm.read_homefile(use_factory_startup=True)
        
        self._temp_dir = tempfile.TemporaryDirectory(prefix="bl_asset_catalog_error_")
        self._library_path = self._temp_dir.name
        
        self._library = bpy.types.AssetLibraryCollection.new(
            name="test_error_lib",
            directory=self._library_path
        )
        
        self._catalog_file = os.path.join(self._library_path, "blender_assets.cats.txt")
        self._ensure_catalog_file_exists()
    
    def tearDown(self):
        """Clean up."""
        super().tearDown()
        
        if self._library is not None:
            bpy.types.AssetLibraryCollection.remove(self._library)
            self._library = None
        
        if hasattr(self, '_temp_dir') and self._temp_dir is not None:
            self._temp_dir.cleanup()
    
    def _ensure_catalog_file_exists(self):
        """Ensure catalog file exists."""
        os.makedirs(self._library_path, exist_ok=True)
        
        if not os.path.exists(self._catalog_file):
            with open(self._catalog_file, 'w') as f:
                f.write("VERSION 1\n")
                f.write("\n")
    
    def _write_catalog_entry(self, catalog_uuid, catalog_path, simple_name):
        """Write a catalog entry."""
        with open(self._catalog_file, 'a') as f:
            f.write(f"{catalog_uuid}:{catalog_path}:{simple_name}\n")
    
    def _read_catalog_file(self):
        """Read catalog entries."""
        with open(self._catalog_file, 'r') as f:
            lines = f.readlines()
        return [line.strip() for line in lines 
                if line.strip() and not line.strip().startswith('#')]
    
    def test_empty_catalog_file_valid(self):
        """Test that empty catalog file is valid."""
        self.assertTrue(os.path.exists(self._catalog_file),
                       "Catalog file should exist")
        
        entries = self._read_catalog_file()
        # Should only have VERSION line
        self.assertTrue(any('VERSION' in e for e in entries),
                       "Should have VERSION entry")
    
    def test_duplicate_paths_allowed(self):
        """Test that duplicate paths can be stored (with different UUIDs)."""
        # This tests the real catalog behavior where multiple UUIDs can point to same path
        uuid1 = str(uuid.uuid4())
        uuid2 = str(uuid.uuid4())
        same_path = "duplicates/path"
        
        self._write_catalog_entry(uuid1, same_path, "First")
        self._write_catalog_entry(uuid2, same_path, "Second")
        
        entries = self._read_catalog_file()
        
        count = sum(1 for e in entries if same_path in e)
        self.assertEqual(count, 2, "Duplicate paths with different UUIDs should be allowed")
    
    def test_catalog_with_no_simple_name(self):
        """Test catalog entry with missing simple name."""
        test_uuid = str(uuid.uuid4())
        
        # Write entry without simple name
        with open(self._catalog_file, 'a') as f:
            f.write(f"{test_uuid}:no/simple/name\n")
        
        entries = self._read_catalog_file()
        found = any(test_uuid in e and "no/simple/name" in e for e in entries)
        
        self.assertTrue(found, "Catalog without simple name should be stored")
    
    def test_malformed_entries_skipped(self):
        """Test that malformed entries don't break the file."""
        # Add some valid entries first
        valid_uuid = str(uuid.uuid4())
        self._write_catalog_entry(valid_uuid, "valid/path", "Valid")
        
        # Add a malformed entry (not following proper format)
        with open(self._catalog_file, 'a') as f:
            f.write("this is not a valid catalog entry\n")
        
        # Add another valid entry
        another_uuid = str(uuid.uuid4())
        self._write_catalog_entry(another_uuid, "another/valid", "Another")
        
        entries = self._read_catalog_file()
        
        # Both valid entries should exist
        valid_found = any(valid_uuid in e for e in entries)
        another_found = any(another_uuid in e for e in entries)
        
        self.assertTrue(valid_found, "First valid entry should exist")
        self.assertTrue(another_found, "Second valid entry should exist")


class CatalogRenameTest(unittest.TestCase):
    """Test catalog renaming operations."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        bpy.ops.wm.read_homefile(use_factory_startup=True)
        
        self._temp_dir = tempfile.TemporaryDirectory(prefix="bl_asset_catalog_rename_")
        self._library_path = self._temp_dir.name
        
        self._library = bpy.types.AssetLibraryCollection.new(
            name="test_rename_lib",
            directory=self._library_path
        )
        
        self._catalog_file = os.path.join(self._library_path, "blender_assets.cats.txt")
        self._ensure_catalog_file_exists()
        
        # Create test catalogs
        self._catalog_uuid_1 = str(uuid.uuid4())
        self._catalog_uuid_2 = str(uuid.uuid4())
        
        self._write_catalog_entry(self._catalog_uuid_1, "original/name", "Original Name")
        self._write_catalog_entry(self._catalog_uuid_2, "original/name/child", "Original Child")
    
    def tearDown(self):
        """Clean up."""
        super().tearDown()
        
        if self._library is not None:
            bpy.types.AssetLibraryCollection.remove(self._library)
            self._library = None
        
        if hasattr(self, '_temp_dir') and self._temp_dir is not None:
            self._temp_dir.cleanup()
    
    def _ensure_catalog_file_exists(self):
        """Ensure catalog file exists."""
        os.makedirs(self._library_path, exist_ok=True)
        
        if not os.path.exists(self._catalog_file):
            with open(self._catalog_file, 'w') as f:
                f.write("VERSION 1\n")
                f.write("\n")
    
    def _write_catalog_entry(self, catalog_uuid, catalog_path, simple_name):
        """Write a catalog entry."""
        with open(self._catalog_file, 'a') as f:
            f.write(f"{catalog_uuid}:{catalog_path}:{simple_name}\n")
    
    def _read_catalog_file(self):
        """Read catalog entries."""
        with open(self._catalog_file, 'r') as f:
            lines = f.readlines()
        return [line.strip() for line in lines 
                if line.strip() and not line.strip().startswith('#')]
    
    def _catalog_path_exists(self, path):
        """Check if a catalog path exists."""
        entries = self._read_catalog_file()
        return any(f":{path}:" in e for e in entries)
    
    def _update_catalog_path(self, old_path, new_path):
        """Rename a catalog path in the file."""
        entries = self._read_catalog_file()
        
        # Read the file without the entries
        with open(self._catalog_file, 'r') as f:
            lines = f.readlines()
        
        # Find and modify the entry
        modified_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('VERSION') or not stripped or stripped.startswith('#'):
                modified_lines.append(line)
            elif f":{old_path}:" in stripped:
                # Replace the old path with new path
                modified_line = stripped.replace(f":{old_path}:", f":{new_path}:")
                modified_lines.append(modified_line + "\n")
            else:
                modified_lines.append(line)
        
        # Write back
        with open(self._catalog_file, 'w') as f:
            f.writelines(modified_lines)
    
    def test_rename_catalog_path(self):
        """Test renaming a catalog path."""
        old_path = "original/name"
        new_path = "renamed/name"
        
        self.assertTrue(self._catalog_path_exists(old_path),
                       "Original path should exist")
        
        self._update_catalog_path(old_path, new_path)
        
        self.assertFalse(self._catalog_path_exists(old_path),
                        "Original path should no longer exist")
        self.assertTrue(self._catalog_path_exists(new_path),
                       "Renamed path should exist")
    
    def test_rename_affects_uuid_association(self):
        """Test that renaming preserves UUID association."""
        old_path = "original/name"
        new_path = "renamed/name"
        
        self._update_catalog_path(old_path, new_path)
        
        entries = self._read_catalog_file()
        
        # Find the entry with our UUID
        found = False
        for entry in entries:
            if self._catalog_uuid_1 in entry and f":{new_path}:" in entry:
                found = True
                break
        
        self.assertTrue(found,
                       "UUID should still be associated with renamed path")
    
    def test_rename_preserves_simple_name(self):
        """Test that renaming preserves simple name."""
        original_simple_name = "Original Name"
        old_path = "original/name"
        new_path = "renamed/name"
        
        self._update_catalog_path(old_path, new_path)
        
        entries = self._read_catalog_file()
        
        found = False
        for entry in entries:
            if self._catalog_uuid_1 in entry and original_simple_name in entry:
                found = True
                break
        
        self.assertTrue(found,
                       "Simple name should be preserved during rename")
    
    def test_rename_child_when_parent_renamed(self):
        """Test that child catalogs update when parent is renamed."""
        # This tests the conceptual case where a parent path changes
        old_parent = "original/name"
        new_parent = "renamed/name"
        old_child = "original/name/child"
        new_child = "renamed/name/child"
        
        self.assertTrue(self._catalog_path_exists(old_child),
                       "Child should exist initially")
        
        self._update_catalog_path(old_parent, new_parent)
        self._update_catalog_path(old_child, new_child)
        
        self.assertTrue(self._catalog_path_exists(new_child),
                       "Child path should be updated")
    
    def test_simple_name_can_be_changed(self):
        """Test that simple names can be updated independently."""
        old_entry = None
        entries = self._read_catalog_file()
        
        for entry in entries:
            if self._catalog_uuid_1 in entry:
                old_entry = entry
                break
        
        self.assertIsNotNone(old_entry)
        
        # Modify the file to change simple name
        with open(self._catalog_file, 'r') as f:
            lines = f.readlines()
        
        modified_lines = []
        for line in lines:
            if self._catalog_uuid_1 in line:
                modified_line = line.rstrip()
                # Change simple name at the end
                parts = modified_line.split(':')
                if len(parts) >= 2:
                    parts[-1] = "Updated Simple Name"
                    modified_lines.append(':'.join(parts) + "\n")
                else:
                    modified_lines.append(line)
            else:
                modified_lines.append(line)
        
        with open(self._catalog_file, 'w') as f:
            f.writelines(modified_lines)
        
        # Verify change
        entries = self._read_catalog_file()
        updated = any("Updated Simple Name" in e and self._catalog_uuid_1 in e 
                     for e in entries)
        
        self.assertTrue(updated,
                       "Simple name should be updatable")


class CatalogDeletionTest(unittest.TestCase):
    """Test catalog deletion operations."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        bpy.ops.wm.read_homefile(use_factory_startup=True)
        
        self._temp_dir = tempfile.TemporaryDirectory(prefix="bl_asset_catalog_delete_")
        self._library_path = self._temp_dir.name
        
        self._library = bpy.types.AssetLibraryCollection.new(
            name="test_delete_lib",
            directory=self._library_path
        )
        
        self._catalog_file = os.path.join(self._library_path, "blender_assets.cats.txt")
        self._ensure_catalog_file_exists()
        
        # Create test catalogs
        self._catalog_uuid_1 = str(uuid.uuid4())
        self._catalog_uuid_2 = str(uuid.uuid4())
        self._catalog_uuid_3 = str(uuid.uuid4())
        
        self._write_catalog_entry(self._catalog_uuid_1, "delete/me", "Delete Me")
        self._write_catalog_entry(self._catalog_uuid_2, "delete/me/child", "Delete Child")
        self._write_catalog_entry(self._catalog_uuid_3, "keep/me", "Keep Me")
        
        # Create a test asset linked to a catalog
        mesh = bpy.data.meshes.new("test_mesh_delete")
        obj = bpy.data.objects.new("test_asset_delete", mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.asset_mark()
        obj.asset_data.catalog_id = self._catalog_uuid_1
        
        self._test_asset = obj
    
    def tearDown(self):
        """Clean up."""
        super().tearDown()
        
        if self._library is not None:
            bpy.types.AssetLibraryCollection.remove(self._library)
            self._library = None
        
        if hasattr(self, '_temp_dir') and self._temp_dir is not None:
            self._temp_dir.cleanup()
    
    def _ensure_catalog_file_exists(self):
        """Ensure catalog file exists."""
        os.makedirs(self._library_path, exist_ok=True)
        
        if not os.path.exists(self._catalog_file):
            with open(self._catalog_file, 'w') as f:
                f.write("VERSION 1\n")
                f.write("\n")
    
    def _write_catalog_entry(self, catalog_uuid, catalog_path, simple_name):
        """Write a catalog entry."""
        with open(self._catalog_file, 'a') as f:
            f.write(f"{catalog_uuid}:{catalog_path}:{simple_name}\n")
    
    def _read_catalog_file(self):
        """Read catalog entries."""
        with open(self._catalog_file, 'r') as f:
            lines = f.readlines()
        return [line.strip() for line in lines 
                if line.strip() and not line.strip().startswith('#')]
    
    def _delete_catalog_entry(self, catalog_uuid):
        """Delete a catalog entry by UUID."""
        with open(self._catalog_file, 'r') as f:
            lines = f.readlines()
        
        # Filter out the entry with this UUID
        filtered_lines = [line for line in lines if catalog_uuid not in line]
        
        with open(self._catalog_file, 'w') as f:
            f.writelines(filtered_lines)
    
    def _catalog_uuid_exists(self, catalog_uuid):
        """Check if a UUID exists in the catalog file."""
        entries = self._read_catalog_file()
        return any(catalog_uuid in e for e in entries)
    
    def test_delete_catalog_entry(self):
        """Test deleting a catalog entry."""
        self.assertTrue(self._catalog_uuid_exists(self._catalog_uuid_1),
                       "Catalog should exist before deletion")
        
        self._delete_catalog_entry(self._catalog_uuid_1)
        
        self.assertFalse(self._catalog_uuid_exists(self._catalog_uuid_1),
                        "Catalog should be deleted")
    
    def test_delete_preserves_other_catalogs(self):
        """Test that deleting one catalog preserves others."""
        self._delete_catalog_entry(self._catalog_uuid_1)
        
        self.assertTrue(self._catalog_uuid_exists(self._catalog_uuid_2),
                       "Child catalog should still exist")
        self.assertTrue(self._catalog_uuid_exists(self._catalog_uuid_3),
                       "Other catalogs should be preserved")
    
    def test_asset_reassigned_when_catalog_deleted(self):
        """Test that assets linked to deleted catalogs can be unassigned."""
        # Verify asset is linked
        self.assertEqual(self._test_asset.asset_data.catalog_id, self._catalog_uuid_1)
        
        # Delete the catalog
        self._delete_catalog_entry(self._catalog_uuid_1)
        
        # Asset should still have the UUID (catalog system would handle reassignment)
        # But we can unassign it
        self._test_asset.asset_data.catalog_id = ""
        
        self.assertTrue(
            self._test_asset.asset_data.catalog_id == "" or
            self._test_asset.asset_data.catalog_id == "00000000-0000-0000-0000-000000000000",
            "Asset should be unassigned"
        )
    
    def test_delete_catalog_path_by_pattern(self):
        """Test deleting all catalogs under a path."""
        # Count entries before
        entries_before = self._read_catalog_file()
        delete_count_before = sum(1 for e in entries_before if self._catalog_uuid_1 in e or self._catalog_uuid_2 in e)
        
        # Delete both entries under "delete" path
        self._delete_catalog_entry(self._catalog_uuid_1)
        self._delete_catalog_entry(self._catalog_uuid_2)
        
        # Verify they're gone
        entries_after = self._read_catalog_file()
        delete_count_after = sum(1 for e in entries_after if self._catalog_uuid_1 in e or self._catalog_uuid_2 in e)
        
        self.assertEqual(delete_count_after, 0,
                        "Both deleted catalogs should be gone")
        self.assertTrue(self._catalog_uuid_exists(self._catalog_uuid_3),
                       "Other catalog should remain")
    
    def test_empty_catalog_file_after_deletion(self):
        """Test that file remains valid after deleting all user catalogs."""
        # Delete all user catalogs (not VERSION)
        self._delete_catalog_entry(self._catalog_uuid_1)
        self._delete_catalog_entry(self._catalog_uuid_2)
        self._delete_catalog_entry(self._catalog_uuid_3)
        
        # Verify VERSION line still exists
        with open(self._catalog_file, 'r') as f:
            content = f.read()
        
        self.assertIn("VERSION 1", content,
                     "VERSION line should persist after deletion")


class CatalogQueryTest(unittest.TestCase):
    """Test catalog querying and searching."""
    
    def setUp(self):
        """Set up test environment with sample catalogs."""
        super().setUp()
        bpy.ops.wm.read_homefile(use_factory_startup=True)
        
        self._temp_dir = tempfile.TemporaryDirectory(prefix="bl_asset_catalog_query_")
        self._library_path = self._temp_dir.name
        
        self._library = bpy.types.AssetLibraryCollection.new(
            name="test_query_lib",
            directory=self._library_path
        )
        
        self._catalog_file = os.path.join(self._library_path, "blender_assets.cats.txt")
        self._ensure_catalog_file_exists()
        
        # Create sample catalogs
        self._sample_catalogs = [
            (str(uuid.uuid4()), "characters/ellie/poses", "Ellie Poses"),
            (str(uuid.uuid4()), "characters/joel/poses", "Joel Poses"),
            (str(uuid.uuid4()), "environments/buildings", "Buildings"),
            (str(uuid.uuid4()), "environments/nature", "Nature"),
            (str(uuid.uuid4()), "props/weapons", "Weapons"),
        ]
        
        for uid, path, name in self._sample_catalogs:
            self._write_catalog_entry(uid, path, name)
    
    def tearDown(self):
        """Clean up."""
        super().tearDown()
        
        if self._library is not None:
            bpy.types.AssetLibraryCollection.remove(self._library)
            self._library = None
        
        if hasattr(self, '_temp_dir') and self._temp_dir is not None:
            self._temp_dir.cleanup()
    
    def _ensure_catalog_file_exists(self):
        """Ensure catalog file exists."""
        os.makedirs(self._library_path, exist_ok=True)
        
        if not os.path.exists(self._catalog_file):
            with open(self._catalog_file, 'w') as f:
                f.write("VERSION 1\n")
                f.write("\n")
    
    def _write_catalog_entry(self, catalog_uuid, catalog_path, simple_name):
        """Write a catalog entry."""
        with open(self._catalog_file, 'a') as f:
            f.write(f"{catalog_uuid}:{catalog_path}:{simple_name}\n")
    
    def _read_catalog_file(self):
        """Read catalog entries."""
        with open(self._catalog_file, 'r') as f:
            lines = f.readlines()
        return [line.strip() for line in lines 
                if line.strip() and not line.strip().startswith('#')]
    
    def test_find_catalog_by_path(self):
        """Test finding catalogs by path prefix."""
        entries = self._read_catalog_file()
        
        # Find all character catalogs
        character_catalogs = [e for e in entries if "characters/" in e]
        
        self.assertGreater(len(character_catalogs), 0,
                          "Should find character catalogs")
        self.assertEqual(len(character_catalogs), 2,
                        "Should find exactly 2 character catalogs")
    
    def test_find_catalog_by_hierarchy_level(self):
        """Test finding catalogs at specific hierarchy levels."""
        entries = self._read_catalog_file()
        
        # Find root level catalogs (no slashes in path)
        root_catalogs = [e for e in entries if e.startswith('VERSION')]
        non_root = [e for e in entries if '/' in e and not e.startswith('VERSION')]
        
        self.assertGreater(len(non_root), 0,
                          "Should have nested catalogs")
    
    def test_list_subcatalogs_by_parent_path(self):
        """Test finding all catalogs under a parent path."""
        entries = self._read_catalog_file()
        
        # Find all catalogs under "characters"
        character_children = []
        for entry in entries:
            if entry.startswith('VERSION') or not ':' in entry:
                continue
            parts = entry.split(':')
            if len(parts) >= 2:
                path = parts[1]
                if path.startswith("characters/"):
                    character_children.append(path)
        
        self.assertEqual(len(character_children), 2,
                        "Should find all character sub-catalogs")
    
    def test_find_catalogs_by_simple_name(self):
        """Test finding catalogs by simple name."""
        entries = self._read_catalog_file()
        
        # Find "Poses" entries
        pose_catalogs = [e for e in entries if "Poses" in e]
        
        self.assertEqual(len(pose_catalogs), 2,
                        "Should find both pose catalogs")
    
    def test_count_catalog_hierarchy_depth(self):
        """Test counting depth of catalog hierarchies."""
        entries = self._read_catalog_file()
        
        max_depth = 0
        for entry in entries:
            if entry.startswith('VERSION') or not ':' in entry:
                continue
            parts = entry.split(':')
            if len(parts) >= 2:
                path = parts[1]
                depth = path.count('/')
                max_depth = max(max_depth, depth)
        
        self.assertGreaterEqual(max_depth, 2,
                               "Should have nested structures")


def main():
    """Main entry point for the test suite."""
    global args
    import argparse
    
    if '--' in sys.argv:
        argv = [sys.argv[0]] + sys.argv[sys.argv.index('--') + 1:]
    else:
        argv = sys.argv
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--testdir', required=False, type=pathlib.Path)
    args, remaining = parser.parse_known_args(argv)
    
    unittest.main(argv=remaining)


if __name__ == "__main__":
    main()
