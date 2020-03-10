# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

import redturtle.rssservice


class RedturtleRssserviceLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        import plone.restapi
        self.loadZCML(package=plone.restapi)
        self.loadZCML(package=redturtle.rssservice)

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'redturtle.rssservice:default')


REDTURTLE_RSSSERVICE_FIXTURE = RedturtleRssserviceLayer()


REDTURTLE_RSSSERVICE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(REDTURTLE_RSSSERVICE_FIXTURE,),
    name='RedturtleRssserviceLayer:IntegrationTesting',
)


REDTURTLE_RSSSERVICE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(REDTURTLE_RSSSERVICE_FIXTURE,),
    name='RedturtleRssserviceLayer:FunctionalTesting',
)


REDTURTLE_RSSSERVICE_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        REDTURTLE_RSSSERVICE_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name='RedturtleRssserviceLayer:AcceptanceTesting',
)
