# SPDX-FileCopyrightText: 2024 Blender Authors
#
# SPDX-License-Identifier: Apache-2.0

# ./blender.bin --background --python tests/python/bl_pyapi_bpy_extras_mesh_utils.py -- --verbose
import unittest


class TestNgonTessellate(unittest.TestCase):
    """Tests for bpy_extras.mesh_utils.ngon_tessellate."""

    def test_simple_quad_no_duplicates(self):
        """A clean quad (4 unique verts) should tessellate into 2 triangles."""
        from bpy_extras.mesh_utils import ngon_tessellate

        # Diamond-shaped quad with no duplicate consecutive vertices.
        verts = [
            (0.0, 5.0, 0.0),
            (2.0, 7.0, 0.0),
            (0.0, 9.0, 0.0),
            (-2.0, 7.0, 0.0),
        ]
        indices = list(range(len(verts)))

        result = ngon_tessellate(verts, indices, fix_loops=False, debug_print=False)

        # A quad always tessellates into exactly 2 triangles.
        self.assertEqual(len(result), 2)
        # Every face must be a triangle.
        for face in result:
            self.assertEqual(len(face), 3)

    def test_quad_with_consecutive_duplicate_vertex(self):
        """A quad where one vertex appears twice consecutively should still
        tessellate into 2 triangles after the duplicate is removed.

        This test catches the bug where the dedup loop used the wrong vector
        component indices (``verts[i][1] == verts[i - 1][0]``, i.e. Y vs X)
        instead of comparing whole vectors (``verts[i] == verts[i - 1]``).
        With the bug the duplicate was not removed, leaving 5 vertices that
        tessellate into 3 triangles instead of 2.
        """
        from bpy_extras.mesh_utils import ngon_tessellate

        # Same diamond shape as above, but vertex at index 1 is duplicated.
        # Using coordinates where y != x for all vertices to ensure the buggy
        # comparison (y_i == x_{i-1}) cannot accidentally match non-duplicates.
        verts = [
            (0.0, 5.0, 0.0),
            (2.0, 7.0, 0.0),  # duplicate starts here …
            (2.0, 7.0, 0.0),  # … and here
            (0.0, 9.0, 0.0),
            (-2.0, 7.0, 0.0),
        ]
        indices = list(range(len(verts)))

        result = ngon_tessellate(verts, indices, fix_loops=False, debug_print=False)

        # After removing the consecutive duplicate the polygon is a quad → 2 triangles.
        self.assertEqual(len(result), 2)
        for face in result:
            self.assertEqual(len(face), 3)


if __name__ == '__main__':
    import sys

    sys.argv = [__file__] + (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    unittest.main()
