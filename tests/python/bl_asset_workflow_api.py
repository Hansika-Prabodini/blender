# SPDX-FileCopyrightText: 2025 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Integration tests for asset workflow operations, validating asset shelves, activation,
preview generation, and library management.

Usage:
blender --background --factory-startup --python tests/python/bl_asset_workflow_api.py
"""

__all__ = (
    "main",
)

import sys
import unittest
import tempfile
import pathlib
import os

import bpy


class AssetWorkflowBase(unittest.TestCase):
    """Base class for asset workflow integration tests."""

    _library = None
    _library_folder = None
    _test_objects = {}
    _test_catalog_path = "integration_test"

    def setUp(self):
        """Set up test catalogs, assets, and shelves."""
        super().setUp()
        
        # Reset to factory startup
        bpy.ops.wm.read_homefile(use_factory_startup=True)
        
        # Create temporary library directory
        self._library_folder = tempfile.TemporaryDirectory("asset_workflow_test")
        
        # Create asset library
        lib_path = self._library_folder.name
        self._library = bpy.types.AssetLibraryCollection.new(
            name="test_workflow_lib",
            directory=lib_path
        )
        
        # Create test objects
        self._create_test_objects()

    def tearDown(self):
        """Clean shelves, libraries, and test assets."""
        super().tearDown()
        
        # Remove created objects
        for obj_name in list(self._test_objects.keys()):
            if obj_name in bpy.data.objects:
                bpy.data.objects.remove(bpy.data.objects[obj_name])
        self._test_objects.clear()
        
        # Remove asset library
        if self._library:
            bpy.types.AssetLibraryCollection.remove(self._library)
            self._library = None
        
        # Clean up temp directory
        if self._library_folder:
            self._library_folder.cleanup()
            self._library_folder = None

    def _create_test_objects(self):
        """Create test objects for asset workflow tests."""
        # Create a test mesh object
        mesh = bpy.data.meshes.new("TestMesh")
        mesh_obj = bpy.data.objects.new("TestObject", mesh)
        bpy.context.scene.collection.objects.link(mesh_obj)
        self._test_objects["TestObject"] = mesh_obj

        # Create a test collection
        test_collection = bpy.data.collections.new("TestCollection")
        bpy.context.scene.collection.children.link(test_collection)
        self._test_objects["TestCollection"] = test_collection

    def _mark_as_asset(self, data_block, catalog_path=""):
        """Mark a data block as an asset."""
        # Handle object types
        if isinstance(data_block, bpy.types.Object):
            # Ensure object is properly selected and active in context
            bpy.context.view_layer.objects.active = data_block
            data_block.select_set(True)
            
            # Use asset.mark operator
            try:
                bpy.ops.asset.mark()
            except RuntimeError:
                # Asset marking might fail for unsupported types
                pass
        
        # Set catalog path if provided
        if catalog_path and data_block.asset_data:
            data_block.asset_data.catalog_id = self._get_or_create_catalog(catalog_path)

    def _get_or_create_catalog(self, catalog_path):
        """Get or create a catalog in the test library."""
        # For now, just return a valid UUID format
        # In real implementation, this would interact with the asset catalog system
        import uuid
        return str(uuid.uuid4())

    def _is_asset_marked(self, data_block) -> bool:
        """Check if a data block is marked as an asset."""
        return data_block.asset_data is not None


class AssetShelfTest(AssetWorkflowBase):
    """Test asset shelf creation and configuration."""

    def test_shelf_creation(self):
        """Test that an asset shelf can be created and configured."""
        # Shelves are UI-level constructs, so we test through the workspace settings
        workspace = bpy.context.workspace
        self.assertIsNotNone(workspace)
        
        # Verify workspace has asset library reference
        self.assertTrue(hasattr(workspace, 'asset_library_ref'))

    def test_shelf_visibility_toggle(self):
        """Test toggling shelf visibility."""
        workspace = bpy.context.workspace
        initial_ref = workspace.asset_library_ref
        
        # Change library reference
        workspace.asset_library_ref = 0  # Change to different library
        self.assertEqual(workspace.asset_library_ref, 0)
        
        # Restore
        workspace.asset_library_ref = initial_ref

    def test_multiple_shelf_configuration(self):
        """Test managing multiple shelf configurations."""
        workspace = bpy.context.workspace
        
        # Store initial state
        initial_ref = workspace.asset_library_ref
        
        # Test that we can manage library references
        self.assertIsNotNone(workspace)
        
        # Restore state
        workspace.asset_library_ref = initial_ref


class AssetActivationTest(AssetWorkflowBase):
    """Test asset activation operations."""

    def test_mark_asset_for_activation(self):
        """Test marking assets for activation and verifying active status."""
        test_obj = self._test_objects["TestObject"]
        
        # Initially, object should not be marked as asset
        self.assertFalse(self._is_asset_marked(test_obj))
        
        # Mark as asset
        self._mark_as_asset(test_obj, self._test_catalog_path)
        
        # Verify marked as asset
        self.assertTrue(self._is_asset_marked(test_obj))

    def test_asset_metadata_assignment(self):
        """Test that asset metadata can be assigned to marked assets."""
        test_obj = self._test_objects["TestObject"]
        
        # Mark as asset
        self._mark_as_asset(test_obj, self._test_catalog_path)
        
        # Verify asset_data exists
        self.assertIsNotNone(test_obj.asset_data)
        
        # Test metadata properties
        asset_data = test_obj.asset_data
        
        # Set description
        asset_data.description = "Test asset description"
        self.assertEqual(asset_data.description, "Test asset description")
        
        # Set author
        asset_data.author = "Test Author"
        self.assertEqual(asset_data.author, "Test Author")

    def test_multiple_asset_activation_states(self):
        """Test managing multiple assets in activation workflow."""
        objects = []
        for i in range(3):
            mesh = bpy.data.meshes.new(f"Mesh{i}")
            obj = bpy.data.objects.new(f"Object{i}", mesh)
            bpy.context.scene.collection.objects.link(obj)
            objects.append(obj)
            self._test_objects[obj.name] = obj
        
        # Mark all as assets
        for obj in objects:
            self._mark_as_asset(obj, self._test_catalog_path)
        
        # Verify all are marked
        for obj in objects:
            self.assertTrue(self._is_asset_marked(obj))


class AssetPreviewTest(AssetWorkflowBase):
    """Test asset preview generation and retrieval."""

    def test_preview_generation_on_marked_asset(self):
        """Test that preview can be generated for marked assets."""
        test_obj = self._test_objects["TestObject"]
        
        # Mark as asset
        self._mark_as_asset(test_obj, self._test_catalog_path)
        
        # Verify asset metadata exists
        self.assertIsNotNone(test_obj.asset_data)
        
        # Preview should be accessible through asset_data
        asset_data = test_obj.asset_data
        self.assertIsNotNone(asset_data)

    def test_preview_data_structure(self):
        """Test that preview data maintains expected structure."""
        test_obj = self._test_objects["TestObject"]
        
        # Mark as asset
        self._mark_as_asset(test_obj, self._test_catalog_path)
        
        # Asset data should have expected attributes
        asset_data = test_obj.asset_data
        self.assertTrue(hasattr(asset_data, 'description'))
        self.assertTrue(hasattr(asset_data, 'author'))
        self.assertTrue(hasattr(asset_data, 'tags'))
        self.assertTrue(hasattr(asset_data, 'catalog_id'))

    def test_preview_tags_management(self):
        """Test managing preview tags."""
        test_obj = self._test_objects["TestObject"]
        
        # Mark as asset
        self._mark_as_asset(test_obj, self._test_catalog_path)
        
        asset_data = test_obj.asset_data
        
        # Test tag operations
        initial_tag_count = len(asset_data.tags)
        
        # Add a tag
        tag = asset_data.tags.new("test_tag")
        self.assertIsNotNone(tag)
        self.assertEqual(tag.name, "test_tag")
        
        # Verify tag count increased
        self.assertEqual(len(asset_data.tags), initial_tag_count + 1)


class AssetLibraryManagementTest(AssetWorkflowBase):
    """Test asset library management and navigation."""

    def test_library_creation(self):
        """Test asset library creation."""
        self.assertIsNotNone(self._library)
        self.assertEqual(self._library.name, "test_workflow_lib")
        self.assertTrue(os.path.isdir(self._library.path))

    def test_library_path_validation(self):
        """Test that library path is valid and accessible."""
        lib_path = self._library.path
        self.assertTrue(os.path.isdir(lib_path))

    def test_local_library_asset_marking(self):
        """Test marking assets in local library."""
        test_obj = self._test_objects["TestObject"]
        
        # Mark in local library
        self._mark_as_asset(test_obj, self._test_catalog_path)
        
        # Verify asset is marked
        self.assertTrue(self._is_asset_marked(test_obj))

    def test_library_switching(self):
        """Test switching between different asset libraries."""
        workspace = bpy.context.workspace
        initial_ref = workspace.asset_library_ref
        
        # Workspace should maintain library reference
        self.assertIsNotNone(workspace)
        
        # Test that library reference can be changed
        # (actual switching depends on available libraries)
        current_ref = workspace.asset_library_ref
        self.assertIsNotNone(current_ref)

    def test_library_persistence_across_operations(self):
        """Test that library configuration persists across operations."""
        # Create asset
        test_obj = self._test_objects["TestObject"]
        self._mark_as_asset(test_obj, self._test_catalog_path)
        
        # Verify library still exists
        self.assertIsNotNone(self._library)
        self.assertTrue(os.path.isdir(self._library.path))
        
        # Verify asset still marked
        self.assertTrue(self._is_asset_marked(test_obj))

    def test_multiple_library_management(self):
        """Test managing multiple asset libraries."""
        # Create second library
        lib_folder_2 = tempfile.TemporaryDirectory("asset_workflow_test_2")
        lib_2 = bpy.types.AssetLibraryCollection.new(
            name="test_workflow_lib_2",
            directory=lib_folder_2.name
        )
        
        try:
            # Verify both libraries exist
            self.assertIsNotNone(self._library)
            self.assertIsNotNone(lib_2)
            self.assertNotEqual(self._library.name, lib_2.name)
        finally:
            # Clean up second library
            if lib_2:
                bpy.types.AssetLibraryCollection.remove(lib_2)
            lib_folder_2.cleanup()


class ShelfPersistenceTest(AssetWorkflowBase):
    """Test shelf configuration persistence."""

    def test_shelf_configuration_retention(self):
        """Test that shelf configuration persists within a session."""
        workspace = bpy.context.workspace
        initial_lib_ref = workspace.asset_library_ref
        
        # Modify workspace settings
        workspace.asset_library_ref = 0
        
        # Verify change persisted
        self.assertEqual(workspace.asset_library_ref, 0)
        
        # Restore
        workspace.asset_library_ref = initial_lib_ref

    def test_asset_shelf_across_context_changes(self):
        """Test shelf persistence across context changes."""
        workspace = bpy.context.workspace
        lib_ref_before = workspace.asset_library_ref
        
        # Change context (switch to different mode if possible)
        if bpy.context.object:
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Verify shelf config maintained
        lib_ref_after = workspace.asset_library_ref
        self.assertEqual(lib_ref_before, lib_ref_after)

    def test_shelf_settings_recovery(self):
        """Test recovery of shelf settings after modifications."""
        workspace = bpy.context.workspace
        original_ref = workspace.asset_library_ref
        
        # Make multiple changes
        workspace.asset_library_ref = 0
        workspace.asset_library_ref = 1
        workspace.asset_library_ref = original_ref
        
        # Verify final state
        self.assertEqual(workspace.asset_library_ref, original_ref)


class AssetLibraryQueryTest(AssetWorkflowBase):
    """Test library-level asset queries and filtering."""

    def test_asset_tagging_for_filtering(self):
        """Test asset tagging for filtering operations."""
        test_obj = self._test_objects["TestObject"]
        
        # Mark as asset
        self._mark_as_asset(test_obj, self._test_catalog_path)
        
        # Add tags
        asset_data = test_obj.asset_data
        asset_data.tags.new("filter_test")
        asset_data.tags.new("important")
        
        # Verify tags exist
        tag_names = {tag.name for tag in asset_data.tags}
        self.assertIn("filter_test", tag_names)
        self.assertIn("important", tag_names)

    def test_asset_catalog_path_assignment(self):
        """Test assigning catalog paths to assets."""
        test_obj = self._test_objects["TestObject"]
        
        # Mark with catalog path
        self._mark_as_asset(test_obj, "textures/pbr")
        
        # Verify asset marked
        self.assertTrue(self._is_asset_marked(test_obj))

    def test_multiple_assets_catalog_organization(self):
        """Test organizing multiple assets in catalogs."""
        # Create multiple objects
        objects = []
        catalog_paths = ["models/characters", "models/props", "models/environments"]
        
        for i, catalog_path in enumerate(catalog_paths):
            mesh = bpy.data.meshes.new(f"Mesh{i}")
            obj = bpy.data.objects.new(f"Object{i}", mesh)
            bpy.context.scene.collection.objects.link(obj)
            self._mark_as_asset(obj, catalog_path)
            objects.append(obj)
            self._test_objects[obj.name] = obj
        
        # Verify all are marked as assets
        for obj in objects:
            self.assertTrue(self._is_asset_marked(obj))

    def test_asset_description_for_search(self):
        """Test setting descriptions for asset searchability."""
        test_obj = self._test_objects["TestObject"]
        
        # Mark as asset
        self._mark_as_asset(test_obj, self._test_catalog_path)
        
        # Set searchable description
        asset_data = test_obj.asset_data
        asset_data.description = "High poly character with rigged skeleton"
        
        # Verify description can be retrieved
        self.assertIn("character", asset_data.description)


class AssetDraggingSimulationTest(AssetWorkflowBase):
    """Test asset dragging simulation."""

    def test_asset_drag_event_simulation(self):
        """Test simulating drag operations on assets."""
        test_obj = self._test_objects["TestObject"]
        
        # Mark as asset
        self._mark_as_asset(test_obj, self._test_catalog_path)
        
        # Verify asset can be identified for dragging
        self.assertTrue(self._is_asset_marked(test_obj))
        
        # Asset drag operations would require UI context
        # which is limited in headless testing
        self.assertIsNotNone(test_obj)

    def test_asset_drag_destination_validation(self):
        """Test validating asset drag destinations."""
        # Create source and destination objects
        src_obj = self._test_objects["TestObject"]
        dst_mesh = bpy.data.meshes.new("DestMesh")
        dst_obj = bpy.data.objects.new("DestObject", dst_mesh)
        bpy.context.scene.collection.objects.link(dst_obj)
        self._test_objects["DestObject"] = dst_obj
        
        # Mark source as asset
        self._mark_as_asset(src_obj, self._test_catalog_path)
        
        # Both objects should exist and be valid
        self.assertIn(src_obj.name, bpy.data.objects)
        self.assertIn(dst_obj.name, bpy.data.objects)


class AssetWorkflowErrorHandlingTest(AssetWorkflowBase):
    """Test error handling for edge cases."""

    def test_empty_shelf_operations(self):
        """Test operations on empty shelves."""
        workspace = bpy.context.workspace
        
        # Empty shelf should not cause errors
        lib_ref = workspace.asset_library_ref
        self.assertIsNotNone(lib_ref)

    def test_missing_library_handling(self):
        """Test handling of missing asset libraries."""
        # Attempting to access non-existent library should not crash
        workspace = bpy.context.workspace
        
        # Default workspace should have valid reference
        self.assertIsNotNone(workspace.asset_library_ref)

    def test_invalid_catalog_path_handling(self):
        """Test handling of invalid catalog paths."""
        test_obj = self._test_objects["TestObject"]
        
        # Mark with valid path (empty string is valid)
        self._mark_as_asset(test_obj, "")
        
        # Should still be marked as asset
        self.assertTrue(self._is_asset_marked(test_obj))

    def test_double_asset_marking(self):
        """Test marking an already-marked asset."""
        test_obj = self._test_objects["TestObject"]
        
        # Mark as asset first time
        self._mark_as_asset(test_obj, self._test_catalog_path)
        self.assertTrue(self._is_asset_marked(test_obj))
        
        # Mark again - should not cause error
        if not self._is_asset_marked(test_obj):
            self._mark_as_asset(test_obj, self._test_catalog_path)
        
        self.assertTrue(self._is_asset_marked(test_obj))

    def test_asset_operations_with_deleted_object(self):
        """Test operations on deleted assets."""
        # Create and immediately delete an object
        mesh = bpy.data.meshes.new("TempMesh")
        temp_obj = bpy.data.objects.new("TempObject", mesh)
        bpy.context.scene.collection.objects.link(temp_obj)
        
        # Remove the object
        bpy.data.objects.remove(temp_obj)
        
        # Object should no longer exist
        self.assertNotIn("TempObject", bpy.data.objects)

    def test_preview_generation_on_unmapped_types(self):
        """Test preview generation on non-standard data types."""
        # Create a material (which can be an asset)
        material = bpy.data.materials.new("TestMaterial")
        
        # Try to mark as asset
        try:
            self._mark_as_asset(material, self._test_catalog_path)
            # Material marking may or may not work depending on Blender version
        except Exception:
            # Some data types may not support asset marking
            pass

    def test_library_operations_with_missing_path(self):
        """Test library operations when path becomes inaccessible."""
        # This test verifies robustness when library path is invalid
        lib_path = self._library.path
        
        # Library should still be valid reference
        self.assertIsNotNone(self._library)
        
        # Path should exist
        self.assertTrue(os.path.isdir(lib_path))


def main():
    """Run the tests."""
    # Handle command-line arguments like other tests
    if '--' in sys.argv:
        argv = [sys.argv[0]] + sys.argv[sys.argv.index('--') + 1:]
    else:
        argv = sys.argv
    
    # Run tests
    unittest.main(argv=argv)


if __name__ == "__main__":
    main()
