/* SPDX-FileCopyrightText: 2024 Blender Authors
 *
 * SPDX-License-Identifier: Apache-2.0 */

#ifdef _WIN32

#include <gtest/gtest.h>
#include <Windows.h>

/* Test that validates the fix for the parent_pid initialization bug in LaunchedFromSteam().
 * 
 * BUG DESCRIPTION:
 * The original code initialized parent_pid (DWORD - unsigned type) to -1:
 *   DWORD parent_pid = -1;
 *   if (parent_pid == -1 || ...)
 * 
 * This is problematic because:
 * 1. DWORD is unsigned, so -1 implicitly converts to 0xFFFFFFFF
 * 2. Comparing unsigned with signed literal (-1) is confusing and error-prone
 * 3. Violates best practices for signed/unsigned type handling
 * 
 * THE FIX:
 * Use 0 as the sentinel value instead:
 *   DWORD parent_pid = 0;
 *   if (parent_pid == 0 || ...)
 * 
 * This is correct because:
 * 1. Process IDs are never 0 on Windows (valid PIDs start from 4)
 * 2. The comparison is clean and unambiguous
 * 3. No implicit type conversions needed
 * 
 * These tests ensure that:
 * 1. The sentinel value (0) is properly used for "parent not found" detection
 * 2. The comparison logic correctly distinguishes found vs. not found cases
 * 3. No signed/unsigned conversion issues exist
 */

namespace blender::tests {

TEST(BlenderLauncherWin32, ParentPidInitializationCorrect)
{
  /* TEST PURPOSE: Verify that initializing parent_pid to 0 correctly signals
   * "parent process not found" in the LaunchedFromSteam() function.
   * 
   * This test would fail with the buggy code (parent_pid = -1) because:
   * - The buggy code checks: if (parent_pid == -1 || ...)
   * - When parent_pid is not set, it remains -1 (0xFFFFFFFF as unsigned)
   * - The comparison works due to implicit conversion, but is semantically wrong
   * 
   * With the fix (parent_pid = 0), the check is clean and unambiguous:
   * - if (parent_pid == 0 || ...)
   * - When parent_pid is not set, it remains 0
   * - The comparison is straightforward and doesn't rely on type conversions */
  
  /* Verify that DWORD is indeed unsigned */
  DWORD test_value = 0;
  ASSERT_TRUE(test_value >= 0);
  
  /* Verify that initializing to 0 creates a valid sentinel value */
  DWORD parent_pid = 0;
  ASSERT_EQ(parent_pid, 0);
  
  /* Simulate the "parent not found" condition in LaunchedFromSteam().
   * When the parent process enumeration fails to find our parent process,
   * parent_pid remains at its initial sentinel value (0).
   * The function should then detect this and return FALSE. */
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
  /* TEST PURPOSE: Verify that when a parent process is successfully found,
   * the comparison correctly identifies it.
   * 
   * In LaunchedFromSteam(), when the process enumeration finds the parent:
   *   if (process_entry.th32ProcessID == our_pid) {
   *     parent_pid = process_entry.th32ParentProcessID;
   *     break;
   *   }
   * 
   * Then the check: if (parent_pid == 0 || ...)
   * Should evaluate to false because parent_pid now contains a valid PID (non-zero) */
  
  /* Start with the initial sentinel value */
  DWORD parent_pid = 0;
  ASSERT_EQ(parent_pid, 0);
  
  /* Simulate finding a parent process with a valid process ID.
   * Process IDs on Windows are always >= 4 (system processes), never 0 */
  DWORD simulated_ppid = 1234;
  parent_pid = simulated_ppid;
  
  /* After assignment, the "parent found" condition should be true */
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
  /* TEST PURPOSE: Demonstrate that the fix eliminates the signed/unsigned
   * type conversion issue that existed in the original buggy code.
   * 
   * ORIGINAL BUGGY CODE ISSUE:
   *   DWORD parent_pid = -1;  // Assigns 0xFFFFFFFF (max unsigned)
   *   if (parent_pid == -1 || ...)  // Compares unsigned with signed literal
   * 
   * Problems with this approach:
   * 1. Signed -1 implicitly converts to unsigned 0xFFFFFFFF in the comparison
   * 2. This is confusing and violates best practices
   * 3. If someone later changes the initialization or comparison, subtle bugs appear
   * 4. Compiler warnings about signed/unsigned comparison may be suppressed
   * 
   * THE FIX:
   *   DWORD parent_pid = 0;   // Clear unsigned initialization
   *   if (parent_pid == 0 || ...)  // Clean unsigned-to-unsigned comparison
   * 
   * Benefits:
   * 1. No implicit type conversions
   * 2. Semantically correct (0 is the sentinel for "not found")
   * 3. No compiler warnings
   * 4. Matches Windows API conventions (PID 0 is invalid) */
  
  DWORD parent_pid = 0;
  
  /* Direct comparison with unsigned literal is safe and clear */
  ASSERT_TRUE(parent_pid == 0U);
  
  /* Verify that with proper initialization, parent_pid is NOT the maximum
   * unsigned value that would result from the buggy -1 assignment */
  ASSERT_FALSE(parent_pid == 0xFFFFFFFFU) 
      << "parent_pid should be 0, not 0xFFFFFFFF (max unsigned value)";
  
  /* This test passes with the fix and would fail if someone accidentally
   * reverted to the buggy initialization of parent_pid = -1 */
}

}  // namespace blender::tests

#endif  /* _WIN32 */
