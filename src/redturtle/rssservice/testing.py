# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.restapi.testing import PloneRestApiDXLayer
from plone.testing import z2

import redturtle.rssservice
import plone.restapi


class RedTurtleRSSServiceLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        self.loadZCML(package=plone.restapi)
        self.loadZCML(package=redturtle.rssservice)

    def setUpPloneSite(self, portal):
        applyProfile(portal, "plone.restapi:default")


REDTURTLE_RSSSERVICE_FIXTURE = RedTurtleRSSServiceLayer()


REDTURTLE_RSSSERVICE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(REDTURTLE_RSSSERVICE_FIXTURE,),
    name="RedTurtleRSSServiceLayer:IntegrationTesting",
)


REDTURTLE_RSSSERVICE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(REDTURTLE_RSSSERVICE_FIXTURE,),
    name="RedTurtleRSSServiceLayer:FunctionalTesting",
)


REDTURTLE_RSSSERVICE_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        REDTURTLE_RSSSERVICE_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name="RedTurtleRSSServiceLayer:AcceptanceTesting",
)


class RedTurtleRSSServiceRestApiLayer(PloneRestApiDXLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        super(RedTurtleRSSServiceRestApiLayer, self).setUpZope(
            app, configurationContext
        )

        self.loadZCML(package=plone.restapi)
        self.loadZCML(package=redturtle.rssservice)

    def setUpPloneSite(self, portal):
        applyProfile(portal, "plone.restapi:default")


REDTURTLE_RSSSERVICE_API_FIXTURE = RedTurtleRSSServiceRestApiLayer()
REDTURTLE_RSSSERVICE_API_INTEGRATION_TESTING = IntegrationTesting(
    bases=(REDTURTLE_RSSSERVICE_API_FIXTURE,),
    name="RedTurtleRSSServiceRestApiLayer:Integration",
)

REDTURTLE_RSSSERVICE_API_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(REDTURTLE_RSSSERVICE_API_FIXTURE, z2.ZSERVER_FIXTURE),
    name="RedTurtleRSSServiceRestApiLayer:Functional",
)
