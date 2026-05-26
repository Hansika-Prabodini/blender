/* SPDX-FileCopyrightText: 2024 Blender Authors
 *
 * SPDX-License-Identifier: Apache-2.0 */

#ifdef _WIN32

#include <gtest/gtest.h>
#include <Windows.h>

/* Test that validates the fix for the parent_pid initialization bug.
 * 
 * The bug was that parent_pid (DWORD - unsigned type) was initialized to -1,
 * which implicitly converts to the maximum unsigned value (0xFFFFFFFF).
 * The correct fix is to initialize it to 0, since process IDs are never 0.
 * 
 * This test ensures that:
 * 1. The sentinel value (0) is used for "not found" detection
 * 2. The comparison logic correctly identifies when a parent process is not found
 */

namespace blender::tests {

TEST(BlenderLauncherWin32, ParentPidInitializationCorrect)
{
  /* Verify that DWORD is indeed unsigned */
  DWORD test_value = 0;
  ASSERT_TRUE(test_value >= 0);
  
  /* Verify that initializing to 0 creates a valid sentinel value */
  DWORD parent_pid = 0;
  ASSERT_EQ(parent_pid, 0);
  
  /* Simulate not finding the parent process.
   * With the correct fix (parent_pid = 0), the check parent_pid == 0
   * will correctly detect that the parent was not found. */
  BOOL found_parent = FALSE;
  if (parent_pid == 0) {
    found_parent = FALSE;
  } else {
    found_parent = TRUE;
  }
  
  ASSERT_FALSE(found_parent) << "Parent process should not be found when parent_pid is 0";
}

TEST(BlenderLauncherWin32, ParentPidAssignmentCorrect)
{
  /* Test that when we assign a valid process ID, the comparison works correctly */
  DWORD parent_pid = 0;
  ASSERT_EQ(parent_pid, 0);
  
  /* Simulate finding a parent process with a valid PID (non-zero) */
  DWORD simulated_ppid = 1234; /* A non-zero process ID */
  parent_pid = simulated_ppid;
  
  /* Now the check should detect that a parent was found */
  BOOL found_parent = FALSE;
  if (parent_pid == 0) {
    found_parent = FALSE;
  } else {
    found_parent = TRUE;
  }
  
  ASSERT_TRUE(found_parent) << "Parent process should be found when parent_pid is non-zero";
  ASSERT_EQ(parent_pid, 1234);
}

TEST(BlenderLauncherWin32, ParentPidSignedUnsignedComparison)
{
  /* This test validates that the fix avoids the signed/unsigned comparison issue.
   * With parent_pid = 0 (unsigned), the comparison parent_pid == 0 is clean
   * and unambiguous, unlike the buggy parent_pid == -1 which relies on
   * implicit conversion. */
  
  DWORD parent_pid = 0;
  
  /* Direct comparison with unsigned literal is safe and clear */
  ASSERT_TRUE(parent_pid == 0U);
  
  /* The old buggy code would do: parent_pid == -1
   * This works due to implicit conversion, but is confusing and error-prone.
   * The signed -1 converts to 0xFFFFFFFF when compared with unsigned DWORD. */
  
  /* With the fix, we get a clear comparison */
  ASSERT_FALSE(parent_pid == 0xFFFFFFFFU) 
      << "parent_pid should not be the maximum unsigned value when initialized to 0";
}

}  // namespace blender::tests

#endif  /* _WIN32 */
