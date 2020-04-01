import io
import os
import pavilion
import time

from pavilion import arguments
from pavilion import commands
from pavilion import plugins
from pavilion.status_file import STATES
from pavilion import system_variables
from pavilion.test_config import variables, VariableSetManager
from pavilion.test_run import TestRun, TestRunError, TestConfigError
from pavilion import unittest
from pavilion.builder import MultiBuildTracker


class conditionalTest(unittest.PavTestCase):

    def setUp(self):
        plugins.initialize_plugins(self.pav_cfg)

    def tearDown(self):
        plugins._reset_plugins()

    def test_no_skip(self):  # this method runs some conditional successes
        test_list = []
        base_cfg = self._quick_test_cfg()
        base_cfg['variables'] = {'person': ['calvin'],
                                 'machine': ['bieber']}

        # The following sections of only_if and not_if consist of
        # permutations to check that all tests pass. These tests
        # check the logic of _match in different scenarios.

        # Test 1:
        # Neither not_if or only_if exist.
        test_cfg = base_cfg.copy()
        test_list.append(test_cfg)

        # Test 2:
        # Not_if with no match, only_if with two matches.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'person': ['bleh', 'notcalvin'],
                              'machine': ['notbieber', 'foo']}
        test_cfg['only_if'] = {'machine': ['notbieber', 'bieber'],
                               'person': ['notcalvin', 'calvin']}
        test_list.append(test_cfg)

        # Test 3:
        # No not_if, only_if has match in second position.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {}
        test_cfg['only_if'] = {'person': ['nivlac', 'calvin']}
        test_list.append(test_cfg)

        # Test 4:
        # No only_if, not_if exists with no match.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'person': ['nivlac', 'notcalvin'],
                              'machine': ['blurg']}
        test_cfg['only_if'] = {}
        test_list.append(test_cfg)

        # Run all 4 tests, all should have skip equal to false.
        for test_cfg in test_list:
            test = self._quick_test(cfg=test_cfg)
            test.run()
            self.assertFalse(test.skipped, msg="None of the tests"
                                               "should be skipped.")

    def test_skip(self):  # this method runs skip conditions
        test_list = []
        base_cfg = self._quick_test_cfg()
        base_cfg['variables'] = {'person': ['calvin'],
                                 'machine': ['bieber']}

        # The following sections of only_if and not_if consist of
        # permutations to check that all tests are skipped. These tests
        # check the logic of _match in different scenarios.

        # Test 1:
        # No matches for not_if but only_if 1/2 match.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'person': ['bleh', 'notcalvin'],
                              'machine': ['notbieb']}
        test_cfg['only_if'] = {'machine': ['notbieber', 'bleh'],
                               'person': ['calvin']}
        test_list.append(test_cfg)

        # Test 2:
        # No not_if and only_if has 0/1 match.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {}
        test_cfg['only_if'] = {'person': ['nivlac', 'notcalvin']}
        test_list.append(test_cfg)

        # Test 3:
        # No only_if, not_if has a match.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'person': ['notcalvin', 'calvin']}
        test_list.append(test_cfg)

        # Test 4:
        # Not_if has 1/2 match and only_if has 2/2 matches.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'machine': ['nivlac', 'notbieber'],
                              'person': ['calvin']}
        test_cfg['only_if'] = {'person': ['nivlac', 'calvin'],
                               'machine': ['bieber']}
        test_list.append(test_cfg)

        # Test 5:
        # Not_if has a match and only_if is missing a match.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'machine': ['nivlac', 'notbieber', 'bieber']}
        test_cfg['only_if'] = {'person': ['nivlac', 'calvin'],
                               'machine': ['notbieber']}
        test_list.append(test_cfg)

        # Run all 5 tests, all should have skip equal to true.
        for test_cfg in test_list:
            test = self._quick_test(cfg=test_cfg)
            test.run()
            self.assertTrue(test.skipped, msg="All tests should be skipped.")

    def test_deferred(self):
        # The following tests make sure deferred variables are
        # interpreted correctly by the conditional checks.

        test_list = []
        base_cfg = self._quick_test_cfg()
        base_cfg['variables'] = {'person': ['calvin'],
                                 'machine': ['bieber']}

        # Test 1:
        # Not_if with deferred variable that resolves to skip.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'dumb_sys_var': ['stupid']}
        test_list.append(test_cfg)

        # Test 2:
        # Only_if with deferred variable that resolves to skip.
        test_cfg = base_cfg.copy()
        test_cfg['only_if'] = {'dumb_sys_var': ['notstupid']}
        test_list.append(test_cfg)

        # Test 3:
        # Not_if that fails to skip with deferred only_if that skips.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'person': ['nivlac', 'notcalvin'],
                              'machine': ['blurg']}
        test_cfg['only_if'] = {'dumb_sys_var': ['notstupid']}
        test_list.append(test_cfg)

        # Test 4:
        # Only_if that fails to skip with deferred not_if that skips.
        test_cfg = base_cfg.copy()
        test_cfg['only_if'] = {'person': ['nivlac', 'calvin'],
                               'machine': ['bieber']}
        test_cfg['not_if'] = {'dumb_sys_var': ['stupid']}
        test_list.append(test_cfg)

        # Run through scenario of deferred(no-skip) into skip.
        for test_cfg in test_list:
            test = self._quick_test(cfg=test_cfg, finalize=False)
            self.assertFalse(test.skipped, msg="dumb_sys_var should be deferred"
                                               " with skip not assigned to"
                                               " the test")

            fin_sys = system_variables.SysVarDict(defer=False, unique=True)
            fin_var_man = VariableSetManager()
            fin_var_man.add_var_set('sys', fin_sys)
            test.finalize(fin_var_man)
            self.assertTrue(test.skipped, msg="Now it should skip")

        test_list = []
        # Test 5:
        # Not_if with deferred variable that resolves to  no skip.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'dumb_sys_var': ['notstupid']}
        test_list.append(test_cfg)

        # Test 6:
        # Only_if with deferred variable that resolves to no skip.
        test_cfg = base_cfg.copy()
        test_cfg['only_if'] = {'dumb_sys_var': ['stupid']}
        test_list.append(test_cfg)

        # Test 7:
        # Not_if and only_if-deferred that fails to skip.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'person': ['nivlac', 'notcalvin'],
                              'machine': ['blurg']}
        test_cfg['only_if'] = {'dumb_sys_var': ['stupid']}
        test_list.append(test_cfg)

        # Test 8:
        # Only_if and not_if-deferred that fails to skip.
        test_cfg = base_cfg.copy()
        test_cfg['only_if'] = {'person': ['nivlac', 'calvin'],
                               'machine': ['bieber']}
        test_cfg['not_if'] = {'dumb_sys_var': ['notstupid']}
        test_list.append(test_cfg)

        # Run through scenario of deferred(no-skip) into no skip.
        for test_cfg in test_list:
            test = self._quick_test(cfg=test_cfg, finalize=False)
            self.assertFalse(test.skipped, msg="dumb_sys_var should be deferred"
                                               " with skip not assigned to"
                                               " the test.")

            fin_sys = system_variables.SysVarDict(defer=False, unique=True)
            fin_var_man = VariableSetManager()
            fin_var_man.add_var_set('sys', fin_sys)
            test.finalize(fin_var_man)
            self.assertFalse(test.skipped, msg="Test Should NOT skip.")

    def test_regex(self):
        # The following tests test basic regex functionality of the
        # conditional tests. It checks to make sure various sequences
        # of regex or resolved correctly through only_if and not_if.

        test_list = []
        base_cfg = self._quick_test_cfg()
        base_cfg['variables'] = {'person': ['calvin'],
                                 'machine': ['bieber']}

        # Test 1:
        # Not_if with regex key that results in no skips
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'person': ['[0-9]']}
        test_list.append(test_cfg)

        # Test 2:
        # Only_if with regex that results in no skip.
        test_cfg = base_cfg.copy()
        test_cfg['only_if'] = {'person': ['^[a-z]{6}']}
        test_list.append(test_cfg)

        # Test 3:
        # Not_if fails to match with regex only_if matches.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'person': ['nivlac', ''],
                              'machine': ['blurg']}
        test_cfg['only_if'] = {'dumb_sys_var': ['[a-z]+$']}
        test_list.append(test_cfg)

        # Test 4:
        # Only_if that fails to skip with deferred not_if that skips.
        test_cfg = base_cfg.copy()
        test_cfg['only_if'] = {'person': ['nivlac', 'calvin'],
                               'machine': ['bieber']}
        test_cfg['not_if'] = {'dumb_sys_var': ['stupid']}
        test_list.append(test_cfg)

        for test_cfg in test_list:
            test = self._quick_test(cfg=test_cfg, finalize=False)
            self.assertFalse(test.skipped, msg="These tests should "
                                               "be skipped.")

        test_list = []  # reset list for skip tests.

        # Test 5:
        # Not_if the skips on any lowercase username.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'person': ['^[a-z]+$']}
        test_list.append(test_cfg)

        # Test 6:
        # Only_if that finds no match on 6 digit number.
        test_cfg = base_cfg.copy()
        test_cfg['only_if'] = {'person': ['^[0-9]{6}$']}
        test_list.append(test_cfg)

        # Test 7:
        # Not_if fails to match with regex only_if not matching.
        test_cfg = base_cfg.copy()
        test_cfg['not_if'] = {'person': ['nivlac', ''],
                              'machine': ['blurg']}
        test_cfg['only_if'] = {'dumb_sys_var': ['^[0-9]bleh$']}
        test_list.append(test_cfg)

        # Test 8:
        # Only_if that fails to skip with deferred not_if
        # regex that matches and appends ^ and $.
        test_cfg = base_cfg.copy()
        test_cfg['only_if'] = {'person': ['nivlac', 'calvin'],
                               'machine': ['bieber']}
        test_cfg['not_if'] = {'dumb_sys_var': ['[a-z]+']}
        test_list.append(test_cfg)

        for test_cfg in test_list:
            test = self._quick_test(cfg=test_cfg)
            self.assertTrue(test.skipped, msg="These tests should "
                                              "be skipped.")
