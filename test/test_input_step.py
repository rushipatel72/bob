# Bob build tool
# Copyright (C) 2016  Jan Klötzke
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from unittest import TestCase
from unittest.mock import Mock

from bob.input import CheckoutStep, BuildStep, PackageStep

class Empty:
    pass

class MockRecipeSet:
    def scmOverrides(self):
        return []

class MockRecipe:
    def getRecipeSet(self):
        return MockRecipeSet()

class MockPackage:
    def __init__(self):
        self.name = "package"

    def getName(self):
        return self.name

    def getRecipe(self):
        return MockRecipe()

nullPkg = MockPackage()
nullFmt = lambda s,t: ""


class TestCheckoutStep(TestCase):
    def testStereotype(self):
        """Check that the CheckoutStep identifies itself correctly"""
        s = CheckoutStep(nullPkg, nullFmt)
        assert s.isCheckoutStep() == True
        assert s.isBuildStep() == False
        assert s.isPackageStep() == False

    def testTrivialDeterministic(self):
        """Trivial steps are deterministic"""
        s = CheckoutStep(nullPkg, nullFmt)
        assert s.isDeterministic()

    def testTrivialInvalid(self):
        """Trivial steps are invalid"""
        s = CheckoutStep(nullPkg, nullFmt)
        assert s.isValid() == False

    def testDigestStable(self):
        """Same input should yield same digest"""
        s1 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            {"a" : "asdf", "q": "qwer" }, { "a" : "asdf" })
        s2 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            {"a" : "asdf", "q": "qwer" }, { "a" : "asdf" })
        assert s1.getVariantId() == s2.getVariantId()

    def testDigestScriptChange(self):
        """Script does influnce the digest"""
        s1 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            {"a" : "asdf", "q": "qwer" }, { "a" : "asdf" })
        s2 = CheckoutStep(nullPkg, nullFmt, None, ("evil", []),
            {"a" : "asdf", "q": "qwer" }, { "a" : "asdf" })
        assert s1.getVariantId() != s2.getVariantId()

    def testDigestFullEnv(self):
        """Full env does not change digest. It is only used for SCMs."""
        s1 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            {"a" : "asdf", "q": "qwer" }, { "a" : "asdf" })
        s2 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            { }, { "a" : "asdf" })
        assert s1.getVariantId() == s2.getVariantId()

    def testDigestEnv(self):
        """Env changes digest"""
        s1 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            env={ "a" : "asdf" })

        # different value
        s2 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            env={ "a" : "qwer" })
        assert s1.getVariantId() != s2.getVariantId()

        # added entry
        s2 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            env={ "a" : "asdf", "b" : "qwer" })
        assert s1.getVariantId() != s2.getVariantId()

        # removed entry
        s2 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            env={ })
        assert s1.getVariantId() != s2.getVariantId()

    def testDigestEnvRotation(self):
        """Rotating characters between key-value pairs must be detected"""
        s1 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            env={ "a" : "bc", "cd" : "e" })
        s2 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            env={ "a" : "bcc", "d" : "e" })
        assert s1.getVariantId() != s2.getVariantId()

        s1 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            env={ "a" : "bb", "c" : "dd", "e" : "ff" })
        s2 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            env={ "a" : "bbc=dd", "e" : "ff" })
        assert s1.getVariantId() != s2.getVariantId()

    def testDigestEmpyEnv(self):
        """Adding empty entry must be detected"""
        s1 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            env={ "a" : "b" })
        s2 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            env={ "a" : "b", "" : "" })
        assert s1.getVariantId() != s2.getVariantId()

    def testDigestTools(self):
        """Tools must influence digest"""
        t1 = Empty()
        t1.step = Empty()
        t1.step.getVariantId = Mock(return_value=b'0123456789abcdef')
        t1.step._getStableVariantId = t1.step.getVariantId
        t1.path = "p1"
        t1.libs = []

        s1 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            tools={"a" : t1})

        # tool name has no influence
        s2 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            tools={"zz" : t1})
        assert s1.getVariantId() == s2.getVariantId()

        # step digest change
        t2 = Empty()
        t2.step = Empty()
        t2.step.getVariantId = Mock(return_value=b'0123456789000000')
        t2.step._getStableVariantId = t2.step.getVariantId
        t2.path = "p1"
        t2.libs = []

        s2 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            tools={"a" : t2})
        assert s1.getVariantId() != s2.getVariantId()

        # path change
        t2.step.getVariantId = Mock(return_value=b'0123456789abcdef')
        t2.step._getStableVariantId = t2.step.getVariantId
        t2.path = "foo"
        t2.libs = []

        s2 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            tools={"a" : t2})
        assert s1.getVariantId() != s2.getVariantId()

        # libs change
        t2.step.getVariantId = Mock(return_value=b'0123456789abcdef')
        t2.step._getStableVariantId = t2.step.getVariantId
        t2.path = "p1"
        t2.libs = ["asdf"]

        s2 = CheckoutStep(nullPkg, nullFmt, None, ("script", []),
            tools={"a" : t2})
        assert s1.getVariantId() != s2.getVariantId()

