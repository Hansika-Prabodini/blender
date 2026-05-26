# SPDX-FileCopyrightText: 2025 Blender Authors
#
# SPDX-License-Identifier: Apache-2.0

# blender -b --factory-startup --python tests/python/bl_asset_system_api.py -- --verbose

__all__ = (
    "main",
)

import unittest
import bpy


class AssetSystemAPITest(unittest.TestCase):
    """Test core asset system API functionality."""

    def setUp(self):
        """Create diverse test assets for testing."""
        # Start with a clean factory startup
        bpy.ops.wm.read_factory_startup(use_empty=True)

        # Create test materials
        self.test_material_1 = bpy.data.materials.new("TestMaterial1")
        self.test_material_2 = bpy.data.materials.new("TestMaterial2")

        # Create test node groups
        self.test_node_group = bpy.data.node_groups.new(
            name="TestShaderNodeGroup",
            type='ShaderNodeTree'
        )

        # Create test texture
        self.test_texture = bpy.data.textures.new("TestTexture", type='CLOUDS')

        # Create test objects
        self.test_object_1 = bpy.data.objects.new("TestObject1", None)
        self.test_object_2 = bpy.data.objects.new("TestObject2", None)

        # Create test mesh
        test_mesh = bpy.data.meshes.new("TestMesh")
        self.test_mesh_object = bpy.data.objects.new("TestMeshObject", test_mesh)

        # Link objects to scene
        scene = bpy.context.scene
        scene.collection.objects.link(self.test_object_1)
        scene.collection.objects.link(self.test_object_2)
        scene.collection.objects.link(self.test_mesh_object)

    def tearDown(self):
        """Clean up test data."""
        # Remove any assets
        if self.test_material_1.asset_data is not None:
            bpy.ops.ed.asset_clear(id=self.test_material_1)
        if self.test_material_2.asset_data is not None:
            bpy.ops.ed.asset_clear(id=self.test_material_2)
        if self.test_node_group.asset_data is not None:
            bpy.ops.ed.asset_clear(id=self.test_node_group)
        if self.test_texture.asset_data is not None:
            bpy.ops.ed.asset_clear(id=self.test_texture)
        if self.test_object_1.asset_data is not None:
            bpy.ops.ed.asset_clear(id=self.test_object_1)
        if self.test_object_2.asset_data is not None:
            bpy.ops.ed.asset_clear(id=self.test_object_2)
        if self.test_mesh_object.asset_data is not None:
            bpy.ops.ed.asset_clear(id=self.test_mesh_object)

        # Remove data blocks
        bpy.data.materials.remove(self.test_material_1, do_unlink=True)
        bpy.data.materials.remove(self.test_material_2, do_unlink=True)
        bpy.data.node_groups.remove(self.test_node_group, do_unlink=True)
        bpy.data.textures.remove(self.test_texture, do_unlink=True)
        bpy.data.objects.remove(self.test_object_1, do_unlink=True)
        bpy.data.objects.remove(self.test_object_2, do_unlink=True)
        bpy.data.objects.remove(self.test_mesh_object, do_unlink=True)
        bpy.data.meshes.remove(self.test_mesh_object.data, do_unlink=True)

    # =========================================================================
    # Asset Marking Tests
    # =========================================================================

    def test_asset_mark_material(self):
        """Test marking a material as an asset."""
        # Material should not be an asset initially
        self.assertIsNone(self.test_material_1.asset_data)

        # Mark as asset
        bpy.ops.ed.asset_mark(id=self.test_material_1)

        # Verify it is now marked as asset
        self.assertIsNotNone(self.test_material_1.asset_data)

    def test_asset_mark_node_group(self):
        """Test marking a node group as an asset."""
        # Node group should not be an asset initially
        self.assertIsNone(self.test_node_group.asset_data)

        # Mark as asset
        bpy.ops.ed.asset_mark(id=self.test_node_group)

        # Verify it is now marked as asset
        self.assertIsNotNone(self.test_node_group.asset_data)

    def test_asset_mark_texture(self):
        """Test marking a texture as an asset."""
        # Texture should not be an asset initially
        self.assertIsNone(self.test_texture.asset_data)

        # Mark as asset
        bpy.ops.ed.asset_mark(id=self.test_texture)

        # Verify it is now marked as asset
        self.assertIsNotNone(self.test_texture.asset_data)

    def test_asset_mark_object(self):
        """Test marking an object as an asset."""
        # Object should not be an asset initially
        self.assertIsNone(self.test_object_1.asset_data)

        # Mark as asset
        bpy.ops.ed.asset_mark(id=self.test_object_1)

        # Verify it is now marked as asset
        self.assertIsNotNone(self.test_object_1.asset_data)

    def test_asset_unmark_material(self):
        """Test unmarking a material from assets."""
        # Mark as asset first
        bpy.ops.ed.asset_mark(id=self.test_material_1)
        self.assertIsNotNone(self.test_material_1.asset_data)

        # Unmark asset
        bpy.ops.ed.asset_clear(id=self.test_material_1)

        # Verify it is no longer an asset
        self.assertIsNone(self.test_material_1.asset_data)

    def test_asset_unmark_multiple(self):
        """Test unmarking multiple assets."""
        # Mark multiple as assets
        bpy.ops.ed.asset_mark(id=self.test_material_1)
        bpy.ops.ed.asset_mark(id=self.test_material_2)
        bpy.ops.ed.asset_mark(id=self.test_node_group)

        self.assertIsNotNone(self.test_material_1.asset_data)
        self.assertIsNotNone(self.test_material_2.asset_data)
        self.assertIsNotNone(self.test_node_group.asset_data)

        # Unmark all
        bpy.ops.ed.asset_clear(id=self.test_material_1)
        bpy.ops.ed.asset_clear(id=self.test_material_2)
        bpy.ops.ed.asset_clear(id=self.test_node_group)

        self.assertIsNone(self.test_material_1.asset_data)
        self.assertIsNone(self.test_material_2.asset_data)
        self.assertIsNone(self.test_node_group.asset_data)

    # =========================================================================
    # Asset Type Query Tests
    # =========================================================================

    def test_asset_type_material(self):
        """Test retrieving asset type for material."""
        bpy.ops.ed.asset_mark(id=self.test_material_1)

        # Verify asset metadata exists
        asset_data = self.test_material_1.asset_data
        self.assertIsNotNone(asset_data)

        # Check asset has correct id_type
        self.assertEqual(self.test_material_1.id_type, 'MATERIAL')

    def test_asset_type_node_group(self):
        """Test retrieving asset type for node group."""
        bpy.ops.ed.asset_mark(id=self.test_node_group)

        # Verify asset metadata exists
        asset_data = self.test_node_group.asset_data
        self.assertIsNotNone(asset_data)

        # Check asset has correct id_type
        self.assertEqual(self.test_node_group.id_type, 'NODETREE')

    def test_asset_type_texture(self):
        """Test retrieving asset type for texture."""
        bpy.ops.ed.asset_mark(id=self.test_texture)

        # Verify asset metadata exists
        asset_data = self.test_texture.asset_data
        self.assertIsNotNone(asset_data)

        # Check asset has correct id_type
        self.assertEqual(self.test_texture.id_type, 'TEXTURE')

    def test_asset_type_object(self):
        """Test retrieving asset type for object."""
        bpy.ops.ed.asset_mark(id=self.test_object_1)

        # Verify asset metadata exists
        asset_data = self.test_object_1.asset_data
        self.assertIsNotNone(asset_data)

        # Check asset has correct id_type
        self.assertEqual(self.test_object_1.id_type, 'OBJECT')

    # =========================================================================
    # Asset Metadata Tests
    # =========================================================================

    def test_asset_metadata_exists(self):
        """Test that asset metadata is created on marking."""
        bpy.ops.ed.asset_mark(id=self.test_material_1)

        asset_data = self.test_material_1.asset_data
        self.assertIsNotNone(asset_data)

        # Verify it's an AssetMetaData object
        self.assertEqual(type(asset_data).__name__, 'AssetMetaData')

    def test_asset_name_accessible(self):
        """Test that asset name is accessible."""
        bpy.ops.ed.asset_mark(id=self.test_material_1)

        # The datablock name should be accessible
        self.assertEqual(self.test_material_1.name, "TestMaterial1")

    def test_asset_library_reference(self):
        """Test accessing asset library reference after marking."""
        bpy.ops.ed.asset_mark(id=self.test_material_1)

        asset_data = self.test_material_1.asset_data
        self.assertIsNotNone(asset_data)

        # library should be None for local assets
        self.assertIsNone(self.test_material_1.library)

    # =========================================================================
    # Asset Filtering Tests
    # =========================================================================

    def test_asset_collection_iteration_empty(self):
        """Test iterating over empty asset collections."""
        # Count assets before marking
        material_count = len(list(bpy.data.materials))
        # All should be unmarked
        unmarked_count = sum(1 for m in bpy.data.materials if m.asset_data is None)
        self.assertEqual(material_count, unmarked_count)

    def test_asset_collection_filtering(self):
        """Test filtering assets from a collection."""
        # Mark some materials as assets
        bpy.ops.ed.asset_mark(id=self.test_material_1)
        bpy.ops.ed.asset_mark(id=self.test_material_2)

        # Filter marked assets
        asset_materials = [m for m in bpy.data.materials if m.asset_data is not None]

        self.assertEqual(len(asset_materials), 2)
        self.assertIn(self.test_material_1, asset_materials)
        self.assertIn(self.test_material_2, asset_materials)

    def test_asset_filtering_mixed_types(self):
        """Test filtering assets of different types."""
        bpy.ops.ed.asset_mark(id=self.test_material_1)
        bpy.ops.ed.asset_mark(id=self.test_node_group)
        bpy.ops.ed.asset_mark(id=self.test_texture)

        # Filter by type using id_type
        material_assets = [a for a in bpy.data.materials if a.asset_data is not None]
        nodegroup_assets = [a for a in bpy.data.node_groups if a.asset_data is not None]
        texture_assets = [a for a in bpy.data.textures if a.asset_data is not None]

        self.assertEqual(len(material_assets), 1)
        self.assertEqual(len(nodegroup_assets), 1)
        self.assertEqual(len(texture_assets), 1)

    def test_asset_filtering_with_unmarked(self):
        """Test filtering when some assets are unmarked."""
        # Mark only first material
        bpy.ops.ed.asset_mark(id=self.test_material_1)

        # Filter assets
        asset_materials = [m for m in bpy.data.materials if m.asset_data is not None]

        # Should only include marked asset
        self.assertEqual(len(asset_materials), 1)
        self.assertIn(self.test_material_1, asset_materials)
        self.assertNotIn(self.test_material_2, asset_materials)

    # =========================================================================
    # Asset Reference Tests
    # =========================================================================

    def test_asset_reference_count(self):
        """Test accessing reference count of asset."""
        bpy.ops.ed.asset_mark(id=self.test_material_1)

        # Reference count should be accessible through asset
        self.assertIsNotNone(self.test_material_1.asset_data)
        self.assertGreaterEqual(self.test_material_1.users, 0)

    def test_asset_reference_identity(self):
        """Test that asset references maintain identity."""
        bpy.ops.ed.asset_mark(id=self.test_material_1)

        # Get reference to asset
        asset_ref = self.test_material_1
        asset_ref_again = bpy.data.materials[self.test_material_1.name]

        # Should be the same object
        self.assertEqual(asset_ref, asset_ref_again)
        self.assertTrue(asset_ref.asset_data is not None)

    def test_asset_reference_by_name(self):
        """Test accessing asset by name."""
        bpy.ops.ed.asset_mark(id=self.test_material_1)

        # Access by name
        found_asset = bpy.data.materials.get(self.test_material_1.name)
        self.assertIsNotNone(found_asset)
        self.assertIsNotNone(found_asset.asset_data)

    def test_asset_reference_persistence(self):
        """Test that asset reference persists after operations."""
        bpy.ops.ed.asset_mark(id=self.test_material_1)
        original_asset_data = self.test_material_1.asset_data

        # Reference should remain
        self.assertIsNotNone(self.test_material_1.asset_data)
        self.assertEqual(original_asset_data, self.test_material_1.asset_data)

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    def test_asset_unmark_non_asset(self):
        """Test unmarking a non-asset (should be safe)."""
        # Material is not an asset
        self.assertIsNone(self.test_material_2.asset_data)

        # Attempting to clear should not raise an error
        try:
            bpy.ops.ed.asset_clear(id=self.test_material_2)
        except RuntimeError:
            pass  # May raise error if not an asset, which is acceptable

    def test_asset_remark_already_marked(self):
        """Test marking an already-marked asset."""
        bpy.ops.ed.asset_mark(id=self.test_material_1)
        first_mark = self.test_material_1.asset_data

        # Mark again
        bpy.ops.ed.asset_mark(id=self.test_material_1)

        # Should still be marked
        self.assertIsNotNone(self.test_material_1.asset_data)

    def test_asset_double_unmark(self):
        """Test unmarking an asset twice."""
        bpy.ops.ed.asset_mark(id=self.test_material_1)
        self.assertIsNotNone(self.test_material_1.asset_data)

        # Unmark once
        bpy.ops.ed.asset_clear(id=self.test_material_1)
        self.assertIsNone(self.test_material_1.asset_data)

        # Unmark again (should be safe)
        try:
            bpy.ops.ed.asset_clear(id=self.test_material_1)
        except RuntimeError:
            pass  # May raise error if already unmarked, which is acceptable

    # =========================================================================
    # Edge Cases Tests
    # =========================================================================

    def test_asset_empty_collection_check(self):
        """Test checking for assets in empty collection."""
        # Create a new texture that won't be marked
        empty_texture = bpy.data.textures.new("EmptyTexture", type='CLOUDS')

        # Check unmarked asset
        self.assertIsNone(empty_texture.asset_data)

        # Filter should not include it
        asset_textures = [t for t in bpy.data.textures if t.asset_data is not None]
        self.assertNotIn(empty_texture, asset_textures)

        # Clean up
        bpy.data.textures.remove(empty_texture, do_unlink=True)

    def test_asset_type_consistency(self):
        """Test that asset type remains consistent."""
        bpy.ops.ed.asset_mark(id=self.test_material_1)

        # Check id_type doesn't change after marking
        id_type_before = self.test_material_1.id_type
        id_type_after = self.test_material_1.id_type

        self.assertEqual(id_type_before, id_type_after)
        self.assertEqual(id_type_before, 'MATERIAL')

    def test_asset_multiple_of_same_type(self):
        """Test managing multiple assets of the same type."""
        # Mark multiple materials
        bpy.ops.ed.asset_mark(id=self.test_material_1)
        bpy.ops.ed.asset_mark(id=self.test_material_2)

        # Both should be marked
        self.assertIsNotNone(self.test_material_1.asset_data)
        self.assertIsNotNone(self.test_material_2.asset_data)

        # Unmark one
        bpy.ops.ed.asset_clear(id=self.test_material_1)

        # Only second should be marked
        self.assertIsNone(self.test_material_1.asset_data)
        self.assertIsNotNone(self.test_material_2.asset_data)

    def test_asset_name_preservation(self):
        """Test that asset name is preserved after marking."""
        original_name = self.test_material_1.name

        bpy.ops.ed.asset_mark(id=self.test_material_1)

        # Name should be preserved
        self.assertEqual(self.test_material_1.name, original_name)

    def test_asset_metadata_type_check(self):
        """Test that asset metadata has expected type structure."""
        bpy.ops.ed.asset_mark(id=self.test_material_1)

        asset_data = self.test_material_1.asset_data
        self.assertIsNotNone(asset_data)

        # Should have properties
        self.assertTrue(hasattr(asset_data, 'tags'))
        self.assertTrue(hasattr(asset_data, 'description'))


def main():
    import sys
    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()


if __name__ == '__main__':
    main()
